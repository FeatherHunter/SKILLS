#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_goal_weight_rate.py — 体重目标速率计算回归(issue #78 · 2026-08-05)

现象:用户设定 目标 69.9 / 当前 86.1 / 截止 2026-10-30(86 天),
AI 心算编出「16.2/86 = 1.32 kg 每月」(无公式、单位错)。
修复:代码算速率带公式(16.2kg ÷ 86天 × 7 = 1.32 kg/周 ≈ 5.7 kg/月),
AI 只回显。本测试锁住 build_rate_info 纯函数契约。

⚠️ import 必须放在测试函数内(conftest 惯例):render_goal_weight 链式导入
weight_goal 时会在模块级解析 DB_PATH,若在收集期导入会指向生产库。
"""
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


def _rate():
    sys.path.insert(0, str(SCRIPTS_DIR))
    import render_goal_weight as rgw
    return rgw


def test_rate_user_case_issue78():
    """issue 现场:16.2kg 差距 / 86 天 → 1.32 kg/周 ≈ 5.7 kg/月,极端目标"""
    rgw = _rate()
    r = rgw.build_rate_info(16.2, 86)
    assert r is not None
    assert r['per_week'] == 1.32
    assert r['per_month'] == 5.7
    assert r['ok'] is False
    assert r['extreme'] is True
    assert '16.2kg ÷ 86天 × 7' in r['formula']


def test_rate_ok_band():
    """合理带内:5kg / 70 天 → 0.5 kg/周,ok 且非极端"""
    rgw = _rate()
    r = rgw.build_rate_info(5.0, 70)
    assert r['per_week'] == 0.5
    assert r['per_month'] == 2.2
    assert r['ok'] is True
    assert r['extreme'] is False
    assert '速率合理' in r['text']


def test_rate_extreme_boundary_at_1_0():
    """阈值边界:恰 1.0 kg/周(精确数学)必须判极端(V2:>= 1.0 即警示)"""
    rgw = _rate()
    r = rgw.build_rate_info(7.0, 49)
    assert r['per_week'] == 1.0
    assert r['extreme'] is True
    assert '这是极端目标' in r['text']
    assert '健康带 0.25–1.0' in r['text']
    r2 = rgw.build_rate_info(7.5, 49)
    assert r2['per_week'] == 1.07
    assert r2['extreme'] is True


def test_rate_slow_below_band():
    """低于 0.25:非极端但 ok=False,提示达成周期偏长"""
    rgw = _rate()
    r = rgw.build_rate_info(1.0, 60)
    assert r['per_week'] == 0.12
    assert r['extreme'] is False
    assert r['ok'] is False


def test_rate_sign_direction():
    """符号语义:正=需减(减重),负=需增(增肌)"""
    rgw = _rate()
    r_loss = rgw.build_rate_info(3.0, 42)
    r_gain = rgw.build_rate_info(-3.0, 42)
    assert r_loss['per_week'] == r_gain['per_week'] == 0.5


def test_rate_invalid_inputs():
    """参数不足 → None(禁止抛错/产出孤立数字)"""
    rgw = _rate()
    assert rgw.build_rate_info(None, 86) is None
    assert rgw.build_rate_info(16.2, None) is None
    assert rgw.build_rate_info(16.2, 0) is None
    assert rgw.build_rate_info(16.2, -7) is None


def test_days_until():
    rgw = _rate()
    assert rgw._days_until('2026-08-06') == (date(2026, 8, 6) - date.today()).days
    assert rgw._days_until('bad-date') is None
    assert rgw._days_until('') is None
    assert rgw._days_until(None) is None
