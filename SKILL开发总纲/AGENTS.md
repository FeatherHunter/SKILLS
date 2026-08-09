# AGENTS.md · SKILL 开发总纲 V1.0

本文件是项目根的 agent 指令文件。任何 agent 进入本项目时自动读取。

## 项目定位

本仓库是 SKILL 开发总纲 V1.0——定义 Skill 这一产物的设计、改造、演化规则的元规范。开发新 Skill 或改造现有 Skill 之前必读。

## Agent skills

### Issue tracker

Issues 以本地 markdown 文件形式存于 `.scratch/<feature>/`。See `docs/agents/issue-tracker.md`.

### Triage labels

使用 5 个默认 canonical roles(needs-triage / needs-info / ready-for-agent / ready-for-human / wontfix)。See `docs/agents/triage-labels.md`.

### Domain docs

单 context 布局:根 `CONTEXT.md` + 根 `docs/adr/`。See `docs/agents/domain.md`.
