---
name: daily-schedule
description: 智能分析每日作息，生成作息报告
---

# Daily Schedule

以最强大脑执行该任务，查询用户语录，推断用户活动，生成作息报告和每周总结。

工作目录（绝对路径）:
- Windows: `D:\2Study\StudyNotes`
- WSL: `/mnt/d/2Study/StudyNotes`

## 安装
触发时检查**当前AI智能体**的 skills 目录：
- 不存在 `skills/daily-schedule/SKILL.md` → 创建SKILL文件(桥接器文件)，SKILL文件内容指向本文件
- 桥接器只符合SKILL规范且包含SKILL触发条件，和SKILL本体文件路径

## 触发方式
### 方式一：cron 触发（每日 06:30）
- 检测 cron 任务，不存在则创建：`30 6 * * *` 执行 `skill daily-schedule`
- 触发后读取 skill 内容
- **今日是周一**：
  1. 查询昨日 06:30 至今日 06:30 的用户语录，生成昨日作息报告
  2. 查询过去7天的用户语录（每天以 06:30 为分割点），汇总生成每周总结
- **今日非周一**：查询昨日 06:30 至今日 06:30 的用户语录，生成昨日作息报告

### 方式二：手动触发
- 说"分析作息"、"今日总结"、"我今天做了什么"
- 按用户指定时间段生成报告

## 数据来源
**唯一数据源：** `~/.hermes/state.db` (SQLite)

### 查询脚本
```python
import sqlite3
from datetime import datetime, timezone, timedelta

db_path = '/home/feather/.hermes/state.db'
beijing_tz = timezone(timedelta(hours=8))

# 时间段（传入参数）
start_dt = datetime({start_year}, {start_month}, {start_day}, {start_hour}, {start_min}, 0, tzinfo=beijing_tz)
end_dt = datetime({end_year}, {end_month}, {end_day}, {end_hour}, {end_min}, 0, tzinfo=beijing_tz)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
    SELECT timestamp, content FROM messages
    WHERE role = 'user'
    AND timestamp >= ? AND timestamp < ?
    AND content NOT LIKE '[SYSTEM%'
    AND content NOT LIKE '[System note%'
    AND content NOT LIKE '[The user sent%'
    ORDER BY timestamp ASC
""", (start_dt.timestamp(), end_dt.timestamp()))
messages = cursor.fetchall()
conn.close()

for ts, content in messages:
    dt = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    first_line = str(content).strip().split('\n')[0]
    if len(first_line) > 200:
        first_line = first_line[:200] + '...'
    print(f'{dt} - {first_line}')
```

### 每日边界
以**北京时间 06:30** 作为一天的分割点，即：
- 0421 06:30 ~ 0422 06:30 = 0422 的一天
- 0422 06:30 ~ 0423 06:30 = 0423 的一天

### 常用时间戳
| 北京时间 | timestamp |
|---------|-----------|
| 今天 06:30 | `{今天06:30的timestamp}` |
| 昨天 06:30 | `{昨天06:30的timestamp}` |
| 7天前 06:30 | `{7天前06:30的timestamp}` |

## 输出格式

**保存路径（绝对路径）：**
- Windows: `D:/2Study/StudyNotes/{YYYY}/个人/{报告日期}/`
- WSL: `/mnt/d/2Study/StudyNotes/{YYYY}/个人/{报告日期}/`

| 触发方式 | 文件名 |
|----------|--------|
| cron单日报告 | `{YYYYMMDD}_作息报告.md` |
| cron每周总结 | `{YYYYMMDD}-{YYYYMMDD}_每周总结.md` |
| 手动触发 | `{YYYYMMDD}[-{YYYYMMDD}]_作息报告.md` |

- cron触发：单日报告（昨日）或每周总结（周一）
- 手动触发：按用户指定日期/范围

**路径规则：**
- 每周总结在**周一**生成，保存路径为**上周最后一天（周日）**的日期目录
  - Windows 示例：周一 2026-04-21 生成周报 → 保存到 `D:/2Study/StudyNotes/2026/个人/20260420/` 目录
  - WSL 示例：周一 2026-04-21 生成周报 → 保存到 `/mnt/d/2Study/StudyNotes/2026/个人/20260420/` 目录
- 每日作息报告保存路径为**报告内容那天**的日期目录
  - Windows 示例：生成 2026-04-24 的作息报告 → 保存到 `D:/2Study/StudyNotes/2026/个人/20260424/` 目录
  - WSL 示例：生成 2026-04-24 的作息报告 → 保存到 `/mnt/d/2Study/StudyNotes/2026/个人/20260424/` 目录

---

## 每日作息报告格式

```markdown
# {日期} 作息报告

## 时间线

| 时间 | 活动 | 备注 |
|------|------|------|
| HH:MM | 起床/睡眠/工作/学习/用餐/通勤/洗漱/运动/休闲 | 简要描述，从用户消息中提炼 |
| ... | ... | ... |

## 时间分配

| 类别 | 时长 | 备注 |
|------|------|------|
| 睡眠 | X小时 | 估算入睡到起床时长 |
| 工作 | X小时 | 有明确工作标记的时间 |
| 学习 | X小时 | 有明确学习标记的时间 |
| 通勤 | X小时 | 骑车/开车/地铁等 |
| 用餐 | X小时 | 午饭/晚饭等 |
| 摸鱼/休闲 | X小时 | 其他 |
| ... | ... | ... |

## 洞察

- 根据该天上下文动态生成：
  - 当天作息特点
  - 有趣的发现
  - 值得注意的行为模式
```

---

## 每周总结格式

```markdown
# {年份}第{周数}周作息总结

## 作息总表

| 时间段 | {周一} | {周二} | {周三} | {周四} | {周五} | {周六} | {周日} |
|--------|--------|--------|--------|--------|--------|--------|--------|
| 🌅 06:30-08:00 | {活动摘要} | ... | ... | ... | ... | ... | ... |
| 💼 08:00-12:00 | {活动摘要} | ... | ... | ... | ... | ... | ... |
| 🍜 12:00-13:00 | {活动摘要} | ... | ... | ... | ... | ... | ... |
| 📚 13:00-18:00 | {活动摘要} | ... | ... | ... | ... | ... | ... |
| 🚴 18:00-19:00 | {活动摘要} | ... | ... | ... | ... | ... | ... |
| 🌙 19:00-06:30 | {活动摘要} | ... | ... | ... | ... | ... | ... |

> 点击任意时间段可跳转到对应日的作息详情页

### 作息详情

| 日期 | 作息报告 |
|------|---------|
| {周一} | [作息报告](../{周一}/YYYYMMDD_作息报告.md) |
| {周二} | [作息报告](../{周二}/YYYYMMDD_作息报告.md) |
| ... | ... |

> 使用相对路径 `../{日期}/YYYYMMDD_作息报告.md` 跳转到每日详情

## 本周数据概览

| 指标 | 本周 | 备注 |
|------|------|------|
| 平均睡眠时长 | X小时 | 估算值 |
| 总工作时长 | X小时 | 有明确工作标记 |
| 总学习时长 | X小时 | 有明确学习标记 |
| 最勤奋日 | {星期} | 学习时长最长那天 |
| 睡眠最少的夜 | {星期} / {时长} | 入睡最晚那天 |

## 作息规律

- **入睡习惯**：通常 {几点} 入睡
- **起床习惯**：工作日通常 {几点} 起 / 周末通常 {几点} 起
- **通勤方式**：{骑车/地铁/开车}
- **学习时段**：{主要在下午/晚上/碎片化}

## 本周洞察

- 根据过去7天的上下文动态生成：
  - 本周整体特点
  - 发现的规律或问题
  - 值得注意的行为变化
  - 简单的优化建议
```

---

## 【强制约束】

1. 报告必须严格符合 SKILL 中定义的「每日作息报告格式」或「每周总结格式」，结构缺失视为不合格
2. 以最强大脑执行：不受限于任何预设规则，以最聪明的方式解读用户消息中的行为和意图
3. 报告生成后，以最强大脑视角审视并修正：活动分类是否准确、时间估算是否合理、洞察是否有深度
4. 多用emoji表情生动活泼
