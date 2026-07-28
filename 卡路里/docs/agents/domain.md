# Domain Docs

engineering skills 在探索代码库时应如何消费本仓库的领域文档。

## 探索之前,先读这些

- 仓库根目录的 **`CONTEXT.md`**;或
- 如果存在仓库根目录的 **`CONTEXT-MAP.md`**,它会指向每个 context 各自的 `CONTEXT.md`。读取与你正在处理的话题相关的那些。
- **`docs/adr/`** —— 阅读触及你即将工作区域的 ADR。在 multi-context 仓库中,还要检查 `src/<context>/docs/adr/` 中 context 级别的决策。

如果其中任何文件不存在,**静默继续**。不要标记它们的缺失;不要预先建议创建它们。`/domain-modeling` skill(经 `/grill-with-docs` 和 `/improve-codebase-architecture` 触达)会在术语或决策真正被解决时按需创建它们。

## 文件结构

单一上下文仓库(大多数仓库):

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

多上下文仓库(根目录存在 `CONTEXT-MAP.md`):

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← 系统级决策
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← context 专属决策
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## 使用 glossary 的词汇

当你的输出提到一个领域概念(在 issue 标题、重构提案、假设、测试名中)时,使用 `CONTEXT.md` 中定义的术语。不要漂移到 glossary 明确避免的同义词。

如果你需要的概念还不在 glossary 里,那是一个信号 —— 要么你在发明项目不用的语言(重新考虑),要么真的存在缺口(记下来交给 `/domain-modeling`)。

## 标记 ADR 冲突

如果你的输出与某个已有 ADR 相冲突,请显式指出,而不是静默覆盖:

> _Contradicts ADR-0007 (event-sourced orders) —— 但值得重新讨论,因为……_
