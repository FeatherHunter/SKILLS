# 01 — CONTEXT.md 加 Skill 标识约定 + 通用术语引用

**What to build:** AI agent reading 居家管家 CONTEXT.md can find both the **Skill 标识约定** (`home_manager`,英文,避开中文路径) AND a **通用术语引用** section pointing to 总纲 §CONTEXT.md for 5 shared terms (5 状态 fallback / 复制 prompt 按钮 / 变体管理 / 相对时间 helper / 跨 Skill 路由).

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

**Source:** spec.md 第 1-2 张 user story;grilling Q1=alpha, Q3=C。

**Acceptance criteria:**

- [ ] CONTEXT.md §Language 节已有 "Skill 标识" 定义,加 1 行 "(2026-07-28 grilling round 1 确认)" 标记此为约定非偏离
- [ ] CONTEXT.md 新增 §通用术语引用 节,列 5 术语 + 指针到 `../../SKILL开发总纲V1.0/CONTEXT.md` 对应位置
- [ ] pytest 全 124 PASS(无代码改动,仅文档)
- [ ] 5 术语均按总纲 28 词表的字面引用,不重复定义

**Risk:** 无(SKILL.md frontmatter 的 schema 风险在 ticket 04 处理)

**Decision trace:**
- Q1 = alpha: 仅放居家管家(不升级总纲)
- Q3 = C: 双层,总纲定义基础 + 居家管家引用