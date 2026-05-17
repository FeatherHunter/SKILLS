# 面试精通系统 - 主流程SOP

> 版本：V2  
> 依赖：cm-learning-system-connector.md, cm-diagnosis.md, cm-mock-interview.md, cm-feedback-generator.md, cm-readiness-checker.md, template-final-report.md

---

## 一、入口触发

**触发词**：
- "我要面试" / "准备面试" / "开始面试训练"
- "准备XXX面试"（指定知识点）
- "模拟面试XXX" / "来一次模拟面试"

---

## 二、主流程SOP（含checkbox）

```
+------------------------------------------------------------------+
|                    面试精通系统 - 主流程SOP                        |
+------------------------------------------------------------------+
|                                                                  |
|  【Step 0: 前置检查 - 必须逐项确认】                             |
|    [ ] 检查 learning-system 目录可访问                          |
|    [ ] 检查 LLM-WIKI skill 可用                                  |
|    [ ] 检查 LLM-WIKI wiki/ 目录存在                              |
|    [ ] 检查 interview-system/data/ 目录存在                     |
|    [ ] 检查 SOPs/rounds/ 目录下5个轮次md文件完整性              |
|    [ ] 检查 SOPs/core-modules/ 目录下6个模块md文件完整性        |
|    [ ] 检查 interviewer-personas/ 目录下6个角色md文件完整性     |
|    [ ] 检查 templates/ 目录下4个模板md文件完整性                |
|    [ ] 加载 LLM-WIKI skill（如失败则报错）                       |
|                                                                  |
|  【Step 1: 学习状态检测 + 诊断测试】                             |
|    - 调用 cm-learning-system-connector.md                       |
|    - 读取 D:\2Study\StudyNotes\2026\learning-system\progress.json |
|    - 读取 D:\2Study\StudyNotes\2026\learning-system\knowledge-list.json |
|    - 识别哪些知识点已达到 L4+（可面试状态）                      |
|    - 调用 cm-diagnosis.md 进行 Level 1-7 分层诊断                |
|    - 识别每知识点的薄弱Level                                     |
|    - 生成诊断报告写入 data/diagnosis-history.json               |
|                                                                  |
|  [ ] Step 1 完成：诊断报告已生成                                 |
|                                                                  |
|  【Step 2: 目标设定】                                            |
|    - 用户选择目标公司/岗位（可选，用于定制化）                   |
|    - 用户选择目标轮次（可多选，默认全选：1-5面）                 |
|    - （注意：角色Soul在每个轮次执行时单独选择）                  |
|                                                                  |
|  [ ] Step 2 完成：目标已设定                                    |
|                                                                  |
|  【Step 3: 轮次执行循环】                                        |
|                                                                  |
|    For round in selected_rounds:                                |
|      [ ] 开始执行轮次：{round_name}                              |
|      |                                                            |
|      |  调用对应轮次SOP文件：                                     |
|      |  - round-1-technical.md (一面)                            |
|      |  - round-2-deep.md (二面)                                 |
|      |  - round-3-architecture.md (三面)                        |
|      |  - round-4-cross.md (四面)                               |
|      |  - round-5-executive.md (五面)                           |
|      |                                                            |
|      |  轮次流程执行：                                           |
|      |  1. 角色Soul选择（系统推荐2个，用户确认或自定义）          |
|      |  2. 题库准备（使用诊断报告结果，持久化到data/questions/） |
|      |  3. 模拟面试（优先薄弱Level题目）                          |
|      |  4. 反馈生成（结合诊断结果，指向learning-system）          |
|      |                                                            |
|      |  [ ] 轮次 {round_name} 执行完成                          |
|      |                                                            |
|    End For                                                       |
|                                                                  |
|  [ ] Step 3 完成：所有选定轮次已执行                            |
|                                                                  |
|  【Step 4: 综合判定】                                            |
|    - 调用 cm-readiness-checker.md                                |
|    - 判定是否达到"面试就绪"标准                                  |
|    - 生成「就绪判定报告」                                        |
|    - 如未就绪（五项有一项不��足），生成「缺失报告」              |
|      （重要：不阻断流程，用户可选择继续或停止）                  |
|                                                                  |
|  [ ] Step 4 完成：综合判定已生成                                |
|                                                                  |
|  【Step 5: 生成最终报告】                                        |
|    - 调用 template-final-report.md                               |
|    - 输出完整版反馈报告（详细分析+补强计划+话术建议）            |
|    - 写入 reports/final-reports/                                |
|                                                                  |
|  [ ] Step 5 完成：最终报告已生成                                |
|                                                                  |
|  【输出】                                                        |
|    [x] 诊断报告（data/diagnosis-history.json）                  |
|    [x] 面试准备进度（data/progress.json）                        |
|    [x] 每轮模拟记录（data/mock-history/）                        |
|    [x] 每轮反馈（data/feedback/）                                |
|    [x] 最终报告（reports/final-reports/）                       |
|    [x] 补强建议（供学习系统读取）                                |
|                                                                  |
+------------------------------------------------------------------+
```

---

## 三、调用关系

```
main-flow.md
    │
    ├─ Step 0 → 检查前置条件
    │
    ├─ Step 1 → cm-learning-system-connector.md
    │           └─→ cm-diagnosis.md
    │
    ├─ Step 2 → 用户输入目标设定
    │
    ├─ Step 3 → rounds/round-*.md (循环)
    │              │
    │              ├─ 角色Soul选择
    │              ├─ cm-mock-interview.md
    │              └─ cm-feedback-generator.md
    │
    ├─ Step 4 → cm-readiness-checker.md
    │
    └─ Step 5 → template-final-report.md
```

---

## 四、错误处理

| 场景 | 处理 |
|------|------|
| LLM-WIKI未找到 | **报错**，停止流程 |
| learning-system无数据 | 继续流程，诊断结果为空 |
| 轮次SOP文件不存在 | 报错，提示缺少文件 |

---

## 五、就绪判定标准

五项标准**必须全部满足**才算就绪，但**不阻断流程**：

| # | 标准 | 说明 |
|---|------|------|
| 1 | 知识深度达标 | 对应轮次的Level要求 |
| 2 | 模拟通过率>=95% | 5轮平均>=90分，每轮>=85分 |
| 3 | 无待处理反馈 | 所有反馈状态为resolved |
| 4 | STAR案例>=3个 | 已验证的案例 |
| 5 | 压力测试通过（可选） | 用户开启时执行 |

---

> 本SOP是面试系统的主入口，由用户触发词激活