---
module: ls-mastery-flow
parent: learning-system-main
description: 精通流程（阶段5-7）协调器
load_when: 用户开始精通流程时加载
depends: [ls-data-structure, LLM-WIKI]
---

# 精通流程（Mastery Path）

## 执行顺序

```
开始精通流程
    ↓
阶段5：加载 ls-stage-5.md → 执行 → 完成
    ↓
阶段6：加载 ls-stage-6.md → 执行 → 完成
    ↓
阶段7：加载 ls-stage-7.md → 执行 → 完成
    ↓
精通流程完成
```

---

## 各阶段文件索引

| 阶段 | 文件 | 目标 | Level | 面试层级 |
|------|------|------|-------|---------|
| 阶段5 | `ls-stage-5.md` | 实战深化 | L5 | 中级面试 |
| 阶段6 | `ls-stage-6.md` | 边界探索 | L6 | 高级面试 |
| 阶段7 | `ls-stage-7.md` | 迁移设计 | L7 | 架构师面试 |

**完成后达到**：Level 7（架构思考）

---

## 补全机制

进入精通流程前，检查基础学习是否完成：
- 检查阶段1-4是否全部完成（foundation_path.stage_progress.stage_X.status == "completed"）
- 全部完成 → 进入阶段5
- 有未完成阶段 → 提示"请先完成基础学习流程"，流程结束

---
