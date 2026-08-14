#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_calorie_deficit_render.py — 「查热量缺口」渲染器守卫测试(T5 · map #349)

验收:
  - 隔离临时库运行 render_calorie_deficit.py 成功产出 HTML(修复 #332 的 3 处列名)
  - 产出页含 Base 管线(charts.line 双系列 + markLine 摄入目标)
  - 缺口语义: 正=缺口(消耗−摄入 · ADR-0013), summary/series 自洽
  - 新场景 key=deficit_analysis 在 _triggers.py 中为正式成员(非 legacy)

隔离: function-scoped fresh_db(monkeypatch SKILLS_DB_PATH),生产库不触碰。

执行:
    cd 卡路里 && python -m pytest tests/test_calorie_deficit_render.py -v
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """function-scoped 独立临时库: init schema, 用完即弃"""
    import db as db_mod

    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    db_path = db_mod.find_db_path(SKILL_DIR)
    db_mod.init_db(str(db_path))
    return db_path


def _seed_deficit_user(db_path, days=7):
    """真实缺口用户: 每天摄入 2000 < 消耗(TDEE≈2507+运动)"""
    import sqlite3
    from datetime import date, timedelta
    conn = sqlite3.connect(str(db_path))
    for i in range(days):
        d = (date.today() - timedelta(days=days - 1 - i)).isoformat()
        conn.execute(
            "INSERT INTO food_log (date, food_name, grams, calories) VALUES (?, '测试餐', 100, 2000)",
            (d,),
        )
        if i % 2 == 0:
            conn.execute(
                "INSERT INTO exercise_log (date, exercise_type, calories_burned) VALUES (?, '跑步', 100)",
                (d,),
            )
    conn.commit()
    conn.close()


class TestRendererSmoke:
    """渲染器冒烟: 隔离临时库产出 HTML"""

    def test_render_succeeds(self, fresh_db, tmp_path):
        """#332 验收: 临时库运行成功产出 HTML(修复 3 处列名)"""
        _seed_deficit_user(fresh_db)
        out = tmp_path / "deficit.html"
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "render_calorie_deficit.py"), "--days", "7", "--output", str(out)],
            cwd=SKILL_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        assert r.returncode == 0, f"渲染失败: {r.stderr}"
        assert out.exists(), "未产出 HTML"
        html = out.read_text(encoding="utf-8")
        assert "charts.line" in html, "应含 Base charts.line 图表调用"
        assert "markLine" in html, "应含摄入目标 markLine"
        assert "摄入目标" in html, "应含摄入目标文案"

    def test_stdout_reports_positive_deficit(self, fresh_db, tmp_path):
        """真实缺口用户 → stdout 缺口为正(正=缺口 · ADR-0013)"""
        _seed_deficit_user(fresh_db)
        out = tmp_path / "deficit.html"
        r = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "render_calorie_deficit.py"), "--days", "7", "--output", str(out)],
            cwd=SKILL_DIR, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        )
        assert r.returncode == 0, r.stderr
        assert "缺口 +" in r.stdout or "缺口 +" in r.stdout.replace(" ", ""), (
            f"真实缺口用户缺口应为正, stdout: {r.stdout}"
        )


class TestSceneMembership:
    """新场景是 _triggers.py 正式成员(非 legacy)"""

    def test_deficit_analysis_is_formal_scene(self):
        """key=deficit_analysis, subfunction=缺口分析, output_type=result"""
        import sys as _s
        _s.path.insert(0, str(SCRIPTS_DIR))
        from _triggers import TRIGGERS
        scene = next((t for t in TRIGGERS if t.get("key") == "deficit_analysis"), None)
        assert scene, "缺 deficit_analysis 场景"
        assert scene["wake_word"] == "查热量缺口"
        assert scene["subfunction"] == "缺口分析"
        assert scene["output_type"] == "result"
        assert scene["html_template"] == "templates/calorie_deficit.html"
        assert "render_calorie_deficit.py" in scene["data_source"]
        # 新格式判定(非 legacy): 含 output_type + prompt_template 双键
        assert "output_type" in scene and "prompt_template" in scene, "应为新 13 字段格式"

    def test_no_duplicate_wake_word(self):
        """wake_word 唯一(旧 legacy 条目已删除)"""
        import sys as _s
        _s.path.insert(0, str(SCRIPTS_DIR))
        from _triggers import TRIGGERS
        hits = [t for t in TRIGGERS if t.get("wake_word") == "查热量缺口"]
        assert len(hits) == 1, f"「查热量缺口」应唯一(legacy 已删), 实得 {len(hits)} 条"
