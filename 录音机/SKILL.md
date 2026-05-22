---
name: 录音机
description: 记录用户的发言和附件，从 OpenClaw session 文件提取用户消息和媒体附件入库，支持灵活时间范围查询。本技能支持小龙虾（OpenClaw）系统，目前仅兼容小龙虾系统，其他系统不兼容。
---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

# 录音机

> 本技能支持小龙虾（OpenClaw）系统，目前仅兼容小龙虾系统，其他系统不兼容。

## 触发词

- "记录语录"、"扫描消息"、"每日语录"
- cron 自动触发（每10分钟）

## 执行方式

### 扫描入库（cron / 手动）
```bash
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/record.py
```
- 不带参数：增量扫描（只扫新消息）
- 每次扫描更新 scan_checkpoint，下次自动增量

### 查询消息
```bash
# 查单日
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/query.py --date 20260509

# 查范围
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/query.py --start 20260509000000 --end 20260509235959

# 单独使用 start 或 end
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/query.py --start 20260509000000

# 同时查询附件
python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/query.py --date 20260509 --attachments
```

## 目录结构

```
录音机/
├── SKILL.md                  # 本文件
├── scripts/
│   ├── record.py             # 主扫描脚本
│   ├── query.py              # 查询脚本
│   └── db.py                 # 数据库模块
└── references/
    ├── database_schema.md    # 表结构说明
    ├── design_rationale.md   # 设计思路
    ├── api_reference.md      # 供其他技能调用的接口
    └── recommended_cron.md   # ⭐ 推荐定时任务配置（必看！）
```

---

## ⭐ 推荐定时任务

**强烈建议配置定时任务，让录音机自动运行！**

> 详细配置说明见 `references/recommended_cron.md`

### 快速配置命令

```bash
# 创建推荐任务（每10分钟扫描一次）
openclaw cron add \
  --name "录音机-每10分记录语录" \
  --every 10m \
  --session isolated \
  --message "静默执行记录今日语录：python3 /mnt/d/2Study/StudyNotes/SKILLS/录音机/scripts/record.py"
```

### 为什么要配置定时任务？

| 手动触发 | 定时任务 |
|---------|---------|
| 需要你记得运行 | 自动后台运行 |
| 可能漏掉消息 | 每10分钟自动增量扫描 |
| 实时性差 | 新消息10分钟内入库 |

### 查看当前状态

```bash
# 查看录音机 cron 任务是否在运行
openclaw cron list | grep 录音机
```

## 数据库

路径：`/mnt/d/2Study/StudyNotes/.db/daily_recorder.db`

**三个表：**
- **user_messages**：用户消息（只存有文字内容的）
- **user_attachments**：用户附件（图片/文件/语音）
- **scan_checkpoint**：增量扫描进度记录

详细说明见 references/ 目录。