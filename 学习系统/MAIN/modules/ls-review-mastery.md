---
module: ls-review-mastery
parent: ls-review-flow
description: L5-L7 精通复习规则——自评+验证+产出
load_when: 精通流程完成后触发精通复习时加载
depends: [ls-data-structure, LLM-WIKI]
---

# 精通复习规则

## 触发条件

```
mastery_path.status == "completed"
且执行 CLI：python3 learning.py review get_mastery_status <id> 检查 next_review <= 今天
```

## 复习步骤

### 步骤 M1：加载知识

```
LLM-WIKI QUERY "{knowledge_id}" → 获取 entity 页完整内容
执行 CLI：python3 learning.py progress get <id> 获取 mastery_path 的 stage_progress
```

### 步骤 M2：逐 Level 验证

| Level | 验证内容 | 方式 | 时间 |
|-------|---------|------|------|
| **L5** | 实战案例 | 用户口述 2-3 个自己整理的案例 | 5 分钟 |
| **L6** | 边界认知 | 问卷："这个知识的极限在哪？什么时候不该用？有哪些坑？" | 3 分钟 |
| **L7** | 架构思考 | 出一道架构设计题（如"设计一个需要 volatile 的高并发场景"） | 7 分钟 |

### 步骤 M3：自评 + 验证

```
每个 Level 验证后：
  → 用户自评：流畅 / 大概 / 忘了
  → "流畅" → 标记 Level 保持
  → "大概" → 提示回顾 entity 页对应章节，不做惩罚
  → "忘了" → 提示重新整理，下次精通复习前补上
```

### 步骤 M4：更新

```
执行 CLI：python3 learning.py review enable_mastery <id>
  mastery_review.last_review = 今天
  mastery_review.next_review = 今天 + 30 天
执行 CLI：python3 learning.py review record_mastery <id>
  追加 mastery_review 记录
```

## 复习间隔

精通复习每 30 天触发一次。无质量自适应（精通级不需要间隔调优）。
