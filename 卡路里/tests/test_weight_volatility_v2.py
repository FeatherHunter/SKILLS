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
from datetime import date, timedelta
from pathlib import Path

import pytest
import sqlite3

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


def test_v2_goal_sigma_uses_full_range_not_7day():
    """01 fix: goal mode 用全程 detrended σ(不依赖时间窗)

    Spec §Implementation Decisions:"goal: 全程 detrended σ(goal 不依赖时间窗)".
    之前的实现在两种 mode 都用 7-day rolling σ(goal mode 也只用最后 7 天),
    违反 spec. 此测试守住 fix.

    数据构造:
      - 前 7 天:85 → 90(快速减重 phase)
      - 后 7 天:90 → 90(稳定 phase)
    - rolling σ(后 7 天)≈ 0
    - goal σ(全程 14 天 detrended diffs)≈ 大(因为前半段有 +5kg 跳变)
    """
    from analysis.weight import weight_volatility_v2
    from unittest.mock import patch, MagicMock

    test_data = (
        [(f"2026-07-{1+i}", 85.0 + i * 0.5) for i in range(7)]  # 85.0..88.0
        + [(f"2026-07-{8+i}", 90.0) for i in range(7)]  # 全 90
    )
    goal_row = (73.0,)

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = test_data
    mock_cursor.fetchone.return_value = goal_row
    mock_conn.cursor.return_value = mock_cursor

    with patch("analysis.weight._get_db", return_value=mock_conn):
        result_rolling = weight_volatility_v2("2026-07-01", "2026-07-14", baseline_mode="rolling")
        result_goal = weight_volatility_v2("2026-07-01", "2026-07-14", baseline_mode="goal")

    sigma_rolling = result_rolling["data"]["baseline_sigma"]
    sigma_goal = result_goal["data"]["baseline_sigma"]
    # rolling(后 7 天 diff 全 0)→ 0
    # goal(全程 13 个 diff:前半段 +0.5,后半段 0)→ σ > 0
    assert sigma_rolling < 0.1, f"rolling sigma 应 < 0.1(后 7 天平),实得 {sigma_rolling}"
    assert sigma_goal > 0.5, f"goal sigma 应 > 0.5(全程含大幅变化),实得 {sigma_goal}"
    assert sigma_goal > sigma_rolling * 10, (
        f"goal sigma 应远大于 rolling(因全程含变化),rolling={sigma_rolling}, goal={sigma_goal}"
    )


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


# ============= ticket 05:CLI + --text + 触发词 =============


def _seed_weight_data(temp_db, days=20):
    """在 temp_db 注入 N 天 daily 体重数据(v2 render 测试用)"""
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("DELETE FROM weight_log")
    for i in range(days):
        d = (date.today() - timedelta(days=days - i - 1)).strftime("%Y-%m-%d")
        kg = 88.0 + (i % 3) * 0.2 - (i // 5) * 0.3  # 小幅波动
        cur.execute(
            "INSERT INTO weight_log(date, time, weight_kg) VALUES (?, '12:00:00', ?)",
            (d, kg),
        )
    conn.commit()
    conn.close()


def test_v2_render_exits_zero(temp_db, tmp_path):
    """05: seam 4 test 2 — render_weight_volatility_v2.py exit 0 + HTML 生成"""
    import os
    RENDER = Path(__file__).resolve().parent.parent / "scripts" / "render_weight_volatility_v2.py"
    assert RENDER.exists(), f"render 脚本缺失: {RENDER}"
    _seed_weight_data(temp_db, days=20)

    out = tmp_path / "food_v2.html"
    r = subprocess.run(
        [sys.executable, str(RENDER), "--output", str(out)],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
        env={**os.environ},
    )
    assert r.returncode == 0, f"render exit {r.returncode}, stderr={r.stderr[:300]}"
    assert out.exists(), f"output HTML 不存在: {out}"
    assert "ACTION=SEND_TO_USER" in r.stdout, f"stdout 应含 ACTION=SEND_TO_USER: {r.stdout[:300]}"


def test_v2_does_not_write_db(temp_db, tmp_path):
    """05: seam 4 test 7 — 跑 render 后 weight_log 记录数不变(纯只读)"""
    import os
    RENDER = Path(__file__).resolve().parent.parent / "scripts" / "render_weight_volatility_v2.py"
    _seed_weight_data(temp_db, days=20)

    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM weight_log")
    before = cur.fetchone()[0]
    conn.close()

    r = subprocess.run(
        [sys.executable, str(RENDER), "--output", str(tmp_path / "x.html")],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
        env={**os.environ},
    )
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM weight_log")
    after = cur.fetchone()[0]
    conn.close()
    assert before == after, f"weight_log 变化:before={before}, after={after}"


def test_v2_text_mode_emits_plain_text(temp_db, tmp_path):
    """05: seam 4 test 8 — `--text` exit 0 + stdout 非 HTML"""
    import os
    RENDER = Path(__file__).resolve().parent.parent / "scripts" / "render_weight_volatility_v2.py"
    _seed_weight_data(temp_db, days=20)

    r = subprocess.run(
        [sys.executable, str(RENDER), "--text"],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=30,
        env={**os.environ},
    )
    assert r.returncode == 0, f"--text exit {r.returncode}, stderr={r.stderr[:300]}"
    assert "<!DOCTYPE" not in r.stdout and "<html" not in r.stdout, (
        f"--text 模式应非 HTML: {r.stdout[:200]}"
    )
    assert "MODE=text" in r.stdout, f"--text 应有 MODE 标识: {r.stdout[:200]}"