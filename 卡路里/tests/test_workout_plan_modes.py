# -*- coding: utf-8 -*-
"""test_workout_plan_modes.py — render_workout_plan 多模式渲染测试 (ticket #6)

覆盖 8 个 mode:
  full / week / today / overview / vs / completion / missed / movement

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
def seed_plan():
    """写入一份 2 周测试计划 + 今日实绩(function-scope,每测试独立)"""
    from db import find_db_path, get_db
    from workout_plan import DB_PATH

    db_path = find_db_path(Path(__file__).resolve().parent.parent, "calorie_data.db")
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
    m = re.search(r"window\.__DATA__ = (\{.*?\});</script>", html, re.DOTALL)
    assert m, "模板未注入 __DATA__"
    raw = m.group(1).replace("<\\/", "</")
    return json.loads(raw)


@pytest.mark.parametrize("mode", [
    "full", "week", "today", "overview", "vs", "completion", "missed", "movement",
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
