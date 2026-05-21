---
name: 作息管家
description: 作息管家技能。根据用户的每日语录（来自daily-recorder-openclaw）自动生成作息时间表，记录0-24点各时间段的活动分类，并提供查询、统计、报告功能。当用户提到"作息"、查询某天的时间安排、生成作息报告时触发。
metadata: { "openclaw": { "emoji": "🌙", "requires": { "python": ">=3.7" } } }
---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 三层架构

| 层级 | 文件 | 职责 |
|------|------|------|
| 底层 | `scripts/schedule_db.py` | 数据库读写、语录数据库读取 |
| 中层 | `scripts/schedule_cli.py` | AI分析引擎、CLI命令 |
| 上层 | 本文件 | 技能定义、触发词、用户接口 |

---

## 数据库结构

**路径**: 由 `scripts/schedule_db.py` 的三层查找逻辑决定（环境变量 > 技能目录 > 父目录.db）

### 主表：schedule_records（作息记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| date | TEXT | 日期（YYYY-MM-DD） |
| time_start | TEXT | 开始时间（HH:MM） |
| time_end | TEXT | 结束时间（HH:MM） |
| duration_minutes | INTEGER | 持续时长（分钟） |
| activity | TEXT | 活动描述 |
| category | TEXT | 分类：睡眠/工作/学习/运动/通勤/餐饮/娱乐/社交/休闲/健康/洗漱/兴趣爱好/未知 |
| source_contents | TEXT | 判断依据的消息原文（多条约逗号分隔） |
| source_timestamps | TEXT | 对应消息时间（逗号分隔） |
| analysis_reasoning | TEXT | AI分析推理过程（心路历程） |

### 摘要表：daily_summary

| 字段 | 类型 | 说明 |
|------|------|------|
| date | TEXT | 日期（主键） |
| total_sleep_minutes | INTEGER | 睡眠总时长 |
| total_work_minutes | INTEGER | 工作总时长 |
| total_exercise_minutes | INTEGER | 运动总时长 |
| total_commute_minutes | INTEGER | 通勤总时长 |
| total_eating_minutes | INTEGER | 餐饮总时长 |
| total_learning_minutes | INTEGER | 学习总时长 |
| total_entertainment_minutes | INTEGER | 娱乐总时长 |
| total_unknown_minutes | INTEGER | 未知活动总时长 |

---

## 增量同步逻辑（核心设计）

### 设计原则
- **不设 checkpoint 表**——避免额外的数据存储
- **游标 = schedule_records 中的最后一条记录的结束时间**
- 下次从游标位置继续向后读取语录数据库

### 同步流程

```
某次同步后，schedule_records 最后一条记录：
  date="2026-05-20", time_end="23:11"

下次 sync 命令执行时：
  1. 读取 schedule_records 最后一条记录 → 得到 "2026-05-20 23:11:00"
  2. 获取该时间之前的最后一条语录（用于理解上下文）
  3. 获取该时间之后的所有新消息
  4. 按日期分组，每组清空旧记录 → 重新生成 → 写入
  5. 完成，下次继续从最新的最后一条记录开始
```

### 好处
- 数据完全由语录驱动，不存在"已处理到哪"的额外状态
- schedule_records 本身就是"处理到哪里"的答案
- 重启/换环境不会丢失游标位置

---

## 触发词

- "作息"、"作息报告"、"作息记录"
- "今天干了什么"、"昨天时间怎么过的"
- "这周作息怎么样"、"近期生活规律吗"
- "作息分析"、"作息统计"

---

## CLI 命令

### 1. 初始化数据库
```bash
python3 scripts/schedule_cli.py init
```

### 2. 增量同步（从最后记录继续）
```bash
python3 scripts/schedule_cli.py sync
# 自动找到 schedule_records 中最后一条记录的时间
# 从该时间点之后读取语录 → 分析 → 写入
```

### 3. 同步指定日期
```bash
python3 scripts/schedule_cli.py sync 2026-05-20
# 清空该日期旧记录，重新从语录生成
```

### 4. 扫描过去N天
```bash
python3 scripts/schedule_cli.py sync-days 7
```

### 5. 查看指定日期作息
```bash
python3 scripts/schedule_cli.py list [YYYY-MM-DD]
# 默认今天
```

### 6. 查看每日摘要
```bash
python3 scripts/schedule_cli.py summary [YYYY-MM-DD]
```

### 7. 时间轴展示
```bash
python3 scripts/schedule_cli.py timeline [YYYY-MM-DD]
```

### 8. 完整报告
```bash
python3 scripts/schedule_cli.py report [YYYY-MM-DD]
```

### 9. 日期范围统计
```bash
python3 scripts/schedule_cli.py range <开始日期> <结束日期>
```

### 10. 数据库状态
```bash
python3 scripts/schedule_cli.py status
```

---

## 分类规则

AI 根据消息内容关键词判断分类：

| 分类 | 关键词 |
|------|------|
| 睡眠 | 睡觉、睡眠、躺、入睡、困、休息 |
| 工作 | 工作、写代码、上班、开会、改bug、需求 |
| 学习 | 学习、复习、看书、课程、刷题 |
| 运动 | 骑行、骑车、跑步、锻炼、俯卧撑 |
| 通勤 | 出发、到达、骑车上班、通勤 |
| 餐饮 | 吃饭、午餐、早餐、晚餐、外卖、做饭 |
| 娱乐 | 游戏、刷手机、看视频、B站、抖音 |
| 社交 | 女朋友、洋洋、约会、聊天 |
| 健康 | 医院、看病、检查 |
| 洗漱 | 洗澡、刷牙、洗脸 |
| 兴趣爱好 | 技能、SKILL、研究、折腾、优化 |
| 未知 | 无关键词匹配 |

---

## 睡眠归属规则

- 睡眠记录归属于**就寝那天**
- 例如：5月20日凌晨1点睡觉，记录在5月20日
- 早上7点起床，记录在5月20日（就寝日）

---

## 与其他技能的联动

| 联动技能 | 角色 |
|------|------|
| daily-recorder-openclaw | 数据源，读取其 user_messages 表 |
| 饼干记账 | 消费记录可辅助判断活动时间段 |
| 卡路里 | 可结合作息数据分析饮食习惯 |

---

## 注意事项

1. **分类关键词还在优化中**——部分消息可能被归为"未知"，需要根据实际运行效果调整关键词库

2. **时间精度**——消息时间使用毫秒时间戳（13位），end_time 由下一条消息时间或当前时间+30分钟估算

3. **重新生成**——sync 命令会先清空目标日期的旧记录，保证数据一致性