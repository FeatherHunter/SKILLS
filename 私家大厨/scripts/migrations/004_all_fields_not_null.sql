-- Migration 004: 所有业务字段 NOT NULL(98 字段,仅 tips 表 2 字段例外)
--
-- ⚠️ 这是 init_db.py 的只读副本,不要直接编辑 ⚠️
-- 自动生成时间:2026-07-22
-- 关联:CHANGELOG.md [5.4]
--
-- 背景:
-- SKILL 五层架构重构 L1 阶段。99 字段(实际 98)全 NOT NULL 兜底,
-- 业务字段完全靠 validators.py 强制必传。
--
-- 决策:
-- ① R2:98 字段中 96 个 NOT NULL(含 17 个 PK),2 个可空(tips 表)
-- ② R3:recipes.status 和 ingredients.is_optional 去掉 DEFAULT,完全靠 validators
-- ③ R1:tip表 step_id/ingredient_id 改回可空 + SET NULL(允许"菜级 tip")
-- ④ R4:业务校验在 L2 阶段 validators.py 加:优先要求 3 个 ID,迫不得已才允许不全
--
-- ⚠️ SQLite 限制:ALTER TABLE 不能改 NOT NULL 状态
-- 所以本文件不是真"迁移脚本",而是 init_db.py DDL 的快照
-- 重新 init DB 时请跑:python scripts/init_db.py
-- 回滚:从 .bak 文件恢复 + python scripts/init_db.py

-- ========== 表1：recipes（食谱主表）==========
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
);

-- ========== 表2：recipe_categories（分类标签）==========
CREATE TABLE IF NOT EXISTS recipe_categories (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    cuisine_type TEXT NOT NULL,
    region TEXT NOT NULL,
    country TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表3：recipe_seasons（适合季节）==========
CREATE TABLE IF NOT EXISTS recipe_seasons (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    season TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表4：recipe_cooking_methods（烹饪方式）==========
CREATE TABLE IF NOT EXISTS recipe_cooking_methods (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    method TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表5：recipe_flavors（口味）==========
CREATE TABLE IF NOT EXISTS recipe_flavors (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    flavor TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表6：recipe_diet_tags（饮食标签）==========
CREATE TABLE IF NOT EXISTS recipe_diet_tags (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表7：recipe_meal_types（用餐类型）==========
CREATE TABLE IF NOT EXISTS recipe_meal_types (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    meal_type TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表8：ingredients（食材清单）==========
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
);

-- ========== 表9：cooking_steps（烹饪步骤）==========
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
);

-- ========== 表10：step_ingredients（步骤×食材关联）==========
-- L3 阶段加回 unit 列(原 v5.1 设计,L1 误删)
-- 2026-07-22 P1 决策:unit 也 NOT NULL(L1 漏设,实测 12 行全有值,migration 005 已应用)
CREATE TABLE IF NOT EXISTS step_ingredients (
    id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    quantity_used REAL NOT NULL,
    introduced_at TEXT NOT NULL,
    unit TEXT NOT NULL,
    FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
);

-- ========== 表11：step_techniques（步骤技法）==========
CREATE TABLE IF NOT EXISTS step_techniques (
    id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL,
    recipe_id TEXT NOT NULL,
    technique_name TEXT NOT NULL,
    description TEXT NOT NULL,
    key_points TEXT NOT NULL,
    FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表12：tips（小贴士）==========
-- step_id/ingredient_id 可空 + SET NULL(允许"菜级 tip")
-- 业务校验在 L2 阶段 validators.py 加:优先要求 3 个 ID,迫不得已才允许不全
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
);

-- ========== 表13：recipe_history（烹饪历史）==========
CREATE TABLE IF NOT EXISTS recipe_history (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    cook_date TEXT NOT NULL,
    cook_sequence INTEGER NOT NULL,
    rating REAL NOT NULL,
    feedback TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表14：background_knowledge（背景知识）==========
-- 1:1 UNIQUE 表,3 字段全 NOT NULL(用户决策:背景知识每菜必录)
CREATE TABLE IF NOT EXISTS background_knowledge (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL UNIQUE,
    origin_story TEXT NOT NULL,
    historical_background TEXT NOT NULL,
    cultural_significance TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表15：recipe_relations（食谱关系）==========
CREATE TABLE IF NOT EXISTS recipe_relations (
    id TEXT PRIMARY KEY,
    parent_id TEXT NOT NULL,
    child_id TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    change_summary TEXT NOT NULL,
    FOREIGN KEY (parent_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (child_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表16：cookware（炊具设备）==========
CREATE TABLE IF NOT EXISTS cookware (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- ========== 表17：nutrition_info（营养信息）==========
-- 1:1 UNIQUE 表,8 字段全 NOT NULL(用户决策:营养信息每菜必录)
-- 白名单 7 个 0 值合法字段:calories/protein/fat/carbs/fiber/sodium/serving_size
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
);