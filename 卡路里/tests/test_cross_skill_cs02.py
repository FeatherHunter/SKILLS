#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卡路里 · 技能互联消费方 CS-02 全链路测试（#274 试点）

隔离约定（DB 红线）:
  - 卡路里侧: 依赖卡路里 conftest 的 session 级 temp_db fixture
    （monkeypatch SKILLS_DB_PATH → 临时目录，非 autouse，必须显式依赖）
  - 作息管家侧: 同一 SKILLS_DB_PATH 下 init_db() 建临时 schedule_data.db
    （schedule_db 必须在 temp_db patch 之后 import——模块级 DB_PATH 固化 #257 教训）
  - 技能互联 skilllink.py: subprocess 真实调用（真 registry → 真 PUBLIC_DOMAINS → temp DB）

覆盖:
  - CS-02 合并: 按天对齐 / 分位分组 / 体重净变化 / 相关性
  - 空数据降级（§6 办成了=true · 数据=[]）
  - 未接入降级（§6 办成了=false · 未接入）
  - HTML 渲染端到端: 注入管线成功 + 产物含注入数据
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


import pytest


@pytest.fixture(autouse=True)
def _clean_dbs(temp_db):
    """session 级 temp_db 数据会跨测试残留 → 每个测试前清空两个临时 DB"""
    import os

    os.environ["SKILLS_DB_PATH"] = str(Path(temp_db).parent)
    sched_scripts = Path(__file__).resolve().parents[2] / "作息管家" / "scripts"
    sys.path.insert(0, str(sched_scripts))
    import schedule_db

    schedule_db.init_db()
    conn = schedule_db.get_connection()
    conn.execute("DELETE FROM daily_summary")
    conn.commit()
    conn.close()

    from db import find_db_path, get_db

    conn2 = get_db(find_db_path(SKILL_DIR))
    conn2.execute("DELETE FROM weight_log")
    conn2.commit()
    conn2.close()
    yield


def _seed_schedule(temp_dir, rows):
    """作息管家临时 DB: 建表 + 写入 daily_summary"""
    import os

    # SKILLS_DB_PATH 指向 DB **目录**（temp_dir 参数实为 temp_db 文件路径 → 取其父目录）
    os.environ["SKILLS_DB_PATH"] = str(Path(temp_dir).parent)
    sched_scripts = Path(__file__).resolve().parents[2] / "作息管家" / "scripts"
    sys.path.insert(0, str(sched_scripts))
    import schedule_db

    schedule_db.init_db()
    conn = schedule_db.get_connection()
    for date, cat, mins in rows:
        conn.execute(
            "INSERT OR REPLACE INTO daily_summary (date, category, total_minutes) "
            "VALUES (?, ?, ?)",
            (date, cat, mins),
        )
    conn.commit()
    conn.close()


def _seed_weight(rows):
    """卡路里临时 DB: 写 weight_log"""
    from db import find_db_path, get_db

    db_path = find_db_path(SKILL_DIR)
    conn = get_db(db_path)
    for date, kg in rows:
        conn.execute(
            "INSERT INTO weight_log (date, time, weight_kg) VALUES (?, '07:00:00', ?)",
            (date, kg),
        )
    conn.commit()
    conn.close()


def _make_days(n=10, start="2026-08-01"):
    from datetime import date, timedelta

    d0 = date.fromisoformat(start)
    return [(d0 + timedelta(days=i)).isoformat() for i in range(n)]


def test_cs02_alignment_and_buckets(temp_db):
    """CS-02 核心: 对齐 / 分组 / 组内体重净变化 / 相关性"""
    days = _make_days(10)
    # 前 5 天: 短睡 <6h（340 分钟）体重缓慢上升 71→71.5
    # 后 5 天: 7-8h（450 分钟）体重下降 71.5→71.0
    sleep_rows = [(d, "维持.睡眠", 340 if i < 5 else 450) for i, d in enumerate(days)]
    weight_rows = []
    for i, d in enumerate(days):
        if i < 5:
            w = 71.0 + i * 0.125      # 71.0, 71.125, 71.25, 71.375, 71.5
        else:
            w = 71.5 - (i - 4) * 0.1  # 71.4, 71.3, 71.2, 71.1, 71.0
        weight_rows.append((d, round(w, 3)))

    _seed_schedule(temp_db, sleep_rows)
    _seed_weight(weight_rows)

    from cross_skill import cs02

    result = cs02(days[0], days[-1])
    assert result["ok"] is True
    assert result["days"] == 10

    groups = {g["label"]: g for g in result["groups"]}
    assert "<6h" in groups and "7-8h" in groups
    # 短睡组体重上升（净变化 > 0），7-8h 组体重下降（净变化 < 0）
    assert groups["<6h"]["weight_delta"] > 0.3
    assert groups["7-8h"]["weight_delta"] < -0.3
    assert groups["<6h"]["days"] == 5
    assert groups["7-8h"]["days"] == 5
    assert groups["<6h"]["sleep_avg"] == 340
    assert groups["7-8h"]["sleep_avg"] == 450

    # 相关性（睡眠 vs 体重：负相关——睡得久体重低）
    assert result["correlation"]["same_day"] is not None
    assert result["correlation"]["lag_1day"] is not None
    assert "组间差" in result["insight"]


def test_cs02_only_weight_no_sleep(temp_db):
    """§6 对方今天没记录 → 办成了=true · 数据=[] → 对齐 0 天 + 数据不足洞察"""
    days = _make_days(5)
    _seed_schedule(temp_db, [])          # 作息管家无睡眠数据
    _seed_weight([(d, 70.0) for d in days])

    from cross_skill import cs02

    result = cs02(days[0], days[-1])
    assert result["ok"] is True
    assert result["days"] == 0
    assert "不足" in result["insight"]


def test_cs02_no_local_db(temp_db, tmp_path):
    """卡路里本地无 DB/无体重 → ok=true · days=0（不崩溃）"""
    days = _make_days(3)
    _seed_schedule(temp_db, [(days[0], "维持.睡眠", 420)])
    # 不写 weight_log

    from cross_skill import cs02

    result = cs02(days[0], days[-1])
    assert result["ok"] is True
    assert result["days"] == 0


def test_read_skill_returns_unified_envelope(temp_db):
    """适配器: 真调 skilllink-read → 统一信封（含作息管家注册表）"""
    _seed_schedule(temp_db, [("2026-08-01", "维持.睡眠", 480)])

    from cross_skill import read_skill

    env = read_skill("作息管家", "sleep", "2026-08-01", "2026-08-05")
    assert env["ok"] is True
    assert env["skill"] == "作息管家"
    assert env["domain"] == "sleep"
    assert env["meta"]["start"] == "2026-08-01"
    assert env["data"] == [{"date": "2026-08-01", "sleep_min": 480}]


def test_read_skill_unknown_domain(temp_db):
    """适配器: 无此域 → ok=false + domains 清单（AI 自救路径）"""
    _seed_schedule(temp_db, [])
    from cross_skill import read_skill

    env = read_skill("作息管家", "nope", "2026-08-01", "2026-08-05")
    assert env["ok"] is False
    assert "没有这个域" in env["error"]
    assert "sleep" in env.get("domains", [])


def test_bucket_boundaries():
    """对抗审查盲区修复: 分位边界（360/420/480/540 整点归属）"""
    from cross_skill import _bucket_of

    assert _bucket_of(359) == "<6h"
    assert _bucket_of(360) == "6-7h"
    assert _bucket_of(419) == "6-7h"
    assert _bucket_of(420) == "7-8h"
    assert _bucket_of(479) == "7-8h"
    assert _bucket_of(480) == "8-9h"
    assert _bucket_of(539) == "8-9h"
    assert _bucket_of(540) == ">9h"
    assert _bucket_of(720) == ">9h"


def test_render_cs02_html(temp_db):
    """端到端: render → 注入管线成功 → 产物含注入数据 + 复制按钮区"""
    days = _make_days(6)
    _seed_schedule(temp_db, [(d, "维持.睡眠", 450) for d in days])
    _seed_weight([(d, 70.0) for d in days])

    from render_cross_skill_cs02 import render

    rc = render(days[0], days[-1])
    assert rc == 0

    # 找到产物（html_scene_path: 睡眠vs减重_结果_*.html）
    out_candidates = list(Path(temp_db).parent.glob("calorie_html/睡眠vs减重_结果_*.html"))
    assert out_candidates, "未生成 CS-02 HTML 产物"
    html = out_candidates[0].read_text(encoding="utf-8")

    # 占位符已被注入器替换（硬拦截通过）
    assert "<!--INJECT-DATA-->" not in html
    assert "<!--SHARED-HELPERS-->" not in html
    # 注入数据在
    assert "睡眠时长 vs 减重" in html
    assert "actionBar" in html or "copyText" in html
    # payload 信封可解析
    import re

    m = re.search(r'<script id="payload" type="application/json">(.*?)</script>', html, re.S)
    assert m, "payload 未注入"
    payload = json.loads(m.group(1))
    assert payload["status"] == "ok"
    assert payload["data"]["meta"]["command_cn"] == "联动作息管家（睡眠时长 vs 减重）"
    assert payload["data"]["scene"]["snapshot"]["title"] == "睡眠时长 vs 减重"
    assert len(payload["data"]["cs02"]["series"]) == 6
