#!/usr/bin/env python3
"""body_metrics DB schema 测试 — Task 1 数据层校验

V1.0 §02 第 ① 数据层 + 第 ④ 可约束:
  - body_composition 7 皮钳 NOT NULL + CHECK
  - body_measurements 13 围度条件 CHECK
  - 软删除 is_deprecated
  - audit 字段 created_at + updated_at
"""

import os
import sqlite3
import sys
import tempfile

import pytest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

from db import init_db  # noqa: E402


def test_body_composition_table_exists():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    conn = sqlite3.connect(path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(body_composition)").fetchall()]
    for required in ["id", "date", "source", "caliper_chest_mm", "body_fat_pct", "is_deprecated"]:
        assert required in cols, f"missing column {required}"
    conn.close()
    os.unlink(path)


def test_body_composition_check_constraints():
    """DB 层硬规则:source 必须在白名单"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    with pytest.raises(sqlite3.IntegrityError):
        c.execute(
            """INSERT INTO body_composition
               (date, source,
                caliper_chest_mm, caliper_abdominal_mm, caliper_thigh_mm,
                caliper_tricep_mm, caliper_subscapular_mm, caliper_suprailiac_mm,
                caliper_midaxillary_mm, body_fat_pct)
               VALUES ('2026-07-25', 'invalid', 5, 10, 15, 8, 10, 8, 7, 20)"""
        )
        conn.commit()
    conn.close()
    os.unlink(path)


def test_body_measurements_table_exists():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    conn = sqlite3.connect(path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(body_measurements)").fetchall()]
    for required in ["id", "date", "waist_cm", "is_deprecated"]:
        assert required in cols
    conn.close()
    os.unlink(path)