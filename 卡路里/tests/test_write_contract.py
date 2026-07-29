#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_write_contract.py — 写入后回执契约真跑测试

V1.0 SKILL开发总纲 V1.0 §02 第 ② 特性 "可验证 · 写入后回执":

    写入后回执 | 返回 ID + 时间戳 + 影响行数

P3 真跑版(非 grep 静态分析)— 每个写库类 CLI 子命令跑一次,验证 stdout:
  1. 含 'id=' 标记(V1.0 §02 第②特性"返回 ID")
  2. 含 YYYY-MM-DD 日期标记(V1.0 §02 第②特性"时间戳")
  3. 含 '影响' 标记(V1.0 §02 第②特性"影响行数")

失败模式(已发生):
  - v2.4.13 之前 weight CLI 只 print "✓ 体重已记录: 70.0" — 缺 ID,违反 §02 第②特性
  - v2.4.14 修复

测试隔离:
  - SKILLS_DB_PATH 指向临时 DB,不污染用户数据
  - 每个 test 用独立 tempdir

用法:
  cd 卡路里 && python3 -m pytest tests/test_write_contract.py -v
"""
import os
import re
import subprocess
import sys
import tempfile

import pytest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")


# ============= 工具函数 =============

def _run_cli(*args, db_dir, db_filename="calorie_data.db", timeout=15):
    """真跑 calorie_tracker.py 子命令,stdout 返 str

    Args:
        *args:           CLI 子命令参数,例如 ["weight", "70.5", "--note", "x"]
        db_dir:          SKILLS_DB_PATH 环境变量指向的目录;DB 文件 <db_dir>/<db_filename>
        db_filename:     DB 文件名(默认 calorie_data.db)
    """
    os.makedirs(db_dir, exist_ok=True)
    env = os.environ.copy()
    env["SKILLS_DB_PATH"] = str(db_dir)
    r = subprocess.run(
        [sys.executable, os.path.join(SCRIPTS_DIR, "calorie_tracker.py"), *args],
        capture_output=True, text=True, timeout=timeout, env=env,
        encoding="utf-8", errors="replace",
    )
    return r.returncode, r.stdout, r.stderr


def _init_db_with_profile(db_dir, age=30, gender="male", height=177):
    """建临时 DB + 设身高(weight CLI 依赖)

    Args:
        db_dir: DB 所在目录(SKILLS_DB_PATH 会指向这)
    """
    import sqlite3
    sys.path.insert(0, SCRIPTS_DIR)
    import db as db_mod
    db_path = os.path.join(db_dir, "calorie_data.db")
    db_mod.init_db(db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    # init_db 已建 user_profile 表 + 身高列(CHECK 身高必须 > 0)
    c.execute('''
        INSERT INTO user_profile (id, age, gender, height_cm)
        VALUES (1, ?, ?, ?)
    ''', (age, gender, height))
    conn.commit()
    conn.close()


def _init_db(db_dir):
    """建空 DB(无需 user_profile,给 list / summary / read-only 测试用)"""
    import sqlite3
    sys.path.insert(0, SCRIPTS_DIR)
    import db as db_mod
    db_path = os.path.join(db_dir, "calorie_data.db")
    db_mod.init_db(db_path)


# ============= fixtures =============

@pytest.fixture
def tmp_db_dir():
    """每个 test 一个 tmpdir,DB 文件 <tmpdir>/calorie_data.db"""
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def tmp_db(tmp_db_dir):
    """初始化完好的临时 DB(含 user_profile 身高)— 写库类测试用"""
    _init_db_with_profile(tmp_db_dir)
    return tmp_db_dir


@pytest.fixture
def tmp_db_empty(tmp_db_dir):
    """仅 init_db,无 user_profile — 只读测试用"""
    _init_db(tmp_db_dir)
    return tmp_db_dir


# ============= 测试 =============

# 写库类子命令的 stdout 必须包含 3 个契约标记
# tuple 4 元: (cmd_args, label, known_violation_reason, seed_cmds)
#   - reason=None → 必须 pass(V1.0 §02 第②特性合规)
#   - reason=str  → xfail:已知违反,等后续 commit 修(strict=True)
#   - seed_cmds=list → 跑 cmd_args 前先跑这些种子命令(例:update-meal 需要先有 add 的 id)
#                      None/[] = 无前置
WRITE_CONTRACTS = [
    # ===== v2.4.16 已修 =====
    (["weight", "70.5", "--note", "test"],  "weight",   None, None, None, None),
    (["water", "500"],                      "water",    None, None, None, None),
    (["add", "鸡胸肉", "165", "31"],        "add",      None, None, None, None),

    # ===== v2.4.17 扩展:其余写库子命令 =====
    # 3 字段独立标记: id_缺 / timestamp_缺 / rows_缺 各自的 xfail reason
    (["weight-update", "1", "--weight", "71"],
     "weight-update",
     None,  # v2.4.18a 修:id= 标记
     None,  # v2.4.18a 修:YYYY-MM-DD 时间戳
     None,  # v2.4.18a 修:"影响" 字样
     [["weight", "70.5", "--note", "test"]]),
    (["delete", "1"],
     "delete",
     "v2.4.17 扩 P3: delete print 'Deleted entry 1' 缺 id=",
     "v2.4.17 扩 P3: delete stdout 缺 YYYY-MM-DD",
     "v2.4.17 扩 P3: delete 缺 '影响' 字样",
     [["add", "test", "100", "10"]]),
    (["update-meal", "1", "--calories", "200"],
     "update-meal",
     "v2.4.17 扩 P3: update-meal stdout 缺 id=",
     "v2.4.17 扩 P3: update-meal stdout 缺 YYYY-MM-DD",
     "v2.4.17 扩 P3: update-meal stdout 缺 '影响' 字样",
     [["add", "test", "100", "10"]]),
    (["goal", "2000", "150", "200", "60", "2000"],
     "goal",
     "v2.4.17 扩 P3: goal stdout 缺 id=",
     "v2.4.17 扩 P3: goal stdout 缺 YYYY-MM-DD",
     "v2.4.17 扩 P3: goal stdout 缺 '影响' 字样",
     None),
(["weight-goal", "--legacy-positional", "75", "2026-12-31"],
      "weight-goal",
      None,  # ticket 04 增量:weight-goal 现已写回执契约(id= + 日期 + 影响 行),合规
      None,
      None,
      None),
    (["add-product", "x", "x", "0", "0", "0", "0", "0", "0", "0", "0"],
     "add-product",
     "v2.4.17 扩 P3: add-product stdout 缺 id=/时间/影响",
     "v2.4.17 扩 P3: add-product stdout 缺 YYYY-MM-DD",
     "v2.4.17 扩 P3: add-product stdout 缺 '影响' 字样",
     None),
    (["update-product", "1", "--calories", "45"],
     "update-product",
     "v2.4.17 扩 P3: update-product stdout 缺 id=",
     "v2.4.17 扩 P3: update-product stdout 缺 YYYY-MM-DD",
     "v2.4.17 扩 P3: update-product stdout 缺 '影响' 字样",
     [["add-product", "x", "x", "0", "0", "0", "0", "0", "0", "0", "0"]]),
    (["exercise-add", "跑步", "300", "--minutes", "30"],
     "exercise-add",
     "v2.4.17 扩 P3: exercise-add stdout 缺 id=",
     "v2.4.17 扩 P3: exercise-add stdout 缺 YYYY-MM-DD",
     "v2.4.17 扩 P3: exercise-add stdout 缺 '影响' 字样",
     None),
    (["profile", "set", "30", "male", "--height", "180"],
     "profile",
     "v2.4.17 扩 P3: profile set stdout 缺 id=",
     None,  # '更新时间: 2026-xx-xxTxx:xx:xx' 命中 YYYY-MM-DD → 合规
     "v2.4.17 扩 P3: profile set stdout 缺 '影响' 字样",
     None),
]


def _maybe_xfail_violation(request, violation, marker):
    """如果 violation 是 str,对该测试加 xfail;否则不加"""
    if violation:
        request.applymarker(pytest.mark.xfail(reason=violation, strict=True))


def _run_with_seed(cmd_args, seed_cmds, db_dir):
    """先跑 seed (如有),再跑 cmd_args"""
    if seed_cmds:
        for seed in seed_cmds:
            _run_cli(*seed, db_dir=db_dir)
    return _run_cli(*cmd_args, db_dir=db_dir)




@pytest.mark.parametrize(
    "cmd_args,label,k_id,k_ts,k_rows,seed_cmds",
    WRITE_CONTRACTS,
)
def test_write_contract_id_marker(
    cmd_args, label, k_id, k_ts, k_rows, seed_cmds, tmp_db, request,
):
    """V1.0 §02 第②特性:写库回执必须含 'id=' 标记"""
    _maybe_xfail_violation(request, k_id, "id")
    db_dir = tmp_db
    rc, out, err = _run_with_seed(cmd_args, seed_cmds, db_dir)
    assert 'id=' in out, (
        f"❌ {label} 写库回执缺 'id=' 标记\n"
        f"  违反 V1.0 §02 第②特性 '写入后回执 = ID + 时间戳 + 影响行数'\n"
        f"  当前 stdout:\n{out}\n"
        f"  stderr:\n{err}"
    )


@pytest.mark.parametrize(
    "cmd_args,label,k_id,k_ts,k_rows,seed_cmds",
    WRITE_CONTRACTS,
)
def test_write_contract_timestamp_marker(
    cmd_args, label, k_id, k_ts, k_rows, seed_cmds, tmp_db, request,
):
    """V1.0 §02 第②特性:写库回执必须含 YYYY-MM-DD 时间戳"""
    _maybe_xfail_violation(request, k_ts, "timestamp")
    db_dir = tmp_db
    rc, out, err = _run_with_seed(cmd_args, seed_cmds, db_dir)
    assert re.search(r'\d{4}-\d{2}-\d{2}', out), (
        f"❌ {label} 写库回执缺 YYYY-MM-DD 日期\n"
        f"  违反 V1.0 §02 第②特性 '时间戳'\n"
        f"  当前 stdout:\n{out}"
    )


@pytest.mark.parametrize(
    "cmd_args,label,k_id,k_ts,k_rows,seed_cmds",
    WRITE_CONTRACTS,
)
def test_write_contract_rows_affected_marker(
    cmd_args, label, k_id, k_ts, k_rows, seed_cmds, tmp_db, request,
):
    """V1.0 §02 第②特性:写库回执必须含 '影响' 标记(影响行数)"""
    _maybe_xfail_violation(request, k_rows, "rows")
    db_dir = tmp_db
    rc, out, err = _run_with_seed(cmd_args, seed_cmds, db_dir)
    assert '影响' in out, (
        f"❌ {label} 写库回执缺 '影响' 标记\n"
        f"  违反 V1.0 §02 第②特性 '影响行数'\n"
        f"  当前 stdout:\n{out}"
    )


# ============= 健康检查 =============

def test_readonly_commands_dont_need_id(tmp_db):
    """只读命令(list / summary / history)不应该被强求 ID — 设计边界

    V1.0 §02 第②特性:写入后回执。读命令没"写入",没"ID"概念。
    这条测试是**反向契约**,防止过度工程 — 别哪天有人在 P3 加了 P2 把读命令也强制要 ID。
    """
    db_dir = tmp_db

    # 测 list(只读)
    rc, out, err = _run_cli("list", db_dir=db_dir)
    # 不强制要 'id=' — list 不写库
    # 但 list 应当接通 render,stdout 应含 ACTION=SEND_TO_USER 标记(V1.3 §HTML 交付协议)
    assert 'SEND_TO_USER' in out or rc != 0, (
        f"list 应当走 HTML 路径或报错(V1.3 §04 决策矩阵 ✅ 必 HTML)\nstdout: {out}"
    )


# ============= 模块说明 =============
#
# 设计的"可覆盖"清单(参数化):
#   - weight          写库类 · 已修 v2.4.14
#   - water           写库类 · 是否已修?待查
#   - add (食物)      写库类 · 是否已修?待查
#
# 设计的"故意不覆盖"(只读契约):
#   - list / summary / history — V1.0 §04 决策矩阵 触发 HTML,不是写库
#
# 未来加 trigger 时:
#   1. 新 trigger 是写库类 → 加进 WRITE_CONTRACTS
#   2. 新 trigger 是只读类 → 测 HTML 路径(test_readonly_commands_dont_need_id 是模板)
#   3. commit 前 python3 -m pytest tests/ 自动跑全套
