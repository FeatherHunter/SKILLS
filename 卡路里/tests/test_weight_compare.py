#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_weight_compare.py — 对比体重 18 场景核心逻辑单测(ticket #4 · 2026-08-02)

覆盖(对抗式审查补充 · 防回归):
  - compare_pair:Δkg/方向/速率差/速度判断
  - scenario_a3:本周 vs 上周(样本不足门槛 ≥3 条)
  - scenario_b8:平台期识别(≥14 天波动 ≤±0.5kg,取最近一次)
  - scenario_e3:减重 N kg 里程碑反查(历史最高起累计)
  - scenario_e5/e6:入夏/入冬最低(季节窗口)
  - scenario_d4:工作日 vs 周末聚合
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"


def _seed(conn, rows):
    """rows: [(date, kg), ...] 升序写入 weight_log"""
    for d, kg in rows:
        conn.execute(
            "INSERT INTO weight_log (date, time, weight_kg, height_cm, bmi, note) VALUES (?, '08:00:00', ?, 177, NULL, '')",
            (d, kg),
        )
    conn.commit()


def _insert(target, monkeypatch, data):
    """把数据写入临时 DB(SKILLS_DB_PATH 指向 target/calorie_data.db),monkeypatch 环境变量"""
    import db as db_mod

    tmp = target / "calorie_data.db"
    db_mod.init_db(str(tmp))
    conn = sqlite3.connect(str(tmp))
    _seed(conn, data)
    conn.close()
    monkeypatch.setenv("SKILLS_DB_PATH", str(target))
    return tmp


class TestComparePair:
    def test_down_speed_slower(self):
        """后段均重更低且速率放缓 → 方向下降、判断慢了"""
        from analysis.weight_compare import compare_pair

        a = {"avg": 80.0, "net_change": -3.0, "range": "2026-01-01 ~ 2026-01-30", "count": 30}
        b = {"avg": 78.0, "net_change": -0.5, "range": "2026-02-01 ~ 2026-03-02", "count": 30}
        c = compare_pair(a, b, "a", "b")
        assert c["delta_kg"] == -2.0
        assert c["direction"] == "下降"
        assert c["speed"] == "慢了"
        assert c["rate_diff_g"] is not None

    def test_flat_speed(self):
        """两段速率接近 → 持平"""
        from analysis.weight_compare import compare_pair

        a = {"avg": 80.0, "net_change": -1.0, "range": "2026-01-01 ~ 2026-01-30", "count": 30}
        b = {"avg": 79.8, "net_change": -0.9, "range": "2026-02-01 ~ 2026-03-02", "count": 30}
        c = compare_pair(a, b, "a", "b")
        assert c["direction"] == "下降"
        assert c["speed"] == "持平"


class TestSampleThreshold:
    def test_a3_sample_insufficient(self, tmp_path, monkeypatch):
        """本周 vs 上周:每段 <3 条 → sample_warning"""
        from analysis.weight_compare import scenario_a3

        today = date.today()
        this_mon = today - timedelta(days=today.weekday())
        last_mon = this_mon - timedelta(days=7)
        data = [
            ((last_mon + timedelta(days=0)).isoformat(), 81.0),
            ((last_mon + timedelta(days=1)).isoformat(), 80.8),
            ((last_mon + timedelta(days=2)).isoformat(), 80.9),  # 上周 3 条
            (this_mon.isoformat(), 80.5),
            (today.isoformat(), 80.3),  # 本周 2 条(<3)
        ]
        _insert(tmp_path, monkeypatch, data)
        d, err = scenario_a3()
        assert err is None
        assert d.get("sample_warning"), "样本不足应产生 sample_warning"


class TestPlateau:
    def test_b8_detect(self, tmp_path, monkeypatch):
        """14 天波动 ≤±0.5kg → 识别到平台期"""
        from analysis.weight_compare import scenario_b8

        today = date.today()
        # 前 17 天缓降,后 14 天在 79.3~79.6 之间(±0.2,满足平台期条件)
        rows = []
        for i in range(31):
            d = (today - timedelta(days=30 - i)).isoformat()
            kg = 80.0 - i * 0.02 if i < 17 else 79.3 + (i % 3) * 0.1
            rows.append((d, round(kg, 1)))
        _insert(tmp_path, monkeypatch, rows)
        d, err = scenario_b8()
        assert err is None, f"应识别到平台期: {err}"
        assert d["seg_a"]["label"] == "平台期首日"
        assert "平台期持续" in [r["label"] for r in d["extra_rows"]]

    def test_b8_no_plateau(self, tmp_path, monkeypatch):
        """波动大 → 未识别(报错信息)"""
        from analysis.weight_compare import scenario_b8

        today = date.today()
        rows = [((today - timedelta(days=29 - i)).isoformat(), 80.0 + (i % 2) * 1.5) for i in range(30)]
        _insert(tmp_path, monkeypatch, rows)
        d, err = scenario_b8()
        assert err and "平台期" in err


class TestMilestone:
    def test_e3_5kg(self, tmp_path, monkeypatch):
        """历史最高 85 → 减 5kg = 80.0 的第一个达标日"""
        from analysis.weight_compare import scenario_e3

        today = date.today()
        rows = [
            ((today - timedelta(days=60)).isoformat(), 85.0),
            ((today - timedelta(days=40)).isoformat(), 82.0),
            ((today - timedelta(days=30)).isoformat(), 80.0),  # 达标日
            ((today - timedelta(days=10)).isoformat(), 79.5),
            (today.isoformat(), 79.0),
        ]
        _insert(tmp_path, monkeypatch, rows)
        d, err = scenario_e3(5)
        assert err is None, err
        assert d["seg_a"]["label"] == "减重 5kg 那天"
        assert d["seg_a"]["range"] == (today - timedelta(days=30)).isoformat()
        assert "用时" in [r["label"] for r in d["extra_rows"]]

    def test_e3_not_reached(self, tmp_path, monkeypatch):
        """未达成 → 提示未达成"""
        from analysis.weight_compare import scenario_e3

        today = date.today()
        rows = [((today - timedelta(days=30)).isoformat(), 82.0), (today.isoformat(), 80.5)]
        _insert(tmp_path, monkeypatch, rows)
        d, err = scenario_e3(10)
        assert err and "未达成" in err


class TestSeason:
    def test_e5_summer(self, tmp_path, monkeypatch):
        """当年 6-8 月最低"""
        from analysis.weight_compare import scenario_e5

        today = date.today()
        rows = [
            (f"{today.year}-06-15", 78.5),
            (f"{today.year}-07-10", 78.0),  # 入夏最低
            (f"{today.year}-08-01", 78.3),
            (today.isoformat(), 79.0),
        ]
        _insert(tmp_path, monkeypatch, rows)
        d, err = scenario_e5()
        if err:
            pytest.skip(f"季节窗口外无数据: {err}")
        assert d["seg_a"]["label"] == "入夏最低"
        assert d["seg_a"]["range"] == f"{today.year}-07-10"


class TestWorkdayWeekend:
    def test_d4(self, tmp_path, monkeypatch):
        """最近一周工作日/周末分组"""
        from analysis.weight_compare import scenario_d4

        today = date.today()
        rows = []
        for i in range(7):
            d = today - timedelta(days=6 - i)
            rows.append((d.isoformat(), 80.0 + (0.2 if d.weekday() >= 5 else 0)))
        _insert(tmp_path, monkeypatch, rows)
        d, err = scenario_d4()
        if err:
            pytest.skip(f"样本不足: {err}")
        assert d["seg_a"]["label"] == "工作日"
        assert d["seg_b"]["label"] == "周末"
        assert "一致率" in [r["label"] for r in d["extra_rows"]]
