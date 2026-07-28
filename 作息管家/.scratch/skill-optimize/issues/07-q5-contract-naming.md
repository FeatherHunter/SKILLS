---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 07
Blocked-by: ["03", "04", "05", "06"]
---

# 07 — Q5 Contract · 删 `_naming_path` 英文 fallback

**What to build:** 所有 record / plan / receipt 域 14 个迁移 ticket(03-06)落地后,删除 `_naming_path` 函数的英文 command 名 fallback,只接受中文 command 名。整个 codebase 验证无英文 command 残留调用。

**Blocked by:** 03, 04, 05, 06(所有 4 个迁移 batch 必须完成,否则删除英文 fallback 会破坏未迁移的调用方)

**Status:** ready-for-agent

- [ ] `_naming_path` 函数删英文 command 名 fallback
- [ ] 英文 command 调用 `_naming_path` 抛 ValueError(明确错误信息:字段名 + 当前值 + 期望值 + 怎么修)
- [ ] 全 codebase grep 验证无英文 command 残留(`rg "record_day\|plan_list\|record_receipt"` 返回 0 结果,除了历史代码注释 / 测试 fixture)
- [ ] pytest 全绿
- [ ] commit Tested-By:fresh-agent-v1(故意跑英文 record_day 应报错 + 中文查作息记录 应正常)