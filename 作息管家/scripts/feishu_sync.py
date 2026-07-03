# -*- coding: utf-8 -*-
"""
feishu_sync.py — 飞书日历同步模块（独立可移植）

模块职责：
1. 探测本机 lark-cli 能力（安装 / 认证 / 日历写入）—— 三档返回
2. 封装飞书日历 CRUD 业务函数（create / update / delete / search）
3. 提供 diff_and_sync 业务编排（DB 事件 vs 飞书事件 diff 同步）

设计原则：
- 探测无副作用（只读）
- 探测结果进程内缓存（TTL=300s）
- 缺失依赖不报错，调用方按探测结果决定后续流程
- 本模块不直连作息管家数据库（数据由 CLI / schedule_db.py 注入）

子命令格式（来自 lark-cli 1.0.59 实测）：
- 探测  : lark-cli --version
- 认证  : lark-cli auth status
- 创建  : lark-cli calendar +create --start ISO --end ISO --summary T [--description D]
- 更新  : lark-cli calendar +update --event-id ID --start ISO --end ISO [--summary T] [--description D]
- 查询  : lark-cli calendar +search-event --start YYYY-MM-DD --end YYYY-MM-DD
- 议程  : lark-cli calendar +agenda
- 删除  : lark-cli calendar events delete --calendar-id CID --event-id EID
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


# ============================================================
# 常量
# ============================================================

LARK_CLI_CANDIDATES = [
    # Windows: npm global（%APPDATA% 自动展开当前用户路径，跨用户通用）
    r"%APPDATA%\npm\lark-cli.cmd",
    r"%APPDATA%\npm\lark-cli",
    # Windows: scoop 全局安装
    r"%LOCALAPPDATA%\Programs\lark-cli\lark-cli.exe",
    r"%LOCALAPPDATA%\Programs\lark-cli\lark-cli.cmd",
    # macOS: Homebrew（Apple Silicon + Intel）
    "/opt/homebrew/bin/lark-cli",
    # Linux: 系统包管理器
    "/usr/local/bin/lark-cli",
    # Linux/macOS: 用户级 npm（避免 sudo 装全局；
    #              Windows 上 $HOME 也会展开为 C:\Users\<user>，但 Windows 用户通常用 %APPDATA%\npm，
    #              所以这两条在 Windows 上一般找不到，skip 后 fallthrough 即可）
    "$HOME/.npm-global/bin/lark-cli",
    "$HOME/.local/bin/lark-cli",
    # WSL: 走 WSL 自身 PATH 中的 lark-cli（建议 WSL 自行 npm i -g lark-cli，
    #      不跨 Windows 用户拉，避免多用户路径冲突）
]

LARK_CLI_TIMEOUT_SHORT = 15   # --version / auth status
LARK_CLI_TIMEOUT_NORMAL = 30  # +agenda / +search-event
LARK_CLI_TIMEOUT_LONG = 60    # +create / +update / events delete

# 探测缓存 TTL（秒）
PROBE_TTL_SECONDS = 300


# ============================================================
# 数据结构
# ============================================================

@dataclass
class FeishuStatus:
    """飞书能力探测结果（三档 + 详情）"""
    cli_installed: bool = False          # lark-cli 是否在 PATH 或常见位置
    cli_path: Optional[str] = None       # 找到的 lark-cli 全路径
    cli_version: Optional[str] = None    # 如 "1.0.59"
    authenticated: bool = False          # 是否已 auth（user/bot 至少一个 ready）
    user_name: Optional[str] = None      # 用户名（如 "用户418832"）
    user_open_id: Optional[str] = None   # 用户 open_id
    calendar_writable: bool = False      # 日历可写（探测时尝试 +agenda 至少能拉取到非空列表，或显式 dry-run +create 不报"无权限"）
    last_error: Optional[str] = None     # 任何探测失败原因

    @property
    def fully_available(self) -> bool:
        """三档判定：cli + auth + writable 全可用"""
        return self.cli_installed and self.authenticated and self.calendar_writable

    @property
    def tier(self) -> str:
        """返回 'full' / 'partial' / 'missing' / 'unknown'"""
        if not self.cli_installed:
            return "missing"
        if not self.authenticated or not self.calendar_writable:
            return "partial"
        if self.fully_available:
            return "full"
        return "unknown"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class FeishuEvent:
    """飞书日历事件（业务层抽象，不暴露 lark-cli 字段）"""
    event_id: str                        # 飞书事件 ID（如 "4e6e44b0-..._0"）
    start: str                           # ISO 8601（如 "2026-06-29T20:00:00+08:00"）
    end: str                             # ISO 8601
    summary: str                         # 标题
    description: str = ""                # 描述（飞书 description 对应 notes）
    # 本模块不写数据库，DB 关联字段（feishu_event_id 等）由 schedule_db.py 维护


# ============================================================
# 探测：lark-cli 路径查找
# ============================================================

def find_lark_cli() -> Optional[str]:
    """在 PATH 和常见安装路径中查找 lark-cli。返回绝对路径或 None。"""
    # 1) PATH
    import shutil
    found = shutil.which("lark-cli")
    if found:
        return found

    # 2) 候选位置（跨平台）
    for cand in LARK_CLI_CANDIDATES:
        expanded = os.path.expandvars(os.path.expanduser(cand))
        if os.path.isfile(expanded):
            return expanded

    return None


# ============================================================
# 探测：lark-cli 子进程调用
# ============================================================

def _run_lark(args: list[str], timeout: int) -> tuple[int, str, str]:
    """
    调用 lark-cli 子进程。
    返回 (exit_code, stdout, stderr)。
    stdout/stderr 已 strip，强制使用 utf-8 / ignore 错误处理。
    """
    cli_path = find_lark_cli()
    if not cli_path:
        raise FileNotFoundError("未找到 lark-cli，请先安装（npm i -g lark-cli）")

    try:
        proc = subprocess.run(
            [cli_path] + args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,  # 避免 Windows shell 引号转义
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"lark-cli 调用超时（{timeout}s）：{' '.join(args)}")
    except FileNotFoundError:
        raise FileNotFoundError(f"lark-cli 不可执行：{cli_path}")


def _run_lark_json(args: list[str], timeout: int) -> dict:
    """调用 lark-cli 并解析 JSON 输出。lark 错误时抛 LarkAPIError。"""
    exit_code, stdout, stderr = _run_lark(args, timeout)
    if not stdout:
        raise LarkAPIError(
            f"lark-cli 无输出（exit={exit_code}）\nargs: {' '.join(args)}\nstderr: {stderr}"
        )
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        raise LarkAPIError(
            f"lark-cli 输出非 JSON（exit={exit_code}）\nargs: {' '.join(args)}\nstdout: {stdout[:500]}"
        ) from e
    # lark-cli 业务错误格式：{"ok": false, "error": {...}}
    if isinstance(data, dict) and data.get("ok") is False:
        err = data.get("error", {})
        raise LarkAPIError(
            f"lark-cli 业务错误：{err.get('message', '?')}\nargs: {' '.join(args)}"
        )
    return data


class LarkAPIError(RuntimeError):
    """lark-cli 业务/协议错误"""
    pass


# ============================================================
# 探测：is_feishu_available（带缓存）
# ============================================================

_STATUS_CACHE: dict[str, Any] = {"status": None, "fetched_at": None}


def _probe_calendar_writable(cli_path: str, user_name: Optional[str], user_open_id: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    探测日历写入权限。策略：
    1) +agenda 拉今天的议程 —— 若 OK，至少能读（很多账号读=写权限同时有）
    2) 进一步用 events 子命令做 read-only 试探（避免误创建真事件）
    注意：写权限的真实探测需要发起一次 +create dry-run，但 dry-run 实际不验证权限。
    这里采用保守策略：能读 +user 身份已 ready → 默认可写（多数 feishu 个人日历 user 都能写）
    """
    try:
        data = _run_lark_json(["calendar", "+agenda"], LARK_CLI_TIMEOUT_NORMAL)
        # 能读到议程（即使空数组）→ 至少有读权限
        if "data" in data or data.get("ok") is True:
            return True, None
        return False, "+agenda 返回结构异常"
    except (LarkAPIError, TimeoutError, FileNotFoundError) as e:
        return False, str(e)


def is_feishu_available(force_refresh: bool = False) -> FeishuStatus:
    """
    探测本机飞书能力（带 300s 进程内缓存）。

    返回 FeishuStatus，调用方根据 .tier 字段决策：
      - "full"    → 全可用
      - "partial" → 部分可用（已装但未授权 / 日历无权限）
      - "missing" → 未安装
    """
    now = datetime.now()
    cached = _STATUS_CACHE["status"]
    fetched_at = _STATUS_CACHE["fetched_at"]
    if not force_refresh and cached and fetched_at:
        if (now - fetched_at).total_seconds() < PROBE_TTL_SECONDS:
            return cached

    status = FeishuStatus()
    cli_path = find_lark_cli()
    if not cli_path:
        status.last_error = "未找到 lark-cli 命令"
        _STATUS_CACHE["status"] = status
        _STATUS_CACHE["fetched_at"] = now
        return status

    status.cli_installed = True
    status.cli_path = cli_path

    # --version
    try:
        exit_code, stdout, _ = _run_lark(["--version"], LARK_CLI_TIMEOUT_SHORT)
        m = re.match(r"lark-cli version (\S+)", stdout)
        if m:
            status.cli_version = m.group(1)
    except Exception as e:
        status.last_error = f"--version 失败：{e}"

    # auth status
    try:
        auth_data = _run_lark_json(["auth", "status"], LARK_CLI_TIMEOUT_SHORT)
        identities = auth_data.get("identities", {})
        user = identities.get("user", {})
        bot = identities.get("bot", {})
        user_ready = user.get("status") == "ready" and user.get("available") is True
        bot_ready = bot.get("status") == "ready" and bot.get("available") is True
        status.authenticated = user_ready or bot_ready
        status.user_open_id = user.get("openId")
        # user_name 不在 auth status 里，留空
    except LarkAPIError as e:
        status.last_error = f"auth status 失败：{e}"

    # calendar writable
    if status.authenticated:
        ok, err = _probe_calendar_writable(cli_path, status.user_name, status.user_open_id)
        status.calendar_writable = ok
        if not ok and err:
            status.last_error = (status.last_error + " | " if status.last_error else "") + f"日历权限：{err}"

    _STATUS_CACHE["status"] = status
    _STATUS_CACHE["fetched_at"] = now
    return status


# ============================================================
# CRUD：create
# ============================================================

def create_event(
    start: str,
    end: str,
    summary: str,
    description: str = "",
    calendar_id: str = "primary",
    dry_run: bool = False,
) -> FeishuEvent:
    """
    创建飞书日历事件。
    start/end: ISO 8601，如 "2026-06-29T20:00:00+08:00"
    summary: 事件标题
    description: 事件描述（对应作息管家的 notes）
    返回 FeishuEvent（含 event_id）
    """
    args = [
        "calendar", "+create",
        "--calendar-id", calendar_id,
        "--start", start,
        "--end", end,
        "--summary", summary,
    ]
    if description:
        args.extend(["--description", description])
    if dry_run:
        args.append("--dry-run")

    data = _run_lark_json(args, LARK_CLI_TIMEOUT_LONG)
    event_data = (data.get("data") or {})
    event_id = event_data.get("event_id")
    if not event_id:
        # dry-run 模式下 lark-cli 返回请求预览，没有 event_id
        # 其他情况视为业务错误
        if dry_run:
            return FeishuEvent(event_id="", start=start, end=end, summary=summary, description=description)
        raise LarkAPIError(f"创建事件成功但无 event_id：{data}")

    return FeishuEvent(
        event_id=event_id,
        start=event_data.get("start_time", {}).get("datetime", start),
        end=event_data.get("end_time", {}).get("datetime", end),
        summary=event_data.get("summary", summary),
        description=event_data.get("description", description),
    )


# ============================================================
# CRUD：update
# ============================================================

def update_event(
    event_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    calendar_id: str = "primary",
) -> FeishuEvent:
    """
    更新飞书日历事件。
    start/end 必须同时传（或同时不传）—— lark-cli 的 --start/--end 互锁。
    summary / description 可单独传。
    """
    args = [
        "calendar", "+update",
        "--calendar-id", calendar_id,
        "--event-id", event_id,
    ]
    if start and end:
        args.extend(["--start", start, "--end", end])
    if summary is not None:
        args.extend(["--summary", summary])
    if description is not None:
        args.extend(["--description", description])

    data = _run_lark_json(args, LARK_CLI_TIMEOUT_LONG)
    event_data = (data.get("data") or {})
    return FeishuEvent(
        event_id=event_id,
        start=event_data.get("start_time", {}).get("datetime", start or ""),
        end=event_data.get("end_time", {}).get("datetime", end or ""),
        summary=event_data.get("summary", summary or ""),
        description=event_data.get("description", description or ""),
    )


# ============================================================
# CRUD：delete（探测时未确认 events 子命令路径，下面走探测得到的真实接口）
# ============================================================

def delete_event(event_id: str, calendar_id: str = "primary") -> bool:
    """
    删除飞书日历事件。
    路径探测结果：lark-cli calendar events delete --calendar-id CID --event-id EID
    （实测若不存在，下面会抛 LarkAPIError，调用方按"未实现"处理）
    """
    args = [
        "calendar", "events", "delete",
        "--calendar-id", calendar_id,
        "--event-id", event_id,
    ]
    data = _run_lark_json(args, LARK_CLI_TIMEOUT_LONG)
    # 删除成功的 data 通常为 {}，ok:true 即视为成功
    return data.get("ok") is True


# ============================================================
# CRUD：search
# ============================================================

def search_events(
    start: str,
    end: str,
    query: Optional[str] = None,
    calendar_id: str = "primary",
) -> list[FeishuEvent]:
    """
    按时间范围搜索飞书事件。返回列表。
    start/end 可接受 ISO 8601 或 YYYY-MM-DD（lark-cli 都支持）。

    **实现说明**:走 +agenda 命令而非 +search-event。
    原因:`+search-event` 返回的 event 不包含 `description` 字段,
    导致 diff_and_sync 误判为"飞书 description 为空"→ 全量 update。
    +agenda 返回完整 description(以及 event_id/start/end/summary)。

    query 过滤:由于 +agenda 不支持 --query,在 Python 端用 substring
    过滤 summary 或 description。
    """
    args = [
        "calendar", "+agenda",
        "--calendar-id", calendar_id,
        "--start", start,
        "--end", end,
    ]

    data = _run_lark_json(args, LARK_CLI_TIMEOUT_NORMAL)
    payload = data.get("data") or []
    if not isinstance(payload, list):
        return []

    events = []
    for it in payload:
        summary = it.get("summary", "")
        description = it.get("description", "")
        # query 在 summary 或 description 里命中即保留(用 substring)
        if query and query not in summary and query not in description:
            continue
        events.append(FeishuEvent(
            event_id=it.get("event_id", ""),
            start=(it.get("start_time") or {}).get("datetime", ""),
            end=(it.get("end_time") or {}).get("datetime", ""),
            summary=summary,
            description=description,
        ))
    return events


# ============================================================
# 业务编排：diff_and_sync
# ============================================================

@dataclass
class PlanEvent:
    """
    一条计划事件（用于 DB 与飞书 diff 的中性结构）。
    不持有 DB/飞书特定字段，由 schedule_db.py 在 CRUD 时构造。
    """
    time_start: str      # "HH:MM"（DB 存储形式）
    time_end: str        # "HH:MM"
    title: str
    notes: str = ""
    category: str = ""
    feishu_event_id: Optional[str] = None  # 已有飞书 event_id 用于 update/delete


def _to_iso(date: str, hhmm: str) -> str:
    """DB 时间 HH:MM + 日期 YYYY-MM-DD → 飞书 ISO 8601（带 +08:00 时区）。
    24:00 特殊处理：飞书日历不接受 24:00:00，所以跨到次日 00:00。
    """
    if hhmm == "24:00":
        from datetime import datetime, timedelta
        next_day = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        return f"{next_day}T00:00:00+08:00"
    return f"{date}T{hhmm}:00+08:00"


def _from_iso(iso: str) -> tuple[str, str]:
    """飞书 ISO 8601 → (日期 YYYY-MM-DD, 时间 HH:MM)，用于反查 key 对齐。
    飞书 ISO 可能跨日返回（如 23:00-24:00 的事件 end 是次日 00:00）。"""
    import re
    from datetime import datetime, timedelta
    m = re.match(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}):\d{2}", iso)
    if not m:
        return ("", "00:00")
    d_str = m.group(1)
    t_str = m.group(2)
    return (d_str, t_str)


def diff_and_sync(
    date: str,
    db_events: list[PlanEvent],
    dry_run: bool = False,
    ask_callback=None,
) -> dict:
    """
    对比"DB 中该日全部活跃事件"vs"飞书当日事件"，分别 create/update/delete。

    参 ask_callback: 可选回调函数 `(question: str) -> bool`，
                      用于在每个写动作前询问用户（详情见 B/C 决策）。
                      None 表示直接执行（用户已预授权）。

    返回 dict：
      {
        "created": [event_ids...],
        "updated": [event_ids...],
        "deleted": [event_ids...],
        "skipped": [event_ids...],   # ask_callback 拒绝的
        "errors": [(event_id, error), ...],
      }
    """
    try:
        return _diff_and_sync_impl(date, db_events, dry_run, ask_callback)
    except Exception:
        import traceback
        traceback.print_exc()
        raise


def _diff_and_sync_impl(
    date: str,
    db_events: list[PlanEvent],
    dry_run: bool,
    ask_callback,
) -> dict:
    # 拉飞书当日事件
    feishu_events = search_events(
        start=date, end=date,
        query="作息管家自动同步",
    )

    # 构造 diff map
    # key = (time_start, time_end) —— 因为同一时段只对应一件事
    db_map = {(e.time_start, e.time_end): e for e in db_events}

    # 保险丝:按 (start, end) 分组飞书事件,记录每个时间槽对应的事件列表。
    # 如果某个时间槽有 >1 个飞书事件(历史重复 create 留下),记录到 duplicate_groups。
    # 正常 diff 仍用每组的"代表"(第一条),但返回结果里会附带冗余信息,
    # 方便上层(比如 resync 函数)打印警告,避免下次重复 create 累积。
    from collections import OrderedDict
    feishu_groups: "OrderedDict[tuple, list]" = OrderedDict()
    for fe in feishu_events:
        key = (_iso_to_hhmm(fe.start, date), _iso_to_hhmm(fe.end, date))
        feishu_groups.setdefault(key, []).append(fe)

    duplicate_groups = []
    for key, events in feishu_groups.items():
        if len(events) > 1:
            duplicate_groups.append({
                "key": key,
                "count": len(events),
                "event_ids": [e.event_id for e in events],
                "summaries": list({e.summary for e in events}),  # 去重,通常都一致
            })

    # diff 用的 feishu_map:每组取第一条作为代表(覆盖 dict 时不会重复报错)
    feishu_map = {key: events[0] for key, events in feishu_groups.items()}

    created, updated, deleted, skipped, errors = [], [], [], [], []

    # create / update
    for key, db_e in db_map.items():
        feishu_e = feishu_map.get(key)
        if feishu_e is None:
            # 需要新建
            if _should_ask(ask_callback, "create", db_e):
                try:
                    new_e = create_event(
                        start=_to_iso(date, db_e.time_start),
                        end=_to_iso(date, db_e.time_end),
                        summary=db_e.title,
                        description=_compose_description(db_e),
                        dry_run=dry_run,
                    )
                    if new_e.event_id:
                        created.append(new_e.event_id)
                    elif dry_run:
                        created.append("(dry-run)")
                except Exception as ex:
                    errors.append((key, str(ex)))
            else:
                skipped.append(db_e.time_start)
        else:
            # 已有飞书事件，content-based diff（简单起见：title 或 description 变了就 update）
            title_changed = feishu_e.summary != db_e.title
            desc_changed = feishu_e.description != _compose_description(db_e)
            if title_changed or desc_changed:
                if _should_ask(ask_callback, "update", db_e, feishu_e):
                    try:
                        update_event(
                            event_id=feishu_e.event_id,
                            summary=db_e.title,
                            description=_compose_description(db_e),
                        )
                        updated.append(feishu_e.event_id)
                    except Exception as ex:
                        errors.append((feishu_e.event_id, str(ex)))
                else:
                    skipped.append(feishu_e.event_id)

    # delete：飞书有但 DB 没有的
    for key, feishu_e in feishu_map.items():
        if key not in db_map:
            if _should_ask(ask_callback, "delete", feishu_e=feishu_e):
                try:
                    delete_event(event_id=feishu_e.event_id)
                    deleted.append(feishu_e.event_id)
                except Exception as ex:
                    errors.append((feishu_e.event_id, str(ex)))
            else:
                skipped.append(feishu_e.event_id)

    return {
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "skipped": skipped,
        "errors": errors,
        "duplicate_groups": duplicate_groups,  # 保险丝字段
    }


# ============================================================
# 业务编排：diff_and_sync — 旧实现已搬到 _diff_and_sync_impl，下面是占位
# ============================================================
    # 拉飞书当日事件
    feishu_events = search_events(
        start=date, end=date,
        query="作息管家自动同步",
    )

    # 构造 diff map
    # key = (time_start, time_end) —— 因为同一时段只对应一件事
    db_map = {(e.time_start, e.time_end): e for e in db_events}
    feishu_map = {(_iso_to_hhmm(e.start, date), _iso_to_hhmm(e.end, date)): e for e in feishu_events}

    created, updated, deleted, skipped, errors = [], [], [], [], []

    # create / update
    for key, db_e in db_map.items():
        feishu_e = feishu_map.get(key)
        if feishu_e is None:
            # 需要新建
            if _should_ask(ask_callback, "create", db_e):
                try:
                    new_e = create_event(
                        start=_to_iso(date, db_e.time_start),
                        end=_to_iso(date, db_e.time_end),
                        summary=db_e.title,
                        description=_compose_description(db_e),
                        dry_run=dry_run,
                    )
                    if new_e.event_id:
                        created.append(new_e.event_id)
                    elif dry_run:
                        created.append("(dry-run)")
                except Exception as ex:
                    errors.append((key, str(ex)))
            else:
                skipped.append(db_e.time_start)
        else:
            # 已有飞书事件，content-based diff（简单起见：title 或 description 变了就 update）
            title_changed = feishu_e.summary != db_e.title
            desc_changed = feishu_e.description != _compose_description(db_e)
            if title_changed or desc_changed:
                if _should_ask(ask_callback, "update", db_e, feishu_e):
                    try:
                        update_event(
                            event_id=feishu_e.event_id,
                            summary=db_e.title,
                            description=_compose_description(db_e),
                        )
                        updated.append(feishu_e.event_id)
                    except Exception as ex:
                        errors.append((feishu_e.event_id, str(ex)))
                else:
                    skipped.append(feishu_e.event_id)

    # delete：飞书有但 DB 没有的
    for key, feishu_e in feishu_map.items():
        if key not in db_map:
            if _should_ask(ask_callback, "delete", feishu_e=feishu_e):
                try:
                    delete_event(event_id=feishu_e.event_id)
                    deleted.append(feishu_e.event_id)
                except Exception as ex:
                    errors.append((feishu_e.event_id, str(ex)))
            else:
                skipped.append(feishu_e.event_id)

    return {
        "created": created,
        "updated": updated,
        "deleted": deleted,
        "skipped": skipped,
        "errors": errors,
    }


def _compose_description(e: PlanEvent) -> str:
    """PlanEvent → 飞书事件 description 字符串"""
    parts = []
    if e.category:
        parts.append(f"[{e.category}]")
    if e.notes:
        parts.append(e.notes)
    parts.append("作息管家自动同步")
    return " | ".join(parts)


def _should_ask(ask_callback, action: str, db_e: Optional[PlanEvent] = None, feishu_e: Optional[FeishuEvent] = None) -> bool:
    """询问回调：默认直接执行（pass=ask_callback=None），否则问。"""
    if ask_callback is None:
        return True
    label_map = {"create": "创建", "update": "更新", "delete": "删除"}
    label = label_map.get(action, action)
    target = (db_e.title if db_e else feishu_e.summary if feishu_e else "?")
    return ask_callback(f"是否{label}飞书事件「{target}」？[Y/n]")


def _iso_to_hhmm(iso: str, date_fallback: str) -> str:
    """ISO 8601 → HH:MM（用于 diff key 对齐）。失败时返回 00:00 兜底。"""
    m = re.search(r"T(\d{2}:\d{2})", iso)
    if m:
        return m.group(1)
    return "00:00"


# ============================================================
# 自检：直接 python feishu_sync.py 时打印探测结果
# ============================================================

if __name__ == "__main__":
    print("=== 飞书能力探测 ===")
    status = is_feishu_available(force_refresh=True)
    print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2))
    print(f"\n→ 可用度分级：{status.tier}")
    print(f"→ fully_available: {status.fully_available}")
