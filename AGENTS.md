# AGENTS

本仓库（`FeatherHunter/SKILLS`）的根级 AI 协作入口。技能子目录各自维护 `AGENTS.md`，本文件只描述**仓库级别**的约定。

## 项目结构

跨技能集装仓库，根目录并排放置多个独立技能（`备忘录/`、`卡路里/`、`居家管家/`、`饼干记账/`、`智剪工坊/`、`作息管家/`、`SKILL开发总纲V1.0/` 等）。每个技能是一个独立产品，各自维护 `AGENTS.md`、`CONTEXT.md`、`docs/adr/` 和 `.scratch/<feature>/` 工作目录。

## 跨技能规范（任何技能的设计/规划/开发必读）

**`SKILL开发总纲V1.0/` = 所有技能的元规范之家**，开发/改造任何技能之前先读其 `README.md`（文件清单索引）。重点：

- `08-HTML交互规范v1.md`（2026-08-04 新增）—— 跨技能 HTML 交互契约：8 类流程 / 通用骨架 / 4 标准能力 / 按钮语义 / 输出双通道 / 图片接收契约。**设计任何场景 HTML 或交互按钮时必读**。
- `09-SKILL重构优化指导.md`（2026-08-06 新增）—— 重构/优化既有 SKILL 的必读流程：规模分级 / 两条路径 / 14 条军规 / 闭环双门禁 / 偏离记录 / 复盘 / 人类理解对齐考题。配套模板集 `09.1-重构优化可复制模板集.md`。**接到任何「重构/优化 SKILL」任务时必读**。
- `04-可视化与注入v2.md` —— HTML 模板与注入原则
- `07-HELP与场景完备性.md` —— HELP 契约
- `05-工程仪式.md` —— FAT / Tested-By / hooks

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

单仓库多上下文布局，根 `CONTEXT.md` + 根 `CONTEXT-MAP.md` 索引到各技能子目录的 `CONTEXT.md`。详见 `docs/agents/domain.md`。