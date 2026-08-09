#!/usr/bin/env python3
"""数据库基础工具 - DB 路径解析、连接、初始化

提供:
- find_db_path(skill_dir, db_filename) — 两层查找数据库路径
- get_db(db_path) — 获取 row_factory=Row 的连接（兼容旧 API）
- connection(db_path) — context manager 风格连接（新代码推荐）
- init_db(db_path) — 初始化所有表 + 迁移
"""

import os
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path

# V1.0 §02 第 ⑧ 反模式"魔法字符串"消除:body_composition.source 用集中常量
sys.path.insert(0, str(Path(__file__).resolve().parent))
from source_constants import SOURCE_HOME_CALIPER, SOURCE_HOSPITAL, SOURCE_GYM, SOURCE_CHOICES


DB_FILENAME = "calorie_data.db"


def _fallback_db_dir():
    """全局 fallback DB 目录(跨机器兼容 · #242 配套)

    - Windows: D:/.db(用户规定,保持不变;无 SKILLS_DB_PATH 时唯一出口)
    - WSL:     /mnt/d/.db(保持现状,D: 盘 automount 场景)
    - macOS/Linux: 用户主目录 ~/.db(XDG 惯例;不再因缺 D 盘/无 /mnt/d 而崩)
    """
    if sys.platform == 'win32':
        return Path('D:/.db')
    d_drive = Path('/mnt/d')
    if d_drive.exists():
        return d_drive / '.db'
    home = Path.home()
    if home:
        return home / '.db'
    raise RuntimeError(
        'SKILLS_DB_PATH 未设置，且无法解析用户主目录。'
        '请设置 SKILLS_DB_PATH 环境变量。'
    )

def find_db_path(skill_dir, db_filename=DB_FILENAME):
    """两层查找 DB 路径：环境变量 SKILLS_DB_PATH > D:/.db

    Args:
        skill_dir: 技能目录路径（通常为 Path(__file__).parent.parent）
        db_filename: 数据库文件名

    Returns:
        Path: 数据库文件路径
    """
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    # 2. fallback: D:\.db\（WSL 自动转 /mnt/d/.db/）
    db_dir = _fallback_db_dir()
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / db_filename


@contextmanager
def connection(db_path):
    """数据库连接 context manager（新代码推荐）

    使用:
        with connection(db_path) as conn:
            conn.execute(...)
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


_migrated_paths = set()


def apply_migrations(conn):
    """幂等列迁移(2026-08-04 #52: 已有 DB 也保证新列,不只建库时)

    对已打开的连接补 daily_goal 新列;PRAGMA 检查幂等,可重复调用。
    """
    c = conn.cursor()
    cols = {r[1] for r in c.execute('PRAGMA table_info(daily_goal)')}
    if 'start_weight' not in cols:
        c.execute('ALTER TABLE daily_goal ADD COLUMN start_weight REAL')
    if 'start_date' not in cols:
        c.execute('ALTER TABLE daily_goal ADD COLUMN start_date TEXT')
    conn.commit()


def get_db(db_path):
    """获取数据库连接（兼容旧 API，调用方需自行 close）

    新代码请用 connection() context manager。
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    key = str(db_path)
    if key not in _migrated_paths:
        apply_migrations(conn)
        _migrated_paths.add(key)
    return conn


def init_db(db_path):
    """初始化数据库所有表 + 应用迁移

    表：food_log / daily_goal / exercise_log / weight_log / nutrition_products
          / workout_plan_config / workout_plans
    迁移：daily_goal 表添加 weight_goal / goal_deadline / water_goal 列
    """
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    # food_log — 食物记录（含饮水）
    c.execute('''
        CREATE TABLE IF NOT EXISTS food_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT,
            food_name TEXT NOT NULL,
            grams INTEGER NOT NULL,
            calories INTEGER NOT NULL,
            protein INTEGER DEFAULT 0,
            carbs INTEGER DEFAULT 0,
            fat INTEGER DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # daily_goal — 每日营养目标 + 体重目标 + 饮水目标
    c.execute('''
        CREATE TABLE IF NOT EXISTS daily_goal (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            calorie_goal INTEGER NOT NULL DEFAULT 1800,
            protein_goal INTEGER DEFAULT 150,
            carbs_goal INTEGER DEFAULT 200,
            fat_goal INTEGER DEFAULT 60,
            weight_goal REAL,
            goal_deadline TEXT,
            water_goal INTEGER DEFAULT 2000,
            goal_paused INTEGER DEFAULT 0,
            exercise_goal INTEGER,
            start_weight REAL,
            start_date TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # exercise_log — 运动记录
    c.execute('''
        CREATE TABLE IF NOT EXISTS exercise_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT,
            exercise_type TEXT NOT NULL,
            duration_minutes INTEGER,
            calories_burned INTEGER NOT NULL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # weight_log — 体重记录
    c.execute('''
        CREATE TABLE IF NOT EXISTS weight_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT,
            weight_kg REAL NOT NULL,
            height_cm REAL,
            bmi REAL,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # nutrition_products — 食品营养成分库（每 100g）
    c.execute('''
        CREATE TABLE IF NOT EXISTS nutrition_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            brand TEXT,
            calories REAL NOT NULL,
            protein REAL NOT NULL,
            fat REAL NOT NULL,
            saturated_fat REAL,
            carbohydrates REAL NOT NULL,
            sugar REAL,
            dietary_fiber REAL,
            sodium REAL NOT NULL,
            source TEXT NOT NULL DEFAULT '未知',
            is_deprecated INTEGER NOT NULL DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_food_log_date ON food_log(date)')

    # 迁移：food_log 表新增 sodium/sugar/fiber（2026-08-02 · ticket #10 · 分析 A5 钠糖纤维场景）
    # 值域：mg/g（钠 mg，糖/纤维 g），按「每 100g 含量 × grams / 100」从 nutrition_products 回填
    _existing_cols_food = {
        row[1] for row in c.execute('PRAGMA table_info(food_log)').fetchall()
    }
    for _col, _type in [
        ('sodium_mg', 'REAL'),
        ('sugar_g', 'REAL'),
        ('fiber_g', 'REAL'),
    ]:
        if _col not in _existing_cols_food:
            c.execute(f'ALTER TABLE food_log ADD COLUMN {_col} {_type}')
    # 回填（幂等：只回填 NULL 的行；按食品名匹配 nutrition_products 每 100g 值 × 克数 / 100）
    c.execute('''
        UPDATE food_log
        SET sodium_mg = ROUND(
                (SELECT n.sodium FROM nutrition_products n
                 WHERE n.product_name = food_log.food_name AND n.is_deprecated = 0
                 ORDER BY n.id DESC LIMIT 1) * food_log.grams / 100.0, 1),
            sugar_g   = ROUND(
                (SELECT n.sugar FROM nutrition_products n
                 WHERE n.product_name = food_log.food_name AND n.is_deprecated = 0
                 ORDER BY n.id DESC LIMIT 1) * food_log.grams / 100.0, 1),
            fiber_g   = ROUND(
                (SELECT n.dietary_fiber FROM nutrition_products n
                 WHERE n.product_name = food_log.food_name AND n.is_deprecated = 0
                 ORDER BY n.id DESC LIMIT 1) * food_log.grams / 100.0, 1)
        WHERE food_log.sodium_mg IS NULL
           OR food_log.sugar_g IS NULL
           OR food_log.fiber_g IS NULL
    ''')

    # 迁移：entries → food_log 改名（2026-07-12）
    _existing_tables = {row[0] for row in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if 'entries' in _existing_tables and 'food_log' not in _existing_tables:
        c.execute('ALTER TABLE entries RENAME TO food_log')
    elif 'entries' in _existing_tables and 'food_log' in _existing_tables:
        # 两个表都存在时,把 entries 数据合并到 food_log,然后删除 entries
        c.execute('INSERT OR IGNORE INTO food_log (date, time, food_name, grams, calories, protein, carbs, fat, note, created_at) SELECT date, time, food_name, grams, calories, protein, carbs, fat, note, created_at FROM entries')
        c.execute('DROP TABLE entries')

    # 迁移：删除废弃的 sleep_records 表（2026-07-12，睡眠跟踪移到作息管家）
    if 'sleep_records' in _existing_tables:
        c.execute('DROP TABLE IF EXISTS sleep_records')
    c.execute('CREATE INDEX IF NOT EXISTS idx_weight_date ON weight_log(date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_exercise_date ON exercise_log(date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_product_name ON nutrition_products(product_name)')

    # 迁移：daily_goal 表新增列
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN weight_goal REAL')
    except Exception:
        pass
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN goal_deadline TEXT')
    except Exception:
        pass
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN water_goal INTEGER DEFAULT 2000')
    except Exception:
        pass
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN goal_paused INTEGER DEFAULT 0')
    except Exception:
        pass
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN exercise_goal INTEGER')  # 2026-08-02 · ticket #5 运动:每日运动消耗目标(卡)
    except Exception:
        pass
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN start_weight REAL')  # 2026-08-04 · #52:体重目标起点体重(设定时快照)
    except Exception:
        pass
    try:
        c.execute('ALTER TABLE daily_goal ADD COLUMN start_date TEXT')  # 2026-08-04 · #52:体重目标起点日期
    except Exception:
        pass

    # 迁移：nutrition_products 表新增 source / is_deprecated（食品库扩展 · 2026-06-30）
    _existing_cols_p = {
        row[1] for row in c.execute('PRAGMA table_info(nutrition_products)').fetchall()
    }
    _products_new_cols = [
        ('source', "TEXT DEFAULT '未知'"),
        ('is_deprecated', 'INTEGER DEFAULT 0'),
        ('category', "TEXT DEFAULT ''"),   # 查食品(按分类) · ticket #3
    ]
    for _col, _type in _products_new_cols:
        if _col not in _existing_cols_p:
            c.execute(f'ALTER TABLE nutrition_products ADD COLUMN {_col} {_type}')

    # 索引：source 字段（建在 ALTER 之后，避免列不存在时失败）
    c.execute('CREATE INDEX IF NOT EXISTS idx_product_source ON nutrition_products(source)')

    # 已有数据回填：note / product_name / brand 任一字段含 [已废弃] → is_deprecated=1
    # （幂等：只更新还没标记的）
    c.execute(
        "UPDATE nutrition_products SET is_deprecated = 1 "
        "WHERE is_deprecated = 0 AND ("
        "note LIKE '%[已废弃]%' "
        "OR product_name LIKE '%[已废弃]%' "
        "OR brand LIKE '%[已废弃]%'"
        ")"
    )

    # 迁移：exercise_log 表新增 6 列（运动功能扩展 · 2026-06-29）
    #   - category        有氧/力量/柔韧/日常
    #   - difficulty      easy/normal/hard（2026-07-12 从 intensity 改为与训记对齐）
    #   - distance_km     跑步/骑行距离
    #   - avg_heart_rate  平均心率
    #   - set_index       力量场景：第几组
    #   - load_kg         力量场景：单侧重量
    # 幂等：检查列是否存在再 ALTER，重复运行不报错
    _existing_cols = {
        row[1] for row in c.execute('PRAGMA table_info(exercise_log)').fetchall()
    }
    _exercise_log_new_cols = [
        ('category', 'TEXT'),
        ('difficulty', 'TEXT'),
        ('distance_km', 'REAL'),
        ('avg_heart_rate', 'INTEGER'),
        ('set_index', 'INTEGER'),
        ('load_kg', 'REAL'),
        ('reps', 'INTEGER'),  # 2026-07-13 补:exercise.py:53 写入时用到,原 DDL 漏声明
        ('updated_at', 'TEXT'),  # 2026-07-13 补:xunji_adapter:97 UPDATE 用到,原 DDL 漏声明(SQLite 限制:DATETIME 默认值需应用层设)
        ('steps', 'INTEGER'),  # 2026-08-02 · ticket #5 运动:记日常活动(步数)
        ('max_heart_rate', 'INTEGER'),  # 2026-08-02 · ticket #5 运动:记有氧运动(最高心率)
        ('is_deleted', 'INTEGER DEFAULT 0'),  # 2026-08-02 · ticket #5 运动:软删除(删/批量删)
        ('is_backfill', 'INTEGER DEFAULT 0'),  # 2026-08-02 · ticket #5 运动:补录标识(补记/批量补记)
    ]
    for _col, _type in _exercise_log_new_cols:
        if _col not in _existing_cols:
            c.execute(f'ALTER TABLE exercise_log ADD COLUMN {_col} {_type}')

    # 迁移：intensity → difficulty 数据迁移（2026-07-12）
    if 'intensity' in _existing_cols:
        c.execute(
            "UPDATE exercise_log SET difficulty = "
            "CASE intensity "
            "WHEN '低' THEN 'easy' "
            "WHEN '中' THEN 'normal' "
            "WHEN '高' THEN 'hard' "
            "ELSE NULL END "
            "WHERE difficulty IS NULL AND intensity IS NOT NULL"
        )

    # 迁移：exercise_log 加 xunji 关联字段（2026-07-12）
    #   xunji_localid  训记训练记录唯一标识（用于关联查询 / 去重）
    #   xunji_title    训练名称（如"胸部训练"）
    _xunji_cols = [('xunji_localid', 'TEXT'), ('xunji_title', 'TEXT')]
    for _col, _type in _xunji_cols:
        if _col not in _existing_cols:
            c.execute(f'ALTER TABLE exercise_log ADD COLUMN {_col} {_type}')

    # 索引：exercise_log 新列（category / set_index 加速按类/按组查询）
    c.execute('CREATE INDEX IF NOT EXISTS idx_exercise_category ON exercise_log(category)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_exercise_type ON exercise_log(exercise_type)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_exercise_xunji_localid ON exercise_log(xunji_localid)')  # 2026-07-13 补:加速 xunji_adapter 幂等去重

    # ============ 健身计划表（2026-07-12 新建）============
    # workout_plan_config — 计划元信息（1行）
    c.execute('''
        CREATE TABLE IF NOT EXISTS workout_plan_config (
            id              INTEGER PRIMARY KEY CHECK (id = 1),
            title           TEXT NOT NULL,
            version         TEXT,
            description     TEXT,
            total_weeks     INTEGER NOT NULL,
            start_date      TEXT NOT NULL,          -- 计划起始日期 YYYY-MM-DD
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # workout_plans — 训练日程（N行：周次×星期几×时间段）
    c.execute('''
        CREATE TABLE IF NOT EXISTS workout_plans (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            week_number     INTEGER NOT NULL,
            day_of_week     INTEGER NOT NULL,
            session_index   INTEGER NOT NULL DEFAULT 1,
            session_label   TEXT NOT NULL,
            time_start      TEXT,
            time_end        TEXT,
            is_rest_day     INTEGER DEFAULT 0,
            total_sets      INTEGER,
            movements       TEXT NOT NULL DEFAULT '[]',
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at      TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(week_number, day_of_week, session_index)
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_wp_week_day ON workout_plans(week_number, day_of_week)')

    # body_photos — 身材照片记录（2026-07-13 移入 db.py 统一管理，原 body_photo_tracker.py 独立 init 已删除）
    c.execute('''
        CREATE TABLE IF NOT EXISTS body_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            photo_path TEXT NOT NULL,
            tag TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_body_photos_date ON body_photos(date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_body_photos_tag ON body_photos(tag)')

    # user_profile — 用户档案（2026-07-16 新增，单行表,review TDEE 用）
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),  -- 单行表
            age INTEGER,                           -- 年龄(岁)
            gender TEXT,                           -- 'male' / 'female'
            height_cm REAL,                        -- 身高(cm,从 weight_log 同步过来)
            note TEXT DEFAULT '',                  -- 备注
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 迁移：user_profile 表新增 activity_level（2026-08-02 · ticket #8 · 基础信息 4 场景）
    # 值域：sedentary / light / moderate / active / very_active（英文字典 + 中文 label 映射，#19A 决策）
    _existing_cols_profile = {
        row[1] for row in c.execute('PRAGMA table_info(user_profile)').fetchall()
    }
    if 'activity_level' not in _existing_cols_profile:
        c.execute(
            "ALTER TABLE user_profile ADD COLUMN activity_level "
            "TEXT DEFAULT 'moderate'"
        )
        # 已有数据回填（幂等：默认值已覆盖，仅防御 NULL）
        c.execute(
            "UPDATE user_profile SET activity_level = 'moderate' "
            "WHERE activity_level IS NULL"
        )
    # 枚举约束（SQLite ADD COLUMN 带 CHECK 兼容性差，用 trigger 守护，同 body_measurements 风格）
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS user_profile_activity_level_check
        BEFORE INSERT ON user_profile
        WHEN (NEW.activity_level IS NOT NULL AND NEW.activity_level NOT IN
              ('sedentary', 'light', 'moderate', 'active', 'very_active'))
        BEGIN
            SELECT RAISE(ABORT, 'activity_level 必须是 sedentary/light/moderate/active/very_active 之一');
        END
    ''')
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS user_profile_activity_level_check_update
        BEFORE UPDATE OF activity_level ON user_profile
        WHEN (NEW.activity_level IS NOT NULL AND NEW.activity_level NOT IN
              ('sedentary', 'light', 'moderate', 'active', 'very_active'))
        BEGIN
            SELECT RAISE(ABORT, 'activity_level 必须是 sedentary/light/moderate/active/very_active 之一');
        END
    ''')

    # 迁移：删除废弃的 fitness_goals 表（2026-07-12，重构为 workout_plans）
    if 'fitness_goals' in _existing_tables:
        c.execute('DROP TABLE IF EXISTS fitness_goals')

    # body_composition — 体脂钳测（2026-07-25，V1.0 §02 第 ① 数据层）
    # 7 皮钳 NOT NULL + CHECK，source 白名单，body_fat_pct [0, 60]
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS body_composition (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL CHECK (source IN ({SOURCE_HOME_CALIPER!r}, {SOURCE_HOSPITAL!r}, {SOURCE_GYM!r})),
            age INTEGER,
            sex TEXT CHECK (sex IN ('male', 'female')),
            caliper_chest_mm REAL CHECK (caliper_chest_mm > 0 AND caliper_chest_mm < 100),
            caliper_abdominal_mm REAL CHECK (caliper_abdominal_mm > 0 AND caliper_abdominal_mm < 100),
            caliper_thigh_mm REAL CHECK (caliper_thigh_mm > 0 AND caliper_thigh_mm < 100),
            caliper_tricep_mm REAL CHECK (caliper_tricep_mm > 0 AND caliper_tricep_mm < 100),
            caliper_subscapular_mm REAL CHECK (caliper_subscapular_mm > 0 AND caliper_subscapular_mm < 100),
            caliper_suprailiac_mm REAL CHECK (caliper_suprailiac_mm > 0 AND caliper_suprailiac_mm < 100),
            caliper_midaxillary_mm REAL CHECK (caliper_midaxillary_mm > 0 AND caliper_midaxillary_mm < 100),
            body_fat_pct REAL NOT NULL CHECK (body_fat_pct >= 0 AND body_fat_pct <= 60),
            calculated_at TEXT,
            note TEXT DEFAULT '',
            is_deprecated INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_body_composition_date ON body_composition(date)')

    # 迁移:body_composition.source CHECK 加 gym(2026-08-02 · ticket #9 记体脂（外部测量）)
    # SQLite 无法改 CHECK → 检测旧 CHECK(不含 gym)则表重建 + 数据迁移
    _bc_sql = c.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='body_composition'"
    ).fetchone()
    if _bc_sql and _bc_sql[0] and SOURCE_GYM not in _bc_sql[0]:
        c.execute("""
            CREATE TABLE body_composition_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                source TEXT NOT NULL CHECK (source IN ({choices})),
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
        """.format(choices=', '.join(repr(s) for s in SOURCE_CHOICES)))
        c.execute('''
            INSERT INTO body_composition_new (
                id, date, source, age, sex,
                caliper_chest_mm, caliper_abdominal_mm, caliper_thigh_mm, caliper_tricep_mm,
                caliper_subscapular_mm, caliper_suprailiac_mm, caliper_midaxillary_mm,
                body_fat_pct, calculated_at, note, is_deprecated, created_at, updated_at
            ) SELECT id, date, source, age, sex,
                caliper_chest_mm, caliper_abdominal_mm, caliper_thigh_mm, caliper_tricep_mm,
                caliper_subscapular_mm, caliper_suprailiac_mm, caliper_midaxillary_mm,
                body_fat_pct, calculated_at, note, is_deprecated, created_at, updated_at
            FROM body_composition
        ''')
        c.execute('DROP TABLE body_composition')
        c.execute('ALTER TABLE body_composition_new RENAME TO body_composition')
        c.execute('CREATE INDEX IF NOT EXISTS idx_body_composition_date ON body_composition(date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_body_composition_source ON body_composition(source)')
    else:
        c.execute('CREATE INDEX IF NOT EXISTS idx_body_composition_source ON body_composition(source)')

    # body_measurements — 围度（2026-07-25，V1.0 §02 第 ① 数据层）
    # 13 围度记录级必填(date + ≥1 围度)，列级 NULL OK + 条件 CHECK
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
    # 记录级必填：date + 至少 1 个围度（SQLite 不支持跨列 NULL 比较 CHECK，用 trigger 实现）
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS body_measurements_require_metric
        BEFORE INSERT ON body_measurements
        WHEN (
            NEW.chest_cm IS NULL AND NEW.waist_cm IS NULL AND NEW.abdomen_cm IS NULL
            AND NEW.hip_cm IS NULL AND NEW.left_thigh_cm IS NULL AND NEW.right_thigh_cm IS NULL
            AND NEW.left_calf_cm IS NULL AND NEW.right_calf_cm IS NULL
            AND NEW.left_arm_cm IS NULL AND NEW.right_arm_cm IS NULL
            AND NEW.left_forearm_cm IS NULL AND NEW.right_forearm_cm IS NULL
            AND NEW.shoulder_cm IS NULL
        )
        BEGIN
            SELECT RAISE(ABORT, 'body_measurements 需要 date + 至少 1 个围度');
        END;
    ''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_body_measurements_date ON body_measurements(date)')

    _migrate_composition_caliper_nullable(conn)

    conn.commit()
    conn.close()


def _migrate_composition_caliper_nullable(conn):
    """迁移:body_composition 7 皮褶列去 NOT NULL(2026-08-03 验收 · 外部测量无皮褶)

    旧表:caliper_*_mm REAL NOT NULL → 新表:REAL(可 NULL,CHECK 保留,NULL 天然通过)。
    SQLite 不支持 ALTER COLUMN 去 NOT NULL,采用 重建表 + 拷数据 + 改名。
    """
    cur = conn.cursor()
    info = {r[1]: r[3] for r in cur.execute('PRAGMA table_info(body_composition)')}
    calipers = ['caliper_chest_mm', 'caliper_abdominal_mm', 'caliper_thigh_mm',
                'caliper_tricep_mm', 'caliper_subscapular_mm', 'caliper_suprailiac_mm',
                'caliper_midaxillary_mm']
    if not all(k in info for k in calipers):
        return
    if all(info[k] == 0 for k in calipers):
        return  # 已迁移
    cols = [r[1] for r in cur.execute('PRAGMA table_info(body_composition)')]
    col_sql = ', '.join(f'"{x}"' for x in cols)
    cur.execute('''
        CREATE TABLE body_composition_mig (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            source TEXT NOT NULL CHECK (source IN ('home_caliper', 'hospital', 'gym')),
            age INTEGER,
            sex TEXT CHECK (sex IN ('male', 'female')),
            caliper_chest_mm REAL CHECK (caliper_chest_mm > 0 AND caliper_chest_mm < 100),
            caliper_abdominal_mm REAL CHECK (caliper_abdominal_mm > 0 AND caliper_abdominal_mm < 100),
            caliper_thigh_mm REAL CHECK (caliper_thigh_mm > 0 AND caliper_thigh_mm < 100),
            caliper_tricep_mm REAL CHECK (caliper_tricep_mm > 0 AND caliper_tricep_mm < 100),
            caliper_subscapular_mm REAL CHECK (caliper_subscapular_mm > 0 AND caliper_subscapular_mm < 100),
            caliper_suprailiac_mm REAL CHECK (caliper_suprailiac_mm > 0 AND caliper_suprailiac_mm < 100),
            caliper_midaxillary_mm REAL CHECK (caliper_midaxillary_mm > 0 AND caliper_midaxillary_mm < 100),
            body_fat_pct REAL NOT NULL CHECK (body_fat_pct >= 0 AND body_fat_pct <= 60),
            calculated_at TEXT,
            note TEXT DEFAULT '',
            is_deprecated INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute(f'INSERT INTO body_composition_mig ({col_sql}) SELECT {col_sql} FROM body_composition')
    cur.execute('DROP TABLE body_composition')
    cur.execute('ALTER TABLE body_composition_mig RENAME TO body_composition')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_body_composition_date ON body_composition(date)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_body_composition_source ON body_composition(source)')