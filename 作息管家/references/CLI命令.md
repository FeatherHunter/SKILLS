# CLI 命令

> 本文件列出所有可用的命令行接口。**所有命令通过 `python3 scripts/schedule_cli.py` 调用。**

---

## 命令列表

### 1. 初始化数据库

```bash
python3 scripts/schedule_cli.py init
```

**作用**：创建 schedule_records、daily_summary、schedule_plans 表（已存在则跳过）

---

### 2. 准备同步消息（供 AI 分析，始终分页）

```bash
# 默认: 从数据库游标到当前时间, 第1页, 每页200条
python3 scripts/schedule_cli.py prepare-messages

# 指定开始时间到当前时间
python3 scripts/schedule_cli.py prepare-messages <开始时间>

# 指定时间范围
python3 scripts/schedule_cli.py prepare-messages <开始时间> <结束时间>

# 分页参数
python3 scripts/schedule_cli.py prepare-messages <开始时间> <结束时间> --page 2
python3 scripts/schedule_cli.py prepare-messages <开始时间> <结束时间> --page 1 --page-size 100

# 时间格式: YYYY-MM-DD HH:MM:SS  或  YYYY-MM-DD
# 示例: python3 scripts/schedule_cli.py prepare-messages 2026-05-09 2026-05-22
```

**作用**：
- 查询游标位置的最后一条记录（或指定开始时间）
- 获取开始时间前10条消息（上下文）+ 开始时间到结束时间的消息（分页）
- 输出 JSON 格式供 AI 分析
- JSON 中含 `pagination` 元数据，`has_next=true` 时需用 `--page N` 获取下一页

**输出**：
```
开始时间: 2026-05-09 00:00:00
结束时间: 2026-05-22 15:59:30

上下文消息: 10 条（仅供参考，不处理）
待处理消息: 200 条（第1页/20页，每页200条，共3873条）

【JSON输出开始】
{ "pagination": { "page": 1, "total_pages": 20, "has_next": true, ... }, ... }
【JSON输出结束】

AI分析说明:
- ⚠️ 还有下一页! 处理完本页后，请用 --page 2 获取下一页
```

---

### 3. 查看指定日期作息

```bash
python3 scripts/schedule_cli.py list [YYYY-MM-DD]
# 默认今天
```

**输出示例**：
```
============================================================
📅 2026-05-22 作息记录
============================================================
  😴 01:00~07:38 [睡眠] ✓
     睡觉
  💕 07:38~08:47 [社交] ✓
     确认睡眠信息、回复消息
  🚴 08:47~09:05 [通勤] ✓
     骑车去公司

  共 3 块, 约 9h49m
```

---

### 4. 详细展示（含分析推理）

```bash
python3 scripts/schedule_cli.py detail [YYYY-MM-DD]
```

**作用**：显示每条记录的 AI 分析推理过程

---

### 5. 查看每日摘要

```bash
python3 scripts/schedule_cli.py summary [YYYY-MM-DD]
```

**输出示例**：
```
📊 2026-05-22 作息摘要
==================================================
  😴 睡眠: 7h0m
  💼 工作: 4h0m
  🚴 通勤: 0h36m
  🍽️ 餐饮: 1h0m
  🎮 娱乐: 1h0m
  ❓ 未知: 1h0m

  总计: 15h36m
```

---

### 6. 时间轴展示

```bash
python3 scripts/schedule_cli.py timeline [YYYY-MM-DD]
```

**输出示例**：
```
⏰ 2026-05-22 时间轴
============================================================
  00:00 ▓▓▓ 😴睡眠
  01:00 ▓▓▓ 😴睡眠
  02:00 ▓▓▓ 😴睡眠
  ...
  08:00 ▓▓▓ 💕社交
  09:00 ▓▓▓ 🚴通勤
  10:00 ▓▓▓ 💼工作
```

---

### 7. 完整报告

```bash
python3 scripts/schedule_cli.py report [YYYY-MM-DD]
```

**作用**：综合 list + summary + timeline

---

### 8. 日期范围统计

```bash
python3 scripts/schedule_cli.py range <开始日期> <结束日期>
```

**输出示例**：
```
📅 2026-05-20 ~ 2026-05-22 作息汇总
============================================================
  2026-05-20: 睡眠7h 工作8h 娱乐2h 总17h
  2026-05-21: 睡眠6h 工作6h 学习1h 娱乐3h 总16h
  2026-05-22: 睡眠7h 工作4h 撸猫0h 娱乐1h 总12h
```

---

### 9. 数据库状态

```bash
python3 scripts/schedule_cli.py status
```

**输出示例**：
```
作息管家 数据库状态
==================================================
  数据库: /path/to/schedule_data.db
  总记录数: 45
  已记录天数: 3
  日期范围: 2026-05-20 ~ 2026-05-22
  最后记录: 2026-05-22 10:49 工作、看工作消息、优化skill
```

---

### 10. 查询计划作息（新增）

```bash
python3 scripts/schedule_cli.py query-plans <日期1,日期2,...>
# 示例：查询单天
python3 scripts/schedule_cli.py query-plans 2026-05-22
# 示例：查询多天
python3 scripts/schedule_cli.py query-plans 2026-05-20,2026-05-21,2026-05-22
```

**输出示例**：
```
============================================================
📅 2026-05-22 计划作息
============================================================
  00:00 - 01:00  睡觉
  01:00 - 02:00  (未规划)
  ...
  08:00 - 09:00  30min通勤(骑车)+30min工作
  09:00 - 10:00  40min改bug+20min摸鱼
  ...
```

---

### 11. 新增/更新计划作息（新增）

```bash
# 简单方式（只填非空小时，其他留空）
python3 scripts/schedule_cli.py upsert-plan <日期> "睡觉" "" "" "" "" "" "" "通勤+工作" "工作"

# JSON方式（推荐）
python3 scripts/schedule_cli.py upsert-plan <日期> --json '{"hour_0": "睡觉", "hour_8": "30min通勤+30min工作", "hour_9": "40min工作+20min摸鱼"}'
```

**效果**：
- 日期不存在 → **插入**新计划
- 日期已存在 → **更新**计划（只更新提供的字段，保留其他）
- ⚠️ **不提供删除接口**

**示例**：
```bash
# 新增今日计划
python3 scripts/schedule_cli.py upsert-plan 2026-05-22 --json '{"hour_0": "睡觉", "hour_8": "通勤", "hour_9": "工作"}'

# 更新某天计划（只改hour_9，其他保留）
python3 scripts/schedule_cli.py upsert-plan 2026-05-22 --json '{"hour_9": "开会+改bug"}'
```