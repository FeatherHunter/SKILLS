#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""后台长跑批处理:3 天同步的"训记"部分。

职责(只做训记,不碰作息/备忘 —— 那些 AI 路由主进程同步调):
  1. 串行 3 天,每天调 `xunji_bridge push-plan --date X`(自带 45s 限频)
  2. 最后调 `xunji_bridge backfill --days N`
  3. 全程写状态文件 `~/.mavis/xunji_bridge_sync_state.json`,供 mavis cron self 检查

为什么 run_sync 是单独模块(不进 push.py):
  - 状态文件 schema 独立演化
  - 后台跑和前台跑的关注点不同(后台要可被 mavis cron 唤醒)
  - AI 路由 Popen 这个,不阻塞对话

公开 API:
    run_sync(days=3, start_offset=0, dry_run=False) -> dict
        串行 days 天同步训记,start_offset 表示"从今天+offset 开始"(默认今天)
        dry_run=True 时只创建状态文件不实际推送

    read_state() -> dict
        公开 API:供 mavis cron self 读当前状态
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# 状态文件路径(供 mavis cron self 读取)
STATE_PATH = Path.home() / ".mavis" / "xunji_bridge_sync_state.json"

# 子进程调 xunji_bridge 需要 cwd 在 scripts/
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _read_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write_state(state: dict) -> None:
    """原子写状态文件。"""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(STATE_PATH)


def _init_state(days: int) -> dict:
    return {
        "status": "running",
        "started_at": _now_iso(),
        "finished_at": None,
        "total_days": days,
        "current_day": 0,
        "phase": None,
        "results": [],
        "error_summary": None,
    }


def _run_subprocess(args: list[str], timeout: int = 900) -> dict:
    """调 xunji_bridge 子命令,返 {rc, stdout, stderr}。

    ⚠ Windows 必须显式 encoding='utf-8' + errors='replace':
       - text=True 默认 locale(中文 Windows = GBK),子进程 stdout 含中文时 UnicodeDecodeError
       - 错误后 stdout=None → 上层 json.loads 抛 'NoneType' object is not subscriptable 假象
       - 修复后子进程失败时 stdout 永远是 str,异常清晰可读
    """
    proc = subprocess.run(
        [sys.executable, "-m", "xunji_bridge"] + args,
        cwd=str(_SCRIPTS_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",       # 2026-07-20 修:GBK 崩溃陷阱
        errors="replace",       # 防止任何残留编码异常中断流程
        timeout=timeout,
    )
    return {
        "rc": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _summarize_push_output(date_str: str, stdout: str) -> dict:
    """从 push-plan stdout JSON 提取关键数字(不存完整 stdout,避免状态文件过大)。"""
    try:
        data = json.loads(stdout)
        return {
            "date": date_str,
            "phase": "push",
            "ok": data.get("fail_count", 0) == 0,
            "session_count": data.get("session_count", 0),
            "ok_count": data.get("ok_count", 0),
            "fail_count": data.get("fail_count", 0),
        }
    except Exception as e:
        return {
            "date": date_str,
            "phase": "push",
            "ok": False,
            "error": f"解析 push-plan 输出失败:{e}",
            "stdout_first_200": stdout[:200],
        }


def _summarize_backfill_output(days: int, stdout: str) -> dict:
    """从 backfill stdout JSON 提取关键数字。"""
    try:
        data = json.loads(stdout)
        if "results" in data:
            return {
                "phase": "backfill",
                "days": days,
                "ok": all(r.get("fetch_ok") for r in data["results"]),
                "total_inserted": data.get("total_inserted", 0),
                "total_updated": data.get("total_updated", 0),
            }
        else:
            return {
                "phase": "backfill",
                "days": days,
                "ok": data.get("fetch_ok", False),
                "total_inserted": data.get("inserted", 0),
                "total_updated": data.get("updated", 0),
            }
    except Exception as e:
        return {
            "phase": "backfill",
            "days": days,
            "ok": False,
            "error": f"解析 backfill 输出失败:{e}",
            "stdout_first_200": stdout[:200],
        }


def run_sync(
    days: int = 3,
    start_offset: int = 0,
    dry_run: bool = False,
) -> dict:
    """后台串行 3 天同步训记。写状态文件,可被 mavis cron self 检查。

    Args:
        days: 同步天数(默认 3)
        start_offset: 起始日偏移(0=今天,1=明天,...)
        dry_run: True 时只创建状态文件,不实际跑

    Returns:
        最终状态文件 dict
    """
    state = _init_state(days)
    _write_state(state)

    if dry_run:
        state["status"] = "completed"
        state["finished_at"] = _now_iso()
        state["phase"] = "push"
        state["error_summary"] = "dry_run 模式,无实际操作"
        state["results"].append({"phase": "dry_run", "ok": True})
        _write_state(state)
        return state

    # ── Phase 1: 串行 N 天 push-plan ──
    for i in range(days):
        target_date = (date.today() + timedelta(days=start_offset + i)).isoformat()
        state["current_day"] = i + 1
        state["phase"] = "push"
        _write_state(state)

        try:
            print(f"[run-sync] day {i+1}/{days}: push-plan --date {target_date}",
                  file=sys.stderr, flush=True)
            proc = _run_subprocess(["push-plan", "--date", target_date], timeout=600)
            summary = _summarize_push_output(target_date, proc["stdout"])
            summary["rc"] = proc["rc"]
            state["results"].append(summary)
        except subprocess.TimeoutExpired:
            state["results"].append({
                "date": target_date,
                "phase": "push",
                "ok": False,
                "error": "push-plan 子进程超时(>600s)",
            })
            state["error_summary"] = f"day {i+1} push 超时"
            state["status"] = "failed"
            state["finished_at"] = _now_iso()
            _write_state(state)
            return state
        except Exception as e:
            state["results"].append({
                "date": target_date,
                "phase": "push",
                "ok": False,
                "error": str(e),
            })
            state["error_summary"] = f"day {i+1} push 异常:{e}"
            state["status"] = "failed"
            state["finished_at"] = _now_iso()
            _write_state(state)
            return state

    # ── Phase 2: 一次 backfill ──
    state["phase"] = "backfill"
    _write_state(state)

    try:
        print(f"[run-sync] backfill --days {days}", file=sys.stderr, flush=True)
        proc = _run_subprocess(["backfill", "--days", str(days)], timeout=600)
        summary = _summarize_backfill_output(days, proc["stdout"])
        summary["rc"] = proc["rc"]
        state["results"].append(summary)
    except subprocess.TimeoutExpired:
        state["results"].append({
            "phase": "backfill",
            "days": days,
            "ok": False,
            "error": "backfill 子进程超时(>600s)",
        })
        state["error_summary"] = "backfill 超时"
        state["status"] = "failed"
        state["finished_at"] = _now_iso()
        _write_state(state)
        return state
    except Exception as e:
        state["results"].append({
            "phase": "backfill",
            "days": days,
            "ok": False,
            "error": str(e),
        })
        state["error_summary"] = f"backfill 异常:{e}"
        state["status"] = "failed"
        state["finished_at"] = _now_iso()
        _write_state(state)
        return state

    # ── 完成 ──
    state["status"] = "completed"
    state["finished_at"] = _now_iso()
    state["phase"] = None
    state["current_day"] = days
    _write_state(state)
    return state


def read_state() -> dict:
    """公开 API:供外部(包括 mavis cron self)读当前状态。"""
    return _read_state()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--start-offset", type=int, default=0)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    result = run_sync(days=args.days, start_offset=args.start_offset, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
