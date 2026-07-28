# 12 — SKILL.md 加「与其他工具的边界」章节

**What to build:** 后续读者看到 `config-cookie-accounting.ts` 不再误以为是本 Skill 的实现 —— SKILL.md 明确声明此文件属于 SkillBoard 数据层视图，独立维护；本 Skill 的 5 层骨架（数据 / 操作 / 规则 / 接口 / 文档）不含此文件。

**Blocked by:** 11 — 先有桥接表，边界声明才有依据

**Status:** ready-for-agent

- [ ] `SKILL.md` 加 §与其他工具的边界 章节
- [ ] 引用 `references/categories-mapping.md`
- [ ] 明确 `config-cookie-accounting.ts` 不在 5 层骨架内、独立维护、与本 Skill 视图的桥接关系
- [ ] `tests/test_render.py` 加测试：`SKILL.md` 含该章节关键词（如「SkillBoard」/「独立维护」）
- [ ] 不修改 SKILL.md 第一段（领域描述）+ §唤醒词总表（留给 08）+ §📌 输出位置（留给 09）