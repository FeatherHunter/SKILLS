# 模拟面试记录模板

> 用途：模拟面试过程记录  
> 依赖：cm-mock-interview.md

---

## 一、模板结构

```json
{
  "mock_id": "mock-{date}-{seq}",
  "round": 1,
  "knowledge_id": "{knowledge_id}",
  "date": "{ISO8601}",
  "duration_minutes": 30,
  
  "interviewer_persona": "persona-strict-inquirer",
  
  "questions_asked": [
    {
      "sequence": 1,
      "question_id": "xxx_l4_001",
      "level": 4,
      "question": "问题内容",
      "standard_answer_brief": "标准答案简要",
      "user_answer": "用户回答",
      "answer_quality": "good/medium/poor",
      "response_time_seconds": 15,
      "keyword_coverage": 0.8,
      "follow_ups": [
        {
          "depth": 1,
          "question": "追问问题",
          "user_answer": "用户回答",
          "answer_quality": "good/medium/poor"
        }
      ],
      "blocked_at_follow_up": 3,
      "blocking_detail": {
        "depth": 3,
        "question": "卡住的追问",
        "diagnosis": "knowledge_gap"
      }
    }
  ],
  
  "summary": {
    "total_questions": 10,
    "passed": 8,
    "failed": 1,
    "partial": 1,
    "score": 82,
    "by_level": {
      "level_1": {"total": 2, "passed": 2, "score": 90},
      "level_2": {"total": 2, "passed": 2, "score": 85},
      "level_3": {"total": 2, "passed": 1, "score": 70},
      "level_4": {"total": 2, "passed": 1, "score": 50},
      "level_5": {"total": 1, "passed": 0, "score": 30}
    },
    "weak_levels": [4, 5],
    "strong_levels": [1, 2, 3]
  },
  
  "feedback_generated": "fb-{date}-{seq}.json"
}
```

---

## 二、使用说明

1. 本模板由cm-mock-interview.md调用生成
2. 写入路径：data/mock-history/{knowledge_id}/
3. 记录完整面试过程，包括所有追问链路
4. 卡点信息用于反馈���成和补强建议

---

> 本模板由cm-mock-interview.md使用