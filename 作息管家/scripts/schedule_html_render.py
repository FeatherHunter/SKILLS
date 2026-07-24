#!/usr/bin/env python3
"""
schedule_html_render.py — 日程计划查询的 HTML 渲染器（2026-07-23 新增）

设计原则(来自《预置 HTML+注入数据指导手册》§4 通用架构):
- HTML 不直连数据库 — 数据全由 CLI/调度器注入
- 模板只放在 templates/, 输出副本到指定路径
- JSON 三段式 {status, data, message}
- 所有注入值走 json.dumps,防 XSS(手册 §11)

职责:
  1. 从 schedule_db 拉数据(list_plan_events / get_plans)
  2. 计算派生字段(summary / gap / feishu 状态)
  3. 读 templates/schedule_list_events.html
  4. JSON 注入 + 写副本

被 schedule_cli.py 的两个新子命令调用:
  - render-list-events <日期>
  - render-query-plans <日期1,日期2,...>
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_DIR = SKILL_DIR / "templates"

# 复用 schedule_db 的 DB 配置(不重复定义)
sys.path.insert(0, str(SCRIPT_DIR))


def _normalize_date(d) -> str:
    """复用 schedule_db 的归一化(避免重复维护)"""
    from schedule_db import _normalize_date as _n
    return _n(d)


def _build_summary(events: list[dict], inactive_ids: set) -> dict:
    """派生首屏摘要卡字段"""
    active = [e for e in events if e["id"] not in inactive_ids]
    completed = sum(1 for e in active if e.get("completion") == "已完成")
    completed_late = sum(1 for e in active if e.get("completion") == "已完成(超时)")
    partial = sum(1 for e in active if e.get("completion") == "部分完成")
    unfin = sum(1 for e in active if e.get("completion") == "未完成")
    unfin_force = sum(1 for e in active if e.get("completion") == "未完成(不可抗力)")
    done_count = completed + completed_late + partial  # "算完成了的"广义口径
    unreviewed = sum(1 for e in active if not e.get("completion"))
    unsynced = sum(1 for e in active if not e.get("feishu_event_id"))
    return {
        "total_active": len(active),
        "total_inactive": len(inactive_ids),
        "completed_count": done_count,
        "completed_strict": completed,
        "completed_late": completed_late,
        "partial": partial,
        "unfinished": unfin,
        "unfinished_force": unfin_force,
        "unreviewed_count": unreviewed,
        "unsynced_count": unsynced,
    }


def _hhmm_to_minutes(t: str) -> int:
    """HH:MM → 分钟数(24:00 → 24*60, 跨日边界;其余正常)"""
    if not t:
        return 0
    if t == "24:00":
        return 24 * 60
    h, m = t.split(":")[:2]
    try:
        return int(h) * 60 + int(m)
    except ValueError:
        return 0


def _build_gap(events: list[dict]) -> dict:
    """检测 24h 联合覆盖;只对 active 事件"""
    active = sorted(
        [e for e in events if e.get("is_active") != 0],
        key=lambda e: _hhmm_to_minutes(e.get("time_start") or "00:00"),
    )
    if not active:
        return {"has_gap": False, "gap_count": 0, "first_gap": None}

    gaps = []
    first_start = _hhmm_to_minutes(active[0].get("time_start") or "00:00")
    if first_start > 0:
        gaps.append(("00:00", active[0].get("time_start")))
    for i in range(len(active) - 1):
        prev_end = _hhmm_to_minutes(active[i].get("time_end") or "00:00")
        next_start = _hhmm_to_minutes(active[i + 1].get("time_start") or "00:00")
        if next_start > prev_end:
            gaps.append((active[i].get("time_end"), active[i + 1].get("time_start")))

    last_end = _hhmm_to_minutes(active[-1].get("time_end") or "00:00")
    if last_end < 24 * 60:
        gaps.append((active[-1].get("time_end"), "24:00"))

    return {
        "has_gap": len(gaps) > 0,
        "gap_count": len(gaps),
        "first_gap": f"{gaps[0][0]} → {gaps[0][1]}" if gaps else None,
        "all_gaps": [f"{a} → {b}" for a, b in gaps],
    }


def _safe_iso_or_empty(dt) -> str:
    try:
        if dt:
            return str(dt)
    except Exception:
        pass
    return ""


def render_list_events(date: str, *, include_inactive: bool = True) -> dict:
    """
    为指定日期生成 HTML 渲染数据(对应 list-events 模式)。
    返回 {status, data, message} 三段式 dict,data 可直接 JSON 注入。
    """
    from schedule_db import list_plan_events

    date = _normalize_date(date)
    active = list_plan_events(date, include_inactive=False)
    all_events = list_plan_events(date, include_inactive=True) if include_inactive else active

    inactive_ids = {e["id"] for e in all_events if e.get("is_active") == 0}
    # 默认按 time_start 排序,等同 list-events 的原行为
    all_events.sort(key=lambda e: (e.get("time_start") or ""))

    summary = _build_summary(all_events, inactive_ids)
    gap = _build_gap(all_events)

    feishu = _get_feishu_summary()

    data = {
        "meta": {
            "mode": "list-events",
            "date": date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "include_inactive": include_inactive,
        },
        "summary": summary,
        "events": all_events,
        "gap": gap,
        "feishu": feishu,
        "inactive": [e for e in all_events if e.get("is_active") == 0],
        "errors": [],
    }
    return {
        "status": "ok",
        "data": data,
        "message": f"✓ {date} 日程 HTML 渲染数据已生成({summary['total_active']} 活跃 + {summary['total_inactive']} 停用)",
    }


def render_query_plans(dates_raw: str) -> dict:
    """
    为 1 个或多个日期生成 24h 聚合视图的 HTML 渲染数据(对应 query-plans 模式)。
    dates_raw: 逗号分隔日期字符串
    """
    from schedule_db import list_plan_events

    dates = [_normalize_date(d) for d in dates_raw.split(",") if d.strip()]
    if not dates:
        return {
            "status": "error",
            "data": None,
            "message": "至少需要一个日期(逗号分隔)",
        }

    days = []
    all_events_flat = []  # 平铺,让模板可用统一 events 数组渲染
    total_active = 0
    total_inactive = 0
    total_unsynced = 0
    total_unreviewed = 0
    total_completed = 0

    for d in dates:
        all_e = list_plan_events(d, include_inactive=True)
        all_e.sort(key=lambda e: (e.get("time_start") or ""))
        inactive_ids = {e["id"] for e in all_e if e.get("is_active") == 0}
        active = [e for e in all_e if e.get("is_active") != 0]
        s = _build_summary(all_e, inactive_ids)
        g = _build_gap(all_e)
        days.append({
            "date": d,
            "summary": s,
            "gap": g,
            "events": all_e,
            "inactive": [e for e in all_e if e.get("is_active") == 0],
        })
        all_events_flat.extend(all_e)
        total_active += s["total_active"]
        total_inactive += s["total_inactive"]
        total_unsynced += s["unsynced_count"]
        total_unreviewed += s["unreviewed_count"]
        total_completed += s["completed_count"]

    feishu = _get_feishu_summary()

    data = {
        "meta": {
            "mode": "query-plans",
            "dates": dates,
            "date_count": len(dates),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "summary": {
            "total_active": total_active,
            "total_inactive": total_inactive,
            "completed_count": total_completed,
            "unreviewed_count": total_unreviewed,
            "unsynced_count": total_unsynced,
        },
        "days": days,
        "events": all_events_flat,  # 平铺,模板 events.length 可用
        "feishu": feishu,
        "errors": [],
    }
    return {
        "status": "ok",
        "data": data,
        "message": f"✓ {len(dates)} 日查询 HTML 渲染数据已生成(共 {total_active} 活跃)",
    }


def _get_feishu_summary() -> dict:
    """探测飞书可用度(三档),失败降级,不抛异常"""
    try:
        from feishu_sync import is_feishu_available
        st = is_feishu_available()
        return {
            "tier": st.tier,
            "cli_installed": st.cli_installed,
            "authenticated": st.authenticated,
            "calendar_writable": st.calendar_writable,
            "last_error": st.last_error,
        }
    except Exception as e:
        return {"tier": "unknown", "last_error": str(e)}


def inject_into_template(template_name: str, payload: dict, output_path: Path) -> Path:
    """
    读模板 → JSON 注入 → 写副本。
    严格遵循手册 §8:生成副本,不污染原模板。
    """
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"模板不存在: {template_path}")

    template_text = template_path.read_text(encoding="utf-8")
    payload_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_str = payload_str.replace("</", "<\\/")

    anchor = '<script id="payload" type="application/json">'
    if anchor not in template_text:
        raise RuntimeError(
            f"模板 {template_name} 缺少 {anchor} 锚点"
        )

    # 找到锚点位置,把锚点开始到 </script> 结束 整段替换为「锚点 + payload + </script>」
    close_tag = "</script>"
    start_idx = template_text.find(anchor)
    end_idx = template_text.find(close_tag, start_idx)
    if end_idx < 0:
        raise RuntimeError(f"模板 {template_name} 缺少 {close_tag} 闭合")
    end_idx += len(close_tag)  # 包含 </script>

    head = template_text[:start_idx]
    tail = template_text[end_idx:]
    injected = head + anchor + payload_str + close_tag + tail
    # 替换 {{ title }} 占位符
    title = title_for_mode(payload.get("data", {}).get("meta", {}))
    injected = injected.replace("{{ title }}", title).replace("{{ TITLE }}", title)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(injected, encoding="utf-8")

    # 5 模板共享 CSS/JS 引擎: 复制到输出目录(让 HTML 离线可读)
    if "schedule_record_" in template_name:
        for aux in ("_record_styles.css", "_record_engine.js"):
            src = TEMPLATE_DIR / aux
            if src.exists():
                import shutil
                shutil.copy2(src, output_path.parent / aux)

    return output_path


# ===== 路径常量:硬绑 SKILLS_DB_PATH(破坏兼容,plan/list + plan/query 也走这里)=====
import os

def _html_base_dir() -> Path:
    """延迟求值,避免模块加载时 SKILLS_DB_PATH/schedule_html 还不存在导致 RECORD_DIR 永久冻结为空"""
    db_dir = os.environ.get('SKILLS_DB_PATH') or 'D:/.db'
    return Path(db_dir) / 'schedule_html'

def _record_dir() -> Path:
    return _html_base_dir() / 'record'


def default_output_path(meta: dict) -> Path:
    """
    根据 meta 决定默认输出路径(硬绑 SKILLS_DB_PATH/schedule_html/):

      record/ 子目录: 5 个 record-* 模式  → 走 record_output_path 分发
      plan/ 子目录: 2 个 plan-* 模式(list-events / query-plans)→ 本函数直接 inline
      fallback: SKILLS_DB_PATH/schedule_html/view.html

    规则来源:SKILL.md §3.x HTML 命名规则(2026-07-23 重构版)
    上一版本写到 SKILL_DIR/reports/,已被一刀删除,从此统一到 SKILLS_DB_PATH 下。
    """
    mode = meta.get("mode", "list-events")
    base = _html_base_dir()
    plan_list = base / 'plan' / 'list'
    plan_query = base / 'plan' / 'query'

    # M10: record-* 模式走 record_output_path 分发(消除死代码)
    if mode.startswith("record-"):
        return record_output_path(mode, meta)

    if mode == "list-events":
        date = meta.get("date", "unknown")
        return plan_list / f"plan_list_{date}.html"
    if mode == "query-plans":
        dates = meta.get("dates", [])
        if len(dates) == 1:
            return plan_query / f"plan_query_{dates[0]}.html"
        return plan_query / f"plan_query_{dates[0]}_to_{dates[-1]}.html"
    if mode == "plan-preview":
        date = meta.get("date", "unknown")
        return plan_list / f"plan_preview_{date}.html"
    if mode == "plan-review":
        date = meta.get("date", "unknown")
        return plan_list / f"plan_review_{date}.html"
    if mode == "plan-receipt":
        # 改/删计划回执(回执型第2款,2026-07-24)
        pid = meta.get("plan_id", "unknown")
        date = meta.get("date", "unknown")
        action = meta.get("action", "update")
        return base / 'plan' / 'receipt' / f"plan_receipt_id{pid}_{date}_{action}.html"
    if mode == "plan-receipt-add":
        # 补计划回执(回执型第3款,2026-07-24)
        pid = meta.get("plan_id", "unknown")
        date = meta.get("date", "unknown")
        return base / 'plan' / 'receipt' / f"plan_receipt_add_id{pid}_{date}.html"
    if mode == "plan-receipt-write":
        # 写摘要回执(回执型第4款,2026-07-24)
        pid = meta.get("plan_id", "unknown")
        date = meta.get("date", "unknown")
        return base / 'plan' / 'receipt' / f"plan_receipt_write_id{pid}_{date}.html"
    return base / "view.html"


# 5 模板目录映射 — M10 改用 record_output_path(meta) 自动派生,不再需要独立字典
# (旧 _RECORD_TEMPLATE_DIRS 已删除)


def record_output_path(mode: str, meta: dict = None) -> Path:
    """
    5 模板统一路径生成器(从 meta dict 派生):
      record-day     meta.date                              → <base>/record/day/<date>_record_day.html
      record-range   meta.start / meta.end                  → <base>/record/range/<start>_to_<end>_record_range.html
      record-compare meta.ranges[0].label / [1].label     → <base>/record/compare/<labelA>_vs_<labelB>_record_compare.html
      record-category meta.category / start / end          → <base>/record/category/<cat>_<start>_to_<end>_record_category.html
      record-anomaly  meta.window                          → <base>/record/anomaly/<today>_w<window>_record_anomaly.html
    """
    base = _html_base_dir() / 'record'
    from datetime import date as _dt
    today = _dt.today().isoformat()
    meta = meta or {}

    if mode == "record-day":
        d = meta.get("date", today)
        return base / "day" / f"{d}_record_day.html"
    if mode == "record-range":
        s = meta.get("start", today)
        e = meta.get("end", today)
        return base / "range" / f"{s}_to_{e}_record_range.html"
    if mode == "record-compare":
        ranges = meta.get("ranges") or []
        a = (ranges[0] or {}).get("label", "a") if len(ranges) > 0 else "a"
        b = (ranges[1] or {}).get("label", "b") if len(ranges) > 1 else "b"
        return base / "compare" / f"{a}_vs_{b}_record_compare.html"
    if mode == "record-category":
        # M5:meta.category 已经是用户原值(不映射),文件名拼原值
        cat = meta.get("category", "cat")
        s = meta.get("start", "x")
        e = meta.get("end", "x")
        return base / "category" / f"{cat}_{s}_to_{e}_record_category.html"
    if mode == "record-anomaly":
        w = meta.get("window", 7)
        return base / "anomaly" / f"{today}_w{w}_record_anomaly.html"
    if mode == "record-report":
        # 兼容旧 CLI,等价 record-day
        d = meta.get("date", today)
        return base / "day" / f"{d}_record_day.html"
    if mode == "record-receipt":
        # 漂亮回执(回执型首款,2026-07-24)
        rid = meta.get("record_id", "unknown")
        return base / "receipt" / f"receipt_id{rid}.html"
    if mode == "plan-receipt":
        # 改/删计划回执(回执型第2款,2026-07-24)
        pid = meta.get("plan_id", "unknown")
        date = meta.get("date", today)
        action = meta.get("action", "update")
        return base / 'plan' / 'receipt' / f"plan_receipt_id{pid}_{date}_{action}.html"
    if mode == "record-detail":
        # 详情页(单日 + 可选 record_id)
        d = meta.get("date", today)
        rid = meta.get("record_id")
        if rid:
            return base / "detail" / f"{d}_id{rid}_record_detail.html"
        return base / "detail" / f"{d}_record_detail.html"
    return base / f"unknown_{today}.html"


def title_for_mode(meta: dict) -> str:
    """为模板 title 生成对应文案(替换 {{title}} 占位符)"""
    mode = meta.get("mode", "list-events")
    if mode == "list-events":
        d = meta.get("date", "")
        return f"日程计划 · {d}"
    if mode == "query-plans":
        dates = meta.get("dates", [])
        if len(dates) == 1:
            return f"日程计划 · {dates[0]}"
        if len(dates) >= 2:
            return f"日程计划 · {dates[0]} ~ {dates[-1]} ({len(dates)} 日)"
        return "日程计划"
    if mode == "record-report":
        d = meta.get("date", "")
        from datetime import date as _dt
        try:
            dt = _dt.fromisoformat(d)
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            return f"作息报告 · {dt.year}年{dt.month}月{dt.day}日（{weekdays[dt.weekday()]}）"
        except Exception:
            return f"作息报告 · {d}"
    return "作息管家"


# ===== 历史 4 段视觉复刻(沿用 _render_report_2026-07-02.py:38-43)=====
EMOJI_MAP = {
    "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
    "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
    "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿", "兴趣爱好": "🎨",
    "家务": "🧹", "未知": "❓", "休息": "📌", "起居": "🪥", "计划": "📋",
    "维持": "🌱", "维持.睡眠": "🌱",
    "饮食记录": "🍽️", "做饭": "🍳", "饮食": "🍽️", "采购": "🛒",
    "就医": "💊", "护肤": "💆",
    "修行": "🧘", "冥想": "🧠", "看病": "🩺", "康复": "🩹", "保健": "🛡️", "八段锦": "☯️",
    "AI调优": "🤖", "开发": "💻", "剪辑": "🎬", "文案": "📝",
    "运营": "📊", "会议": "🤝", "财务": "💰", "调研": "🔍",
    "技术": "💻", "语言": "🗣️", "考试": "✏️", "读书": "📕",
    "研究": "🔬", "AI": "🤖", "阅读": "📰",
    "文字": "✍️", "视频": "🎥", "音频": "🎵", "设计": "🖌️",
    "编程": "💻", "菜谱": "🍴", "SOP": "📋", "教学": "👨‍🏫",
    "家人": "👨‍👩‍👧", "朋友": "🧑‍🤝‍🧑", "同事": "👔", "伴侣": "❤️",
    "宠物": "🐾", "社交/服务": "👋",
    "游戏": "🎮", "视频/追剧": "📺", "音乐": "🎧", "手机": "📱",
    "玩耍": "🎈", "发呆": "💭", "散步": "🚶", "午睡": "😴",
    "过渡": "⏳", "休息/娱乐": "📰",
    "代办": "☑️", "决策": "🤔", "杂事": "🔧", "收拾": "🧹",
    "行政": "📑", "等候": "⏳", "园艺": "🌿",
    "健身": "🏋️", "通勤/回家": "🚴",
    "维持/通勤": "🚴", "学习/研究": "🔬",
}

COLOR_MAP = {
    "睡眠": "#5E5CE6", "工作": "#007AFF", "学习": "#34C759", "运动": "#FF9500",
    "通勤": "#64D2FF", "餐饮": "#FF9F0A", "娱乐": "#AF52DE", "社交": "#FF2D55",
    "休闲": "#30D158", "健康": "#FF3B30", "洗漱": "#5AC8FA", "兴趣爱好": "#BF8F5F",
    "家务": "#A2845E", "未知": "#8E8E93", "休息": "#8E8E93", "起居": "#8E8E93", "计划": "#FF6B9D",
    "维持": "#5E5CE6",
    "做饭": "#FF9F0A", "饮食": "#FF9F0A", "采购": "#FF9F0A",
    "就医": "#FF3B30", "护肤": "#FF3B30",
    "出行": "#64D2FF",
    "健身": "#FF9500", "修行": "#FF9500", "冥想": "#FF9500",
    "AI调优": "#007AFF", "开发": "#007AFF", "技术": "#007AFF",
    "散步": "#34C759", "午睡": "#5E5CE6",
    "游戏": "#AF52DE", "手机": "#AF52DE",
    "代办": "#A2845E", "杂事": "#A2845E", "收拾": "#A2845E", "行政": "#A2845E",
}


def _cat_emoji(cat: str) -> str:
    return EMOJI_MAP.get(cat, "📌")


def _cat_color(cat: str) -> str:
    return COLOR_MAP.get(cat, "#8E8E93")


def _to_min(hhmm: str) -> int:
    """HH:MM → 分钟数(24:00 → 24*60,跨日边界;其余正常)"""
    if not hhmm:
        return 0
    if hhmm == "24:00":
        return 24 * 60
    h, m = hhmm.split(":")[:2]
    try:
        return int(h) * 60 + int(m)
    except ValueError:
        return 0


def _fmt_dur(mins: int) -> str:
    if mins <= 0:
        return "0分钟"
    h = mins // 60
    m = mins % 60
    if h and m:
        return f"{h}小时{m}分钟"
    if h:
        return f"{h}小时"
    return f"{m}分钟"


def _fmt_dur_short(mins: int) -> str:
    """时间轴 tooltip 用:6h40m 这种短格式"""
    h = mins // 60
    m = mins % 60
    if h and m:
        return f"{h}h{m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def _build_full_records(records: list) -> list:
    """
    100% 字段暴露原则:把 schedule_records 原始行映射为 11 字段 dict 列表。
    11 字段:id / date / time_start / time_end / duration_minutes / activity /
    category / source_contents / source_timestamps / analysis_reasoning / created_at。
    上层(HTML 模板) 自行决定消费哪些、是否折叠、什么样式。
    """
    return [
        {
            "id": r["id"],
            "date": r["date"],
            "time_start": r["time_start"],
            "time_end": r["time_end"],
            "duration_minutes": int(r.get("duration_minutes") or 0),
            "activity": r["activity"],
            "category": r["category"],
            "source_contents": r.get("source_contents") or "",
            "source_timestamps": r.get("source_timestamps") or "",
            "analysis_reasoning": r.get("analysis_reasoning") or "",
            "created_at": r.get("created_at") or "",
        }
        for r in records
    ]


def render_record_report(date: str) -> dict:
    """兼容旧 CLI render-record-report — 等价于 render_record_day"""
    return render_record_day(date)


def render_records_detail(date: str, record_id: int = None) -> dict:
    """
    作息详情网页数据派生（人工智能推理溯源, 四步契约 §8 落地）.

    100% 字段暴露原则:每条作息记录的全部 11 字段都注入 payload,
      上层(HTML 模板) 自行决定渲染哪些字段、用什么样式、是否折叠。
      全部字段:id / date / time_start / time_end / duration_minutes / activity /
      category / source_contents / source_timestamps / analysis_reasoning / created_at。

    返回: {status, data: {meta, records, selected_record, ai_questions, errors, ...},
           message}
    """
    from schedule_db import _normalize_date, get_records_by_date
    from calculations import ai_questions_for_day, aggregate_by_category

    date = _normalize_date(date)
    records = get_records_by_date(date)

    full_records = [
        {
            "id": r["id"],
            "date": r["date"],
            "time_start": r["time_start"],
            "time_end": r["time_end"],
            "duration_minutes": int(r.get("duration_minutes") or 0),
            "activity": r["activity"],
            "category": r["category"],
            "source_contents": r.get("source_contents") or "",
            "source_timestamps": r.get("source_timestamps") or "",
            "analysis_reasoning": r.get("analysis_reasoning") or "",
            "created_at": r.get("created_at") or "",
        }
        for r in records
    ]

    selected = None
    if record_id is not None:
        for fr in full_records:
            if fr["id"] == record_id:
                selected = fr
                break

    cat_minutes = aggregate_by_category(records)
    total_minutes = sum(cat_minutes.values())
    sleep_records = [r for r in records if "睡眠" in r.get("category", "") or "午睡" in r.get("category", "")]
    sleep_min = max((r.get("duration_minutes") or 0 for r in sleep_records), default=0)

    dt = datetime.fromisoformat(date)
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    payload = {
        "meta": {
            "mode": "record-detail",
            "date": date,
            "record_id": record_id,
            "weekday": weekdays[dt.weekday()],
            "title": f"作息详情 · {dt.year}年{dt.month}月{dt.day}日({weekdays[dt.weekday()]})",
            "subtitle": f"共 {len(records)} 条记录 · 详情溯源 · 每条全 11 字段",
            "record_count": len(records),
            "total_minutes": int(total_minutes),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-23",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "records": full_records,
        "selected_record": selected,
        "summary_categories_count": len(cat_minutes),
        "ai_questions": ai_questions_for_day(date, [], sleep_min, total_minutes, 0),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {date} 作息详情数据已生成({len(records)} 条记录,每条含 11 字段)",
    }


def render_plans_preview(date: str, plan_events: list, locked_events: list = None) -> dict:
    """
    商量计划预览(过程型首批落地,四步契约§3.6 + 手册§原则10 过程型 AI 协同模式).

    数据契约:
      - plan_events: 候选 24h 事件 list[{time_start, time_end, title, notes, category}, ...]
      - locked_events: 已有 schedule_plans WHERE date=date AND is_active=1 list[...]

    输出:
      - status: 'ok' | 'conflict' | 'incomplete'
      - 4 部分 prompt 字符串(场景/数据/期望/来源) → 用户复制给 AI
      - 24h 覆盖率 coverage_pct
      - conflicts: 候选与 locked 时间重叠
      - copy_prompt: 完整指令文本
    """
    from schedule_db import _normalize_date, list_plan_events, validate_24h_coverage

    date = _normalize_date(date)
    locked_events = locked_events or []
    if not plan_events:
        return {
            "status": "error",
            "data": None,
            "message": f"plan_events 为空,至少需要 1 条候选事件",
        }

    # 计算 24h 覆盖率
    coverage_err = validate_24h_coverage(plan_events)
    if coverage_err is None:
        coverage_pct = 100
        coverage_status = "ok"
    else:
        # 24h 不完整,粗略计算已覆盖分钟数
        covered_minutes = 0
        for ev in plan_events:
            try:
                sh, sm = map(int, ev["time_start"].split(":"))
                eh, em = map(int, ev["time_end"].split(":"))
                ev_min = (eh * 60 + em) - (sh * 60 + sm)
                if ev_min > 0:
                    covered_minutes += ev_min
            except (KeyError, ValueError):
                pass
        coverage_pct = round(covered_minutes / 1440 * 100, 1)
        coverage_status = "incomplete"

    # 计算冲突(候选与 locked 时间重叠)
    def to_min(hhmm):
        h, m = map(int, hhmm.split(":"))
        return h * 60 + m
    conflicts = []
    for i, cand in enumerate(plan_events):
        try:
            cs, ce = to_min(cand["time_start"]), to_min(cand["time_end"])
        except (KeyError, ValueError):
            continue
        for lk in locked_events:
            try:
                ls, le = to_min(lk["time_start"]), to_min(lk["time_end"])
            except (KeyError, ValueError):
                continue
            if cs < le and ls < ce:  # 时间区间相交
                conflicts.append({
                    "time_range": cand["time_start"] + "–" + cand["time_end"],
                    "candidate": cand.get("title", "—"),
                    "locked": lk.get("title", "—"),
                    "candidate_idx": i,
                })

    # 整体状态
    if conflicts:
        status = "conflict"
    elif coverage_status == "incomplete":
        status = "incomplete"
    else:
        status = "ok"

    # 4 部分 prompt(手册§原则10)
    plan_json_str = json.dumps(plan_events, ensure_ascii=False, indent=2)
    locked_summary = ""
    if locked_events:
        locked_summary = "\n⑤ 已锁定事件(写库时锁定时段,会被保护):\n" + \
            "\n".join([f"  - {e['time_start']}–{e['time_end']} {e.get('title','—')}" for e in locked_events]) + "\n"

    conflicts_summary = ""
    if conflicts:
        conflicts_summary = "\n⚠ 检测到 " + str(len(conflicts)) + " 处候选与已锁定事件时间冲突:\n" + \
            "\n".join([f"  - {c['time_range']}: 候选「{c['candidate']}」与已锁定「{c['locked']}」重叠" for c in conflicts]) + \
            "\n请调整候选事件时段或更新已锁定事件后重新预览。\n"

    copy_prompt = f"""① 场景: 我和 AI 多轮对话生成了 {date} 的候选计划({len(plan_events)} 段事件覆盖 24h {coverage_pct}%)。{('有 ' + str(len(conflicts)) + ' 处冲突需调整') if conflicts else '无冲突'}

② 数据(候选 24h 时间块):
{plan_json_str}{locked_summary}{conflicts_summary}
③ 期望: 请执行 schedule_cli.py upsert-plan-events {date} --json @plan.json 写库;询问飞书同步(Y/n)
  - 无冲突时直接采纳
  - 有冲突时先与用户讨论调整再写

④ 来源: plan_preview.html 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")},数据来自多轮对话
"""

    payload = {
        "meta": {
            "mode": "plan-preview",
            "date": date,
            "title": f"商量计划预览 · {date}",
            "subtitle": f"候选 {len(plan_events)} 段事件 · 24h 覆盖率 {coverage_pct}% · {len(conflicts)} 处冲突" + (" · 需调整" if conflicts else ""),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "plan_events": plan_events,
        "locked_events": locked_events,
        "conflicts": conflicts,
        "coverage_pct": coverage_pct,
        "status": status,
        "copy_prompt": copy_prompt,
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {date} 商量计划预览数据已生成(候选 {len(plan_events)} 段,冲突 {len(conflicts)} 处,24h 覆盖率 {coverage_pct}%)",
    }


def render_plans_review(date: str) -> dict:
    """
    复盘报告(process-html 阶段第 2 款,手册§原则10 过程型 AI 协同模式).

    数据契约:拉取 schedule_plans WHERE date=date AND is_active=1
    输出:每条事件含 id / time_start / time_end / title / category / completion / completion_note
          + meta(已标记的 completion 预填到 userMarks)
          + 4 部分 prompt 模板骨架(前端 JS 根据用户标记动态生成)

    与 render_plans_preview 区别:
      - preview 是"写库前预览"(AI 写库前确认)
      - review 是"写库后复盘"(AI 写库后用户标 status + note)
    """
    from schedule_db import _normalize_date, list_plan_events
    from calculations import ai_questions_for_day

    date = _normalize_date(date)
    events = list_plan_events(date, include_inactive=False)  # 仅活跃

    # 标准化为模板消费的字段
    plan_events = []
    for ev in events:
        plan_events.append({
            "id": ev.get("id"),
            "date": ev.get("date"),
            "time_start": ev.get("time_start"),
            "time_end": ev.get("time_end"),
            "title": ev.get("title"),
            "category": ev.get("category"),
            "notes": ev.get("notes") or "",
            "completion": ev.get("completion"),  # 已有 completion 预填
            "completion_note": ev.get("completion_note") or "",
        })

    # 计算复盘进度
    reviewed_count = sum(1 for ev in plan_events if ev["completion"])
    total = len(plan_events)
    progress_pct = round(reviewed_count / total * 100, 1) if total > 0 else 0

    payload = {
        "meta": {
            "mode": "plan-review",
            "date": date,
            "title": f"复盘报告 · {date}",
            "subtitle": f"逐条标记状态 · 复制 4 部分 prompt 给 AI · {reviewed_count}/{total} 已标记",
            "reviewed_count": reviewed_count,
            "total_count": total,
            "progress_pct": progress_pct,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "plan_events": plan_events,
        "ai_questions": ai_questions_for_day(date, [], 0, 0, 0),  # 占位
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {date} 复盘报告数据已生成({total} 段事件,{reviewed_count} 已标记)",
    }


def render_receipt(record_id: int) -> dict:
    """
    单条 CRUD 后漂亮回执(回执型首款,用户 2026-07-23 提出 3 类型分类中的"回执型"首批落地).

    ③ 期望: AI 自主决定,不让用户选 A/B/C(2026-07-24 改进)
      - 用户复制粘贴 = 一次性动作
      - AI 收到上下文 → 自主回复(继续记/看全貌/复盘/补漏)
      - 不让用户做"选方案"决定
    """
    from schedule_db import get_record_by_id, get_records_by_date, get_records_range
    from datetime import timedelta

    record = get_record_by_id(record_id)
    if not record:
        return {
            "status": "error",
            "data": None,
            "message": f"未找到 id={record_id} 的作息记录",
        }

    date = record.get("date")
    duration = int(record.get("duration_minutes") or 0)
    category = record.get("category") or ""

    today_records = get_records_by_date(date) if date else []
    today_count = len(today_records)
    today_mins = sum(int(r.get("duration_minutes") or 0) for r in today_records)

    try:
        end_dt = datetime.fromisoformat(date)
        start_dt = end_dt - timedelta(days=6)
        week_records = get_records_range(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
        week_count = len(week_records)
    except Exception:
        week_count = today_count

    category_records = [r for r in today_records if r.get("category") == category]
    category_total = len(category_records)
    try:
        sorted_cats = sorted(category_records, key=lambda r: r.get("time_start", ""))
        category_rank = next((i + 1 for i, r in enumerate(sorted_cats) if r.get("id") == record_id), category_total)
    except Exception:
        category_rank = category_total

    record_json = json.dumps({
        "id": record.get("id"),
        "date": record.get("date"),
        "time_start": record.get("time_start"),
        "time_end": record.get("time_end"),
        "duration_minutes": duration,
        "activity": record.get("activity"),
        "category": category,
        "source_contents": record.get("source_contents") or "",
        "source_timestamps": record.get("source_timestamps") or "",
        "analysis_reasoning": record.get("analysis_reasoning") or "",
        "created_at": record.get("created_at"),
    }, ensure_ascii=False, indent=2)

    # 3 种"复制动作"prompt(2026-07-24 设计改进:取消独立"复制今日进度"按钮,
    # §1 三个操作按钮 = 3 种具体 prompt。每个按钮 = 用户决策 + AI 指令合一。)
    base_prompt = f"""① 场景: 我刚记录了一条作息(id={record_id} · {record.get('date')} {record.get('time_start')}–{record.get('time_end')} {category})

② 数据(今日进度):
  - 今日已记录 {today_count} 条,总时长 {today_mins} 分钟({today_mins // 60}h{today_mins % 60}m)
  - 本周累计 {week_count} 条(最近 7 天)
  - 在「{category}」分类中,本条排第 {category_rank} / 共 {category_total} 条
  - 刚记录:
{record_json}

④ 来源: receipt_id{record_id}_{date}.html 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")},新记录 id={record_id}
"""

    prompt_continue = base_prompt + """
③ 期望: 用户即将告诉你"我刚才在做 X"。
请调 schedule_cli.py add 写库 + 调 render-receipt <新 id> 生成下一份回执。
不要做其他事,等用户输入。"""

    prompt_overview = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-record-day {record.get('date')} 生成今日报告 HTML,
让我扫读全部记录(包含今日所有作息 + 24h 时间轴 + 分类进度)。
不要做复盘,纯展示。"""

    prompt_review = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-plans-review {record.get('date')} 生成复盘报告 HTML,
让我逐条标"已完成 / 已完成(超时) / 部分完成 / 未完成 / 未完成(不可抗力)" + 写完成原因。
完成后给我返回复盘小结(完成率 + 各类占比 + 1-2 句今日总结)。"""

    payload = {
        "meta": {
            "mode": "record-receipt",
            "title": "已记录",
            "record_id": record_id,
            "date": date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "record": record,
        "stats": {
            "today_count": today_count,
            "today_mins": today_mins,
            "week_count": week_count,
            "category": category,
            "category_rank": category_rank,
            "category_total": category_total,
        },
        "prompts": {
            "continue": prompt_continue,  # §1 按钮 1:继续记
            "overview": prompt_overview,  # §1 按钮 2:看今日全貌
            "review":   prompt_review,     # §1 按钮 3:晚点复盘
        },        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ id={record_id} 漂亮回执已生成(今日 {today_count} 条,本周 {week_count} 条)",
    }


def _calc_plan_minutes(p):
    """计算 plan_event 的时段分钟数(无效返回 0)"""
    try:
        ts = p.get("time_start") or "0:0"
        te = p.get("time_end") or "0:0"
        sh, sm = map(int, ts.split(":"))
        eh, em = map(int, te.split(":"))
        m = (eh * 60 + em) - (sh * 60 + sm)
        if m > 0:
            return m
    except Exception:
        pass
    return 0


def _calc_plan_receipt_stats(plan, today_plans):
    """render_plan_receipt 4 款公共 stats 派生(2026-07-24 提取)"""
    today_count = len(today_plans)
    completed_count = sum(1 for p in today_plans if p.get("completion") and p["completion"] != "未完成")
    note_count = sum(1 for p in today_plans if p.get("completion_note"))
    completion_rate = round(completed_count / today_count * 100) if today_count > 0 else 0
    feishu_synced = sum(1 for p in today_plans if p.get("feishu_event_id"))
    coverage_minutes = sum(_calc_plan_minutes(p) for p in today_plans if p.get("is_active", 1) == 1)
    coverage_hours = round(coverage_minutes / 60, 1)
    return {
        "today_count": today_count,
        "completed_count": completed_count,
        "note_count": note_count,
        "completion_rate": completion_rate,
        "feishu_synced": feishu_synced,
        "coverage_hours": coverage_hours,
    }


def _build_plan_json(plan):
    """render_plan_receipt 4 款公共 plan_json 拼装(13 字段)"""
    return json.dumps({
        "id": plan.get("id"),
        "date": plan.get("date"),
        "time_start": plan.get("time_start"),
        "time_end": plan.get("time_end"),
        "title": plan.get("title"),
        "notes": plan.get("notes") or "",
        "category": plan.get("category") or "",
        "feishu_event_id": plan.get("feishu_event_id"),
        "last_synced_at": plan.get("last_synced_at"),
        "is_active": plan.get("is_active", 1),
        "completion": plan.get("completion"),
        "completion_note": plan.get("completion_note") or "",
    }, ensure_ascii=False, indent=2)


def _build_plan_receipt_base_prompt(plan_id, plan, stats, plan_json, action_verb_zh, action_label_zh, file_action):
    """render_plan_receipt 4 款公共 base_prompt 构造"""
    date = plan.get("date", "")
    return f"""① 场景: 我刚"{action_verb_zh}"了一条计划(id={plan_id} · {date} {plan.get("time_start")}–{plan.get("time_end")} {plan.get("title")})

② 数据(今日计划概况):
  - 今日共 {stats["today_count"]} 条计划(完成 {stats["completed_count"]} 条,完成率 {stats["completion_rate"]}%)
  - 飞书已同步 {stats["feishu_synced"]} 条
  - 24h 覆盖率 {stats["coverage_hours"]} 小时
  - 刚"{action_label_zh}":
{plan_json}

④ 来源: plan_receipt_{file_action}_id{plan_id}_{date}.html 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")},操作 action={file_action}
"""





def render_plan_receipt(plan_id: int, action: str = "update") -> dict:
    """改/删计划回执(回执型第2款,2026-07-24,复用 #0 漂亮回执模式)."""
    from schedule_db import get_plan_event, list_plan_events

    plan = get_plan_event(plan_id)
    if not plan:
        return {"status": "error", "data": None, "message": f"未找到 id={plan_id} 的计划事件"}

    date = plan.get("date")
    today_plans = list_plan_events(date, include_inactive=(action == "deactivate"))
    stats = _calc_plan_receipt_stats(plan, today_plans)
    plan_json = _build_plan_json(plan)

    action_verb_zh = "修改" if action == "update" else "软删"
    base_prompt = _build_plan_receipt_base_prompt(plan_id, plan, stats, plan_json, action_verb_zh, action_verb_zh, action)

    prompt_adjust = base_prompt + f"""
③ 期望: 用户即将告诉你修改内容(改时间/改标题/补备注/改分类)。
请调 schedule_cli.py update-event {plan_id} <字段> <值> 写库。
不要做其他事,等用户输入。"""

    prompt_overview = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-list-events {date} 生成今日所有计划 HTML,
让我扫读今日全部计划(包含所有状态 + 飞书同步状态)。
不要做复盘,纯展示。"""

    prompt_review = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-plans-review {date} 生成复盘报告 HTML,
让我逐条标"已完成 / 已完成(超时) / 部分完成 / 未完成 / 未完成(不可抗力)" + 写完成原因。
完成后给我返回复盘小结(完成率 + 各类占比 + 1-2 句今日总结)。"""

    payload = {
        "meta": {
            "mode": "plan-receipt",
            "title": "已" + ("修改" if action == "update" else "删除"),
            "action": action,
            "plan_id": plan_id, "date": date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "plan": plan, "stats": stats,
        "prompts": {"adjust": prompt_adjust, "overview": prompt_overview, "review": prompt_review},
        "errors": [],
    }
    return {
        "status": "ok", "data": payload,
        "message": f"✓ id={plan_id} 计划 {action_verb_zh}回执已生成(今日 {stats['today_count']} 条计划,完成率 {stats['completion_rate']}%)",
    }


def render_plan_receipt_add(plan_id: int) -> dict:
    """补计划回执(回执型第 3 款,2026-07-24,绿色调)."""
    from schedule_db import get_plan_event, list_plan_events

    plan = get_plan_event(plan_id)
    if not plan:
        return {"status": "error", "data": None, "message": f"未找到 id={plan_id} 的计划事件"}

    date = plan.get("date")
    today_plans = list_plan_events(date, include_inactive=True) if date else []
    stats = _calc_plan_receipt_stats(plan, today_plans)
    plan_json = _build_plan_json(plan)
    base_prompt = _build_plan_receipt_base_prompt(plan_id, plan, stats, plan_json, "补", "补", "add")

    prompt_continue = base_prompt + """
③ 期望: 用户即将告诉你"继续补下一条"。
请调 schedule_cli.py ensure-plan-event <新日期> <新时段> --title "..." --category "..." 写库。
不要做其他事,等用户输入。"""

    prompt_overview = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-list-events {date} 生成今日所有计划 HTML,
让我扫读今日全部计划(包含所有状态 + 飞书同步状态)。
不要做复盘,纯展示。"""

    prompt_review = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-plans-review {date} 生成复盘报告 HTML,
让我逐条标"已完成 / 已完成(超时) / 部分完成 / 未完成 / 未完成(不可抗力)" + 写完成原因。
完成后给我返回复盘小结(完成率 + 各类占比 + 1-2 句今日总结)。"""

    payload = {
        "meta": {
            "mode": "plan-receipt-add", "title": "已补计划",
            "plan_id": plan_id, "date": date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "plan": plan, "stats": stats,
        "prompts": {"continue": prompt_continue, "overview": prompt_overview, "review": prompt_review},
        "errors": [],
    }
    return {
        "status": "ok", "data": payload,
        "message": f"✓ id={plan_id} 计划 已补回执已生成(今日 {stats['today_count']} 条计划,完成率 {stats['completion_rate']}%)",
    }


def render_plan_receipt_write(plan_id: int) -> dict:
    """写摘要回执(回执型第 4 款,2026-07-24,紫色调,与 update 同源)."""
    from schedule_db import get_plan_event, list_plan_events

    plan = get_plan_event(plan_id)
    if not plan:
        return {"status": "error", "data": None, "message": f"未找到 id={plan_id} 的计划事件"}

    date = plan.get("date")
    today_plans = list_plan_events(date, include_inactive=True) if date else []
    stats = _calc_plan_receipt_stats(plan, today_plans)
    plan_json = _build_plan_json(plan)
    base_prompt = _build_plan_receipt_base_prompt(plan_id, plan, stats, plan_json, "写摘要", "写摘要", "write")

    prompt_continue = base_prompt + """
③ 期望: 用户即将告诉你"继续写另一条摘要"。
请调 schedule_cli.py update-event <新 id> --completion X --completion-note "Y"。
不要做其他事,等用户输入。"""

    prompt_overview = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-plans-review {date} 生成复盘报告 HTML,
让我扫读所有事件(已标完成 + 未完成),继续标剩余事件。
不要做其他事,纯展示 + 让我标。"""

    prompt_look_all = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-list-events {date} 生成今日所有计划 HTML,
让我扫读今日全部计划(包含所有状态 + 飞书同步状态)。
不要做复盘,纯展示。"""

    payload = {
        "meta": {
            "mode": "plan-receipt-write", "title": "已写摘要",
            "plan_id": plan_id, "date": date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "plan": plan, "stats": stats,
        "prompts": {"continue": prompt_continue, "overview": prompt_overview, "look_all": prompt_look_all},
        "errors": [],
    }
    return {
        "status": "ok", "data": payload,
        "message": f"✓ id={plan_id} 计划 已写摘要回执已生成(今日 {stats['today_count']} 条计划,完成率 {stats['completion_rate']}%,已写反思 {stats['note_count']} 条)",
    }


# ===== 5 模板数据派生函数(T1~T5,2026-07-23 升级)=====

def render_record_day(date: str) -> dict:
    """T1 单日:4 卡摘要 + 24h 时间轴 + 分类进度 + 睡眠分析 + 健康分 + AI 钩子"""
    from schedule_db import _normalize_date, get_records_by_date
    from calculations import (
        aggregate_by_category, build_hourly_dominant, compute_health_score,
        ai_questions_for_day,
    )

    date = _normalize_date(date)
    records = get_records_by_date(date)
    cat_minutes = aggregate_by_category(records)
    total_minutes = sum(cat_minutes.values())

    sorted_cats = sorted(cat_minutes.items(), key=lambda x: -x[1])
    summary_items = [
        {
            "category": cat, "emoji": _cat_emoji(cat), "color": _cat_color(cat),
            "total_minutes": int(mins), "duration_text": _fmt_dur(int(mins)),
            "pct": round((mins / total_minutes * 100) if total_minutes else 0.0, 1),
        }
        for cat, mins in sorted_cats
    ]

    hour_dominant = build_hourly_dominant(records)
    timeline = [
        {"hour": h["hour"], "category": h["dominant_cat"],
         "color": _cat_color(h["dominant_cat"]),
         "tip": f"{h['hour']:02d}:00 {h['dominant_cat']}"}
        for h in hour_dominant
    ]

    sleep_records = [r for r in records
                    if "睡眠" in r.get("category", "") or "午睡" in r.get("category", "")]
    main_sleep = max(sleep_records, key=lambda r: r.get("duration_minutes") or 0) if sleep_records else None
    sleep_data = {
        "total_records": len(sleep_records),
        "main_sleep": (
            {
                "time_start": main_sleep["time_start"],
                "time_end": main_sleep["time_end"],
                "duration_minutes": int(main_sleep.get("duration_minutes") or 0),
                "duration_text": _fmt_dur(int(main_sleep.get("duration_minutes") or 0)),
                "category": main_sleep.get("category"),
                "color": _cat_color(main_sleep.get("category", "睡眠")),
            } if main_sleep else None
        ),
        "is_sufficient": (main_sleep.get("duration_minutes") or 0) >= 7 * 60 if main_sleep else False,
    }
    sleep_min = main_sleep.get("duration_minutes") or 0 if main_sleep else 0

    dt = datetime.fromisoformat(date)
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    payload = {
        "meta": {
            "mode": "record-day",
            "date": date,
            "weekday": weekdays[dt.weekday()],
            "title": f"作息报告 · {dt.year}年{dt.month}月{dt.day}日({weekdays[dt.weekday()]})",
            "subtitle": f"共 {len(records)} 条记录,总时长 {_fmt_dur(total_minutes)}",
            "record_count": len(records),
            "total_minutes": int(total_minutes),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "summary_items": summary_items,
        "timeline": timeline,
        "sleep_data": sleep_data,
        "records": _build_full_records(records),
        "health": {
            "score": compute_health_score(records),
            "label": "充足" if sleep_min >= 7*60 else ("偏短" if sleep_min >= 5*60 else "严重不足"),
        },
        "ai_questions": ai_questions_for_day(date, summary_items, sleep_min, total_minutes, compute_health_score(records)),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {date} 单日报告数据已生成",
    }


def render_record_range(start: str, end: str) -> dict:
    """T2 区间:4 卡摘要 + 7 维趋势 SVG + 分类进度 + 健康分 + AI 钩子"""
    from schedule_db import _normalize_date, get_records_range
    from calculations import (
        aggregate_by_category, build_dimension_aggregates, build_trend_series,
        compute_health_score, ai_questions_for_range,
    )
    import math

    start = _normalize_date(start)
    end = _normalize_date(end)
    records = get_records_range(start, end)
    days = sorted({r.get("date", "") for r in records})
    days_count = len(days)

    dim_totals = build_dimension_aggregates(records)
    cat_minutes = aggregate_by_category(records)
    total = sum(dim_totals.values())

    sorted_cats = sorted(cat_minutes.items(), key=lambda x: -x[1])
    summary_items = [
        {
            "category": cat, "emoji": _cat_emoji(cat), "color": _cat_color(cat),
            "total_minutes": int(mins), "duration_text": _fmt_dur(int(mins)),
            "pct": round((mins / total * 100) if total else 0.0, 1),
        }
        for cat, mins in sorted_cats
    ]

    # 7 维趋势 SVG
    HEALTH_DIMS = ["维持", "健康", "工作", "学习", "调整", "日常", "投入"]
    colors = {"维持":"#5E5CE6","健康":"#FF9500","工作":"#007AFF","学习":"#34C759","调整":"#30D158","日常":"#8E8E93","投入":"#FF2D55"}
    series = {d: build_trend_series(records, d) for d in HEALTH_DIMS}
    max_y = max((s["mins"] for arr in series.values() for s in arr), default=1) or 1
    width, height = 640, 130
    n = max(1, days_count)
    step_x = (width - 40) / max(1, n - 1) if n > 1 else 0
    svg_lines = [f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">']
    for d in HEALTH_DIMS:
        arr = series[d]
        if not arr:
            continue
        pts = []
        for i, pt in enumerate(arr):
            x = 20 + i * step_x
            y = height - 10 - (pt["mins"] / max_y * (height - 30))
            pts.append(f"{x:.1f},{y:.1f}")
        svg_lines.append(f'<polyline class="line" stroke="{colors[d]}" points="{" ".join(pts)}"/>')
    if days:
        for i in [0, len(days) - 1]:
            if 0 <= i < len(days):
                x = 20 + i * step_x
                svg_lines.append(f'<text class="axis" x="{x:.1f}" y="{height-2}" text-anchor="{"start" if i==0 else "end"}">{days[i][5:]}</text>')
    svg_lines.append('</svg>')
    trend_chart = "".join(svg_lines)

    health = {"score": compute_health_score(records), "label": ""}
    payload = {
        "meta": {
            "mode": "record-range",
            "start": start, "end": end, "days": days_count,
            "title": f"作息区间报告 · {start} ~ {end}",
            "subtitle": f"{days_count} 天,{len(records)} 条记录,总时长 {_fmt_dur(total)}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "days": days,
        "summary_items": summary_items,
        "dim_totals": dim_totals,
        "total_records": len(records),
        "records": _build_full_records(records),
        "trend_chart": trend_chart,
        "health": health,
        "ai_questions": ai_questions_for_range(start, end, dim_totals, health["score"], 0),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {start} ~ {end} 区间报告数据已生成",
    }


def render_record_compare(label_a: str, start_a: str, end_a: str, label_b: str, start_b: str, end_b: str) -> dict:
    """T3 对比:2 段 A/B 7 维差异柱"""
    from schedule_db import _normalize_date, get_records_range
    from calculations import build_compare_aggregates, build_diff_table, ai_questions_for_compare
    from datetime import date as _d

    start_a = _normalize_date(start_a)
    end_a = _normalize_date(end_a)
    start_b = _normalize_date(start_b)
    end_b = _normalize_date(end_b)
    recs_a = get_records_range(start_a, end_a)
    recs_b = get_records_range(start_b, end_b)
    days_a = (_d.fromisoformat(end_a) - _d.fromisoformat(start_a)).days + 1
    days_b = (_d.fromisoformat(end_b) - _d.fromisoformat(start_b)).days + 1
    ranges = build_compare_aggregates([
        {"label": label_a, "start": start_a, "end": end_a, "days": days_a, "records": recs_a},
        {"label": label_b, "start": start_b, "end": end_b, "days": days_b, "records": recs_b},
    ])
    diffs = build_diff_table(ranges[0], ranges[1])
    payload = {
        "meta": {
            "mode": "record-compare",
            "title": f"作息对比 · {label_a} vs {label_b}",
            "subtitle": f"{label_a}:{start_a}~{end_a} · {label_b}:{start_b}~{end_b}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "ranges": ranges,
        "diffs": diffs,
        "ai_questions": ai_questions_for_compare(ranges, diffs),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ 对比 {label_a} vs {label_b} 数据已生成",
    }


def render_record_category(category: str, start: str, end: str) -> dict:
    """T4 类别深挖:24h × N 天 热力图"""
    from schedule_db import _normalize_date, get_records_range
    from calculations import l1_of, ai_questions_for_category

    start = _normalize_date(start)
    end = _normalize_date(end)
    records = get_records_range(start, end)
    l1_target = l1_of(category)
    cat_records = [r for r in records if l1_of(r.get("category", "")) == l1_target]
    total = sum(r.get("duration_minutes") or 0 for r in cat_records)
    days = sorted({r.get("date", "") for r in cat_records})
    days_count = len(days)
    daily_avg = round(total / days_count, 1) if days_count else 0  # L8 修复:整数除法丢精度

    by_date: dict[str, list[dict]] = {}
    for r in cat_records:
        by_date.setdefault(r.get("date", ""), []).append(r)
    sorted_dates = sorted(by_date.keys())
    matrix = []
    for d in sorted_dates:
        hour_mins = [0] * 24
        for r in by_date[d]:
            s_min = _to_min(r.get("time_start", ""))
            e_min = _to_min(r.get("time_end", ""))
            if e_min <= s_min:
                continue
            cur = s_min
            while cur < e_min:
                h = cur // 60
                if 0 <= h < 24:
                    nh = (h + 1) * 60
                    covered = min(nh, e_min) - cur
                    if covered > 0:
                        hour_mins[h] += covered
                cur += 60
        row = []
        for h in range(24):
            if hour_mins[h] > 0:
                row.append({"cat": l1_target, "mins": hour_mins[h], "color": _cat_color(l1_target)})
            else:
                row.append({"cat": None, "mins": 0, "color": "#f5f5f7"})
        matrix.append(row)

    payload = {
        "meta": {
            "mode": "record-category",
            # M5:用户原值 (category) + 映射后值 (l1_target) 都写 meta,文件名前缀用原值
            "category": category,         # 用户原值 "运动" → 文件名 "运动_..."
            "l1_category": l1_target,    # 映射后值 "健康" → 内部过滤用
            "start": start, "end": end,
            "title": f"类别深挖 · {l1_target} · {start} ~ {end}",
            "subtitle": f"{days_count} 天活跃,日均 {_fmt_dur(daily_avg)}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "days": sorted_dates,
        "total_minutes": total,
        "daily_avg": daily_avg,
        "heatmap": matrix,
        "records": _build_full_records(cat_records),
        "ai_questions": ai_questions_for_category(l1_target, days_count, total, daily_avg),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {l1_target} 类别深挖数据已生成",
    }


def render_record_anomaly(window_days: int = 7) -> dict:
    """T5 异常:默认 7 天 vs 近 30 天基线 + 7 维雷达 SVG"""
    from schedule_db import get_records_range
    from calculations import detect_anomalies, build_dimension_aggregates, ai_questions_for_anomaly
    from datetime import date as _d, timedelta as _td
    import math

    today = _d.today()
    window_start = (today - _td(days=window_days - 1)).isoformat()
    today_iso = today.isoformat()
    baseline_start = (today - _td(days=30)).isoformat()

    cur_records = get_records_range(window_start, today_iso)
    baseline_records = get_records_range(baseline_start, today_iso)

    anomalies = detect_anomalies(cur_records, baseline_records, threshold=0.2)

    HEALTH_DIMS = ["维持", "健康", "工作", "学习", "调整", "日常", "投入"]
    cur = build_dimension_aggregates(cur_records)
    base = build_dimension_aggregates(baseline_records)
    cx, cy, r = 200, 200, 130
    n = len(HEALTH_DIMS)
    svg = [f'<svg class="radar-svg" viewBox="0 0 400 420">']
    for r2 in [0.2, 0.4, 0.6, 0.8, 1.0]:
        pts = []
        for i in range(n):
            a = -math.pi/2 + i * 2*math.pi/n
            pts.append(f"{cx + r*r2*math.cos(a):.1f},{cy + r*r2*math.sin(a):.1f}")
        svg.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="#d2d2d7" stroke-width="0.5"/>')
    for i, d in enumerate(HEALTH_DIMS):
        a = -math.pi/2 + i * 2*math.pi/n
        x2, y2 = cx + r*math.cos(a), cy + r*math.sin(a)
        svg.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#d2d2d7" stroke-width="0.5"/>')
        svg.append(f'<text class="radar-axis" x="{x2:.1f}" y="{y2:.1f}" text-anchor="middle" dy="4">{d}</text>')
    pts_curr, pts_base = [], []
    max_v = max(max(cur.values(), default=1), max(base.values(), default=1), 1)
    for i, d in enumerate(HEALTH_DIMS):
        a = -math.pi/2 + i * 2*math.pi/n
        vc = cur.get(d, 0) / max_v
        vb = base.get(d, 0) / max_v
        pts_curr.append(f"{cx + r*vc*math.cos(a):.1f},{cy + r*vc*math.sin(a):.1f}")
        pts_base.append(f"{cx + r*vb*math.cos(a):.1f},{cy + r*vb*math.sin(a):.1f}")
    svg.append(f'<polygon points="{" ".join(pts_base)}" fill="#8E8E93" fill-opacity="0.2" stroke="#8E8E93" stroke-width="1"/>')
    svg.append(f'<polygon points="{" ".join(pts_curr)}" fill="#007AFF" fill-opacity="0.3" stroke="#007AFF" stroke-width="2"/>')
    svg.append('<text x="200" y="395" text-anchor="middle" font-size="11" fill="#6e6e73">蓝=当前 | 灰=基线(30天)</text>')
    svg.append('</svg>')
    radar_svg = "".join(svg)

    payload = {
        "meta": {
            "mode": "record-anomaly",
            "window": window_days,
            "title": f"异常检测 · 最近 {window_days} 天",
            "subtitle": f"对比基线:近 30 天均值,阈值 ±20%",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "anomalies": anomalies,
        "radar_svg": radar_svg,
        "ai_questions": ai_questions_for_anomaly(anomalies, window_days),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ 异常检测完成,检出 {len(anomalies)} 项",
    }


def render_and_write(payload: dict, output_path: Path = None) -> dict:
    """渲染 + 写入文件,返回 {status, data:{file_path, bytes}, message}"""
    template_map = {
        "list-events":     "schedule_list_events.html",
        "query-plans":     "schedule_list_events.html",
        "plan-preview":    "schedule_plan_preview.html",  # 商量计划预览(过程型首批落地,2026-07-24)
        "plan-review":     "schedule_plan_review.html",   # 复盘报告(过程型第2款,2026-07-24)
        "record-receipt":  "schedule_record_receipt.html", # 漂亮回执(回执型首款,2026-07-24)
        "plan-receipt":     "schedule_plan_receipt.html",   # 改/删计划回执(回执型第2款,2026-07-24)
        "plan-receipt-add": "schedule_plan_receipt_add.html", # 补计划回执(回执型第3款,2026-07-24)
        "plan-receipt-write": "schedule_plan_receipt_write.html", # 写摘要回执(回执型第4款,2026-07-24)
        "record-report":   "schedule_record_day.html",   # 兼容旧 CLI
        "record-day":      "schedule_record_day.html",
        "record-range":    "schedule_record_range.html",
        "record-compare":  "schedule_record_compare.html",
        "record-category": "schedule_record_category.html",
        "record-anomaly":  "schedule_record_anomaly.html",
        "record-detail":   "schedule_record_detail.html",  # 详情页(人工智能推理溯源)
    }
    mode = payload.get("data", {}).get("meta", {}).get("mode", "list-events")
    template_name = template_map.get(mode)
    if not template_name:
        return {
            "status": "error",
            "data": None,
            "message": f"未知 mode: {mode}",
        }

    if output_path is None:
        output_path = default_output_path(payload["data"]["meta"])

    try:
        final_path = inject_into_template(template_name, payload, output_path)
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"渲染失败: {type(e).__name__}: {e}",
        }

    size_kb = final_path.stat().st_size // 1024
    return {
        "status": "ok",
        "data": {
            "file_path": str(final_path),
            "size_kb": size_kb,
            "mode": mode,
        },
        "message": f"✓ HTML 已写入: {final_path} ({size_kb} KB)",
    }


if __name__ == "__main__":
    print("schedule_html_render.py — 渲染器模块")
    print("用法: 由 schedule_cli.py 的 render-list-events / render-query-plans / render-record-report 调用")
    print("直接运行无副作用")
