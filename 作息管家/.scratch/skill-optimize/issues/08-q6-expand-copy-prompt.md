---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 08
Blocked-by: []
---

# 08 — Q6 Expand · record_receipt 加"复制 prompt"按钮 + payload

**What to build:** 用户打开 `记作息回执_<TS>.html`(record_receipt),看到页面有"📋 复制 prompt"按钮,点击后剪贴板里是包含 4 部分(场景 / 数据 / 期望 / 来源)的 prompt,用户粘贴给 AI 即可让 AI 执行该记录的"修正作息"等后续操作。

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] render_payload 新增 `prompt_meta` 字段(wake_word / scenario_title / prompt 4 部分 / 来源 CLI + 时间)
- [ ] `_record_engine.js` 共享层支持复制按钮 + 4 部分渲染
- [ ] 剪贴板 API 优先(`navigator.clipboard.writeText`);不可用时降级(`execCommand` + textarea)
- [ ] 复制成功 toast 反馈(`✅ 已复制 · 粘贴给 AI`)
- [ ] 移动端响应式(640px 以下仍可点击)
- [ ] pytest 全绿 + 新增测试覆盖复制逻辑
- [ ] commit Tested-By:fresh-agent-v1(跑 record_receipt → 浏览器看到复制按钮 → 点击 → 剪贴板有 4 部分)