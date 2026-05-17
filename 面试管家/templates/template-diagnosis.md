# 诊断报告模板

> 用途：诊断测试结果输出  
> 依赖：cm-diagnosis.md

---

## 一、模板结构

```json
{
  "diagnosis_id": "diag-{date}-{seq}",
  "knowledge_id": "{knowledge_id}",
  "date": "{ISO8601}",
  "diagnosis_type": "level_test",
  
  "knowledge_info": {
    "title": "知识点标题",
    "current_level": 4,
    "learning_source": "learning-system"
  },
  
  "levels": {
    "level_1": {
      "tested": true/false,
      "passed": true/false,
      "score": 0-100,
      "details": "具体表现"
    },
    "level_2": {...},
    "level_3": {...},
    "level_4": {...},
    "level_5": {...},
    "level_6": {...},
    "level_7": {...}
  },
  
  "weak_levels": [4, 5],
  "strong_levels": [1, 2, 3],
  
  "diagnosis_summary": "综合诊断结论",
  
  "recommendation": {
    "focus_levels": [4, 5],
    "priority_order": [
      {"level": 4, "reason": "面试高频，源码题必考"},
      {"level": 5, "reason": "中级面试必问项目经验"}
    ]
  }
}
```

---

## 二、使用说明

1. 本模板由cm-diagnosis.md调用生成
2. 写入路径：data/diagnosis-history/
3. 轮次流程读取诊断结果，优先抽取薄弱Level题目
4. 反馈生成时结合诊断结果生成精准补强建议

---

> 本模板由cm-diagnosis.md使用