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
- CLI 命令返回 JSON 格式：`{"status": "ok/error", "data": ..., "message": "..."}`

---

## 功能模块

### 1. 笔记管理

快速添加、更新、删除文字笔记，支持分类标签。

**触发词：**
- "记一下..." / "帮我记..." / "备忘..."
- "添加笔记" / "存一下..."
- "更新笔记" / "修改笔记"
- "删除笔记" / "删掉..."

**CLI 命令：**
- `script/memo_cli.py add <content> [-c category] [-m media_path]`
- `script/memo_cli.py update <id> [--content] [-c category] [-m media_path]`
- `script/memo_cli.py delete <id>`

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

**CLI 命令：**
- `script/memo_cli.py search [keyword] [-c category] [-l limit]`

### 4. 定时提醒

支持一次性提醒和重复提醒（每天/每周/每月/每年）。

**触发词：**
- "提醒我明天下午3点开会"
- "每周五早上9点提醒我还信用卡"
- "设置每天8点提醒我喝水"
- "我有哪些提醒？"

**CLI 命令：**
- `script/memo_cli.py remind <note_id> [--at time] [--repeat-type type] [--rule rule]`
- `script/memo_cli.py reminders [--status active/dismissed]`
- `script/memo_cli.py dismiss <id>`

---

## 意图识别指导

当用户发送备忘录相关请求时，按以下规则解析：

### 添加笔记
- 匹配词：记一下、帮我记、记住、备忘、添加、存一下
- 提取内容：去掉前缀词后的文本
- 提取分类：社交→social，心愿→wish，灵感→inspiration，成就→achievement，工作→work，学习→study，记账→finance
- 构造命令：`script/memo_cli.py add "内容" -c 分类`

### 搜索笔记
- 匹配词：搜一下、搜索、查找、有没有、找一下、看看
- 提取关键词和分类
- 构造命令：`script/memo_cli.py search "关键词" -c 分类`

### 更新笔记
- 匹配词：更新、修改、改一下
- 构造命令：`script/memo_cli.py update <id> --content "新内容"`

### 删除笔记
- 匹配词：删除、删掉
- 先搜索找到笔记 ID，再删除
- 构造命令：`script/memo_cli.py delete <id>`

### 设置提醒
- 匹配词：提醒、定时
- 时间识别：明天、后天、今天 + 时间
- 重复规则：每天→daily，每周→weekly，每月→monthly，每年→yearly
- 先添加笔记获取 ID，再设置提醒
- 构造命令：`script/memo_cli.py remind <id> --at "时间"` 或 `--repeat-type type --rule "规则"`

### 查看提醒
- 匹配词：提醒列表、有哪些提醒、我的提醒
- 构造命令：`script/memo_cli.py reminders`

---

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MEMO_DB_PATH` | 数据库文件路径 | `memo.db` |
| `MEMO_MEDIA_DIR` | 媒体文件存储目录 | `media` |

---

## 依赖模块

- `script/memo_cli.py`：CLI 工具，处理所有笔记和提醒操作
- `script/reminder_scheduler.py`：提醒调度器，由 cron 调用
- `script/init.sql`：数据库初始化脚本

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
