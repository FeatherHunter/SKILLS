---
name: daily-recorder-openclaw
description: 记录用户的发言和附件，从 OpenClaw session 文件提取用户消息和媒体附件入库，支持灵活时间范围查询。
---

# Daily Recorder - OpenClaw 版

## 触发词

- "记录语录"、"扫描消息"、"每日语录"
- cron 自动触发（每小时的 15分 和 45分）

## 执行方式

### 扫描入库（cron / 手动）
```bash
python3 /mnt/d/2Study/StudyNotes/SKILLS/daily-recorder-openclaw/scripts/record.py
```
- 不带参数：增量扫描（只扫新消息）
- 每次扫描更新 scan_checkpoint，下次自动增量

### 查询消息
```bash
# 查单日
python3 /mnt/d/2Study/StudyNotes/SKILLS/daily-recorder-openclaw/scripts/query.py --date 20260509

# 查范围
python3 /mnt/d/2Study/StudyNotes/SKILLS/daily-recorder-openclaw/scripts/query.py --start 20260509000000 --end 20260509235959

# 单独使用 start 或 end
python3 /mnt/d/2Study/StudyNotes/SKILLS/daily-recorder-openclaw/scripts/query.py --start 20260509000000

# 同时查询附件
python3 /mnt/d/2Study/StudyNotes/SKILLS/daily-recorder-openclaw/scripts/query.py --date 20260509 --attachments
```

## 目录结构

```
daily-recorder-openclaw/
├── SKILL.md                  # 本文件
├── scripts/
│   ├── record.py             # 主扫描脚本
│   ├── query.py              # 查询脚本
│   └── db.py                 # 数据库模块
└── references/
    ├── database_schema.md    # 表结构说明
    ├── design_rationale.md   # 设计思路
    └── api_reference.md      # 供其他技能调用的接口
```

## 数据库

路径：`/mnt/d/2Study/StudyNotes/.db/daily_recorder.db`

**三个表：**
- **user_messages**：用户消息（只存有文字内容的）
- **user_attachments**：用户附件（图片/文件/语音）
- **scan_checkpoint**：增量扫描进度记录

详细说明见 references/ 目录。