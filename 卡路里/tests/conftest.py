#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/conftest.py — pytest 共享 fixture · ADR-0006

ticket 01 · 2026-07-29 起

提供:
  - temp_db(session-scope):monkeypatch SKILLS_DB_PATH 到临时目录,
    拷贝 schema,测试结束自动清理。任何 calorie_tracker.py / db.py 调用
    find_db_path() 都会拿到 temp 路径,生产 calorie_data.db 永不被触碰。

为什么 session-scope:测试间无 schema 变化,fixture setup/teardown 只跑一次,
避免每个测试 copy/remove 浪费时间。
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
PROD_DB = SKILL_DIR / "calorie_data.db"

# 让 tests 可 import scripts/*.py(同 test_redesign.py 做法)
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _copy_schema(prod_db: Path, temp_db: Path) -> None:
    """从生产 DB 拷 schema(sql)到 temp DB;不拷数据

    用 db.py 的 init_db,统一 schema 来源(避免顺序错乱)。
    init_db 内已含 CREATE TABLE 顺序保证 + 迁移逻辑。
    """
    import db as db_mod
    db_mod.init_db(str(temp_db))
    # 验证 schema 拷过来了
    if prod_db.exists():
        src_count = sqlite3.connect(str(prod_db)).execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        dst_count = sqlite3.connect(str(temp_db)).execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
        ).fetchone()[0]
        # temp 应 >= prod 的表数(可能 init 多了迁移加的表)
        assert dst_count >= src_count, (
            f"temp DB 拷 schema 不全:prod={src_count} tables, temp={dst_count} tables"
        )


@pytest.fixture(scope="session")
def temp_db(tmp_path_factory, monkeypatch_session):
    """session-scope 临时 DB,monkeypatch SKILLS_DB_PATH,init schema

    Args:
        tmp_path_factory: pytest 内置,提供临时目录
        monkeypatch_session: 自定义 session-scope monkeypatch(见下)
    """
    import db as db_mod

    temp_dir = tmp_path_factory.mktemp("calorie_test_db")
    temp_db_path = temp_dir / "calorie_data.db"
    _copy_schema(PROD_DB, temp_db_path)

    # Monkeypatch SKILLS_DB_PATH,让 db.find_db_path() 解析到 temp
    monkeypatch_session.setenv("SKILLS_DB_PATH", str(temp_dir))

    # 验证 patch 生效(避免 silent failure)
    resolved = db_mod.find_db_path(SKILL_DIR)
    assert resolved == temp_db_path, (
        f"find_db_path 解析失败:expected {temp_db_path}, got {resolved}"
    )

    yield temp_db_path

    # Teardown:pytest tmp_path_factory 自动清理 temp_dir


@pytest.fixture(scope="session")
def monkeypatch_session():
    """session-scope 的 monkeypatch(默认 monkeypatch 是 function-scope)

    pytest 没有原生 session-scope monkeypatch;自己实现一份。
    """
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()
