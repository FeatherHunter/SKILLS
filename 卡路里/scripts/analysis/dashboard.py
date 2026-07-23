#!/usr/bin/env python3
"""综合健康报告 — 4 维度仪表盘

调用顺序：
1. 体重趋势（weight_trend）
2. 热量趋势（diet_calorie_trend）
3. 运动趋势（exercise_trend）
4. 热量缺口（diet_deficit_analysis）

每个维度独立 try/except，单个失败不影响其他维度输出。

2026-07-23 D1 重构：加 as_dict=False 参数
- as_dict=True → 返回结构化 dict（合并 4 维）
- as_dict=False → 保持原 print（向后兼容）
"""
import sys
from pathlib import Path

from analysis._utils import _parse_date

_scripts_dir = str(Path(__file__).resolve().parent.parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


def dashboard(start_date, end_date=None, as_dict=False):
    """综合健康报告

    Args:
        start_date: 开始日期
        end_date: 结束日期，可选
        as_dict: True 返回 dict；False print（默认）
    """
    start_date = _parse_date(start_date)
    end_date = _parse_date(end_date) or start_date

    # 2026-07-23 D1 增：聚合 4 维 dict
    dims = {}
    if as_dict:
        for name, fn in [
            ('weight', lambda: __import__('analysis.weight', fromlist=['weight_trend']).weight_trend(start_date, end_date, as_dict=True)),
            ('calorie', lambda: __import__('analysis.diet', fromlist=['diet_calorie_trend']).diet_calorie_trend(start_date, end_date, as_dict=True)),
            ('exercise', lambda: __import__('analysis.exercise', fromlist=['exercise_trend']).exercise_trend(start_date, end_date, as_dict=True)),
            ('deficit', lambda: __import__('analysis.diet', fromlist=['diet_deficit_analysis']).diet_deficit_analysis(start_date, end_date, as_dict=True)),
        ]:
            try:
                dims[name] = fn()
            except Exception as e:
                dims[name] = {"status": "error", "data": None, "message": str(e)}

        # 任一维度失败 → status=warn
        overall_status = "ok"
        for d in dims.values():
            if d.get("status") == "error":
                overall_status = "warn"
                break

        return {
            "status": overall_status,
            "data": {
                "start": start_date,
                "end": end_date,
                "weight": dims.get('weight', {}).get('data'),
                "calorie": dims.get('calorie', {}).get('data'),
                "exercise": dims.get('exercise', {}).get('data'),
                "deficit": dims.get('deficit', {}).get('data'),
            },
            "message": f"健康报告 {start_date} ~ {end_date}",
        }

    # 原 print 行为（向后兼容）
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