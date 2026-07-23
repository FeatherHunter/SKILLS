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

      <SKILLS_DB_PATH>/schedule_html/record/<date>_record_report.html
      <SKILLS_DB_PATH>/schedule_html/plan/list/plan_list_<date>.html
      <SKILLS_DB_PATH>/schedule_html/plan/query/plan_query_<date>[_to_<date>].html

    规则来源:SKILL.md §3.x HTML 命名规则(2026-07-23 重构版)
    上一版本写到 SKILL_DIR/reports/,已被一刀删除,从此统一到 SKILLS_DB_PATH 下。
    """
    mode = meta.get("mode", "list-events")
    base = _html_base_dir()
    plan_list = base / 'plan' / 'list'
    plan_query = base / 'plan' / 'query'
    record = base / 'record'

    if mode == "list-events":
        date = meta.get("date", "unknown")
        return plan_list / f"plan_list_{date}.html"
    if mode == "query-plans":
        dates = meta.get("dates", [])
        if len(dates) == 1:
            return plan_query / f"plan_query_{dates[0]}.html"
        return plan_query / f"plan_query_{dates[0]}_to_{dates[-1]}.html"
    if mode == "record-report":
        date = meta.get("date", "unknown")
        return record / f"{date}_record_report.html"
    return base / "view.html"


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


def render_record_report(date: str) -> dict:
    """
    作息记录单日 HTML 报告 — 4 段结构(时间分配/24h色带/AI亮点占位/睡眠分析)
    视觉严格沿用历史 _render_report_2026-07-02.py 的 CSS 与布局
    数据从 schedule_records 现读 + 实时聚合(替代原 /tmp/report_data.json 中间文件)
    """
    from collections import defaultdict
    from schedule_db import _normalize_date, get_records_by_date

    date = _normalize_date(date)

    # 1. 取该日全部记录
    records = get_records_by_date(date)

    # 2. 计算 cat_minutes(分类聚合时长)— 沿用 _gen_report 算法
    cat_minutes: dict[str, int] = defaultdict(int)
    for r in records:
        cat_minutes[r["category"]] += r.get("duration_minutes") or 0
    total_minutes = sum(cat_minutes.values())

    # 3. 24h 时间轴(每条按分钟切片到小时桶,取主导分类)
    #    沿用 _render_report_2026-07-02.py:79-118 算法
    hour_minutes = [defaultdict(int) for _ in range(24)]
    hour_min_count = [0 for _ in range(24)]  # 该小时实际记录数
    hour_first_cat = [None for _ in range(24)]  # 该小时首条记录的分类
    for r in records:
        ts = r["time_start"]
        te = r["time_end"]
        if not ts or not te:
            continue
        h_start = _to_min(ts) // 60
        e_min = _to_min(te)
        if e_min <= _to_min(ts):
            continue  # 跨日跳过
        cat = r["category"]
        # 切片到小时桶
        cur = _to_min(ts)
        while cur < e_min:
            h = cur // 60
            if 0 <= h < 24:
                next_hour = (h + 1) * 60
                covered = min(next_hour, e_min) - cur
                hour_minutes[h][cat] += covered
                if hour_first_cat[h] is None:
                    hour_first_cat[h] = cat
                hour_min_count[h] += 1
            cur += 60
            if covered <= 0:
                cur = next_hour
    hour_cats = []
    for h in range(24):
        if hour_minutes[h]:
            dominant = max(hour_minutes[h].items(), key=lambda x: x[1])[0]
        elif hour_first_cat[h]:
            dominant = hour_first_cat[h]
        else:
            dominant = "休息"
        hour_cats.append(dominant)

    # 4. 睡眠分析(沿用 _gen_report 算法)— 过滤 category="睡眠"/"睡眠(超时)"
    sleep_records = [
        r for r in records
        if str(r.get("category", "")).startswith("睡眠") or str(r.get("category", "")) in ("午睡",)
    ]
    main_sleep = None
    if sleep_records:
        # 取时长最长的(原 _gen_report 用 real_duration,这里 duration_minutes 等价)
        sleep_sorted = sorted(sleep_records, key=lambda r: r.get("duration_minutes") or 0, reverse=True)
        main_sleep = sleep_sorted[0]

    # 5. 组装 summary_items(按时长倒序,与历史报告一致)
    sorted_cats = sorted(cat_minutes.items(), key=lambda x: -x[1])
    summary_items = []
    for cat, mins in sorted_cats:
        pct = (mins / total_minutes * 100) if total_minutes else 0.0
        summary_items.append({
            "category": cat,
            "emoji": _cat_emoji(cat),
            "color": _cat_color(cat),
            "total_minutes": int(mins),
            "duration_text": _fmt_dur(int(mins)),
            "pct": round(pct, 1),
        })

    # 6. timeline[24]
    timeline = []
    for h in range(24):
        timeline.append({
            "hour": h,
            "category": hour_cats[h],
            "color": _cat_color(hour_cats[h]),
            "tip": f"{h:02d}:00 {hour_cats[h]}",
        })

    # 7. sleep_data(给模板睡眠分析卡片用)
    sleep_data = {
        "total_records": len(sleep_records),
        "main_sleep": (
            {
                "time_start": main_sleep["time_start"],
                "time_end": main_sleep["time_end"],
                "duration_minutes": int(main_sleep.get("duration_minutes") or 0),
                "duration_text": _fmt_dur(int(main_sleep.get("duration_minutes") or 0)),
                "category": main_sleep.get("category"),
            }
            if main_sleep else None
        ),
        "is_sufficient": (main_sleep.get("duration_minutes") or 0) >= 7 * 60 if main_sleep else False,
    }

    # 8. meta
    payload = {
        "meta": {
            "mode": "record-report",
            "date": date,
            "record_count": len(records),
            "total_minutes": int(total_minutes),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "summary_items": summary_items,
        "timeline": timeline,
        "sleep_data": sleep_data,
        "highlights": [],   # 第 ③ 段默认空(本次不做 AI 叙事亮点)
        "errors": [],
    }

    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {date} 作息记录渲染数据已生成({len(records)} 条,共 {total_minutes // 60}h{total_minutes % 60}m)",
    }


def render_and_write(payload: dict, output_path: Path = None) -> dict:
    """渲染 + 写入文件,返回 {status, data:{file_path, bytes}, message}"""
    template_map = {
        "list-events": "schedule_list_events.html",
        "query-plans": "schedule_list_events.html",
        "record-report": "schedule_record_report.html",
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
