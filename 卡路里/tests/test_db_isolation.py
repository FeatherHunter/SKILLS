#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_db_isolation.py — 测试隔离 seam 7 守门 + L2 iso_db 强制隔离验收

ticket 01 · ADR-0006 · #400 重建(2026-08-16,原 15 测试文件丢失后按 #400 记录恢复)

覆盖:
  1. 测试写入临时 DB,生产 DB 永不被触碰(本地副本 + 真生产 D:/2Study/StudyNotes/.db)
  2. L2 autouse 强制隔离:pytest 启动即 setenv SKILLS_DB_PATH → temp(不请求 temp_db 也隔离)
  3. 模块级 DB_PATH 烘焙被 L2 覆盖(import scripts.diet 后 DB_PATH 指向 temp)
  4. cwd_sentry 模块单测(供 #404 L3 复用)
  5. scripts/tests 代码无 hardcode 生产 DB 路径(已知 one-off 脚本豁免,见 allowlist)
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
PROD_DB = SKILL_DIR / "calorie_data.db"  # 本地副本(fresh clone 常见)
PROD_DB_REAL = Path(r"D:\2Study\StudyNotes\.db\calorie_data.db")  # 真生产库(只读比对)
PROD_DIR_REAL = Path(r"D:\2Study\StudyNotes\.db")

# 供 cwd_sentry 单测 import
ISO_DB_DIR = SKILL_DIR.parent / "公共组件" / "iso_db"


# ---------------------------------------------------------------------------
# 1. 本地副本隔离(既有 seam 7 守门)
# ---------------------------------------------------------------------------

def test_writes_dont_touch_prod_db(temp_db, monkeypatch):
    """任何测试写入都进 temp DB,本地生产 calorie_data.db 永不被修改

    seam 7 · ADR-0006 第①条:测试隔离生效
    """
    if not PROD_DB.exists():
        pytest.skip("本地无 calorie_data.db,跳过(常见于 fresh clone)")
    prod_mtime_before = PROD_DB.stat().st_mtime
    prod_size_before = PROD_DB.stat().st_size

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

    prod_mtime_after = PROD_DB.stat().st_mtime
    prod_size_after = PROD_DB.stat().st_size
    assert prod_mtime_after == prod_mtime_before, (
        f"生产 DB 被测试写入!mtime before={prod_mtime_before}, after={prod_mtime_after}"
    )
    assert prod_size_after == prod_size_before, (
        f"生产 DB 体积变化!before={prod_size_before}, after={prod_size_after}"
    )


# ---------------------------------------------------------------------------
# 2. 真生产库隔离(5 种 SQL · #400 对抗式发现修复:旧测试只查本地副本,形同虚设)
# ---------------------------------------------------------------------------

def _assert_isolated_from_real_prod(resolved: Path) -> None:
    """写库前守卫:解析路径绝不能是真生产库(隔离失效则 FAIL,而非写生产)"""
    assert str(resolved.resolve()) != str(PROD_DB_REAL.resolve()), (
        f"[iso_db] 隔离失效!find_db_path 解析到真生产库 {resolved};拒绝执行写操作"
    )


def _real_prod_snapshot():
    if not PROD_DB_REAL.exists():
        pytest.skip("本地无真生产库 D:\\2Study\\StudyNotes\\.db\\calorie_data.db,跳过")
    return PROD_DB_REAL.stat().st_mtime, PROD_DB_REAL.stat().st_size


def test_writes_dont_touch_real_prod_db_via_insert():
    """INSERT 隔离:写入解析路径(temp),真生产 D:/.db 零变化"""
    import db as db_mod
    resolved = db_mod.find_db_path(SKILL_DIR)
    _assert_isolated_from_real_prod(resolved)
    before = _real_prod_snapshot()

    db_mod.init_db(str(resolved))  # temp 库建 schema(写 temp,不写生产)
    conn = sqlite3.connect(str(resolved))
    conn.execute(
        "INSERT INTO weight_log(date, time, weight_kg) VALUES (?, ?, ?)",
        ("2026-08-16", "12:00:00", 99.99),
    )
    conn.commit()
    conn.close()

    after = _real_prod_snapshot()
    assert after == before, f"真生产库被 INSERT 触碰!before={before} after={after}"


def test_writes_dont_touch_real_prod_db_via_update():
    """UPDATE 隔离"""
    import db as db_mod
    resolved = db_mod.find_db_path(SKILL_DIR)
    _assert_isolated_from_real_prod(resolved)
    before = _real_prod_snapshot()

    db_mod.init_db(str(resolved))
    conn = sqlite3.connect(str(resolved))
    conn.execute("INSERT INTO weight_log(date, time, weight_kg) VALUES ('2026-08-16','12:00:00',80.0)")
    conn.execute("UPDATE weight_log SET weight_kg = 81.0 WHERE date = '2026-08-16'")
    conn.commit()
    conn.close()

    after = _real_prod_snapshot()
    assert after == before, f"真生产库被 UPDATE 触碰!before={before} after={after}"


def test_writes_dont_touch_real_prod_db_via_delete():
    """DELETE 隔离"""
    import db as db_mod
    resolved = db_mod.find_db_path(SKILL_DIR)
    _assert_isolated_from_real_prod(resolved)
    before = _real_prod_snapshot()

    db_mod.init_db(str(resolved))
    conn = sqlite3.connect(str(resolved))
    conn.execute("INSERT INTO weight_log(date, time, weight_kg) VALUES ('2026-08-16','12:00:00',80.0)")
    conn.execute("DELETE FROM weight_log WHERE date = '2026-08-16'")
    conn.commit()
    conn.close()

    after = _real_prod_snapshot()
    assert after == before, f"真生产库被 DELETE 触碰!before={before} after={after}"


def test_writes_dont_touch_real_prod_db_via_drop():
    """DROP TABLE 隔离"""
    import db as db_mod
    resolved = db_mod.find_db_path(SKILL_DIR)
    _assert_isolated_from_real_prod(resolved)
    before = _real_prod_snapshot()

    db_mod.init_db(str(resolved))
    conn = sqlite3.connect(str(resolved))
    conn.execute("DROP TABLE weight_log")  # 只 drop temp 库的表
    conn.commit()
    conn.close()

    after = _real_prod_snapshot()
    assert after == before, f"真生产库被 DROP 触碰!before={before} after={after}"


def test_writes_dont_touch_real_prod_db_via_truncate():
    """TRUNCATE 隔离(模拟 08-11 事故:DELETE FROM exercise_log 清空 8297 行)"""
    import db as db_mod
    resolved = db_mod.find_db_path(SKILL_DIR)
    _assert_isolated_from_real_prod(resolved)
    before = _real_prod_snapshot()

    db_mod.init_db(str(resolved))
    conn = sqlite3.connect(str(resolved))
    conn.execute("INSERT INTO exercise_log(date, time, exercise_type, calories_burned) "
                 "VALUES ('2026-08-16','12:00:00','跑步',300)")
    conn.execute("DELETE FROM exercise_log")
    conn.commit()
    conn.close()

    after = _real_prod_snapshot()
    assert after == before, f"真生产库被 TRUNCATE 触碰!before={before} after={after}"


# ---------------------------------------------------------------------------
# 3. L2 autouse 强制隔离验收
# ---------------------------------------------------------------------------

def test_iso_db_plugin_loaded():
    """pytest 启动最早时机 SKILLS_DB_PATH 已被强制 setenv 到 temp(不请求 temp_db 也生效)"""
    env = os.environ.get("SKILLS_DB_PATH", "")
    assert env, "[iso_db] SKILLS_DB_PATH 未被设置!pytest_configure 未生效"
    p = Path(env)
    assert p.is_dir(), f"[iso_db] SKILLS_DB_PATH 指向不存在目录: {env}"
    assert str(p.resolve()) != str(PROD_DIR_REAL.resolve()), (
        f"[iso_db] SKILLS_DB_PATH 仍指向生产: {env}"
    )
    assert "iso_db_pytest_" in p.name or "calorie_test_db" in p.name, (
        f"[iso_db] SKILLS_DB_PATH 不是 iso_db/temp 目录: {env}"
    )


def test_modules_baked_after_plugin_get_temp_path():
    """adversarial:import scripts.diet 后,diet.DB_PATH(模块级烘焙)必须指向 temp 而非生产"""
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import diet
    baked = Path(diet.DB_PATH)
    assert str(baked.parent.resolve()) != str(PROD_DIR_REAL.resolve()), (
        f"[iso_db] diet.DB_PATH 烘焙到生产: {baked} —— L2 autouse 未覆盖模块级烘焙"
    )
    assert baked.parent.is_dir(), f"[iso_db] diet.DB_PATH 指向不存在目录: {baked}"


# ---------------------------------------------------------------------------
# 4. cwd_sentry 单测(#404 L3 复用 · 逻辑无 pytest hook 依赖,独立可测)
# ---------------------------------------------------------------------------

def _load_cwd_sentry():
    if str(ISO_DB_DIR) not in sys.path:
        sys.path.insert(0, str(ISO_DB_DIR))
    import cwd_sentry
    return cwd_sentry


def test_cwd_sentry_not_demo_in_repo_root(tmp_path, monkeypatch):
    """真实调用路径(cwd 不在 .scratch/,脚本名正常)→ 不隔离"""
    monkeypatch.chdir(SKILL_DIR)
    monkeypatch.setattr(sys, "argv", ["calorie_tracker.py"])
    sentry = _load_cwd_sentry()
    assert sentry.is_demo_path() is False
    assert sentry.ensure_isolation(verbose=False) is None


def test_cwd_sentry_demo_in_scratch_dir(tmp_path, monkeypatch):
    """cwd 含 .scratch/ → 判定为 demo 路径,自动隔离到 temp"""
    scratch_dir = tmp_path / ".scratch" / "demo"
    scratch_dir.mkdir(parents=True)
    monkeypatch.chdir(scratch_dir)
    monkeypatch.setattr(sys, "argv", ["some_script.py"])
    monkeypatch.delenv("SKILLS_DB_PATH", raising=False)
    sentry = _load_cwd_sentry()
    assert sentry.is_demo_path() is True
    result = sentry.ensure_isolation(verbose=False)
    assert result is not None, "demo 路径应自动隔离"
    assert Path(result).is_dir()
    assert os.environ.get("SKILLS_DB_PATH") == str(result)


def test_cwd_sentry_demo_by_script_name(tmp_path, monkeypatch):
    """脚本名 demo_/scratch_/_demo 前缀 → 判定 demo(即使 cwd 正常)"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["demo_render_meal.py"])
    sentry = _load_cwd_sentry()
    assert sentry.is_demo_path() is True


def test_cwd_sentry_force_prod_bypass(tmp_path, monkeypatch):
    """CALORIE_FORCE_PROD=1 → 即使在 demo 路径也不隔离(opt-in 生产)"""
    scratch_dir = tmp_path / ".scratch" / "prod"
    scratch_dir.mkdir(parents=True)
    monkeypatch.chdir(scratch_dir)
    monkeypatch.setattr(sys, "argv", ["demo_x.py"])
    monkeypatch.setenv("CALORIE_FORCE_PROD", "1")
    monkeypatch.delenv("SKILLS_DB_PATH", raising=False)
    sentry = _load_cwd_sentry()
    assert sentry.force_prod_enabled() is True
    assert sentry.is_demo_path() is True
    assert sentry.ensure_isolation(verbose=False) is None, (
        "CALORIE_FORCE_PROD=1 时应跳过隔离"
    )


def test_cwd_sentry_ensure_isolation_skips_when_env_set(tmp_path, monkeypatch):
    """调用方已显式设置 SKILLS_DB_PATH → 哨兵不重复覆盖(demo 路径也不动)"""
    scratch_dir = tmp_path / ".scratch" / "explicit"
    scratch_dir.mkdir(parents=True)
    monkeypatch.chdir(scratch_dir)
    monkeypatch.setattr(sys, "argv", ["demo_x.py"])
    custom = str(tmp_path / "custom_env_dir")
    os.makedirs(custom, exist_ok=True)
    monkeypatch.setenv("SKILLS_DB_PATH", custom)
    sentry = _load_cwd_sentry()
    assert sentry.ensure_isolation(verbose=False) is None
    assert os.environ.get("SKILLS_DB_PATH") == custom


# ---------------------------------------------------------------------------
# 5. hardcode 生产 DB 路径扫描(已知 one-off 脚本豁免 · L1 verify 记录不改 C1.5)
# ---------------------------------------------------------------------------

# 已知 hardcode 生产路径的 one-off 脚本(2026-08-14 L1 verify 报告 + 实测),
# 均为一次性数据导入/CLI 默认参数,非正常 CLI 路径;L1 决策"verify 记录不改"。
# 新增任何 hardcode 文件 → 测试失败,须先消除或显式加入本清单(带理由)。
_KNOWN_HARDCODE_SCRIPTS = {
    "_add_jimmy_dean_products.py",   # 一次性产品导入脚本(Jimmy Dean 鸡排/松饼,L11 直连生产)
    "scan_contraindications.py",     # CLI --db 参数默认值(L64,用户可 --db 覆盖;非模块级烘焙)
}


def test_no_scripts_file_hardcodes_prod_db_path():
    """scripts/*.py 无新增 hardcode 生产 DB 路径(除已知豁免清单)"""
    bad_patterns = [
        r'r["\']D:\\2Study\\StudyNotes\\.db\\calorie_data\.db',
        r'"D:\\2Study\\StudyNotes\\.db\\calorie_data\.db',
        r"'D:\\2Study\\StudyNotes\\.db\\calorie_data\.db",
        r"D:/2Study/StudyNotes/\.db/calorie_data\.db",
    ]
    bad_re = re.compile("|".join(bad_patterns))

    offenders = []
    for py_file in SCRIPTS_DIR.rglob("*.py"):
        if py_file.name in _KNOWN_HARDCODE_SCRIPTS:
            continue
        text = py_file.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if bad_re.search(line) and not line.strip().startswith("#"):
                offenders.append((py_file.relative_to(SKILL_DIR), i, line.strip()))

    assert not offenders, (
        "以下 scripts 文件 hardcode 了生产 DB 路径(违反 ADR-0006 + L2 隔离契约):\n"
        + "\n".join(f"  {p}:{i}: {l}" for p, i, l in offenders)
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
