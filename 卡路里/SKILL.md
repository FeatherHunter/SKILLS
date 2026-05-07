---
name: 卡路里
description: 卡路里技能。当用户提到"卡路里"时必须使用此技能，追踪每日热量和蛋白质摄入、设定目标、记录体重。使用 SQLite 数据库存储，支持每日自动汇总。
metadata: { "openclaw": { "emoji": "🍎", "requires": { "python": ">=3.7" } } }
---

# 卡路里 - 热量追踪技能 v2.0

## 功能概述

- **食物记录**：记录热量、蛋白质、碳水、脂肪（克为单位）
- **每日目标**：设置热量和三大宏量营养素目标
- **体重追踪**：记录体重，自动计算BMI
- **餐次自动推断**：根据时间自动判断早/午/晚餐
- **历史统计**：查看每日/每周/每月趋势

## 数据库结构

```
calorie_data.db
├── entries       # 食物记录
├── daily_goal    # 每日目标
└── weight_log   # 体重记录
```

### entries 表（食物记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| date | TEXT | 日期（YYYY-MM-DD） |
| time | TEXT | 时间（HH:MM:SS） |
| food_name | TEXT | 食物名称 |
| grams | INTEGER | 重量（克） |
| calories | INTEGER | 热量（卡） |
| protein | INTEGER | 蛋白质（克） |
| carbs | INTEGER | 碳水化合物（克） |
| fat | INTEGER | 脂肪（克） |
| note | TEXT | 备注 |

### daily_goal 表（每日目标）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 固定为1 |
| calorie_goal | INTEGER | 热量目标（默认1800卡） |
| protein_goal | INTEGER | 蛋白质目标（默认156克） |
| carbs_goal | INTEGER | 碳水目标（默认200克） |
| fat_goal | INTEGER | 脂肪目标（默认60克） |

### weight_log 表（体重记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| date | TEXT | 日期（YYYY-MM-DD） |
| time | TEXT | 时间（HH:MM:SS） |
| weight_kg | REAL | 体重（公斤） |
| height_cm | REAL | 身高（厘米） |
| bmi | REAL | BMI（自动计算） |
| note | TEXT | 备注 |

## 命令行用法

### 添加食物记录
```bash
python scripts/calorie_tracker.py add "鸡胸肉" 165 31 0 3 150
# 参数：食物名 热量 蛋白质 碳水 脂肪 克数
```

### 今日摘要
```bash
python scripts/calorie_tracker.py summary
```

### 设置每日目标
```bash
python scripts/calorie_tracker.py goal 1800 156 200 60
# 参数：热量 蛋白质 碳水 脂肪
```

### 记录体重
```bash
python scripts/calorie_tracker.py weight 70 178
# 参数：体重(kg) 身高(cm)
```

### 体重历史
```bash
python scripts/calorie_tracker.py weight-history 30
```

### 热量历史
```bash
python scripts/calorie_tracker.py history 7
```

## AI 触发指引

**重要提示**：技能目录在 `workspace/skills/卡路里/`。所有命令使用此路径前缀。

### 触发场景：用户提到"卡路里"或记录饮食

触发词：
- "卡路里"、"热量"
- "吃了什么"、"记录饮食"
- "我吃了..."

操作步骤：
1. 解析用户输入，提取：食物名、克数、热量、蛋白质、碳水、脂肪
2. 如果用户没说具体数值，AI 估算
3. 执行：`python3 workspace/skills/卡路里/scripts/calorie_tracker.py add <食物> <热量> <蛋白质> [碳水] [脂肪] [克数]`
4. 返回今日汇总

### 触发场景：用户要查看今日摄入

触发词：
- "今天吃了多少卡"、"今日热量"
- "今日摘要"

操作步骤：
1. 执行：`python3 workspace/skills/卡路里/scripts/calorie_tracker.py summary`

### 触发场景：用户要设置目标

触发词：
- "设置目标"、"每天吃多少"
- "热量目标"、"蛋白质目标"

操作步骤：
1. 从对话中提取目标数值
2. 执行：`python3 workspace/skills/卡路里/scripts/calorie_tracker.py goal <热量> [蛋白质] [碳水] [脂肪]`

### 触发场景：用户要记录体重

触发词：
- "体重"、"多少公斤"
- "称了下"、"今天体重"

操作步骤：
1. 从输入中提取体重（公斤）和身高（如果知道）
2. 执行：`python3 workspace/skills/卡路里/scripts/calorie_tracker.py weight <体重> [身高]`
3. 自动计算BMI

## 餐次自动推断

根据时间自动判断餐次：

| 时间 | 餐次 |
|------|------|
| 06:00-10:00 | 早餐 |
| 10:00-14:00 | 午餐 |
| 14:00-18:00 | 下午茶 |
| 18:00-22:00 | 晚餐 |
| 22:00-06:00 | 夜宵 |

## 蛋白质估算参考

如果用户没说蛋白质，按以下比例估算（g/100卡）：
- 鸡胸肉/鱼：~20g
- 牛肉：~15g
- 鸡蛋：~6g/个
- 米饭/面条：~3g/100g
- 蔬菜：~1g/100g

## 每日目标参考值

根据用户信息（195斤/97.5kg，久坐）：

| 目标 | 数值 | 说明 |
|------|------|------|
| 热量 | 1800卡 | 减肥缺口500卡 |
| 蛋白质 | 156克 | 约1.6g/kg体重 |
| 碳水 | 200克 | 约2g/kg体重 |
| 脂肪 | 60克 | 约30%热量 |

## 示例对话

**用户**：吃了碗米饭
**AI**：好的！米饭大概 200克，232卡，4g蛋白，50g碳水，0.5g脂肪
（执行添加命令）
✓ 已记录：米饭 (232卡, 4蛋白, 50碳, 0.5脂, 200克)
今日：232/1800卡 | 蛋白4/156克 | 碳50/200克 | 脂0.5/60克

**用户**：体重70公斤
**AI**：（执行：weight 70 178）
✓ 体重已记录：70.0公斤
BMI：22.1（正常范围）