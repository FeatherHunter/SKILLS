# 反馈生成模块

> 模块：cm-feedback-generator  
> 用途：分析卡点原因，生成补强建议  
> 依赖：cm-mock-interview.md, cm-diagnosis.md, cm-learning-system-connector.md

---

## 一、模块概述

本模块分析模拟面试中的卡点，生成精准补强建议，直接指向learning-system的具体阶段。

---

## 二、分析维度

| 维度 | 判断方法 | 阈值 | 诊断结果 |
|------|----------|------|----------|
| 关键词覆盖度 | 对比standard_answer | <30% | 概念不熟悉 |
| 回答深度 | 追问层级 | <2层 | 理解不深入 |
| 追问响应 | 是否卡住 | 卡住 | 细节掌握不足 |
| 反应时间 | 回答耗时 | >10秒 | 熟练度不够 |

---

## 三、补强指向映射

| 薄弱表现 | 指向learning-system阶段 |
|----------|-------------------------|
| 概念不熟悉 | 阶段1：认知建构 |
| 理解不深入 | 阶段2：原理内化 |
| 实现理解不足 | 阶段2-3：实现探究/验证 |
| 实战经验不足 | 阶段5：实战深化 |
| 边界认知不足 | 阶段6：边界探索 |
| 架构思考不足 | 阶段7：迁移设计 |

---

## 四、输出格式

```json
{
  "feedback_id": "fb-{date}-{seq}",
  "created_at": "2026-05-06T10:30:00Z",
  "source": "mock_interview",
  "round": 1,
  "knowledge_id": "kotlin-coroutine",
  "blocking_points": [
    {
      "question": "协程挂起的实现原理",
      "level": 4,
      "blocked_at_depth": 3,
      "ai_diagnosis": {
        "primary_reason": "细节掌握不足",
        "confidence": 0.8
      }
    }
  ],
  "reinforcement_plan": [
    {
      "topic": "状态机源码实现",
      "target_level": 4,
      "priority_score": 15,
      "reinforcement_source": "learning-system 阶段4",
      "action": "进入learning-system阶段4源码研读"
    }
  ],
  "status": "pending"
}
```

---

## 五、反馈状态机

```
pending（待处理）
   ├→ acknowledged（用户已知晓）
   │     └→ actioned（已采取行动）
   │           └→ resolved（已解决）
   │
   └→ dismissed（用户忽略）
```

---

> 本模块由各轮次SOP在Step 3调用