#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_diet_multi_filename_suffix.py — 批量补记/复制昨日/改/删/同餐合并 回执文件名带内容标识
(issue #266 · 2026-08-12 grilling 拍板 Q1A~Q5A)

拍板方案:
  - 批量补记(--live-diet-batch):首食物+等N项 → 批量补记饮食_回执_米饭等3项_<TS>.html
  - 同餐合并(--live-diet-batch-meal):同批量补记规则(首食物+等N项)
  - 复制昨日饮食(--live-diet-copy):源日期 YYYYMMDD → 复制昨日饮食_回执_20260810_<TS>.html
  - 改饮食记录(--live-diet-update):改后食物名 → 改饮食记录_回执_香蕉_<TS>.html
  - 删饮食记录(--live-diet-delete):被删食物名 → 删饮食记录_回执_清蒸鱼_<TS>.html
  - 兜底:拼接后 _sanitize_filename_part 整体截断 32 + 同秒冲突 _N(与 #49 一致)

⚠️ 隔离说明:本文件端到端用例**自建独立 DB 目录**(tmp_path),不依赖 session 级共享
temp_db —— 避免跨用例数据残留导致幂等防重撞车(2026-08-12 #266 实测:seed 与既有
用例撞车 → add_meal 返回 duplicate → id=None → CLI 用 'None' 当 id 渲染失败)。
"""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / 'scripts'

_CHAIN = '1.测试_266_多命令回执文件名'


# ---------- 隔离 DB 工具(自建独立目录,不碰生产库 / 共享 temp_db) ----------

def _make_db(tmp_path, name='db'):
    """建独立 DB 目录 + init schema,返回 (db_dir, db_path)"""
    db_dir = tmp_path / name
    db_dir.mkdir()
    import db as db_mod
    db_path = db_dir / 'calorie_data.db'
    db_mod.init_db(str(db_path))
    return db_dir, db_path


def _seed_meal(db_path, food='米饭', grams=200, calories=232, protein=4.3,
               date='2026-08-10', time='12:00:00'):
    """往独立 DB 直接写一条饮食记录(不走 add_meal,避免幂等撞车),返回 id"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('''INSERT INTO food_log (date, time, food_name, grams, calories, protein, carbs, fat, note)
                 VALUES (?, ?, ?, ?, ?, ?, 0, 0, '')''',
              (date, time, food, grams, calories, protein))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def _run_render(env_dir, *args):
    """跑 render_crud_receipt.py CLI(隔离 DB:SKILLS_DB_PATH=独立目录)"""
    env = {**os.environ, 'SKILLS_DB_PATH': str(env_dir)}
    return subprocess.run(
        [sys.executable, 'render_crud_receipt.py', *args, '--chain', _CHAIN],
        cwd=str(SCRIPTS_DIR), env=env, capture_output=True, text=True,
        encoding='utf-8', timeout=120)


def _write_json(tmp_path, name, entries):
    p = tmp_path / name
    p.write_text(json.dumps(entries, ensure_ascii=False), encoding='utf-8')
    return p


def _html_names(db_dir, prefix):
    html_dir = db_dir / 'calorie_html'
    return sorted(p.name for p in html_dir.glob(f'{prefix}*.html')) if html_dir.exists() else []


# ---------- 纯函数:_batch_content_suffix ----------

def test_batch_suffix_first_food_and_count(tmp_path):
    from render_crud_receipt import _batch_content_suffix
    p = _write_json(tmp_path, 'batch.json', [
        {'food_name': '米饭', 'grams': 200, 'calories': 232, 'protein': 4.3},
        {'food_name': '清蒸鱼', 'grams': 150, 'calories': 165, 'protein': 28},
        {'food_name': '炒青菜', 'grams': 100, 'calories': 50, 'protein': 2},
    ])
    assert _batch_content_suffix(str(p)) == '米饭等3项'


def test_batch_suffix_first_empty_uses_next(tmp_path):
    """首条 food_name 为空 → 取下一个非空(批量输入可能含空名条目)"""
    from render_crud_receipt import _batch_content_suffix
    p = _write_json(tmp_path, 'batch.json', [
        {'food_name': '', 'grams': 200, 'calories': 232, 'protein': 4.3},
        {'food_name': '面条', 'grams': 150, 'calories': 165, 'protein': 28},
    ])
    assert _batch_content_suffix(str(p)) == '面条等2项'


def test_batch_suffix_empty_or_invalid_returns_none(tmp_path):
    from render_crud_receipt import _batch_content_suffix
    assert _batch_content_suffix(str(tmp_path / 'missing.json')) is None
    # 文件存在但内容非数组(对象)→ None
    bad = tmp_path / 'bad.json'
    bad.write_text('{"food_name": "米饭"}', encoding='utf-8')
    assert _batch_content_suffix(str(bad)) is None
    # 空数组 → None
    empty = tmp_path / 'empty.json'
    empty.write_text('[]', encoding='utf-8')
    assert _batch_content_suffix(str(empty)) is None


# ---------- 端到端:批量补记 / 同餐合并 / 复制昨日(独立 DB) ----------

def test_e2e_batch_filename_first_food_and_count(tmp_path):
    """批量补记 3 条 → 批量补记饮食_回执_米饭等3项_<TS>.html"""
    db_dir, _ = _make_db(tmp_path)
    p = _write_json(tmp_path, 'batch.json', [
        {'food_name': '米饭', 'grams': 200, 'calories': 232, 'protein': 4.3},
        {'food_name': '清蒸鱼', 'grams': 150, 'calories': 165, 'protein': 28},
        {'food_name': '炒青菜', 'grams': 100, 'calories': 50, 'protein': 2},
    ])
    res = _run_render(db_dir, '--live-diet-batch', '--input', str(p))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '批量补记饮食_回执_')
    assert any('米饭等3项_' in n for n in names), names


def test_e2e_batch_meal_filename_first_food_and_count(tmp_path):
    """同餐合并 3 个食物 → 记一餐(同餐合并)_回执_米饭等3项_<TS>.html"""
    db_dir, _ = _make_db(tmp_path)
    p = _write_json(tmp_path, 'meal.json', [
        {'food_name': '米饭', 'grams': 200, 'calories': 232, 'protein': 4.3},
        {'food_name': '清蒸鱼', 'grams': 150, 'calories': 165, 'protein': 28},
        {'food_name': '豆腐汤', 'grams': 300, 'calories': 90, 'protein': 6},
    ])
    res = _run_render(db_dir, '--live-diet-batch-meal', '--input', str(p))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '记一餐(同餐合并)_回执_')
    assert any('米饭等3项_' in n for n in names), names


def test_e2e_copy_filename_source_date(tmp_path):
    """复制昨日饮食 → 复制昨日饮食_回执_20260810_<TS>.html(源日期,YYYYMMDD 无连字符)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_meal(db_path, food='米饭', date='2026-08-10', time='12:00:00')
    res = _run_render(db_dir, '--live-diet-copy', '--from', '2026-08-10')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '复制昨日饮食_回执_')
    assert any('_20260810_' in n for n in names), names


def test_e2e_copy_default_from_yesterday(tmp_path):
    """不传 --from → 默认昨天,文件名带昨天日期(YYYYMMDD)"""
    from datetime import date, timedelta
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    ymd = yesterday.replace('-', '')
    db_dir, db_path = _make_db(tmp_path)
    _seed_meal(db_path, food='苹果', date=yesterday, time='08:00:00')
    res = _run_render(db_dir, '--live-diet-copy')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '复制昨日饮食_回执_')
    assert any(f'_{ymd}_' in n for n in names), names


# ---------- 端到端:改 / 删饮食记录(独立 DB) ----------

def test_e2e_update_filename_after_food(tmp_path):
    """改饮食记录 → 改饮食记录_回执_<改后名>_<TS>.html"""
    db_dir, db_path = _make_db(tmp_path)
    rec_id = _seed_meal(db_path, food='燕麦', date='2026-08-12', time='07:00:00')
    res = _run_render(db_dir, '--live-diet-update', str(rec_id), '--food', '香蕉')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改饮食记录_回执_')
    assert any('_香蕉_' in n for n in names), names


def test_e2e_delete_filename_before_food(tmp_path):
    """删饮食记录 → 删饮食记录_回执_<被删名>_<TS>.html"""
    db_dir, db_path = _make_db(tmp_path)
    rec_id = _seed_meal(db_path, food='清蒸鱼', date='2026-08-10', time='12:30:00')
    res = _run_render(db_dir, '--live-diet-delete', str(rec_id))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删饮食记录_回执_')
    assert any('_清蒸鱼_' in n for n in names), names


# ---------- 冲突兜底(同秒同名 → _2) ----------

def test_e2e_batch_same_content_twice_conflict(tmp_path):
    """同秒两次相同批量补记 → 第二个文件名 _2 后缀仍工作"""
    db_dir, _ = _make_db(tmp_path)
    p = _write_json(tmp_path, 'batch.json', [
        {'food_name': '米饭', 'grams': 200, 'calories': 232, 'protein': 4.3},
    ])
    res1 = _run_render(db_dir, '--live-diet-batch', '--input', str(p))
    assert res1.returncode == 0, res1.stderr
    res2 = _run_render(db_dir, '--live-diet-batch', '--input', str(p))
    assert res2.returncode == 0, res2.stderr
    names = _html_names(db_dir, '批量补记饮食_回执_')
    assert len(names) >= 2
    assert any('_2.' in n for n in names), names


def test_e2e_copy_same_source_twice_conflict(tmp_path):
    """同秒两次复制同一源日期 → 第二个文件名 _2 后缀仍工作"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_meal(db_path, food='鸡蛋', date='2026-08-11', time='08:00:00')
    res1 = _run_render(db_dir, '--live-diet-copy', '--from', '2026-08-11')
    assert res1.returncode == 0, res1.stderr
    res2 = _run_render(db_dir, '--live-diet-copy', '--from', '2026-08-11')
    assert res2.returncode == 0, res2.stderr
    names = _html_names(db_dir, '复制昨日饮食_回执_')
    assert len(names) >= 2
    assert any('_2.' in n for n in names), names
