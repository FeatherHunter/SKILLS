---
name: 卡路里
description: 卡路里技能。当用户提到"卡路里"时必须使用此技能，追踪每日热量和蛋白质摄入、设定目标、记录体重。使用 SQLite 数据库存储，支持每日自动汇总。
metadata: { "openclaw": { "emoji": "🍎", "requires": { "python": ">=3.7" } } }
---

## 参考文档

- [分析函数接口文档](references/analysis_api.md) — 11种分析维度详解
- [数据库结构](references/database_schema.md) — 表设计/索引/关系

---

# 卡路里 - 热量追踪技能 v2.0

## 功能概述

- **食物记录**：记录热量、蛋白质、碳水、脂肪（克为单位）
- **每日目标**：设置热量和三大宏量营养素目标
- **体重追踪**：记录体重，自动计算BMI
- **数据分析**：3大类11种分析维度
  - 体重变化分析（趋势/同期对比/目标进度/波动）
  - 饮食分析（热量趋势/营养素占比/食物TOP榜/热量缺口）
  - 运动分析（运动趋势/类型分布/缺口贡献）
  - 综合报告（dashboard整合四维度仪表盘）

## 数据库结构

```
calorie_data.db
├── entries              # 食物记录
├── daily_goal           # 每日目标（含体重目标）
├── weight_log           # 体重记录
├── exercise_log         # 运动记录
└── nutrition_products  # 食品营养成分库
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
| weight_goal | REAL | 体重目标（如69.5kg） |
| goal_deadline | TEXT | 目标截止日期（YYYY-MM-DD） |

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

### exercise_log 表（运动记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| date | TEXT | 日期（YYYY-MM-DD） |
| time | TEXT | 时间（HH:MM:SS） |
| exercise_type | TEXT | 运动类型（如骑行、跑步） |
| duration_minutes | INTEGER | 运动时长（分钟） |
| calories_burned | INTEGER | 消耗卡路里 |
| note | TEXT | 备注 |
| reps | INTEGER | 动作次数/组数 |
| created_at | TEXT | 创建时间 |

### nutrition_products 表（食品营养成分库）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| product_name | TEXT | 产品名称 |
| brand | TEXT | 品牌（可选） |
| calories | REAL | 热量（千卡/100g） |
| protein | REAL | 蛋白质（克/100g） |
| fat | REAL | 脂肪（克/100g） |
| saturated_fat | REAL | 饱和脂肪（克/100g，可NULL） |
| carbohydrates | REAL | 碳水化合物（克/100g） |
| sugar | REAL | 糖（克/100g，可NULL） |
| dietary_fiber | REAL | 膳食纤维（克/100g，可NULL） |
| sodium | REAL | 钠（毫克/100g） |
| note | TEXT | 备注 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

> **营养学知识**：糖是碳水化合物的子部分，饱和脂肪是脂肪的子部分。数据库存储独立数值，业务逻辑在应用层处理。

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

### 设定体重目标
```bash
# 直接调用 Python 函数
set_weight_goal(69.5, '2026-11-25')  # 目标69.5kg，截止2026-11-25
set_weight_goal(69.5)               # 只有目标体重，不设截止日期
```

### 体重历史
```bash
python scripts/calorie_tracker.py weight-history 30
```

### 运动记录
```bash
# 直接调用 Python 函数
add_exercise('骑行', 300, 40)           # 骑行40分钟消耗300卡
add_exercise('钻石俯卧撑', 100, 30, reps=20)  # 20个30分钟100卡
```

### 分析接口（11种分析维度）
```python
# 体重变化分析
weight_analysis(start_date, end_date, analysis_type='trend')
# analysis_type: trend | compare | milestone | volatility

# 饮食分析
diet_analysis(start_date, end_date, analysis_type='calorie_trend')
# analysis_type: calorie_trend | macro_ratio | food_ranking | deficit_analysis

# 运动分析
exercise_analysis(start_date, end_date, analysis_type='exercise_trend')
# analysis_type: exercise_trend | type_breakdown | deficit_contribution

# 综合报告
dashboard(start_date, end_date)  # 整合四维度仪表盘
```

### 热量历史
```bash
python scripts/calorie_tracker.py history 7
```

### 添加食品营养成分表
```bash
python scripts/calorie_tracker.py add-product "可口可乐" "可口可乐" 42 0 0 0 10.6 10.6 0 20 "经典款330ml"
# 参数：产品名称 品牌 热量 蛋白质 脂肪 饱和脂肪 碳水 糖 膳食纤维 钠 备注
```

### 查询食品营养成分
```bash
python scripts/calorie_tracker.py search-product "可乐"
# 参数：搜索关键词
```

### 更新食品营养成分
```bash
python scripts/calorie_tracker.py update-product 1 --calories 45 --note "更新为新包装"
# 参数：产品ID + 要更新的字段
```

## AI 触发指引

**重要提示**：技能目录在 `workspace/skills/卡路里/`。所有命令使用此路径前缀。

### 触发场景：用户提到"卡路里"或记录饮食

触发词：
- "卡路里"、"热量"
- "吃了什么"、"记录饮食"
- "我吃了..."
- "记录吃了..."

**完整流程（重要）**：

#### Step 1：解析用户输入
提取：食物名、克数（如有）

#### Step 2：模糊查询 nutrition_products 表
执行：`python3 workspace/skills/卡路里/scripts/calorie_tracker.py search-product <食物名>`

#### Step 3：根据查询结果分流

**Path A：找到匹配结果（≥1条）**
```
列表显示所有匹配项，格式：
  ID | 产品名称 | 品牌 | 热量
请用户选择是哪个（或输入新的）
         ↓
用户确认后，询问克数（如用户未提供）
         ↓
计算：热量/100 × 克数
         ↓
执行 add 命令记录到 entries 表
         ↓
返回今日汇总
```

**Path B：库中没找到，用户提供了营养成分表图片**
```
AI：未找到该食品，请提供营养成分表图片
         ↓
用户发送图片
         ↓
AI 调用 mmx vision describe 识别：
  mmx vision describe --image <图片路径> \
    --prompt "请识别这张营养成分表，提取：产品名称、品牌、热量(千卡)、蛋白质(克)、脂肪(克)、饱和脂肪(克)、碳水化合物(克)、糖(克)、膳食纤维(克)、钠(毫克)。请以JSON格式返回。"
         ↓
AI 展示识别结果，确认是否正确
         ↓
用户确认后，询问是否保存到营养成分库
         ↓
执行 add-product 命令存入 nutrition_products 表
         ↓
继续 Path A 流程（让用户确认克数 → 计算 → add）
```

**Path C：库中没找到，用户无法提供营养成分表**
```
AI：未找到该食品，请问有营养成分表图片吗？
         ↓
用户：没有图片 / 不知道营养成分 / 不确定
         ↓
交互式讨论：
  - 询问用户大概吃了多少克
  - 可以描述食物外观、大小、份量
  - 讨论后估算一个合理克数
  - 若讨论不出结果 → 跳过本次记录
         ↓
若讨论出克数：
  AI 调用 mmx search 查询该食品参考营养数据：
    mmx search query --q "<食物名> 营养成分表 每100克热量"
         ↓
展示参考数据（注明：仅供参考，不存入营养成分库）
         ↓
用户确认后，计算热量并执行 add 命令
         ↓
返回：✓ 已记录（参考数据） + 今日汇总
```

**注意**：Path C 查询到的营养数据**不存入** nutrition_products 表，因数据来源为外部搜索，结果仅供参考。

#### Step 4：返回确认信息
执行 add 命令后，返回：
```
✓ 已记录：<食物名> (<热量>卡, <克数>克)
餐次：<早/午/晚/下午茶/夜宵>
今日：<热量>/<目标>卡 | 蛋白<蛋白>/<目标>g | 碳<碳>/<目标>g | 脂<脂>/<目标>g
```

### 触发场景：用户要添加食品营养成分表

触发词：
- "添加营养成分"、"录入营养成分"
- "这个食品的营养成分是..."
- 发营养成分表图片

操作步骤：
1. 解析用户输入或图片，提取：产品名称、品牌、热量、蛋白质、脂肪、饱和脂肪、碳水、糖、膳食纤维、钠、备注
2. 执行：`python3 workspace/skills/卡路里/scripts/calorie_tracker.py add-product <产品名> <品牌> <热量> <蛋白质> <脂肪> <饱和脂肪> <碳水> <糖> <膳食纤维> <钠> [备注]`
3. 返回确认信息

### 触发场景：用户要查询/搜索营养成分

触发词：
- "查询营养成分"、"搜索营养成分"
- "这个食品有多少卡"
- "XXX的营养成分是什么"

操作步骤：
1. 解析用户输入，提取搜索关键词
2. 执行：`python3 workspace/skills/卡路里/scripts/calorie_tracker.py search-product <关键词>`
3. 返回匹配的食品列表

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

---

## 高级配置

### 数据库路径查找顺序

1. **环境变量** `SKILLS_DB_PATH`（最高优先级）
   - 设置后所有技能db统一存放
   - 例：`export SKILLS_DB_PATH=/mnt/d/2Study/Notes/.db`

2. **技能所在目录**（默认）
   - 开箱即用，适合他人clone后直接使用

3. **父目录层层查找 `.db` 文件夹**
   - 适合集中管理多个技能的db文件
   - 脚本从技能目录向上搜索，找到 `.db` 目录为止

### 推荐做法

将db文件统一存放在 `~/.db/` 或项目根目录的 `.db/` 文件夹中：

```
D:\2Study\Notes\SKILLS\
├── .db\
│   ├── 居家管家.db
│   ├── 卡路里.db
│   └── 饼干记账.db
├── 居家管家\
├── 卡路里\
└── 饼干记账\
```

设置环境变量后，所有技能自动使用统一目录：

```bash
# Windows (WSL)
export SKILLS_DB_PATH=/mnt/d/2Study/Notes/.db

# Windows (PowerShell)
$env:SKILLS_DB_PATH="D:\2Study\Notes\.db"
```

---

## 联动说明

本技能可能与以下技能产生联动：

| 技能 | 可能的联动场景 |
|------|--------------|
| 居家管家 | 购买食品时可同步记录物品位置和数量 |
| 饼干记账 | 记录饮食消费时可同步记录支出金额 |

**处理原则**：在处理用户请求时，主动思考是否需要与上述技能联动。如判断需要联动，先完成主技能操作，再询问用户是否需要触发关联技能的相应功能。不要强制联动，尊重用户意图。

---

## Lint 检查（数据健康检查）

**触发词**：`"健康检查"`、`"检查数据"`、`"lint"`、`"数据审计"`

### 检查项

**1. 数据新鲜度检查**
- 今日是否记录体重（weight_log）
- 今日是否记录饮食（entries）
- 今日是否记录运动（exercise_log）

**2. 体重目标进度**
- 调用 `weight_milestone()` 检查目标进度
- 当前体重与目标差距、预计达成时间

**3. 热量趋势预警**
- 调用 `diet_calorie_trend()` 检查近7天热量趋势
- 超标连续3天以上则预警

**4. 热量缺口分析**
- 调用 `diet_deficit_analysis()` 检查缺口
- 缺口长期为正（摄入 > 消耗）需提示

**5. 运动连续性**
- 调用 `exercise_trend()` 检查运动记录
- 连续7天以上未运动则预警

### 处理原则
- 发现问题后列出清单，让用户确认是否需要处理
- 不要自动修改，只能建议
- 用户说"检查一下"时执行，不主动触发