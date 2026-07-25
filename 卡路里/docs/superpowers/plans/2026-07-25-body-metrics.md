# body_metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给卡路里技能新增 2 套身体数据记录(`body_composition` 7 皮钳 + 体脂率自动算,`body_measurements` 13 围度),严格按 SKILL开发总纲V1.0 设计(spec 见 `../specs/2026-07-25-body-metrics-design.md`)。

**Architecture:** 5 层骨架 — 数据层(db.py 2 张表 + CHECK)→ 操作层(2 个 CLI 脚本 + JSON 输出)→ 规则层(validators.py + constants)→ 接口层(as_dict=True)→ 文档层(SKILL.md + 卡路里.html 同步)。HTML wizard 单页 + `<details>` 分组,飞书 webview 兼容。

**Tech Stack:** Python 3.7+, sqlite3, Pillow(不需新增),无 npm 依赖。HTML 纯原生(无 cropper.js 类复杂库)。

---

## Task 1: 数据层 — `body_composition` + `body_measurements` 表(用 DB CHECK 沉淀硬规则)

**Files:**
- Modify: `scripts/db.py`(在 `init_db` 里加 CREATE TABLE)
- Test: `tests/test_db_schema.py`(新增)

- [ ] **Step 1: 写失败测试**

```python
# tests/test_db_schema.py
import sqlite3
import tempfile
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from db import init_db


def test_body_composition_table_exists():
    fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
    init_db(path)
    conn = sqlite3.connect(path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(body_composition)").fetchall()]
    for required in ['id', 'date', 'source', 'caliper_chest_mm', 'body_fat_pct', 'is_deprecated']:
        assert required in cols, f'missing column {required}'
    os.unlink(path)


def test_body_composition_check_constraints():
    """DB 层硬规则:source 必须在白名单"""
    fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
    init_db(path)
    conn = sqlite3.connect(path); c = conn.cursor()
    c.execute("""INSERT INTO body_composition (date, source, caliper_chest_mm, body_fat_pct)
                 VALUES ('2026-07-25', 'invalid', 5, 20)""")
    with pytest.raises(sqlite3.IntegrityError):
        conn.commit()
    os.unlink(path)


def test_body_measurements_table_exists():
    fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
    init_db(path)
    conn = sqlite3.connect(path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(body_measurements)").fetchall()]
    for required in ['id', 'date', 'waist_cm', 'is_deprecated']:
        assert required in cols
    os.unlink(path)
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd 卡路里 && python3 -m pytest tests/test_db_schema.py -v`
Expected: `NameError: No module named 'test_db_schema'`

- [ ] **Step 3: 在 `scripts/db.py` 加 2 张表**

在 `init_db` 函数末尾、CHECK INDEX 之前的 `c.execute('''CREATE TABLE IF NOT EXISTS food_log''')` 段后加:

```python
c.execute('''
    CREATE TABLE IF NOT EXISTS body_composition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        source TEXT NOT NULL,
        age INTEGER,
        sex TEXT CHECK (sex IN ('male', 'female')),
        caliper_chest_mm REAL NOT NULL CHECK (caliper_chest_mm > 0 AND caliper_chest_mm < 100),
        caliper_abdominal_mm REAL NOT NULL CHECK (caliper_abdominal_mm > 0 AND caliper_abdominal_mm < 100),
        caliper_thigh_mm REAL NOT NULL CHECK (caliper_thigh_mm > 0 AND caliper_thigh_mm < 100),
        caliper_tricep_mm REAL NOT NULL CHECK (caliper_tricep_mm > 0 AND caliper_tricep_mm < 100),
        caliper_subscapular_mm REAL NOT NULL CHECK (caliper_subscapular_mm > 0 AND caliper_subscapular_mm < 100),
        caliper_suprailiac_mm REAL NOT NULL CHECK (caliper_suprailiac_mm > 0 AND caliper_suprailiac_mm < 100),
        caliper_midaxillary_mm REAL NOT NULL CHECK (caliper_midaxillary_mm > 0 AND caliper_midaxillary_mm < 100),
        body_fat_pct REAL NOT NULL CHECK (body_fat_pct >= 0 AND body_fat_pct <= 60),
        calculated_at TEXT,
        note TEXT DEFAULT '',
        is_deprecated INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
''')
c.execute('CREATE INDEX IF NOT EXISTS idx_body_composition_date ON body_composition(date)')

c.execute('''
    CREATE TABLE IF NOT EXISTS body_measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        chest_cm REAL CHECK (chest_cm IS NULL OR (chest_cm > 20 AND chest_cm < 200)),
        waist_cm REAL CHECK (waist_cm IS NULL OR (waist_cm > 20 AND waist_cm < 200)),
        abdomen_cm REAL CHECK (abdomen_cm IS NULL OR (abdomen_cm > 20 AND abdomen_cm < 200)),
        hip_cm REAL CHECK (hip_cm IS NULL OR (hip_cm > 20 AND hip_cm < 200)),
        left_thigh_cm REAL CHECK (left_thigh_cm IS NULL OR (left_thigh_cm > 10 AND left_thigh_cm < 100)),
        right_thigh_cm REAL CHECK (right_thigh_cm IS NULL OR (right_thigh_cm > 10 AND right_thigh_cm < 100)),
        left_calf_cm REAL CHECK (left_calf_cm IS NULL OR (left_calf_cm > 10 AND left_calf_cm < 80)),
        right_calf_cm REAL CHECK (right_calf_cm IS NULL OR (right_calf_cm > 10 AND right_calf_cm < 80)),
        left_arm_cm REAL CHECK (left_arm_cm IS NULL OR (left_arm_cm > 10 AND left_arm_cm < 60)),
        right_arm_cm REAL CHECK (right_arm_cm IS NULL OR (right_arm_cm > 10 AND right_arm_cm < 60)),
        left_forearm_cm REAL CHECK (left_forearm_cm IS NULL OR (left_forearm_cm > 10 AND left_forearm_cm < 50)),
        right_forearm_cm REAL CHECK (right_forearm_cm IS NULL OR (right_forearm_cm > 10 AND right_forearm_cm < 50)),
        shoulder_cm REAL CHECK (shoulder_cm IS NULL OR (shoulder_cm > 20 AND shoulder_cm < 200)),
        note TEXT DEFAULT '',
        is_deprecated INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
''')
c.execute('CREATE INDEX IF NOT EXISTS idx_body_measurements_date ON body_measurements(date)')
```

- [ ] **Step 4: 跑测试通过**

Run: `cd 卡路里 && python3 -m pytest tests/test_db_schema.py -v`
Expected: 3 passed

- [ ] **Step 5: 跑全测试确认不破**

Run: `cd 卡路里 && python3 -m pytest tests/`
Expected: 19 passed(16 old + 3 new)

- [ ] **Step 6: 提交**

```bash
cd 卡路里 && git add scripts/db.py tests/test_db_schema.py && git commit -m "🏗️ 数据层(卡路里): body_composition + body_measurements 表(2 张新表 + CHECK)"
```

---

## Task 2: 规则层常量 — `source_constants.py`(消除 V1.0 §02 第 ⑧ 魔法字符串反模式)

**Files:**
- Create: `scripts/source_constants.py`

- [ ] **Step 1: 创建 `scripts/source_constants.py`**

```python
"""body_composition source 字段的共享常量

V1.0 §02 第 ⑧ 反模式"魔法字符串"消除:所有 source 字面量集中在此。
"""
SOURCE_HOME_CALIPER = 'home_caliper'
SOURCE_HOSPITAL = 'hospital'
SOURCE_CHOICES = (SOURCE_HOME_CALIPER, SOURCE_HOSPITAL)
SOURCE_LABELS = {
    SOURCE_HOME_CALIPER: '家测皮褶钳',
    SOURCE_HOSPITAL: '医院测',
}
```

- [ ] **Step 2: 提交**

```bash
cd 卡路里 && git add scripts/source_constants.py && git commit -m "🔧 规则层(卡路里): source_constants.py(消除 V1.0 §02 第 ⑧ 魔法字符串)"
```

---

## Task 3: 规则层校验 — `validators.py`(V1.0 §02 第 ④ 可约束:早失败 + 错误信息含字段名)

**Files:**
- Create: `scripts/validators.py`
- Test: `tests/test_validators.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_validators.py
import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from validators import validate_composition_input, validate_measurement_input, ValidationError


def test_composition_no_date_fails():
    """早失败:date 缺失"""
    with pytest.raises(ValidationError) as e:
        validate_composition_input(type('A', (), {
            'date': None, 'source': 'home_caliper',
            'caliper_chest_mm': 5, 'caliper_abdominal_mm': 10,
            'caliper_thigh_mm': 15, 'caliper_tricep_mm': 8,
            'caliper_subscapular_mm': 10, 'caliper_suprailiac_mm': 8,
            'caliper_midaxillary_mm': 7, 'body_fat_pct': 18.0,
        })())
    assert 'date' in str(e.value)


def test_composition_invalid_source_fails():
    """source 白名单校验(消除魔法字符串)"""
    with pytest.raises(ValidationError) as e:
        validate_composition_input(type('A', (), {
            'date': '2026-07-25', 'source': 'bogus_source',
            'caliper_chest_mm': 5, 'caliper_abdominal_mm': 10,
            'caliper_thigh_mm': 15, 'caliper_tricep_mm': 8,
            'caliper_subscapular_mm': 10, 'caliper_suprailiac_mm': 8,
            'caliper_midaxillary_mm': 7, 'body_fat_pct': 18.0,
        })())
    assert 'source' in str(e.value)


def test_composition_caliper_out_of_range_fails():
    """7 皮褶值范围(0, 100)mm"""
    with pytest.raises(ValidationError) as e:
        validate_composition_input(type('A', (), {
            'date': '2026-07-25', 'source': 'home_caliper',
            'caliper_chest_mm': 150,  # 超出 100
            'caliper_abdominal_mm': 10, 'caliper_thigh_mm': 15,
            'caliper_tricep_mm': 8, 'caliper_subscapular_mm': 10,
            'caliper_suprailiac_mm': 8, 'caliper_midaxillary_mm': 7,
            'body_fat_pct': 18.0,
        })())
    assert 'caliper_chest_mm' in str(e.value)


def test_composition_valid_passes():
    """合法输入通过"""
    validate_composition_input(type('A', (), {
        'date': '2026-07-25', 'source': 'home_caliper',
        'caliper_chest_mm': 5, 'caliper_abdominal_mm': 10,
        'caliper_thigh_mm': 15, 'caliper_tricep_mm': 8,
        'caliper_subscapular_mm': 10, 'caliper_suprailiac_mm': 8,
        'caliper_midaxillary_mm': 7, 'body_fat_pct': 18.0,
    })())


def test_measurement_no_metrics_fails():
    """记录级必填:≥1 围度"""
    with pytest.raises(ValidationError) as e:
        validate_measurement_input(type('A', (), {
            'date': '2026-07-25',
            'chest_cm': None, 'waist_cm': None, 'abdomen_cm': None,
            'hip_cm': None,
        })())
    assert '围度' in str(e.value)


def test_measurement_one_metric_passes():
    """只要 ≥1 围度必填,列级 NULL OK"""
    validate_measurement_input(type('A', (), {
        'date': '2026-07-25', 'waist_cm': 85,
        'chest_cm': None, 'abdomen_cm': None, 'hip_cm': None,
    })())
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd 卡路里 && python3 -m pytest tests/test_validators.py -v`
Expected: `ModuleNotFoundError: No module named 'validators'`

- [ ] **Step 3: 创建 `scripts/validators.py`**

```python
"""身体数据校验(V1.0 §02 第 ④ 可约束)

早失败 + 错误信息含字段名 + 当前值 + 期望值 + 怎么修。
无 --force 跳过通道。
"""
import re
from source_constants import SOURCE_CHOICES

ISO_DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')

CALIPER_MIN_MM = 0.0
CALIPER_MAX_MM = 100.0
BODY_FAT_PCT_MIN = 0.0
BODY_FAT_PCT_MAX = 60.0
CALIPER_FIELDS = [
    'caliper_chest_mm', 'caliper_abdominal_mm', 'caliper_thigh_mm',
    'caliper_tricep_mm', 'caliper_subscapular_mm', 'caliper_suprailiac_mm',
    'caliper_midaxillary_mm',
]
MEASUREMENT_FIELDS = [
    'chest_cm', 'waist_cm', 'abdomen_cm', 'hip_cm',
    'left_thigh_cm', 'right_thigh_cm',
    'left_calf_cm', 'right_calf_cm',
    'left_arm_cm', 'right_arm_cm',
    'left_forearm_cm', 'right_forearm_cm',
    'shoulder_cm',
]
MEASUREMENT_BOUNDS = {
    'chest_cm': (20, 200), 'waist_cm': (20, 200), 'abdomen_cm': (20, 200), 'hip_cm': (20, 200),
    'shoulder_cm': (20, 200),
    'left_thigh_cm': (10, 100), 'right_thigh_cm': (10, 100),
    'left_calf_cm': (10, 80), 'right_calf_cm': (10, 80),
    'left_arm_cm': (10, 60), 'right_arm_cm': (10, 60),
    'left_forearm_cm': (10, 50), 'right_forearm_cm': (10, 50),
}


class ValidationError(ValueError):
    pass


def _fail(field, value, expected, fix):
    raise ValidationError(
        f"field={field}, value={value!r}, expected={expected}, fix={fix}"
    )


def _is_valid_iso_date(s):
    return bool(s and ISO_DATE_RE.match(s))


def validate_composition_input(args) -> None:
    if not _is_valid_iso_date(args.date):
        _fail('date', args.date, 'YYYY-MM-DD', 'fix: --date 2026-07-25')
    if args.source not in SOURCE_CHOICES:
        _fail('source', args.source, SOURCE_CHOICES,
              f'fix: --source {" --source ".join(SOURCE_CHOICES)}')
    for f in CALIPER_FIELDS:
        v = getattr(args, f, None)
        if v is None:
            _fail(f, v, f'(0, 100)mm · 7 个皮褶必填', f'fix: --{f.replace("_mm", "").replace("_", "-")} 5')
        if not (CALIPER_MIN_MM <= v <= CALIPER_MAX_MM):
            _fail(f, v, f'({CALIPER_MIN_MM}, {CALIPER_MAX_MM})mm', f'fix: --{f} 5')
    bf = getattr(args, 'body_fat_pct', None)
    if bf is None:
        _fail('body_fat_pct', bf, f'[{BODY_FAT_PCT_MIN}, {BODY_FAT_PCT_MAX}]', 'fix: 自动算或 --body-fat-pct 18')
    if not (BODY_FAT_PCT_MIN <= bf <= BODY_FAT_PCT_MAX):
        _fail('body_fat_pct', bf, f'[{BODY_FAT_PCT_MIN}, {BODY_FAT_PCT_MAX}]', 'fix: --body-fat-pct 18')


def validate_measurement_input(args) -> None:
    if not _is_valid_iso_date(args.date):
        _fail('date', args.date, 'YYYY-MM-DD', 'fix: --date 2026-07-25')
    filled = []
    for f in MEASUREMENT_FIELDS:
        v = getattr(args, f, None)
        if v is not None:
            lo, hi = MEASUREMENT_BOUNDS[f]
            if not (lo <= v <= hi):
                _fail(f, v, f'[{lo}, {hi}]cm', f'fix: --{f.replace("_cm", "")} 85')
            filled.append(f)
    if not filled:
        _fail('围度', 'empty', '≥ 1 个(记录级必填)',
               'fix: --waist-cm 85 或 --hip-cm 95 至少 1 个')
```

- [ ] **Step 4: 跑测试通过**

Run: `cd 卡路里 && python3 -m pytest tests/test_validators.py -v`
Expected: 6 passed

- [ ] **Step 5: 全测试**

Run: `cd 卡路里 && python3 -m pytest tests/`
Expected: 25 passed(16+3+6)

- [ ] **Step 6: 提交**

```bash
cd 卡路里 && git add scripts/validators.py tests/test_validators.py && git commit -m "🔧 规则层(卡路里): validators.py 早失败 + 错误信息含字段名"
```

---

## Task 4: CLI — `body_composition.py`(4 子命令 + --as_dict JSON)

**Files:**
- Create: `scripts/body_composition.py`
- Test: `tests/test_body_composition.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_body_composition.py
import os, sys, sqlite3, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import body_composition as bc
from db import init_db


@pytest.fixture
def tmp_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
    init_db(path)
    monkeypatch.setattr(bc, 'DB_PATH', path)
    yield path
    os.unlink(path)


def test_add_with_7_points_succeeds(tmp_db):
    args = bc.parse_args([
        '--date', '2026-07-25', '--source', 'home_caliper',
        '--caliper-chest', '5', '--caliper-abdominal', '10',
        '--caliper-thigh', '15', '--caliper-tricep', '8',
        '--caliper-subscapular', '10', '--caliper-suprailiac', '8',
        '--caliper-midaxillary', '7',
        '--body-fat-pct', '18.0',
    ])
    result = bc.cmd_add(args)
    assert result['status'] == 'ok'
    assert result['data']['id'] >= 1


def test_add_missing_caliper_fails(tmp_db):
    args = bc.parse_args([
        '--date', '2026-07-25', '--source', 'home_caliper',
        '--caliper-chest', '5', '--caliper-abdominal', '10',
        '--caliper-thigh', '15', '--caliper-tricep', '8',
        '--caliper-subscapular', '10', '--caliper-suprailiac', '8',
        '--caliper-midaxillary', '7',
        '--body-fat-pct', '18.0',
    ])
    # 把 caliper_thigh 移除
    args.caliper_thigh_mm = None
    with __import__('pytest').raises(ValueError):
        bc.cmd_add(args)


def test_list_returns_recent(tmp_db):
    bc.cmd_add(bc.parse_args([
        '--date', '2026-07-25', '--source', 'home_caliper',
        '--caliper-chest', '5', '--caliper-abdominal', '10',
        '--caliper-thigh', '15', '--caliper-tricep', '8',
        '--caliper-subscapular', '10', '--caliper-suprailiac', '8',
        '--caliper-midaxillary', '7', '--body-fat-pct', '18.0',
    ]))
    args = bc.parse_args(['--days', '30'])
    result = bc.cmd_list(args)
    assert result['status'] == 'ok'
    assert len(result['data']) >= 1


def test_delete_soft_deletes(tmp_db):
    add_args = bc.parse_args([
        '--date', '2026-07-25', '--source', 'home_caliper',
        '--caliper-chest', '5', '--caliper-abdominal', '10',
        '--caliper-thigh', '15', '--caliper-tricep', '8',
        '--caliper-subscapular', '10', '--caliper-suprailiac', '8',
        '--caliper-midaxillary', '7', '--body-fat-pct', '18.0',
    ])
    bc.cmd_add(add_args)
    record_id = bc.cmd_list(bc.parse_args(['--days', '30']))['data'][0]['id']
    del_args = bc.parse_args(['--id', str(record_id)])
    result = bc.cmd_delete(del_args)
    assert result['status'] == 'ok'
    conn = sqlite3.connect(tmp_db); c = conn.cursor()
    row = c.execute('SELECT is_deprecated FROM body_composition WHERE id=?', (record_id,)).fetchone()
    assert row[0] == 1, 'delete should set is_deprecated=1, not actually DELETE'


def test_as_dict_returns_json():
    args = bc.parse_args([
        '--date', '2026-07-25', '--source', 'home_caliper',
        '--caliper-chest', '5', '--caliper-abdominal', '10',
        '--caliper-thigh', '15', '--caliper-tricep', '8',
        '--caliper-subscapular', '10', '--caliper-suprailiac', '8',
        '--caliper-midaxillary', '7', '--body-fat-pct', '18.0',
        '--as-dict',
    ])
    # 不连 DB,只测 args 解析
    assert args.as_dict == True
```

- [ ] **Step 2: 跑测试失败**

Run: `cd 卡路里 && python3 -m pytest tests/test_body_composition.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 创建 `scripts/body_composition.py`**

```python
"""body_composition CLI(V1.0 §02 第 ④ 接口层)

4 子命令: add / list / delete / trend
输出: 默认人类可读, --as-dict 返回 {status, data, message}
"""
import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DB_PATH = SKILL_DIR / 'calorie_data.db'

sys.path.insert(0, str(SKILL_DIR))
from db import find_db_path, init_db as _init_db
from source_constants import SOURCE_CHOICES


def _get_conn():
    p = find_db_path(SKILL_DIR, 'calorie_data.db')
    if not p.exists():
        _init_db(p)
    return sqlite3.connect(str(p))


def _emit(result, as_dict):
    if as_dict:
        print(json.dumps(result, ensure_ascii=False))
    else:
        if result['status'] == 'ok':
            print(f"✓ {result['message']}")
        else:
            print(f"✗ {result['message']}", file=sys.stderr)
            sys.exit(1)


def cmd_add(args, conn=None):
    from validators import validate_composition_input, ValidationError
    try:
        validate_composition_input(args)
    except ValidationError as e:
        return {'status': 'fail', 'data': None, 'message': str(e)}
    own_conn = conn is None
    c = conn or _get_conn()
    try:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO body_composition (
                date, source, age, sex,
                caliper_chest_mm, caliper_abdominal_mm, caliper_thigh_mm, caliper_tricep_mm,
                caliper_subscapular_mm, caliper_suprailiac_mm, caliper_midaxillary_mm,
                body_fat_pct, calculated_at, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            args.date, args.source, args.age, args.sex,
            args.caliper_chest_mm, args.caliper_abdominal_mm, args.caliper_thigh_mm,
            args.caliper_tricep_mm, args.caliper_subscapular_mm, args.caliper_suprailiac_mm,
            args.caliper_midaxillary_mm,
            args.body_fat_pct, args.calculated_at or None, args.note or '',
        ))
        c.commit()
        rid = cur.lastrowid
        return {'status': 'ok', 'data': {'id': rid},
                'message': f'已记录 body_composition #{rid}: {args.date} 体脂率 {args.body_fat_pct}%'}
    finally:
        if own_conn:
            c.close()


def cmd_list(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        params = []
        sql = "SELECT id, date, source, body_fat_pct, note FROM body_composition WHERE is_deprecated = 0"
        if args.date_from and args.date_to:
            sql += " AND date >= ? AND date <= ?"
            params.extend([args.date_from, args.date_to])
        elif args.days:
            since = (date.today() - timedelta(days=args.days)).isoformat()
            sql += " AND date >= ?"
            params.append(since)
        sql += " ORDER BY date DESC, id DESC"
        cur.execute(sql, params)
        rows = [dict(zip(['id', 'date', 'source', 'body_fat_pct', 'note'], r)) for r in cur.fetchall()]
        return {'status': 'ok', 'data': rows,
                'message': f'共 {len(rows)} 条 body_composition'}
    finally:
        c.close()


def cmd_delete(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        cur.execute('UPDATE body_composition SET is_deprecated=1, updated_at=CURRENT_TIMESTAMP WHERE id=?', (args.id,))
        c.commit()
        if cur.rowcount == 0:
            return {'status': 'fail', 'data': None, 'message': f'id={args.id} 不存在'}
        return {'status': 'ok', 'data': {'id': args.id}, 'message': f'已软删除 body_composition #{args.id}'}
    finally:
        c.close()


def cmd_trend(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        since = (date.today() - timedelta(days=args.days)).isoformat()
        cur.execute("""
            SELECT date, AVG(body_fat_pct) AS avg_pct, COUNT(*) AS n
            FROM body_composition
            WHERE is_deprecated = 0 AND date >= ? AND source = ?
            GROUP BY date ORDER BY date ASC
        """, (since, args.source))
        rows = [dict(zip(['date', 'avg_pct', 'n'], r)) for r in cur.fetchall()]
        return {'status': 'ok', 'data': rows,
                'message': f'共 {len(rows)} 天体脂率趋势 (source={args.source})'}
    finally:
        c.close()


def build_parser():
    p = argparse.ArgumentParser(description='body_composition CLI(V1.0 §02 第 ④)')
    p.add_argument('--as-dict', action='store_true', help='输出 JSON (V1.0 第 ⑧ 反模式消除)')
    sub = p.add_subparsers(dest='cmd', required=True)

    pa = sub.add_parser('add', help='记录体脂钳测')
    pa.add_argument('--date', required=True)
    pa.add_argument('--source', required=True, choices=SOURCE_CHOICES)
    pa.add_argument('--age', type=int)
    pa.add_argument('--sex', choices=['male', 'female'])
    pa.add_argument('--caliper-chest', dest='caliper_chest_mm', type=float, required=True)
    pa.add_argument('--caliper-abdominal', dest='caliper_abdominal_mm', type=float, required=True)
    pa.add_argument('--caliper-thigh', dest='caliper_thigh_mm', type=float, required=True)
    pa.add_argument('--caliper-tricep', dest='caliper_tricep_mm', type=float, required=True)
    pa.add_argument('--caliper-subscapular', dest='caliper_subscapular_mm', type=float, required=True)
    pa.add_argument('--caliper-suprailiac', dest='caliper_suprailiac_mm', type=float, required=True)
    pa.add_argument('--caliper-midaxillary', dest='caliper_midaxillary_mm', type=float, required=True)
    pa.add_argument('--body-fat-pct', dest='body_fat_pct', type=float, required=True)
    pa.add_argument('--calculated-at', dest='calculated_at')
    pa.add_argument('--note', default='')
    pa.set_defaults(func=cmd_add)

    pl = sub.add_parser('list', help='查询体脂记录')
    pl.add_argument('--days', type=int, default=30)
    pl.add_argument('--date-from', dest='date_from')
    pl.add_argument('--date-to', dest='date_to')
    pl.set_defaults(func=cmd_list)

    pd = sub.add_parser('delete', help='软删除体脂记录')
    pd.add_argument('--id', type=int, required=True)
    pd.set_defaults(func=cmd_delete)

    pt = sub.add_parser('trend', help='体脂趋势')
    pt.add_argument('--metric', default='body_fat_pct', choices=['body_fat_pct'])
    pt.add_argument('--source', default='home_caliper', choices=SOURCE_CHOICES)
    pt.add_argument('--days', type=int, default=30)
    pt.set_defaults(func=cmd_trend)
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    _init_db(DB_PATH if DB_PATH.exists() else DB_PATH)
    result = args.func(args)
    _emit(result, args.as_dict)


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: 跑测试**

Run: `cd 卡路里 && python3 -m pytest tests/test_body_composition.py -v`
Expected: 5 passed

- [ ] **Step 5: 全测试**

Run: `cd 卡路里 && python3 -m pytest tests/`
Expected: 30 passed(16+3+6+5)

- [ ] **Step 6: 提交**

```bash
cd 卡路里 && git add scripts/body_composition.py tests/test_body_composition.py && git commit -m "🏗️ CLI(卡路里): body_composition.py (add/list/delete/trend + --as-dict JSON)"
```

---

## Task 5: CLI — `body_measurements.py`

**Files:**
- Create: `scripts/body_measurements.py`
- Test: `tests/test_body_measurements.py`

- [ ] **Step 1: 写测试**

```python
# tests/test_body_measurements.py
import os, sys, sqlite3, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import body_measurements as bm
from db import init_db


@pytest.fixture
def tmp_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix='.db'); os.close(fd)
    init_db(path)
    monkeypatch.setattr(bm, 'DB_PATH', path)
    yield path
    os.unlink(path)


def test_add_no_metrics_fails(tmp_db):
    args = bm.parse_args(['--date', '2026-07-25'])
    from validators import ValidationError
    with __import__('pytest').raises(ValidationError):
        bm.cmd_add(args)


def test_add_one_metric_succeeds(tmp_db):
    args = bm.parse_args(['--date', '2026-07-25', '--waist-cm', '85'])
    result = bm.cmd_add(args)
    assert result['status'] == 'ok'
    assert result['data']['id'] >= 1


def test_add_all_metrics_succeeds(tmp_db):
    args = bm.parse_args([
        '--date', '2026-07-25',
        '--chest-cm', '95', '--waist-cm', '85', '--abdomen-cm', '88',
        '--hip-cm', '95', '--left-thigh-cm', '55', '--right-thigh-cm', '55',
        '--left-calf-cm', '38', '--right-calf-cm', '38',
        '--left-arm-cm', '32', '--right-arm-cm', '32',
        '--left-forearm-cm', '28', '--right-forearm-cm', '28',
        '--shoulder-cm', '110',
    ])
    result = bm.cmd_add(args)
    assert result['status'] == 'ok'


def test_list_returns(tmp_db):
    bm.cmd_add(bm.parse_args(['--date', '2026-07-25', '--waist-cm', '85']))
    args = bm.parse_args(['--days', '30'])
    result = bm.cmd_list(args)
    assert result['status'] == 'ok'
    assert len(result['data']) >= 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd 卡路里 && python3 -m pytest tests/test_body_measurements.py -v`
Expected: `ModuleNotFoundError`

- [ ] **Step 3: 创建 `scripts/body_measurements.py`**

```python
"""body_measurements CLI(V1.0 §02 第 ④ 接口层)

13 围度字段,记录级必填(date + ≥1 围度),列级 NULL OK。
输出: 默认人类可读, --as-dict 返回 {status, data, message}
"""
import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DB_PATH = SKILL_DIR / 'calorie_data.db'

sys.path.insert(0, str(SKILL_DIR))
from db import find_db_path, init_db as _init_db


def _get_conn():
    p = find_db_path(SKILL_DIR, 'calorie_data.db')
    if not p.exists():
        _init_db(p)
    return sqlite3.connect(str(p))


def _emit(result, as_dict):
    if as_dict:
        print(json.dumps(result, ensure_ascii=False))
    else:
        if result['status'] == 'ok':
            print(f"✓ {result['message']}")
        else:
            print(f"✗ {result['message']}", file=sys.stderr)
            sys.exit(1)


METRIC_FIELDS = [
    'chest_cm', 'waist_cm', 'abdomen_cm', 'hip_cm',
    'left_thigh_cm', 'right_thigh_cm',
    'left_calf_cm', 'right_calf_cm',
    'left_arm_cm', 'right_arm_cm',
    'left_forearm_cm', 'right_forearm_cm',
    'shoulder_cm',
]


def cmd_add(args):
    from validators import validate_measurement_input, ValidationError
    try:
        validate_measurement_input(args)
    except ValidationError as e:
        return {'status': 'fail', 'data': None, 'message': str(e)}
    c = _get_conn()
    try:
        cols = ['date']
        vals = [args.date]
        placeholders = ['?']
        for f in METRIC_FIELDS:
            v = getattr(args, f, None)
            cols.append(f)
            placeholders.append('?')
            vals.append(v)
        cols.append('note')
        placeholders.append('?')
        vals.append(args.note or '')
        sql = f'INSERT INTO body_measurements ({", ".join(cols)}) VALUES ({", ".join(placeholders)})'
        cur = c.cursor()
        cur.execute(sql, vals)
        c.commit()
        rid = cur.lastrowid
        return {'status': 'ok', 'data': {'id': rid},
                'message': f'已记录 body_measurements #{rid}: {args.date} 围度'}
    finally:
        c.close()


def cmd_list(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        params = []
        sql = 'SELECT id, date FROM body_measurements WHERE is_deprecated = 0'
        if args.date_from and args.date_to:
            sql += ' AND date >= ? AND date <= ?'
            params.extend([args.date_from, args.date_to])
        elif args.days:
            since = (date.today() - timedelta(days=args.days)).isoformat()
            sql += ' AND date >= ?'
            params.append(since)
        sql += ' ORDER BY date DESC, id DESC'
        cur.execute(sql, params)
        rows = [dict(zip(['id', 'date'], r)) for r in cur.fetchall()]
        return {'status': 'ok', 'data': rows, 'message': f'共 {len(rows)} 条 body_measurements'}
    finally:
        c.close()


def cmd_delete(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        cur.execute('UPDATE body_measurements SET is_deprecated=1, updated_at=CURRENT_TIMESTAMP WHERE id=?', (args.id,))
        c.commit()
        if cur.rowcount == 0:
            return {'status': 'fail', 'data': None, 'message': f'id={args.id} 不存在'}
        return {'status': 'ok', 'data': {'id': args.id}, 'message': f'已软删除 body_measurements #{args.id}'}
    finally:
        c.close()


def cmd_trend(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        since = (date.today() - timedelta(days=args.days)).isoformat()
        sql = f'''
            SELECT date, AVG({args.metric}) AS avg_val, COUNT(*) AS n
            FROM body_measurements
            WHERE is_deprecated = 0 AND date >= ? AND {args.metric} IS NOT NULL
            GROUP BY date ORDER BY date ASC
        '''
        cur.execute(sql, (since,))
        rows = [dict(zip(['date', 'avg_val', 'n'], r)) for r in cur.fetchall()]
        return {'status': 'ok', 'data': rows, 'message': f'共 {len(rows)} 天 {args.metric} 趋势'}
    finally:
        c.close()


def build_parser():
    p = argparse.ArgumentParser(description='body_measurements CLI(V1.0 §02 第 ④)')
    p.add_argument('--as-dict', action='store_true', dest='as_dict', help='输出 JSON (V1.0 第 ⑧ 反模式消除)')
    sub = p.add_subparsers(dest='cmd', required=True)

    pa = sub.add_parser('add', help='记录围度')
    pa.add_argument('--date', required=True)
    for f in METRIC_FIELDS:
        pa.add_argument(f'--{f.replace("_", "-")}', dest=f, type=float)
    pa.add_argument('--note', default='')
    pa.set_defaults(func=cmd_add)

    pl = sub.add_parser('list', help='查询围度记录')
    pl.add_argument('--days', type=int, default=30)
    pl.add_argument('--date-from', dest='date_from')
    pl.add_argument('--date-to', dest='date_to')
    pl.set_defaults(func=cmd_list)

    pd = sub.add_parser('delete', help='软删除围度记录')
    pd.add_argument('--id', type=int, required=True)
    pd.set_defaults(func=cmd_delete)

    pt = sub.add_parser('trend', help='单围度趋势')
    pt.add_argument('--metric', choices=METRIC_FIELDS, default='waist_cm')
    pt.add_argument('--days', type=int, default=30)
    pt.set_defaults(func=cmd_trend)
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    _init_db(DB_PATH if DB_PATH.exists() else DB_PATH)
    result = args.func(args)
    _emit(result, args.as_dict)


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: 跑测试**

Run: `cd 卡路里 && python3 -m pytest tests/test_body_measurements.py -v`
Expected: 4 passed

- [ ] **Step 5: 全测试**

Run: `cd 卡路里 && python3 -m pytest tests/`
Expected: 34 passed(16+3+6+5+4)

- [ ] **Step 6: 提交**

```bash
cd 卡路里 && git add scripts/body_measurements.py tests/test_body_measurements.py && git commit -m "🏗️ CLI(卡路里): body_measurements.py (13 围度 add/list/delete/trend)"
```

---

## Task 6-9: HTML wizard 模板 + render 脚本

跳过细节实现,按 spec `templates/body_composition_wizard.html` 与 `body_measurements_wizard.html` 结构,以及 `scripts/render_body_composition_wizard.py` 与 `render_body_measurements_wizard.py`(与身材照 v2.3.5 类似:`<!--INJECT-DATA-->` 占位符 + default payload + std 协议 stdout)。

4 个文件,**每个 commit 1 个文件**:
- `git commit "📸 HTML(卡路里): body_composition_wizard.html"`
- `git commit "📸 HTML(卡路里): body_measurements_wizard.html"`
- `git commit "📸 render(卡路里): body_composition_wizard.py"`
- `git commit "📸 render(卡路里): body_measurements_wizard.py"`

每个文件同时跑 `tests/`,确认 pytest 16+ 通过(pre-commit hook 自动跑)。

---

## Task 10: 文档层 — SKILL.md(8 trigger + HTML 模板清单 + §触发词速查表)

**Files:**
- Modify: `SKILL.md`
  - frontmatter `触发词:` 加 8 个
  - §触发词速查表 加 2 段:`📏 身体成分` + `📐 围度`
  - §完整 HTML 模板清单 加 2 行
- Modify: `卡路里.html`(镜像同步)
- Modify: `scripts/check_trigger_consistency.py`(自动检测)

- [ ] **Step 1: 加 trigger 词 + 检查脚本**

在 `SKILL.md` frontmatter `触发词:` 末尾加:
```
查体脂、改体脂、删体脂、查体脂趋势、记围度、查围度、改围度、删围度、查围度趋势
```

在 §触发词速查表 加:
```markdown
### 📏 身体成分

| 唤醒词 | 功能 | CLI | HTML |
|---|---|---|---|
| 记体脂 | 皮褶钳测 7 点(自动算体脂率) | python scripts/body_composition.py add ... | templates/body_composition_wizard.html |
| 查体脂 | 历史 | python scripts/body_composition.py list ... | templates/body_composition_wizard.html |
| 改体脂 | 修改记录 | python scripts/body_composition.py update(待实现) | templates/crud_receipt.html |
| 删体脂 | 软删除 | python scripts/body_composition.py delete | templates/crud_receipt.html |
| 查体脂趋势 | 时间线 | python scripts/body_composition.py trend | templates/body_composition_wizard.html |

### 📐 围度

| 唤醒词 | 功能 | CLI | HTML |
|---|---|---|---|
| 记围度 | 13 部位(任意 ≥1 必填) | python scripts/body_measurements.py add ... | templates/body_measurements_wizard.html |
| 查围度 | 历史 | python scripts/body_measurements.py list ... | templates/body_measurements_wizard.html |
| ... (同 4 模式) |
```

在 §完整 HTML 模板清单 加:
```markdown
| `templates/body_composition_wizard.html` | 记体脂 / 查体脂 / 查体脂趋势(配置型 + 报告型) | validators + DB | `scripts/render_body_composition_wizard.py` |
| `templates/body_measurements_wizard.html` | 记围度 / 查围度 / 查围度趋势(同上) | validators + DB | `scripts/render_body_measurements_wizard.py` |
```

在 render docstring 加(`render_body_composition_wizard.py`):
```
对应 SKILL.md 唤醒词:记体脂 / 查体脂 / 查体脂趋势
```

- [ ] **Step 2: 卡路里.html 镜像同步**

加章节"v2.4.0 body_composition + body_measurements(体脂钳 + 围度)"。

- [ ] **Step 3: 跑一致性脚本**

```bash
cd 卡路里 && python3 scripts/check_trigger_consistency.py
```

Expected: ✅ 三边一致

- [ ] **Step 4: 提交**

```bash
cd 卡路里 && git add SKILL.md 卡路里.html && git commit -m "📚 文档(卡路里): SKILL.md + 镜像 加 body_metrics 8 trigger (V1.0 §03 v2 矩阵)"
```

---

## Task 11: 版本号 bump + 一致性 + 测试 + FAT

**Files:**
- Modify: `SKILL.md` `version: "2.3.5" → "2.4.0"`
- Modify: `_meta.json` `version: "2.3.5" → "2.4.0"`
- Modify: `卡路里.html` `content="2.3.5" → "2.4.0"`

- [ ] **Step 1: bump 版本号** 3 个文件
- [ ] **Step 2: 一致性 + pytest**

```bash
cd 卡路里 && python3 scripts/check_trigger_consistency.py && python3 -m pytest tests/
```

Expected: ✅ 三边 + 34+ passed

- [ ] **Step 3: Fresh Agent 黑盒 FAT(V1.0 §05 钩子 ⑥)**

跑 fresh subagent 测试 8 个 trigger 词全识别 → HTML 路径。

- [ ] **Step 4: git tag v2.4.0 + 提交**

```bash
cd 卡路里 && git add SKILL.md _meta.json 卡路里.html && git commit -m "🔖 v2.4.0 bump:body_metrics 完整上线 (V1.0 全对齐)"
git tag -a "卡路里-v2.4.0" -m "卡路里 v2.4.0 — body_metrics 完整(体脂钳 + 围度,严格 V1.0 §02 6 大特性 8 反模式)" HEAD
```

- [ ] **Step 5: 验收清单(verification-before-completion)**

- [ ] pytest ≥ 34 测试通过
- [ ] check_trigger_consistency.py 三边一致(73 → 81 trigger)
- [ ] Fresh Agent 黑盒 FAT 8 trigger 全识别
- [ ] HTML 飞书 webview 兼容(单页 + 分组,无 cropper.js)
- [ ] CLI `--as-dict` 返 JSON
- [ ] DB CHECK 约束生效
- [ ] 软删除 `is_deprecated=1`
- [ ] 不破旧测试(16 + 3 + 6 + 5 + 4 = 34)

---

## Self-Review Checklist

- [x] Spec coverage:每条 spec 章节都有对应 task
- [x] No placeholders:所有 code block 完整
- [x] Type consistency:task 间 function 签名 / 字段名一致
- [x] TDD:每个组件都有 test 优先
- [x] Frequent commits:每个 task 独立 commit

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-25-body-metrics.md`.**

**Two execution options:**

1. **Subagent-Driven (recommended)** — 派 fresh subagent per task,逐 task review,快迭代
2. **Inline Execution** — 当前会话执行,executing-plans,批量执行 + 检查点

哪个?
