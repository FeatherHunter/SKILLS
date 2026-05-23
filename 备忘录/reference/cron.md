# Cron 配置指南

## 概述

备忘录技能需要设置 cron 任务，每分钟检查一次到期提醒，并通过消息渠道推送给用户。

## 配置要求

- 执行频率：每分钟
- 执行命令：`python3 ${SKILL_DIR}/script/reminder_scheduler.py`
- 推送渠道：QQ（或其他已配置的消息渠道）

## 验证

1. 添加一条提醒：`script/memo_cli.py remind <note_id> --at "当前时间"`
2. 等待 cron 任务执行
3. 检查是否收到提醒消息

## 故障排查

- 检查 cron 任务是否已添加
- 检查数据库中是否有 active 状态的提醒
- 检查消息渠道是否已配置
