-- 002_rollback.sql
-- 撤销 002_shopping_index.sql 的索引改动
DROP INDEX IF EXISTS idx_ingredients_recipe_category;