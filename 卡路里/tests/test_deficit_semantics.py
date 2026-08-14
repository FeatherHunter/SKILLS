#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_deficit_semantics.py — 热量缺口符号统一回归测试(ADR-0013)

第一性原理: 热量缺口 = 消耗 − 摄入, 正值 = 缺口 = 减重潜力。
本文件锁住 series.py 字段公式 + 消费端(cross/anomaly/simulate/render_analysis)
对「正=缺口」的语义,防止符号回退(曾: series 负=缺口, simulate 对真实缺口
用户预测增重, cross 有缺口日判定反向)。

隔离: 本文件自带 function-scoped `fresh_db` fixture(monkeypatch SKILLS_DB_PATH
到每测试独立临时目录 + db.init_db),生产 calorie_data.db 永不被触碰。
⚠️ 不用 conftest 的 session-scoped temp_db——跨测试数据累积会污染断言。

执行:
    cd 卡路里 && python -m pytest tests/test_deficit_semantics.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# 场景: 摄入 2000 < 消耗 2607 (TDEE 2507 + 运动 100) → 真实缺口 607 卡
INTAKE = 2000
EXERCISE = 100


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """function-scoped 独立临时库: 每测试一个, init schema, 用完即弃"""
    import db as db_mod

    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    db_path = db_mod.find_db_path(SKILL_DIR)
    db_mod.init_db(str(db_path))
    return db_path


def _seed_deficit_user(db_path, days=7, with_weight=False):
    """构造真实缺口用户: 连续 N 天摄入 < 消耗 (可选带体重记录)"""
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    for i in range(days):
        d = f"2026-08-{1 + i:02d}"
        conn.execute(
            "INSERT INTO food_log (date, food_name, grams, calories) VALUES (?, '测试餐', 100, ?)",
            (d, INTAKE),
        )
        if i % 2 == 0:  # 隔天运动
            conn.execute(
                "INSERT INTO exercise_log (date, exercise_type, calories_burned) VALUES (?, '跑步', ?)",
                (d, EXERCISE),
            )
        if with_weight:
            conn.execute("INSERT INTO weight_log (date, weight_kg) VALUES (?, 71.0)", (d,))
    conn.commit()
    conn.close()


class TestSeriesDeficitSign:
    """series.py 字段公式: 消耗 − 摄入, 正=缺口"""

    def test_real_deficit_user_positive(self, fresh_db):
        _seed_deficit_user(fresh_db)
        from analysis import series as S
        s = S.build_series("2026-08-01", "2026-08-07")
        deficits = [d["deficit"] for d in s if d.get("deficit") is not None]
        assert deficits, "应产出 deficit 字段"
        # 摄入 2000, 消耗 = TDEE(≈2507) + 运动(0 或 100) → deficit 应为正(≈507~607)
        for d in deficits:
            assert d > 0, f"真实缺口用户 deficit 应为正(消耗−摄入), 实得 {d}"

    def test_no_intake_day_deficit_none(self, fresh_db):
        """无摄入日 → deficit 为 None(不伪造)"""
        _seed_deficit_user(fresh_db, days=3)  # 只有 8/1-8/3 有记录
        from analysis import series as S
        s = S.build_series("2026-08-01", "2026-08-07")
        empty = [d for d in s[3:] if d.get("calories") is None]
        assert empty, "应有无记录日"
        assert all(d["deficit"] is None for d in empty), "无记录日 deficit 应为 None"

    def test_surplus_user_negative(self, fresh_db):
        """摄入 > 消耗 → deficit 为负(盈余)"""
        import sqlite3
        conn = sqlite3.connect(str(fresh_db))
        for i in range(3):
            d = f"2026-08-{1 + i:02d}"
            conn.execute(
                "INSERT INTO food_log (date, food_name, grams, calories) VALUES (?, '大吃', 100, 4000)",
                (d,),
            )
        conn.commit()
        conn.close()
        from analysis import series as S
        s = S.build_series("2026-08-01", "2026-08-03")
        for d in s:
            assert d["deficit"] < 0, f"盈余用户 deficit 应为负, 实得 {d['deficit']}"


class TestSimulateSign:
    """simulate: 模拟减重 / 缺口预测 对真实缺口用户输出减重(正)"""

    def test_weight_sim_cut_real_deficit_predicts_loss(self, fresh_db):
        """模拟减重(每天-300卡): 真实缺口用户应预测减重(正 weekly_loss)"""
        _seed_deficit_user(fresh_db, days=14, with_weight=True)
        from analysis import series as S
        from analysis import simulate as Sim
        s = S.build_series("2026-08-01", "2026-08-14")
        r = Sim.weight_sim_cut(s, 300, "模拟减重(每天-300卡)")
        assert not r.get("degraded"), f"应可计算, 实得 degrade: {r.get('degrade_msg')}"
        assert r["weekly_loss"] > 0, (
            f"真实缺口用户模拟减重应预测减重(正), 实得 {r['weekly_loss']} kg/周"
        )
        assert r["new_deficit"] > 0, f"新缺口应为正, 实得 {r['new_deficit']}"

    def test_calorie_deficit_eta_weekly_positive(self, fresh_db):
        """摄入预测(卡路里缺口预测): weekly 应为正(减重)"""
        _seed_deficit_user(fresh_db, days=14)
        from analysis import series as S
        from analysis import simulate as Sim
        s = S.build_series("2026-08-01", "2026-08-14")
        r = Sim.calorie_deficit_eta(s, "摄入预测(卡路里缺口预测)")
        assert not r.get("degraded"), f"应可计算, 实得 degrade: {r.get('degrade_msg')}"
        assert r["weekly_loss"] > 0, f"缺口预测 weekly 应为正, 实得 {r['weekly_loss']}"
        assert r["avg_deficit"] > 0, f"日均缺口应为正, 实得 {r['avg_deficit']}"


class TestCrossSign:
    """cross: 看体重 vs 缺口 分组/分桶语义"""

    def test_deficit_strat_marks_deficit_days(self, fresh_db):
        """真实缺口日应被判为「有缺口日」(正=缺口)"""
        _seed_deficit_user(fresh_db, with_weight=True)  # 体重是 weight_deficit 的 a 轴
        from analysis import series as S
        from analysis import cross as C
        s = S.build_series("2026-08-01", "2026-08-07")
        r = C.analyze_pair(s, "weight_deficit", "7d")
        strat = r.get("strat") or {}
        rows = strat.get("rows") or []
        assert rows, "应产出分层行"
        deficit_row = next((x for x in rows if x["label"] == "有缺口日"), None)
        assert deficit_row, f"应有「有缺口日」行, 实得 labels: {[x['label'] for x in rows]}"
        assert deficit_row["days"] == 7, (
            f"7 天全为真实缺口日, 有缺口日应=7, 实得 {deficit_row['days']}"
        )

    def test_deficit_buckets_positive(self, fresh_db):
        """分桶: 真实缺口 507~607 → 应入「标准缺口(100~500)」或「深缺口(>500)」"""
        _seed_deficit_user(fresh_db)
        from analysis import series as S
        from analysis import cross as C
        s = S.build_series("2026-08-01", "2026-08-07")
        r = C.analyze_pair(s, "weight_deficit", "7d")
        buckets = r.get("deficit_buckets") or []
        labels = {b["label"]: b["days"] for b in buckets}
        assert labels, f"应产出分桶, 实得 {buckets}"
        # 无「盈余」桶(用户真实在缺口)
        assert not any("盈余" in k for k in labels), f"真实缺口用户不应有盈余桶, 实得 {labels}"
        total = sum(labels.values())
        assert total == 7, f"分桶天数应合计 7, 实得 {labels}"


class TestAnomalySign:
    """anomaly: 诊断类判定语义(正=缺口)"""

    def test_why_not_losing_defers_to_plateau(self, fresh_db):
        """有缺口仍不动 → 走「缺口存在但体重不动」分支(不再误判「缺口为零或为正」)"""
        _seed_deficit_user(fresh_db)
        import sqlite3
        conn = sqlite3.connect(str(fresh_db))
        # 补体重记录(体重 14 天 ±0.5kg 内, 触发平台期分支)
        for i in range(1, 8):
            d = f"2026-08-{i:02d}"
            conn.execute("INSERT INTO weight_log (date, weight_kg) VALUES (?, 71.0)", (d,))
        conn.commit()
        conn.close()
        from analysis import series as S
        from analysis import anomaly as A
        s = S.build_series("2026-08-01", "2026-08-07")
        r = A.diagnose("why_not_losing", s)
        findings = " ".join(f.get("cause", "") for f in r.get("findings", []))
        assert "缺口存在但体重不动" in findings, f"应判定缺口存在, 实得: {findings}"

    def test_overall_marks_deficit_dimension_ok(self, fresh_db):
        """综合健康评估: 真实缺口 → 「缺口维度 ✅ 在缺口」"""
        _seed_deficit_user(fresh_db)
        import sqlite3
        conn = sqlite3.connect(str(fresh_db))
        for i in range(1, 8):
            d = f"2026-08-{i:02d}"
            conn.execute("INSERT INTO weight_log (date, weight_kg) VALUES (?, 71.0)", (d,))
        conn.commit()
        conn.close()
        from analysis import series as S
        from analysis import anomaly as A
        s = S.build_series("2026-08-01", "2026-08-07")
        r = A.diagnose("overall", s)
        findings = " ".join(f.get("evidence", "") for f in r.get("findings", []))
        assert "缺口维度 ✅ 在缺口" in findings, f"应判在缺口, 实得: {findings}"


class TestRenderAnalysisSign:
    """render_analysis: 异常日标注 / TDEE 静态缺口"""

    def test_anomaly_days_no_false_deficit(self, fresh_db):
        """真实缺口 607 卡(<900)不应被标「缺口过大」"""
        _seed_deficit_user(fresh_db)
        from analysis import series as S
        from render_analysis import _anomaly_days
        s = S.build_series("2026-08-01", "2026-08-07")
        days = _anomaly_days(s)
        for d in days:
            assert not any("缺口过大" in n for n in d["notes"]), (
                f"607 卡缺口不应标缺口过大, 实得 {d['notes']}"
            )

    def test_tdee_report_deficit_positive(self, fresh_db):
        """看TDEE报告: 静态缺口 = TDEE − 摄入(正=缺口)"""
        _seed_deficit_user(fresh_db)
        from render_analysis import view_report

        class _Args:
            window = "custom"
            start = "2026-08-01"
            end = "2026-08-07"
            kind = "tdee"

        r = view_report(_Args())
        assert r["deficit"] > 0, f"TDEE 静态缺口应为正(消耗−摄入), 实得 {r['deficit']}"
