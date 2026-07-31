# CONTEXT — 仓库级术语表

本文件是 `FeatherHunter/SKILLS` 仓库的根级领域词汇表。覆盖跨技能共享或未归入任何单个技能的概念。各技能子目录维护自己的 `CONTEXT.md`，通过 `CONTEXT-MAP.md` 索引。

## 仓库核心概念

- **技能（Skill）**：本仓库并排放置的独立产品单元，每个技能是一个目录（如 `备忘录/`、`卡路里/`），有自身的 `SKILL.md`、业务脚本、模板与测试。
- **唤醒词（Wake Word）**：技能面向 AI 助手的自然语言入口短语，由 `SKILL.md` 定义并通过 `references/scenarios.yaml` 描述。
- **场景（Scenario）**：唤醒词对应的用户意图+参数+结果形态三元组，是模板化输出的事实源。
- **HTML 镜像**：每个技能的 `SKILL.md` 对应一份镜像 HTML（如 `备忘录.html`），由 skill CLI 自动生成，不手写。

## 仓库级工作流

- **A.4 5 文件范式**：`.scratch/<feature>/` 下必备 `spec.md` / `verify.*` / `issues/` / `decisions.md` / `artifacts/`（最后一项可空）。
- **commit 中文硬规则**：见根 `AGENTS.md`；每条 commit 必须含 `Tested-By:` 行末。
- **Issue 隔离**：GitHub Issue 标题必须以 `[技能名]` 起首，并通过 `skill:<名>` label 标注归属（详见 `docs/agents/issue-tracker.md`）。

## 仓库基础设施

- **git 子模块**：`mcp_excalidraw/`、`superpowers/`、`taste-skill/`、`ui-ux-pro-max-skill/`，独立仓库独立维护。
- **`.githooks/`**：仓库级 Git 钩子（`commit-msg` 强制中文格式，`pre-commit` 还原测试副产物）。
- **`.scratch/`**：仓库根级别整目录 gitignore；只用于跨技能一次性调试产物（如 `phone-repro/`、`weight-history-table-mobile-redesign/`），不作为 issue tracker。

## 待补全

> 占位：随着 `/domain-modeling` 在跨技能主题上的实际工作展开，这里会逐步添加术语。每个新术语需配套：定义 / 反例 / 出现于哪份文件。

- _（暂无）_