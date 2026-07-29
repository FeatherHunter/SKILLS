-- 2026-07-29_recovery.sql
-- 卡路里 DB 恢复脚本 · ticket 03 · ADR-0006
--
-- 目的:
--   1. 恢复 daily_goal.weight_goal='--help' 污染(7/20 备份原值 69.95 kg,deadline '2026-10-30')
--   2. 删除 weight_log id 132-135 的 4 条测试数据(note='测试' / 'P2 测试' / 'P1+P2 测试' / '现状核实')
--
-- 执行步骤(需用户显式点头 per SKILL §⚠️ 强制性规定 第 3 条):
--   1. 备份: cp calorie_data.db calorie_data.db.pre-recovery.20260729_HHMMSS
--   2. Pre-flight: SELECT weight_goal FROM daily_goal WHERE id=1;  → 确认是 '--help'
--   3. 跑本 SQL
--   4. Post-flight: SELECT weight_goal, goal_deadline FROM daily_goal WHERE id=1;  → 应是 69.95 / '2026-10-30'
--   5. Post-flight: SELECT COUNT(*) FROM weight_log WHERE id IN (132,133,134,135);  → 应是 0

-- 1. 恢复 daily_goal 体重目标
UPDATE daily_goal
SET weight_goal = 69.95,
    goal_deadline = '2026-10-30',
    updated_at = '2026-07-29 ' || strftime('%H:%M:%S', 'now')
WHERE id = 1;

-- 2. 删除 weight_log 4 条测试数据
DELETE FROM weight_log WHERE id IN (132, 133, 134, 135);

-- 3. 验证(只读)
SELECT 'post-flight: daily_goal' AS check_name;
SELECT id, weight_goal, goal_deadline, updated_at FROM daily_goal WHERE id = 1;

SELECT 'post-flight: weight_log test data should be 0' AS check_name;
SELECT COUNT(*) AS test_data_count FROM weight_log WHERE id IN (132, 133, 134, 135);