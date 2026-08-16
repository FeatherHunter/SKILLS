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

L2 iso_db 强制隔离层(#400 重建 · 2026-08-16 · #386 Q6):
  - pytest_configure:最早时机强制覆盖 SKILLS_DB_PATH → mktemp,
    覆盖用户 shell 持久生产 env(opt-out: SKILLS_KEEP_DB=1 调试用)。
  - iso_db_isolate(session autouse):兜底 setenv + 验证 find_db_path 解析到 temp。
  - pytest_unconfigure:清理 mktemp 目录。
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys
import tempfile
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


# ============================================================================
# L2 iso_db 强制隔离层(#400 重建 · 2026-08-16 · #386 Q6)
#
# 背景:用户 shell 持久 SKILLS_DB_PATH=D:\2Study\StudyNotes\.db(生产)。
# 早期 temp_db 仅 session-scope + 显式请求;不请求 temp_db 的测试/import 会
# 直接解析到生产路径(模块级 DB_PATH 烘焙在 import 时固化,monkeypatch 无效)。
#
# 本层在 pytest 启动最早时机(pytest_configure)强制 setenv SKILLS_DB_PATH →
# mktemp,使任何 import / find_db_path() 都拿到 temp;autouse 兜底二次校验。
# 调试 opt-out:SKILLS_KEEP_DB=1(保留 caller 已设 env,测试将指向真实路径,
# 仅限开发者确认隔离问题时使用)。
# ============================================================================

_ISO_TEMP_DIR: Path | None = None


def pytest_configure(config):
    """pytest 启动最早时机:强制覆盖 SKILLS_DB_PATH → mktemp

    为什么这里:任何 scripts/*.py 的模块级 DB_PATH 烘焙都发生在 import 时,
    而 conftest 的 import 先于测试收集;在此 setenv 可保证烘焙读到 temp。
    """
    global _ISO_TEMP_DIR
    if os.environ.get("SKILLS_KEEP_DB") == "1":
        print("[iso_db] SKILLS_KEEP_DB=1 保留 caller 已设 SKILLS_DB_PATH(调试)")
        return
    _ISO_TEMP_DIR = Path(tempfile.mkdtemp(prefix="iso_db_pytest_"))
    os.environ["SKILLS_DB_PATH"] = str(_ISO_TEMP_DIR)
    print(f"[iso_db] pytest_configure CALLED · SKILLS_DB_PATH set to {_ISO_TEMP_DIR}")


def pytest_unconfigure(config):
    """pytest 退出:清理 mktemp 目录"""
    global _ISO_TEMP_DIR
    if _ISO_TEMP_DIR is not None:
        shutil.rmtree(_ISO_TEMP_DIR, ignore_errors=True)
        _ISO_TEMP_DIR = None


@pytest.fixture(scope="session", autouse=True)
def iso_db_isolate():
    """session-scope autouse 兜底:再 setenv + 验证 find_db_path 解析到 temp

    双保险:pytest_configure 若被绕过(如第三方加载方式),本 fixture 仍兜底。
    SKILLS_KEEP_DB=1(调试 opt-out):不覆盖 caller env,仅打印警告不硬断言
    (硬断言由 test_db_isolation.py::test_iso_db_plugin_loaded 承担,避免
    调试模式下整个 session 无法运行)。
    """
    import db as db_mod

    if os.environ.get("SKILLS_KEEP_DB") != "1" and _ISO_TEMP_DIR is not None:
        os.environ["SKILLS_DB_PATH"] = str(_ISO_TEMP_DIR)

    if os.environ.get("SKILLS_KEEP_DB") == "1":
        print("[iso_db] SKILLS_KEEP_DB=1 调试模式:未强制隔离,写库测试可能触碰真实路径!")
        yield
        return

    resolved = db_mod.find_db_path(SKILL_DIR)
    prod = Path(r"D:\2Study\StudyNotes\.db") / "calorie_data.db"
    assert str(resolved.resolve()) != str(prod.resolve()), (
        f"[iso_db] 隔离未生效!find_db_path 解析到生产: {resolved}"
    )
    yield
