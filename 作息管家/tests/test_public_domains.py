# -*- coding: utf-8 -*-
"""作息管家 · 技能互联 sleep 域取数测试（#274 试点）

隔离: 依赖作息管家 conftest 的 autouse conn fixture
  （monkeypatch schedule_db.get_connection → tmp_path 临时 DB，永不碰生产库）。
覆盖:
  - 主睡眠段匹配: '维持.睡眠'（新二级）/ '睡眠'（旧一级）都算
  - 午睡排除: '调整.午睡' 不算主睡眠
  - 同日多睡眠行 SUM 聚合
  - skilllink.py 端到端: 真作息管家注册表 → 统一信封
"""
from __future__ import annotations

import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _seed_summary(conn, rows):
    """rows: [(date, category, total_minutes)]"""
    for date, cat, mins in rows:
        conn.execute(
            "INSERT OR REPLACE INTO daily_summary (date, category, total_minutes) "
            "VALUES (?, ?, ?)",
            (date, cat, mins),
        )
    conn.commit()


def test_fetch_sleep_main_segments_only(conn):
    """主睡眠段匹配 + 午睡排除"""
    import schedule_db as db

    conn = db.get_connection()
    _seed_summary(conn, [
        ("2026-08-01", "维持.睡眠", 480),   # 主睡眠（新二级）✓
        ("2026-08-01", "调整.午睡", 30),    # 午睡 ✗
        ("2026-08-02", "睡眠", 420),        # 主睡眠（旧一级）✓
        ("2026-08-03", "工作.开发", 300),   # 其他 ✗
    ])
    conn.close()

    from PUBLIC_DOMAINS import fetch_sleep

    out = fetch_sleep("2026-08-01", "2026-08-10")
    assert out == [
        {"date": "2026-08-01", "sleep_min": 480},
        {"date": "2026-08-02", "sleep_min": 420},
    ]


def test_fetch_sleep_sums_same_day(conn):
    """同日多条主睡眠行（同分类被 upsert 覆盖）+ 非主睡眠排除"""
    import schedule_db as db

    conn = db.get_connection()
    _seed_summary(conn, [
        ("2026-08-05", "维持.睡眠", 420),
        ("2026-08-05", "维持.睡眠", 60),    # 同分类重复 → INSERT OR REPLACE 覆盖为 60
        ("2026-08-05", "维持.早睡", 30),    # 非主睡眠 ✗
    ])
    conn.close()

    from PUBLIC_DOMAINS import fetch_sleep

    out = fetch_sleep("2026-08-05", "2026-08-05")
    assert out == [{"date": "2026-08-05", "sleep_min": 60}]


def test_fetch_sleep_empty_range(conn):
    """无数据区间 → 空数组（§6 对方今天没记录语义）"""
    import schedule_db as db

    conn = db.get_connection()
    conn.close()

    from PUBLIC_DOMAINS import fetch_sleep

    assert fetch_sleep("2026-09-01", "2026-09-10") == []


def test_skilllink_e2e_sleep(conn):
    """端到端：skilllink-read 真身 → 作息管家注册表 → 统一信封"""
    import json

    import schedule_db as db

    conn = db.get_connection()
    _seed_summary(conn, [
        ("2026-08-01", "维持.睡眠", 480),
        ("2026-08-02", "睡眠", 420),
        ("2026-08-02", "调整.午睡", 30),
    ])
    conn.close()

    link_dir = Path(__file__).resolve().parents[2] / "技能互联"
    sys.path.insert(0, str(link_dir))
    import skilllink

    # --what 问能力
    out, code = _run_cli(skilllink, ["--skill", "作息管家", "--what"])
    assert code == 0
    assert out["ok"] is True
    assert out["skill"] == "作息管家"
    assert [d["name"] for d in out["domains"]] == ["sleep"]
    assert out["domains"][0]["cn"] == "睡眠"

    # --domain 查数据
    out2, code2 = _run_cli(skilllink, [
        "--skill", "作息管家", "--domain", "sleep",
        "--from", "2026-08-01", "--to", "2026-08-10",
    ])
    assert code2 == 0
    assert out2["ok"] is True
    assert out2["domain"] == "sleep"
    assert out2["data"] == [
        {"date": "2026-08-01", "sleep_min": 480},
        {"date": "2026-08-02", "sleep_min": 420},
    ]

    # 无此域 → 自救清单
    out3, code3 = _run_cli(skilllink, [
        "--skill", "作息管家", "--domain", "nope",
        "--from", "2026-08-01", "--to", "2026-08-10",
    ])
    assert code3 == 1
    assert out3["ok"] is False
    assert "没有这个域" in out3["error"]
    assert out3["domains"] == ["sleep"]


def _run_cli(skilllink, args):
    import io
    from contextlib import redirect_stdout

    import json

    buf = io.StringIO()
    with redirect_stdout(buf):
        code = skilllink.main(args)
    return json.loads(buf.getvalue()), code
