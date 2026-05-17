---
module: ls-review-writeback
parent: ls-review-flow
description: 复习后精华写回 Wiki 的触发条件
load_when: 复习流程 SOP 步骤 7 时加载
depends: [LLM-WIKI]
---

# 复习精华写回规则

## 触发条件一览

| 条件 | 写回目标 | LLM-WIKI 操作 |
|------|---------|--------------|
| 答题中用户说出不在当前 entity 页的知识 | `raw/notes/{知识}-review-discovery-{日期}.md` | INGEST |
| 用户答错/遗漏，LLM-WIKI 中缺该纠正内容 | `raw/notes/{知识}-review-gap-{日期}.md` | INGEST |
| 跨知识对比 ≥ 3 维度 + 结论明确 | `comparisons/{a}-vs-{b}.md` | INGEST |
| 答题质量高，值得存为 FAQ | `queries/{知识}-R{轮次}.md` | INGEST |
| 错题对应的薄弱点 | entity 页 frontmatter 加 `weak_point_for: {knowledge_id}` | UPDATE |
| 提炼出可复用的回答模式 | `concepts/{概念名}.md`（需用户确认后才建） | INGEST |

## 判断详细规则

### 1. 新知识 / 遗漏补充

```
条件：用户回答中包含当前 entity 页未覆盖的事实/观点/细节
动作：创建 raw/notes/{知识}-review-discovery-{日期}.md
内容：用户原话 + 对应的题目 + AI 补充说明
后续：不立即升级到 entity 页；下次学该知识点时 AI 提示"有未消化的发现"
```

### 2. 跨知识对比

```
条件：
  - 执行 CLI：python3 learning.py progress get <id> 确认知识点 A 和 B 都有记录
  - 对比维度 >= 3
  - 有明确的选择建议或结论
动作：创建 comparisons/{a}-vs-{b}.md
不满足条件：内容写进 queries/ 而非 comparisons/
```

### 3. FAQ 问答

```
条件：用户回答质量自评"流畅"，且 LLM-WIKI 当前无类似问答
动作：创建 queries/{知识}-R{轮次}.md
格式：
  # 问题：[原题]
  ## 回答：[用户答案 + AI 补充]
内容简短（< 200 行）即存；超长则精简。
```

### 4. 薄弱点标记

```
条件：错题 topic 明确，且该 topic 未在 entity 页标记过
动作：UPDATE entity 页 frontmatter，追加：
      weak_point_for: {knowledge_id}
      resolved: false
后续：下次学该知识时 AI 提示"有未解决的薄弱点"
```

### 5. 概念提炼（需用户确认）

```
条件：AI 认为可从本次答题中提炼出抽象概念
动作：提示用户，用户确认后创建 concepts/{概念名}.md
不确认：丢弃
```
