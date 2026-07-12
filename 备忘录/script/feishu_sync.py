#!/usr/bin/env python3
"""
备忘录 ↔ 飞书任务 同步模块

第一性原则：
1. 本地优先：memo DB 是 Single Source of Truth，飞书是镜像
2. 自动检测：is_feishu_available() 决定是否联动（不靠环境变量开关）
3. 失败降级：飞书 API 失败不阻塞本地操作，只记录 warning
4. 反向查找：notes.feishu_task_guid 是 memo → 飞书的反向 key

支持的飞书操作（V2）：
- add_wish_sync(memo_id, content): 建飞书 task，返回 task_guid
- update_wish_sync(task_guid, content): 改飞书 task 内容
- complete_wish_sync(task_guid): 标飞书 task 完成
- sync_from_feishu(): 反向同步（拉飞书已完成 task → 触发本地 complete-wish）

支持的平台：
- Windows: %APPDATA%\\npm\\lark-cli.cmd
- WSL/Linux/Mac: which lark-cli
"""
import json
import time
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Optional
from memo_cli import DB_PATH


# ==================== 配置 ====================
# ⚠️ 第一性原则：技能不能硬编码用户特定信息
#   1. 备忘录不复制用户身份（lark-cli auth status 是真值源）
#   2. 不要求用户设置环境变量（open_id 自动检测）
#   3. DB 路径统一走 memo_cli.DB_PATH（两层查找：环境变量 > D:/.db）


# open_id 缓存
_USER_OPEN_ID_CACHE: Optional[str] = None
_USER_OPEN_ID_FAILED = False


def _get_user_open_id() -> Optional[str]:
    """从 lark-cli auth 读取当前 user open_id（带缓存）

    第一性原则：
      - lark-cli auth login 后的 identity 是真值源
      - 备忘录不再要求设置 MEMO_FEISHU_USER_OPEN_ID 环境变量
      - 模块级缓存避免每次 add 心愿都 sub-process
      - 失败一次后标记失败,不再重复探测

    返回：open_id 字符串或 None（None 表示 lark-cli 不可用/未登录）
    """
    global _USER_OPEN_ID_CACHE, _USER_OPEN_ID_FAILED
    if _USER_OPEN_ID_CACHE is not None:
        return _USER_OPEN_ID_CACHE
    if _USER_OPEN_ID_FAILED:
        return None
    if not is_feishu_available():
        _USER_OPEN_ID_FAILED = True
        return None

    cli = get_lark_cli_path()
    try:
        # lark-cli auth status 默认就输出 JSON 到 stdout
        proc = subprocess.run(
            [cli, "auth", "status"],
            capture_output=True, timeout=5,
        )
        raw = proc.stdout
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        if not raw.strip():
            _USER_OPEN_ID_FAILED = True
            return None
        d = json.loads(raw.decode("utf-8"))
        open_id = d.get("identities", {}).get("user", {}).get("openId")
        if open_id:
            _USER_OPEN_ID_CACHE = open_id
            return open_id
        _USER_OPEN_ID_FAILED = True
        return None
    except Exception:
        _USER_OPEN_ID_FAILED = True
        return None


# ==================== 跨平台 CLI 探测 ====================

def _find_lark_cli() -> Optional[str]:
    """跨平台查找 lark-cli 可执行文件路径"""
    if sys.platform == "win32":
        # Windows: 优先 %APPDATA%\\npm\\lark-cli.cmd
        appdata = os.environ.get("APPDATA", "")
        candidate = Path(appdata) / "npm" / "lark-cli.cmd"
        if candidate.exists():
            return str(candidate)
        # 回退: where lark-cli
        try:
            r = subprocess.run(["where", "lark-cli"], capture_output=True, timeout=5)
            if r.returncode == 0:
                encoding = sys.getdefaultencoding()
                return r.stdout.decode(encoding, errors="replace").strip().split("\n")[0].strip()
        except Exception:
            pass
    else:
        # POSIX (Linux/WSL/Mac): which lark-cli
        try:
            r = subprocess.run(
                ["which", "lark-cli"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=5,
            )
            if r.returncode == 0:
                return r.stdout.strip().split("\n")[0].strip()
        except Exception:
            pass
        # 常见路径回退
        for candidate in ["/usr/local/bin/lark-cli", "/usr/bin/lark-cli"]:
            if Path(candidate).exists():
                return candidate
    return None


_LARK_CLI_CACHE: dict = {"path": None, "fetched_at": 0.0}
_CACHE_TTL = 300  # 5 分钟（5min 后自动重探测，避免永久缓存失效路径）


def is_feishu_available(force_refresh: bool = False) -> bool:
    """检测飞书 CLI 是否可用（带 TTL 缓存 + 强制刷新参数）

    Args:
        force_refresh: True 时忽略缓存，重新探测（用于路径变更后手动刷新）
    """
    global _LARK_CLI_CACHE
    if (
        force_refresh
        or _LARK_CLI_CACHE["path"] is None
        or (time.time() - _LARK_CLI_CACHE["fetched_at"] > _CACHE_TTL)
    ):
        path = _find_lark_cli()
        _LARK_CLI_CACHE = {"path": path, "fetched_at": time.time()}
    return _LARK_CLI_CACHE["path"] is not None


def get_lark_cli_path() -> Optional[str]:
    """获取 lark-cli 路径（必须在 is_feishu_available() 后调用）"""
    return _LARK_CLI_CACHE["path"]


# ==================== lark-cli 包装 ====================

def _run_lark(args: list, timeout: int = 30) -> dict:
    """调 lark-cli，捕获输出并解析 JSON"""
    cli = get_lark_cli_path()
    if not cli:
        return {"ok": False, "error": "lark-cli not available"}
    try:
        proc = subprocess.run(
            [cli] + args,
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=timeout,
        )
        out = (proc.stdout or proc.stderr or "").strip()
        try:
            return json.loads(out)
        except json.JSONDecodeError:
            return {"_raw": out[:300], "_stderr": proc.stderr[:200], "ok": False}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==================== 同步操作 ====================

def add_wish_sync(memo_id: int, content: str, category: str = "心愿",
                  tasklist_guid: Optional[str] = None) -> dict:
    """新建飞书 task,返回 {ok, task_guid, error}

    第一性原则：
    - lark-cli auth 身份 = assignee 真值源,自动检测（不读 env）
    - 飞书 task 可不指定 tasklist（tasklists 是可选字段），会进飞书"我的任务"主页
    - tasklist_guid 由调用方显式传入（CLI 参数），不读环境变量"预配置"
    - 零配置即可使用飞书联动（不传 tasklist_guid → 进飞书主页）

    行为：
      1. 自动从 lark-cli auth 读 user open_id（缓存）
      2. 接受 tasklist_guid 参数（可选，默认 None）
      3. 调 lark-cli `task +create --summary <title> --description <desc> --assignee <open_id> [--tasklist-id <guid>]`
      4. 返回 task_guid（用于写入 notes.feishu_task_guid）

    参数：
      memo_id: memo note id（用于编码到 description 反查）
      content: 飞书 task 标题
      category: memo 分类（保留扩展性，目前不影响 tasklist 选择）
      tasklist_guid: 飞书 tasklist GUID（可选）。None → task 进飞书"我的任务"主页

    返回：
      {"ok": bool, "task_guid": str | None, "error": str | None}
    """
    # 配置检查：从 lark-cli auth 自动读取 open_id（缓存）
    user_open_id = _get_user_open_id()
    if not user_open_id:
        return {"ok": False, "task_guid": None, "error": "无法从 lark-cli auth 读取 user open_id（请先 lark-cli auth login）"}

    # 用 lark-cli 的 flag 模式（避免 --data positional 解析问题）
    # 注：飞书 task create 不支持 extra 字段（API 拒绝）
    #     memo_id 编码进 description（"原备忘 #N"），靠正则反查
    args = [
        "task", "+create",
        "--summary", content[:200],  # 飞书 title 最长 3000 字符
        "--description", f"原备忘 #{memo_id}",
        "--assignee", user_open_id,
    ]
    # 只有传了 tasklist_guid 才加（飞书会建无 tasklist 的 task 在"我的任务"主页）
    if tasklist_guid:
        args += ["--tasklist-id", tasklist_guid]
    r = _run_lark(args)

    if r.get("ok"):
        task_data = r.get("data") or {}
        task_guid = task_data.get("task", {}).get("guid") or task_data.get("guid")
        return {"ok": True, "task_guid": task_guid, "error": None}
    else:
        return {"ok": False, "task_guid": None, "error": r.get("error") or r.get("_raw", "unknown")}


def update_wish_sync(task_guid: str, content: str) -> dict:
    """更新飞书 task 标题

    返回：{"ok": bool, "error": str | None}
    """
    r = _run_lark([
        "task", "+update",
        "--task-id", task_guid,
        "--summary", content[:200],
    ])
    return {"ok": r.get("ok", False), "error": r.get("error") if not r.get("ok") else None}


def complete_wish_sync(task_guid: str) -> dict:
    """标飞书 task 完成

    返回：{"ok": bool, "error": str | None}
    """
    r = _run_lark(["task", "+complete", "--task-id", task_guid])
    return {"ok": r.get("ok", False), "error": r.get("error") if not r.get("ok") else None}


def update_due_sync(task_guid: str, due_iso: str) -> dict:
    """更新飞书 task due 日期

    第一性：备忘录 notes.due 是 SoT, 飞书 task.due 是镜像。
    飞书 tasklist +update --due 接受 ISO 8601 / YYYY-MM-DD / 相对时间 / ms timestamp。

    参数：
      task_guid: 飞书 task GUID
      due_iso: ISO 日期 "YYYY-MM-DD"（如 "2026-06-30"）

    返回：{"ok": bool, "error": str | None}
    """
    if not task_guid:
        return {"ok": False, "error": "task_guid is required"}
    if not due_iso:
        return {"ok": False, "error": "due_iso is required"}
    r = _run_lark([
        "task", "+update",
        "--task-id", task_guid,
        "--due", due_iso,
    ])
    return {"ok": r.get("ok", False), "error": r.get("error") if not r.get("ok") else None}


def clear_due_sync(task_guid: str) -> dict:
    """清除飞书 task due（与本地 notes.due=null 镜像）

    第一性：
      - 飞书 task.update API 中 due=null 是合法值，服务端识别为"清空"
      - lark-cli 不暴露 --due=null 之类的清空 flag（只有 --due <ISO 日期>）
      - 只能走 --data JSON payload `{"due": null}` 显式传 null

    注意：PowerShell 直接调 `lark-cli ... --data '{"due": null}'` 会失败,因为
      PowerShell 把单引号字符串当字面量保留,argv[6] 实际是 `'{...}'`(首字符 `'`),
      触发 lark-cli 校验 "invalid character 'd' looking for beginning of object key string"。
    解决:用 Python 的 subprocess.run(list) 模式 → 跳过 PowerShell 字符串解析,
      由 Windows CreateProcess + CommandLineToArgvW 正确拆 argv。

    与 update_due_sync 的对称：
      - update: 本地 due 非空 → 调 update_due_sync
      - clear: 本地 due 为空 → 调 clear_due_sync（新增）

    参数：
      task_guid: 飞书 task GUID

    返回：{"ok": bool, "error": str | None}
    """
    if not task_guid:
        return {"ok": False, "error": "task_guid is required"}

    cli = get_lark_cli_path()
    if not cli:
        return {"ok": False, "error": "lark-cli path not cached"}

    data_payload = '{"due": null}'

    try:
        # 不分 Windows/POSIX,统一用 list 模式(Windows 上 Python 已正确处理引号)
        proc = subprocess.run(
            [cli, "task", "+update",
             "--task-id", task_guid,
             "--data", data_payload],
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=30,
        )

        out = (proc.stdout or proc.stderr or "").strip()
        try:
            r = json.loads(out)
        except json.JSONDecodeError:
            return {"ok": False, "error": out[:200]}

        return {"ok": r.get("ok", False), "error": r.get("error") if not r.get("ok") else None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ==================== V4: 反向同步（含 due）====================

def _list_all_tasks() -> list:
    """列出飞书所有 task（不区分 status,caller 按 status 过滤）

    第一性:list 接口不带 due 字段,所以一次拉全量交给 caller 处理:
      - status=done → 步骤 2 (反向 complete-wish)
      - status=todo → 步骤 3 (反向 due 同步)
    """
    if not is_feishu_available():
        return []

    r = _run_lark(["task", "+get-related-tasks"])
    if not r.get("ok"):
        return []

    return (r.get("data") or {}).get("items") or []


def _get_task_detail(task_guid: str) -> Optional[dict]:
    """获取飞书 task 完整详情（含 due 字段）

    与 list 接口不同,单 task 接口才返回 due.timestamp。
    """
    r = _run_lark(["task", "tasks", "get", "--task-guid", task_guid])
    if not r.get("ok"):
        return None
    return (r.get("data") or {}).get("task") or {}


def _parse_feishu_due(due_dict) -> Optional[str]:
    """飞书 due dict → 本地 YYYY-MM-DD 字符串

    飞书结构: {"is_all_day": True, "timestamp": "1782864000000"}  (ms UTC)
    换算: UTC ms → 北京日期(BJ = UTC + 8h)
    无 due / due 字段 absent → 返回 None

    注:这里只解析,不构造,反向构造由 memo_cli.set_due → update_due_sync 处理
    """
    if not due_dict:
        return None
    ts = due_dict.get("timestamp")
    if not ts:
        return None
    from datetime import datetime, timezone, timedelta
    dt_utc = datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)
    dt_bj = dt_utc.astimezone(timezone(timedelta(hours=8)))
    return dt_bj.strftime("%Y-%m-%d")


def _backfill_local_wishes(conn) -> int:
    """本地补建：notes 中 category=心愿 AND feishu_task_guid IS NULL → 调 add_wish_sync 建飞书 task

    第一性：
    - 补建 = "本地有,飞书没"的对账,让飞书镜像符合本地 source of truth
    - 单条失败不阻塞其他,累积到 caller 的 errors
    - 写回 feishu_task_guid 是关键,否则下一轮 sync 会重复尝试

    返回: 成功补建的 note 数
    """
    rows = conn.execute(
        "SELECT id, content FROM notes WHERE category = '心愿' AND feishu_task_guid IS NULL ORDER BY id"
    ).fetchall()
    if not rows:
        return 0

    n_synced = 0
    for r in rows:
        memo_id, content = r["id"], r["content"]
        rr = add_wish_sync(memo_id, content, "心愿")
        if rr.get("ok") and rr.get("task_guid"):
            conn.execute(
                "UPDATE notes SET feishu_task_guid = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (rr["task_guid"], memo_id),
            )
            conn.commit()
            n_synced += 1
        # 失败不阻塞,下一轮 sync 会重试
    return n_synced


def sync_from_feishu(db_path: str = None) -> dict:
    """完整同步:本地心愿补建飞书 task + 飞书 done → 本地 complete-wish + 飞书 todo due → 本地 notes.due

    第一性原则:
      - "同步" = 双向对账(本地补建 + 反向同步 done + 反向同步 due)
      - 本地是 source of truth(写入时 SoT);飞书是镜像;对账时飞书优先(用户主动触发 sync 即视同飞书说了算)
      - due 反向同步仅处理 status=todo 的 task(已完成 task 的 due 已无价值)
      - list 接口不带 due 字段,所以一次拉全量、按 status 分流,步骤 3 逐个 get 详情

    流程:
      步骤 1: 本地补建 (本地 → 飞书)
        - 查 notes WHERE category='心愿' AND feishu_task_guid IS NULL
        - 对每个 note 调 add_wish_sync 建飞书 task
        - 成功 → UPDATE notes.feishu_task_guid
        - 失败 → 不阻塞,下一轮会重试

      步骤 2: 反向同步 done (飞书 → 本地)
        - 筛 status=done 的 task
        - 用 description 反查 memo_id
        - 本地心愿还在 → 触发 complete-wish

      步骤 3: 反向同步 due (飞书 → 本地, 仅 status=todo)
        - 逐个 task tasks get 拉 due.timestamp → YYYY-MM-DD (UTC ms → 北京日期)
        - 飞书优先四象限(用户决策):
          * 飞书有/本地无 → 写本地 (due_added)
          * 飞书有/本地有且不同 → 覆盖本地 (due_overridden)
          * 飞书无/本地有 → 清本地 (due_removed)
          * 一致 → 跳过

    返回:
      {
        "backfilled": int,           # 步骤1 本地补建数
        "scanned_done": int,         # 步骤2 飞书 done task 数
        "synced": int,               # 步骤2 触发的 complete-wish 数
        "scanned_pending": int,      # 步骤3 飞书 todo task 数
        "due_added": int,            # 步骤3 飞书新加 due → 写入本地
        "due_overridden": int,       # 步骤3 飞书改 due → 覆盖本地
        "due_removed": int,          # 步骤3 飞书清 due → 本地也清
        "skipped_no_memo_id": int,
        "skipped_already_done": int,
        "skipped_no_local_note": int,
        "errors": [str],
      }
    """
    if not is_feishu_available():
        return {
            "backfilled": 0, "scanned_done": 0, "synced": 0,
            "scanned_pending": 0, "due_added": 0, "due_overridden": 0, "due_removed": 0,
            "errors": ["feishu CLI not available"],
        }

    if db_path is None:
        db_path = str(DB_PATH)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 步骤 1: 本地补建 (本地 → 飞书)
    n_backfilled = _backfill_local_wishes(conn)

    # 一次 list 全量,按 status 分流到步骤 2/3
    items = _list_all_tasks()
    done_tasks = [t for t in items if t.get("status") == "done"]
    todo_tasks = [t for t in items if t.get("status") == "todo"]

    result = {
        "backfilled": n_backfilled,
        "scanned_done": len(done_tasks),
        "synced": 0,
        "scanned_pending": len(todo_tasks),
        "due_added": 0,
        "due_overridden": 0,
        "due_removed": 0,
        "skipped_no_memo_id": 0,
        "skipped_already_done": 0,
        "skipped_no_local_note": 0,
        "errors": [],
    }
    memo_cli = os.path.join(os.path.dirname(__file__), "memo_cli.py")
    memo_python = sys.executable

    import re
    memo_id_re = re.compile(r"原备忘\s*#(\d+)")

    # 步骤 2: 反向同步 done (飞书 → 本地 complete-wish)
    for t in done_tasks:
        task_guid = t.get("guid")
        if not task_guid:
            continue

        desc = t.get("description", "")
        m = memo_id_re.search(desc)
        if not m:
            result["skipped_no_memo_id"] += 1
            continue
        memo_id = int(m.group(1))

        # 反查本地
        local = conn.execute(
            "SELECT id, category FROM notes WHERE id = ? AND feishu_task_guid = ?",
            (memo_id, task_guid),
        ).fetchone()

        if not local:
            # 本地 note 不存在或飞书 guid 不匹配
            result["skipped_no_local_note"] += 1
            continue

        if local["category"] != "心愿":
            # 不是心愿分类(如已变成打卡)→ 已处理过
            result["skipped_already_done"] += 1
            continue

        # 触发本地 complete-wish
        try:
            proc = subprocess.run(
                [memo_python, memo_cli, "complete-wish", str(memo_id)],
                capture_output=True, encoding="utf-8", timeout=10,
            )
            if proc.returncode == 0:
                result["synced"] += 1
            else:
                result["errors"].append(f"complete memo_id={memo_id}: {proc.stdout[:200]}")
        except Exception as e:
            result["errors"].append(f"complete memo_id={memo_id}: {e}")

    # 步骤 3: 反向同步 due (飞书 → 本地 notes.due, 飞书优先)
    for t in todo_tasks:
        task_guid = t.get("guid")
        if not task_guid:
            continue

        desc = t.get("description", "")
        m = memo_id_re.search(desc)
        if not m:
            result["skipped_no_memo_id"] += 1
            continue
        memo_id = int(m.group(1))

        local = conn.execute(
            "SELECT id, due, category FROM notes WHERE id = ? AND feishu_task_guid = ?",
            (memo_id, task_guid),
        ).fetchone()

        if not local:
            result["skipped_no_local_note"] += 1
            continue

        if local["category"] != "心愿":
            result["skipped_already_done"] += 1
            continue

        # 拉飞书 task 详情取 due
        task = _get_task_detail(task_guid)
        if not task:
            result["errors"].append(f"due memo_id={memo_id}: failed to get task detail")
            continue

        feishu_due = _parse_feishu_due(task.get("due"))
        local_due = local["due"]

        if feishu_due == local_due:
            # 一致 → 跳过
            continue

        # 飞书优先四象限处理
        conn.execute(
            "UPDATE notes SET due = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (feishu_due, memo_id),  # feishu_due 为 None 时写 NULL
        )
        conn.commit()

        if feishu_due is None:
            # 飞书清 due → 本地也清(用户决策)
            result["due_removed"] += 1
        elif local_due is None:
            # 飞书新加 due → 写本地
            result["due_added"] += 1
        else:
            # 飞书改 due,本地不同 → 覆盖
            result["due_overridden"] += 1

    conn.close()
    return result


# ==================== CLI 入口 ====================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="备忘录 ↔ 飞书同步模块")
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="检测飞书 CLI 是否可用")

    p_add = sub.add_parser("add", help="建飞书 task")
    p_add.add_argument("--memo-id", type=int, required=True)
    p_add.add_argument("--content", required=True)
    p_add.add_argument("--category", default="心愿")
    p_add.add_argument("--tasklist-guid", help="飞书 tasklist GUID（可选，不传则 task 进飞书'我的任务'主页）")

    p_complete = sub.add_parser("complete", help="标飞书 task 完成")
    p_complete.add_argument("--task-guid", required=True)

    p_update = sub.add_parser("update", help="更新飞书 task 标题")
    p_update.add_argument("--task-guid", required=True)
    p_update.add_argument("--content", required=True)

    p_sync = sub.add_parser("sync-from-feishu", help="反向同步（飞书 done → 本地 complete-wish）")
    p_list_tl = sub.add_parser("list-tasklists", help="列出飞书所有 tasklist（配置用）")

    args = parser.parse_args()

    if args.command == "check":
        ok = is_feishu_available()
        print(json.dumps({"available": ok, "cli_path": get_lark_cli_path()}, ensure_ascii=False, indent=2))
    elif args.command == "add":
        result = add_wish_sync(args.memo_id, args.content, args.category, args.tasklist_guid)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "complete":
        result = complete_wish_sync(args.task_guid)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "update":
        result = update_wish_sync(args.task_guid, args.content)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "sync-from-feishu":
        result = sync_from_feishu()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "list-tasklists":
        # 列出飞书所有 tasklist（用户偶尔指定 --tasklist-guid 时用）
        r = _run_lark(["task", "tasklists", "list"])
        items = (r.get("data") or {}).get("items") or []
        output = [{"name": t["name"], "guid": t["guid"]} for t in items]
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()