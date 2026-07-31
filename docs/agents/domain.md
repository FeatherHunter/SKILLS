# 领域文档

工程技能在探索本仓库时应如何消费领域文档。

## 探索之前，先读这些

按顺序：

1. **`CONTEXT-MAP.md`**（仓库根） —— 索引本仓库所有技能子目录的 `CONTEXT.md`。先读它，再决定读哪一份。
2. **`<技能>/CONTEXT.md`** —— 当前话题所在技能的术语表与领域概念定义。
3. **`docs/adr/`**（仓库根） —— 仓库级决策；同时检查 `<技能>/docs/adr/` 下技能专属决策。
4. **`.scratch/<feature>/`**（若存在） —— 该技能的活跃工作目录，含 `spec.md` / `decisions.md` / `issues/`（历史归档，本地 md）/ `verify.*` / `artifacts/`。

若上述任一文件不存在，**静默继续**。`/domain-modeling`（经 `/grill-with-docs` 与 `/improve-codebase-architecture` 触达）会在术语或决策真正被解决时按需懒创建。

## 文件结构

本仓库采用 **单仓库多上下文**：根 `CONTEXT.md` + 根 `CONTEXT-MAP.md` 索引到各技能子目录的 `CONTEXT.md`。每个技能是一个独立的领域上下文。

```
SKILLS/
├── AGENTS.md                       ← 仓库级协作入口
├── CONTEXT.md                      ← 仓库级术语表
├── CONTEXT-MAP.md                  ← 索引各技能 CONTEXT.md
├── docs/
│   ├── agents/
│   │   ├── issue-tracker.md        ← GitHub Issues + 前缀方案
│   │   ├── triage-labels.md
│   │   └── domain.md               ← 本文件
│   └── adr/                        ← 仓库级 ADR
└── <技能>/
    ├── AGENTS.md
    ├── CONTEXT.md
    ├── docs/adr/                   ← 技能专属 ADR
    ├── SKILL.md
    ├── .scratch/<feature>/         ← 活跃工作目录
    └── .out-of-scope/              ← /triage 拒绝 enhancement 的 KB
```

## 词汇与术语

当你的输出命名一个领域概念（在 issue 标题、重构提案、假设、测试名中）时，**优先用**对应 `CONTEXT.md` 中定义的术语；跨技能话题用根 `CONTEXT.md` 的术语。

如果你需要的概念尚未在任何 `CONTEXT.md` 中：

- 你可能在发明项目未使用的语言 → 重新考虑
- 存在真实的术语缺口 → 走 `/domain-modeling` 录入

## 标记 ADR 冲突

若你的输出与某条已有 ADR 相悖，请显式指出，而非默默覆盖：

> _与 ADR-0007（事件溯源订单）相悖 —— 但值得重新讨论，因为……_

## 范围标识

每个工作目录（issue / ADR / spec / 评论）必须包含技能归属，方式：

- GitHub issue：标题 `[技能名]` 前缀 + `skill:技能名` label
- ADR：frontmatter `Skill: <技能名>`（仓库级 ADR 留空）
- 本地 md ticket：路径含技能目录（`<技能>/.scratch/<feature>/issues/NN-*.md`）