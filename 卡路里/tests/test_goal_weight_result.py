#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_goal_weight_result.py — 定体重目标结果回执回归(issue #79 · 2026-08-05)

现象:定体重目标流程 填写 HTML → 复制 prompt → AI 写库 后,
AI 只回纯文字,没有可视化确认页。
修复:render_goal_weight.py --live 写库 + 结果回执 HTML(goal_weight_result.html)。
本测试锁住:写库字段 / 进度数据契约 / 极端警示渲染。

⚠️ import 必须放在测试函数内(conftest 惯例):render_goal_weight 链式导入
weight_goal 时会在模块级解析 DB_PATH,若在收集期导入会指向生产库。
"""
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / 'scripts'


@pytest.fixture(scope='session', autouse=True)
def _env_guard(temp_db):
    """session autouse:任何 weight_goal 导入前 SKILLS_DB_PATH 必须已指向 temp

    若本模块测试先于 temp_db 请求方运行,render_goal_weight 链式导入
    weight_goal 会在模块级解析 DB_PATH = 生产库(D:\\2Study\\StudyNotes\\.db),
    测试写库会污染生产 daily_goal(2026-08-05 实测踩坑)。
    """
    yield


@pytest.fixture()
def goal_env(temp_db):
    conn = sqlite3.connect(str(temp_db))
    conn.execute('DELETE FROM weight_log')
    conn.execute("INSERT OR REPLACE INTO user_profile (id, age, gender, height_cm, activity_level) "
                 "VALUES (1, 30, 'male', 175, 'moderate')")
    conn.execute("INSERT OR REPLACE INTO daily_goal (id, calorie_goal) VALUES (1, 1800)")
    conn.commit()
    conn.close()
    sys.path.insert(0, str(SCRIPTS_DIR))
    import weight
    weight.log_weight(86.1, target_date='2026-08-05')
    yield


def _rgw():
    sys.path.insert(0, str(SCRIPTS_DIR))
    import render_goal_weight as rgw
    return rgw


def test_live_result_writes_and_returns_written(goal_env, temp_db):
    """写库字段必须完整回传(daily_goal 实际落库值)"""
    rgw = _rgw()
    data = rgw.build_live_result(69.9, deadline='2026-10-30',
                                 start_kg=86.1, start_date='2026-08-05')
    w = data['written']
    assert w['weight_goal'] == 69.9
    assert w['deadline'] == '2026-10-30'
    assert w['start_weight'] == 86.1
    assert w['start_date'] == '2026-08-05'
    conn = sqlite3.connect(str(temp_db))
    row = conn.execute('SELECT weight_goal, goal_deadline, start_weight, start_date FROM daily_goal WHERE id = 1').fetchone()
    conn.close()
    assert (row[0], row[1], row[2], row[3]) == (69.9, '2026-10-30', 86.1, '2026-08-05')


def test_live_result_progress_math(goal_env):
    """进度数据:#78 现场 — 差距 16.2kg / 剩余天数 = 今天→截止 / 速率带公式"""
    rgw = _rgw()
    data = rgw.build_live_result(69.9, deadline='2026-10-30',
                                 start_kg=86.1, start_date='2026-08-05')
    assert data['current_weight'] == 86.1
    assert data['gap'] == 16.2
    days_left = (date(2026, 10, 30) - date.today()).days
    assert data['days_left'] == days_left
    r = data['rate']
    assert r is not None
    assert r['days'] == days_left
    assert r['per_week'] == round(abs(data['gap']) / days_left * 7, 2)
    assert r['extreme'] is True
    assert f"{abs(data['gap']):.1f}kg ÷ {days_left}天 × 7" in r['formula']
    assert '已写入体重目标 69.9kg' in data['one_line']
    assert '极端目标' in data['one_line']


def test_live_result_journey_and_est_date(goal_env):
    """旅程进度条数据:起点→目标 完成% + 按 0.5kg/周 推算达成日(对抗审查 2026-08-05 补)"""
    rgw = _rgw()
    data = rgw.build_live_result(69.9, deadline='2026-10-30',
                                 start_kg=86.1, start_date='2026-08-05')
    j = data['journey']
    assert j is not None
    assert (j['start'], j['target'], j['current']) == (86.1, 69.9, 86.1)
    assert j['total'] == 16.2
    assert j['done'] == 0.0
    assert j['pct'] == 0.0
    assert data['est_date'] is not None
    from datetime import timedelta
    weeks = max(1, __import__('math').ceil(abs(data['gap']) / 0.5))
    assert data['est_date'] == (date.today() + timedelta(days=weeks * 7)).isoformat()


def test_live_result_journey_pct_after_loss(goal_env):
    """有进展后:当前 < 起点 → 完成% > 0"""
    rgw = _rgw()
    import weight
    weight.log_weight(85.0, target_date='2026-08-05')
    data = rgw.build_live_result(69.9, deadline='2026-10-30',
                                 start_kg=86.1, start_date='2026-08-05')
    j = data['journey']
    assert j['done'] == 1.1
    assert round(j['pct'], 1) == round(1.1 / 16.2 * 100, 1)


def test_live_result_without_deadline_no_rate(goal_env):
    """无截止日:rate=None(不产出孤立数字)"""
    rgw = _rgw()
    data = rgw.build_live_result(70.0, start_kg=86.1, start_date='2026-08-05')
    assert data['written']['weight_goal'] == 70.0
    assert data['days_left'] is None
    assert data['rate'] is None
    assert '速率' not in data['one_line']


def test_result_html_renders_written_and_warning(goal_env):
    """结果 HTML 必须包含:已写入标记 + 极端目标警示(issue #79 V1/V2)"""
    rgw = _rgw()
    data = rgw.build_live_result(69.9, deadline='2026-10-30',
                                 start_kg=86.1, start_date='2026-08-05')
    data['meta'] = {'wake_word': '定体重目标(含起始日)', 'chain': '1.解析→2.写库→3.回执',
                    'fetched_at': '2026-08-05 10:00', 'source': 'daily_goal',
                    'render_cmd': 'python scripts/render_goal_weight.py --live'}
    html = rgw.render_result_html(data)
    assert '已写入' in html
    assert '"extreme": true' in html
    assert '1.32 kg/周' in html
    assert '<div class="warn">' in html
    assert '写入时间' in html
    assert 'heroNum' in html
    assert 'journeyFill' in html
    assert 'scene_id' in html
    assert 'payload' in html


def test_result_html_ok_case(goal_env):
    """合理速率(带内):注入数据 extreme=false,速率文本走「速率合理」口径"""
    rgw = _rgw()
    from datetime import timedelta
    deadline = (date.today() + timedelta(days=45)).isoformat()
    data = rgw.build_live_result(83.0, deadline=deadline,
                                 start_kg=86.1, start_date='2026-08-05')
    assert data['rate'] is not None
    assert data['rate']['extreme'] is False
    assert data['rate']['ok'] is True
    data['meta'] = {'wake_word': '定体重目标', 'chain': '1.解析→2.写库→3.回执'}
    html = rgw.render_result_html(data)
    assert '"extreme": false' in html
    assert '速率合理' in html
