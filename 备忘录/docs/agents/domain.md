# 领域文档 · 备忘录

本目录的领域文档布局按仓库根协议（详见 `D:\2Study\StudyNotes\SKILLS\docs\agents\domain.md`）。

## 探索之前，先读这些

按顺序（根协议定义）：

1. 仓库根 `CONTEXT-MAP.md` — 索引本仓库所有技能子目录的 `CONTEXT.md`
2. `备忘录/CONTEXT.md` — 本技能的术语表与领域概念定义
3. `备忘录/docs/adr/`（若有）— 本技能专属决策
4. 仓库根 `docs/adr/`（若有）— 仓库级决策

若上述任一文件不存在，**静默继续**。

## 本仓库布局

本仓库是**单仓库多上下文**：根 `CONTEXT.md` + 根 `CONTEXT-MAP.md` 索引到各技能子目录的 `CONTEXT.md`。每个技能是一个独立的领域上下文。

## 范围标识

每个 issue 标题必须以 `[备忘录]` 开头，并携带 `skill:备忘录` label。