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
import functools
import json
import time
import os
import shutil
import sqlite3
import subprocess
import sys
import traceback
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


# ==================== 权限编排(#46 · 2026-08-08 · 单一真值源) ====================
# 备忘录飞书联动需要的最小写权限集合。check 差集 / 授权引导 / sentinel 实测 全部以此为准。
# 来源:lark-cli research 实证(#195)——task/calendar 写权限 scope 标识符,与开发者后台批量导出一致。
# 注意:这些写权限属飞书开放平台「需审核权限」,必须先应用后台申请+审核+发布版本,授权页才会出现。
REQUIRED_SCOPES = [
    # task 域:心愿 → 飞书任务(创建/更新/完成)
    "task:task:write",
    "task:tasklist:write",
    # calendar 域:日程(创建/更新/删除)
    "calendar:calendar.event:create",
    "calendar:calendar.event:update",
    "calendar:calendar.event:delete",
]

# sentinel 实测前缀(必清协议标识):所有测试任务/日程必须带此前缀,用户可识别并手动删除
SENTINEL_PREFIX = "[备忘录测试]"


def reset_user_open_id_cache() -> None:
    """重置 open_id 缓存与失败标志(B3 修复)。

    #46 B3:进程内失败标志不重置 → 用户 auth login 成功后仍报未登录。
    登录/授权流程完成后调用本函数,下一次读取即重新探测(反映最新登录状态)。
    """
    global _USER_OPEN_ID_CACHE, _USER_OPEN_ID_FAILED
    _USER_OPEN_ID_CACHE = None
    _USER_OPEN_ID_FAILED = False


def _get_user_open_id() -> Optional[str]:
    """从 lark-cli auth status 读取当前 user open_id（带缓存）

    第一性原则：
      - lark-cli auth login 后的 identity 是真值源(auth status 输出 identities.user.openId)
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
        # B1 修复:Windows .cmd 包装器以自身所在目录为 cwd 执行,避免相对路径/环境问题
        kwargs = {}
        if sys.platform == "win32" and str(cli).lower().endswith(".cmd"):
            kwargs["cwd"] = os.path.dirname(str(cli))
        proc = subprocess.run(
            [cli, "auth", "status"],
            capture_output=True, timeout=5, **kwargs,
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
                lines = [l.strip() for l in r.stdout.decode(encoding, errors="replace").split("\n") if l.strip()]
                # B1 修复:多行输出优先选 .cmd(Windows npm 包装器),避免选到 .exe 导致命令行为差异
                cmd_lines = [l for l in lines if l.lower().endswith(".cmd")]
                if cmd_lines:
                    return cmd_lines[0]
                if lines:
                    return lines[0]
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
        # B1 修复:Windows .cmd 包装器以自身所在目录为 cwd 执行
        kwargs = {}
        if sys.platform == "win32" and str(cli).lower().endswith(".cmd"):
            kwargs["cwd"] = os.path.dirname(str(cli))
        proc = subprocess.run(
            [cli] + args,
            capture_output=True, encoding="utf-8", errors="replace",
            timeout=timeout, **kwargs,
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

def _traceback_guard(fn):
    """B4 防御(B4 修复 · #46):sync 函数任何未捕获异常 → 结构化 error + traceback。

    用户视角:以前同步失败只看到「同步失败」四个字;现在 error 字段带完整 traceback,
    可自助排查(文档要求)。返回值兼容 add_wish_sync / update_* / complete_* 等所有调用方
    (外部只读 ok / task_guid / error;existed 仅模块内部使用)。
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            return {
                "ok": False,
                "task_guid": None,
                "existed": False,
                "error": f"{e}\n{traceback.format_exc()}",
            }
    return wrapper


def _search_feishu_task_by_due_and_summary(due_iso: str, summary: str) -> Optional[str]:
    """查飞书 task 列表,找同 summary + due 的 task,返回 guid;没有返回 None。

    用途:add_wish_sync 前的双侧查重(类似作息管家 diff_and_sync 的第二步)。
    2026-07-14 实测 lark-cli task +search --format json 返回字段:
      data.items[].summary   (str, 标题)
      data.items[].due_at    (str, "2026-07-14 08:00:00" 形式,前缀匹配 due_iso)
      data.items[].guid      (str, 任务 GUID)
    """
    r = _run_lark([
        "task", "+search",
        "--query", summary,
        "--due", f"{due_iso},{due_iso}",
        "--format", "json",
    ])
    if not r.get("ok"):
        return None
    items = (r.get("data") or {}).get("items") or []
    for item in items:
        item_summary = item.get("summary", "")
        item_due_at = item.get("due_at", "")
        if item_summary == summary and item_due_at.startswith(due_iso):
            return item.get("guid")
    return None


@_traceback_guard
def add_wish_sync(memo_id: int, content: str, category: str = "心愿",
                  tasklist_guid: Optional[str] = None,
                  due_iso: Optional[str] = None) -> dict:
    """新建飞书 task,返回 {ok, task_guid, error, existed}

    B4 修复:函数体异常由 _traceback_guard 兜底,error 带完整 traceback。

    第一性原则：
    - lark-cli auth 身份 = assignee 真值源,自动检测（不读 env）
    - 飞书 task 可不指定 tasklist（tasklists 是可选字段），会进飞书"我的任务"主页
    - tasklist_guid 由调用方显式传入（CLI 参数），不读环境变量"预配置"
    - 零配置即可使用飞书联动（不传 tasklist_guid → 进飞书主页）
    - add 心愿接口的第一责任 = 本地 note + 飞书 task 一次性建好(2026-07-13)
      due 与 title 同属核心字段,add 时直接透传给飞书 task,无需 set-due 补救

    2026-07-14 增:飞书查重(类似作息管家 diff_and_sync 的第二步)
      add 前先查飞书 task 列表,如果同 summary + due 的 task 已存在,直接复用其 guid。
      防止"本地无、飞书有"时新建重复 task(2026-07-14 实测 7/14 重复 4 条的修复)。
      返回的 dict 多一个 existed: bool 字段(存在则 True,新建则 False)。
      - existed=True 时 task_guid 是复用的,不会建新 task
      - 调用方(memo_cli.add_note)应把 task_guid 写回 notes.feishu_task_guid

    行为：
      1. 自动从 lark-cli auth 读 user open_id（缓存）
      2. 接受 tasklist_guid 参数（可选，默认 None）
      3. 接受 due_iso 参数（可选，YYYY-MM-DD；与 title 同属"创建时即带"的核心字段）
      4. 调 lark-cli `task +create --summary <title> --description <desc> --assignee <open_id> [--tasklist-id <guid>] [--due <date>]`
      5. 返回 task_guid（用于写入 notes.feishu_task_guid）

    参数：
      memo_id: memo note id（用于编码到 description 反查）
      content: 飞书 task 标题
      category: memo 分类（保留扩展性，目前不影响 tasklist 选择）
      tasklist_guid: 飞书 tasklist GUID（可选）。None → task 进飞书"我的任务"主页
      due_iso: 期望完成日期 YYYY-MM-DD（2026-07-13 增）。None/空 → 不传 --due,行为不变(向后兼容)

    返回：
      {"ok": bool, "task_guid": str | None, "error": str | None, "existed": bool}
    """
    # 2026-07-14 增:飞书查重(防重复,类似 diff_and_sync 第二步)
    if due_iso:
        existing_guid = _search_feishu_task_by_due_and_summary(due_iso, content)
        if existing_guid:
            return {"ok": True, "task_guid": existing_guid, "error": None, "existed": True}

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
    # 2026-07-13 增:add 时直接带 due(与 title 同为核心字段,1 次 API 调用原子写入)
    # YYYY-MM-DD 本身就是 ISO 8601 date-only 形式,lark-cli --due 直接接受
    if due_iso:
        args += ["--due", due_iso]
    # 只有传了 tasklist_guid 才加（飞书会建无 tasklist 的 task 在"我的任务"主页）
    if tasklist_guid:
        args += ["--tasklist-id", tasklist_guid]
    r = _run_lark(args)

    if r.get("ok"):
        task_data = r.get("data") or {}
        task_guid = task_data.get("task", {}).get("guid") or task_data.get("guid")
        return {"ok": True, "task_guid": task_guid, "error": None, "existed": False}
    else:
        return {"ok": False, "task_guid": None, "error": r.get("error") or r.get("_raw", "unknown"), "existed": False}


@_traceback_guard
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


@_traceback_guard
def complete_wish_sync(task_guid: str) -> dict:
    """标飞书 task 完成

    返回：{"ok": bool, "error": str | None}
    """
    r = _run_lark(["task", "+complete", "--task-id", task_guid])
    return {"ok": r.get("ok", False), "error": r.get("error") if not r.get("ok") else None}


@_traceback_guard
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


@_traceback_guard
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
        "SELECT id, content, due FROM notes WHERE category = '心愿' AND feishu_task_guid IS NULL ORDER BY id"
    ).fetchall()
    if not rows:
        return 0

    n_synced = 0
    for r in rows:
        memo_id, content, due = r["id"], r["content"], r["due"]
        # B1 子问题修复(#46):补建时透传 due —— 本地排期日期是 SoT,补建的飞书 task 应带上
        rr = add_wish_sync(memo_id, content, "心愿", due_iso=due)
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


# ==================== 权限编排(#46 · 常驻 sync check 能力) ====================

def _check_scope_via_cli(scope: str) -> bool:
    """lark-cli auth check --scope <s> → exit 0 = 已授权, 1 = 缺失。"""
    cli = get_lark_cli_path()
    if not cli:
        return False
    try:
        proc = subprocess.run(
            [cli, "auth", "check", "--scope", scope],
            capture_output=True, timeout=10,
        )
        return proc.returncode == 0
    except Exception:
        return False


def get_granted_scopes() -> list:
    """读取已授权 scope 清单(差集检查用)。

    优先 `auth status --json` 的 identities.user.scope(一次调用拿全量);
    该字段输出结构未实证(#195 HITL 点 2),解析失败时**退化**为逐项 `auth check --scope`。
    返回 [] 表示无法读取(未登录 / CLI 不可用 / 结构未知)。
    """
    cli = get_lark_cli_path()
    if not cli:
        return []
    try:
        kwargs = {}
        if sys.platform == "win32" and str(cli).lower().endswith(".cmd"):
            kwargs["cwd"] = os.path.dirname(str(cli))
        proc = subprocess.run(
            [cli, "auth", "status", "--json"],
            capture_output=True, timeout=10, encoding="utf-8", errors="replace",
            **kwargs,
        )
        raw = proc.stdout
        if raw.startswith("\ufeff"):
            raw = raw[3:]
        d = json.loads(raw)
        scopes = (d.get("identities") or {}).get("user", {}).get("scope")
        if isinstance(scopes, list) and all(isinstance(s, str) for s in scopes):
            return list(scopes)
    except Exception:
        pass
    # 退化:逐项 auth check(结构不可用时仍能给出差集)
    return [s for s in REQUIRED_SCOPES if _check_scope_via_cli(s)]


def get_app_scopes() -> list:
    """读取应用可用 scope 清单(`auth scopes`)。

    **提示层,非硬门禁**(D6 定案):能发现「应用没申请」,但发现不了「申请了没审核/没发布」;
    真正的硬门禁是 sentinel 实测。解析失败返回 [] 表示无法读取。
    """
    cli = get_lark_cli_path()
    if not cli:
        return []
    try:
        kwargs = {}
        if sys.platform == "win32" and str(cli).lower().endswith(".cmd"):
            kwargs["cwd"] = os.path.dirname(str(cli))
        proc = subprocess.run(
            [cli, "auth", "scopes"],
            capture_output=True, timeout=10, encoding="utf-8", errors="replace",
            **kwargs,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("\ufeff"):
            raw = raw[3:]
        d = json.loads(raw)
        # 输出结构未实证:兼容 list / data.items[].scope / data.scopes 等形态
        if isinstance(d, list):
            return [s for s in d if isinstance(s, str)]
        if isinstance(d, dict):
            for key in ("scopes", "items", "data"):
                v = d.get(key)
                if isinstance(v, list):
                    return [s for s in v if isinstance(s, str)]
                if isinstance(v, dict) and isinstance(v.get("scopes"), list):
                    return [s for s in v["scopes"] if isinstance(s, str)]
        return []
    except Exception:
        return []


def check_permissions() -> dict:
    """计算 required/granted/missing + app_scopes 提示(差集检查,不跑 sentinel)。

    返回结构:
      required / granted / missing / app_scopes{readable, missing_in_app} / note
    """
    granted = get_granted_scopes()
    missing = [s for s in REQUIRED_SCOPES if s not in granted]
    app_scopes = get_app_scopes()
    return {
        "required": list(REQUIRED_SCOPES),
        "granted": granted,
        "missing": missing,
        "app_scopes": {
            "readable": bool(app_scopes),
            "missing_in_app": [s for s in REQUIRED_SCOPES if s not in app_scopes] if app_scopes else None,
        },
        "note": (
            "写权限属飞书开放平台「需审核权限」:若 missing 授权后仍存在,请先到开发者后台"
            "确认应用已申请对应 scope 并提交审核、发布版本(否则授权页不会出现这些选项)。"
        ) if missing else None,
    }


def _sentinel_task(prefix: str) -> list:
    """task 域 sentinel:create → update → complete(真打一遍)。

    必清协议:task 无 +delete shortcut,以 complete 为终态(完成即关闭,不留待办)。
    """
    results = []
    ts = time.strftime("%H%M%S")
    summary = f"{prefix} 任务权限验证 {ts}"
    user_open_id = _get_user_open_id()
    r = _run_lark(["task", "+create", "--summary", summary, "--assignee", user_open_id])
    data = r.get("data") or {}
    guid = data.get("task", {}).get("guid") or data.get("guid")
    results.append({
        "name": "task_create",
        "ok": bool(r.get("ok") and guid),
        "error": r.get("error") if not r.get("ok") else None,
    })
    if not guid:
        return results  # 创建失败短路,后续步骤无对象可测

    r = _run_lark(["task", "+update", "--task-id", guid, "--summary", summary + "(已更新)"])
    results.append({
        "name": "task_update",
        "ok": r.get("ok", False),
        "error": r.get("error") if not r.get("ok") else None,
    })

    r = _run_lark(["task", "+complete", "--task-id", guid])
    results.append({
        "name": "task_complete",
        "ok": r.get("ok", False),
        "error": r.get("error") if not r.get("ok") else None,
        "note": "测试任务已标记完成(终态,无待办残留);如想彻底移除可到飞书删除",
    })
    return results


def _sentinel_calendar(prefix: str) -> list:
    """calendar 域 sentinel:create → update → delete(真打一遍)。

    必清协议:日程必须删除(会出现在用户日历);删除失败 → note 明示资源位置。
    """
    results = []
    ts = time.strftime("%H%M%S")
    from datetime import datetime, timedelta
    start = datetime.now() + timedelta(days=1)
    start = start.replace(hour=12, minute=0, second=0, microsecond=0)
    start_iso = start.strftime("%Y-%m-%dT%H:%M+08:00")
    end_iso = (start + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M+08:00")
    summary = f"{prefix} 日程权限验证 {ts}"

    r = _run_lark(["calendar", "+create", "--summary", summary, "--start", start_iso, "--end", end_iso])
    data = r.get("data") or {}
    event_id = data.get("event", {}).get("event_id") or data.get("event_id")
    results.append({
        "name": "calendar_create",
        "ok": bool(r.get("ok") and event_id),
        "error": r.get("error") if not r.get("ok") else None,
    })
    if not event_id:
        return results  # 创建失败短路

    r = _run_lark(["calendar", "+update", "--event-id", event_id, "--summary", summary + "(已更新)"])
    results.append({
        "name": "calendar_update",
        "ok": r.get("ok", False),
        "error": r.get("error") if not r.get("ok") else None,
    })

    r = _run_lark(["calendar", "events", "delete", "--calendar-id", "primary", "--event-id", event_id])
    ok = r.get("ok", False)
    results.append({
        "name": "calendar_delete",
        "ok": ok,
        "error": r.get("error") if not ok else None,
        "note": None if ok else f"删除失败!测试日程仍存在于飞书日历,请手动删除(标题: {summary})",
    })
    return results


def run_sentinel_write_test() -> list:
    """真打一遍 6 项写操作(task 3 + calendar 3),带强制前缀。

    用户会看到短暂出现的测试任务/日程 —— 文案告知「这是自动验证」。
    """
    prefix = SENTINEL_PREFIX
    return _sentinel_task(prefix) + _sentinel_calendar(prefix)


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
        # 权限编排(#46):check 是常驻诊断入口。先重置 open_id 缓存(B3),
        # 强制重探测 CLI 路径,再跑差集检查 + sentinel 实测。
        reset_user_open_id_cache()
        ok = is_feishu_available(force_refresh=True)
        auth = bool(_get_user_open_id())
        out = {"available": ok, "cli_path": get_lark_cli_path(), "auth": auth}
        if ok and auth:
            perms = check_permissions()
            if perms["missing"]:
                # 差集未通过 → 先授权,不跑 sentinel(没权限白跑报错)
                perms["status"] = "missing_scopes"
                perms["sentinel_write_test"] = {"skipped": True,
                                                "reason": "存在缺失权限,先完成授权再实测"}
                perms["verdict"] = "飞书权限未实测:先补齐缺失权限"
            else:
                # 差集通过 → 真打一遍 6 项写操作(sentinel 是唯一硬门禁)
                sent = run_sentinel_write_test()
                perms["sentinel_write_test"] = sent
                all_ok = all(it.get("ok") for it in sent)
                perms["status"] = "ok" if all_ok else "sentinel_failed"
                perms["verdict"] = "飞书权限已实测" if all_ok else "飞书权限实测未通过"
            out["permissions"] = perms
        elif not ok:
            out["permissions"] = {
                "status": "skipped", "skipped_reason": "cli_not_available",
                "required": list(REQUIRED_SCOPES), "granted": [], "missing": [],
            }
        else:
            out["permissions"] = {
                "status": "skipped", "skipped_reason": "not_logged_in",
                "required": list(REQUIRED_SCOPES), "granted": [], "missing": [],
            }
        print(json.dumps(out, ensure_ascii=False, indent=2))
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