# -*- coding: utf-8 -*-
"""test_workout_plan_modes.py — render_workout_plan 多模式渲染测试 (ticket #6)

覆盖 9 个 mode:
  full / week / today / day / overview / vs / completion / missed / movement

验证:
- 每个 mode 生成合法 HTML,占位符恰好替换 1 次
- 数据结构含 mode 标记 + 对应字段
- JS 主入口可渲染(容器非空) — 由 Playwright 侧验证(本测试做结构断言)
"""
import json
import re
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import render_workout_plan as rwp  # noqa: E402


@pytest.fixture()
def seed_plan(temp_db):
    """写入一份 2 周测试计划 + 今日实绩(function-scope,每测试独立)

    显式依赖 temp_db(session-scope): 2026-08-11 事故教训——此前未请求
    temp_db, 单独跑本文件时 SKILLS_DB_PATH 解析到生产库, DELETE 会清空
    生产库 workout_plan_config/workout_plans(与 #257 事故同源)。
    """
    from db import get_db

    db_path = temp_db
    conn = get_db(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM workout_plan_config")
    c.execute("DELETE FROM workout_plans")
    c.execute(
        "INSERT INTO workout_plan_config (title, version, description, total_weeks, start_date) "
        "VALUES (?, ?, ?, ?, ?)",
        ("测试计划", "v1", "pytest", 2, "2026-07-27"),
    )
    movements = json.dumps([
        {"name": "深蹲", "part": "腿", "sets": [{"reps": 10, "weight": 50}]},
        {"name": "卧推", "part": "胸", "sets": [{"reps": 8, "weight": 40}]},
    ], ensure_ascii=False)
    c.execute(
        "INSERT INTO workout_plans (week_number, day_of_week, session_index, session_label, "
        "time_start, time_end, is_rest_day, total_sets, movements) VALUES (?,?,?,?,?,?,?,?,?)",
        (1, 1, 1, "晨训", "07:00", "08:00", 0, 2, movements),
    )
    conn.commit()
    conn.close()
    yield db_path
    # teardown: 清空
    conn = get_db(db_path)
    conn.execute("DELETE FROM workout_plans")
    conn.execute("DELETE FROM workout_plan_config")
    conn.commit()
    conn.close()


def _extract_data(html: str) -> dict:
    m = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.DOTALL)
    assert m, "模板未注入 payload"
    raw = m.group(1).replace("<\\/", "</")
    return json.loads(raw)


@pytest.mark.parametrize("mode", [
    "full", "week", "today", "day", "overview", "vs", "completion", "missed", "movement", "action",
])
def test_mode_renders(seed_plan, mode):
    html = rwp.render(mode=mode, output_path=str(Path(__file__).parent / f"_plan_{mode}.html"))
    assert isinstance(html, str) and Path(html).exists()
    text = Path(html).read_text(encoding="utf-8")
    # 占位符被替换(恰好 1 次)
    assert text.count("<!--INJECT-DATA-->") == 0
    payload = _extract_data(text)
    assert payload["status"] == "ok"
    d = payload["data"]
    assert d["mode"] == mode
    assert d["config"]["title"] == "测试计划"


def test_full_mode_weeks(seed_plan):
    html = rwp.render(mode="full", output_path=str(Path(__file__).parent / "_plan_full.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["mode"] == "full"
    assert len(d["weeks"]) >= 1
    assert d["weeks"][0]["days"][0]["sessions"][0]["session_label"] == "晨训"


def test_today_mode_completion(seed_plan):
    html = rwp.render(mode="today", output_path=str(Path(__file__).parent / "_plan_today.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert "completion" in d
    assert "plan_sets" in d["completion"]
    assert d["date"]  # 今日


def test_overview_kpi(seed_plan):
    html = rwp.render(mode="overview", output_path=str(Path(__file__).parent / "_plan_ov.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["kpi"]["total_weeks"] == 2
    assert isinstance(d["weekly_rates"], list)


def test_vs_movement_rows(seed_plan):
    html = rwp.render(mode="vs", output_path=str(Path(__file__).parent / "_plan_vs.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert "movement_rows" in d
    assert "completion_rate" in d


def test_missed_and_movement(seed_plan):
    html = rwp.render(mode="missed", output_path=str(Path(__file__).parent / "_plan_missed.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert isinstance(d["missed"], list)
    html2 = rwp.render(mode="movement", output_path=str(Path(__file__).parent / "_plan_mv.html"))
    d2 = _extract_data(Path(html2).read_text(encoding="utf-8"))["data"]
    assert isinstance(d2["ranking"], list)


def test_plan_generator_delete_plan(seed_plan):
    """缺口②:delete_plan 删除整个计划"""
    from plan_generator import delete_plan
    from workout_plan import get_plan_config

    result = delete_plan()
    assert result["deleted_config"]["title"] == "测试计划"
    assert result["deleted_rows"] >= 1
    assert get_plan_config() is None


def test_plan_generator_copy_plan(seed_plan):
    """缺口②:copy_plan 复制整个计划"""
    from plan_generator import _get_db, copy_plan
    from workout_plan import get_plan_config

    result = copy_plan(new_title="测试副本")
    assert result["new_title"] == "测试副本"
    assert result["copied_rows"] >= 1
    cfg = get_plan_config()
    assert cfg["title"] == "测试副本"
    # 清理
    db = _get_db()
    db.execute("DELETE FROM workout_plans")
    db.execute("DELETE FROM workout_plan_config")
    db.commit()
    db.close()


def test_plan_generator_delete_day(seed_plan):
    """缺口②:delete_day 删除某天全部 session"""
    from plan_generator import delete_day

    result = delete_day(1, 1)
    assert result["deleted_sessions"] >= 1
    assert result["snapshot"][0]["session_label"] == "晨训"


def test_day_mode_specific(seed_plan):
    """#255: day 模式 4 态验证(训练日/休息日/未开始/非法日期)"""
    from datetime import date
    from db import get_db

    db = get_db(seed_plan)
    c = db.cursor()
    # 周三休息日(训练日已有 week1/day1)
    c.execute(
        "INSERT INTO workout_plans (week_number, day_of_week, session_index, session_label, is_rest_day, total_sets, movements) "
        "VALUES (?,?,?,?,?,?,?)",
        (1, 3, 1, "休息", 1, 0, "[]"),
    )
    db.commit()
    db.close()

    # 训练日(2026-07-27 周一 = 计划第 1 周)
    html = rwp.render(mode="day", day_date=date(2026, 7, 27),
                      output_path=str(Path(__file__).parent / "_plan_day1.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["mode"] == "day"
    assert d["unstarted"] is False
    assert len(d["sessions"]) >= 1
    assert d["sessions"][0]["session_label"] == "晨训"
    assert d["plan_week"] == 1

    # 休息日(2026-07-29 周三)
    html2 = rwp.render(mode="day", day_date=date(2026, 7, 29),
                       output_path=str(Path(__file__).parent / "_plan_day2.html"))
    d2 = _extract_data(Path(html2).read_text(encoding="utf-8"))["data"]
    assert d2["is_rest"] is True

    # 未开始(2026-07-01 < start 07-27)
    html3 = rwp.render(mode="day", day_date=date(2026, 7, 1),
                       output_path=str(Path(__file__).parent / "_plan_day3.html"))
    d3 = _extract_data(Path(html3).read_text(encoding="utf-8"))["data"]
    assert d3["unstarted"] is True

    # 非法日期 → 友好错误(非 traceback)
    err = rwp.render(mode="day", day_date="abc")
    assert isinstance(err, str) and "无效" in err


def test_today_mode_unchanged(seed_plan):
    """#255 重构: today 模式 mode 字段与完成度契约不变"""
    html = rwp.render(mode="today", output_path=str(Path(__file__).parent / "_plan_today2.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["mode"] == "today"
    assert "completion" in d


def test_action_mode_specific(seed_plan):
    """#256: action 模式 4 态(精确匹配/子串/无匹配+候选/空名)"""
    from db import get_db

    db = get_db(seed_plan)
    c = db.cursor()
    # seed 计划有 深蹲/卧推(week1 day1 晨训); 补一周末周验证覆盖范围
    c.execute(
        "INSERT INTO workout_plans (week_number, day_of_week, session_index, session_label, time_start, time_end, is_rest_day, total_sets, movements) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (2, 1, 1, "晨训", "07:00", "08:00", 0, 2,
         json.dumps([{"name": "深蹲", "part": "腿", "sets": [{"reps": 10, "weight": 50}]}], ensure_ascii=False)),
    )
    db.commit()
    db.close()

    # 精确匹配
    html = rwp.render(mode="action", action_name="深蹲", output_path=str(Path(__file__).parent / "_plan_act1.html"))
    d = _extract_data(Path(html).read_text(encoding="utf-8"))["data"]
    assert d["mode"] == "action"
    assert d["query"] == "深蹲"
    assert len(d["positions"]) >= 2  # 2 周都有
    assert d["summary"]["total_sets"] >= 2  # 每周 1 组 × 2 周
    assert d["next_date"]  # 循环语义下必有下次练习日

    # 子串匹配(卧推 → 杠铃卧推)
    html2 = rwp.render(mode="action", action_name="卧推", output_path=str(Path(__file__).parent / "_plan_act2.html"))
    d2 = _extract_data(Path(html2).read_text(encoding="utf-8"))["data"]
    assert len(d2["positions"]) >= 1
    assert d2["positions"][0]["name"].endswith("卧推")

    # 无匹配 → error + candidates
    html3 = rwp.render(mode="action", action_name="高翻", output_path=str(Path(__file__).parent / "_plan_act3.html"))
    d3 = _extract_data(Path(html3).read_text(encoding="utf-8"))["data"]
    assert "error" in d3 and "无" in d3["error"]
    assert "candidates" in d3

    # 空名 → 缺动作名错误
    html4 = rwp.render(mode="action", action_name="", output_path=str(Path(__file__).parent / "_plan_act4.html"))
    d4 = _extract_data(Path(html4).read_text(encoding="utf-8"))["data"]
    assert d4["error"] == "缺少动作名"
