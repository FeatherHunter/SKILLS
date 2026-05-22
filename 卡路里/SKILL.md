---
name: 卡路里
description: 卡路里与营养追踪技能。当用户提及"卡路里"、或描述饮食/体重/运动/营养相关意图时触发。记录每日饮食热量、蛋白质、碳水、脂肪摄入，查询今日/历史摄入摘要；记录体重并查看趋势、对比、目标进度；记录运动消耗并查看运动报表；设置每日营养目标和体重目标。当用户说"醒了"、"睡醒了"、"起床啦"等起床唤醒词时，自动查询数据库计算睡眠时长并确认记录。
metadata: { "openclaw": { "emoji": "🍎", "requires": { "python": ">=3.7" } } }
---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 🤝 卡路里技能帮助

> 用户说"卡路里 help"时显示本帮助

---

## 记录饮食
"吃了碗米饭" / "中午吃了biangbiang面" / "下午吃了包薯片" / 发营养成分表图片

## 删除记录
"删掉那条记录" / "删除ID 3"

## 查看今日记录
"今天吃了什么" / "list"

## 查询今日摘要
"今天吃了多少卡" / "今日摘要" / "今天还能吃多少"

## 查询历史
"最近7天吃了什么" / "这周热量多少"

## 搜索食品
"查一下鸡胸肉的热量" / "米饭有多少卡" / "可乐的营养成分"

## 添加食品到库
"把这个存到食品库" / "添加营养成分表"

## 更新食品库
"更新ID 1的热量" / "修改一下这个食品"

## 查看食品库
"看看食品库里有什么" / "list-products"

## 记录体重
"体重70公斤" / "今天69.5kg" / "称了下75"

## 查看体重历史
"体重历史" / "最近30天体重"

## 记录运动
"今天骑行了40分钟" / "跑了30分钟" / "做了30个俯卧撑"

## 查看运动汇总
"这周运动了多少" / "运动摘要"

## 设置每日目标
"每天吃1800卡" / "goal 2000 150 200 60"

## 设置体重目标
"我想瘦到70公斤" / "目标69.5kg年底达成"

## 体重目标进度
"离目标还差多少" / "按现在速度多久能到" / "目标有没有戏"

## 体重趋势
"体重趋势" / "最近7天体重趋势" / "一个月体重趋势" / "最近3个月体重趋势" / "5月1日到5月9日体重趋势" / "同期体重对比"

## 体重对比
"体重对比" / "最近7天vs上个月" / "这周和上周比" / "和上月同期比怎么样"

## 目标进度
"目标进度" / "离目标还差多少" / "按现在速度多久能到"

## 体重波动
"体重波动" / "最近1个月体重稳定吗" / "有没有大起大落"

## 热量趋势
"热量趋势" / "最近7天热量趋势" / "一个月热量趋势" / "这周吃了多少" / "同期热量对比"

## 营养配比
"营养配比" / "最近7天营养配比" / "一个月营养配比" / "蛋白质够吗" / "碳水是不是吃多了" / "脂肪比例" / "同期营养配比"

## 食物排行榜
"食物排行榜" / "最近7天什么最胖" / "一个月热量炸弹" / "最近吃什么最容易胖" / "同期食物排行"

## 低热量榜
"低热量榜" / "最近7天健康食物" / "一个月可以多吃的" / "有什么可以多吃的"

## 频繁吃榜
"频繁吃榜" / "最近7天什么吃得最多" / "一个月最常吃什么" / "我最常吃什么"

## 高碳水榜
"高碳水榜" / "最近7天碳水最高" / "一个月碳水炸弹" / "哪些碳水多"

## 高蛋白榜
"高蛋白榜" / "最近7天蛋白质最高" / "一个月蛋白质榜" / "哪些蛋白质多"

## 热量缺口
"热量缺口" / "最近7天缺口多大" / "一个月缺口" / "少吃了多少" / "同期缺口对比"

## 运动趋势
"运动趋势" / "最近7天运动趋势" / "一个月运动趋势" / "这周锻炼了几天" / "同期运动对比"

## 运动类型
"运动类型" / "最近7天做什么运动最多" / "一个月运动类型" / "骑行多还是跑步多"

## 运动贡献
"运动贡献" / "最近7天运动贡献" / "一个月运动贡献" / "运动帮我消耗了多少" / "运动占比多少"

## dashboard
"dashboard" / "最近7天综合报告" / "一个月综合报告" / "给我看看整体情况" / "同期综合报告"

## 健身目标
"设置俯卧撑目标" / "健身目标" / "每天做50个俯卧撑" / "暂停健身目标"

## 睡眠记录
"昨晚睡了多久" / "记录睡眠" / "睡眠7小时" / "昨晚11点睡的"

---

# 卡路里 - 热量追踪技能 v2.0

## 功能概述

- **食物记录**：记录热量、蛋白质、碳水、脂肪（克为单位）
- **每日目标**：设置热量和三大宏量营养素目标
- **体重追踪**：记录体重，自动计算BMI
- **健身目标**：设置每日/每周/每月/长期健身目标，支持暂停/进行中状态
- **睡眠记录**：记录每日睡眠时长和就寝/起床时间，**睡眠归属于就寝那天**
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
├── nutrition_products  # 食品营养成分库
├── fitness_goals        # 健身目标（每日/每周/每月/长期）
└── sleep_records        # 睡眠记录（归属于就寝日）
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

### fitness_goals 表（健身目标）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| name | TEXT | 目标名称，如"每日俯卧撑" |
| goal_type | TEXT | 类型：daily/weekly/monthly/longterm |
| exercise_type | TEXT | 运动类型：俯卧撑/骑行/跑步等 |
| target_unit | TEXT | 单位：个/分钟/公里 |
| target_value | INTEGER | 目标值，如50 |
| start_date | TEXT | 开始日期 |
| end_date | TEXT | 截止日期（NULL表示永久） |
| status | TEXT | 状态：active/paused |
| note | TEXT | 备注 |
| created_at | INTEGER | 创建时间戳 |
| updated_at | INTEGER | 更新时间戳 |

### sleep_records 表（睡眠记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| date | TEXT | 日期（YYYY-MM-DD，**归属就寝日**） |
| sleep_hours | REAL | 睡眠时长（小时） |
| bedtime | TEXT | 就寝时间（HH:MM） |
| wake_time | TEXT | 起床时间（HH:MM） |
| note | TEXT | 备注 |
| created_at | INTEGER | 创建时间戳 |
| updated_at | INTEGER | 更新时间戳 |

> **睡眠归属规则**：睡眠记录归属于**就寝那天**，而非起床日。例如5月11日23:30入睡，5月12日07:00醒来，记录在5月11日。

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

### 健身目标 CLI
```bash
# 添加目标
python scripts/fitness_goals.py add "每日俯卧撑" --type daily --exercise 俯卧撑 --unit 个 --target 50 --start 2026-05-11

# 查询目标
python scripts/fitness_goals.py list                           # 所有
python scripts/fitness_goals.py list --type daily              # 按类型
python scripts/fitness_goals.py list --status active           # 按状态

# 更新目标
python scripts/fitness_goals.py update 1 --target 60          # 修改目标值
python scripts/fitness_goals.py update 1 --status paused      # 暂停目标

# 删除目标
python scripts/fitness_goals.py delete 1
```

### 睡眠记录 CLI
```bash
# 添加睡眠记录（归属就寝日）
python scripts/sleep_tracker.py add 2026-05-11 --hours 7.5 --bed 23:30 --wake 07:00

# 更新睡眠记录
python scripts/sleep_tracker.py update 2026-05-11 --hours 8 --note "睡得不错"

# 查询睡眠记录
python scripts/sleep_tracker.py list --days 7
```

> **睡眠归属规则**：睡眠归属于**就寝那天**。例如"昨晚11:30睡的，今天7:00醒"，记录在就寝日（昨晚的日期）。

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

### 触发场景：用户要管理健身目标

触发词：
- "健身目标"、"设置俯卧撑目标"、"添加运动目标"
- "每天做50个俯卧撑"

操作步骤：
1. 解析用户输入，提取：目标名称、类型、目标值、运动类型
2. 执行：`python3 workspace/skills/卡路里/scripts/fitness_goals.py add <名称> --type <类型> --exercise <运动> --unit <单位> --target <值> --start <日期>`
3. 目标类型：daily/weekly/monthly/longterm
4. 状态只有 active 和 paused（没有completed）

### 触发场景：用户要记录睡眠

触发词：
- "昨晚睡了多久"、"记录睡眠"
- "昨晚11点睡的"、"睡眠7小时"
- **起床唤醒词（自动查询睡眠时长）**："醒了"、"睡醒了"、"起床啦"、"起来了"、"我醒了"

**起床唤醒词处理流程（被动确认式A方案）：**
1. 检测到上述唤醒词时，立即查询 录音机 数据库
2. 找到"最后一次人类消息"的时间（入睡信号）和当前唤醒消息的时间（起床信号）
3. 计算睡眠时长 = 起床时间 - 入睡前最后一条消息时间
4. 向用户确认：「检测到你刚才睡了X小时，要不要记录？」
5. 用户确认后，执行：`python3 workspace/skills/卡路里/scripts/sleep_tracker.py add <就寝日期> --hours <时长> --bed <就寝时间> --wake <起床时间>`
6. 睡眠归属于就寝那天
7. 确认语中**不提及"卡路里"**三个字，直接问"要不要记录"

**普通触发词处理流程：**
1. 解析用户输入，提取：就寝日期、睡眠时长、就寝时间、起床时间
2. **关键**：睡眠归属于**就寝那天**，不是起床日
3. 执行：`python3 workspace/skills/卡路里/scripts/sleep_tracker.py add <就寝日期> --hours <时长> --bed <就寝时间> --wake <起床时间>`
4. 返回确认信息

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

---

## TypeScript 配置生成

当以下情况发生时，应运行 `python3 scripts/generate_ts_config.py` 生成/更新 `config-calorie.ts`：

**触发场景**：
- 表结构变了（增/删/改字段）
- 数据库表数量变了
- 技能数据库路径变了
- SkillBoard 报错说缺字段

**生成后**：
- 检查输出确认7张表都在
- 如发现 TS 格式问题，手动修正或重新生成

**注意**：queries/actions/views 部分由 AI 根据表能力自动设计，如有不合理处让 AI 重新读取表结构后调整。