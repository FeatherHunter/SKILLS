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
