# 模拟面试执行模块

> 模块：cm-mock-interview  
> 用途：执行模拟面试的核心逻辑  
> 依赖：轮次SOP, cm-diagnosis.md, cm-learning-system-connector.md

---

## 一、模块概述

本模块负责模拟面试的执行，包括抽题、提问、追问、评分。

---

## 二、执行流程

```
1. 加载题库（从data/questions/或动态生成）
2. 优先抽取诊断报告中的薄弱Level题目
3. 按轮次要求的Level比例补充题目
4. AI面试官逐题提问
5. 用户回答后，AI进行追问
6. 记录回答质量、追问链路
7. 计算得分，写入mock-history/
```

---

## 三、追问机制

| 回答质量 | AI行为 |
|----------|--------|
| 优秀 | 追问更深层（不超过max_follow_up_depth） |
| 一般 | 追问澄清 |
| 差 | 记录卡点，跳到下一题 |

---

## 四、评分维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 关键词覆盖度 | 50% | 对比题库standard_answer |
| 回答深度 | 30% | 追问层级 |
| 逻辑连贯性 | 20% | 表达是否清晰 |

---

## 五、输出格式

```json
{
  "mock_id": "mock-{date}-{seq}",
  "round": 1,
  "knowledge_id": "kotlin-coroutine",
  "date": "2026-05-06T10:00:00Z",
  "duration_minutes": 30,
  "questions_asked": [
    {
      "question_id": "kc_l4_001",
      "level": 4,
      "question": "协程挂起的实现原理是什么？",
      "user_answer": "...",
      "answer_quality": "good",
      "response_time_seconds": 15,
      "keyword_coverage": 0.8,
      "follow_ups": [...]
    }
  ],
  "summary": {
    "total_questions": 10,
    "passed": 8,
    "score": 82
  }
}
```

---

## 六、题库持久化

每次获取题库后，持久化到：
```
data/questions/{knowledge_id}/level-{1-7}.json
```

下次面试直接读取，无需重新生成。

---

> 本模块由各轮次SOP在Step 2调用