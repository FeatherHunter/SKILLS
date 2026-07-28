# 08 — 工程仪式落地(commit hook + SKILL.md 3 问段 + CHANGELOG Tested-By)

**Parent**: `00-memo-skill-v1.1.5-refactor-spec.md`

**What to build:**
维护者任何 commit 提交时,自动被三层工程仪式守护:

1. **commit-msg hook** 自动检查 commit 信息 — 不符合 `[<skill>] <主题> · <细节>` 全中文格式时拒绝;缺少 `Tested-By:` 行末时拒绝
2. **SKILL.md 顶部"改动前 3 问"段** — 每次改动前肉眼自检"影响哪些文件 / 数据迁移 / 回滚方案",豁免纯 doc/comment
3. **CHANGELOG.md 每个版本段含 `**Tested-By**` 字段** — 历史版本追溯,人类阅读友好

整套仪式从 v1.1.5 起强制启用。

**Blocked by:** ticket 02(SKILL.md frontmatter 先落地,version metadata 与 Tested-By 一致)+ ticket 05(术语统一后再加 3 问段,避免术语冲突)

**Status:** ready-for-agent

## Acceptance criteria

### commit-msg hook

- [ ] `.githooks/commit-msg` 文件存在,可执行(PowerShell `git config core.hooksPath` 已设为 `.githooks`,需确认)
- [ ] 输入非中文 commit(如 `fix: foo bar`) → hook 拒绝,exit 1
- [ ] 输入合规 commit 但缺 `Tested-By:` → hook 拒绝
- [ ] 输入合规 commit + `Tested-By: exempt(...)` → hook 通过
- [ ] hook 错误信息友好(中文提示"commit 信息必须为全中文,详见 ADR-0003")

### SKILL.md 3 问段

- [ ] SKILL.md frontmatter 后、`## 强制性规定` 前,加 `## 改动前 3 问` 段
- [ ] 段内含 3 问:影响哪些文件 / 数据迁移 / 回滚方案
- [ ] 段内含豁免规则:仅 doc/comment 改动可豁免

### CHANGELOG.md Tested-By

- [ ] CHANGELOG.md 每个 `[版本号]` 段末尾含 `**Tested-By**` 字段
- [ ] 历史版本补 `Tested-By: unknown(v1.1.4 之前未启用 Tested-By 字段)`
- [ ] v1.1.5 起 commit 都含 Tested-By(由 commit-msg hook 强制)

## Out of scope

- FAT 协议实跑(D.1 决策 exempt,无 fresh agent)
- 历史 commit 回填 Tested-By(commit history 不可改)
- pre-commit hook(`.githooks/pre-commit` 已修过,c0e6455 commit,本 ticket 不动)
- `git notes` Tested-By(ADR-0005 D.2 决策只用 commit 行末 + CHANGELOG)
