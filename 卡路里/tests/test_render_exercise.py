#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ticket #5 · 运动 39 场景 — 渲染器测试(2026-08-02 对抗审查收尾)

覆盖 7 个渲染器核心路径(temp DB):
  1. render_exercise_receipt:记运动/记力量(每组一行)/删(软删快照)
  2. render_exercise_summary:今日 vs 目标/力量筛选(默认 30 天)/降采样
  3. render_exercise_goal_view:已设目标达成/未设空状态
  4. render_exercise_strength / cardio / trend / recap / distribution 生成 + 关键字段
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
sys.path.insert(0, str(SKILL_DIR))

from db import init_db  # noqa: E402


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """独立 temp DB + SKILLS_DB_PATH"""
    db_path = tmp_path / "calorie_data.db"
    init_db(str(db_path))
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    import importlib
    import db as db_mod
    import exercise_tracker as et_mod
    importlib.reload(db_mod)
    importlib.reload(et_mod)
    return et_mod


def _seed(et):
    """造基础数据:今天跑步 + 昨天力量 + 3 天前深蹲 + 运动目标 500"""
    from datetime import date, timedelta
    t = date.today()
    et.add_record(t.isoformat(), "跑步", 300, minutes=30, category="有氧",
                  distance=5, heart_rate=140, max_heart_rate=165, note="晨跑")
    et.add_record((t - timedelta(days=1)).isoformat(), "哑铃弯举", 22,
                  category="力量", set_index=1, load_kg=10, reps=12)
    et.add_record((t - timedelta(days=3)).isoformat(), "深蹲", 30,
                  category="力量", set_index=1, load_kg=60, reps=8)
    conn = et.get_db()
    conn.execute("INSERT OR REPLACE INTO daily_goal (id, exercise_goal, updated_at) "
                 "VALUES (1, 500, CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()


def _render(script, args, monkeypatch_env=True):
    """运行渲染器子进程,返回 html 文本"""
    out_p = SKILL_DIR / "tests" / "_tmp_render_out.html"
    r = subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / script), *args,
                        "--chain", "1.识别->2.读->3.渲染", "--output", str(out_p)],
                       capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ})
    assert r.returncode == 0, (script, r.stderr)
    text = out_p.read_text(encoding="utf-8")
    out_p.unlink()
    return text


# ---------- 1. 写类回执 ----------

def test_receipt_add(env):
    _seed(env)
    html = _render("render_exercise_receipt.py",
                   ["--live-add", "--type", "拉伸", "--calories", "60", "--minutes", "15"])
    assert "拉伸" in html and "60" in html


def test_receipt_strength_sets(env):
    _seed(env)
    html = _render("render_exercise_receipt.py",
                   ["--live-add-strength", "--type", "卧推", "--sets", "3",
                    "--load", "40", "--reps", "8"])
    assert "卧推" in html and "3 组" in html and "40.0kg" in html


def test_receipt_delete_soft(env):
    _seed(env)
    html = _render("render_exercise_receipt.py", ["--live-delete", "--id", "1"])
    assert "删除" in html and "跑步" in html
    import sqlite3
    conn = sqlite3.connect(str(env.DB_PATH))
    row = conn.execute("SELECT is_deleted FROM exercise_log WHERE id = 1").fetchone()
    assert row[0] == 1
    conn.close()


# ---------- 2. 看类报表 ----------

def test_summary_today_vs_goal(env):
    _seed(env)
    html = _render("render_exercise_summary.py", ["--mode", "records", "--today"])
    assert "跑步" in html and "500" in html and "%" in html


def test_summary_strength_filter_default_30d(env):
    """力量筛选无窗口 → 默认最近 30 天(2026-08-02 对抗审查修复)"""
    _seed(env)
    html = _render("render_exercise_summary.py", ["--mode", "records", "--category", "力量"])
    assert "哑铃弯举" in html and "10.0" in html


def test_summary_downsample_week(env):
    _seed(env)
    html = _render("render_exercise_summary.py",
                   ["--mode", "summary", "--days", "365", "--downsample", "week"])
    assert "W" in html or "卡" in html


# ---------- 3. 达成视图 ----------

def test_goal_view_achieved(env):
    _seed(env)
    html = _render("render_exercise_goal_view.py", ["--period", "today"])
    assert "500" in html and "%" in html


def test_goal_view_empty(tmp_path, monkeypatch):
    """未设目标 → 空状态 + 引导文案"""
    db_path = tmp_path / "calorie_data.db"
    init_db(str(db_path))
    monkeypatch.setenv("SKILLS_DB_PATH", str(tmp_path))
    html = _render("render_exercise_goal_view.py", ["--period", "today"])
    assert "未设置每日运动目标" in html


# ---------- 4-7. 分析/复盘渲染器 ----------

def test_strength_overview(env):
    _seed(env)
    html = _render("render_exercise_strength.py", [])
    assert "哑铃弯举" in html and "深蹲" in html and "总组数" in html


def test_cardio_overview(env):
    _seed(env)
    html = _render("render_exercise_cardio.py", [])
    assert "跑步" in html and "配速" in html


def test_trend(env):
    _seed(env)
    html = _render("render_exercise_trend.py", ["--days", "30"])
    assert "卡" in html and "分钟" in html


def test_recap_week(env):
    _seed(env)
    html = _render("render_exercise_recap.py", ["--period", "week"])
    assert "运动复盘" in html and "次" in html


def test_distribution(env):
    _seed(env)
    html = _render("render_exercise_distribution.py", ["--mode", "distribution"])
    assert "力量" in html and "有氧" in html


# ---------- 8. --chain 强制 ----------

def test_chain_required():
    """所有渲染器未传 --chain 必须报错(exit 2)"""
    cases = [
        "render_exercise_receipt.py --live-add --type X --calories 1",
        "render_exercise_summary.py --today",
        "render_exercise_goal_view.py --period today",
        "render_exercise_strength.py",
        "render_exercise_cardio.py",
        "render_exercise_trend.py",
        "render_exercise_recap.py --period week",
        "render_exercise_distribution.py --mode distribution",
    ]
    for cmd in cases:
        parts = cmd.split()
        r = subprocess.run([sys.executable, str(SKILL_DIR / "scripts" / parts[0]), *parts[1:]],
                           capture_output=True, text=True, encoding="utf-8",
                           env={**os.environ})
        assert r.returncode == 2, f"{parts[0]} 未强制 --chain (rc={r.returncode})"
