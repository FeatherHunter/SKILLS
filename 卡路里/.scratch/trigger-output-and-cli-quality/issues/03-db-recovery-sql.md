# 03 — DB 恢复 SQL(用户 gated)

**What to build:**
The production `calorie_data.db` is restored to a known-good state: weight_goal is `69.95 kg`, deadline is `2026-10-30`, and 4 polluting test records (weight_log ids 132-135) are deleted. This is the data-hygiene baseline every other ticket assumes.

**Blocked by:** None — but execution requires explicit user approval per the 卡路里 SKILL §⚠️ 强制性规定 第 3 条 ("对该技能的所有文件、脚本的任何一行修改都需要明确得到用户的 1 次确认,未经确认不得执行写入操作"). AI agent MUST NOT run this SQL until user says go.

**Status:** ready-for-agent (file prep); **execution-blocked** (SQL run requires user green-light)

- [ ] File `.scratch/trigger-output-and-cli-quality/migrations/2026-07-29_recovery.sql` exists and contains exactly:
  - A commented header explaining what the script does and why
  - `DELETE FROM weight_log WHERE id IN (132, 133, 134, 135);`
  - `UPDATE daily_goal SET weight_goal = 69.95, goal_deadline = '2026-10-30' WHERE id = 1;`
  - A verification SELECT at the end (read-only, prints expected state)
- [ ] Pre-flight check: read current state via Python sqlite3 — confirm `daily_goal.weight_goal='--help'` (corrupted) and `weight_log` has 4 rows at ids 132-135
- [ ] Backup created: `cp calorie_data.db calorie_data.db.pre-recovery.20260729_HHMMSS`
- [ ] SQL script executed
- [ ] Post-flight check: confirm `daily_goal.weight_goal=69.95`, `goal_deadline='2026-10-30'`, `weight_log` no longer contains ids 132-135
- [ ] Backup file confirmed to exist and have non-zero size