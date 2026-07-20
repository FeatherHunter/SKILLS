#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_plan.py — 一键"同步健身计划"(跨平台 Python 实现)

对应唤醒词:`/卡路里 同步健身计划`

封装 4 步:
  Step 1 · 补计划(飞书日历)— 调作息管家 ensure-plan-event
  Step 2 · 记心愿(飞书 task) — 调备忘录 add --category 心愿
  Step 3 · 训记推送 — 调 xunji_bridge push-plan (每天 ~3 分钟)
  Step 4 · 训记回写 — 调 xunji_bridge backfill --days N

为什么存在(2026-07-20 用户决策):
  之前每次 AI 都要重新拼装 3 个工具的 CLI(SKILL.md 全文 1200+ 行,易漏步骤)。
  把固定流程沉到脚本,用户 / AI 一键即可。

用法:
    python sync_plan.py                              # 从今天起 3 天
    python sync_plan.py --start-offset 1             # 从明天起 3 天
    python sync_plan.py --days 7                     # 推 7 天
    python sync_plan.py --skip-backfill              # 不做回写
    python sync_plan.py --backfill-days 3            # 回写 3 天
    python sync_plan.py --dry-run                    # 不实际改任何数据,只打印计划

依赖 CLI:
    - SKILLS/作息管家/scripts/schedule_cli.py ensure-plan-event
    - SKILLS/备忘录/script/memo_cli.py add / search
    - SKILLS/卡路里/scripts/xunji_bridge.py push-plan / run-sync / backfill
    - lark-cli.cmd (Windows 路径 C:\\Users\\<user>\\AppData\\Roaming\\npm\\lark-cli.cmd)

环境要求:
    - Python 3.10+
    - 训记 KEY 已配(XUNJI_TRAINS_KEY 优先,兼容 XUNJI_API_KEY)
    - 飞书 lark-cli 已登录

跨平台:
    - Windows / macOS / Linux 都跑,Windows 自动找 lark-cli.cmd

对应 SKILL.md 章节:「同步健身计划」
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

# ── 默认路径 ──
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILLS_ROOT = SKILL_DIR.parent

SCHEDULE_CLI = SKILLS_ROOT / "作息管家" / "scripts" / "schedule_cli.py"
MEMO_CLI = SKILLS_ROOT / "备忘录" / "script" / "memo_cli.py"
XUNJI_BRIDGE_DIR = SKILL_DIR  # xunji_bridge 在卡路里/scripts/

# lark-cli 路径(Windows)
LARK_CLI_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Roaming" / "npm" / "lark-cli.cmd",
    Path("/usr/local/bin/lark-cli"),
    Path("/usr/bin/lark-cli"),
]


def find_lark_cli() -> str | None:
    """Windows 默认位置 + 跨平台兜底:找 lark-cli(.cmd/.sh)。"""
    for p in LARK_CLI_CANDIDATES:
        if p.exists():
            return str(p)
    # 兜底 1:PATH 里有 "lark-cli"
    from shutil import which
    return which("lark-cli")


def run(cmd: list[str], timeout: int = 60) -> dict:
    """subprocess.run 包裹:统一 UTF-8 + 编码异常替换。

    Windows GBK 会让中文 stdout 崩溃(2026-07-20 实测),必须显式 encoding。
    """
    proc = subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    return {
        "rc": proc.returncode,
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def calc_day_plans(start_offset: int, days: int) -> list[dict]:
    """读卡路里 DB 计算 N 天 plan。

    Returns:
        [{date, is_rest, sessions: [{session_index, session_label,
                                     time_start, time_end, movements: [...]}]}, ...]
    """
    sys.path.insert(0, str(XUNJI_BRIDGE_DIR))
    from workout_plan import get_day_plan  # noqa: E402

    result = []
    for i in range(days):
        dt = date.today() + timedelta(days=start_offset + i)
        plan = get_day_plan(dt)
        sessions = plan.get("sessions", []) or []
        is_unstarted = bool(plan.get("unstarted"))
        is_rest = all(s.get("is_rest_day") for s in sessions) if sessions else is_unstarted
        result.append({
            "date": dt.isoformat(),
            "plan_week": plan.get("plan_week"),
            "is_unstarted": is_unstarted,
            "is_rest": bool(is_rest),
            "sessions": [
                {
                    "session_index": s.get("session_index"),
                    "session_label": s.get("session_label", ""),
                    "time_start": s.get("time_start", ""),
                    "time_end": s.get("time_end", ""),
                    "movements": s.get("movements", []) or [],
                }
                for s in sessions
            ],
        })
    return result


def step1_plan_events(plans: list[dict], dry_run: bool) -> dict:
    """Step 1 · 补计划(作息管家 → 飞书日历)"""
    print("\n═══ Step 1 · 补计划(飞书日历) ═══")
    created = skipped = failed = 0
    for p in plans:
        for s in p["sessions"]:
            label = s.get("session_label", "")
            if label == "休息日" or p["is_unstarted"]:
                print(f"  跳过: {p['date']} 休息日")
                skipped += 1
                continue
            ts = s.get("time_start", "")
            te = s.get("time_end", "")
            title = f"健身 {label} {ts}-{te}"
            notes = "; ".join(
                f"{m.get('name','')}{len(m.get('sets', []))}组"
                for m in s.get("movements", [])[:3]
            )
            if dry_run:
                print(f"  DRY: {p['date']} {title}")
                created += 1
                continue
            r = run([
                sys.executable, str(SCHEDULE_CLI),
                "ensure-plan-event", p["date"],
                "--time-start", ts, "--time-end", te,
                "--title", title,
                "--notes", notes, "--category", "运动",
            ])
            try:
                data = json.loads(r["stdout"])
                action = data.get("action", "?")
                eid = data.get("event", {}).get("feishu_event_id", "?")
                if action == "created":
                    created += 1
                    print(f"  ✅ {p['date']} {title}  feishu_id={eid[:18]}...")
                elif action == "found":
                    skipped += 1
                    print(f"  ⏭  {p['date']} {title}  (already exists)")
                else:
                    failed += 1
                    print(f"  ❌ {p['date']} {title}  {action}: {r['stdout'][:120]}")
            except json.JSONDecodeError:
                failed += 1
                print(f"  ❌ {p['date']} parse_err: {r['stdout'][:120]} | stderr: {r['stderr'][:120]}")
    return {"created": created, "skipped": skipped, "failed": failed}


def step2_wishes(plans: list[dict], dry_run: bool) -> dict:
    """Step 2 · 记心愿(备忘录 → 飞书 task)"""
    print("\n═══ Step 2 · 记心愿(飞书 task) ═══")
    added = skipped = failed = 0
    lark = find_lark_cli()
    for p in plans:
        for s in p["sessions"]:
            label = s.get("session_label", "")
            if label == "休息日" or p["is_unstarted"]:
                continue
            ts = s.get("time_start", "")
            te = s.get("time_end", "")
            content = f"健身 {label} {ts}-{te}"

            # 三步查重 (SKILL.md Step 3.1/3.2/3.3)
            sr = run([sys.executable, str(MEMO_CLI), "search", content,
                      "--category", "心愿", "--due", p["date"]])
            try:
                local_items = json.loads(sr["stdout"]).get("data", []) or []
            except json.JSONDecodeError:
                local_items = []
            in_local = len(local_items) > 0

            in_feishu = False
            if not in_local and lark:
                fr = run([lark, "task", "+search",
                          "--query", content,
                          "--due", f"{p['date']},{p['date']}",
                          "--format", "json"], timeout=20)
                try:
                    fr_data = json.loads(fr["stdout"])
                    items = (fr_data.get("data") or {}).get("items") or []
                    in_feishu = any(
                        it.get("summary") == content and
                        (it.get("due_at") or "").startswith(p["date"])
                        for it in items
                    )
                except json.JSONDecodeError:
                    in_feishu = False

            if in_local or in_feishu:
                skipped += 1
                print(f"  ⏭  {p['date']} {content}  (local={in_local} feishu={in_feishu})")
                continue

            if dry_run:
                added += 1
                print(f"  DRY: {p['date']} {content}")
                continue
            ar = run([sys.executable, str(MEMO_CLI), "add", content,
                      "--category", "心愿", "--due", p["date"]])
            try:
                ad = json.loads(ar["stdout"])
                if ad.get("status") == "ok":
                    added += 1
                    print(f"  ✅ {p['date']} {content}")
                else:
                    failed += 1
                    print(f"  ❌ {p['date']} {ar['stdout'][:120]}")
            except json.JSONDecodeError:
                failed += 1
                print(f"  ❌ {p['date']} parse_err: {ar['stdout'][:120]}")
    return {"added": added, "skipped": skipped, "failed": failed}


def step3_push_plans(plans: list[dict], dry_run: bool,
                     start_offset: int, days: int) -> dict:
    """Step 3 · 训记推送(每天 ~3 分钟)"""
    print("\n═══ Step 3 · 训记推送(每天 4 段 × 45s 限频) ═══")
    if dry_run:
        for p in plans:
            n = sum(1 for s in p["sessions"] if s.get("session_label") != "休息日")
            print(f"  DRY: {p['date']} ~{n} 段")
        return {"dry_run": True}
    # 真跑:用 run-sync 串行 N 天
    os.chdir(XUNJI_BRIDGE_DIR)
    r = run([sys.executable, "-m", "xunji_bridge", "run-sync",
             "--days", str(days), "--start-offset", str(start_offset)],
            timeout=900)
    print(r["stdout"][-2000:] if len(r["stdout"]) > 2000 else r["stdout"])
    if r["stderr"]:
        print(f"  stderr: {r['stderr'][-500:]}")
    return {"rc": r["rc"], "stdout_tail": r["stdout"][-500:]}


def step4_backfill(backfill_days: int, dry_run: bool) -> dict:
    """Step 4 · 训记回写(--days N,回看 N 天)"""
    print(f"\n═══ Step 4 · 训记回写(--days {backfill_days}) ═══")
    if dry_run:
        print(f"  DRY: backfill --days {backfill_days}")
        return {"dry_run": True}
    os.chdir(XUNJI_BRIDGE_DIR)
    r = run([sys.executable, "-m", "xunji_bridge", "backfill",
             "--days", str(backfill_days)], timeout=600)
    print(r["stdout"][-1500:] if len(r["stdout"]) > 1500 else r["stdout"])
    if r["stderr"]:
        print(f"  stderr: {r['stderr'][-300:]}")
    return {"rc": r["rc"], "stdout_tail": r["stdout"][-500:]}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="一键同步健身计划(4 步:补计划 + 记心愿 + 训记推送 + 回写)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--start-offset", type=int, default=0,
                    help="起始日偏移(0=今天,1=明天,默认 0)")
    ap.add_argument("--days", type=int, default=3,
                    help="同步天数(默认 3 天)")
    ap.add_argument("--backfill-days", type=int, default=1,
                    help="回写天数(默认 1 天=今天打完勾即可回写)")
    ap.add_argument("--skip-backfill", action="store_true",
                    help="跳过训记回写(只做前 3 步)")
    ap.add_argument("--dry-run", action="store_true",
                    help="不实际改任何数据,只打印计划")
    args = ap.parse_args()

    print("📋 sync_plan 配置:")
    print(f"  START_OFFSET={args.start_offset}  DAYS={args.days}  BACKFILL_DAYS={args.backfill_days}")
    print(f"  DRY_RUN={args.dry_run}")
    print(f"  PYTHON={sys.executable}")
    print(f"  lark-cli={find_lark_cli() or 'NOT FOUND'}")

    plans = calc_day_plans(args.start_offset, args.days)
    if not plans:
        print("❌ 读 plan 失败,DB 路径不对?")
        return 1

    print(f"\n📅 {len(plans)} 天 plan 概览:")
    for p in plans:
        ns = len([s for s in p["sessions"] if s.get("session_label") != "休息日"])
        marker = "  [休息日]" if p["is_rest"] else ""
        print(f"  {p['date']} (week {p['plan_week']})  {ns} 段{marker}")

    s1 = step1_plan_events(plans, args.dry_run)
    s2 = step2_wishes(plans, args.dry_run)
    s3 = step3_push_plans(plans, args.dry_run, args.start_offset, args.days)
    s4 = {} if args.skip_backfill else step4_backfill(args.backfill_days, args.dry_run)

    print("\n═══ 汇总 ═══")
    print(f"  Step 1 补计划: created={s1.get('created', 0)}  skipped={s1.get('skipped', 0)}  failed={s1.get('failed', 0)}")
    print(f"  Step 2 记心愿: added={s2.get('added', 0)}  skipped={s2.get('skipped', 0)}  failed={s2.get('failed', 0)}")
    print(f"  Step 3 训记推送: rc={s3.get('rc', '?')}")
    if s4:
        print(f"  Step 4 训记回写: rc={s4.get('rc', '?')}")
    elif args.skip_backfill:
        print(f"  Step 4 训记回写: SKIPPED")
    print("\n✅ sync_plan 完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())