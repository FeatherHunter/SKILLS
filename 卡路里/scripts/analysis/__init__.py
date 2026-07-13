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
                    compare_start=None, compare_end=None):
    """体重分析统一入口

    Args:
        start_date: 开始日期
        end_date: 结束日期（可选，默认同 start_date 单日）
        analysis_type: 分析类型
            - 'trend'      趋势分析（均重/日均变化/趋势判断）
            - 'compare'    同期对比（需 compare_start/compare_end，可选默认上一周期）
            - 'milestone'  目标进度（预计达成日/状态）
            - 'volatility' 波动分析（标准差/异常记录）
        compare_start: 对比期开始日期（compare 模式可选）
        compare_end:   对比期结束日期（compare 模式可选）
    """
    if analysis_type == 'trend':
        return weight_trend(start_date, end_date)
    elif analysis_type == 'compare':
        if compare_start and compare_end:
            return weight_compare(start_date, end_date or start_date,
                                  compare_start, compare_end)
        else:
            # 默认与上一个等长周期对比
            span = _days_between(start_date, end_date or start_date)
            end_dt = datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)
            cs = (end_dt - timedelta(days=span)).strftime('%Y-%m-%d')
            ce = end_dt.strftime('%Y-%m-%d')
            return weight_compare(start_date, end_date or start_date, cs, ce)
    elif analysis_type == 'milestone':
        return weight_milestone()
    elif analysis_type == 'volatility':
        return weight_volatility(start_date, end_date)
    else:
        print(f"⚠️ 未知分析类型: {analysis_type}，使用趋势分析")
        return weight_trend(start_date, end_date)


def diet_analysis(start_date, end_date=None, analysis_type='calorie_trend'):
    """饮食分析统一入口

    Args:
        start_date: 开始日期
        end_date: 结束日期
        analysis_type: 分析类型
            - 'calorie_trend'    热量趋势（工作日 vs 周末 / 合规率）
            - 'macro_ratio'      营养素占比（蛋白/碳水/脂肪）
            - 'food_ranking'     食物 TOP 榜（默认 high_calorie）
            - 'deficit_analysis' 热量缺口（饮食 + 运动贡献）
    """
    if analysis_type == 'calorie_trend':
        return diet_calorie_trend(start_date, end_date)
    elif analysis_type == 'macro_ratio':
        return diet_macro_ratio(start_date, end_date)
    elif analysis_type == 'food_ranking':
        return diet_food_ranking(start_date, end_date, category='high_calorie')
    elif analysis_type == 'deficit_analysis':
        return diet_deficit_analysis(start_date, end_date)
    else:
        print(f"⚠️ 未知分析类型: {analysis_type}，使用热量趋势")
        return diet_calorie_trend(start_date, end_date)


def exercise_analysis(start_date, end_date=None, analysis_type='exercise_trend'):
    """运动分析统一入口

    Args:
        start_date: 开始日期
        end_date: 结束日期
        analysis_type: 分析类型
            - 'exercise_trend'         运动趋势（天数/时长/消耗/间隔）
            - 'type_breakdown'         运动类型分布（消耗/频次/时长占比）
            - 'deficit_contribution'   运动对缺口的贡献占比
            - 'review'                 复盘训练（计划 vs 实绩对比）
    """
    if analysis_type == 'exercise_trend':
        return exercise_trend(start_date, end_date)
    elif analysis_type == 'type_breakdown':
        return exercise_type_breakdown(start_date, end_date)
    elif analysis_type == 'deficit_contribution':
        return exercise_deficit_contribution(start_date, end_date)
    elif analysis_type == 'review':
        return exercise_review(start_date, end_date)
    else:
        print(f"⚠️ 未知分析类型: {analysis_type}，使用运动趋势")
        return exercise_trend(start_date, end_date)


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