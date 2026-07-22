-- 002_shopping_index.sql
-- v5.2 采购清单重构 - 给 ingredients 表加常用查询索引
--
-- 改动前必答 3 问:
--   1. 影响哪些文件? 本文件(ALTER TABLE) + db.py 自动跑 migration
--   2. 有没有数据迁移? 是(创建索引),CREATE INDEX IF NOT EXISTS 安全
--   3. 回滚方案? 对应 002_rollback.sql(DROP INDEX)
--
-- 索引设计:
--   idx_ingredients_recipe_category: (recipe_id, category) 联合索引
--     - shopping_manager.py generate 的核心查询路径
--     - WHERE recipe_id IN (...) AND is_optional = 0 ORDER BY category, sequence
--   已有 idx_ingredients_recipe_id(单列),但联合索引在多食谱场景更快

CREATE INDEX IF NOT EXISTS idx_ingredients_recipe_category
    ON ingredients (recipe_id, category);

-- 单食谱的精确查询索引(可选,看是否真有用,先不加)
-- CREATE INDEX IF NOT EXISTS idx_ingredients_recipe_id ON ingredients (recipe_id);