#!/usr/bin/env python3
"""
备忘录 ↔ 飞书任务 同步模块（最简版）

第一性原则：
- 本地优先：memo DB 是 Single Source of Truth，飞书是镜像
- 降级：飞书 API 失败不阻塞本地操作，只记录 warning
- 映射源：复用 wish_feishu_map.json（demo 时期留下）

功能（V1）：
- complete_wish_sync(memo_id): 同步飞书 task 完成
  - 从 wish_feishu_map.json 查 memo_id → task_guid
  - 调用 lark-cli `task +complete --task-id <guid>`
  - 失败返回 False，不抛异常

未来扩展（不在 V1）：
- add 心愿时自动建飞书 task
- 双向同步（飞书手动操作反查 memo）
"""
import json
import os
import subprocess
from pathlib import Path


# 复用 demo 留下的映射文件
DEFAULT_MAP_PATH = r"D:\2Study\StudyNotes\.db\wish_feishu_map.json"

LARK_CLI = os.environ.get(
    "LARK_CLI_PATH",
    r"C:\Users\辰辰洋洋\AppData\Roaming\npm\lark-cli.cmd",
)


def _load_map(map_path: str = DEFAULT_MAP_PATH) -> dict:
    """读 wish_feishu_map.json，没有则返回空 dict"""
    if not os.path.exists(map_path):
        return {"tasklists": {}, "tasks": {}}
    try:
        with open(map_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"tasklists": {}, "tasks": {}}


def _save_map(data: dict, map_path: str = DEFAULT_MAP_PATH) -> None:
    """写 wish_feishu_map.json"""
    try:
        with open(map_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass  # 静默失败


def _run_lark(args: list[str], timeout: int = 30) -> dict:
    """调 lark-cli，捕获输出"""
    try:
        proc = subprocess.run(
            [LARK_CLI] + args,
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


def complete_wish_sync(memo_id: int, map_path: str = DEFAULT_MAP_PATH) -> dict:
    """同步飞书 task 完成（流式工作流的最后一步）

    行为：
      1. 从 wish_feishu_map.json 查 memo_id → task_guid
      2. 若无映射（新增心愿未同步过飞书），跳过飞书同步（本地操作不受影响）
      3. 调用 lark-cli `task +complete --task-id <guid>`
      4. 成功返回 {"synced": True, "task_guid": ...}
      5. 失败返回 {"synced": False, "error": ...}（不抛异常）

    返回：
      {
        "synced": bool,
        "task_guid": str | None,
        "reason": str,            # "ok" | "no_mapping" | "api_error"
        "error": str | None,
      }
    """
    memo_id_str = str(memo_id)
    data = _load_map(map_path)
    task_guid = data.get("tasks", {}).get(memo_id_str)

    if not task_guid:
        return {
            "synced": False,
            "task_guid": None,
            "reason": "no_mapping",
            "error": f"memo_id={memo_id} 在飞书映射表中找不到（可能未同步过飞书）",
        }

    # 调飞书 +complete
    r = _run_lark(["task", "+complete", "--task-id", task_guid])

    if r.get("ok"):
        return {
            "synced": True,
            "task_guid": task_guid,
            "reason": "ok",
            "error": None,
        }
    else:
        return {
            "synced": False,
            "task_guid": task_guid,
            "reason": "api_error",
            "error": r.get("error") or r.get("_raw", "unknown"),
        }


# CLI 入口（手动触发同步，不依赖 memo_cli.py）
def main():
    import argparse
    parser = argparse.ArgumentParser(description="备忘录 ↔ 飞书同步模块")
    sub = parser.add_subparsers(dest="command")

    p_complete = sub.add_parser("complete-wish", help="同步飞书 task 完成")
    p_complete.add_argument("memo_id", type=int, help="memo note id")

    args = parser.parse_args()

    if args.command == "complete-wish":
        result = complete_wish_sync(args.memo_id)
        # 输出 JSON 格式
        print(json.dumps(result, ensure_ascii=False, indent=2))
        # 失败用 exit code 1（区分成功 vs 失败）
        if not result["synced"] and result["reason"] == "api_error":
            exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()