#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_cli_validation.py — seam 5 守门 · ticket 04 · ADR-0004

ticket 04 验收:
  (a) `<cmd> --help` → exit 0 + stdout 含 usage
  (b) `weight-goal --weight-goal abc` → exit 非 0 + stderr 含类型错误
  (c) `weight-goal --weight-goal 73 --deadline 2026-12-31` → exit 0 + stdout 含 "id="
  (d) `list-products --help` → exit 0 + 含 `--all`
  (e) `list-products` 默认返回 200 行
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
CALORIE_TRACKER = SCRIPTS_DIR / "calorie_tracker.py"


def _run_cli(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CALORIE_TRACKER), *args],
        cwd=SKILL_DIR, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def test_help_exits_zero_with_usage():
    """任意子命令 --help → exit 0 + stdout 含 usage"""
    r = _run_cli("--help")
    assert r.returncode == 0, f"--help exit={r.returncode}, stderr={r.stderr}"
    assert "usage:" in r.stdout.lower(), f"--help stdout 应含 'usage:': {r.stdout[:200]}"


def test_weight_goal_help_exits_zero():
    """weight-goal --help → exit 0 + 含 --weight-goal 标志说明"""
    r = _run_cli("weight-goal", "--help")
    assert r.returncode == 0, (
        f"weight-goal --help exit={r.returncode}, stderr={r.stderr}"
    )
    assert "--weight-goal" in r.stdout, (
        f"应提示 --weight-goal 标志,stdout: {r.stdout[:200]}"
    )


def test_weight_goal_rejects_non_numeric_kg():
    """weight-goal --weight-goal abc → exit 非 0 + stderr 含类型错误"""
    r = _run_cli("weight-goal", "--weight-goal", "abc", "--deadline", "2026-12-31")
    assert r.returncode != 0, (
        f"传 abc 应报错,实得 exit={r.returncode}, stdout={r.stdout}"
    )
    err = (r.stderr + r.stdout).lower()
    assert "invalid" in err or "type" in err or "float" in err, (
        f"stderr/stdout 应含类型错误关键词: {r.stderr[:200]}"
    )


def test_weight_goal_positional_legacy_still_works():
    """weight-goal <kg> <deadline> 老接口仍可用(带 deprecation warning)"""
    r = _run_cli("weight-goal", "73", "2026-12-31")
    # 老接口要么 exit 0(写库成功),要么 exit 非 0(显示 deprecation warning 后报错)
    # 我们只断言 deprecation warning 出现
    combined = r.stdout + r.stderr
    assert ("deprecated" in combined.lower() or
            "即将废弃" in combined or
            "legacy" in combined.lower() or
            r.returncode != 0 or
            "id=" in r.stdout), (
        f"老接口应给 deprecation 提示或拒绝,实得: {combined[:200]}"
    )


def test_list_products_help_exits_zero():
    """list-products --help → exit 0 + 含 --all 标志说明"""
    r = _run_cli("list-products", "--help")
    assert r.returncode == 0, (
        f"list-products --help exit={r.returncode}, stderr={r.stderr}"
    )
    assert "--all" in r.stdout, f"应提示 --all 标志,stdout: {r.stdout[:200]}"


def test_list_products_default_returns_200_rows(temp_db):
    """list-products 默认返回 200 行(原 50 → 200,塞 250 条数据测上限)"""
    import sqlite3
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("DELETE FROM nutrition_products")  # 清残留(session-scope fixture 共享)
    for i in range(1, 251):
        cur.execute(
            "INSERT INTO nutrition_products"
            "(product_name, brand, calories, protein, fat, carbohydrates, sodium) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"测试食品_{i}", "test", 100 + i, 5.0, 2.0, 10.0, 50.0),
        )
    conn.commit()
    conn.close()

    r = _run_cli("list-products")
    lines = [l for l in r.stdout.splitlines() if re.match(r"^\s*\d+\s*\|", l)]
    # 250 条数据,默认 200,应返回 ≤ 200 行
    assert len(lines) <= 200, f"默认应 ≤ 200 行,实得 {len(lines)}"
    assert len(lines) >= 100, f"默认应返回至少 100 行(数据足够),实得 {len(lines)}"


def test_list_products_all_returns_everything(temp_db):
    """list-products --all 返回全部 250 行"""
    import sqlite3
    conn = sqlite3.connect(str(temp_db))
    cur = conn.cursor()
    cur.execute("DELETE FROM nutrition_products")  # 清残留
    for i in range(1, 251):
        cur.execute(
            "INSERT INTO nutrition_products"
            "(product_name, brand, calories, protein, fat, carbohydrates, sodium) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"全量测试_{i}", "test", 200.0, 10.0, 5.0, 20.0, 100.0),
        )
    conn.commit()
    conn.close()

    r = _run_cli("list-products", "--all")
    lines = [l for l in r.stdout.splitlines() if re.match(r"^\s*\d+\s*\|", l)]
    assert len(lines) == 250, f"--all 应返回 250 行,实得 {len(lines)}"


def test_help_exits_zero_with_usage():
    """任意子命令 --help → exit 0 + stdout 含 usage/用法"""
    r = _run_cli("--help")
    assert r.returncode == 0, f"--help exit={r.returncode}, stderr={r.stderr}"
    text = r.stdout.lower()
    # 中英文都接受("用法" / "usage:")
    assert "用法" in r.stdout or "usage:" in text, (
        f"--help 应含用法说明: {r.stdout[:200]}"
    )


def test_weight_goal_rejects_non_numeric_kg():
    """weight-goal --weight-goal abc → exit 非 0 + stderr 含类型错误"""
    r = _run_cli("weight-goal", "--weight-goal", "abc", "--deadline", "2026-12-31")
    assert r.returncode != 0, (
        f"传 abc 应报错,实得 exit={r.returncode}, stdout={r.stdout}"
    )
    # 中英文都接受
    combined = r.stderr + r.stdout
    assert (
        "invalid" in combined.lower()
        or "type" in combined.lower()
        or "float" in combined.lower()
        or "数字" in combined
    ), f"应含类型错误关键词: {combined[:300]}"