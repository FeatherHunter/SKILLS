# -*- coding: utf-8 -*-
"""test_overview_period.py — #258 周期剩余进度测试

覆盖 build_overview_data 新增周期进度字段:
  - active(进行中): current_week / remaining_weeks / remaining_training_days / period_status
  - unstarted(未开始): current_week=0, 全部剩余
  - finished(已结束): 剩余为 0, 提示本周期已完成
  - HTML 渲染: 周期进度条 section + KPI 追加 + 结束态提示

显式依赖 temp_db(2026-08-11 事故教训: 写库测试 fixture 必须请求 temp_db,
非 autouse, 单独跑文件不请求会解析到生产库)。
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import render_workout_plan as rwp  # noqa: E402


@pytest.fixture()
def seed_period_plan(temp_db):
    """4 周循环计划,每周 3 个训练日(周一/周三/周五),start_date=2026-08-03(周一)

    训练日结构:
      周一 深蹲(腿) 2 组 / 周三 卧推(胸) 2 组 / 周五 硬拉(背) 2 组
    每周训练日数 = 3
    """
    from db import get_db

    conn = get_db(temp_db)
    c = conn.cursor()
    c.execute("DELETE FROM workout_plan_config")
    c.execute("DELETE FROM workout_plans")
    c.execute(
        "INSERT INTO workout_plan_config (title, version, description, total_weeks, start_date) "
        "VALUES (?, ?, ?, ?, ?)",
        ("推拉腿测试", "v1", "pytest #258", 4, "2026-08-03"),
    )
    plan = [
        (1, 1, "深蹲", 2),
        (1, 3, "卧推", 2),
        (1, 5, "硬拉", 2),
        (2, 1, "深蹲", 2),
        (2, 3, "卧推", 2),
        (2, 5, "硬拉", 2),
        (3, 1, "深蹲", 2),
        (3, 3, "卧推", 2),
        (3, 5, "硬拉", 2),
        (4, 1, "深蹲", 2),
        (4, 3, "卧推", 2),
        (4, 5, "硬拉", 2),
    ]
    for week, dow, name, sets_n in plan:
        movements = json.dumps([
            {"name": name, "part": "腿", "sets": [{"reps": 10, "weight": 50} for _ in range(sets_n)]},
        ], ensure_ascii=False)
        c.execute(
            "INSERT INTO workout_plans (week_number, day_of_week, session_index, session_label, "
            "time_start, time_end, is_rest_day, total_sets, movements) VALUES (?,?,?,?,?,?,?,?,?)",
            (week, dow, 1, "训练", "07:00", "08:00", 0, sets_n, movements),
        )
    conn.commit()
    conn.close()
    yield temp_db
    conn = get_db(temp_db)
    conn.execute("DELETE FROM workout_plans")
    conn.execute("DELETE FROM workout_plan_config")
    conn.commit()
    conn.close()


def _kpi(temp_db, today):
    from db import get_db
    conn = get_db(temp_db)
    data = rwp.build_overview_data(conn, today=today)
    conn.close()
    assert data and data["mode"] == "overview"
    return data["kpi"]


def test_active_week2(seed_period_plan):
    """进行中: 2026-08-10 = 第 2 周周一 → 已过 1 周, 剩余完整周 2

    精确到天(B 口径): 从明天 8/11 数到 8/30 = 本周剩(8/12 三 + 8/14 五)
    + 第 3 周(8/17 一 + 8/19 三 + 8/21 五) + 第 4 周(8/24 一 + 8/26 三 + 8/28 五) = 8
    """
    k = _kpi(seed_period_plan, date(2026, 8, 10))
    assert k["period_status"] == "active"
    assert k["current_week"] == 2
    assert k["remaining_weeks"] == 2
    assert k["remaining_training_days"] == 8
    assert k["period_end"] == "2026-08-30"  # start + 4周×7天 - 1


def test_active_week4_last_day(seed_period_plan):
    """进行中最后一周: 2026-08-24 = 第 4 周周一 → 剩余完整周 0, 但本周还有 2 个训练日(周三/周五)

    #258 用户拍板 B·精确到天: 从明天起逐日数, 当前周剩余训练日也计入。
    """
    k = _kpi(seed_period_plan, date(2026, 8, 24))
    assert k["period_status"] == "active"
    assert k["current_week"] == 4
    assert k["remaining_weeks"] == 0
    assert k["remaining_training_days"] == 2  # 本周三 8/26 + 周五 8/28


def test_active_week2_midweek(seed_period_plan):
    """进行中周中: 2026-08-12(周三) = 第 2 周周三 → 本周剩周五 + 第 3/4 周各 3 天

    验证「精确到天」比「完整周×每周天数」多算当前周剩余训练日。
    """
    k = _kpi(seed_period_plan, date(2026, 8, 12))
    assert k["period_status"] == "active"
    assert k["current_week"] == 2
    assert k["remaining_weeks"] == 2
    # 精确到天: 8/13(四)之后 → 8/14(五) + 第3周3天(8/17,19,21) + 第4周3天(8/24,26,28) = 7
    # 完整周口径(旧) = 2×3 = 6 —— B 口径多算本周剩余 1 天
    assert k["remaining_training_days"] == 7


def test_unstarted(seed_period_plan):
    """未开始: 早于 start_date → current_week=0, 全部剩余(4 周 × 3 = 12 训练日)"""
    k = _kpi(seed_period_plan, date(2026, 7, 27))
    assert k["period_status"] == "unstarted"
    assert k["current_week"] == 0
    assert k["remaining_weeks"] == 4
    assert k["remaining_training_days"] == 12


def test_finished(seed_period_plan):
    """已结束: 晚于周期最后一天 → 剩余全 0, current_week=总周数"""
    k = _kpi(seed_period_plan, date(2026, 9, 7))
    assert k["period_status"] == "finished"
    assert k["current_week"] == 4
    assert k["remaining_weeks"] == 0
    assert k["remaining_training_days"] == 0


def test_render_contains_period_section(seed_period_plan):
    """HTML 渲染: 周期进度 section + KPI 追加 + 结束态提示

    ⚠️ 不做真实日期断言(render 内部用 date.today(), 会随运行日期漂移,
    2026-08-30 周期结束后 period_status 变 finished 仍应通过)——
    只断言结构存在 + 字段类型正确。
    """
    html = rwp.render(mode="overview", output_path=str(Path(__file__).parent / "_plan_ov_period.html"))
    assert isinstance(html, str) and Path(html).exists()
    text = Path(html).read_text(encoding="utf-8")
    # 周期进度 section 存在(注入数据含字段即可, 不必等 JS 跑)
    m = re.search(r'<script id="payload" type="application/json">(.*?)</script>', text, re.DOTALL)
    assert m, "模板未注入 payload"
    raw = m.group(1).replace("<\\/", "</")
    data = json.loads(raw)
    k = data["data"]["kpi"]
    # 字段存在 + 类型正确(不锁死具体状态值, 避免时间炸弹)
    assert k["period_status"] in ("active", "unstarted", "finished")
    assert isinstance(k["current_week"], int)
    assert isinstance(k["remaining_weeks"], int)
    assert isinstance(k["remaining_training_days"], int)
    assert "period_status" in k
    # JS 渲染函数里含周期进度 UI 代码(模板静态部分)
    assert "周期进度" in text
    assert "period-end-tip" in text
    assert "剩余训练日" in text


def test_render_finished_hint(seed_period_plan):
    """已结束态渲染: current_week=总周数 → 进度条 100% 文案分支(finished 提示)"""
    conn = rwp._get_db()
    data = rwp.build_overview_data(conn, today=date(2026, 9, 7))
    conn.close()
    assert data["kpi"]["period_status"] == "finished"
    # JS 侧 finished 分支文案存在于模板
    text = rwp.TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "本周期已完成" in text
