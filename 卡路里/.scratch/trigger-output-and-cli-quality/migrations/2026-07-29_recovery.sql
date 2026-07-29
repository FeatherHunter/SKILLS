-- 2026-07-29_recovery.sql — 卡路里 DB 恢复脚本 · ticket 03 · ADR-0006
--
-- 目的:
--   删除 weight_log id 132-135 的 4 条测试数据
--   (note='测试' / 'P2 测试' / 'P1+P2 测试' / '现状核实')
--
-- 2026-07-29 11:07 之前的污染:daily_goal.weight_goal='--help' 字符串
--   2026-07-29 19:09 实际执行时,weight_goal 已被用户(或前序 fix)改回合理值 73.0
--   故本脚本跳过 UPDATE daily_goal(用户选择保留 73.0)
--
-- 执行步骤(需用户显式点头 per SKILL §⚠️ 强制性规定 第 3 条):
--   1. 备份: cp calorie_data.db calorie_data.db.pre-recovery.20260729_HHMMSS
--   2. Pre-flight: SELECT COUNT(*) FROM weight_log WHERE id IN (132,133,134,135);
--   3. 跑本 SQL(只 1 行 DELETE)
--   4. Post-flight: SELECT COUNT(*) FROM weight_log WHERE id IN (132,133,134,135);  → 应是 0

-- 1. 删除 weight_log 4 条测试数据
DELETE FROM weight_log WHERE id IN (132, 133, 134, 135);

-- 2. 验证(只读)
SELECT 'post-flight: weight_log test data should be 0' AS check_name;
SELECT COUNT(*) AS test_data_count FROM weight_log WHERE id IN (132, 133, 134, 135);

-- 3. weight_goal 保持不动(用户当前 73.0,如需改 7/20 备份的 69.95,执行:
--    UPDATE daily_goal SET weight_goal=69.95, goal_deadline='2026-10-30' WHERE id=1;
--  )

-- 4. 当前 daily_goal 全状态(只读)
SELECT 'post-flight: daily_goal' AS check_name;
SELECT id, weight_goal, goal_deadline, updated_at FROM daily_goal WHERE id=1;