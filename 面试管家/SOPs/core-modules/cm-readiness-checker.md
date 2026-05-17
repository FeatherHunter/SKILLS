# 就绪判定模块

> 模块：cm-readiness-checker  
> 用途：判定是否达到面试就绪标准  
> 依赖：cm-learning-system-connector.md, mock-history/, feedback/

---

## 一、模块概述

本模块在主流程Step 4调用，判定用户是否达到面试就绪标准。

**重要**：五项标准必须全部满足，但**不阻断流程**。

---

## 二、判定标准

| # | 标准 | 要求 | 检查方式 |
|---|------|------|----------|
| 1 | 知识深度达标 | 对应轮次Level要求 | 读取progress.json |
| 2 | 模拟通过率>=95% | 5轮平均>=90分，每轮>=85分 | 统计mock-history/ |
| 3 | 无待处理反馈 | 所有反馈status=resolved | 遍历feedback/ |
| 4 | STAR案例>=3个 | 已验证的STAR案例 | 检查interview_assets |
| 5 | 压力测试通过（可选） | 连续追问3层不卡顿 | 用户开启时执行 |

---

## 三、判定流程

```
1. 读取learning-system/progress.json
2. 读取mock-history/中的模拟记录
3. 读取feedback/中的反馈状态
4. 逐项检查五项标准
5. 如全部���足 -> 标记"就绪"
6. 如有任何一项不满足 -> 生成"缺失报告"
7. 显示结果，但**不阻断流程**
8. 询问用户："继续训练"或"结束"
```

---

## 四、输出格式

```json
{
  "check_id": "check-{date}-{seq}",
  "date": "2026-05-06T10:00:00Z",
  "results": {
    "knowledge_depth": {"passed": true, "details": "L5达标"},
    "mock_pass_rate": {"passed": true, "details": "95%"},
    "no_pending_feedback": {"passed": true, "details": "无pending"},
    "star_cases": {"passed": false, "details": "当前2个，需要3个"},
    "pressure_test": {"passed": null, "details": "未开启"}
  },
  "overall": "未就绪",
  "gap_report": {
    "star_cases": {"current": 2, "required": 3}
  },
  "recommendation": "建议继续训练，重点补STAR案例"
}
```

---

## 五、缺失报告内容

当有标准未满足时，生成缺失报告：
- 未达标的标准列表
- 每个标准的当前状态 vs 目标状态
- 建议的补强优先级
- "继续训练"或"结束"选项

---

> 本模块由main-flow.md在Step 4调用