---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 06
Blocked-by: ["02"]
---

# 06 — Q5 Migrate · list_events 1 模板路径对齐

**What to build:** 跑 render-list-events 子命令,输出文件名 `查日程_<TS>.html`(对应"查日程" / "看日程"唤醒词)。

**Blocked by:** 02(Q5 Expand 必须先完成)

**Status:** ready-for-agent

- [ ] render-list-events 子命令的默认路径改为 `查日程_<TS>.html`
- [ ] tests/test_naming.py 覆盖 list_events 新文件名
- [ ] pytest 全绿
- [ ] commit Tested-By:fresh-agent-v1(查日程 + 看日程各 2 个 prompt)