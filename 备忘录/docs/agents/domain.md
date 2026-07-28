# 领域文档

工程技能在探索本仓库代码库时应如何消费领域文档。

## 探索之前，先读这些

- **`CONTEXT.md`** 位于 `备忘录/` 根目录；或
- **`CONTEXT-MAP.md`** 位于 `备忘录/` 根目录（若存在）—— 它指向每个上下文一份 `CONTEXT.md`。阅读与你话题相关的那几份。
- **`docs/adr/`** —— 阅读涉及你即将改动区域的 ADR。多上下文仓库中，也检查 `src/<上下文>/docs/adr/` 下上下文专属的决策。

若上述任一文件不存在，**静默继续**。不要标记其缺失；不要建议预先创建。`/domain-modeling` 技能（经 `/grill-with-docs` 和 `/improve-codebase-architecture` 触达）会在术语或决策真正被解决时按需懒创建它们。

## 文件结构

单上下文仓库（大多数仓库）：

```
备忘录/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── script/
```

多上下文仓库（根目录存在 `CONTEXT-MAP.md` 时）：

```
备忘录/
├── CONTEXT-MAP.md
├── docs/adr/                          ← 系统级决策
└── script/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← 上下文专属决策
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## 使用术语表的词汇

当你的输出命名一个领域概念（在问题标题、重构提案、假设、测试名中）时，使用 `CONTEXT.md` 中定义的术语。不要漂移到术语表明确避免的同义词。

若你需要的概念尚未在术语表中，这是一个信号 —— 要么你在发明项目未使用的语言（重新考虑），要么存在真实的缺口（记录给 `/domain-modeling`）。

## 标记 ADR 冲突

若你的输出与某条已有 ADR 相悖，请显式指出，而非默默覆盖：

> _与 ADR-0007（事件溯源订单）相悖 —— 但值得重新讨论，因为……_
