# 02 — Agent 入口完整路径(SKILL.md frontmatter + AGENTS.md 升级)

**Parent**: `00-memo-skill-v1.1.5-refactor-spec.md`

**What to build:**
任何 AI agent(包括 opencode)进入备忘录 skill 目录时,从两个文件就能立刻得到完整"我该怎么用这个 skill"的信息。具体讲:读 SKILL.md 顶部 YAML frontmatter 立刻知道 skill 名称 / 版本 / 状态 / 一句话描述 / 最后更新;读 AGENTS.md 立刻知道项目定位 / 路径约定 / 决策文件位置 / commit 格式硬规则 / HTML 镜像约定。两个文件加起来让 agent 在不读 1038 行 SKILL.md 的前提下,完整理解 skill 的入口契约。

**Blocked by:** None — 可立即开始

**Status:** ready-for-agent

## Acceptance criteria

- [ ] SKILL.md 顶部含 YAML frontmatter,5 字段:`name`(备忘录) / `version`(1.1.5) / `status`(active) / `description`(一句话) / `last_updated`(2026-07-28)
- [ ] frontmatter 用 `---` 包围,YAML 格式合法(Python `yaml.safe_load` 可解析)
- [ ] SKILL.md frontmatter 的 `version` 与 `_meta.json` 的 `version` 一致(由 ticket 04 同步落地)
- [ ] `AGENTS.md` 升级到 25-30 行,从原 13 行扩展
- [ ] AGENTS.md 新增 5 段:项目定位 / 路径约定 / 决策文件位置 / commit 格式 / HTML 镜像约定
- [ ] AGENTS.md 引用 ADR-0003 commit 全中文硬规则(README 不直接复制硬规则)

## Out of scope

- README.md(由 ticket 01 处理)
- pytest.ini(由 ticket 03 处理)
- SKILL.md 主体内容改动(91 处术语替换由 ticket 05 处理)
