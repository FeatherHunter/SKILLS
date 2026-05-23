# 备忘录技能重构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 重构备忘录技能，使其符合 openclaw SKILL 开发规范，支持环境变量配置、自动安装、cron 定时提醒和消息推送。

**Architecture:** 采用分层架构：SKILL.md 作为 AI 入口，script/ 目录包含 Python CLI 和调度脚本，reference/ 目录包含文档。通过环境变量配置路径，支持灵活部署。

**Tech Stack:** Python 3.x, SQLite, FTS5, openclaw cron

---

## 文件结构

```
备忘录/
├── SKILL.md                    # 主文档（AI 入口）
├── _meta.json                  # 技能元数据
├── script/
│   ├── init.sql               # 数据库初始化脚本
│   ├── memo_cli.py            # CLI 工具
│   ├── intent_handler.py      # 意图识别模块
│   └── reminder_scheduler.py  # 提醒调度器
└── reference/
    ├── schema.md              # 数据库 schema
    ├── examples.md            # 对话示例
    └── cron.md                # cron 配置指南
```

---

## Task 1: 创建 _meta.json 元数据文件

**Files:**
- Create: `备忘录/_meta.json`

- [ ] **Step 1: 创建 _meta.json**

```json
{
  "name": "备忘录",
  "version": "1.0.0",
  "description": "私人多功能备忘录，支持文字记录、分类、媒体附件、全文搜索和定时提醒",
  "author": "Feather",
  "tags": ["productivity", "notes", "reminder"],
  "min_openclaw_version": "1.0.0",
  "env_vars": [
    {
      "name": "MEMO_DB_PATH",
      "description": "数据库文件路径",
      "default": "memo.db"
    },
    {
      "name": "MEMO_MEDIA_DIR",
      "description": "媒体文件存储目录",
      "default": "media"
    }
  ]
}
```

- [ ] **Step 2: 验证 JSON 格式**

Run: `python -m json.tool "D:\2Study\StudyNotes\SKILLS\备忘录/_meta.json"`
Expected: 格式正确，无报错

- [ ] **Step 3: Commit**

```bash
git add "备忘录/_meta.json"
git commit -m "feat: 创建 _meta.json 元数据文件"
```

---

## Task 2: 修改 memo_cli.py 支持环境变量配置

**Files:**
- Modify: `备忘录/script/memo_cli.py:14`

- [ ] **Step 1: 修改 DB_PATH 支持环境变量**

将第 14 行：
```python
DB_PATH = os.path.join(os.path.dirname(__file__), "../memo.db")
```

改为：
```python
DB_PATH = os.environ.get("MEMO_DB_PATH", os.path.join(os.path.dirname(__file__), "../memo.db"))
```

- [ ] **Step 2: 验证修改**

Run: `python -c "import sys; sys.path.insert(0, 'D:\2Study\StudyNotes\SKILLS\备忘录\script'); import memo_cli; print('DB_PATH:', memo_cli.DB_PATH)"`
Expected: 输出数据库路径

- [ ] **Step 3: Commit**

```bash
git add "备忘录/script/memo_cli.py"
git commit -m "feat: memo_cli.py 支持 MEMO_DB_PATH 环境变量"
```

---

## Task 3: 修改 reminder_scheduler.py 支持环境变量

**Files:**
- Modify: `备忘录/script/reminder_scheduler.py:11`

- [ ] **Step 1: 修改 cli_path 支持环境变量**

将第 11 行：
```python
cli_path = os.path.join(os.path.dirname(__file__), "memo_cli.py")
```

改为：
```python
cli_path = os.environ.get("MEMO_CLI_PATH", os.path.join(os.path.dirname(__file__), "memo_cli.py"))
```

- [ ] **Step 2: 验证修改**

Run: `python -c "import sys; sys.path.insert(0, 'D:\2Study\StudyNotes\SKILLS\备忘录\script'); import reminder_scheduler; print('cli_path:', reminder_scheduler.cli_path)"`
Expected: 输出 CLI 路径

- [ ] **Step 3: Commit**

```bash
git add "备忘录/script/reminder_scheduler.py"
git commit -m "feat: reminder_scheduler.py 支持 MEMO_CLI_PATH 环境变量"
```

---

## Task 4: 创建 reference/cron.md

**Files:**
- Create: `备忘录/reference/cron.md`

- [ ] **Step 1: 创建 cron.md**

```markdown
# Cron 配置指南

## 概述

备忘录技能使用 openclaw cron 功能实现定时提醒检查。系统每分钟自动检查一次，将到期提醒通过消息渠道推送给用户。

## 配置步骤

### 1. 添加 cron 任务

在 openclaw 中执行以下命令添加 cron 任务：

```
cron add --name "memo-reminder-check" --schedule "* * * * *" --command "python3 ${SKILL_DIR}/script/reminder_scheduler.py"
```

### 2. 验证 cron 任务

```
cron list
```

应该能看到类似输出：

```
memo-reminder-check: * * * * * python3 /path/to/备忘录/script/reminder_scheduler.py
```

### 3. 测试 cron 执行

```
cron run memo-reminder-check
```

## 环境变量

确保以下环境变量已配置：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MEMO_DB_PATH` | 数据库文件路径 | `memo.db` |
| `MEMO_CLI_PATH` | CLI 工具路径 | `script/memo_cli.py` |

## 消息推送

cron 任务检测到提醒后，会通过 openclaw 的通知系统发送消息。支持的渠道：

- QQ
- 微信（如已配置）

消息格式：
```
【备忘录提醒】{时间} - {内容}
```

## 故障排查

### cron 任务未执行

1. 检查 cron 任务是否已添加：`cron list`
2. 检查脚本路径是否正确
3. 检查环境变量是否配置

### 提醒未推送

1. 检查数据库中是否有 active 状态的提醒
2. 检查 openclaw 通知渠道是否配置
3. 查看 cron 执行日志
```

- [ ] **Step 2: Commit**

```bash
git add "备忘录/reference/cron.md"
git commit -m "docs: 添加 cron 配置指南"
```

---

## Task 5: 重构 SKILL.md

**Files:**
- Modify: `备忘录/SKILL.md`

- [ ] **Step 1: 重写 SKILL.md**

```markdown
# 备忘录 (Memorandum)

## 快速开始

复制以下 prompt 给 AI，即可安装并配置备忘录技能：

```
请帮我安装备忘录技能：

1. 安装技能：读取 SKILL.md 并按照说明配置
2. 配置环境变量：
   - MEMO_DB_PATH: 数据库文件路径（默认：memo.db）
   - MEMO_MEDIA_DIR: 媒体文件目录（默认：media）
3. 初始化数据库：运行 script/init.sql
4. 添加 cron 任务：每分钟检查提醒，命令为 python3 ${SKILL_DIR}/script/reminder_scheduler.py
5. 验证安装：运行 python3 script/memo_cli.py --help
```

如需更改目录，修改环境变量即可：
```
请帮我修改备忘录的存储目录：
1. 修改 MEMO_DB_PATH 为新数据库路径
2. 修改 MEMO_MEDIA_DIR 为新媒体目录
3. 重启 cron 任务使配置生效
```

---

## 操作规范

- 所有笔记操作通过 `script/memo_cli.py` 执行
- 提醒必须关联笔记，不可独立存在
- 媒体文件路径使用相对路径存储
- 定时提醒由 cron 自动触发，每分钟检查一次

---

## 功能模块

### 1. 笔记管理

快速添加、编辑、删除文字笔记，支持分类标签。

**触发词：**
- "记一下..." / "帮我记..." / "备忘..."
- "添加笔记" / "存一下..."

### 2. 媒体附件

支持图片、录音、文件等媒体附件，路径存储在笔记中。

**触发词：**
- "拍张照存起来"
- "保存这个文件"

### 3. 分类检索

按分类组织笔记，支持全文搜索和列表浏览。

**触发词：**
- "我的社交夹里有什么？"
- "搜一下关于旅行的笔记"
- "看看工作笔记"

### 4. 定时提醒

支持一次性提醒和重复提醒（每天/每周/每月/每年）。

**触发词：**
- "提醒我明天下午3点开会"
- "每周五早上9点提醒我还信用卡"
- "设置每天8点提醒我喝水"

---

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MEMO_DB_PATH` | 数据库文件路径 | `memo.db` |
| `MEMO_MEDIA_DIR` | 媒体文件存储目录 | `media` |
| `MEMO_CLI_PATH` | CLI 工具路径 | `script/memo_cli.py` |

---

## 依赖模块

- `script/memo_cli.py`：CLI 工具，处理所有笔记和提醒操作
- `script/intent_handler.py`：意图识别，将自然语言转换为 CLI 命令
- `script/reminder_scheduler.py`：提醒调度器，由 cron 调用

---

## Cron 配置

详见 `reference/cron.md`。

---

## 数据库

详见 `reference/schema.md`。

---

## 对话示例

详见 `reference/examples.md`。

---

## 核心原则

- 所有路径使用相对路径，支持多环境迁移
- 媒体文件加密由上层处理，CLI 仅记录路径
- 提醒规则实时计算，不预存触发时间
- 错误信息清晰明确，便于排查
```

- [ ] **Step 2: 验证 Markdown 格式**

Run: `python -c "import sys; content = open('D:\2Study\StudyNotes\SKILLS\备忘录\SKILL.md', 'r', encoding='utf-8').read(); print('Length:', len(content))"`
Expected: 输出文件长度

- [ ] **Step 3: Commit**

```bash
git add "备忘录/SKILL.md"
git commit -m "refactor: 重构 SKILL.md，符合 openclaw 规范"
```

---

## Task 6: 更新 reference/schema.md

**Files:**
- Modify: `备忘录/reference/schema.md:4`

- [ ] **Step 1: 更新 init.sql 路径引用**

将第 4 行：
```markdown
详见 `script/init.sql`。
```

改为：
```markdown
详见 `script/init.sql`。

## 环境变量

数据库路径通过 `MEMO_DB_PATH` 环境变量配置，默认为 `memo.db`。
```

- [ ] **Step 2: Commit**

```bash
git add "备忘录/reference/schema.md"
git commit -m "docs: schema.md 添加环境变量说明"
```

---

## Task 7: 更新 reference/examples.md

**Files:**
- Modify: `备忘录/reference/examples.md`

- [ ] **Step 1: 更新 CLI 路径引用**

将所有 `script/memo_cli.py` 引用保持不变（已在之前修改过）。

- [ ] **Step 2: 验证文件内容**

Run: `grep -n "memo_cli" "D:\2Study\StudyNotes\SKILLS\备忘录\reference\examples.md"`
Expected: 所有引用都是 `script/memo_cli.py`

- [ ] **Step 3: Commit**

```bash
git add "备忘录/reference/examples.md"
git commit -m "docs: examples.md 路径引用已更新"
```

---

## Task 8: 验证整体结构

- [ ] **Step 1: 检查目录结构**

Run: `find "D:\2Study\StudyNotes\SKILLS\备忘录" -type f | sort`
Expected:
```
备忘录/SKILL.md
备忘录/_meta.json
备忘录/docs/superpowers/plans/2026-05-23-memo-skill-refactor.md
备忘录/reference/cron.md
备忘录/reference/examples.md
备忘录/reference/schema.md
备忘录/script/init.sql
备忘录/script/intent_handler.py
备忘录/script/memo_cli.py
备忘录/script/reminder_scheduler.py
```

- [ ] **Step 2: 验证 JSON 格式**

Run: `python -m json.tool "D:\2Study\StudyNotes\SKILLS\备忘录/_meta.json"`
Expected: 格式正确

- [ ] **Step 3: 验证 Python 语法**

Run: `python -m py_compile "D:\2Study\StudyNotes\SKILLS\备忘录\script\memo_cli.py" && python -m py_compile "D:\2Study\StudyNotes\SKILLS\备忘录\script\reminder_scheduler.py" && python -m py_compile "D:\2Study\StudyNotes\SKILLS\备忘录\script\intent_handler.py"`
Expected: 无报错

- [ ] **Step 4: 最终 Commit**

```bash
git add -A
git commit -m "feat: 备忘录技能重构完成，符合 openclaw 规范"
```

---

## 完成

计划已完成。两个执行选项：

**1. Subagent-Driven (recommended)** - 每个任务分发一个新子代理，任务间进行审查，快速迭代

**2. Inline Execution** - 在当前会话中使用 executing-plans 执行任务，批量执行并设置检查点

选择哪种方式？
