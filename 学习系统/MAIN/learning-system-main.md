---
name: 学习系统
description: 通用高效学习系统 - 七阶段学习法，支持任意知识领域
---

# 通用高效学习系统

## 目录导航

一、系统概述
二、学习流程架构
三、触发条件
四、模块索引
五、LLM Wiki 知识库
六、心理学原理科普
七、快速参考

[TOC]

---

## 一、系统概述

### 适用领域

本系统支持任意知识领域的学习：
- 编程语言（Kotlin、Java、Python、Rust等）
- 技术框架（Android Framework、React、Spring等）
- 理论知识（算法、设计模式、架构原则等）
- 其他任何需要系统性学习的领域

### 核心特性

| 特性 | 说明 |
|------|------|
| **科学性** | 基于中西方心理学原理，符合认知科学 |
| **通用性** | 文件结构不随知识类型变化，元数据驱动 |
| **持久性** | SQLite数据库存储，脚本层校验，透明可控 |
| **智能性** | 自动生成复习计划，动态调整难度 |
| **分层性** | 基础流程达到Level 4，精通流程达到Level 7 |
| **交互性** | 采访式、诊断式、验证式、反思式学习 |

### 与面试系统的对接

**接口**：通过 scripts 调用数据库，不直接读写 JSON 文件

**脚本调用**：所有数据操作通过 `learning.py` CLI 调用 scripts

```bash
# 查询知识点进度
python3 learning.py progress get <knowledge_id>

# 查询可面试知识列表
python3 learning.py knowledge list
```

**面试系统典型加载流程**：

```
1. 执行 CLI：python3 learning.py knowledge list 获取所有知识点元数据
2. 对每个知识点，执行 CLI：python3 learning.py progress get <id>
3. 筛选 current_level >= 4 的知识点 → 可面试列表
4. 对每个知识点，读 interview_assets：
   - star_case_path 非 null → 有一面/二面素材
   - failure_case_path 非 null → 有二面追问素材
   - adr_path 非 null → 有三面架构面素材
5. 按面试轮次组织叙事（参考《面试备战叙事引擎.md》）
6. 无素材的知识点 → 面试系统提示"需先完成L5-L7"

---

## 设计约束（AI 需强制遵守）

### 数据结构权威

`modules/ls-data-structure.md` 是数据结构设计的**唯一权威来源**。

**规则**：任何数据结构改动必须：
1. 先修改 `modules/ls-data-structure.md`
2. 再修改其他引用该结构的文件

### 脚本调用原则

**重要**：AI 不能直接读写 JSON 文件，所有 DB 操作必须通过 scripts。

| 操作 | 正确方式 | 错误方式 |
|------|---------|---------|
| 添加知识点 | `python3 learning.py knowledge add '<json>'` | 直接写 JSON |
| 更新进度 | `python3 learning.py progress update_stage <id> <stage> '<json>'` | 直接改 JSON |
| 查询进度 | `python3 learning.py progress get <id>` | 直接读 JSON |
| 复习操作 | `python3 learning.py review complete_round <id> <round> <score>` | 直接改 JSON |

### 安全检查（AI 自动执行）

在阅读任何 `.md` 文件时，同步检查是否与 `ls-data-structure.md` 定义的字段存在冲突：

| 冲突类型 | 检测规则 | 处理方式 |
|---------|---------|---------|
| 字段名冲突 | 存在同名不同义的字段 | **立即报警**，提示用户 |
| 字段类型冲突 | 存在同名不同类型 | **立即报警**，提示用户 |
| 路径冲突 | 存在不一致的目录/文件路径 | **立即报警**，提示用户 |
| 命名冲突 | 存在与数据结构文件重复的定义 | **立即报警**，提示用户 |

**触发时机**：每次加载 skill 时自动执行，无需用户触发。

---



## 二、学习流程架构

### 双流程设计

```
learning-system
│
├── 基础学习流程（Foundation Path）
│   ├── 阶段1：认知建构 → Level 1
│   ├── 阶段2：实践应用 → Level 2
│   ├── 阶段3：原理内化 → Level 3 + Level 4部分
│   └── 阶段4：实现理解 → Level 4
│   │
│   └── 完成后达到：Level 4（能说怎么实现）
│
└── 精通流程（Mastery Path）
    ├── 阶段5：实战深化 → Level 5
    ├── 阶段6：边界探索 → Level 6
    └── 阶段7：迁移设计 → Level 7
    │
    └── 完成后达到：Level 7（架构思考）
```

### 七阶段总览

| 阶段 | 流程 | 目标Level | 能力产出 | 核心心理学技巧 | 步骤数 |
|------|------|-----------|----------|---------------|--------|
| 阶段1 | 基础 | L1 | 能说是什么 | 组块化、双重编码、预测试 | 4步 |
| 阶段2 | 基础 | L2 | 能在项目中使用 | 情境学习、脚手架策略、渐进式任务、变式练习 | 4步 |
| 阶段3 | 基础 | L3+L4部分 | 能说为什么+了解实现 | 苏格拉底提问、对比分析、提取练习 | 5步 |
| 阶段4 | 基础 | L4 | 能说怎么实现 | 验证式学习、记忆锚点、情景编码、间隔重复 | 6步 |
| 阶段5 | 精通 | L5 | 能举案例 | 情境学习、生成效应、踩坑复盘 | - |
| 阶段6 | 精通 | L6 | 能说极限和坑 | 变式练习、错误分析、对比分析 | - |
| 阶段7 | 精通 | L7 | 能延伸设计 | 知识迁移、创新组合、提取练习 | - |

### 知识类型适配

不同知识类型在学习方式上有差异：

| 知识类型 | 例子 | 阶段3"原理探究"适配 | 阶段4"实现探究"适配 |
|----------|------|---------------------|---------------------|
| 开源库/框架 | Glide、Retrofit | 理解设计动机因果链 | 读核心类源码 |
| 语言特性 | Kotlin协程、Java并发 | 理解底层机制原理 | JDK/SDK源码分析 |
| 数据结构 | HashMap、红黑树 | 了解设计取舍原因 | 观察实现+复杂度分析 |
| 算法 | 排序、搜索 | 理解算法设计动机 | 手写+推导复杂度 |
| 设计模式 | 单例、观察者 | 分析为什么这样设计 | 典型场景应用分析 |
| 协议/标准 | HTTP、TCP/IP | 理解设计约束原因 | RFC文档+抓包验证 |

---



## 三、触发条件

### 3.1 入口总览

AI加载本文件后，根据用户输入识别入口：
【强制约束】识别入口前需要加载技能 LLM-WIKI 和 ls-data-structure.md，如果没找到该技能强制报错提醒用户，终止一切行为!

| 用户说（示例） | 识别为 |
|---------------|--------|
| 我要学XXX / 开始学习XXX / 学习XXX | 学习新知识 |
| 我要复习 / 今天要复习什么 | 复习列表 |
| 复习XXX | 复习指定知识 |
| 我要精通XXX / 继续精通XXX | 精通流程 |
| 我要精通（无XXX）/ 我可以精通什么 | 精通列表 |
| 我的学习进度 / XXX学到哪了 | 进度查询 |
| 有哪些XXX / 想学XXX相关的 | 知识探索 |
| 综合练习 / 系统设计题 / 给我一道大题 | 能力整合（模式一） |
| 随机挑战 / 随机出题 / 来道开放题 | 能力整合（模式二） |
| 其他 | 友好询问 |

**被动触发**：基础流程完成时，系统自动提示"是否继续进入精通流程？" → 进入精通流程入口

---

### 3.2 统一执行流

```
用户输入 → 识别入口（按3.1表） → 执行对应SOP → 输出结果/加载模块
```

---

### 3.3 学习新知识

**触发词**：我要学XXX / 开始学习XXX / 学习XXX / 帮我学XXX

**Step 1** 加载 `ls-data-structure.md` + `LLM-WIKI skill`

**Step 2** 执行 `LLM-WIKI QUERY "XXX"`，检查知识是否存在
- **不存在** → Step 3A
- **存在** → Step 3B

**Step 3A** 知识不存在
1. 加载 `ls-content-mgmt.md`
2. 执行 Ingest 创建知识点
3. 执行 CLI：`python3 learning.py progress init <knowledge_id>` 初始化进度
4. 加载 `ls-learning-flow.md` → 进入阶段1学习

**Step 3B** 知识存在
1. 执行 `LLM-WIKI QUERY "XXX"` 获取该知识的所有子知识
2. 执行 CLI：`python3 learning.py knowledge list` 获取所有知识点元数据
3. 对每个子知识：
   - 在 DB 中已存在且 `level > 0` → **跳过**（已学过，不动）
   - 在 DB 中已存在且 `level == 0` → **跳过**（已是待学，不动）
   - 在 DB 中不存在 → **跳过**（进度初始化在 Step 5 做）
4. 展示所有子知识列表（标注哪些已学、哪些待学）
5. 用户选择一个
6. 执行 CLI：`python3 learning.py progress init <knowledge_id>` 初始化进度（如果尚未初始化）
7. 加载 `ls-learning-flow.md` → 从阶段1开始该子知识

---

### 3.4 复习列表

**触发词**：我要复习 / 今天要复习什么

**Step 1** 加载 `ls-data-structure.md` + `LLM-WIKI skill`

**Step 2** 执行 CLI：`python3 learning.py review get_due` 获取今日到期的复习任务
- 显示：知识名称、到期日期、轮次

**Step 3** 用户选择 → 加载 `ls-review-flow.md` → 执行复习流程

---

### 3.5 复习指定知识

**触发词**：复习XXX

**Step 1** 加载 `ls-review-flow.md` + `ls-data-structure.md` + `LLM-WIKI skill`

**Step 2** 执行 `LLM-WIKI QUERY "XXX"`，获取知识内容

**Step 3** 执行 CLI：`python3 learning.py review get_history <knowledge_id>` 获取复习历史

**Step 4** 执行复习流程

---

### 3.6 精通流程

**触发词（主动）**：我要精通XXX / 继续精通XXX / 开始精通流程
**触发词（被动）**：基础流程完成时系统提示"是否继续进入精通流程？"

**Step 1** 加载 `ls-mastery-flow.md` + `ls-data-structure.md` + `LLM-WIKI skill`

**Step 2** 执行 CLI：`python3 learning.py progress get <knowledge_id>` 获取进度，检查 `foundation_path.status`
- `foundation_path.status != "completed"` → 提示"需要先完成基础流程"，退出
- `foundation_path.status == "completed"` → 继续

**Step 3** 从阶段5开始执行精通流程

---

### 3.7 精通列表

**触发词**：我要精通（无XXX）/ 我可以精通什么

**Step 1** 执行 CLI：`python3 learning.py knowledge list` 获取所有知识点，然后筛选 `foundation_path.status == "completed"` 且 `mastery_path.status == "not_started"` 的知识
- 显示：知识名称、基础完成日期

**Step 2** 用户选择 → 进入「3.6 精通流程」

---

### 3.8 进度查询

**触发词**：我的学习进度 / XXX学到哪了 / 查看学习状态 / 当前Level是多少

**Step 1** 执行 CLI：`python3 learning.py knowledge list` 获取所有知识点元数据

**Step 2** 对每个知识点执行 CLI：`python3 learning.py progress get <id>`，生成进度报告：
- 各知识当前 level 一览
- 精通表（基础完成 + 未开始精通）
- 当前 active_session 状态（执行 `python3 learning.py progress get_session`）

**Step 3** 展示给用户

---

### 3.9 知识探索

**触发词**：有哪些XXX / 想学XXX相关的

**Step 1** 执行 `LLM-WIKI QUERY "XXX相关"`，获取相关知识列表

**Step 2** 展示子知识树

**Step 3** 用户选择一个 → 进入「3.3 学习新知识」或「3.6 精通流程」

**限制**：单次入口流程内最多探索 3 次，超出则询问"是否回到选择？"

---

### 3.10 能力整合（模式一：已知域整合）

**触发词**：综合练习 / 系统设计题 / 给我一道大题

**Step 1** 加载 `ls-integration.md` + `ls-data-structure.md` + `LLM-WIKI skill`

**Step 2** 按 `ls-integration.md` 模式一流程执行：
   - 执行 CLI：`python3 learning.py integration list` 查询已完成场景（避免重复）
   - 选已学知识点 → 构造系统设计题 → 用户答题 → 评分 → 执行 `python3 learning.py integration update_solution <id> <summary> '<json>'` 记录

### 3.11 能力整合（模式二：探索域整合）

**触发词**：随机挑战 / 随机出题 / 来道开放题

**Step 1** 加载 `ls-integration.md` + `ls-data-structure.md` + `LLM-WIKI skill`

**Step 2** 按 `ls-integration.md` 模式二流程执行：
   - 随机抽 entity → 构造系统设计题 → 标注未学知识点 → 用户答题 → 评分 → 执行 `python3 learning.py integration update_solution <id> <summary> '<json>'` 记录

### 3.12 其他输入

不匹配以上任意入口 → 友好询问："可以说说你想做什么吗？比如'我要学XXX'、'我要复习'、'我的进度'等"

---



## 四、模块索引

根据使用场景，按需加载以下模块：

| 模块文件 | 加载场景 | 依赖模块 | 核心内容 |
|----------|----------|----------|----------|
| `modules/ls-data-structure.md` | 所有 DB 操作场景 | — | 数据库结构、CLI 调用规范（核心文档） |
| `modules/ls-source-prep.md` | 阶段4步骤0（源码准备） | ls-data-structure | 知识类型→权威实现映射、下载命令、镜像方案 |
| `modules/ls-learning-flow.md` | 开始基础学习 | ls-data-structure, LLM-WIKI | 基础流程（阶段1-4）学习流程、交互式设计 |
| `modules/ls-mastery-flow.md` | 开始精通流程 | ls-data-structure | 精通流程（阶段5-7）学习流程、补全机制 |
| `modules/ls-review-flow.md` | 复习入口 | ls-data-structure, LLM-WIKI | 复习 SOP：轮次设计 + 8 步执行 + 质量自适应 |
| `modules/ls-review-basic.md` | 复习步骤 3（出题） | ls-data-structure, LLM-WIKI, ls-review-psychology | stage×轮次 题型矩阵 + 出题规则 |
| `modules/ls-review-psychology.md` | ls-review-basic 加载时 | — | 复习设计背后的心理学原理参考（不参与流程） |
| `modules/ls-review-mastery.md` | 精通复习触发 | ls-data-structure, LLM-WIKI | L5-L7 精通复习规则 |
| `modules/ls-review-writeback.md` | 复习步骤 7（写回） | LLM-WIKI | 精华写回 wiki 的 6 种触发条件 |
| `modules/ls-content-mgmt.md` | 生成知识点内容 | ls-data-structure, LLM-WIKI | 内容生成规则、笔记整合 |
| `modules/ls-integration.md` | 能力整合练习（系统设计题） | ls-data-structure, LLM-WIKI | 模式一（已知域）模式二（探索域）系统设计题生成与评分 |

### 快速加载指南

| 用户说 | 入口 | 加载模块 |
|--------|------|---------|
| 我要学XXX（知识不存在） | 3.3 Step 3A | ls-content-mgmt.md + `learning.py progress init` → ls-learning-flow.md |
| 我要学XXX（知识存在） | 3.3 Step 3B | ls-learning-flow.md |
| 我要复习（无指定） | 3.4 | `learning.py review get_due` → ls-review-flow.md |
| 复习XXX | 3.5 | ls-review-flow.md |
| 我要精通XXX | 3.6 | ls-mastery-flow.md |
| 我要精通（无XXX） | 3.7 | `learning.py knowledge list` + `learning.py progress get` → 3.6 |
| 我的进度/学到哪了 | 3.8 | `learning.py progress get` + `learning.py progress get_session` |
| 有哪些XXX/相关 | 3.9 | LLM-WIKI QUERY |
| 综合练习 / 系统设计题 | 3.10 | ls-integration.md |
| 随机挑战 / 开放题 | 3.11 | ls-integration.md |

**通用依赖**：几乎所有入口都需要先加载 `ls-data-structure.md` + `LLM-WIKI skill`

---

## 七、快速参考

详细调用规范请参阅 `modules/ls-data-structure.md`（包含完整的 CLI 命令、字段校验、错误处理）。
