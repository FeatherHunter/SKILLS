# 最终报告模板

> 用途：完整版反馈报告（8-12页）  
> 依赖：template-diagnosis.md, template-mock-record.md, template-feedback.md

---

## 一、报告结构

### 1. 执行摘要（1页）
- 总得分、各轮表现概览、就绪状态
- 关键指标一览

### 2. 详细分析（3-5页）
- 每轮每个问题的分析
- 追问链路还原
- 卡点诊断详情

### 3. 补强计划（2-3页）
- 优先级排序
- 直接指向 learning-system 的具体阶段
- 预计补强时间
- 学习路径建议

### 4. 话术建议（1-2页）
- 每个薄弱点的回答话术
- 过渡技巧
- 不会回答时的应对策略
- STAR案例讲述技巧

### 5. 面试前检查清单（1页）
- 面试当天准备事项
- 心态调整建议
- 常见问题快速回顾

---

## 二、模板结构

```json
{
  "report_id": "fr-{date}-{seq}",
  "created_at": "{ISO8601}",
  "report_type": "final",
  
  "executive_summary": {
    "total_score": 82,
    "rounds_completed": 5,
    "readiness_status": "就绪/未就绪",
    "key_strengths": ["L1-L3掌握良好"],
    "key_weaknesses": ["状态机源码", "项目案例"]
  },
  
  "detailed_analysis": {
    "round_1": {
      "score": 85,
      "passed": true,
      "questions_analysis": [...],
      "weak_points": [...]
    },
    "round_2": {...},
    "round_3": {...},
    "round_4": {...},
    "round_5": {...}
  },
  
  "reinforcement_plan": {
    "priority_1": {
      "topic": "状态机源码实现",
      "target_level": 4,
      "source": "learning-system阶段4",
      "estimated_time": "2小时",
      "action_steps": [...]
    },
    "priority_2": {...},
    "priority_3": {...}
  },
  
  "speech_suggestions": {
    "weak_point_1": {
      "question": "协程挂起的实现原理",
      "suggested_answer": "协程挂起通过Continuation接口...",
      "transitions": [
        "说到挂起，我之前在项目中遇到过...",
        "这个原理让我想到..."
      ],
      "fallback": "坦白承认不熟悉，但展示学习意愿"
    }
  },
  
  "pre_interview_checklist": {
    "day_before": [
      "复习L1-L4核心概念",
      "准备好2-3个STAR案例",
      "确认面试时间和平台"
    ],
    "day_of": [
      "提前30分钟进入面试间",
      "准备好水和纸巾",
      "保持放松心态"
    ],
    "mindset": [
      "自信但不自负",
      "诚实承认不会",
      "展示学习意愿"
    ]
  }
}
```

---

## 三、使用说明

1. 本模板由main-flow.md在Step 5调用
2. 写入路径：reports/final-reports/
3. 格式：JSON + 可选Markdown版本
4. 供学习系统解析读取补强建议

---

> 本模板由main-flow.md在Step 5使用