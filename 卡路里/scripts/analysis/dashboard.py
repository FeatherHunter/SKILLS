#!/usr/bin/env python3
"""综合健康报告 — 4 维度仪表盘

调用顺序：
1. 体重趋势（weight_trend）
2. 热量趋势（diet_calorie_trend）
3. 运动趋势（exercise_trend）
4. 热量缺口（diet_deficit_analysis）

每个维度独立 try/except，单个失败不影响其他维度输出。
"""

import sys
from pathlib import Path

from analysis._utils import _parse_date

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def dashboard(start_date, end_date=None):
    """综合健康报告

    Args:
        start_date: 开始日期
        end_date: 结束日期，可选
    """
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    print(f"""
{'='*55}
  📋 综合健康报告（{start_date} ~ {end_date}）
{'='*55}""")

    print("\n📊 体重趋势")
    try:
        from analysis.weight import weight_trend
        weight_trend(start_date, end_date)
    except Exception as e:
        print(f"  无法获取体重数据: {e}")

    print("\n🔥 热量趋势")
    try:
        from analysis.diet import diet_calorie_trend
        diet_calorie_trend(start_date, end_date)
    except Exception as e:
        print(f"  无法获取热量数据: {e}")

    print("\n🏃 运动趋势")
    try:
        from analysis.exercise import exercise_trend
        exercise_trend(start_date, end_date)
    except Exception as e:
        print(f"  无法获取运动数据: {e}")

    print("\n📉 热量缺口")
    try:
        from analysis.diet import diet_deficit_analysis
        diet_deficit_analysis(start_date, end_date)
    except Exception as e:
        print(f"  无法获取缺口数据: {e}")

    print(f"\n{'='*55}")