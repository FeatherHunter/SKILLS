# -*- coding: utf-8 -*-
"""#357 实施 map · #359 决议开启清单守卫（T3 · 2026-08-14）

判据（#359 决议 · 对抗式审查换轴）: 量型指标（体重/体脂/围度/摄入/饮水/钠糖纤维/缺口）
缺记录日 = 未采样 → connectNulls 连线; 事件型指标（运动）缺日 = 真实 0 → 0 归一;
无 null 模板（仅记录日/0 填充/双边对齐/滤 null）→ 不开启（物理 no-op）。

- 开启 5: six_factors / health_report / combined_analysis / long_trend / nutrition_analysis
- 不开 14: 体重类仅记录日 6 + 0 填充 4 + 其他 4（exercise_summary/exercise_review/cross_skill_sleep/predict_report）
"""
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES = SKILL_DIR / 'templates'

ENABLED = [
    'six_factors.html',
    'health_report.html',
    'combined_analysis.html',
    'long_trend.html',
    'nutrition_analysis.html',
]
DISABLED = [
    'weight_dashboard.html', 'weight_review.html', 'weight_history.html',
    'weight_log_receipt.html', 'body_composition_view.html', 'body_measurements_view.html',
    'calorie_trend.html', 'calorie_deficit.html', 'home_dashboard.html', 'goal_progress.html',
    'exercise_summary.html', 'exercise_review.html', 'cross_skill_sleep.html', 'predict_report.html',
]


@pytest.mark.parametrize('name', ENABLED)
def test_connect_nulls_enabled(name):
    """清单内模板必须显式开启 connectNulls: true（#359 决议）"""
    src = (TEMPLATES / name).read_text(encoding='utf-8')
    assert 'connectNulls: true' in src, f'{name} 应开启 connectNulls: true（#359 决议）'


@pytest.mark.parametrize('name', DISABLED)
def test_connect_nulls_not_enabled(name):
    """清单外模板不得含 connectNulls（#359 决议 · 无 null 物理 no-op）"""
    src = (TEMPLATES / name).read_text(encoding='utf-8')
    assert 'connectNulls' not in src, f'{name} 不应开启 connectNulls（#359 决议）'


def test_exercise_zero_fill_in_mixed_charts():
    """混合图（含运动序列）必须做事件型 0 归一, 防止休息日被 connectNulls 伪造成连续运动"""
    for name in ('six_factors.html', 'health_report.html'):
        src = (TEMPLATES / name).read_text(encoding='utf-8')
        assert 'zeroFill' in src, f'{name} 运动序列应 0 归一（#359 决议 Q2）'
    src = (TEMPLATES / 'combined_analysis.html').read_text(encoding='utf-8')
    assert 'bExercise' in src, 'combined_analysis 运动侧应 0 归一（#359 决议 Q2）'
    src = (TEMPLATES / 'long_trend.html').read_text(encoding='utf-8')
    assert 'EX_FIELDS' in src, 'long_trend 运动域应 0 归一（#359 决议 Q2）'
