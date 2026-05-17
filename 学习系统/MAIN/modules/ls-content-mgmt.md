---
module: ls-content-mgmt
parent: learning-system-main
description: 知识点内容生成规则、现有笔记整合
load_when: 首次生成知识点内容时加载
depends: [ls-data-structure, LLM-WIKI]
---

# 知识点内容生成规则



## 首次生成

**触发条件**：用户首次请求学习某知识点，LLM-WIKI 中无此知识点

**内容来源**：
1. 用户提供的个人笔记/文档（交互式获取）
2. AI网络搜索（最后兜底）

**生成流程**：

```
        用户请求学习某知识点
                   ↓
        执行 LLM-WIKI Query 操作
                   ↓
           知识点是否存在？
                   ↓
          ┌────────┴────────┐
          ↓                 ↓
         否                 是
          ↓                 ↓
     首次生成        加载 ls-learning-flow.md
          ↓
   询问用户提供资料（个人笔记/文档/链接）
                   ↓
          ┌────────┴────────┐
          ↓                 ↓
         有                 无
          ↓                 ↓
          ↓          AI 搜索资料
          ↓                 ↓
          ↓         审查 + 质量提升
          ↓                 ↓
          └────────┬────────┘
                   ↓
        执行 LLM-WIKI Ingest 操作
                   ↓
        加载 ls-learning-flow.md 开始学习
```

**注意**：
- 内容生成通过 LLM-WIKI Ingest 操作完成
- learning-system 不直接操作 LLM-WIKI 内部






