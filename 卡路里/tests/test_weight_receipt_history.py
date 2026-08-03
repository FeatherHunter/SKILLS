#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_weight_receipt_history.py — 记体重回执趋势图数据序回归(ticket #43 · 场景 1 人工终审)

L5 缺陷(2026-08-03 发现):_latest_history 返回 oldest→newest,而模板
weight_log_receipt.html 的 JS 假设 newest→oldest(newestW = HISTORY[0])
→ 趋势方向反 / 距目标算错 / 橙色「最新记录」点标在最旧点。
修复:render_weight_receipt._latest_history 去掉 reversed(rows)。
本测试锁住数据契约:history[0] 必须是刚写入的最新记录。
"""
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))


@pytest.fixture()
def clean_weight_log(temp_db):
    conn = sqlite3.connect(str(temp_db))
    conn.execute('DELETE FROM weight_log')
    conn.execute("INSERT OR REPLACE INTO user_profile (id, age, gender, height_cm, activity_level) "
                 "VALUES (1, 30, 'male', 175, 'moderate')")
    conn.execute("INSERT OR REPLACE INTO daily_goal (id, calorie_goal, weight_goal) "
                 "VALUES (1, 1800, 68.0)")
    conn.commit()
    conn.close()
    yield


def _test_build_receipt_impl(clean_weight_log, temp_db):
    import render_weight_receipt as rwr
    import weight

    weight.log_weight(69.0, target_date='2026-07-30')
    weight.log_weight(68.5, target_date='2026-07-31')
    weight.log_weight(68.2, target_date='2026-08-01')
    data = rwr.build_live_receipt(68.0)
    return data


def test_receipt_history_newest_first(clean_weight_log, temp_db):
    """history 必须 newest→oldest(模板 JS 契约:newestW = HISTORY[0])"""
    data = _test_build_receipt_impl(clean_weight_log, temp_db)
    dates = [h['date'] for h in data['history']]
    assert dates == sorted(dates, reverse=True), f'history 必须按日期降序,实际 {dates}'


def test_receipt_history_first_is_just_written(clean_weight_log, temp_db):
    """history[0] = 刚写入的记录(模板据此算趋势方向/距目标)"""
    data = _test_build_receipt_impl(clean_weight_log, temp_db)
    assert data['history'][0]['weight_kg'] == 68.0
    assert data['history'][-1]['weight_kg'] == 69.0


def test_receipt_goal_diff_uses_latest(clean_weight_log, temp_db):
    """距目标必须按最新体重算(68.0 - 68.0 = 0.0),不得用最旧(69.0-68.0=1.0)"""
    data = _test_build_receipt_impl(clean_weight_log, temp_db)
    assert data['summary']['goal_diff'] == 0.0
