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
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Optional


# ==================== 配置 ====================
# ⚠️ 第一性原则：技能不能硬编码用户特定信息
#   1. 备忘录不复制用户身份（lark-cli auth status 是真值源）
#   2. 不要求用户设置环境变量（open_id 自动检测）
#   3. DB 路径仍走环境变量（SKILLS_DB_PATH），因为是路径而非身份

# memo DB 路径环境变量（与 memo_cli.py 共享）
ENV_SKILLS_DB_PATH = "SKILLS_DB_PATH"


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


def _get_memo_db_path() -> str:
    """取 memo DB 路径（跟随 memo_cli.py 的查找逻辑）"""
    # 1. 环境变量 SKILLS_DB_PATH（最高优先级）
    env_path = os.environ.get(ENV_SKILLS_DB_PATH)
    if env_path:
        return os.path.join(env_path, "memo.db")
    # 2. 父目录 .db/ 层层找（与 memo_cli._find_db_path 行为一致）
    script_dir = Path(__file__).parent.parent  # 技能目录
    for parent in script_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            return str(db_dir / "memo.db")
    # 3. 技能目录下 .db/memo.db（最后 fallback）
    default_dir = script_dir / ".db"
    default_dir.mkdir(exist_ok=True)
    return str(default_dir / "memo.db")


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
                return r.stdout.strip().split("\n")[0].strip()
        except Exception:
            pass
    else:
        # POSIX (Linux/WSL/Mac): which lark-cli
        try:
            r = subprocess.run(["which", "lark-cli"], capture_output=True, timeout=5)
            if r.returncode == 0:
                return r.stdout.strip().split("\n")[0].strip()
        except Exception:
            pass
        # 常见路径回退
        for candidate in ["/usr/local/bin/lark-cli", "/usr/bin/lark-cli"]:
            if Path(candidate).exists():
                return candidate
    return None


_LARK_CLI_CACHE: Optional[str] = None


def is_feishu_available() -> bool:
    """检测飞书 CLI 是否可用（带缓存，避免重复探测）"""
    global _LARK_CLI_CACHE
    if _LARK_CLI_CACHE is None:
        _LARK_CLI_CACHE = _find_lark_cli()
    return _LARK_CLI_CACHE is not None


def get_lark_cli_path() -> Optional[str]:
    """获取 lark-cli 路径（必须在 is_feishu_available() 后调用）"""
    return _LARK_CLI_CACHE


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


# ==================== V3: 反向同步 ====================

def _list_all_done_tasks() -> list:
    """列出飞书所有 status=done 的 task"""
    if not is_feishu_available():
        return []

    r = _run_lark(["task", "+get-related-tasks"])
    if not r.get("ok"):
        return []

    items = (r.get("data") or {}).get("items") or []
    return [t for t in items if t.get("status") == "done"]


def _get_task_memo_id(task_guid: str) -> Optional[int]:
    """从飞书 task description 反查 memo_id（正则提取 '原备忘 #N'）

    返回：memo_id (int) 或 None
    """
    import re
    r = _run_lark(["task", "tasks", "get", "--task-guid", task_guid])
    if not r.get("ok"):
        return None
    task = (r.get("data") or {}).get("task", {})
    desc = task.get("description", "")
    if not desc:
        return None
    m = re.search(r"原备忘\s*#(\d+)", desc)
    if m:
        return int(m.group(1))
    return None


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
    """完整同步:本地心愿补建飞书 task + 飞书 done → 本地 complete-wish

    第一性原则:
      - "同步" = 双向对账(本地补建 + 反向同步)
      - 本地是 source of truth,飞书是镜像
      - 不破坏现有报告结构(向后兼容),新加 backfilled 字段

    流程:
      步骤 1: 本地补建 (本地 → 飞书)
        - 查 notes WHERE category='心愿' AND feishu_task_guid IS NULL
        - 对每个 note 调 add_wish_sync 建飞书 task
        - 成功 → UPDATE notes.feishu_task_guid
        - 失败 → 不阻塞,下一轮会重试

      步骤 2: 反向同步 (飞书 → 本地)
        - 拉飞书所有 done task
        - 用 description 反查 memo_id
        - 本地心愿还在 → 触发 complete-wish

    返回:
      {
        "backfilled": int,        # 本地补建数(步骤 1)
        "scanned": int,           # 飞书 done task 数(步骤 2)
        "synced": int,            # 触发的本地 complete-wish 数(步骤 2)
        "skipped_no_memo_id": int,
        "skipped_already_done": int,
        "skipped_no_local_note": int,
        "errors": [str],
      }
    """
    if not is_feishu_available():
        return {"backfilled": 0, "scanned": 0, "synced": 0, "errors": ["feishu CLI not available"]}

    if db_path is None:
        # 默认 DB 路径(通过 _get_memo_db_path 自动探测,不写死任何用户路径)
        db_path = _get_memo_db_path()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 步骤 1: 本地补建 (本地 → 飞书)
    n_backfilled = _backfill_local_wishes(conn)

    # 步骤 2: 反向同步 (飞书 → 本地)
    done_tasks = _list_all_done_tasks()

    result = {
        "backfilled": n_backfilled,
        "scanned": len(done_tasks),
        "synced": 0,
        "skipped_no_memo_id": 0,
        "skipped_already_done": 0,
        "skipped_no_local_note": 0,
        "errors": [],
    }
    memo_cli = os.path.join(os.path.dirname(__file__), "memo_cli.py")
    memo_python = sys.executable

    for t in done_tasks:
        task_guid = t.get("guid")
        if not task_guid:
            continue

        # 从 description 反查 memo_id
        memo_id = _get_task_memo_id(task_guid)
        if not memo_id:
            result["skipped_no_memo_id"] += 1
            continue

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
                result["errors"].append(f"memo_id={memo_id}: {proc.stdout[:200]}")
        except Exception as e:
            result["errors"].append(f"memo_id={memo_id}: {e}")

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