-- 003_rollback.sql
-- 撤销 003_ingredient_category_v11.sql:把"葱姜蒜"恢复回"调料"
UPDATE ingredients SET category = '调料'
WHERE name IN ('生姜', '姜', '老姜', '大蒜', '蒜', '蒜瓣', '蒜苗',
               '葱', '小葱', '香葱', '大葱', '葱花', '蒜蓉',
               '姜末', '蒜末')
  AND category = '葱姜蒜';