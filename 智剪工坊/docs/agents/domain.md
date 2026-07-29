# 领域文档

说明工程类技能在探索代码库时应如何消费本仓库的领域文档。

## 探索前必读

- 仓库根目录的 **`CONTEXT.md`**;若根目录存在 **`CONTEXT-MAP.md`**,则它指向每个上下文各自的 `CONTEXT.md` —— 阅读与当前主题相关的每一份。
- **`docs/adr/`** —— 阅读与你即将改动区域相关的 ADR。多上下文仓库中,还要检查 `src/<context>/docs/adr/` 中该上下文专属的决策。

若上述任一文件不存在,**静默继续**。不要标记其缺失;不要建议预先创建。`/domain-modeling` 技能(经 `/grill-with-docs` 与 `/improve-codebase-architecture` 调用)会在术语或决策真正得到解决时按需创建它们。

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
    │   └── docs/adr/                  ← 上下文专属决策
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## 使用术语表的词汇

当你的输出提及某个领域概念(在 issue 标题、重构提案、假设、测试名中)时,使用 `CONTEXT.md` 中定义的术语。不要漂移到术语表明确规避的同义词。

若你所需的概念尚未在术语表中,这是一个信号 —— 要么你在发明项目并不使用的语言(请重新考虑),要么确实存在缺口(记下来交给 `/domain-modeling`)。

## 标记 ADR 冲突

若你的输出与某条已有 ADR 相悖,请显式指出,而非静默覆盖:

> _与 ADR-0007(事件溯源订单)相悖 —— 但值得重开,因为……_
