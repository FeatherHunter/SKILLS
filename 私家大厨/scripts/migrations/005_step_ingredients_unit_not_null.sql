-- Migration 005: step_ingredients.unit 改 NOT NULL
-- 用户决策 2026-07-22: ALL 字段都非空(L1 阶段漏设 unit NOT NULL)
--
-- ⚠️ SQLite 限制:ALTER TABLE 不能改 NOT NULL 状态
-- 必须 recreate table: CREATE NEW + COPY + DROP + RENAME
--
-- 关联:CHANGELOG.md [P1]
-- 回滚:从 .bak 文件恢复
-- 备份时间:2026-07-22

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

-- 1. 创建新表(unit NOT NULL)
CREATE TABLE step_ingredients_new (
    id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    quantity_used REAL NOT NULL,
    introduced_at TEXT NOT NULL,
    unit TEXT NOT NULL,  -- 改 NOT NULL
    FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
);

-- 2. 复制数据(只复制 unit 非空的 — 实测 12 行全有值,但保险起见加 WHERE)
INSERT INTO step_ingredients_new (id, step_id, ingredient_id, quantity_used, introduced_at, unit)
SELECT id, step_id, ingredient_id, quantity_used, introduced_at, unit
FROM step_ingredients
WHERE unit IS NOT NULL;

-- 3. 检查是否有丢数据(单元 NULL 行数,应 = 0)
-- SELECT COUNT(*) FROM step_ingredients WHERE unit IS NULL;  -- 应 = 0

-- 4. DROP 旧表 + RENAME 新表
DROP TABLE step_ingredients;
ALTER TABLE step_ingredients_new RENAME TO step_ingredients;

-- 5. 重建索引
CREATE INDEX idx_step_ingredients_step ON step_ingredients(step_id);
CREATE INDEX idx_step_ingredients_ingredient ON step_ingredients(ingredient_id);

COMMIT;
PRAGMA foreign_keys = ON;