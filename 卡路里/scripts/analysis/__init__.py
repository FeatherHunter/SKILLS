#!/usr/bin/env python3
"""分析模块 — 11 维分析 + 4 统一入口

统一入口（推荐使用）：
- weight_analysis(start, end, type)   — 体重分析
    type: trend | compare | milestone | volatility
- diet_analysis(start, end, type)     — 饮食分析
    type: calorie_trend | macro_ratio | food_ranking | deficit_analysis
- exercise_analysis(start, end, type) — 运动分析
    type: exercise_trend | type_breakdown | deficit_contribution
- dashboard(start, end)               — 综合报告

直接调用 11 个分析函数（按领域拆分到子模块）：
- analysis.weight:      weight_trend / weight_compare / weight_milestone / weight_volatility
- analysis.diet:        diet_calorie_trend / diet_macro_ratio / diet_food_ranking / diet_deficit_analysis
- analysis.exercise:    exercise_trend / exercise_type_breakdown / exercise_deficit_contribution
- analysis.dashboard:   dashboard
"""

from datetime import datetime, timedelta

from analysis._utils import _parse_date, _days_between
from analysis.weight import (
    weight_trend,
    weight_compare,
    weight_milestone,
    weight_volatility,
)
from analysis.diet import (
    diet_calorie_trend,
    diet_macro_ratio,
    diet_food_ranking,
    diet_deficit_analysis,
)
from analysis.exercise import (
    exercise_trend,
    exercise_type_breakdown,
    exercise_deficit_contribution,
    exercise_review,
)
from analysis.dashboard import dashboard


def weight_analysis(start_date, end_date=None, analysis_type='trend',
                    compare_start=None, compare_end=None, as_dict=False):
    """体重分析统一入口

    Args:
        as_dict: True 返回 dict；False print（默认）
    """
    if analysis_type == 'trend':
        return weight_trend(start_date, end_date, as_dict=as_dict)
    elif analysis_type == 'compare':
        if compare_start and compare_end:
            return weight_compare(start_date, end_date or start_date,
                                  compare_start, compare_end, as_dict=as_dict)
        else:
            span = _days_between(start_date, end_date or start_date)
            end_dt = datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)
            cs = (end_dt - timedelta(days=span)).strftime('%Y-%m-%d')
            ce = end_dt.strftime('%Y-%m-%d')
            return weight_compare(start_date, end_date or start_date, cs, ce, as_dict=as_dict)
    elif analysis_type == 'milestone':
        return weight_milestone(as_dict=as_dict)
    elif analysis_type == 'volatility':
        return weight_volatility(start_date, end_date, as_dict=as_dict)
    else:
        if not as_dict:
            print(f"⚠️ 未知分析类型: {analysis_type}，使用趋势分析")
        return weight_trend(start_date, end_date, as_dict=as_dict)


def diet_analysis(start_date, end_date=None, analysis_type='calorie_trend', as_dict=False, **kwargs):
    """饮食分析统一入口

    Args:
        as_dict: True 返回 dict；False print（默认）
        **kwargs: 传给底层函数（如 food_ranking 的 category / top_n）
    """
    if analysis_type == 'calorie_trend':
        return diet_calorie_trend(start_date, end_date, as_dict=as_dict)
    elif analysis_type == 'macro_ratio':
        return diet_macro_ratio(start_date, end_date, as_dict=as_dict)
    elif analysis_type == 'food_ranking':
        return diet_food_ranking(start_date, end_date, as_dict=as_dict, **kwargs)
    elif analysis_type == 'deficit_analysis':
        return diet_deficit_analysis(start_date, end_date, as_dict=as_dict)
    else:
        if not as_dict:
            print(f"⚠️ 未知分析类型: {analysis_type}，使用热量趋势")
        return diet_calorie_trend(start_date, end_date, as_dict=as_dict)


def exercise_analysis(start_date, end_date=None, analysis_type='exercise_trend', as_dict=False, silent=False):
    """运动分析统一入口

    Args:
        as_dict: True 返回 dict；False print（默认）
        silent: 兼容旧调用，exercise_review 用
    """
    if analysis_type == 'exercise_trend':
        return exercise_trend(start_date, end_date, as_dict=as_dict)
    elif analysis_type == 'type_breakdown':
        return exercise_type_breakdown(start_date, end_date, as_dict=as_dict)
    elif analysis_type == 'deficit_contribution':
        return exercise_deficit_contribution(start_date, end_date, as_dict=as_dict)
    elif analysis_type == 'review':
        return exercise_review(start_date, end_date, as_dict=as_dict, silent=silent)
    else:
        if not as_dict:
            print(f"⚠️ 未知分析类型: {analysis_type}，使用运动趋势")
        return exercise_trend(start_date, end_date, as_dict=as_dict)


__all__ = [
    # 4 统一入口
    'weight_analysis',
    'diet_analysis',
    'exercise_analysis',
    'dashboard',
    # 11 个原子函数
    'weight_trend', 'weight_compare', 'weight_milestone', 'weight_volatility',
    'diet_calorie_trend', 'diet_macro_ratio', 'diet_food_ranking', 'diet_deficit_analysis',
    'exercise_trend', 'exercise_type_breakdown', 'exercise_deficit_contribution',
    'exercise_review',
]