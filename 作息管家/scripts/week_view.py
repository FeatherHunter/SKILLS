#!/usr/bin/env python3
"""
scripts/week_view.py — 周视图 · 7×24 全分类总览(实施 T6 · G1-A6)

真新增自包含域模块:模块级 COMMANDS 注册表 → schedule_cli 自动发现 dispatch,
不碰 schedule_cli.py / scenarios.yaml(实施 map 依赖 ← T1),也不改共享渲染器
(schedule_html_render.py 零改动:命名/注入/复制 prompt 全部本地构建)。

热力图组件复用(对抗式审查矛盾 4 修正:复用+扩展,不复制):
- 前端: _record_engine.js 新增 renderWeek,复用 record_category 热力图同款
  .heatmap 网格标记(hm-row-label / hm-col-label / hm-cell)+ statBlock/
  recordsCollapsible/copyPromptBlock 共享 helper
- 样式: _record_styles.css 既有 .heatmap/.hm-* 类,零新增
- 数据: heatmap 7×24 矩阵,cell = {cat, mins, color},与 render_record_category
  的 heatmap 同形态(格 = 该小时覆盖分钟最多的 L1 分类)

用法:
  python scripts/schedule_cli.py render-record-week [YYYY-MM-DD]
    anchor 缺省 = 今天;任意日期 → 定位所在周(周一~周日)
"""
import json
from datetime import date as _d, timedelta as _td, datetime
from pathlib import Path

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _week_range(anchor: str = "") -> tuple:
    """anchor 所在周(周一~周日);anchor 缺省 = 本周"""
    if anchor:
        a = _d.fromisoformat(anchor)
    else:
        a = _d.today()
    monday = a - _td(days=a.weekday())
    return monday, monday + _td(days=6)


def _hour_cells(day_recs: list[dict]) -> list[dict]:
    """单日 24 格:每格 = 该小时覆盖分钟最多的 L1 分类(record_category 同形态)"""
    from calculations import l1_of, cat_color
    from schedule_html_render import _to_min

    hour_mins: list[dict] = [dict() for _ in range(24)]
    for r in day_recs:
        s = _to_min(r.get("time_start", ""))
        e = _to_min(r.get("time_end", ""))
        if e <= s:
            continue
        cat = l1_of(r.get("category", ""))
        cur = s
        while cur < e:
            h = cur // 60
            if 0 <= h < 24:
                nh = (h + 1) * 60
                covered = min(nh, e) - cur
                if covered > 0:
                    hour_mins[h][cat] = hour_mins[h].get(cat, 0) + covered
            cur += 60
    row = []
    for h in range(24):
        if hour_mins[h]:
            dom = max(hour_mins[h].items(), key=lambda x: x[1])[0]
            row.append({"cat": dom, "mins": hour_mins[h][dom], "color": cat_color(dom)})
        else:
            row.append({"cat": None, "mins": 0, "color": "#f5f5f7"})
    return row


def _build_ai_questions(total_minutes, day_totals, l1_minutes, sleep_minutes) -> list:
    """周维度 AI 思考钩子(数据事实驱动,不虚构)"""
    from calculations import fmt_dur_short

    days_with = sum(1 for t in day_totals if t > 0)
    qs = []
    if days_with == 0:
        qs.append("本周 schedule_records 无记录,建议先补录作息或确认查询的周是否正确")
        return qs
    avg = total_minutes / days_with
    qs.append(f"本周 {days_with}/7 天有记录,日均 {fmt_dur_short(round(avg))},生活节奏是否稳定?")
    target = 49 * 60
    if sleep_minutes > 0:
        if sleep_minutes >= target:
            qs.append(f"睡眠/午睡合计 {fmt_dur_short(sleep_minutes)},达到 7 天 49 小时目标 ✓")
        else:
            qs.append(f"睡眠/午睡合计 {fmt_dur_short(sleep_minutes)},距 7 天 49 小时目标还差 "
                      f"{fmt_dur_short(target - sleep_minutes)},是否需要调整就寝时间?")
    if l1_minutes:
        top = max(l1_minutes.items(), key=lambda x: x[1])
        qs.append(f"本周投入最多的是「{top[0]}」({fmt_dur_short(int(top[1]))}),符合你的优先级规划吗?")
    return qs


def _build_copy_prompt(meta, records, summary_items, health) -> str:
    """4 部分复制 prompt(ADR-0002 Q6 · 总纲 §04 原则 10 · 本地构建,不依赖共享映射)"""
    from calculations import fmt_dur_short

    top3 = summary_items[:3]
    cat_lines = "\n".join(
        f"  - {s.get('emoji', '')} {s['category']}:{s['duration_text']}({s.get('pct', 0)}%)"
        for s in top3
    )
    return (
        f"① 场景: 查看了 {meta['start']} 至 {meta['end']} 作息周视图"
        f"(7×24 全分类总览,共 {len(records)} 条记录,总时长 {fmt_dur_short(meta['total_minutes'])})\n\n"
        f"② 数据:\n健康分: {health.get('score', '—')} ({health.get('label', '—')})\n{cat_lines}\n\n"
        f"③ 期望: 可对某类做区间深挖(render-record-category-range),"
        f"或对本周单日做复盘(render-replay),或规划下周安排\n\n"
        f"④ 来源: week_view.html 生成于 {meta['generated_at']},"
        f"数据来自 schedule_records WHERE date BETWEEN {meta['start']} AND {meta['end']}"
    )


def render_record_week(anchor: str = "") -> dict:
    """周视图 payload:7 天 × 24 小时全分类总览(日历周一~周日,无数据的天也占位)"""
    from schedule_db import get_records_range
    from calculations import (
        aggregate_by_l1, cat_emoji, cat_color, fmt_dur, fmt_dur_short,
        compute_health_score,
    )
    from schedule_html_render import _build_full_records

    monday, sunday = _week_range(anchor)
    start = monday.isoformat()
    end = sunday.isoformat()
    records = get_records_range(start, end)
    total_minutes = sum(r.get("duration_minutes") or 0 for r in records)

    days = [(monday + _td(days=i)).isoformat() for i in range(7)]
    weekday_labels = [f"{WEEKDAYS[i]} {days[i][5:]}" for i in range(7)]

    by_date: dict[str, list[dict]] = {}
    for r in records:
        by_date.setdefault(r.get("date", ""), []).append(r)
    heatmap = [_hour_cells(by_date.get(d, [])) for d in days]
    day_totals = [sum(c["mins"] for c in row) for row in heatmap]

    l1_minutes = aggregate_by_l1(records)
    sorted_l1 = sorted(l1_minutes.items(), key=lambda x: -x[1])
    summary_items = [
        {
            "category": cat, "emoji": cat_emoji(cat), "color": cat_color(cat),
            "total_minutes": int(mins), "duration_text": fmt_dur_short(int(mins)),
            "pct": round(mins / total_minutes * 100, 1) if total_minutes else 0.0,
        }
        for cat, mins in sorted_l1
    ]

    sleep_minutes = sum(
        r.get("duration_minutes") or 0
        for r in records
        if "睡眠" in r.get("category", "") or "午睡" in r.get("category", "")
    )
    active_days = sum(1 for t in day_totals if t > 0)
    health_score = compute_health_score(records)
    health = {
        "score": health_score,
        "label": ("充足" if sleep_minutes >= 49 * 60
                  else ("偏短" if sleep_minutes >= 35 * 60 else "严重不足")),
    }

    meta = {
        "mode": "record-week",
        "date": anchor or _d.today().isoformat(),
        "start": start, "end": end,
        "weekdays": WEEKDAYS,
        "total_minutes": int(total_minutes),
        "active_days": active_days,
        "title": f"作息周视图 · {start} ~ {end}",
        "subtitle": (f"{WEEKDAYS[0]}~{WEEKDAYS[-1]} · {len(records)} 条记录 · "
                     f"总时长 {fmt_dur(total_minutes)}"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    payload = {
        "meta": meta,
        "days": days,
        "weekday_labels": weekday_labels,
        "heatmap": heatmap,
        "day_totals": day_totals,
        "summary_items": summary_items,
        "records": _build_full_records(records),
        "ai_questions": _build_ai_questions(total_minutes, day_totals, l1_minutes, sleep_minutes),
        "copy_prompt": _build_copy_prompt(meta, records, summary_items, health),
        "errors": [],
    }
    # #269 补齐: Base scene.snapshot + meta 信封（复制数据/日志按钮）
    from schedule_html_render import _ensure_base_meta, _build_base_scene_block
    from calculations import fmt_dur_short
    payload = _ensure_base_meta(payload, "周视图", "周视图")
    _h = health or {}
    payload.update(_build_base_scene_block(
        "周视图", "周视图",
        [f"{start}~{end} · 总时长 {fmt_dur_short(total_minutes)}",
         f"健康分 {_h.get('score', '—')} ({_h.get('label', '')})"],
        [{"heading": "每日总览", "rows": [
            f"{days[i] if i < len(days) else '?'}: {day_totals[i] if i < len(day_totals) else 0} 分钟"
            for i in range(min(7, len(day_totals) if day_totals else 0))
        ]},
         {"heading": "分类统计", "rows": [
            f"{s.get('category') or ''}: {fmt_dur_short(s.get('total_minutes') or 0)}"
            for s in (summary_items or [])[:8]
        ]}],
    ))
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {start} ~ {end} 周视图数据已生成",
    }


def week_view_main(args):
    """render-record-week [YYYY-MM-DD] — 周视图(anchor 缺省 = 本周)"""
    from schedule_html_render import inject_into_template, _naming_path

    anchor = args[0] if args else ""
    if anchor:
        try:
            _d.fromisoformat(anchor)
        except ValueError:
            print(json.dumps({
                "status": "error",
                "message": f"date 格式非法: '{anchor}'(期望 YYYY-MM-DD)",
            }, ensure_ascii=False))
            return

    payload = render_record_week(anchor)
    if payload.get("status") != "ok":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    try:
        output_path = _naming_path("查作息周视图", "record/week")
        final_path = inject_into_template("week_view.html", payload, output_path)
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "message": f"渲染失败: {type(e).__name__}: {e}",
        }, ensure_ascii=False))
        return

    fp = Path(final_path)
    out = {
        "status": "ok",
        "data": {
            "file_path": str(fp),
            "bytes": fp.stat().st_size,
            "size_kb": fp.stat().st_size // 1024,
            "mode": "record-week",
            "start": payload["data"]["meta"]["start"],
            "end": payload["data"]["meta"]["end"],
            "days": 7,
            "total_records": len(payload["data"]["records"]),
        },
        "message": f"✓ 周视图已写入: {fp}",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


COMMANDS = {"render-record-week": week_view_main}


if __name__ == "__main__":
    import sys
    week_view_main(sys.argv[1:])
