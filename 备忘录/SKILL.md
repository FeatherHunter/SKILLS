# 备忘录 (Memorandum)

## 描述

私人多功能备忘录，支持文字记录、分类、媒体附件、全文搜索和定时提醒。

## 快速开始

复制以下 prompt 给 AI 安装技能：

```
请帮我安装备忘录技能：
1. 读取 SKILL.md 了解功能
2. 运行 script/init.sql 初始化数据库
3. 设置 cron 任务：每分钟检查提醒，通过 QQ 渠道推送消息
4. 验证：运行 python3 script/memo_cli.py --help
```

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MEMO_DB_PATH` | 数据库文件路径 | `memo.db` |
| `MEMO_MEDIA_DIR` | 媒体文件目录 | `media` |

## 操作规范

- 所有操作通过 `script/memo_cli.py` 执行
- 提醒必须关联笔记，不可独立存在
- 媒体文件路径使用相对路径存储
- CLI 返回 JSON：`{"status": "ok/error", "data": ..., "message": "..."}`

## 功能与触发词

### 添加笔记
- 触发词：记一下、帮我记、备忘、添加、存一下
- 命令：`script/memo_cli.py add "内容" -c 分类`
- 分类映射：社交→social，心愿→wish，灵感→inspiration，成就→achievement，工作→work，学习→study，记账→finance

### 搜索笔记
- 触发词：搜一下、搜索、查找、找一下、看看
- 命令：`script/memo_cli.py search "关键词" -c 分类`

### 更新笔记
- 触发词：更新、修改、改一下
- 先搜索找到笔记 ID，再更新
- 命令：`script/memo_cli.py update <id> --content "新内容"`

### 删除笔记
- 触发词：删除、删掉
- 先搜索找到笔记 ID，再删除
- 命令：`script/memo_cli.py delete <id>`

### 查看笔记详情
- 触发词：看看、查看、详情
- 命令：`script/memo_cli.py get <id>`

### 按时间搜索
- 触发词：这个月、最近、上周
- 命令：`script/memo_cli.py search-date <start> <end>`

### 编辑笔记分类
- 触发词：改分类、换个分类
- 先搜索找到笔记 ID，再更新分类
- 命令：`script/memo_cli.py update-category <id> <category>`

### 设置提醒
- 触发词：提醒、定时
- 时间识别：明天、后天、今天 + 时间
- 重复规则：每天→daily，每周→weekly，每月→monthly，每年→yearly
- 流程：先添加笔记获取 ID，再设置提醒
- 命令：`script/memo_cli.py remind <id> --at "YYYY-MM-DD HH:MM"` 或 `--repeat-type daily --rule "09:00"`

### 查看提醒
- 触发词：我有哪些提醒、提醒列表
- 命令：`script/memo_cli.py reminders`

### 废弃提醒
- 命令：`script/memo_cli.py dismiss <id>`

## 定时提醒机制

- cron 每分钟触发一次 `script/reminder_scheduler.py`
- 提前 10 分钟查找待提醒事项
- 一次性提醒：触发后记录 notified_at，避免重复通知
- 重复提醒（每天/每周/每月/每年）：正常触发
- 通过 QQ 渠道推送消息

## 参考文档

- 数据库结构：`reference/schema.md`
- 对话示例：`reference/examples.md`
- Cron 配置：`reference/cron.md`
