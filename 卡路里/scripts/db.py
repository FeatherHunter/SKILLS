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


DB_FILENAME = "calorie_data.db"


def _fallback_db_dir():
    """全局 fallback DB 目录：Windows → D:/.db，WSL → /mnt/d/.db"""
    if sys.platform == 'win32':
        return Path('D:/.db')
    d_drive = Path('/mnt/d')
    if d_drive.exists():
        return d_drive / '.db'
    raise RuntimeError(
        'SKILLS_DB_PATH 未设置，且 D: 盘未挂载到 /mnt/d/。'
        '请检查 WSL automount 配置或设置 SKILLS_DB_PATH 环境变量。'
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


def get_db(db_path):
    """获取数据库连接（兼容旧 API，调用方需自行 close）

    新代码请用 connection() context manager。
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
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

    # 迁移：nutrition_products 表新增 source / is_deprecated（食品库扩展 · 2026-06-30）
    _existing_cols_p = {
        row[1] for row in c.execute('PRAGMA table_info(nutrition_products)').fetchall()
    }
    _products_new_cols = [
        ('source', "TEXT DEFAULT '未知'"),
        ('is_deprecated', 'INTEGER DEFAULT 0'),
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

    # 迁移：删除废弃的 fitness_goals 表（2026-07-12，重构为 workout_plans）
    if 'fitness_goals' in _existing_tables:
        c.execute('DROP TABLE IF EXISTS fitness_goals')

    conn.commit()
    conn.close()