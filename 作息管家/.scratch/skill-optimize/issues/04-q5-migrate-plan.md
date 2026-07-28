---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 04
Blocked-by: ["02"]
---

# 04 — Q5 Migrate · plan 域 5 模板路径对齐

**What to build:** 跑任一 plan 域 render 命令(查日程 / 改日程回执 / 补日程回执 / 写日程回执 / 商量计划预览 / 复盘),输出文件名都是 `<中文 command>_<YYYYMMDD>_<HHMMSS>.html`,用户在 IDE 直接看到中文文件名对应 SKILL.md 唤醒词。

**Blocked by:** 02(Q5 Expand 必须先完成)

**Status:** ready-for-agent

- [ ] 5 个 render-plan-* / render-query-plans / render-plan-receipt-* / render-plans-preview / render-plans-review 子命令的默认路径改为中文 command 名
- [ ] 输出文件名:`查日程_<TS>.html` / `改日程回执_<TS>.html` / `补日程回执_<TS>.html` / `写日程回执_<TS>.html` / `商量计划预览_<TS>.html` / `复盘_<TS>.html`
- [ ] SKILL.md §3.1 / §4 / §11 路径引用更新
- [ ] tests/test_naming.py 扩展覆盖 5 个新文件名
- [ ] pytest 全绿
- [ ] commit Tested-By:fresh-agent-v1(5 个唤醒词各 2 个 prompt)