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
# 所有用户/本机特定配置必须通过环境变量传入

# 用户飞书 open_id 环境变量
# 设置方法: set MEMO_FEISHU_USER_OPEN_ID=ou_xxx
ENV_USER_OPEN_ID = "MEMO_FEISHU_USER_OPEN_ID"

# memo DB 路径环境变量（与 memo_cli.py 共享）
ENV_SKILLS_DB_PATH = "SKILLS_DB_PATH"


def _get_user_open_id() -> Optional[str]:
    """取用户飞书 open_id（环境变量）"""
    return os.environ.get(ENV_USER_OPEN_ID)


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
    """新建飞书 task，返回 {ok, task_guid, error}

    第一性原则：
    - 飞书 task 可不指定 tasklist（tasklists 是可选字段），会进飞书"我的任务"主页
    - tasklist_guid 由调用方显式传入（CLI 参数），不读环境变量"预配置"
    - 零配置即可使用飞书联动（不传 tasklist_guid → 进飞书主页）

    行为：
      1. 查用户 open_id（环境变量，必须）
      2. 接受 tasklist_guid 参数（可选，默认 None）
      3. 调 lark-cli `tasks create --data {summary, description, [tasklists], members}`
      4. 返回 task_guid（用于写入 notes.feishu_task_guid）

    参数：
      memo_id: memo note id（用于编码到 description 反查）
      content: 飞书 task 标题
      category: memo 分类（保留扩展性，目前不影响 tasklist 选择）
      tasklist_guid: 飞书 tasklist GUID（可选）。None → task 进飞书"我的任务"主页

    返回：
      {"ok": bool, "task_guid": str | None, "error": str | None}
    """
    # 配置检查：user_open_id 必须有
    user_open_id = _get_user_open_id()
    if not user_open_id:
        return {"ok": False, "task_guid": None, "error": f"环境变量 {ENV_USER_OPEN_ID} 未设置"}

    # 构造 task payload
    # 注：飞书 task create 不支持 extra 字段（API 拒绝）。
    #     memo_id 编码进 description（"原备忘 #N"），靠正则反查。
    payload = {
        "summary": content[:200],  # 飞书 title 最长 3000 字符
        "description": f"原备忘 #{memo_id}",
        "members": [
            {"id": user_open_id, "type": "user", "role": "assignee"},
            {"id": user_open_id, "type": "user", "role": "follower"},
        ],
    }
    # 只有传了 tasklist_guid 才加（飞书会建无 tasklist 的 task 在"我的任务"主页）
    if tasklist_guid:
        payload["tasklists"] = [{"tasklist_guid": tasklist_guid}]
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
        # 默认 DB 路径（通过 _get_memo_db_path 自动探测，不写死任何用户路径）
        db_path = _get_memo_db_path()

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