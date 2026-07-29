#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_weight_volatility_v2.py — ticket 01-05 seam 4 测试

ticket 01-05 · 2026-07-29

覆盖 spec.md §Testing Decisions 的 seam 4(10 case)。
tier 按 ticket 分组:01 (math) / 02-04 (dashboard) / 05 (CLI + integration)。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
TEMPLATE = SKILL_DIR / "templates" / "weight_volatility_v2.html"
RENDER = SCRIPTS_DIR / "render_weight_volatility_v2.py"


# ============= ticket 01:math + σ 算法 =============


def test_v2_detrended_sigma_calculation():
    """01: detrended σ 算法 — 用确定性 daily 数据验证

    用 7 个接近的数据(88.0 ± 0.1)验证 σ 应在 0.05-0.15 范围
    """
    from analysis.weight import weight_volatility_v2
    from unittest.mock import patch, MagicMock

    test_data = [
        ("2026-07-22", 88.0),
        ("2026-07-23", 88.1),
        ("2026-07-24", 87.9),
        ("2026-07-25", 88.0),
        ("2026-07-26", 88.1),
        ("2026-07-27", 88.0),
        ("2026-07-28", 88.0),
    ]
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = test_data
    mock_cursor.fetchone.return_value = (73.0,)
    mock_conn.cursor.return_value = mock_cursor

    with patch("analysis.weight._get_db", return_value=mock_conn):
        result = weight_volatility_v2("2026-07-22", "2026-07-28", baseline_mode="rolling")

    assert result["status"] == "ok"
    data = result["data"]
    assert 0.05 < data["baseline_sigma"] < 0.15, (
        f"detrended σ 应在 0.05-0.15,实得 {data['baseline_sigma']}"
    )
    expected_mean = sum(w for _, w in test_data) / len(test_data)
    assert abs(data["baseline_value"] - expected_mean) < 0.01


def test_v2_anomaly_thresholds_1p5_2p0_sigma():
    """01: thresholds = {yellow: 1.5σ, red: 2.0σ}"""
    from analysis.weight import weight_volatility_v2
    from unittest.mock import patch, MagicMock

    test_data = [(f"2026-07-{20+i}", 88.0 + (i % 3) * 0.1) for i in range(15)]
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = test_data
    mock_cursor.fetchone.return_value = (73.0,)
    mock_conn.cursor.return_value = mock_cursor

    with patch("analysis.weight._get_db", return_value=mock_conn):
        result = weight_volatility_v2("2026-07-20", "2026-08-03", baseline_mode="rolling")

    sigma = result["data"]["baseline_sigma"]
    thresholds = result["data"]["thresholds"]
    assert abs(thresholds["yellow"] - 1.5 * sigma) < 1e-9
    assert abs(thresholds["red"] - 2.0 * sigma) < 1e-9


def test_v2_returns_required_data_shape():
    """01: dict 含 spec §Implementation Decisions 要求的全部字段"""
    from analysis.weight import weight_volatility_v2
    from unittest.mock import patch, MagicMock

    test_data = [(f"2026-07-{20+i}", 88.0) for i in range(10)]
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = test_data
    mock_cursor.fetchone.return_value = (73.0,)
    mock_conn.cursor.return_value = mock_cursor

    with patch("analysis.weight._get_db", return_value=mock_conn):
        result = weight_volatility_v2("2026-07-20", "2026-07-30", baseline_mode="rolling")

    assert result["status"] == "ok"
    data = result["data"]
    required_fields = {
        "baseline_mode", "baseline_value", "baseline_sigma",
        "thresholds", "points", "recent_anomalies", "sigma_trend",
        "early_warning", "baseline_toggle_label",
    }
    missing = required_fields - set(data.keys())
    assert not missing, f"缺字段: {missing}"


def test_v2_baseline_toggle_rolling_vs_goal():
    """03/04: baseline_mode='rolling' vs 'goal' 返回不同 baseline_value"""
    from analysis.weight import weight_volatility_v2
    from unittest.mock import patch, MagicMock

    test_data = [(f"2026-07-{20+i}", 88.0) for i in range(15)]
    goal_row = (73.0,)

    # rolling mode
    mock_conn_r = MagicMock()
    mock_cursor_r = MagicMock()
    mock_cursor_r.fetchall.return_value = test_data
    mock_cursor_r.fetchone.return_value = goal_row
    mock_conn_r.cursor.return_value = mock_cursor_r

    with patch("analysis.weight._get_db", return_value=mock_conn_r):
        result_rolling = weight_volatility_v2("2026-07-20", "2026-08-03", baseline_mode="rolling")

    # goal mode
    mock_conn_g = MagicMock()
    mock_cursor_g = MagicMock()
    mock_cursor_g.fetchall.return_value = test_data
    mock_cursor_g.fetchone.return_value = goal_row
    mock_conn_g.cursor.return_value = mock_cursor_g

    with patch("analysis.weight._get_db", return_value=mock_conn_g):
        result_goal = weight_volatility_v2("2026-07-20", "2026-08-03", baseline_mode="goal")

    assert result_rolling["data"]["baseline_value"] == 88.0
    assert result_goal["data"]["baseline_value"] == 73.0


def test_v2_recent_anomalies_window_7_days():
    """03: recent_anomalies 只含最近 7 天"""
    from analysis.weight import weight_volatility_v2
    from unittest.mock import patch, MagicMock

    test_data = [
        ("2026-07-01", 88.0),
        ("2026-07-10", 88.0),
        ("2026-07-20", 88.0),
        ("2026-07-25", 88.0),
        ("2026-07-26", 95.0),  # 异常 +7kg
        ("2026-07-27", 81.0),  # 异常 -7kg
        ("2026-07-28", 88.0),
    ]
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = test_data
    mock_cursor.fetchone.return_value = (73.0,)
    mock_conn.cursor.return_value = mock_cursor

    with patch("analysis.weight._get_db", return_value=mock_conn):
        result = weight_volatility_v2("2026-07-20", "2026-07-30", baseline_mode="rolling")

    recent = result["data"]["recent_anomalies"]
    for anomaly in recent:
        assert anomaly["date"] >= "2026-07-22", (
            f"recent_anomaly date {anomaly['date']} 不在最近 7 天内"
        )