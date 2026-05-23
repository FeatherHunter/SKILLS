---
module: ls-data-structure
parent: learning-system-main
description: 数据库结构设计、CLI调用规范、表关系说明
load_when: 需要读取或写入数据时加载
depends: []
---

# Learning System 数据库结构

> **重要**：所有数据操作通过 scripts，不直接读写 JSON 文件。

---

## 一、数据库路径

```
数据库位置：D:\2Study\StudyNotes\.db\learning-system.db

路径查找顺序（与卡路里技能一致）：
1. 环境变量 SKILLS_DB_PATH
2. 技能目录（默认）
3. 父目录 .db 文件夹
```

---

## 二、脚本调用方式

### 统一入口

```bash
cd /mnt/d/2Study/StudyNotes/2026/learning-system/scripts
python3 learning.py <module> <action> [args]
```

### 可用模块

| 模块 | 脚本 | 功能 |
|------|------|------|
| knowledge | knowledge_api.py | 知识点元数据管理 |
| progress | progress_api.py | 学习进度管理 |
| review | review_api.py | 复习计划管理 |
| integration | integration_api.py | 能力整合练习 |

---

## 三、表关系（ER图）

```
knowledge_list (知识点元数据)
    │
    ├── 1:1 ──→ knowledge_progress (进度主表)
    │               │
    │               ├── 1:1 ──→ foundation_path (基础流程)
    │               │               │
    │               │               └── 1:4 ──→ stage_progress (阶段1-4)
    │               │
    │               ├── 1:1 ──→ mastery_path (精通流程)
    │               │               │
    │               │               └── 1:3 ──→ mastery_stage_progress (阶段5-7)
    │               │
    │               ├── 1:1 ──→ interview_assets (面试素材)
    │               │
    │               └── 1:1 ──→ active_session (当前会话)
    │
    └── 1:1 ──→ review_schedule (复习计划)
                    │
                    └── 1:5 ──→ review_round (复习轮次)
                            │
                            └── 1:1 ──→ mastery_review (精通复习)
```

### 表分组

| 分组 | 表 |
|------|-----|
| **知识点** | knowledge_list |
| **基础流程 (Stage 1-4)** | foundation_path + stage_progress |
| **精通流程 (Stage 5-7)** | mastery_path + mastery_stage_progress |
| **面试素材** | interview_assets |
| **复习** | review_schedule + review_round + mastery_review |
| **系统** | knowledge_progress + active_session |

**外键约束**：表之间通过外键 `knowledge_id` 关联，保证数据一致性。查询时可分开查（效率高），也可 JOIN（功能全）。

---

### 表1：knowledge_list（知识点元数据）

```sql
CREATE TABLE knowledge_list (
    id TEXT PRIMARY KEY,           -- 知识点ID，如 "kotlin-coroutine"
    title TEXT NOT NULL,           -- 显示名称，如 "Kotlin协程"
    language TEXT NOT NULL,       -- 语言：kotlin/java/python/rust/javascript/typescript/go/cpp/c/swift/other
    category TEXT NOT NULL,        -- 分类：编程语言/框架/理论/工具/其他
    subcategory TEXT,              -- 子分类，如 "并发编程"
    framework TEXT,                -- 所属框架，如 "android-framework"
    tags TEXT,                    -- JSON array，如 ["coroutine","async"]
    metadata TEXT,                -- JSON object，如 {"difficulty":"medium","estimated_hours":2}
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**调用示例**：
```bash
python3 learning.py knowledge add '{"id":"kotlin-coroutine","title":"Kotlin协程","language":"kotlin","category":"编程语言"}'
python3 learning.py knowledge list
python3 learning.py knowledge get kotlin-coroutine
python3 learning.py knowledge update kotlin-coroutine '{"title":"Kotlin协程深入"}'
python3 learning.py knowledge delete kotlin-coroutine
```

---

### 表2：knowledge_progress（学习进度主表）

```sql
CREATE TABLE knowledge_progress (
    knowledge_id TEXT PRIMARY KEY,
    target_level INTEGER DEFAULT 7,
    last_activity TIMESTAMP,
    total_learning_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
);
```

**Level 语义**：
| Level | 含义 | 说明 |
|-------|------|------|
| 0 | 待学 | 知识点已列入计划，尚未开始 |
| 1 | 概念认知 | 能说是什么 |
| 2 | 应用掌握 | 能在项目中使用 |
| 3 | 原理理解 | 能说为什么 |
| 4 | 实现理解 | 能说怎么实现（基础流程完成） |
| 5 | 实战深化 | 能举案例 |
| 6 | 边界探索 | 能说极限和坑 |
| 7 | 迁移设计 | 能延伸设计（精通流程完成） |

**调用示例**：
```bash
python3 learning.py progress init kotlin-coroutine
python3 learning.py progress get kotlin-coroutine
```

---

### 表3：foundation_path（基础流程进度）

```sql
CREATE TABLE foundation_path (
    knowledge_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(not_started/in_progress/completed),
    current_stage INTEGER DEFAULT 1 CHECK(1-4),
    completed_at TIMESTAMP,
    total_learning_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
);
```

**调用示例**：
```bash
python3 learning.py progress update_foundation kotlin-coroutine '{"status":"completed","completed_at":"2026-05-10T14:00:00+08:00","total_learning_minutes":90}'
```

---

### 表4：stage_progress（阶段进度）

```sql
CREATE TABLE stage_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id TEXT NOT NULL,
    stage_name TEXT NOT NULL CHECK(stage_1/stage_2/stage_3/stage_4),
    status TEXT NOT NULL CHECK(not_started/in_progress/completed),
    completed_at TIMESTAMP,
    essence_keywords TEXT,  -- JSON array
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id),
    UNIQUE(knowledge_id, stage_name)
);
```

**调用示例**：
```bash
python3 learning.py progress update_stage kotlin-coroutine stage_1 '{"status":"completed","completed_at":"2026-05-10T13:00:00+08:00","essence_keywords":["协程是什么","挂起"]}'
```

---

### 表5：mastery_path（精通流程进度）

```sql
CREATE TABLE mastery_path (
    knowledge_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(not_started/in_progress/completed),
    current_stage INTEGER CHECK(5-7),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_learning_minutes INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
);
```

**调用示例**：
```bash
python3 learning.py progress update_mastery kotlin-coroutine '{"status":"in_progress","started_at":"2026-05-10T15:00:00+08:00"}'
```

---

### 表6：mastery_stage_progress（精通阶段进度）

```sql
CREATE TABLE mastery_stage_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id TEXT NOT NULL,
    stage_name TEXT NOT NULL CHECK(stage_5/stage_6/stage_7),
    status TEXT NOT NULL CHECK(not_started/in_progress/completed),
    step INTEGER DEFAULT 1,
    cases_documented INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id),
    UNIQUE(knowledge_id, stage_name)
);
```

---

### 表7：interview_assets（面试素材路径）

```sql
CREATE TABLE interview_assets (
    knowledge_id TEXT PRIMARY KEY,
    star_case_path TEXT,           -- STAR 案例卡路径（L5完成时写入）
    failure_case_path TEXT,        -- 反面案例卡路径（L6完成时写入）
    adr_path TEXT,                 -- ADR路径（L7完成时写入）
    validated_questions TEXT,     -- JSON array，已验证的面试问答
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
);
```

---

### 表8：active_session（当前学习会话）

```sql
CREATE TABLE active_session (
    id INTEGER PRIMARY KEY CHECK(id=1),
    knowledge_id TEXT,
    path_type TEXT CHECK(foundation/mastery/unknown),
    stage INTEGER CHECK(1-7),
    step INTEGER,
    started_at TIMESTAMP,
    total_minutes INTEGER DEFAULT 0,
    updated_at TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
);
```

**调用示例**：
```bash
python3 learning.py progress update_session '{"knowledge_id":"kotlin-coroutine","path_type":"foundation","stage":1,"step":1}'
python3 learning.py progress get_session
```

---

### 表10：review_schedule（复习计划）

```sql
CREATE TABLE review_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id TEXT UNIQUE NOT NULL,
    current_round INTEGER DEFAULT 0 CHECK(0-5),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
);
```

**调用示例**：
```bash
python3 learning.py review create_schedule kotlin-coroutine
python3 learning.py review get_schedule kotlin-coroutine
python3 learning.py review get_due
```

---

### 表11：review_round（复习轮次）

```sql
CREATE TABLE review_round (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER NOT NULL,
    round INTEGER NOT NULL CHECK(1-5),
    target_day INTEGER NOT NULL,
    scheduled_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK(pending/completed),
    completed_at TIMESTAMP,
    score INTEGER,
    questions_count INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (schedule_id) REFERENCES review_schedule(id),
    UNIQUE(schedule_id, round)
);
```

**调用示例**：
```bash
python3 learning.py review complete_round kotlin-coroutine 1 85 10 8 15 "还行" '[3,5]'
```

---

### 表12：mastery_review（精通复习计划）

```sql
CREATE TABLE mastery_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schedule_id INTEGER UNIQUE NOT NULL,
    enabled INTEGER DEFAULT 0,
    last_review TIMESTAMP,
    next_review TIMESTAMP,
    history TEXT,  -- JSON array
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (schedule_id) REFERENCES review_schedule(id)
);
```

**调用示例**：
```bash
python3 learning.py review enable_mastery kotlin-coroutine
python3 learning.py review record_mastery kotlin-coroutine
python3 learning.py review get_mastery_status kotlin-coroutine
```

---

### 表13：review_history（复习历史）

```sql
CREATE TABLE review_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_id TEXT NOT NULL,
    round INTEGER NOT NULL CHECK(1-5),
    review_date TIMESTAMP NOT NULL,
    duration_minutes INTEGER,
    questions_count INTEGER,
    correct_count INTEGER,
    score INTEGER CHECK(0-100),
    user_feedback TEXT,
    wrong_questions TEXT,     -- JSON array
    verification TEXT,        -- JSON object，可选
    created_at TIMESTAMP,
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
);
```

**调用示例**：
```bash
python3 learning.py review get_history kotlin-coroutine
python3 learning.py review add_verification kotlin-coroutine 3 now '[{"topic":"supervisorScope","passed":true}]' 1 1
python3 learning.py review get_weak kotlin-coroutine
```

---

### 表14：integration_scenario（能力整合练习记录）

```sql
CREATE TABLE integration_scenario (
    id TEXT PRIMARY KEY,     -- int-XXX 格式
    scenario TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(known/explore),
    knowledge_used TEXT,      -- JSON array
    knowledge_unlearned TEXT,  -- JSON array
    knowledge_unlearned_explanations TEXT,  -- JSON object
    difficulty TEXT CHECK(senior/architect),
    created_at TIMESTAMP NOT NULL,
    user_solution_summary TEXT,
    ai_feedback TEXT,          -- JSON object
    unlearned_interest TEXT, -- JSON array
    updated_at TIMESTAMP
);
```

**调用示例**：
```bash
python3 learning.py integration create '{"scenario":"设计消息推送系统","mode":"known","difficulty":"architect","knowledge_used":["android-binder"]}'
python3 learning.py integration get int-001
python3 learning.py integration list
python3 learning.py integration update_solution int-001 "我的方案是..." '{"score":78}'
python3 learning.py integration stats
```

---

### 表15：meta（版本控制）

```sql
CREATE TABLE meta (
    file_key TEXT PRIMARY KEY,
    version TEXT,
    last_updated TIMESTAMP,
    last_check TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## 四、Level 计算规则

Level 由 `foundation_path` 和 `mastery_path` 的 status 自动计算：

```
if foundation_path.status == "completed":
    base = 4
    if mastery_path.status == "completed":
        current_level = 7
    elif mastery_path.status == "in_progress":
        current_level = 4 + (mastery_path.current_stage - 5)
    else:
        current_level = 4
elif foundation_path.status == "in_progress":
    current_level = foundation_path.current_stage - 1
else:
    current_level = 0
```

**AI 注意**：调用 `progress get` 返回的 `current_level` 是计算值，不要直接修改，应该通过更新 `foundation_path.status` 或 `mastery_path.status` 来间接改变。

---

## 五、关键业务规则

### 知识点生命周期

```
knowledge_list 创建
    ↓
progress init（level=0, 所有 stage=not_started）
    ↓
阶段1-4 学习（每个 stage 完成时 update_stage）
    ↓
foundation_path.status == "completed"（自动创建复习计划）
    ↓
阶段5-7 精通（mastery_path 状态变化）
    ↓
mastery_path.status == "completed"（level=7）
```

### 复习计划触发

- 基础流程 `stage_4` 完成时 → 自动创建 5 轮复习计划
- 精通流程完成时 → 启用精通复习（每30天一次）

---

## 六、快速参考

### 常用 CLI 命令

```bash
# 知识点
python3 learning.py knowledge add '<json>'
python3 learning.py knowledge list [category] [language]
python3 learning.py knowledge get <id>

# 进度
python3 learning.py progress init <id>
python3 learning.py progress get <id>
python3 learning.py progress get_session
python3 learning.py progress update_stage <id> <stage> '<json>'
python3 learning.py progress update_foundation <id> '<json>'
python3 learning.py progress update_mastery <id> '<json>'

# 复习
python3 learning.py review get_due [date]
python3 learning.py review complete_round <id> <round> <score>
python3 learning.py review get_history [id] [limit]
python3 learning.py review get_weak <id>

# 能力整合
python3 learning.py integration create '<json>'
python3 learning.py integration update_solution <id> <summary> '<json>'
python3 learning.py integration list
```

### 字段校验

| 字段 | 可选值 |
|------|--------|
| language | kotlin, java, python, rust, javascript, typescript, go, cpp, c, swift, other |
| category | 编程语言, 框架, 理论, 工具, 其他 |
| status | not_started, in_progress, completed |
| path_type | foundation, mastery, unknown |
| round | 1, 2, 3, 4, 5 |
| current_stage | 1-4 (foundation), 5-7 (mastery) |
| score | 0-100 |

---

## 七、错误处理

调用脚本后检查返回：

```json
// 成功
{"success": true, "data": {...}}

// 失败
{"success": false, "errors": ["[校验失败] xxx", "[业务规则] xxx"]}
```

AI 处理错误：
1. 解析 `success` 字段
2. 失败时读取 `errors` 列表
3. 修正参数后重试（最多3次）
4. 3次后仍失败，报告给用户