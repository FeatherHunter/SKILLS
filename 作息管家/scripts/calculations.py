#!/usr/bin/env python3
"""
shared/calculations.py — 作息记录 HTML 报告共享派生函数(2026-07-23 新增)

设计原则(来自 SKILL五层 + 预置 HTML 手册):
- 数据层隔离: 只调 schedule_db,不动 SQL
- 纯函数: 无副作用,可单元测试
- 一级词表稳定: 8 个固定(L1_KEYS),二级词用白名单
- 算法沿用历史 _gen_report_*.py 的 13 维度派生(meal_records / leisure_records / ...)
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any


# ===== L1 一级词固定表(8 个 + 7 维核心维度)=====
# 注:7 维核心维度 = 8 L1 中除「其他/未知」外的 7 个,用于健康分计算
L1_KEYS = ["维持", "健康", "工作", "学习", "创作", "投入", "调整", "日常"]
# 7 维核心维度(健康分计算)
HEALTH_DIMS = ["维持", "健康", "工作", "学习", "调整", "日常", "投入"]


# ===== 健康阈值(通用推荐,Phase 2 可改用户级)=====
HEALTH_TARGETS = {
    # 一级: 每日推荐分钟
    "维持":  10 * 60,  # 维持类(睡眠/用餐)10h
    "健康":  60,       # 运动 ≥1h
    "工作":  8 * 60,   # 工作 ≤8h(超过扣分)
    "学习":  60,
    "调整":  2 * 60,   # 调整 2h(够休息)
    "日常":  2 * 60,
    "投入":  60,
}


# ===== 颜色与 emoji(沿用 _render_report_*.py + 补全 8 L1)=====
COLOR_MAP = {
    "维持": "#5E5CE6", "健康": "#FF9500", "工作": "#007AFF",
    "学习": "#34C759", "创作": "#AF52DE", "投入": "#FF2D55",
    "调整": "#30D158", "日常": "#8E8E93",
    # 兼容旧词
    "睡眠": "#5E5CE6", "运动": "#FF9500", "通勤": "#64D2FF",
    "餐饮": "#FF9F0A", "娱乐": "#AF52DE", "社交": "#FF2D55",
    "休闲": "#30D158", "健康": "#FF3B30", "洗漱": "#5AC8FA",
    "兴趣爱好": "#BF8F5F", "家务": "#A2845E", "未知": "#8E8E93",
    "休息": "#8E8E93", "起居": "#8E8E93", "计划": "#FF6B9D",
    "做饭": "#FF9F0A", "饮食": "#FF9F0A", "采购": "#FF9F0A",
    "就医": "#FF3B30", "护肤": "#FF3B30",
    "健身": "#FF9500", "修行": "#FF9500", "冥想": "#FF9500",
    "AI调优": "#007AFF", "开发": "#007AFF", "技术": "#007AFF",
    "散步": "#34C759", "午睡": "#5E5CE6",
    "游戏": "#AF52DE", "手机": "#AF52DE",
    "代办": "#A2845E", "杂事": "#A2845E", "收拾": "#A2845E", "行政": "#A2845E",
}

EMOJI_MAP = {
    "维持": "🌱", "健康": "💪", "工作": "💼",
    "学习": "📚", "创作": "🎨", "投入": "🤝",
    "调整": "😌", "日常": "📋",
    # 兼容旧词
    "睡眠": "😴", "运动": "🏋️", "通勤": "🚴",
    "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
    "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿",
    "兴趣爱好": "🎨", "家务": "🧹", "未知": "❓",
    "休息": "📌", "起居": "🪥", "计划": "📋",
    "做饭": "🍳", "饮食": "🍽️", "采购": "🛒",
    "就医": "💊", "护肤": "💆",
    "健身": "🏋️", "修行": "🧘", "冥想": "🧠",
    "AI调优": "🤖", "开发": "💻", "技术": "💻",
    "散步": "🚶", "午睡": "😴",
    "游戏": "🎮", "手机": "📱",
    "代办": "☑️", "杂事": "🔧", "收拾": "🧹", "行政": "📑",
}


def l1_of(category: str) -> str:
    """'工作.AI调优' -> '工作',  '工作·AI 配置' -> '工作',  '睡眠' -> '睡眠'
    兼容两种分隔符:英文点 . 与中文间隔号 · (U+00B7)
    """
    if not category:
        return "未知"
    for sep in (".", "·", "・", "•"):
        if sep in category:
            return category.split(sep)[0]
    return category


def cat_emoji(cat: str) -> str:
    return EMOJI_MAP.get(cat, EMOJI_MAP.get(l1_of(cat), "📌"))


def cat_color(cat: str) -> str:
    return COLOR_MAP.get(cat, COLOR_MAP.get(l1_of(cat), "#8E8E93"))


def fmt_dur(mins: int) -> str:
    if mins <= 0:
        return "0分钟"
    h, m = mins // 60, mins % 60
    if h and m:
        return f"{h}小时{m}分钟"
    if h:
        return f"{h}小时"
    return f"{m}分钟"


def fmt_dur_short(mins: int) -> str:
    h, m = mins // 60, mins % 60
    if h and m:
        return f"{h}h{m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def fmt_pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round(part / whole * 100, 1)


def hhmm_to_min(hhmm: str) -> int:
    if not hhmm:
        return 0
    if hhmm == "24:00":
        return 24 * 60
    try:
        h, m = hhmm.split(":")[:2]
        return int(h) * 60 + int(m)
    except (ValueError, AttributeError):
        return 0


# ===== 核心派生 =====

def aggregate_by_category(records: list[dict]) -> dict[str, int]:
    """records → {category: total_minutes}"""
    out: dict[str, int] = defaultdict(int)
    for r in records:
        out[r.get("category", "未知")] += r.get("duration_minutes") or 0
    return dict(out)


def aggregate_by_l1(records: list[dict]) -> dict[str, int]:
    """按一级分类聚合(支持'8.70'复合键)"""
    out: dict[str, int] = defaultdict(int)
    for r in records:
        out[l1_of(r.get("category", ""))] += r.get("duration_minutes") or 0
    return dict(out)


def build_hourly_dominant(records: list[dict]) -> list[dict]:
    """每条按分钟切片到 24 个小时桶,取主导分类 + 占比分布
    返回: [{hour, dominant_cat, dominant_mins, segments: [{cat, mins, pct, color}], records_count}]
    """
    hour_mins: list[dict[str, int]] = [defaultdict(int) for _ in range(24)]
    hour_recs: list[list[str]] = [[] for _ in range(24)]
    for r in records:
        ts = r.get("time_start")
        te = r.get("time_end")
        if not ts or not te:
            continue
        s_min = hhmm_to_min(ts)
        e_min = hhmm_to_min(te)
        if e_min <= s_min:
            continue
        cat = r.get("category", "未知")
        cur = s_min
        while cur < e_min:
            h = cur // 60
            if 0 <= h < 24:
                next_hour = (h + 1) * 60
                covered = min(next_hour, e_min) - cur
                if covered > 0:
                    hour_mins[h][cat] += covered
                    if cat not in hour_recs[h]:
                        hour_recs[h].append(cat)
                cur = next_hour if covered <= 0 else cur + 60
            else:
                break
    out = []
    for h in range(24):
        if hour_mins[h]:
            total = sum(hour_mins[h].values())
            dominant_cat = max(hour_mins[h].items(), key=lambda x: x[1])[0]
            segments = sorted(
                [{"cat": c, "mins": m, "pct": fmt_pct(m, total), "color": cat_color(c)}
                 for c, m in hour_mins[h].items()],
                key=lambda x: -x["mins"]
            )
        else:
            total = 0
            dominant_cat = "休息"
            segments = []
        out.append({
            "hour": h,
            "dominant_cat": dominant_cat,
            "dominant_mins": hour_mins[h].get(dominant_cat, 0) if total else 0,
            "segments": segments,
            "records_count": len(hour_recs[h]),
        })
    return out


def build_24h_heatmap(records: list[dict]) -> list[list[dict]]:
    """返回 7 天 × 24 小时的二维矩阵:[[{cat, mins, color} for h in 24] for d in 7]
    用 records 的 date 字段做 day 索引(0=最早, 6=最新)
    """
    # 按 date 分组
    by_date: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        by_date[r.get("date", "")].append(r)
    sorted_dates = sorted(by_date.keys())[-7:]  # 最近 7 天
    matrix = []
    for d in sorted_dates:
        day_recs = by_date[d]
        hour_mins = [defaultdict(int) for _ in range(24)]
        for r in day_recs:
            s_min = hhmm_to_min(r.get("time_start", ""))
            e_min = hhmm_to_min(r.get("time_end", ""))
            if e_min <= s_min:
                continue
            cat = r.get("category", "未知")
            cur = s_min
            while cur < e_min:
                h = cur // 60
                if 0 <= h < 24:
                    nh = (h + 1) * 60
                    covered = min(nh, e_min) - cur
                    if covered > 0:
                        hour_mins[h][cat] += covered
                cur += 60
        row = []
        for h in range(24):
            if hour_mins[h]:
                total = sum(hour_mins[h].values())
                dom = max(hour_mins[h].items(), key=lambda x: x[1])[0]
                row.append({"cat": dom, "mins": total, "color": cat_color(dom)})
            else:
                row.append({"cat": None, "mins": 0, "color": "#f5f5f7"})
        matrix.append(row)
    return matrix, sorted_dates


def build_trend_series(records: list[dict], dim: str = "维持") -> list[dict]:
    """按日聚合 dim 维度的总时长,生成折线数据点
    返回: [{date, mins, color}, ...]  按时间排序
    """
    by_date: dict[str, int] = defaultdict(int)
    for r in records:
        if l1_of(r.get("category", "")) == dim:
            by_date[r.get("date", "")] += r.get("duration_minutes") or 0
    return [
        {"date": d, "mins": m, "color": cat_color(dim)}
        for d, m in sorted(by_date.items())
    ]


def build_dimension_aggregates(records: list[dict]) -> dict[str, int]:
    """返回 7 维(维持/健康/工作/学习/调整/日常/投入)的总分钟数"""
    out = {dim: 0 for dim in HEALTH_DIMS}
    for r in records:
        l1 = l1_of(r.get("category", ""))
        if l1 in out:
            out[l1] += r.get("duration_minutes") or 0
    return out


def build_compare_aggregates(ranges: list[dict]) -> list[dict]:
    """ranges = [{label, start, end, records}]
    返回: [{label, total, by_l1: {dim: mins}, by_day_avg: float}]
    """
    out = []
    for r in ranges:
        by_l1 = build_dimension_aggregates(r["records"])
        total = sum(by_l1.values())
        days = max(1, r.get("days", 1))
        out.append({
            "label": r["label"],
            "start": r["start"],
            "end": r["end"],
            "days": days,
            "total": total,
            "by_l1": by_l1,
            "by_day_avg": total // days,
        })
    return out


def build_diff_table(a: dict, b: dict) -> list[dict]:
    """对比两个 build_compare_aggregates 的结果 → 每个维度的差值 + 颜色标记"""
    diffs = []
    for dim in HEALTH_DIMS:
        va = a["by_l1"].get(dim, 0)
        vb = b["by_l1"].get(dim, 0)
        delta = vb - va
        diffs.append({
            "dim": dim,
            "a": va, "b": vb,
            "delta": delta,
            "delta_short": fmt_dur_short(abs(delta)),
            "pct": fmt_pct(abs(delta), va) if va > 0 else (100.0 if vb > 0 else 0.0),
            "color": "#34C759" if delta > 0 else ("#FF3B30" if delta < 0 else "#86868b"),
            "emoji": cat_emoji(dim),
        })
    return diffs


def compute_health_score(records: list[dict], target: dict = None) -> int:
    """健康分 0-100,基于 7 维达标率加权
    逻辑:每维实际值 vs 阈值,达标得 100,偏差 20% 内线性衰减,超 20% 得 0
    整体得分 = 各维得分均值
    """
    target = target or HEALTH_TARGETS
    by_l1 = build_dimension_aggregates(records)
    scores = []
    for dim, mins in by_l1.items():
        if dim not in target:
            continue
        tgt = target[dim]
        # "工作"是上限,超阈扣分;"其他"是下限
        if dim == "工作":
            if mins <= tgt:
                scores.append(100)
            elif mins <= tgt * 1.5:
                scores.append(int(100 * (1.5 - mins / tgt) / 0.5))
            else:
                scores.append(0)
        else:
            if mins >= tgt:
                scores.append(100)
            elif mins >= tgt * 0.8:
                scores.append(int(100 * mins / tgt))
            elif mins >= tgt * 0.5:
                scores.append(int(100 * (mins / tgt) * 0.7))
            else:
                scores.append(int(100 * (mins / tgt) * 0.4))
    return int(sum(scores) / len(scores)) if scores else 0


def detect_anomalies(records: list[dict], baseline_records: list[dict] = None, threshold: float = 0.2) -> list[dict]:
    """异常检测:各维实际 vs 基线(默认近 30 天),偏差 ± 20% 标红
    返回: [{dim, current, baseline, delta_pct, severity: 'red'|'yellow'|'ok', message}]
    """
    baseline = build_dimension_aggregates(baseline_records or records)
    current = build_dimension_aggregates(records)
    out = []
    for dim in HEALTH_DIMS:
        b = baseline.get(dim, 0)
        c = current.get(dim, 0)
        if b == 0:
            continue
        delta_pct = (c - b) / b
        if abs(delta_pct) >= threshold:
            severity = "red"
        elif abs(delta_pct) >= threshold / 2:
            severity = "yellow"
        else:
            severity = "ok"
        if severity == "ok":
            continue
        out.append({
            "dim": dim, "current": c, "baseline": b,
            "delta_pct": round(delta_pct * 100, 1),
            "severity": severity,
            "direction": "↑" if delta_pct > 0 else "↓",
            "message": (
                f"{cat_emoji(dim)} {dim}:{fmt_dur_short(c)}(基线 {fmt_dur_short(b)},"
                f"{'涨' if delta_pct>0 else '降'} {abs(delta_pct):.1f}%)"
            ),
        })
    return out


def records_in_range(get_records_fn, start: str, end: str) -> list[dict]:
    """调 get_records_range 包一层,sort by date+time_start"""
    recs = get_records_fn(start, end)
    recs.sort(key=lambda r: (r.get("date", ""), r.get("time_start", "")))
    return recs
