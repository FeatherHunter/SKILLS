# 完整反馈报告模板

> 用途：每轮反馈详情  
> 依赖：cm-feedback-generator.md

---

## 一、模板结构

```json
{
  "feedback_id": "fb-{date}-{seq}",
  "created_at": "{ISO8601}",
  "updated_at": "{ISO8601}",
  "source": "mock_interview",
  "round": 1,
  "knowledge_id": "{knowledge_id}",
  
  "status": "pending/acknowledged/actioned/resolved",
  "status_history": [
    {"status": "pending", "at": "{ISO8601}"},
    {"status": "acknowledged", "at": "{ISO8601}"}
  ],
  "expires_at": "{ISO8601}",
  
  "mock_summary": {
    "total_questions": 10,
    "passed_questions": 8,
    "score": 82,
    "weak_levels": [4, 5]
  },
  
  "blocking_points": [
    {
      "sequence": 1,
      "question": "协程挂起的实现原理",
      "level": 4,
      "question_path": [
        "什么是挂起函数",
        "挂起是怎么实现的",
        "状态机是怎么生成的",
        "状态机具体实现代���"
      ],
      "blocked_at_depth": 4,
      "blocked_at": "状态机具体实现代码",
      "user_answer": "协程挂起就是...",
      "ai_diagnosis": {
        "primary_reason": "细节掌握不足",
        "confidence": 0.8,
        "evidence": [
          "关键词覆盖率45%，低于阈值50%",
          "追问到状态机细节时卡住"
        ]
      }
    }
  ],
  
  "reinforcement_plan": [
    {
      "topic": "状态机源码实现",
      "target_level": 4,
      "priority_score": 15,
      "reason": "高频面试题，连续2次卡住",
      "reinforcement_source": "learning-system 阶段4",
      "action": "进入learning-system阶段4源码研读"
    }
  ],
  
  "user_response": {
    "acknowledged_at": "{ISO8601}",
    "acknowledged_message": "好的，我会重点补状态机源码"
  }
}
```

---

## 二、使用说明

1. 本模板由cm-feedback-generator.md调用生成
2. 写入路径：data/feedback/
3. 状态机流转：pending -> acknowledged -> actioned -> resolved
4. 补强建议直接指向learning-system的具体阶段

---

> 本模板由cm-feedback-generator.md使用