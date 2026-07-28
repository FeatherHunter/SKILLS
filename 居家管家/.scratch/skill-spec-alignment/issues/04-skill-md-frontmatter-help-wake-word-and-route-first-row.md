# 04 — SKILL.md frontmatter help_wake_word + §路由表 第 1 行(钩子 7)

**What to build:** AI agent can find the HELP wake word in two ways: (a) reading SKILL.md frontmatter metadata (machine-readable), (b) reading §路由表 first row (human-readable)。`help` 子命令从此在两个入口都立即可见。

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

**Source:** spec.md §Solution · Q10=single_first · 总纲钩子 7。

**Acceptance criteria:**

- [ ] SKILL.md frontmatter 新增 `metadata.help_wake_word: "居家管家 帮助"`(单数字符串,非数组)
- [ ] §路由表 第 1 行 改为 HELP 唤醒词(从原第 33 行提升)
- [ ] §路由表 新首行格式:`| 居家管家 帮助 | 技能速查 | help | 是 |`
- [ ] 原 §路由表 第 2 行起的顺序不变(其他 32 唤醒词相对位置保留)
- [ ] **Risk A 写入 ADR-0001**:加 1 段"frontmatter 约定:metadata.help_wake_word 是 2026-07-28 约定,若未来总纲 frontmatter schema 严格化(字段白名单),可改字段名 + 同步 AI 调用方"
- [ ] pytest 全 124 PASS(无代码改动,home_manager.py 不解析 frontmatter)

**Risk A:** frontmatter schema 未来变化 — 已写入 ADR-0001 留 future-proofing 路径

**Decision trace:**
- Q10 = single_first(非 multi 复数,非 single_keep 原位置)
- 理由:简单、显眼、足以满足钩子 7
- metadata 不被 home_manager.py 解析,blast radius = 0