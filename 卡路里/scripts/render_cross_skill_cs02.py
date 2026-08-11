#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卡路里 · CS-02「睡眠时长 vs 减重」HTML 渲染（#274 试点 · 技能互联全链路）

流程: cross_skill.cs02() 取合并结果 → 组织 payload（契约 §4 信封）→
公共组件注入管线（INJECT-DATA / SHARED-HELPERS / SHARED-CSS 硬拦截）→ 落盘 calorie_html/。

用法:
  python scripts/render_cross_skill_cs02.py                     # 近 30 天
  python scripts/render_cross_skill_cs02.py --from 2026-07-01 --to 2026-08-10
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from cross_skill import cs02, default_window  # noqa: E402
from html_paths import html_scene_path  # noqa: E402

TEMPLATE = SKILL_DIR / "templates" / "cross_skill_sleep.html"
INJECTOR = Path(__file__).resolve().parents[2] / "公共组件" / "injector.py"


def build_payload(result: dict) -> dict:
    """cs02 结果 → 注入器信封（公共组件契约 §4）"""
    now = datetime.now().isoformat(timespec="seconds")
    series = result.get("series", [])
    groups = result.get("groups", [])
    corr = result.get("correlation", {})

    def _dur(mins: int) -> str:
        h, m = divmod(int(mins), 60)
        return f"{h}h{m:02d}m" if h else f"{m}m"

    summary = [f"窗口 {result.get('start', '—')} ~ {result.get('end', '—')}"]
    if result.get("ok"):
        summary.append(f"对齐 {result['days']} 天（睡眠 {result['sleep_days']} 天 · 体重 {result['weight_days']} 天）")
        if corr.get("same_day") is not None:
            summary.append(f"同日相关 r={corr['same_day']:+.2f} · 前夜相关 r={corr.get('lag_1day') or '—'}")
    summary.append(result.get("insight", ""))

    group_rows = []
    for g in groups:
        delta = g["weight_delta"]
        delta_s = f"{delta:+.2f} kg" if delta is not None else "—"
        group_rows.append(
            f"{g['label']} · {g['days']} 天 · 日均 {_dur(g['sleep_avg'] or 0)} · 体重净变化 {delta_s}"
        )
    detail_rows = [
        f"{s['date']} · 睡眠 {_dur(s['sleep_min'])} · 体重 {s['weight_kg']:.1f} kg"
        for s in series[-14:]  # 明细只带最近 14 天，复制不爆长
    ]

    sections = []
    if group_rows:
        sections.append({"heading": "睡眠分位分组 · 体重变化", "rows": group_rows})
    if detail_rows:
        sections.append({"heading": "每日明细（最近 14 天）", "rows": detail_rows})

    snapshot = {
        "title": "睡眠时长 vs 减重",
        "summary": summary,
        "sections": sections,
    }
    if not result.get("ok"):
        snapshot["sections"] = [{"heading": "取数失败", "rows": [result.get("error", "未知错误")]}]

    return {
        "status": "ok" if result.get("ok") else "error",
        "message": "" if result.get("ok") else result.get("error", "取数失败"),
        "data": {
            "meta": {
                "command_cn": "联动作息管家（睡眠时长 vs 减重）",
                "occurred_at": now,
                "skill_name": "卡路里",
                "wake_word": "联动作息管家（睡眠时长 vs 减重）",
            },
            "scene": {
                "scene_id": "cs02",
                "snapshot": snapshot,
                "buttons": [],
            },
            "cs02": result,
            "copy_log": {
                "thinking": "CS-02 组合分析：睡眠时长（作息管家 daily_summary 主睡眠段）与体重（卡路里 weight_log）按天对齐，"
                           "按睡眠时长分 5 组（<6h/6-7h/7-8h/8-9h/>9h）对比各组体重净变化，再算同日与前夜（滞后 1 天）相关性。",
                "data_structure": f"series[{len(series)}]{{date,sleep_min,weight_kg}} · groups[{len(groups)}]{{label,days,sleep_avg,weight_delta}} · correlation{{same_day,lag_1day}}",
                "call_chain": "render_cross_skill_cs02 → cross_skill.cs02 → skilllink-read(作息管家.sleep) + weight_log(卡路里本地)",
                "timestamp": now,
                "exception": "" if result.get("ok") else result.get("error", ""),
            },
        },
    }


def render(start: str, end: str) -> int:
    result = cs02(start, end)
    payload = build_payload(result)

    # 注入管线（公共组件 injector · 硬拦截占位符校验）
    payload_file = SKILL_DIR / ".scratch" / "_cs02_payload.json"
    payload_file.parent.mkdir(parents=True, exist_ok=True)
    payload_file.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    import subprocess

    out_path = html_scene_path(SKILL_DIR, "睡眠vs减重", "result")
    r = subprocess.run(
        [sys.executable, str(INJECTOR), str(TEMPLATE),
         "--payload", str(payload_file), "--output", str(out_path),
         "--strict-payload"],
        capture_output=True, text=True, encoding="utf-8",
    )
    try:
        inj = json.loads(r.stdout)
    except json.JSONDecodeError:
        inj = {"status": "error", "message": r.stdout[:300] or r.stderr[:300]}
    if inj.get("status") != "ok":
        print(f"❌ 注入失败: {inj.get('message', '未知')}", file=sys.stderr)
        return 1

    print(f"✅ 已生成: {out_path}")
    print(f"   场景: 睡眠时长 vs 减重 | 窗口: {start} ~ {end} | 对齐 {result.get('days', 0)} 天")
    print(f"   洞察: {result.get('insight', '')[:80]}")
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={out_path.absolute()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="CS-02 睡眠 vs 减重 HTML 渲染")
    parser.add_argument("--from", dest="from_", default=None, help="开始日期 YYYY-MM-DD（默认近 30 天）")
    parser.add_argument("--to", default=None, help="结束日期 YYYY-MM-DD（默认今天）")
    args = parser.parse_args()
    start, end = default_window()
    if args.from_:
        start = args.from_
    if args.to:
        end = args.to
    return render(start, end)


if __name__ == "__main__":
    from _io_guard import guard_io

    guard_io()
    sys.exit(main())
