#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_db_isolation.py — 测试隔离 seam 7 守门

ticket 01 · ADR-0006 · SKILLS_DB_PATH_TEST 测试隔离契约

覆盖:
  1. 测试写入临时 DB,生产 DB 永不被触碰
  2. 测试代码无 hardcode 生产 DB 路径
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
PROD_DB = SKILL_DIR / "calorie_data.db"  # 测试 fixture 应让此文件**不被触碰**


def test_writes_dont_touch_prod_db(temp_db, monkeypatch):
    """任何测试写入都进 temp DB,生产 calorie_data.db 永不被修改

    seam 7 · ADR-0006 第①条:测试隔离生效
    """
    # 记录生产 DB 的 mtime + size(基准)
    if not PROD_DB.exists():
        pytest.skip("本地无 calorie_data.db,跳过(常见于 fresh clone)")
    prod_mtime_before = PROD_DB.stat().st_mtime
    prod_size_before = PROD_DB.stat().st_size

    # 在测试期间 conftest 的 temp_db fixture 已 monkeypatch SKILLS_DB_PATH
    # 模拟一次写库操作
    import db as db_mod
    db_path = db_mod.find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO weight_log(date, time, weight_kg) VALUES (?, ?, ?)",
        ("2026-07-29", "12:00:00", 99.99),
    )
    conn.commit()
    conn.close()

    # 生产 DB mtime + size 应**完全没变**
    prod_mtime_after = PROD_DB.stat().st_mtime
    prod_size_after = PROD_DB.stat().st_size
    assert prod_mtime_after == prod_mtime_before, (
        f"生产 DB 被测试写入!mtime before={prod_mtime_before}, after={prod_mtime_after}"
    )
    assert prod_size_after == prod_size_before, (
        f"生产 DB 体积变化!before={prod_size_before}, after={prod_size_after}"
    )


def test_no_test_file_hardcodes_prod_db_path():
    """扫所有 tests/*.py,断言无文件 hardcode 生产 DB 绝对路径

    seam 7 · ADR-0006 第②条:测试代码无 hardcode
    """
    tests_dir = SKILL_DIR / "tests"
    # 匹配常见 hardcode 模式
    bad_patterns = [
        r"D:\\.db\\calorie_data\.db",      # Windows 绝对路径
        r"/mnt/d/\.db/calorie_data\.db",    # WSL 绝对路径
        r"D:/.db/calorie_data\.db",         # Windows 斜杠
        r"calorie_data\.db\.bak",           # 备份文件(不应在测试里引用)
    ]
    bad_re = re.compile("|".join(bad_patterns))

    offenders = []
    for py_file in tests_dir.rglob("*.py"):
        # 跳过自己(本测试是 seam 守门,允许引用 prod path 验证)
        if py_file.name == "test_db_isolation.py":
            continue
        text = py_file.read_text(encoding="utf-8", errors="replace")
        matches = bad_re.findall(text)
        if matches:
            offenders.append((py_file.relative_to(SKILL_DIR), matches))

    assert not offenders, (
        f"以下测试文件 hardcode 了生产 DB 路径(违反 ADR-0006):\n"
        + "\n".join(f"  {p}: {m}" for p, m in offenders)
    )
