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
from datetime import date, timedelta
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

    today = date.today()
    weight.log_weight(69.0, target_date=(today - timedelta(days=9)).isoformat())
    weight.log_weight(68.5, target_date=(today - timedelta(days=8)).isoformat())
    weight.log_weight(68.2, target_date=(today - timedelta(days=7)).isoformat())
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


def test_receipt_history_window_excludes_old(clean_weight_log, temp_db):
    """issue #198:近 30 天窗口过滤 —— 31+ 天前的记录不得进入 history

    此前 SQL 只取最新 30 条无日期过滤,稀疏记录时横跨远超 30 天
    (x 轴出现更早月份,用户实测 2026-08-08:最新 30 条跨 44 天)。
    """
    import render_weight_receipt as rwr
    import weight

    today = date.today()
    # 窗口内(近 30 天)1 条 + 窗口外(40 天前)1 条 —— 稀疏记录场景
    weight.log_weight(70.0, target_date=(today - timedelta(days=40)).isoformat())
    weight.log_weight(68.0, target_date=today.isoformat())
    data = rwr.build_live_receipt(67.8)  # 写库本身再记一条今天
    dates = [h['date'] for h in data['history']]
    assert dates == [today.isoformat(), today.isoformat()], f'窗口外记录必须被过滤,实际 {dates}'
    assert data['summary']['new_record']['weight_kg'] == 67.8


def test_receipt_history_window_boundary_29_days(clean_weight_log, temp_db):
    """窗口边界:第 30 天前(day=30)应排除,day=29 应保留

    窗口语义:date >= today - 30 天(含 30 天前当天,共 31 个日期?不——
    按 _latest_history 实现 today-30 天起算,day=29 保留、day=31 排除)。
    """
    import render_weight_receipt as rwr
    import weight

    today = date.today()
    weight.log_weight(70.0, target_date=(today - timedelta(days=31)).isoformat())
    weight.log_weight(69.5, target_date=(today - timedelta(days=29)).isoformat())
    weight.log_weight(68.0, target_date=today.isoformat())
    data = rwr.build_live_receipt(67.8)
    dates = [h['date'] for h in data['history']]
    assert (today - timedelta(days=31)).isoformat() not in dates, '31 天前应被过滤'
    assert (today - timedelta(days=29)).isoformat() in dates, '29 天前应保留'
