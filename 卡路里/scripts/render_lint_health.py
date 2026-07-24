#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_lint_health.py — 数据健康检查(Lint 5 项)HTML 渲染器(报告型)

对应 SKILL.md 唤醒词: 查卡路里数据
对应模板: templates/lint_health.html
"""
import argparse, json, sys
from datetime import date, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "lint_health.html"

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


# 中文消息常量(纯字符串,不含嵌套引号)
NO_GOAL = "尚{\u672a}{\u8bbe}{\u7f6e}{\u4f53}{\u91cd}{\u76ee}{\u6807}{\u3002}"
SUG_SET = "建议通过\"设体重目标\"添加目标"
GOOD_FRESH_FMT = "今日({0})已记录饮食 {1} 卡,饮水 {2[today_water]}ml,{2[today_exercise]} 次运动。完整 {\u2713}"
BAD_FRESH_FMT = "今日({0})完全无记录 — 体重/饮食/运动全缺。"
WARN_FRESH_FMT = "今日({0})未记录:{1}。其他项 OK。"
WARN_WEIGHT_FMT = "目标 {0} kg(截至 {1}),但尚未记录当前体重。"
GOOD_WEIGHT_FMT = "目标 {0} kg(截至 {1}) — 当前 {2} kg 已达成 {\u2713}"
BAD_WEIGHT_FMT = "目标 {0} kg(截至 {1}) — 当前 {2} kg,差 {3} kg,**已逾期**。"
WARN_PROGRESS_FMT = "当前 {0} kg → 目标 {1} kg(差 {2} kg)。剩余 {3} 天,日均需减重 {4} kg/天。"
SUG_PROGRESS_FMT = "当前减重速率需 ~{0} 卡/天热量缺口。建议:① 微调每日摄入 -200 卡 ② 或增加运动消耗 +200 卡。"
OK_CALORIE_FMT = "近 {0} 天热量摄入在合理范围内(平均 {1} 卡,目标 {2})。"
BAD_TREND_FMT = "近 {0} 天,{1} 实际超目标 {2} 卡(/天),连续 {3} 天摄入偏高(平均 {4} 卡)。"
SUG_TREND = "{\u26a0} 热量持续高于目标 - 建议从今日起:① 减每餐主食 30% ② 加 30 分钟有氧 ③ 监控下周缺口能否回正。"
WARN_TREND_FMT = "近 {0} 天有 {1} 天摄入超目标 +5% 以上(平均 {2} 卡)。"
GOOD_DEFICIT_FMT = "近 {0} 天累计缺口 +{1} 卡(实际摄入 {2},实际消耗 {3})。缺口方向正确(正向=减重方向 {\u2713})。"
WARN_DEFICIT_FMT = "近 {0} 天缺口 {1} 卡,摄入略高于消耗(盈余 {2} 卡)。"
BAD_DEFICIT_FMT = "近 {0} 天严重盈余 {1} 卡,摄入远超消耗。"
GOOD_EXERCISE_FMT = "近 {0} 天运动 {1} 天,频次优秀 {\u2713}"
WARN_EXERCISE_FMT = "近 {0} 天运动 {1} 天,有 {2} 天未运动。"
BAD_EXERCISE_FMT = "近 {0} 天运动仅 {1} 天,严重不足。"
SUG_BAD_EXERCISE = "{\u26a0} 急需提升运动频次:① 每周至少 3 次 ② 每次 ≥ 30 分钟 ③ 从散步/快走等低强度开始,避免受伤。"
WARN_WEIGHT_RECORD = "先记体重记录当前数据,系统才能算进度。"
BAD_FRESH_SUG = "建议立即补录今日数据,否则营养分析和缺口告警失效。"
WARN_FRESH_SUG = "建议补录缺失项,以保证各项分析准确。"
GOOD_WEIGHT_SUG = "保持当前习惯即可。"
BAD_WEIGHT_SUG = "建议重新设定合理的目标日期或调整减重计划。"
GOOD_DEFICIT_SUG = "缺口正向,持续即可。"
WARN_DEFICIT_SUG = "建议略减主食/甜食,或加 1 次有氧运动。"
BAD_DEFICIT_SUG = "急需调整:① 显著减少高热量摄入 ② 增加运动频次与时长 ③ 监控 1 周后缺口是否好转。"
GOOD_TREND_SUG = "保持当前习惯。"
WARN_TREND_SUG = "建议减少高热量饮食,保持接近目标 ±5%。"
GOOD_EXERCISE_SUG = "保持当前频次。"
WARN_EXERCISE_SUG = "建议:① 在未运动日加 20-30 分钟散步 ② 重点安排下肢力量训练 1 次/周。"
BAD_EXERCISE_SUG = "急需提升运动频次。"
GOOD_FRESH_SUG = "保持每日记录习惯。"
WEIGHT_GOAL_DAILY_FMT = "当前减重速率需 ~{0} 卡/天热量缺口。"
SUG_OK_BREAK_DOWN = "保持当前习惯即可。"


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if raw.get("status") != "ok":
        raise ValueError("数据状态非 ok")
    return raw


def _check_freshness(conn, today):
    """数据新鲜度"""
    items = {"today_weight": 0, "today_calorie": 0, "today_water": 0, "today_exercise": 0}
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM weight_log WHERE date=?", (today,))
    items["today_weight"] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(calorie),0) FROM food_log WHERE date=?", (today,))
    cal = items["today_calorie"] = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(calorie),0) FROM food_log WHERE date=? AND food_name='\U0001F4A7水'", (today,))
    items["today_water"] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM exercise_log WHERE date=?", (today,))
    items["today_exercise"] = cur.fetchone()[0]
    miss = []
    if items["today_weight"] == 0: miss.append("体重")
    if cal == 0: miss.append("饮食")
    if items["today_exercise"] == 0: miss.append("运动")
    if not miss:
        return "good", GOOD_FRESH_FMT.format(today, cal, items), GOOD_FRESH_SUG
    if len(miss) == 3:
        return "bad", BAD_FRESH_FMT.format(today), BAD_FRESH_SUG
    return "warn", WARN_FRESH_FMT.format(today, ", ".join(miss)), WARN_FRESH_SUG


def _check_weight_goal(conn, today):
    """体重目标进度"""
    cur = conn.cursor()
    cur.execute("SELECT weight_kg, deadline FROM weight_goal ORDER BY id DESC LIMIT 1")
    g = cur.fetchone()
    if not g:
        return "warn", NO_GOAL, SUG_SET
    target, deadline = g
    cur.execute("SELECT weight_kg FROM weight_log ORDER BY date DESC LIMIT 1")
    latest = cur.fetchone()
    if not latest:
        return "warn", WARN_WEIGHT_FMT.format(target, deadline), WARN_WEIGHT_RECORD
    current = latest[0]
    diff = current - target
    days_left = (date.fromisoformat(deadline) - date.fromisoformat(today)).days
    if diff <= 0:
        return "good", GOOD_WEIGHT_FMT.format(target, deadline, current), GOOD_WEIGHT_SUG
    if days_left <= 0:
        return "bad", BAD_WEIGHT_FMT.format(target, deadline, current, diff), BAD_WEIGHT_SUG
    daily_need = round(diff / days_left, 3)
    return "warn", WARN_PROGRESS_FMT.format(current, target, diff, days_left, daily_need), SUG_PROGRESS_FMT.format(round(daily_need*7700))


def _check_calorie_trend(conn, today, days=7):
    """热量趋势"""
    start = (date.fromisoformat(today) - timedelta(days=days-1)).isoformat()
    cur = conn.cursor()
    cur.execute("SELECT date, COALESCE(SUM(calorie),0) FROM food_log WHERE date BETWEEN ? AND ? GROUP BY date", (start, today))
    daily = dict(cur.fetchall())
    cur.execute("SELECT calorie FROM daily_goal ORDER BY id DESC LIMIT 1")
    g = cur.fetchone() or (1800,)
    target = g[0]
    over_days = sum(1 for c in daily.values() if c > target * 1.05)
    over_strict = [d for d, c in daily.items() if c > target * 1.10]
    avg = sum(daily.values()) / len(daily) if daily else 0
    if over_strict:
        return "bad", BAD_TREND_FMT.format(days, ", ".join(over_strict), round(target*1.10-0.1), over_days, round(avg)), SUG_TREND
    if over_days >= 3:
        return "warn", WARN_TREND_FMT.format(days, over_days, round(avg)), WARN_TREND_SUG
    return "good", OK_CALORIE_FMT.format(days, round(avg), target), GOOD_TREND_SUG


def _check_deficit(conn, today, days=7):
    """热量缺口"""
    start = (date.fromisoformat(today) - timedelta(days=days-1)).isoformat()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(calorie),0) FROM food_log WHERE date BETWEEN ? AND ?", (start, today))
    intake = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(calorie),0) FROM exercise_log WHERE date BETWEEN ? AND ?", (start, today))
    burn = cur.fetchone()[0]
    tdee = 1700 * days
    total_burn = tdee + burn
    diff = total_burn - intake
    if diff > 0:
        return "good", GOOD_DEFICIT_FMT.format(days, diff, intake, total_burn), GOOD_DEFICIT_SUG
    if diff > -2000:
        return "warn", WARN_DEFICIT_FMT.format(days, diff, -diff), WARN_DEFICIT_SUG
    return "bad", BAD_DEFICIT_FMT.format(days, -diff), BAD_DEFICIT_SUG


def _check_exercise_consistency(conn, today, days=7):
    """运动连续性"""
    start = (date.fromisoformat(today) - timedelta(days=days-1)).isoformat()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT date FROM exercise_log WHERE date BETWEEN ? AND ?", (start, today))
    days_set = {r[0] for r in cur.fetchall()}
    n = len(days_set)
    if n >= 5:
        return "good", GOOD_EXERCISE_FMT.format(days, n), GOOD_EXERCISE_SUG
    if n >= 3:
        return "warn", WARN_EXERCISE_FMT.format(days, n, days - n), WARN_EXERCISE_SUG
    return "bad", BAD_EXERCISE_FMT.format(days, n), BAD_EXERCISE_SUG


def build_data():
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    today = date.today().isoformat()

    funcs = [
        ("freshness",           _check_freshness,           (conn, today)),
        ("weight_goal",         _check_weight_goal,         (conn, today)),
        ("calorie_trend",       _check_calorie_trend,       (conn, today)),
        ("deficit",             _check_deficit,             (conn, today)),
        ("exercise_consistency",_check_exercise_consistency,(conn, today)),
    ]

    items = []
    good_count = warn_count = bad_count = 0
    for idx, (tid, fn, args) in enumerate(funcs):
        # 标题硬编码(避免 f-string 嵌套)
        titles = {
            "freshness": "① 数据新鲜度",
            "weight_goal": "② 体重目标进度",
            "calorie_trend": "③ 热量趋势预警",
            "deficit": "④ 热量缺口分析",
            "exercise_consistency": "⑤ 运动连续性",
        }
        status, desc, sugg = fn(*args)
        items.append({"id": tid, "title": titles[tid], "status": status, "description": desc, "suggestion": sugg})
        if status == "good": good_count += 1
        elif status == "warn": warn_count += 1
        else: bad_count += 1
    conn.close()

    return {
        "status": "ok",
        "data": {
            "summary": {"good_count": good_count, "warn_count": warn_count, "bad_count": bad_count},
            "items": items,
            "meta": {"check_at": f"{date.today().isoformat()} 18:30", "today": today},
        },
        "message": "已生成 5 项 Lint 健康检查",
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    if template.count("<!--INJECT-DATA-->") != 1:
        raise ValueError("模板缺少唯一占位符")
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("<!--INJECT-DATA-->", f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description="渲染 5 项 Lint 健康检查 HTML(报告型)")
    p.add_argument("--mock")
    p.add_argument("--output")
    args = p.parse_args()
    try:
        data = _load_data(args.mock) if args.mock else build_data()
        html = render_html(data)
    except Exception as e:
        print(f"渲染失败: {e}", file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, "lint_health")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    sm = data["data"]["summary"]
    print(f"OK {out_path}")
    print(f"   5 项 Lint: ✓{sm['good_count']} ⚠{sm['warn_count']} ✗{sm['bad_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
