---
name: daily-recorder-openclaw
description: 记录用户的语录，从 OpenClaw session 文件提取用户发言（直接执行 Python 脚本）
---
# Daily Recorder - OpenClaw 版

> **架构说明**：本 skill 的核心逻辑在 `record_yulu.py` 脚本中。cron 任务直接调用该脚本，不经过 AI，避免 AI 行为干扰。

## 执行方式

### cron 自动调用
```bash
python3 /mnt/d/2Study/StudyNotes/SKILLS/daily-recorder-openclaw/record_yulu.py
```
- 每小时 15分 和 45分 自动执行
- 追加到当日语录文件，不覆盖

### 手动调用
```bash
# 今天
python3 /mnt/d/2Study/StudyNotes/SKILLS/daily-recorder-openclaw/record_yulu.py

# 指定日期
python3 /mnt/d/2Study/StudyNotes/SKILLS/daily-recorder-openclaw/record_yulu.py 20260507
```

## 工作流程

1. **扫描所有 session 文件**（跨多个文件，全局处理）
2. **过滤**：心跳/cron触发/系统元数据
3. **全局按时间排序**
4. **去重追加**：基于最后一条内容去重
5. **更新统计**

## 过滤规则

以下消息类型会被过滤：
- `[SYSTEM`、`[System note`、`[The user sent`
- `[cron:`、`[OpenClaw heartbeat`
- `Sender (untrusted metadata)`
- `openclaw-control-ui` 元数据

## 输出路径

`D:\2Study\StudyNotes\{YYYY}\个人\{YYYYMMDD}\{YYYYMMDD}_语录.md`

## 数据来源

`/home/feather/.openclaw/agents/main/sessions/*.jsonl`
