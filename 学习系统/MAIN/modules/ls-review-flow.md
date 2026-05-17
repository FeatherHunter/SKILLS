---
module: ls-review-flow
parent: learning-system-main
description: 复习流程主 SOP——轮次设计 + 执行步骤 + 质量自适应
load_when: 用户复习知识点时加载
depends: [ls-data-structure, LLM-WIKI, ls-review-basic, ls-review-mastery, ls-review-writeback]
---

# 复习流程

## 一、轮次设计

| 轮次 | 间隔 | 目标 |
|------|------|------|
| R1 | 1 天 | 快速回忆，防止 24h 遗忘 |
| R2 | 3 天 | 综合应用 |
| R3 | 7 天 | 深度分析 |
| R4 | 14 天 | 实战挑战 |
| R5 | 30 天 | 知识整合 |

## 二、执行步骤（SOP）

AI 必须按编号顺序执行。每步完成才可进入下一步。

### 步骤 1：读取复习计划

```
1.1 执行 CLI：python3 learning.py review get_schedule <id>
1.2 找 scheduled_date <= 今天 且 status == "pending" 的条
1.3 展示给用户，格式：知识名 | 轮次 | 计划日期 | 状态
1.4 用户选择本次复习的知识点
```

### 步骤 2：获取知识内容

```
2.1 LLM-WIKI QUERY "{knowledge_id}"
    → 获取该知识的 entity 页 + raw notes + sources 片段
2.2 执行 CLI：python3 learning.py progress get <id>
2.3 执行 CLI：python3 learning.py review get_history <id>（最近一次 verification 中 passed=false 的 topic）
```

### 步骤 3：生成题目

```
3.1 加载 ls-review-basic.md（R1-R5 题型规则）
3.2 根据 {current_stage, current_level, 轮次} 查 stage×轮次 矩阵 → 确定题数 + 题型
3.3 AI 用 LLM-WIKI QUERY 返回的内容生成题目
```

**强制规则**：AI 不可凭空出题。每道题的内容必须来自 LLM-WIKI QUERY 返回的知识。
如 QUERY 返回的内容不足以支撑某道题，降级为较低轮次的题型，并在步骤 7 记录为"内容缺失"。

### 步骤 4：用户答题

```
4.1 选择题/填空题/解释题：用户在对话中直接答
4.2 代码题：
    a) 创建 exercises/{knowledge_id}_R{round}_{n}.{ext}
    b) 自动打开文件（Windows: start）
    c) 用户编辑 → 回复"提交"或"跳过"
4.3 AI 逐题判对错，累计分数
```

### 步骤 5：评估 + 即时验证

```
5.1 计算分数
5.2 如果错题数 < 2 → 跳到步骤 6
5.3 如果错题数 >= 2 → 触发即时验证：
    a) 问用户："现在验证"或"跳过"
    b) 验证时：
       - 逐个错题：讲解 → 问"你觉得理解了吗？"
       - 出变参验证题
       - 通过 → 下一题
       - 不通过 → 最多 3 次，3 次均失败 → 疲劳检测，问是否暂停
    c) 执行 CLI：python3 learning.py review add_verification <id> <round> '<json>'
```

### 步骤 6：更新文件

```
6.1 执行 CLI：python3 learning.py review create_schedule <id>
    - 当前轮次 status = "completed"，completed_at = 现在
    - current_round 更新
    - 下一轮 scheduled_date = 今天 + 该轮 target_day（受步骤 7 质量系数调整）
6.2 执行 CLI：python3 learning.py review add_history '<json>'
    - 追加本条复习记录（含 verification 如有）
6.3 执行 CLI：python3 learning.py progress update_stage <id> <stage> '<json>'
    - last_activity 更新
```

### 步骤 7：精华写回 Wiki

```
7.1 加载 ls-review-writeback.md
7.2 按其中触发条件判断是否需要写回：
    - 发现 LLM-WIKI 中缺失的知识 → INGEST
    - 跨知识对比（维度 >= 3）→ comparisons/
    - 有价值的问答 → queries/
    - 提炼出新概念 → concepts/
    - 新增薄弱点 → entity 页标记 weak_point_for
7.3 执行对应 LLM-WIKI 操作
```

### 步骤 8：复习完成

```
8.1 向用户展示：得分 | 薄弱点 | 写回内容
8.2 如还有到期复习未完成 → 询问"继续复习下一个？"
```

## 三、质量自适应

```
如果 score >= 90：
   下一轮 scheduled_date = 完成日 + (target_day * 1.2)
如果 score >= 70：
   下一轮 scheduled_date = 完成日 + target_day
如果 score < 70：
   下一轮 scheduled_date = 完成日 + (target_day * 0.5)
   且薄弱点标记为 weak_point_for = {knowledge_id}
```

## 四、LLM-WIKI 兜底机制

复习全程适用：

| 场景 | 动作 |
|------|------|
| QUERY 返回"未找到" | 不可继续出题。提示用户："该知识在 Wiki 中未收录，需要先 Ingest。"退出复习 |
| 答题中用户说出不在 Wiki 中的知识点 | 记录到步骤 7，标记为待 Ingest |
| 用户答错、Wiki 中缺少该错误相关的纠正内容 | 提示用户："这个错题对应知识 Wiki 未覆盖，是否先 Ingest ？" |

## 五、子模块索引

| 模块 | 加载场景 | 内容 |
|------|---------|------|
| `ls-review-basic.md` | SOP 步骤 3 | stage×轮次 题型矩阵 + 出题规则 |
| `ls-review-mastery.md` | 精通复习触发 | L5-L7 复习规则 |
| `ls-review-writeback.md` | SOP 步骤 7 | 精华写回 wiki 触发条件 |
