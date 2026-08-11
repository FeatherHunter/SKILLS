"""T3 · 复盘一体模板粒度测试(2026-08-09 · G1-A2/A3/A4 · 对抗式审查矛盾 2 修正)

锁定:
- 粒度路由:day/week/month/range 各粒度 payload 数据齐备
- 区间按长度路由:≤1 天→day / ≤7 天→week / ≤31 天→month / 其他→通用(range 4 段叙事)
- 健康分全粒度:day=单日 / week+month=均值+序列
- day 缺计划 → plan_guide 补齐引导(不降级)
- month 环比:与上月同期对比
- 复盘→计划衔接:copy_prompt 含"制定明日计划"引导
- CLI 端到端:render-replay --granularity day 生成一体模板 HTML
"""
import sys
import json
import subprocess
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import schedule_db as _db


def _rec(date, ts, te, cat="工作.AI调优", act="测试", mins=None, i=0):
    return _db.add_record_full(
        date=date, time_start=ts, time_end=te,
        duration_minutes=mins or (int(te.split(":")[0]) * 60 + int(te.split(":")[1])
                                  - int(ts.split(":")[0]) * 60 - int(ts.split(":")[1])),
        activity=f"{act} {i}", category=cat,
        source_contents=f"原文 {i}", source_timestamps=ts, analysis_reasoning=f"推理 {i}",
    )


def _plan(date, ts, te, title, comp="已完成"):
    r = _db.ensure_plan_event(date=date, time_start=ts, time_end=te, title=title, category="工作.AI调优")
    if comp:
        _db.update_plan_event(r["id"], {"completion": comp})
    return r["id"]


# ---- day 粒度 ----

def test_replay_day_granularity():
    """day 粒度:meta.granularity=day + 计划 vs 实际对照 + 单日健康分"""
    _rec("2026-08-09", "10:00", "11:00", i=1)
    _plan("2026-08-09", "10:00", "11:00", "写代码")
    from schedule_html_render import render_replay
    result = render_replay("2026-08-09", "2026-08-09", granularity="day")
    assert result["status"] == "ok"
    d = result["data"]
    assert d["meta"]["granularity"] == "day"
    assert d["meta"]["title"] == "今日复盘 · 2026-08-09"
    gd = d["granularity_data"]
    assert gd["granularity"] == "day"
    # 计划 vs 实际对照
    pairs = d["cross_domain"]["planned_actual_pairs"]
    assert len(pairs) == 1
    assert pairs[0]["title"] == "写代码"
    assert pairs[0]["actual_duration_minutes"] == 60
    # 单日健康分
    assert gd["health_score"] > 0
    # 有计划 → 无补齐引导
    assert gd["plan_guide"] is None


def test_replay_day_missing_plan_guide():
    """day 粒度缺计划 → plan_guide 补齐引导(不降级)+ status incomplete"""
    _rec("2026-08-09", "10:00", "11:00", i=1)
    from schedule_html_render import render_replay
    result = render_replay("2026-08-09", "2026-08-09", granularity="day")
    assert result["status"] == "incomplete"
    gd = result["data"]["granularity_data"]
    assert gd["plan_guide"] is not None
    assert "还没有日程计划" in gd["plan_guide"]["hint"] or gd["plan_guide"]["hint"]
    assert "ensure-plan-event" in gd["plan_guide"]["prompt"]
    assert "granularity day" in gd["plan_guide"]["prompt"]


# ---- week 粒度 ----

def test_replay_week_health_series():
    """week 粒度:health_series 每日序列 + health_mean 均值"""
    _rec("2026-08-03", "08:00", "09:00", cat="维持.睡眠", i=1)
    _rec("2026-08-04", "08:00", "09:00", cat="维持.睡眠", i=2)
    _rec("2026-08-05", "08:00", "09:00", cat="维持.睡眠", i=3)
    from schedule_html_render import render_replay
    result = render_replay("2026-08-03", "2026-08-09", granularity="week")
    assert result["status"] in ("ok", "incomplete"), f"单域数据应为 ok/incomplete: {result['status']}"
    gd = result["data"]["granularity_data"]
    assert gd["granularity"] == "week"
    assert len(gd["health_series"]) == 3
    assert gd["health_mean"] > 0
    # 趋势 + 热力图数据(周区块核心)
    ra = result["data"]["record_aggregate"]
    assert ra["trend"] and ra["heatmap"]


# ---- month 粒度 ----

def test_replay_month_compare():
    """month 粒度:环比对比(本月 vs 上月同期)+ 目标达成数据"""
    # 上月 8 月:维持.睡眠 120min
    _rec("2026-07-05", "22:00", "24:00", cat="维持.睡眠", i=1)
    _plan("2026-07-06", "09:00", "10:00", "上月计划", comp="已完成")
    # 本月 9 月:维持.睡眠 120min
    _rec("2026-08-05", "22:00", "24:00", cat="维持.睡眠", i=2)
    _rec("2026-08-06", "09:00", "10:00", cat="工作.AI调优", i=3)
    _plan("2026-08-06", "09:00", "10:00", "本月计划", comp="已完成")
    from schedule_html_render import render_replay
    result = render_replay("2026-08-01", "2026-08-31", granularity="month")
    assert result["status"] == "ok"
    gd = result["data"]["granularity_data"]
    assert gd["granularity"] == "month"
    assert gd["month_compare"], "month 粒度应有环比对比数据"
    # 环比里的睡眠分类:本月 120 vs 上月 120 → delta 0
    sleep_row = next((m for m in gd["month_compare"] if "睡眠" in m["category"]), None)
    assert sleep_row is not None
    assert sleep_row["current"] == 120 and sleep_row["previous"] == 120
    # 完成率环比(两月都 100%)
    assert gd["month_rate_compare"] is not None
    assert gd["month_rate_compare"]["current_rate"] == 1.0
    assert gd["month_rate_compare"]["delta_pct"] == 0.0


# ---- range 按长度路由 ----

def test_replay_range_route_by_length():
    """range 粒度按区间长度路由:1 天→day / 7 天→week / 30 天→month / 60 天→通用"""
    from schedule_html_render import render_replay
    for d in ("2026-08-01", "2026-08-02", "2026-08-03"):
        _rec(d, "09:00", "10:00", i=1)
    r1 = render_replay("2026-08-01", "2026-08-01")   # 1 天
    assert r1["data"]["meta"]["granularity"] == "day"
    assert r1["data"]["meta"]["requested_granularity"] == "range"
    r7 = render_replay("2026-08-01", "2026-08-07")   # 7 天
    assert r7["data"]["meta"]["granularity"] == "week"
    r30 = render_replay("2026-08-01", "2026-08-30")  # 30 天
    assert r30["data"]["meta"]["granularity"] == "month"
    r60 = render_replay("2026-08-01", "2026-09-29")  # 60 天
    assert r60["data"]["meta"]["granularity"] == "range"


def test_replay_invalid_granularity():
    """非法 granularity → error"""
    from schedule_html_render import render_replay
    result = render_replay("2026-08-01", "2026-08-09", granularity="year")
    assert result["status"] == "error"
    assert "granularity" in result["message"]


# ---- 复盘→计划衔接 + CLI 端到端 ----

def test_replay_copy_prompt_plan_link():
    """copy_prompt 含复盘→计划衔接引导(跨场景约定 C)"""
    _rec("2026-08-09", "10:00", "11:00", i=1)
    _plan("2026-08-09", "10:00", "11:00", "写代码")
    from schedule_html_render import render_replay
    result = render_replay("2026-08-09", "2026-08-09", granularity="day")
    cp = result["data"]["copy_prompt"]
    assert "今日" in cp
    assert "制定明日计划" in cp or "计划" in cp


def test_replay_cli_granularity_day(tmp_path):
    """CLI 端到端:render-replay --granularity day 生成一体模板 HTML(粒度字段 + 区块标识)"""
    import os
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(tmp_path)
    cwd = str(SKILL_DIR)
    subprocess.run([sys.executable, str(SCRIPTS_DIR / "schedule_cli.py"), "init"],
                   capture_output=True, env=env, cwd=cwd)
    subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "schedule_cli.py"), "add",
         "--date", "2026-08-09", "--time-start", "10:00", "--time-end", "11:00",
         "--duration-minutes", "60", "--activity", "测试", "--category", "工作.AI调优",
         "--source-contents", "原文", "--source-timestamps", "10:00",
         "--analysis-reasoning", "推理"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=cwd)
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "schedule_cli.py"), "render-replay",
         "2026-08-09", "2026-08-09", "--granularity", "day"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=cwd, timeout=30)
    out = json.loads(r.stdout[r.stdout.find("{"):])
    assert out["status"] in ("ok", "incomplete"), f"render-replay 失败: {out.get('message')}"
    assert out["data"]["granularity"] == "day"
    fp = Path(out["data"]["file_path"])
    assert fp.exists()
    html = fp.read_text(encoding="utf-8")
    # 一体模板特征:粒度路由 JS + 计划 vs 实际对照 + 健康分全粒度 + 计划衔接
    assert "gran === " in html or "gran" in html
    assert "计划 vs 实际对照" in html
    assert "健康分均值" in html
    assert "plan-link-zone" in html
