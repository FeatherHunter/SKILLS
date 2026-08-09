#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_diet_batch_meal_receipt.py — 同餐多食物合并回执(issue #158 · 2026-08-09)

现象:用户「中午吃米饭、清蒸鱼、炒青菜、豆腐汤」→ AI 逐个调 add → N 个回执。
修复:--live-diet-batch-meal 一次写库 N 条 + 单一回执(食物列表 + 营养合计 + 调用透明)。

本测试锁住:
- V1:同餐 ≥2 食物 → 单一回执数据(1 个 data,内含全部食物)
- V3:summary 含「合并 1 个回执」透明度
- V4:回执含 食物列表 items + 总卡/总蛋白/总碳水/总脂肪
"""
import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))


@pytest.fixture()
def meal_input(temp_db):
    """生成同餐多食物输入 JSON 文件(米饭+清蒸鱼+青菜)"""
    entries = [
        {'food_name': '米饭', 'grams': 200, 'calories': 232, 'protein': 4.3, 'carbs': 50, 'fat': 0.5,
         'date': '2026-08-09', 'time': '12:30:00'},
        {'food_name': '清蒸鱼', 'grams': 150, 'calories': 165, 'protein': 28, 'carbs': 0, 'fat': 6,
         'date': '2026-08-09', 'time': '12:30:00'},
        {'food_name': '炒青菜', 'grams': 200, 'calories': 60, 'protein': 2, 'carbs': 6, 'fat': 3,
         'date': '2026-08-09', 'time': '12:30:00'},
    ]
    p = Path(temp_db.parent) / 'meal_input.json'
    p.write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')
    yield str(p)
    p.unlink(missing_ok=True)


def test_batch_meal_single_receipt_with_all_foods(meal_input):
    """V1+V4:同餐 3 食物 → 1 个回执,含全部食物列表 + 营养合计"""
    import render_crud_receipt as rcr
    data = rcr.build_live_diet_batch_meal(meal_input)
    assert data['status'] == 'ok'
    items = data['data']['context']['items']
    assert len(items) == 3, f'回执必须含全部 3 个食物,实际 {len(items)}'
    foods = {it['food_name'] for it in items}
    assert foods == {'米饭', '清蒸鱼', '炒青菜'}
    # 营养合计:232+165+60 = 457 卡;蛋白 4.3+28+2 = 34.3
    kpis = {k['label']: k['value'] for k in data['data']['context']['kpis']}
    assert kpis['总热量'] == '457 卡'
    assert kpis['总蛋白'] == '34.3 g'
    assert kpis['食物数'] == '3 种'


def test_batch_meal_v3_transparency(meal_input):
    """V3:调用透明 — summary 必须说明写库 N 条合并 1 个回执"""
    import render_crud_receipt as rcr
    data = rcr.build_live_diet_batch_meal(meal_input)
    assert '合并 1 个回执' in data['data']['summary']
    assert '写库 3 条' in data['data']['summary']


def test_batch_meal_skipped_partial(meal_input, temp_db):
    """异常条目(负卡路里)跳过,但回执仍含成功食物 + 跳过提示"""
    import render_crud_receipt as rcr
    entries = [
        {'food_name': '米饭', 'grams': 200, 'calories': 232, 'protein': 4.3, 'carbs': 50, 'fat': 0.5,
         'date': '2026-08-09', 'time': '13:00:00'},
        {'food_name': '坏数据', 'grams': 100, 'calories': -5, 'protein': 1, 'carbs': 0, 'fat': 0,
         'date': '2026-08-09', 'time': '13:00:00'},
    ]
    p = Path(temp_db.parent) / 'meal_input2.json'
    p.write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')
    data = rcr.build_live_diet_batch_meal(str(p))
    items = data['data']['context']['items']
    assert len(items) == 1 and items[0]['food_name'] == '米饭'
    assert '跳过 1 条' in data['data']['summary']
    p.unlink(missing_ok=True)


def test_batch_meal_empty_input_rejected(meal_input):
    """空数组必须拒绝(不产生空回执)"""
    import render_crud_receipt as rcr
    p = Path(meal_input).parent / 'empty.json'
    p.write_text('[]', encoding='utf-8')
    with pytest.raises(ValueError):
        rcr.build_live_diet_batch_meal(str(p))
    p.unlink(missing_ok=True)
