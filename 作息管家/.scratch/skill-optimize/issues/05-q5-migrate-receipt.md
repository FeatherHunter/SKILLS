---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 05
Blocked-by: ["02"]
---

# 05 — Q5 Migrate · receipt 域 2 模板路径对齐

**What to build:** 跑 record_receipt / record_receipt_edit 子命令,输出文件名都是 `<中文 command>_<YYYYMMDD>_<HHMMSS>.html`(`记作息回执_<TS>.html` / `修正作息回执_<TS>.html`)。

**Blocked by:** 02(Q5 Expand 必须先完成)

**Status:** ready-for-agent

- [ ] 2 个 receipt render 子命令的默认路径改为中文 command 名
- [ ] 输出文件名:`记作息回执_<TS>.html` / `修正作息回执_<TS>.html`
- [ ] SKILL.md §0 记作息 / §12 修正作息 路径引用更新
- [ ] tests/test_naming.py 扩展覆盖 2 个新文件名
- [ ] pytest 全绿
- [ ] commit Tested-By:fresh-agent-v1(记作息 + 修正作息各 2 个 prompt)