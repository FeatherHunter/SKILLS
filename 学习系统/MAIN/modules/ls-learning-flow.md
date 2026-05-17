---
module: ls-learning-flow
parent: learning-system-main
description: 基础学习流程（四阶段）协调器
load_when: 用户开始学习新知识时加载
depends: [ls-data-structure, LLM-WIKI]
---

# 基础学习流程（Foundation Path）

## 执行顺序

```
开始基础学习流程
    ↓
阶段1：加载 ls-stage-1.md → 执行 → 完成
    ↓
阶段2：加载 ls-stage-2.md → 执行 → 完成
    ↓
阶段3：加载 ls-stage-3.md → 执行 → 完成
    ↓
阶段4：加载 ls-stage-4.md → 执行 → 完成
    ↓
创建复习计划（python3 learning.py review create_schedule <id>）
    ↓
询问用户：是否进入精通流程？
    ↓
┌─────────────────────────────────────────────────┐
│ 是 → 加载 ls-stage-5.md → ls-stage-6.md → ls-stage-7.md │
│ 否 → 基础流程结束                               │
└─────────────────────────────────────────────────┘
```

---

## 各阶段文件索引

| 阶段 | 文件 | 目标 |
|------|------|------|
| 阶段4前置 | `ls-source-prep.md` | 源码/文档准备指南（知识类型→权威实现映射） |
| 阶段1 | `ls-stage-1.md` | Level 1（能说是什么） |
| 阶段2 | `ls-stage-2.md` | Level 2（能在项目用） |
| 阶段3 | `ls-stage-3.md` | Level 3（能说为什么） |
| 阶段4 | `ls-stage-4.md` | Level 4（能说怎么实现） |
| 阶段5 | `ls-stage-5.md` | Level 5（能举案例） |
| 阶段6 | `ls-stage-6.md` | Level 6（能说极限和坑） |
| 阶段7 | `ls-stage-7.md` | Level 7（能延伸设计） |

---

## 精通流程执行顺序

```
开始精通流程
    ↓
阶段5：加载 ls-stage-5.md → 执行 → 完成
    ↓
阶段6：加载 ls-stage-6.md → 执行 → 完成
    ↓
阶段7：加载 ls-stage-7.md → 执行 → 完成
    ↓
精通流程完成
```
