---
name: 录音机
description: 从 OpenClaw session 文件提取用户消息和附件入库。支持：扫描入库（增量/全量）、按日期/范围/渠道/发送者查询消息、查询附件（图片/语音/文件）、数据库管理（初始化/统计/重建索引）、定时任务管理（创建/查看/删除/触发）。触发词：扫描消息、全量扫描、扫描附件、查询消息、查询日期、查询范围、查询最近、查询今日、查询渠道、查询发送者、查询附件、查询图片、查询语音、初始化数据库、查看状态、统计消息、重建索引、查看定时、创建定时、删除定时、手动触发。
triggers:
  - 扫描消息
  - 全量扫描
  - 扫描附件
  - 查询消息
  - 查询日期
  - 查询范围
  - 查询最近
  - 查询今日
  - 查询渠道
  - 查询发送者
  - 查询附件
  - 查询图片
  - 查询语音
  - 初始化数据库
  - 查看状态
  - 统计消息
  - 重建索引
  - 查看定时
  - 创建定时
  - 删除定时
  - 手动触发
---

# 录音机

> 从 OpenClaw session 文件提取用户消息和附件入库，支持灵活查询。本技能仅兼容小龙虾（OpenClaw）系统。

## ⚠️ 强制性规定（最高优先级）

1. **该技能的所有优化和变动、脚本的所有变动都必须体现在 `录音机.html` 上。**
2. **该强制性规定优先级最高，覆盖一切其他规则。**
3. **对该技能的所有文件、脚本的任何一行修改都需要明确得到用户的 1 次确认。**

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

## 唤醒词路由表

### A. 扫描入库

| 唤醒词 | 动作 | 命令 |
|---|---|---|
| 扫描消息 | 增量扫描新消息和附件入库 | `python3 scripts/record.py` |
| 全量扫描 | 清空 checkpoint 全量重扫 | `python3 scripts/record.py --full` |
| 扫描附件 | 扫描并提取附件入库（同扫描消息） | `python3 scripts/record.py` |

> 注：扫描消息时自动提取附件，无需单独扫描。

### B. 查询消息

| 唤醒词 | 动作 | 命令 |
|---|---|---|
| 查询消息 | 通用查询入口 | `python3 scripts/query.py --date YYYYMMDD` |
| 查询日期 | 按指定日期查消息 | `python3 scripts/query.py --date YYYYMMDD` |
| 查询范围 | 按时间范围查消息 | `python3 scripts/query.py --start YYYYMMDDHHMMSS --end YYYYMMDDHHMMSS` |
| 查询最近 | 查最近 N 条消息 | `python3 scripts/query.py --recent N` |
| 查询今日 | 查今日消息 | `python3 scripts/query.py --date $(date +%Y%m%d)` |
| 查询渠道 | 按渠道筛选消息 | `python3 scripts/query.py --channel qq/wechat/pc` |
| 查询发送者 | 按发送者筛选消息 | `python3 scripts/query.py --sender <sender_id>` |

### C. 查询附件

| 唤醒词 | 动作 | 命令 |
|---|---|---|
| 查询附件 | 按日期查附件列表 | `python3 scripts/query.py --date YYYYMMDD --attachments` |
| 查询图片 | 只查图片附件 | `python3 scripts/query.py --date YYYYMMDD --type image` |
| 查询语音 | 只查语音附件 | `python3 scripts/query.py --date YYYYMMDD --type audio` |

### D. 数据库管理

| 唤醒词 | 动作 | 命令 |
|---|---|---|
| 初始化数据库 | 建表建索引 | `python3 scripts/status.py --init` |
| 查看状态 | DB 路径、记录数、checkpoint 概况 | `python3 scripts/status.py` |
| 统计消息 | 总数/今日/各渠道统计 | `python3 scripts/status.py --stats` |
| 重建索引 | 重建数据库索引 | `python3 scripts/status.py --reindex` |

### E. 定时任务

| 唤醒词 | 动作 | 命令 |
|---|---|---|
| 查看定时 | 查看录音机 cron 任务 | `openclaw cron list \| grep 录音机` |
| 创建定时 | 创建定时扫描任务 | `openclaw cron add --name "录音机-每10分记录语录" --every 10m --session isolated --message "静默执行：python3 scripts/record.py"` |
| 删除定时 | 删除定时任务 | `openclaw cron delete <task-id>` |
| 手动触发 | 手动执行一次定时任务 | `openclaw cron run <task-id>` |

## 配置项

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `SKILLS_DB_PATH` | 数据库目录 |  |
| `OPENCLAW_SESSIONS` | OpenClaw agent 或 sessions 目录 | `~/.openclaw/agents`（自动扫描所有 agent） |

## 一键安装

```
请帮我初始化录音机技能：
1. 检查 Python 环境
2. 引导我配置环境变量
3. 显示当前环境变量配置
4. 告诉我如何更改数据目录
```

## 目录结构

```
录音机/
├── SKILL.md                  # 本文件
├── 录音机.html               # 功能手册（单文件 HTML）
├── scripts/
│   ├── record.py             # 主扫描脚本（增量/全量）
│   ├── query.py              # 查询脚本（消息/附件/渠道/类型）
│   ├── status.py             # 状态/统计/维护脚本
│   └── db.py                 # 数据库模块
└── references/
    ├── database_schema.md    # 表结构说明
    ├── design_rationale.md   # 设计思路
    ├── api_reference.md      # 供其他技能调用的接口
    └── recommended_cron.md   # 推荐定时任务配置
```

## ⭐ 推荐定时任务

> 详细配置见 `references/recommended_cron.md`

```bash
openclaw cron add \
  --name "录音机-每10分记录语录" \
  --every 10m \
  --session isolated \
  --message "静默执行记录今日语录：python3 scripts/record.py"
```

## 数据库

路径通过三级路由自动查找：环境变量 `SKILLS_DB_PATH` > 父目录 `.db/` > 技能目录 `.db/`

**三个表：**
- **user_messages**：用户消息（只存有文字内容的）
- **user_attachments**：用户附件（图片/文件/语音）
- **scan_checkpoint**：增量扫描进度记录

详细说明见 references/ 目录。
