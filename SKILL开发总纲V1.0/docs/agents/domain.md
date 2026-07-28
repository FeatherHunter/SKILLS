# 领域文档

工程类 skill 在探索代码库时,如何消费本仓库的领域文档。

## 探索前必读

- **`CONTEXT.md`** 在仓库根,或
- **`CONTEXT-MAP.md`** 在仓库根(若存在)——它指向每个 context 的 `CONTEXT.md`。读取与当前话题相关的那些
- **`docs/adr/`** — 读取触及你即将工作区域的 ADR。多 context 仓库中,也检查 `src/<context>/docs/adr/` 的 context 级决策

如果这些文件任何一个不存在,**静默继续**。不要标记它们的缺失;不要建议预先创建。`/domain-modeling` skill(经 `/grill-with-docs` 和 `/improve-codebase-architecture` 到达)会在术语或决策真正被解析时懒创建它们。

## 文件结构

单 context 仓库(本仓库):

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-a-coordinate-internal-consistency.md
│   └── 0002-remove-scale-flexibility.md
├── docs/agents/        ← 本文件所在
└── (总纲 9 个 .md + 3 _assets + HTML 镜像)
```

## 使用术语表词汇

当你的输出命名一个领域概念(在 issue 标题、重构提案、假设、测试名里),使用 `CONTEXT.md` 中定义的术语。不要漂移到术语表明确避免的同义词。

如果你需要的概念还不在术语表里,这是个信号——要么你在发明项目不用的语言(重新考虑),要么有真实缺口(记下来给 `/domain-modeling`)。

## 标记 ADR 冲突

如果你的输出与现有 ADR 矛盾,显式标记出来,而非静默覆盖:

> _与 ADR-0001(A 坐标优先)冲突——但值得重开,因为…_
