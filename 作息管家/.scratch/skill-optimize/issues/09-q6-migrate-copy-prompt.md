---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 09
Blocked-by: ["08"]
---

# 09 — Q6 Migrate · 其余 14 模板补"复制 prompt"

**What to build:** 跑任一 render 命令(record / plan / receipt 域 14 个),打开 HTML 都有"复制 prompt"按钮 + 4 部分 prompt + 剪贴板降级 + Toast 反馈。用户在任一模板页面都能复制场景给 AI。

**Blocked by:** 08(record_receipt 模板必须先落地,提供复制按钮 + payload 模式)

**Status:** ready-for-agent

- [ ] 14 个模板(record 域 5 + plan 域 5 + receipt 域 1 + list_events 1 + plan_review 1 + plan_preview 1)全部补"复制 prompt"
- [ ] 每场景独立复制按钮(非"全部复制")
- [ ] 每场景 4 部分结构(场景 / 数据 / 期望 / 来源)
- [ ] tests/test_copy_prompt.py 覆盖 15 个模板(包含 record_receipt)
- [ ] pytest 全绿
- [ ] commit Tested-By:fresh-agent-v1(15 个模板各 1 个 prompt,验证都有复制按钮)