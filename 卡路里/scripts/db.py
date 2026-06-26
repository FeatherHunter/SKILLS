#!/usr/bin/env python3
"""数据库基础工具 - DB 路径解析、连接、初始化

提供:
- find_db_path(skill_dir, db_filename) — 三层查找数据库路径
- get_db(db_path) — 获取 row_factory=Row 的连接（兼容旧 API）
- connection(db_path) — context manager 风格连接（新代码推荐）
- init_db(db_path) — 初始化所有表 + 迁移
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


DB_FILENAME = "calorie_data.db"


def find_db_path(skill_dir, db_filename=DB_FILENAME):
    """三层查找 DB 路径：环境变量 > 技能目录 > 父目录 .db

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
        if p.exists():
            return p
    # 2. 技能目录（默认）
    p = skill_dir / db_filename
    if p.exists():
        return p
    # 3. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / db_filename
            if p.exists():
                return p
    # 4. 都找不到则创建在 .db 目录
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename


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

    表：entries / daily_goal / exercise_log / weight_log / nutrition_products
    迁移：daily_goal 表添加 weight_goal / goal_deadline / water_goal 列
    """
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()

    # entries — 食物记录（含饮水）
    c.execute('''
        CREATE TABLE IF NOT EXISTS entries (
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
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date)')
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

    conn.commit()
    conn.close()