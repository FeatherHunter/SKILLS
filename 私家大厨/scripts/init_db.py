#!/usr/bin/env python3
"""
私家大厨 - 数据库初始化脚本
创建17张表的DDL

设计哲学:
- 严格遵循"SKILLS_DB_PATH 环境变量优先"原则
- 如果 env var 指定路径,即使文件不存在,也在该路径创建空 DB + 建表
- 如果 env var 没设,沿用 db_config.py 的 fallback 逻辑
"""
import sqlite3
import sys
from pathlib import Path

from db_config import get_connection, get_db_path, ensure_wal_mode, DB_PATH


def _ensure_db_file():
    """确保 DB 文件物理存在(env var 路径或 fallback 路径)

    为什么需要这一步:
    - get_connection() 调 sqlite3.connect(str(DB_PATH)),如果文件不存在会自动创建空 DB
    - 但用户期望 init_db 是"幂等"的 — 显式创建比隐式更可控
    - 同时 init_db 可能被外部脚本调用,显式创建便于其他工具感知 DB 位置
    """
    if DB_PATH.exists():
        return False  # 已存在,跳过

    # 创建空 DB(只含 sqlite_master,无 user tables)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.close()
    return True  # 新建


def init_db():
    """初始化数据库，创建所有表"""
    db_path = get_db_path()

    # 0. 显式确保 DB 文件存在(env var 路径或 fallback)
    created = _ensure_db_file()
    if created:
        print(f"📁 已创建空 DB: {db_path}")

    # 1. 确保 WAL 模式
    ensure_wal_mode()

    # 2. 拿连接
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("BEGIN")

    print(f"初始化数据库: {get_db_path()}")
    
    # ========== 表1：recipes（食谱主表）==========
    # L1-A: 全部业务字段 NOT NULL(用户决策 R2),status 去掉 DEFAULT(用户决策 R3)
    # created_at/updated_at 保留 DEFAULT CURRENT_TIMESTAMP(系统必需)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            servings INTEGER NOT NULL,
            total_time_minutes INTEGER NOT NULL,
            status TEXT NOT NULL,
            photo_url TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_name ON recipes(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_difficulty ON recipes(difficulty)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipes_status ON recipes(status)")
    print("✓ recipes 表创建完成")
    
    # ========== 表2：recipe_categories（分类标签）==========
    # L1-A: 3 业务字段 NOT NULL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_categories (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            cuisine_type TEXT NOT NULL,
            region TEXT NOT NULL,
            country TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_categories_recipe ON recipe_categories(recipe_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_categories_cuisine ON recipe_categories(cuisine_type)")
    print("✓ recipe_categories 表创建完成")
    
    # ========== 表3：recipe_seasons（适合季节）==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_seasons (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            season TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_seasons_recipe ON recipe_seasons(recipe_id)")
    print("✓ recipe_seasons 表创建完成")
    
    # ========== 表4：recipe_cooking_methods（烹饪方式）==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_cooking_methods (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            method TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_cooking_methods_recipe ON recipe_cooking_methods(recipe_id)")
    print("✓ recipe_cooking_methods 表创建完成")
    
    # ========== 表5：recipe_flavors（口味）==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_flavors (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            flavor TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_flavors_recipe ON recipe_flavors(recipe_id)")
    print("✓ recipe_flavors 表创建完成")
    
    # ========== 表6：recipe_diet_tags（饮食标签）==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_diet_tags (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_diet_tags_recipe ON recipe_diet_tags(recipe_id)")
    print("✓ recipe_diet_tags 表创建完成")
    
    # ========== 表7：recipe_meal_types（用餐类型）==========
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_meal_types (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            meal_type TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_meal_types_recipe ON recipe_meal_types(recipe_id)")
    print("✓ recipe_meal_types 表创建完成")
    
    # ========== 表8：ingredients（食材清单）==========
    # L1-A: 7 业务字段 NOT NULL,is_optional 去掉 DEFAULT 0(用户决策 R3)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingredients (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            quantity_text TEXT NOT NULL,
            is_optional INTEGER NOT NULL,
            substitute TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingredients_recipe ON ingredients(recipe_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ingredients_name ON ingredients(name)")
    print("✓ ingredients 表创建完成")
    
    # ========== 表9：cooking_steps（烹饪步骤）==========
    # L1-A: 4 业务字段 NOT NULL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cooking_steps (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            action TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            heat_level TEXT NOT NULL,
            temperature TEXT NOT NULL,
            expected_result TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cooking_steps_recipe ON cooking_steps(recipe_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cooking_steps_sequence ON cooking_steps(recipe_id, sequence)")
    print("✓ cooking_steps 表创建完成")
    
    # ========== 表10：step_ingredients（步骤×食材关联）==========
    # L1-A: 2 业务字段 NOT NULL
    # L3 阶段加回 unit 列(原 v5.1 设计的,被 L1 误删,add_steps 还在用)
    # 2026-07-22 P1 决策:unit 也 NOT NULL(L1 漏设,实测 12 行全有值,migration 005 已应用)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS step_ingredients (
            id TEXT PRIMARY KEY,
            step_id TEXT NOT NULL,
            ingredient_id TEXT NOT NULL,
            quantity_used REAL NOT NULL,
            introduced_at TEXT NOT NULL,
            unit TEXT NOT NULL,
            FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE CASCADE,
            FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_step_ingredients_step ON step_ingredients(step_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_step_ingredients_ingredient ON step_ingredients(ingredient_id)")
    print("✓ step_ingredients 表创建完成")
    
    # ========== 表11：step_techniques（步骤技法）==========
    # L1-A: 2 业务字段 NOT NULL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS step_techniques (
            id TEXT PRIMARY KEY,
            step_id TEXT NOT NULL,
            recipe_id TEXT NOT NULL,
            technique_name TEXT NOT NULL,
            description TEXT NOT NULL,
            key_points TEXT NOT NULL,
            FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE CASCADE,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_step_techniques_step ON step_techniques(step_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_step_techniques_recipe ON step_techniques(recipe_id)")
    print("✓ step_techniques 表创建完成")
    
    # ========== 表12：tips（小贴士）==========
    # L1-A (用户决策 R1/R4 B-1):
    # - category/priority NOT NULL
    # - step_id/ingredient_id 改回可空 + SET NULL(允许"菜级 tip")
    # - 业务校验在 L2 阶段 validators.py 加:优先要求 3 个 ID,迫不得已才允许不全
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tips (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            step_id TEXT,
            ingredient_id TEXT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            priority INTEGER NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
            FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE SET NULL,
            FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE SET NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tips_recipe ON tips(recipe_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tips_step ON tips(step_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tips_ingredient ON tips(ingredient_id)")
    print("✓ tips 表创建完成")
    
    # ========== 表13：recipe_history（烹饪历史）==========
    # L1-A: 3 业务字段 NOT NULL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_history (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            cook_date TEXT NOT NULL,
            cook_sequence INTEGER NOT NULL,
            rating REAL NOT NULL,
            feedback TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_history_recipe ON recipe_history(recipe_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_history_date ON recipe_history(cook_date)")
    print("✓ recipe_history 表创建完成")
    
    # ========== 表14：background_knowledge（背景知识）==========
    # L1-A: 1:1 UNIQUE 表,3 字段全 NOT NULL(用户决策:背景知识每菜必录)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS background_knowledge (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL UNIQUE,
            origin_story TEXT NOT NULL,
            historical_background TEXT NOT NULL,
            cultural_significance TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_background_recipe ON background_knowledge(recipe_id)")
    print("✓ background_knowledge 表创建完成")
    
    # ========== 表15：recipe_relations（食谱关系）==========
    # L1-A: 2 业务字段 NOT NULL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recipe_relations (
            id TEXT PRIMARY KEY,
            parent_id TEXT NOT NULL,
            child_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            change_summary TEXT NOT NULL,
            FOREIGN KEY (parent_id) REFERENCES recipes(id) ON DELETE CASCADE,
            FOREIGN KEY (child_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_relations_parent ON recipe_relations(parent_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recipe_relations_child ON recipe_relations(child_id)")
    print("✓ recipe_relations 表创建完成")
    
    # ========== 表16：cookware（炊具设备）==========
    # L1-A: 1 业务字段 NOT NULL
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cookware (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cookware_recipe ON cookware(recipe_id)")
    print("✓ cookware 表创建完成")
    
    # ========== 表17：nutrition_info（营养信息）==========
    # L1-A: 1:1 UNIQUE 表,8 字段全 NOT NULL(用户决策:营养信息每菜必录)
    # 白名单 7 个 0 值合法字段(用户决策):calories/protein/fat/carbs/fiber/sodium/serving_size
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS nutrition_info (
            id TEXT PRIMARY KEY,
            recipe_id TEXT NOT NULL UNIQUE,
            serving_size REAL NOT NULL,
            serving_unit TEXT NOT NULL,
            calories INTEGER NOT NULL,
            protein REAL NOT NULL,
            fat REAL NOT NULL,
            carbs REAL NOT NULL,
            fiber REAL NOT NULL,
            sodium REAL NOT NULL,
            FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_nutrition_recipe ON nutrition_info(recipe_id)")
    print("✓ nutrition_info 表创建完成")
    
    conn.commit()
    conn.close()

    print(f"\n✅ 数据库初始化完成！")
    print(f"数据库路径: {get_db_path()}")
    print(f"WAL 模式: 已启用")

if __name__ == "__main__":
    init_db()