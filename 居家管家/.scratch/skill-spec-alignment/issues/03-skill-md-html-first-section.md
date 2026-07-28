# 03 — SKILL.md §⛓ HTML-First 章节(原则 11 强约定)

**What to build:** AI agent reading SKILL.md sees an explicit **HTML-First 行为契约**:12 个唤醒词命中后必须 invoke HTML,文字答视为 fail mode;允许优雅降级(HTML 失败 → 结构化文本)。

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

**Source:** spec.md §Solution · Q6=B · 总纲原则 11。

**Acceptance criteria:**

- [ ] SKILL.md 新增 §⛓ HTML-First 章节(插入位置:`## ⚠️ 核心使用原则` 之后 / `## §📌 输出位置` 之前)
- [ ] 章节列出 12 个唤醒词:`查物品 / 看物品 / 盘物品 / 盘全部 / 统物品 / 查高频 / 查低频 / 查过期 / 查快递 / 穿什么 / 带物品 / 归物品`
- [ ] 措辞强约定:"命中下列唤醒词后,**必须** invoke HTML 工作流,文字答视为 fail mode"
- [ ] 显式优雅降级:"若 HTML 生成失败(磁盘满 / 模板错),fallback 到结构化文本 + 错误回执,不要直接报错"
- [ ] 引用总纲原则 11 字面
- [ ] pytest 全 124 PASS(无代码改动)

**Risk:** 无(纯 SKILL.md 章节)

**Decision trace:**
- Q6 = B: 强约定(非 A 软建议 / 非 C 铁律)
- 理由:实际无 log 系统,C 铁律形式主义;B 强约定配合 commit 6 的 fallback 是务实选择