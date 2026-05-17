# 诊断测试模块

> 模块：cm-diagnosis  
> 用途：对知识点进行Level 1-7分层诊断测试  
> 依赖：cm-learning-system-connector.md, LLM-WIKI

---

## 一、模块概述

本模块在主流程Step 1调用，对用户掌握的知识点进行分层诊断，识别薄弱Level。

---

## 二、诊断流程

```
1. 读取learning-system/progress.json
2. 筛选已学习的知识点（Level > 0）
3. 对每个知识点进行Level 1-7分层测试
4. 识别每知识点的薄弱Level
5. 生成诊断报告
```

---

## 三、诊断方式

| Level | 诊断方式 | 通过标准 |
|-------|----------|----------|
| L1 | 概念题（是什么） | 能准确说定义 |
| L2 | 使用题（怎么用） | 能说出API用法 |
| L3 | 原理题（为什么） | 能说清原理 |
| L4 | 实现题（怎么实现） | 能说源码或原理推导 |
| L5 | 实战题（案例） | 能举真实项目案例 |
| L6 | 边界题（极限和坑） | 能说性能极限和踩坑经历 |
| L7 | 架构题（延伸设计） | 能做设计延伸 |

---

## 四、输出格式

```json
{
  "diagnosis_id": "diag-{date}-{seq}",
  "knowledge_id": "kotlin-coroutine",
  "date": "2026-05-06T10:00:00Z",
  "levels": {
    "level_1": {"tested": true, "passed": true, "score": 90},
    "level_2": {"tested": true, "passed": true, "score": 85},
    "level_3": {"tested": true, "passed": true, "score": 75},
    "level_4": {"tested": true, "passed": false, "score": 40, "weak_points": ["状态机源码"]},
    "level_5": {"tested": true, "passed": false, "score": 30, "weak_points": ["项目案例不足"]},
    "level_6": {"tested": false, "passed": false, "score": 0},
    "level_7": {"tested": false, "passed": false, "score": 0}
  },
  "weak_levels": [4, 5],
  "diagnosis_summary": "实现理解和实战经验是薄弱点"
}
```

---

## 五、使用场景

- 主流程Step 1：生成诊断报告
- 轮次流程Step 1：读取诊断结果，优先抽取薄弱Level题目
- 反馈生成：结合诊断结果生成精准补强建议

---

> 本模块由main-flow.md在Step 1调用