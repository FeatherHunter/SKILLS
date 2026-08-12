#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_non_diet_filename_suffix.py — 喝水/食品/体重 回执文件名带内容标识
(issue #284 · 2026-08-12 grilling 全 A 拍板 · #266 姊妹项)

拍板方案:
  - 记喝水(--live-water-add):本次毫升 → 记喝水_回执_500ml_<TS>.html
  - 存食品(--live-product-add):食品名 → 存食品_回执_香蕉_<TS>.html
  - 改食品(--live-product-update):总是带食品名(改名带改后名;只改营养字段带原名)
  - 下架食品(--live-product-deprecate):食品名 → 下架食品_回执_香蕉_<TS>.html
  - 改体重记录(--live-weight-update):日期 YYYYMMDD → 改体重记录_回执_20260812_<TS>.html
  - 删体重记录(--live-weight-delete --id):记录日期 → 删体重记录_回执_20260812_<TS>.html
  - 删某日体重(--live-weight-delete --date):目标日期 → 删某日体重_回执_20260812_<TS>.html
  - 批量删体重(--live-weight-delete --start/--end):起止范围 → 批量删体重_回执_20260809至20260812_<TS>.html
  - 兜底:拼接后 _sanitize_filename_part 整体截断 32 + 同秒冲突 _N(与 #49/#266 一致)

⚠️ 隔离说明:端到端用例**自建独立 DB 目录**(tmp_path),不依赖 session 级共享 temp_db
(2026-08-12 #266 实测教训:共享 temp_db 跨用例数据残留会撞车)。
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / 'scripts'

_CHAIN = '1.测试_284_非饮食域回执文件名'


# ---------- 隔离 DB 工具(自建独立目录,不碰生产库 / 共享 temp_db) ----------

def _make_db(tmp_path, name='db'):
    """建独立 DB 目录 + init schema,返回 (db_dir, db_path)"""
    db_dir = tmp_path / name
    db_dir.mkdir()
    import db as db_mod
    db_path = db_dir / 'calorie_data.db'
    db_mod.init_db(str(db_path))
    return db_dir, db_path


def _seed_weight(db_path, date='2026-08-12', time='07:00:00', weight_kg=68.5):
    """往独立 DB 直接写一条体重记录,返回 id"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('''INSERT INTO weight_log (date, time, weight_kg, bmi, note)
                 VALUES (?, ?, ?, 22.1, '')''', (date, time, weight_kg))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def _seed_product(db_path, name='香蕉', calories=89.0):
    """往独立 DB 直接写一条食品,返回 id"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('''INSERT INTO nutrition_products
                 (product_name, brand, calories, protein, fat, saturated_fat,
                  carbohydrates, sugar, dietary_fiber, sodium, source)
                 VALUES (?, '都乐', ?, 1.1, 0.3, 0, 22, 12, 1, 1, '手动录入')''',
              (name, calories))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def _seed_profile(db_path, height_cm=177.0):
    """写用户档案身高(update_weight 重算 BMI 的前置条件 · 无身高返回 None 无法改体重)"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("INSERT INTO user_profile (id, age, gender, height_cm) VALUES (1, 30, 'male', ?)",
              (height_cm,))
    conn.commit()
    conn.close()


def _run_render(env_dir, *args):
    """跑 render_crud_receipt.py CLI(隔离 DB:SKILLS_DB_PATH=独立目录)"""
    env = {**os.environ, 'SKILLS_DB_PATH': str(env_dir)}
    return subprocess.run(
        [sys.executable, 'render_crud_receipt.py', *args, '--chain', _CHAIN],
        cwd=str(SCRIPTS_DIR), env=env, capture_output=True, text=True,
        encoding='utf-8', timeout=120)


def _html_names(db_dir, prefix):
    html_dir = db_dir / 'calorie_html'
    return sorted(p.name for p in html_dir.glob(f'{prefix}*.html')) if html_dir.exists() else []


# ---------- 端到端:记喝水 ----------

def test_e2e_water_filename_ml(tmp_path):
    """记喝水 500 → 记喝水_回执_500ml_<TS>.html(本次毫升)"""
    db_dir, _ = _make_db(tmp_path)
    res = _run_render(db_dir, '--live-water-add', '500')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '记喝水_回执_')
    assert any('_500ml_' in n for n in names), names


# ---------- 端到端:食品(存 / 改 / 下架) ----------

def test_e2e_product_add_filename_name(tmp_path):
    """存食品 → 存食品_回执_香蕉_<TS>.html(食品名)"""
    db_dir, _ = _make_db(tmp_path)
    res = _run_render(db_dir, '--live-product-add', '香蕉', '都乐', '89', '1.1', '0.3',
                      '0', '22', '12', '1', '1', '无')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '存食品_回执_')
    assert any('_香蕉_' in n for n in names), names


def test_e2e_product_update_filename_renamed(tmp_path):
    """改食品改名 → 改食品_回执_<改后名>_<TS>.html"""
    db_dir, db_path = _make_db(tmp_path)
    pid = _seed_product(db_path, name='香蕉')
    res = _run_render(db_dir, '--live-product-update', str(pid), '--product_name', '香蕉(熟)')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改食品_回执_')
    assert any('香蕉(熟)' in n for n in names), names


def test_e2e_product_update_filename_original_when_nutrition_only(tmp_path):
    """改食品只改热量(没改名)→ 仍带原名:改食品_回执_香蕉_<TS>.html
    (回执 new_record 只含被改字段,原名从 summary「已更新「X」」兜底 · 2026-08-12)"""
    db_dir, db_path = _make_db(tmp_path)
    pid = _seed_product(db_path, name='香蕉', calories=89.0)
    res = _run_render(db_dir, '--live-product-update', str(pid), '--calories', '100')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改食品_回执_')
    assert any('_香蕉_' in n for n in names), names


def test_e2e_product_deprecate_filename_name(tmp_path):
    """下架食品 → 下架食品_回执_香蕉_<TS>.html(食品名)"""
    db_dir, db_path = _make_db(tmp_path)
    pid = _seed_product(db_path, name='香蕉')
    res = _run_render(db_dir, '--live-product-deprecate', str(pid))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '下架食品_回执_')
    assert any('_香蕉_' in n for n in names), names


# ---------- 端到端:体重(改 / 删) ----------

def test_e2e_weight_update_by_id_filename_date(tmp_path):
    """按 ID 改体重 → 改体重记录_回执_20260812_<TS>.html(记录日期)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_profile(db_path)
    wid = _seed_weight(db_path, date='2026-08-12', weight_kg=68.5)
    res = _run_render(db_dir, '--live-weight-update', str(wid), '--weight', '68')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改体重记录_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_weight_update_by_date_filename_date(tmp_path):
    """按日期改体重 → 改体重记录_回执_20260812_<TS>.html(目标日期)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_profile(db_path)
    _seed_weight(db_path, date='2026-08-12', weight_kg=68.5)
    res = _run_render(db_dir, '--live-weight-update', '2026-08-12', '--weight', '68')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改体重记录_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_weight_delete_by_id_filename_date(tmp_path):
    """按 ID 删体重 → 删体重记录_回执_20260812_<TS>.html(记录日期)"""
    db_dir, db_path = _make_db(tmp_path)
    wid = _seed_weight(db_path, date='2026-08-12', weight_kg=68.5)
    res = _run_render(db_dir, '--live-weight-delete', '--id', str(wid))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删体重记录_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_weight_delete_by_date_filename_date(tmp_path):
    """按日期删体重 → 删某日体重_回执_20260812_<TS>.html(目标日期)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_weight(db_path, date='2026-08-12', weight_kg=68.5)
    res = _run_render(db_dir, '--live-weight-delete', '--date', '2026-08-12')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删某日体重_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_weight_delete_range_filename_span(tmp_path):
    """批量删体重 → 批量删体重_回执_20260809至20260812_<TS>.html(起止范围)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_weight(db_path, date='2026-08-09', weight_kg=69.0)
    _seed_weight(db_path, date='2026-08-12', weight_kg=68.5)
    res = _run_render(db_dir, '--live-weight-delete', '--start', '2026-08-09', '--end', '2026-08-12')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '批量删体重_回执_')
    assert any('_20260809至20260812_' in n for n in names), names


# ---------- 端到端:体重删除 · pos 裸位置参数形式(#284 顺手修 cmd_name 路径的测试覆盖) ----------

def test_e2e_weight_delete_by_pos_id_filename_date(tmp_path):
    """删体重记录 · pos 裸数字 id → 删体重记录_回执_20260812_<TS>.html"""
    db_dir, db_path = _make_db(tmp_path)
    wid = _seed_weight(db_path, date='2026-08-12', weight_kg=68.5)
    res = _run_render(db_dir, '--live-weight-delete', str(wid))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删体重记录_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_weight_delete_by_pos_date_filename_date(tmp_path):
    """删某日体重 · pos 裸日期 → 删某日体重_回执_20260812_<TS>.html
    (2026-08-12 顺手修:pos 裸日期原 cmd_name 漏设,会错名成「删体重记录」)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_weight(db_path, date='2026-08-12', weight_kg=68.5)
    res = _run_render(db_dir, '--live-weight-delete', '2026-08-12')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删某日体重_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_weight_delete_by_pos_range_filename_span(tmp_path):
    """批量删体重 · pos 裸起止 → 批量删体重_回执_20260809至20260812_<TS>.html"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_weight(db_path, date='2026-08-09', weight_kg=69.0)
    _seed_weight(db_path, date='2026-08-12', weight_kg=68.5)
    res = _run_render(db_dir, '--live-weight-delete', '2026-08-09', '2026-08-12')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '批量删体重_回执_')
    assert any('_20260809至20260812_' in n for n in names), names


# ---------- 冲突兜底说明 ----------
# 同秒同名冲突 _2/_3 是 html_paths 纯函数层职责(#49 已覆盖),端到端不重复测
# 时序敏感场景两次 subprocess 可能跨秒 → TS 不同 → 无 _2,测试偶发失败污染回归
# 可信度(2026-08-12 实测教训)。本文件聚焦「suffix 内容标识正确传入」。
