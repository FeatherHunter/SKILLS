# -*- coding: utf-8 -*-
"""test_exercise_review_volume.py — #257 训练容量/负荷趋势测试

覆盖:
1. 数据层: exercise_review JSON 的 __meta__.volume 结构
   - 周容量(计划/实做 Σ kg×次数) 按自然周聚合
   - 主项动作 TOP4 周序列(计划线恒定 / 实做线衰减)
   - 无实绩 -> has_actual=False
2. 渲染层: render_exercise_review_html 解包注入(纯日期 dict, 非 {status,data,message} 包装)
3. 模板: 容量图表容器 + 空态提示存在

测试隔离: conftest temp_db(session-scope) monkeypatch SKILLS_DB_PATH 到临时目录,
本文件用 function-scope fixture 清表, 不写生产库。
"""
import json
import re
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import analysis.exercise as ex  # noqa: E402


@pytest.fixture()
def seed_volume(temp_db, monkeypatch):
    """写入 2 周推日计划(周一深蹲/卧推) + 实绩(第1周全做, 第2周做一半)

    显式依赖 temp_db + monkeypatch 模块级 DB_PATH:
    - 2026-08-11 事故: 未请求 temp_db 时单独跑测试直接操作生产库(清空 exercise_log 8297 行)
    - analysis._utils.DB_PATH 是 collection 时解析的模块级常量(早于 conftest setenv),
      必须在此 monkeypatch 指向 temp_db, 否则 exercise_review 内部 _get_db() 读生产库
    """
    import analysis._utils as utils

    monkeypatch.setattr(utils, 'DB_PATH', Path(str(temp_db)))
    from db import get_db

    conn = get_db(temp_db)
    c = conn.cursor()
    c.execute("DELETE FROM workout_plan_config")
    c.execute("DELETE FROM workout_plans")
    c.execute("DELETE FROM exercise_log")
    c.execute(
        "INSERT INTO workout_plan_config (title, version, description, total_weeks, start_date) "
        "VALUES (?, ?, ?, ?, ?)",
        ("容量测试计划", "v1", "pytest-volume", 2, "2026-07-27"),
    )
    movements = json.dumps([
        {"name": "深蹲", "part": "腿", "sets": [{"reps": 10, "weight": 50}, {"reps": 10, "weight": 50}]},
        {"name": "卧推", "part": "胸", "sets": [{"reps": 8, "weight": 40}]},
    ], ensure_ascii=False)
    # 每周一训练日(day_of_week=1); 推日 3 组 = 深蹲 2 + 卧推 1
    for w in range(1, 3):
        c.execute(
            "INSERT INTO workout_plans (week_number, day_of_week, session_index, session_label, "
            "time_start, time_end, is_rest_day, total_sets, movements) VALUES (?,?,?,?,?,?,?,?,?)",
            (w, 1, 1, "推日", "15:00", "16:00", 0, 3, movements),
        )
    # 实绩: 第1周完整 3 组(深蹲2+卧推1), 第2周只做卧推 1 组
    rows = [
        ("2026-07-27", "深蹲", 1, 10, 50.0),
        ("2026-07-27", "深蹲", 2, 10, 50.0),
        ("2026-07-27", "卧推", 1, 8, 40.0),
        ("2026-08-03", "卧推", 1, 8, 40.0),
    ]
    for r in rows:
        c.execute(
            "INSERT INTO exercise_log (date, exercise_type, set_index, reps, load_kg, duration_minutes, calories_burned) "
            "VALUES (?,?,?,?,?,?,?)",
            (*r, 0, 0),
        )
    conn.commit()
    conn.close()
    yield
    # teardown
    conn = get_db(temp_db)
    conn.execute("DELETE FROM exercise_log")
    conn.execute("DELETE FROM workout_plans")
    conn.execute("DELETE FROM workout_plan_config")
    conn.commit()
    conn.close()


def _volume(start="2026-07-27", end="2026-08-09"):
    """调用 exercise_review 并返回 __meta__.volume"""
    result = ex.exercise_review(start, end, as_dict=True, silent=True)
    assert result["status"] == "ok"
    return result["data"]["__meta__"]["volume"]


def test_volume_weekly_plan_constant(seed_volume):
    """计划容量按自然周恒定: 每周 Σ(kg×次数) 相同(推日重复)"""
    vol = _volume()
    weeks = vol["weeks"]
    assert len(weeks) == 2
    # 计划: 深蹲 50*10*2组 + 卧推 40*8 = 1000 + 320 = 1320/周
    plans = [w["plan"] for w in weeks]
    assert plans == [1320, 1320], f"计划周容量应恒定, 实得 {plans}"


def test_volume_actual_decay(seed_volume):
    """实做容量衰减: 第1周全做(1320), 第2周仅卧推(320)"""
    vol = _volume()
    actuals = [w["actual"] for w in vol["weeks"]]
    assert actuals == [1320, 320], f"实做容量应衰减, 实得 {actuals}"
    assert vol["has_actual"] is True
    assert vol["total_plan"] == 2640
    assert vol["total_actual"] == 1640


def test_volume_movements_top4(seed_volume):
    """主项动作: 深蹲/卧推周序列, 计划线恒定 + 实做线衰减"""
    vol = _volume()
    names = [m["name"] for m in vol["movements"]]
    assert "深蹲" in names and "卧推" in names
    squat = next(m for m in vol["movements"] if m["name"] == "深蹲")
    assert squat["plan_total"] == 2000  # 50*10*2组*2周
    assert squat["actual_total"] == 1000  # 仅第1周做
    assert [w["actual"] for w in squat["weeks"]] == [1000, 0]


def test_volume_no_actual_flag(seed_volume, temp_db):
    """无实绩 -> has_actual=False, 周容量只有计划"""
    from db import get_db

    conn = get_db(temp_db)
    conn.execute("DELETE FROM exercise_log")
    conn.commit()
    conn.close()
    vol = _volume()
    assert vol["has_actual"] is False
    assert all(w["actual"] == 0 for w in vol["weeks"])
    assert vol["total_actual"] == 0


def test_render_injects_unwrapped_data(seed_volume):
    """渲染注入解包: window.__DATA__ 顶层是纯日期 dict(非 {status,data,message} 包装)"""
    import render_exercise_review_html as rer

    raw = {
        "status": "ok",
        "data": {"2026-07-27": {"completion_rate": 100}, "__meta__": {"volume": {"weeks": []}}},
        "message": "ok",
    }
    html = rer.render_html(raw)
    m = re.search(r"window\.__DATA__ = (\{.*?\});</script>", html, re.DOTALL)
    assert m, "模板未注入 __DATA__"
    data = json.loads(m.group(1).replace("<\\/", "</"))
    assert "2026-07-27" in data
    assert "status" not in data
    assert "__meta__" in data
    assert "volume" in data["__meta__"]


def test_template_contains_volume_sections():
    """模板含容量图表容器(周容量柱状 + 主项折线 + 空态提示)"""
    tpl = Path(__file__).resolve().parent.parent / "templates" / "exercise_review.html"
    text = tpl.read_text(encoding="utf-8")
    assert "周训练容量" in text and "volumeChart" in text
    assert "主项动作负荷趋势" in text and "movementChart" in text
    assert "renderVolume" in text and "renderMovements" in text
    assert "实做数据不足" in text  # 空态提示
