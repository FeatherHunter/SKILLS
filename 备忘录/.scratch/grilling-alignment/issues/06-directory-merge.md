# 06 — 双目录合并(expand-contract 两阶段)

**Parent**: `00-memo-skill-v1.1.5-refactor-spec.md`

**What to build:**
消除 `reference/` 与 `references/` 双目录并存,统一为 `references/`(复数)。整个过程采用 expand-contract 两阶段(双目录差异小,只需 2 阶段):

- **Phase 1 (expand)**: 把 `reference/` 下 3 个 .md(schema.md / examples.md / cron.md)复制到 `references/`(保留 `reference/`,新旧都能访问,所有现有路径引用继续工作)。期间 174 pytest 全过。
- **Phase 2 (contract)**: SKILL.md 4 处引用更新到 `references/`(用 git mv 跟踪);删除 `reference/` 空目录。期间 174 pytest 全过。

**Blocked by:** None — 可立即开始

**Status:** ready-for-agent

## Acceptance criteria

### Phase 1 (expand)

- [ ] `references/schema.md` / `examples.md` / `cron.md` 存在(从 reference/ 复制,内容 byte-identical)
- [ ] `reference/` 保留,3 个 .md 还在
- [ ] `references/` 现含 4 个文件(scenarios.yaml + 3 个 .md)
- [ ] SKILL.md 中所有 `reference/` 路径引用继续解析成功
- [ ] 174 pytest 全过

### Phase 2 (contract)

- [ ] SKILL.md 中 4 处 `reference/` 路径改为 `references/`
- [ ] `reference/` 目录删除(`rm -rf reference/` 验证)
- [ ] `references/` 现含 4 个文件(scenarios.yaml + 3 个 .md),均为 git mv 跟踪
- [ ] `memo_render.py:30` 的 `references/scenarios.yaml` 引用不变(本来就是新路径)
- [ ] 174 pytest 全过
- [ ] `git grep "reference/" -- ':!docs/adr/0002-*.md'` 返回 0 行(ADR 是历史归档,允许保留)

## Out of scope

- 3 个 .md 文件内容修改(本 ticket 只搬位置,不调整内容)
- scenarios.yaml 改名(它是场景资产,不动)
- 跨 Skill `_shared/` 共享代码(v1.1.0 教训,不重提)
