-- Migration 001: step_ingredients 表加 unit 列
--
-- 背景:5 层架构改造 v5.0 端到端测试发现,JSON 里 step_ingredients[].unit
-- 字段写入了但 schema 没接住(数据丢失)。修法:加 unit 列。
--
-- 风险:ALTER TABLE ADD COLUMN 在 SQLite 是安全的(默认 NULL),不会锁表。
-- 回滚:见 migrations/001_rollback.sql
--
-- 日期:2026-07-21
-- 关联:CHANGELOG.md [5.1]

ALTER TABLE step_ingredients ADD COLUMN unit TEXT;
