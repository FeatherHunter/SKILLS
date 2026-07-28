---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 10
Blocked-by: ["03", "04", "05", "06"]
---

# 10 — Q7 · `_naming_path` 按 record/plan/receipt/help 4 域注释分组

**What to build:** `_naming_path` 函数体内按 4 域(record / plan / receipt / help)加注释分组,代码结构清晰可读,为将来拆模块打基础(ADR-0003)。schedule_cli.py 字节数 < 150KB / 行数 < 4000(不超拆模块触发条件)。

**Blocked by:** 03, 04, 05, 06(路径对齐迁移完成后再做分组,避免边迁移边重构)

**Status:** ready-for-agent

- [ ] `_naming_path` 函数体内有 4 个 `# === <域> ===` 注释分组
- [ ] 每个分组下是该域的命令映射(if/elif 链或 dict 查找)
- [ ] schedule_cli.py 字节数 < 150KB(防止拆模块触发条件提前满足)
- [ ] schedule_cli.py 行数 < 4000
- [ ] pytest 全绿(行为不变,纯内部重构)
- [ ] commit Tested-By:exempt(纯内部重构 · 行为不变)