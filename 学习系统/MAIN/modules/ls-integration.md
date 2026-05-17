---
module: ls-integration
parent: learning-system-main
description: 能力整合层 — 将多个已掌握或随机抽取的知识点组合，解决真实场景的系统设计问题。两种模式：已知域整合（模式一）+ 探索域整合（模式二）。
load_when: 用户请求综合练习/系统设计题/随机挑战时加载
depends: [ls-data-structure, LLM-WIKI]
---

# 能力整合层

**定位**：单知识点学习（L1-L7）的"组合练习层"。验证你是否能将 N 个独立知识串联成一个完整的系统设计方案。这是从"知道很多点"到"能做一个系统"的关键一步。

---

## 一、两种模式

| | 模式一：已知域整合 | 模式二：探索域整合 |
|---|---|---|
| **触发词** | "综合练习" / "系统设计题" / "给我一道大题" | "随机挑战" / "随机出题" / "来道开放题" |
| **选点策略** | 执行 CLI：python3 learning.py progress get <id> 筛选 L4+ 知识点 | 从 Wiki entity 列表中随机抽取 |
| **出题逻辑** | 选 3-6 个已完成知识点，判断能否构成有意义的系统设计题 | 随机抽 4-6 个，判断能否构成有意义的题；告知哪些未学 |
| **产物** | 系统设计方案 + 设计决策树 | 系统设计方案 + 设计决策树 + 待补知识清单 |

### 模式一流程

```
用户说"综合练习"
        ↓
1. 执行 CLI：python3 learning.py knowledge list + progress get 读取
2. 筛选 foundation_path.status == "completed" 的知识点
3. 按 category 分组，确保跨领域选题
4. 选 3-6 个不同 category 的知识点
5. 调用 LLM-WIKI QUERY 获取各知识点的核心能力
6. 判断能否构成有意义的系统设计题：
   - 能 → 构造题目
   - 不能 → 重新选（最多 3 次）
7. 展示题目 + 涉及的知识点列表
8. 用户答题
9. AI 评价 + 对比 Wiki 参考方案
10. 执行 CLI：python3 learning.py integration update_solution <id> '<summary>' '<json>'
```

### 模式二流程

```
用户说"随机挑战"
        ↓
1. AI 读取 Wiki index.md，获取所有 entity 列表
2. 随机抽取 4-6 个 entity
3. 调用 LLM-WIKI QUERY 获取各 entity 的核心能力
4. 判断能否构成有意义的系统设计题：
   - 能 → 检查哪些是用户未学过的
   - 不能 → 重新抽（最多 3 次）
5. 展示题目：
   - 标注"已学知识点"（绿色）
   - 标注"未学知识点"（橙色）+ 简要说明其核心能力
   - "这些未学知识不影响答题，如果答完后想学，可以从这里开始"
6. 用户答题
7. AI 评价 + 对比 Wiki 参考方案
8. 如果用户对未学知识感兴趣 → 进入 3.3 学习新知识流程
9. 执行 CLI：python3 learning.py integration update_solution <id> '<summary>' '<json>'
```

---

## 二、出题规则

### 2.1 知识点选择要求

| 规则 | 说明 |
|------|------|
| **跨 category** | 选到的知识点必须来自 ≥ 2 个不同的 category（如1个Framework + 1个优化 + 1个网络） |
| **有交集场景** | 存在一个真实的系统设计场景，解决它必须同时用到选到的知识点 |
| **不可硬凑** | AI 判断无法构成有意义的题 → 重新选。声明"这组知识点无法构成设计题，重新选" |
| **优先已有案例** | 如果选到的某个知识点已有 STAR 案例卡，优先从该案例展开题目 |

### 2.2 题目模板

```markdown
## 系统设计题：[题目名称]

**场景描述**：[2-3 句话描述业务背景，真实感要强]

**核心需求**：
1. [需求1]
2. [需求2]
3. [需求3]

**技术约束**：
- [约束1：如"日活 500 万，QPS 峰值 2 万"]
- [约束2：如"需要兼容 Android 8.0+"]
- [约束3：如"不能引入超过 2 个三方库"]

**涉及的知识领域**：
- ✅ [已学] [知识A]：[一句话说明为什么这道题需要它]
- ✅ [已学] [知识B]：...
- ⚠️ [未学] [知识C]（仅模式二出现）：...

**答题要求**：
1. 画出系统架构图（文字描述即可）
2. 说出 3 个以上的关键设计决策及 trade-off
3. 指出你认为最容易出问题的 2 个地方

**预期讨论时长**：15-20 分钟
```

### 2.3 题目有效性检查

AI 在出题前必须自检：

```
检查点：
☐ 场景真实吗？（不是学院派习题，是实际项目会遇到的）
☐ 需要 N 个知识点才能完整回答吗？
☐ 有开放式余地吗？（不只一个正确答案）
☐ 能引出一组 trade-off 讨论吗？
☐ 用户能在 15 分钟内给出基本方案吗？

任意"否" → 重新构造题目
```

---

## 三、评分与反馈

### 3.1 评分维度

| 维度 | 权重 | 评估方式 |
|------|------|---------|
| **方案完整性** | 30% | 是否覆盖了所有核心需求 |
| **技术选型合理性** | 25% | 选型理由是否站得住脚，是否考虑了替代方案 |
| **Trade-off 分析** | 25% | 是否识别出 3 个以上的权衡点并给出选择理由 |
| **边界意识** | 20% | 是否说出方案的局限、不适合的场景、潜在风险 |

### 3.2 反馈模板

```markdown
## 答题反馈

**得分**：[X]/100

### 做得好的
1. [具体的点1]
2. [具体的点2]

### 没考虑到的
1. [漏掉的 trade-off 1]：[为什么重要]
2. [漏掉的 trade-off 2]：[为什么重要]
3. [边界情况]：[什么场景这个方案会出问题]

### 维基参考方案
[调用 LLM-WIKI QUERY 获取相关知识点的架构设计参考，不是标准答案，而是展示其他可能的方向]

### 建议
- 如果对这个话题感兴趣，可以深入：[相关知识点1]、[相关知识点2]
- 推荐练习：[类似的系统设计题方向]
```

---

## 四、数据结构

### 4.1 `integration_scenario` 表

```
D:/2Study/StudyNotes/2026/learning-system/
└── 执行 CLI：python3 learning.py integration list/update_solution
```

```json
{
  "version": "1.0",
  "history": [
    {
      "id": "int-001",
      "scenario": "设计一个消息推送系统",
      "mode": "known",
      "knowledge_used": ["android-binder", "java-threadpool", "android-lifecycle"],
      "knowledge_unlearned": [],
      "knowledge_unlearned_explanations": {},
      "created_at": "2026-05-06T15:00:00+08:00",
      "difficulty": "architect",
      "user_solution_summary": "采用长连接 + 本地持久化 + 分级推送策略...",
      "ai_feedback": {
        "score": 78,
        "strengths": ["清晰的架构分层", "考虑了离线消息"],
        "weak_areas": ["未考虑推送通道降级", "未评估电量影响"],
        "missed_tradeoffs": ["长连接 vs 轮询的取舍未量化"]
      },
      "unlearned_interest": null
    }
  ]
}
```

### 4.2 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 唯一标识，自增编号 |
| scenario | string | 题目名称 |
| mode | string | "known"（模式一）或 "explore"（模式二） |
| knowledge_used | array | 题目中使用的知识点ID列表 |
| knowledge_unlearned | array | 模式二中标为未学的知识点ID |
| knowledge_unlearned_explanations | object | key=knowledge_id，value=该知识简要说明 |
| difficulty | string | "senior"（高级工程师）或 "architect"（架构师） |
| user_solution_summary | string | 用户方案的简要概括 |
| ai_feedback.score | number | 综合评分 0-100 |
| ai_feedback.strengths | array | 做得好的点 |
| ai_feedback.weak_areas | array | 薄弱点 |
| ai_feedback.missed_tradeoffs | array | 遗漏的权衡维度 |
| unlearned_interest | array or null | 用户表示想学的未学知识点ID列表 |

---

## 五、后续流程

### 5.1 从反馈到学习

答题后如果发现明显薄弱点或对未学知识感兴趣：

```
用户说"我想先学 [知识X]"
    ↓
进入 learning-system-main 3.3 学习新知识流程
（如果知识X存在但 level=0，直接开始学习）
```

### 5.2 从练习到面试

模式一完成的系统设计题，可被面试叙事层引用。特别是：
- 如果某题得分 >= 80，建议将其方案转为 L7 的 ADR 素材
- 如果某题得分 < 60，该题涉及的知识点全部置为薄弱，优先复习

---

## 六、与 LLM-WIKI 联动

| 步骤 | LLM-WIKI 操作 | 说明 |
|------|--------------|------|
| 选点时 | QUERY（search） | 通过 wiki index 查找 entity 列表 |
| 构造题目时 | QUERY 各知识点 | 获取核心设计要点和边界数据 |
| 生成参考方案时 | QUERY 相关知识 | 获取 wiki 中的架构参考 |
| 发现新见解时 | INGEST | 如果用户方案中包含 wiki 未覆盖的洞见，写入 raw |
| 建立关联时 | INGEST（UPDATE entity） | 将练习中发现的新关联写入 related_to |
