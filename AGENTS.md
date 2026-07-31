# AGENTS

本仓库（`FeatherHunter/SKILLS`）的根级 AI 协作入口。技能子目录各自维护 `AGENTS.md`，本文件只描述**仓库级别**的约定。

## 项目结构

跨技能集装仓库，根目录并排放置多个独立技能（`备忘录/`、`卡路里/`、`居家管家/`、`饼干记账/`、`智剪工坊/`、`作息管家/`、`SKILL开发总纲V1.0/` 等）。每个技能是一个独立产品，各自维护 `AGENTS.md`、`CONTEXT.md`、`docs/adr/` 和 `.scratch/<feature>/` 工作目录。

## Git 与远端

- 远程：`github.com/FeatherHunter/SKILLS`
- 主分支：`main`
- 子模块（独立仓库）：`mcp_excalidraw/`、`superpowers/`、`taste-skill/`、`ui-ux-pro-max-skill/`
- 嵌入式 PAT 见 `docs/agents/issue-tracker.md` 安全备注

## 提交规范

全中文硬规则（详见 `docs/agents/issue-tracker.md` 与子技能各自 `AGENTS.md`）：

```
[技能名] <主题> · <细节(可选)>
Tested-By: exempt(无 fresh agent · 详见 ADR-0005)
```

❌ 禁用英文类型前缀（`fix:` `docs:` `feat:` `chore:`）与英文括号类型（`fix(...)` 等）。
✅ 每个 commit 必须含 `Tested-By` 行末。

## Agent skills

### Issue tracker

GitHub Issues（`FeatherHunter/SKILLS`），按技能前缀分区：`[备忘录]` / `[卡路里]` / `[居家管家]` / `[饼干记账]` / `[智剪工坊]` / `[作息管家]` / `[SKILL开发总纲V1.0]`。详见 `docs/agents/issue-tracker.md`。

### Triage labels

五状态二分类默认标签（`needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix` + `bug` / `enhancement`）。详见 `docs/agents/triage-labels.md`。

### Domain docs

单上下文仓库布局，根 `CONTEXT.md` + 根 `docs/adr/` 存仓库级术语与决策；各技能通过 `CONTEXT-MAP.md` 索引到各自的 `CONTEXT.md`。详见 `docs/agents/domain.md`。