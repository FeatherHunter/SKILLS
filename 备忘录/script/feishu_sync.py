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

# 飞书 tasklist 映射（category → tasklist_guid）
# 可被环境变量 MEMO_FEISHU_TASKLISTS 覆盖（JSON 字符串）
DEFAULT_TASKLISTS = {
    "心愿": "9f05b59e-9c73-4669-9319-6e5981091f01",  # 💾 心愿-数据（临时通用 tasklist）
}
# 注：当前默认所有心愿进同一个 tasklist。后续可扩展按 sub_category 细分。

USER_OPEN_ID = "ou_cd84288d35925aa490f67332327972dd"  # 用户 open_id


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


def _get_tasklist_for_category(category: str) -> Optional[str]:
    """根据 category 查 tasklist_guid"""
    tasklists = DEFAULT_TASKLISTS
    custom = os.environ.get("MEMO_FEISHU_TASKLISTS")
    if custom:
        try:
            tasklists = json.loads(custom)
        except json.JSONDecodeError:
            pass
    return tasklists.get(category)


# ==================== 同步操作 ====================

def add_wish_sync(memo_id: int, content: str, category: str = "心愿") -> dict:
    """新建飞书 task，返回 {ok, task_guid, error}

    行为：
      1. 查 category 对应的 tasklist_guid
      2. 调 lark-cli `tasks create --data {summary, description, tasklists, due, members, extra}`
      3. 返回 task_guid（用于写入 notes.feishu_task_guid）

    返回：
      {"ok": bool, "task_guid": str | None, "error": str | None}
    """
    tasklist_guid = _get_tasklist_for_category(category)
    if not tasklist_guid:
        return {"ok": False, "task_guid": None, "error": f"no tasklist mapping for category={category}"}

    # 构造 task payload
    # 注：飞书 task create 不支持 extra 字段（API 拒绝）。
    #     memo_id 编码进 description（"原备忘 #N"），靠正则反查。
    payload = {
        "summary": content[:200],  # 飞书 title 最长 3000 字符
        "description": f"原备忘 #{memo_id}",
        "tasklists": [{"tasklist_guid": tasklist_guid}],
        "members": [
            {"id": USER_OPEN_ID, "type": "user", "role": "assignee"},
            {"id": USER_OPEN_ID, "type": "user", "role": "follower"},
        ],
    }
    r = _run_lark(["task", "tasks", "create", "--data", json.dumps(payload, ensure_ascii=False)])

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


def sync_from_feishu(db_path: str = None) -> dict:
    """反向同步：飞书已 done → 触发本地 complete-wish

    流程：
      1. 拉飞书所有 done task
      2. 对每个 task 取 extra.memo_id
      3. 反查本地 notes.feishu_task_guid
      4. 如果本地心愿还在 → 调用 memo_cli.py complete-wish memo_id
      5. 报告处理结果

    返回：
      {
        "scanned": int,        # 扫到的 done task 数
        "synced": int,         # 触发的本地同步数
        "skipped_no_memo_id": int,
        "skipped_already_done": int,
        "errors": [str],
      }
    """
    if not is_feishu_available():
        return {"scanned": 0, "synced": 0, "errors": ["feishu CLI not available"]}

    done_tasks = _list_all_done_tasks()

    if db_path is None:
        # 默认 DB 路径
        db_path = os.path.join(os.environ.get("SKILLS_DB_PATH", r"D:\2Study\StudyNotes\.db"), "memo.db")

    result = {
        "scanned": len(done_tasks),
        "synced": 0,
        "skipped_no_memo_id": 0,
        "skipped_already_done": 0,
        "skipped_no_local_note": 0,
        "errors": [],
    }

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

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
            # 不是心愿分类（如已变成打卡）→ 已处理过
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

    p_complete = sub.add_parser("complete", help="标飞书 task 完成")
    p_complete.add_argument("--task-guid", required=True)

    p_update = sub.add_parser("update", help="更新飞书 task 标题")
    p_update.add_argument("--task-guid", required=True)
    p_update.add_argument("--content", required=True)

    p_sync = sub.add_parser("sync-from-feishu", help="反向同步（飞书 done → 本地 complete-wish）")

    args = parser.parse_args()

    if args.command == "check":
        ok = is_feishu_available()
        print(json.dumps({"available": ok, "cli_path": get_lark_cli_path()}, ensure_ascii=False, indent=2))
    elif args.command == "add":
        result = add_wish_sync(args.memo_id, args.content, args.category)
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()