# Domain Docs

工程类 skill 在探索代码库时,如何消费本仓库的领域文档。

## 探索前必读

- **`CONTEXT.md`** 在仓库根(若存在)— 本仓库当前**未创建**,按 domain-modeling 协议 lazy create
- **`CONTEXT-MAP.md`** 在仓库根(若存在) — 指向每个 context 的 `CONTEXT.md`。本仓库**不存在**(单 context 不需要)
- **`docs/adr/`** — 读取触及你即将工作区域的 ADR。单 context 仓库所有 ADR 集中在根目录

如果这些文件任何一个不存在,**静默继续**。不要标记它们的缺失;不要建议预先创建。`/domain-modeling` skill(经 `/grill-with-docs` 和 `/improve-codebase-architecture` 到达)会在术语或决策真正被解析时懒创建它们。

## 文件结构

**单 context 仓库**(本仓库作息管家):

```
作息管家/
├── AGENTS.md                        ← 工程 skill 配置入口(本仓库有)
├── CONTEXT.md                       ← lazy create(暂无)
├── docs/
│   ├── adr/                         ← ADR 目录(已存在:0001/0002/0003)
│   │   ├── 0001-help-html-stable-mirror.md
│   │   ├── 0002-strict-skill-spec.md
│   │   └── 0003-defer-cli-split.md
│   └── agents/                      ← 本文件所在
│       ├── issue-tracker.md
│       └── domain.md
├── .scratch/                        ← local markdown issue tracker
│   └── <feature>/
│       ├── spec.md
│       └── issues/
│           └── NN-<slug>.md
├── SKILL.md                         ← AI 主读本
├── references/
├── scripts/
├── templates/
├── tests/
└── CHANGELOG.md
```

## 使用术语表词汇

当你的输出命名一个领域概念(在 issue 标题、重构提案、假设、测试名里),使用 `CONTEXT.md` 中定义的术语。不要漂移到术语表明确避免的同义词。

如果你需要的概念还不在术语表里,这是个信号 — 要么你在发明项目不用的语言(重新考虑),要么有真实缺口(记下来给 `/domain-modeling`)。

## 标记 ADR 冲突

如果你的输出与现有 ADR 矛盾,显式标记出来,而非静默覆盖:

> _与 ADR-0001 作息管家.html 稳定入口 冲突 — 但值得重开,因为…_

## 已知备注

- 本仓库作息管家是 SKILLS/ monorepo 子目录,但**作息管家自身的 issue tracker / domain docs 配置独立维护**(在 `作息管家/` 子目录内),不依赖 SKILLS/ 根
- 如未来要做跨 SKILL 协同(例如作息管家 ↔ 卡路里 双向联动),重新评估 multi-context 布局,创建 `CONTEXT-MAP.md`