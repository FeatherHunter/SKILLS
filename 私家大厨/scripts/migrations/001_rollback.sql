-- Rollback 001: 撤销 step_ingredients.unit 列
--
-- 注意:SQLite 不支持 DROP COLUMN(< 3.35),但 3.35+ 支持。
-- 如果 SQLite 版本 < 3.35,需要重建表:
--   1. CREATE TABLE step_ingredients_new AS SELECT * FROM step_ingredients;
--   2. DROP TABLE step_ingredients;
--   3. ALTER TABLE step_ingredients_new RENAME TO step_ingredients;
-- 当前 3.10+ 一般支持,这里用标准 SQL:

ALTER TABLE step_ingredients DROP COLUMN unit;
