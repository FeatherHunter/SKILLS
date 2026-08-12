#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_other_receipt_filename_suffix.py — 运动/体重/计划/身材照/删体脂 回执文件名带内容标识
(issue #286 · 2026-08-12 grilling 全 A 拍板 · #266/#284 治理链姊妹项)

拍板方案(全 A · 按场景语义各带各的):
  运动(render_exercise_receipt.py · 11 场景):
    - 记运动/力量/日常/补记:运动名 → 记运动_回执_跑步_<TS>.html
    - 批量补记:首类型+等N项 → 批量补记运动_回执_跑步等2项_<TS>.html
    - 复制昨日:源日期 YYYYMMDD → 复制昨日运动_回执_20260811_<TS>.html
    - 改运动记录:改后运动名(只改其他字段=原名) → 改运动记录_回执_游泳_<TS>.html
    - 改某日:日期 → 改某日运动_回执_20260812_<TS>.html
    - 删运动记录:被删运动名 → 删运动记录_回执_跑步_<TS>.html
    - 删某日:日期 → 删某日运动_回执_20260812_<TS>.html
    - 批量删:起止范围 → 批量删运动_回执_20260809至20260812_<TS>.html
  体重(render_weight_receipt.py · 2 场景):
    - 记体重/含备注/补录:体重值(format 'g' 去尾零) → 记体重_回执_70.5kg_<TS>.html
    - 批量补录体重:首条+等N项 → 批量补录体重_回执_70kg等2项_<TS>.html
  计划(render_plan_receipt.py · 12 场景):
    - 定/复制/改/撤销计划:计划名 → 定训练计划_回执_8周增肌循环_<TS>.html
    - 定休息日/改某天/删某天:第N周周X → 定休息日_回执_第1周周1_<TS>.html
    - 加动作:动作名 → 加训练动作_回执_深蹲_<TS>.html
    - 定一周:第N周 → 定一周计划_回执_第2周_<TS>.html
    - 改动作:改后动作名 → 改动作_回执_深蹲_<TS>.html
    - 同步/拉训记:日期 YYYYMMDD → 同步到训记_回执_20260812_<TS>.html
  身材照(render_body_photo_receipt.py · 5 场景):
    - 存照片:标签(批量:首标签+等N项) → 存一张照片_回执_正面_<TS>.html
    - 删身材照:照片日期 → 删身材照_回执_20260812_<TS>.html
    - 改照片标签:改后全标签 → 改照片标签_回执_正面、侧面_<TS>.html
    - 加/删照片标签:实际新增/移除的标签
  删体脂/删围度(render_body_delete_receipt.py · 2 场景):
    - 记录日期 YYYYMMDD → 删体脂_回执_20260812_<TS>.html
  兜底:提取失败 → None 保持原文件名,不因标识失败而崩;suffix 由 _sanitize_filename_part
  整体截断 32 + 同秒冲突 _N(与 #49/#266/#284 一致,html_paths 纯函数层已测,端到端不重复)。

⚠️ 隔离说明:端到端用例**自建独立 DB 目录**(tmp_path),不依赖 session 级共享 temp_db
(#266 实测教训:共享 temp_db 跨用例数据残留会撞车)。subprocess 显式 encoding='utf-8'
(2026-08-11 sitecustomize 全局 UTF-8 × text=True cp936 解码崩教训)。
"""
import base64
import json
import os
import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / 'scripts'

_CHAIN = '1.测试_286_回执文件名内容标识'

# 1x1 像素 PNG(身材照用例的假照片)
_PNG = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')


# ---------- 隔离 DB 工具(自建独立目录,不碰生产库 / 共享 temp_db) ----------

def _make_db(tmp_path, name='db'):
    """建独立 DB 目录 + init schema,返回 (db_dir, db_path)"""
    db_dir = tmp_path / name
    db_dir.mkdir()
    import db as db_mod
    db_path = db_dir / 'calorie_data.db'
    db_mod.init_db(str(db_path))
    return db_dir, db_path


def _conn(db_dir):
    return sqlite3.connect(str(db_dir / 'calorie_data.db'))


def _run(db_dir, script, *args, photos_dir=None):
    """跑渲染器 CLI(隔离 DB:SKILLS_DB_PATH=独立目录;身材照另加 CALORIE_PHOTOS_DIR)"""
    env = {**os.environ, 'SKILLS_DB_PATH': str(db_dir)}
    if photos_dir is not None:
        env['CALORIE_PHOTOS_DIR'] = str(photos_dir)
    return subprocess.run(
        [sys.executable, script, *args, '--chain', _CHAIN],
        cwd=str(SCRIPTS_DIR), env=env, capture_output=True, text=True,
        encoding='utf-8', timeout=120)


def _html_names(db_dir, prefix):
    html_dir = db_dir / 'calorie_html'
    return sorted(p.name for p in html_dir.glob(f'{prefix}*.html')) if html_dir.exists() else []


def _seed_profile(db_path, height_cm=177.0):
    """写用户档案身高(log_weight 写库前置:无档案返回 None)"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("INSERT INTO user_profile (id, age, gender, height_cm) VALUES (1, 30, 'male', ?)",
              (height_cm,))
    conn.commit()
    conn.close()


def _seed_exercise(db_path, date_str='2026-08-12', type_='跑步', calories=300):
    """直接插一条运动记录,返回 id(记录日期由调用方控制)"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('''INSERT INTO exercise_log (date, time, exercise_type, calories_burned, note)
                 VALUES (?, '07:00:00', ?, ?, '')''', (date_str, type_, calories))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def _seed_plan(db_path, title='8周增肌循环'):
    """插计划 config(1行)+ 1 条训练日程(movements 含 俯卧撑),返回 plans 行 id"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('''INSERT INTO workout_plan_config (id, title, version, description, total_weeks, start_date)
                 VALUES (1, ?, 'v1', '', 8, '2026-08-10')''', (title,))
    c.execute('''INSERT INTO workout_plans (week_number, day_of_week, session_index, session_label,
                 time_start, time_end, is_rest_day, total_sets, movements)
                 VALUES (1, 1, 1, '训练', '18:00', '19:00', 0, 1,
                 '[{"name": "俯卧撑", "sets": [{"reps": 10, "weight": 0}]}]')''')
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def _seed_body_photo(db_path, date_str='2026-08-12', photo_path='/tmp/body.png', tag='正面'):
    """插一条身材照记录(photo_path 指向真实存在的文件,删照会 embed 读文件),返回 id"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('''INSERT INTO body_photos (date, time, photo_path, tag, note)
                 VALUES (?, '08:00:00', ?, ?, '')''', (date_str, str(photo_path), tag))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def _seed_body_composition(db_path, date_str='2026-08-12'):
    """插一条体脂记录,返回 id"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute('''INSERT INTO body_composition
                 (date, source, caliper_chest_mm, caliper_abdominal_mm, caliper_thigh_mm,
                  caliper_tricep_mm, caliper_subscapular_mm, caliper_suprailiac_mm,
                  caliper_midaxillary_mm, body_fat_pct, note)
                 VALUES (?, 'home_caliper', 10, 15, 12, 8, 10, 9, 8, 15.5, '')''', (date_str,))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def _seed_body_measurements(db_path, date_str='2026-08-12'):
    """插一条围度记录,返回 id"""
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("INSERT INTO body_measurements (date, chest_cm, note) VALUES (?, 90.5, '')",
              (date_str,))
    conn.commit()
    rid = c.lastrowid
    conn.close()
    return rid


def _write_plan_json(tmp_path, title='8周增肌循环'):
    """最小合法计划(weeks 非空 + movements 空,避开动作库/器材校验),返回文件路径"""
    plan = {
        'config': {'title': title, 'total_weeks': 1, 'start_date': '2026-08-10'},
        'weeks': [{'week_number': 1,
                   'days': [{'day_of_week': 1,
                             'sessions': [{'session_label': '训练', 'time_start': '18:00',
                                           'time_end': '19:00', 'is_rest_day': False,
                                           'total_sets': 0, 'movements': []}]}]}],
    }
    p = tmp_path / 'plan.json'
    p.write_text(json.dumps(plan, ensure_ascii=False), encoding='utf-8')
    return p


# ═══════════════════ 运动(render_exercise_receipt.py · 11 场景) ═══════════════════

def test_e2e_exercise_add_filename_type(tmp_path):
    """记运动 → 记运动_回执_跑步_<TS>.html(运动名)"""
    db_dir, _ = _make_db(tmp_path)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-add', '--type', '跑步', '--calories', '300')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '记运动_回执_')
    assert any('_跑步_' in n for n in names), names


def test_e2e_exercise_add_strength_filename_type(tmp_path):
    """记力量训练 → 记力量训练_回执_卧推_<TS>.html(动作名)"""
    db_dir, _ = _make_db(tmp_path)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-add-strength',
               '--type', '卧推', '--sets', '3', '--load', '50', '--reps', '10')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '记力量训练_回执_')
    assert any('_卧推_' in n for n in names), names


def test_e2e_exercise_add_daily_filename_type(tmp_path):
    """记日常活动 → 记日常活动_回执_散步_<TS>.html(类型)"""
    db_dir, _ = _make_db(tmp_path)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-add-daily',
               '--type', '散步', '--minutes', '30')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '记日常活动_回执_')
    assert any('_散步_' in n for n in names), names


def test_e2e_exercise_backfill_filename_type(tmp_path):
    """补记运动 → 补记运动_回执_骑行_<TS>.html(运动名)"""
    db_dir, _ = _make_db(tmp_path)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-backfill',
               '--date', '2026-08-10', '--type', '骑行', '--calories', '200')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '补记运动_回执_')
    assert any('_骑行_' in n for n in names), names


def test_e2e_exercise_batch_add_filename_first_type(tmp_path):
    """批量补记运动 → 批量补记运动_回执_跑步等2项_<TS>.html(首类型+等N项)"""
    db_dir, _ = _make_db(tmp_path)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-batch-add',
               '--items', '2026-08-10 跑步 300;2026-08-11 游泳 400')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '批量补记运动_回执_')
    assert any('_跑步等2项_' in n for n in names), names


def test_e2e_exercise_copy_filename_source_date(tmp_path):
    """复制昨日运动 → 复制昨日运动_回执_<昨日YYYYMMDD>_<TS>.html(源日期)"""
    db_dir, db_path = _make_db(tmp_path)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _seed_exercise(db_path, date_str=yesterday, type_='跑步', calories=300)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-copy')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '复制昨日运动_回执_')
    assert any(yesterday.replace('-', '') in n for n in names), names


def test_e2e_exercise_update_filename_renamed(tmp_path):
    """改运动记录改名 → 改运动记录_回执_游泳_<TS>.html(改后运动名)"""
    db_dir, db_path = _make_db(tmp_path)
    eid = _seed_exercise(db_path, type_='跑步', calories=300)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-update', '--id', str(eid),
               '--field', 'exercise_type', '--value', '游泳')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改运动记录_回执_')
    assert any('_游泳_' in n for n in names), names


def test_e2e_exercise_update_day_filename_date(tmp_path):
    """改某日运动 → 改某日运动_回执_20260812_<TS>.html(目标日期)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_exercise(db_path, date_str='2026-08-12', type_='跑步', calories=300)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-update-day',
               '--date', '2026-08-12', '--field', 'note', '--value', '改备注')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改某日运动_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_exercise_delete_filename_type(tmp_path):
    """删运动记录 → 删运动记录_回执_跑步_<TS>.html(被删运动名)"""
    db_dir, db_path = _make_db(tmp_path)
    eid = _seed_exercise(db_path, type_='跑步', calories=300)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-delete', '--id', str(eid))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删运动记录_回执_')
    assert any('_跑步_' in n for n in names), names


def test_e2e_exercise_delete_day_filename_date(tmp_path):
    """删某日运动 → 删某日运动_回执_20260812_<TS>.html(目标日期)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_exercise(db_path, date_str='2026-08-12', type_='跑步', calories=300)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-delete-day', '--date', '2026-08-12')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删某日运动_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_exercise_delete_range_filename_span(tmp_path):
    """批量删运动 → 批量删运动_回执_20260809至20260812_<TS>.html(起止范围)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_exercise(db_path, date_str='2026-08-09', type_='跑步', calories=300)
    _seed_exercise(db_path, date_str='2026-08-12', type_='游泳', calories=400)
    res = _run(db_dir, 'render_exercise_receipt.py', '--live-delete-range',
               '--from', '2026-08-09', '--to', '2026-08-12')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '批量删运动_回执_')
    assert any('_20260809至20260812_' in n for n in names), names


# ═══════════════════ 体重(render_weight_receipt.py · 2 场景) ═══════════════════

def test_e2e_weight_add_filename_kg(tmp_path):
    """记体重 → 记体重_回执_70.5kg_<TS>.html(体重值,format 'g' 去尾零)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_profile(db_path)
    res = _run(db_dir, 'render_weight_receipt.py', '--live', '--kg', '70.5')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '记体重_回执_')
    assert any('_70.5kg_' in n for n in names), names


def test_e2e_weight_batch_filename_first_kg(tmp_path):
    """批量补录体重 → 批量补录体重_回执_70kg等2项_<TS>.html(首条+等N项)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_profile(db_path)
    items = tmp_path / 'items.jsonl'
    items.write_text('{"date": "2026-08-10", "kg": 70}\n{"date": "2026-08-11", "kg": 70.5}\n',
                     encoding='utf-8')
    res = _run(db_dir, 'render_weight_receipt.py', '--live-batch', '--input', str(items))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '批量补录体重_回执_')
    assert any('_70kg等2项_' in n for n in names), names


# ═══════════════════ 计划(render_plan_receipt.py · 12 场景) ═══════════════════

def test_e2e_plan_set_filename_title(tmp_path):
    """定训练计划 → 定训练计划_回执_8周增肌循环_<TS>.html(计划名)"""
    db_dir, _ = _make_db(tmp_path)
    pj = _write_plan_json(tmp_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-set', '--plan-json', pj.read_text(encoding='utf-8'))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '定训练计划_回执_')
    assert any('_8周增肌循环_' in n for n in names), names


def test_e2e_plan_copy_filename_title(tmp_path):
    """复制训练计划 → 复制训练计划_回执_<新标题>_<TS>.html(计划名)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_plan(db_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-copy', '--new-title', '8周增肌循环v2')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '复制训练计划_回执_')
    assert any('_8周增肌循环v2_' in n for n in names), names


def test_e2e_plan_rest_filename_week_day(tmp_path):
    """定休息日 → 定休息日_回执_第1周周1_<TS>.html(周次+星期)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_plan(db_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-rest', '--week', '1', '--day', '1')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '定休息日_回执_')
    assert any('_第1周周1_' in n for n in names), names


def test_e2e_plan_add_filename_name(tmp_path):
    """加训练动作 → 加训练动作_回执_深蹲_<TS>.html(动作名)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_plan(db_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-add',
               '--week', '1', '--day', '1', '--name', '深蹲', '--sets', '3')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '加训练动作_回执_')
    assert any('_深蹲_' in n for n in names), names


def test_e2e_plan_set_week_filename_week(tmp_path):
    """定一周计划 → 定一周计划_回执_第2周_<TS>.html(周次)"""
    db_dir, _ = _make_db(tmp_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-set-week',
               '--week', '2', '--days-json', '{"1": [{"label": "训练", "total_sets": 1}]}')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '定一周计划_回执_')
    assert any('_第2周_' in n for n in names), names


def test_e2e_plan_update_filename_title(tmp_path):
    """改训练计划 → 改训练计划_回执_<新标题>_<TS>.html(计划名)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_plan(db_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-update',
               '--field', 'title', '--value', '10周增肌循环')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改训练计划_回执_')
    assert any('_10周增肌循环_' in n for n in names), names


def test_e2e_plan_update_day_filename_week_day(tmp_path):
    """改某天训练 → 改某天训练_回执_第1周周1_<TS>.html(周次+星期)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_plan(db_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-update-day',
               '--week', '1', '--day', '1', '--session', '1', '--label', '晨练')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改某天训练_回执_')
    assert any('_第1周周1_' in n for n in names), names


def test_e2e_plan_delete_day_filename_week_day(tmp_path):
    """删某天训练 → 删某天训练_回执_第1周周1_<TS>.html(周次+星期)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_plan(db_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-delete-day', '--week', '1', '--day', '1')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删某天训练_回执_')
    assert any('_第1周周1_' in n for n in names), names


def test_e2e_plan_update_movement_filename_renamed(tmp_path):
    """改动作 → 改动作_回执_深蹲_<TS>.html(改后动作名,对齐 #284 Q2A)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_plan(db_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-update-movement',
               '--week', '1', '--day', '1', '--session', '1',
               '--old-name', '俯卧撑', '--new-name', '深蹲')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改动作_回执_')
    assert any('_深蹲_' in n for n in names), names


def test_e2e_plan_delete_filename_title(tmp_path):
    """撤销训练计划 → 撤销训练计划_回执_8周增肌循环_<TS>.html(计划名)"""
    db_dir, db_path = _make_db(tmp_path)
    _seed_plan(db_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-delete')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '撤销训练计划_回执_')
    assert any('_8周增肌循环_' in n for n in names), names


def test_e2e_plan_sync_filename_date(tmp_path):
    """同步到训记 → 同步到训记_回执_20260812_<TS>.html(推送日期)"""
    db_dir, _ = _make_db(tmp_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-sync', '--date', '2026-08-12')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '同步到训记_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_plan_backfill_filename_date(tmp_path):
    """拉训记实绩 → 拉训记实绩_回执_20260812_<TS>.html(回写日期)"""
    db_dir, _ = _make_db(tmp_path)
    res = _run(db_dir, 'render_plan_receipt.py', '--live-plan-backfill', '--date', '2026-08-12')
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '拉训记实绩_回执_')
    assert any('_20260812_' in n for n in names), names


# ═══════════════════ 身材照(render_body_photo_receipt.py · 5 场景) ═══════════════════

def _photo_env(tmp_path):
    """造照片目录 + 1x1 png,返回 (photos_dir, png_path)"""
    photos_dir = tmp_path / 'photos'
    photos_dir.mkdir()
    png = photos_dir / 'body.png'
    png.write_bytes(_PNG)
    return photos_dir, png


def test_e2e_body_photo_add_filename_tag(tmp_path):
    """存一张照片 → 存一张照片_回执_正面_<TS>.html(标签)"""
    db_dir, _ = _make_db(tmp_path)
    photos_dir, png = _photo_env(tmp_path)
    res = _run(db_dir, 'render_body_photo_receipt.py', '--live-add', str(png), '--tag', '正面',
               photos_dir=photos_dir)
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '存一张照片_回执_')
    assert any('_正面_' in n for n in names), names


def test_e2e_body_photo_batch_add_filename_first_tag(tmp_path):
    """批量存照片 → 批量存照片_回执_正面等2项_<TS>.html(首标签+等N项)"""
    db_dir, _ = _make_db(tmp_path)
    photos_dir, png = _photo_env(tmp_path)
    png2 = photos_dir / 'body2.png'
    png2.write_bytes(_PNG)
    res = _run(db_dir, 'render_body_photo_receipt.py', '--live-add', str(png), str(png2),
               '--tag', '正面', photos_dir=photos_dir)
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '批量存照片_回执_')
    assert any('_正面等2项_' in n for n in names), names


def test_e2e_body_photo_delete_filename_date(tmp_path):
    """删身材照 → 删身材照_回执_20260812_<TS>.html(照片日期)"""
    db_dir, db_path = _make_db(tmp_path)
    photos_dir, png = _photo_env(tmp_path)
    pid = _seed_body_photo(db_path, date_str='2026-08-12', photo_path=png)
    res = _run(db_dir, 'render_body_photo_receipt.py', '--live-delete', '--id', str(pid),
               photos_dir=photos_dir)
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删身材照_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_body_photo_tag_set_filename_after(tmp_path):
    """改照片标签 → 改照片标签_回执_正面、侧面_<TS>.html(改后全标签)"""
    db_dir, db_path = _make_db(tmp_path)
    photos_dir, png = _photo_env(tmp_path)
    pid = _seed_body_photo(db_path, date_str='2026-08-12', photo_path=png, tag='正面')
    res = _run(db_dir, 'render_body_photo_receipt.py', '--live-tag-set',
               '--id', str(pid), '--tag-list', '正面,侧面', photos_dir=photos_dir)
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '改照片标签_回执_')
    assert any('_正面、侧面_' in n for n in names), names


def test_e2e_body_photo_tag_add_filename_added(tmp_path):
    """加照片标签 → 加照片标签_回执_背部_<TS>.html(实际新增标签)"""
    db_dir, db_path = _make_db(tmp_path)
    photos_dir, png = _photo_env(tmp_path)
    pid = _seed_body_photo(db_path, date_str='2026-08-12', photo_path=png, tag='正面')
    res = _run(db_dir, 'render_body_photo_receipt.py', '--live-tag-add',
               '--id', str(pid), '--tag', '背部', photos_dir=photos_dir)
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '加照片标签_回执_')
    assert any('_背部_' in n for n in names), names


def test_e2e_body_photo_tag_remove_filename_removed(tmp_path):
    """删照片标签 → 删照片标签_回执_正面_<TS>.html(实际移除标签)"""
    db_dir, db_path = _make_db(tmp_path)
    photos_dir, png = _photo_env(tmp_path)
    pid = _seed_body_photo(db_path, date_str='2026-08-12', photo_path=png, tag='正面,背部')
    res = _run(db_dir, 'render_body_photo_receipt.py', '--live-tag-remove',
               '--id', str(pid), '--tag', '正面', photos_dir=photos_dir)
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删照片标签_回执_')
    assert any('_正面_' in n for n in names), names


# ═══════════════════ 删体脂/删围度(render_body_delete_receipt.py · 2 场景) ═══════════════════

def test_e2e_body_delete_composition_filename_date(tmp_path):
    """删体脂 → 删体脂_回执_20260812_<TS>.html(记录日期)"""
    db_dir, db_path = _make_db(tmp_path)
    cid = _seed_body_composition(db_path, date_str='2026-08-12')
    res = _run(db_dir, 'render_body_delete_receipt.py', '--entity', 'composition', '--id', str(cid))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删体脂_回执_')
    assert any('_20260812_' in n for n in names), names


def test_e2e_body_delete_measurements_filename_date(tmp_path):
    """删围度 → 删围度_回执_20260812_<TS>.html(记录日期)"""
    db_dir, db_path = _make_db(tmp_path)
    mid = _seed_body_measurements(db_path, date_str='2026-08-12')
    res = _run(db_dir, 'render_body_delete_receipt.py', '--entity', 'measurements', '--id', str(mid))
    assert res.returncode == 0, res.stderr
    names = _html_names(db_dir, '删围度_回执_')
    assert any('_20260812_' in n for n in names), names
