---
name: 卡路里
description: >
  饮食热量、饮水、体重、运动、睡眠、营养追踪与分析技能。
  触发词：记吃了、拍营养表、删吃的、查今天吃、查吃的记录、查热量历史、记喝水、查今天喝水、查热量、存食品、改食品、查食品库、记体重、查体重历史、查体重趋势、对比体重、查体重波动、设体重目标、查体重目标、记运动、改运动记录、查运动记录、查运动汇总、查运动类型、查运动趋势、设健身目标、查健身目标、改健身目标、删健身目标、记睡眠、改睡眠记录、查睡眠记录、记录起床、查热量趋势、查营养配比、查热量缺口、查食物排行、查高热量榜、查低热量榜、查频繁吃榜、查高碳水榜、查高蛋白榜、查运动分布、查运动贡献、设营养目标、查营养目标、查健康报告、查卡路里数据、记身材照、查身材照、删身材照、改照片标签
metadata: { "openclaw": { "emoji": "🍎", "requires": { "python": ">=3.7" } } }
---

**🔗 联动提示：** 完成本技能主操作后，检查技能路由器（`图片路由/SKILL.md`）的联动规则，判断是否需要联动其他技能（如用户提到食物花费→询问是否记录支出；用户提到买了新食品→询问是否存入食品库）。详见路由器的联动规则表。

## ⚠️ 强制性规定（最高优先级）

1. **HTML 同步**：本技能的所有优化和变动、脚本的所有变动都必须体现在相应的 HTML 页面上。HTML 是技能功能的可视化镜像，任何功能变更若未同步到 HTML 视为未完成。
2. **优先级**：本强制性规定优先级最高，高于下方所有操作规范和功能说明。
3. **变更确认**：对该技能的所有文件、脚本的任何一行修改都需要明确得到用户的 1 次确认，未经确认不得执行写入操作。

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

## 核心原则

- **数据操作只走 CLI**：所有增删改查通过 `scripts/` 下的 Python 脚本执行，禁止直接操作 SQLite
- **睡眠归属就寝日**：睡眠记录归属于就寝那天，不是起床日
- **Path C 参考数据不存库**：外部搜索到的营养数据仅用于本次记录，不写入 nutrition_products
- **起床确认不提卡路里**：唤醒词场景的确认语中不出现"卡路里"三字，直接问"要不要记录"
- **只建议不自动修改**：Lint 检查发现问题后列出清单，让用户决定

---

## 📦 安装与配置

### 依赖

- Python >= 3.7
- 无第三方依赖（仅用标准库 sqlite3、argparse、datetime）

### 配置项

| 环境变量 | 说明 | 
|---------|------|
| `SKILLS_DB_PATH` | 数据库文件所在目录 |

DB 查找顺序：`SKILLS_DB_PATH` 环境变量 → 技能目录 → 父目录 `.db/` 文件夹 → 自动创建 `.db/` 目录。

### 一键安装 prompt

将以下内容发送给 AI 即可安装本技能：

```
请帮我安装卡路里技能：
1. 检查 Python 环境
2. 引导我配置环境变量
3. 显示当前环境变量配置
4. 告诉我如何更改数据目录
```

---

## 🤝 触发词速查表

> 用户说"卡路里 help"时显示本表。全部唤醒词为动词+名词结构。

### 🍚 饮食记录

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记吃了 | 记录饮食（库匹配/图片识别/外部搜索统一入口） | `calorie_tracker.py add` |
| 拍营养表 | 图片识别营养成分表并记录 | `mmx vision describe` → `add` |
| 删吃的 | 删除饮食记录 | `calorie_tracker.py delete` |
| 查今天吃 | 今日饮食摘要（vs 目标） | `calorie_tracker.py summary` |
| 查吃的记录 | 今日逐条饮食记录 | `calorie_tracker.py list` |
| 查热量历史 | 最近 N 天热量摄入历史 | `calorie_tracker.py history` |
| 记喝水 | 记录饮水量（ml） | `calorie_tracker.py water <ml>` |
| 查今天喝水 | 今日饮水量（含在 summary 中） | `calorie_tracker.py summary` |

### 🏷️ 食品库

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 查热量 | 搜索食品营养成分 | `calorie_tracker.py search-product` |
| 存食品 | 添加食品营养成分表到库 | `calorie_tracker.py add-product` |
| 改食品 | 更新食品营养成分 | `calorie_tracker.py update-product` |
| 查食品库 | 列出全部食品营养成分 | `calorie_tracker.py list-products` |

### ⚖️ 体重

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记体重 | 记录体重（自动算 BMI） | `calorie_tracker.py weight` |
| 查体重历史 | 体重历史记录 | `calorie_tracker.py weight-history` |
| 查体重趋势 | 体重趋势分析（均重/日均变化/趋势判断） | `weight_analysis(trend)` |
| 对比体重 | 两时间段体重对比 | `weight_analysis(compare)` |
| 查体重波动 | 体重波动分析（标准差/异常记录） | `weight_analysis(volatility)` |
| 设体重目标 | 设定体重目标和截止日期 | `set_weight_goal()` |
| 查体重目标 | 体重目标达成进度 | `weight_analysis(milestone)` |

### 🏃 运动

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记运动 | 记录运动消耗 | `exercise_tracker.py add` |
| 改运动记录 | 更新运动记录 | `exercise_tracker.py update` |
| 查运动记录 | 查询运动记录（按日期/天数/类型） | `exercise_tracker.py list` |
| 查运动汇总 | 运动汇总统计 | `exercise_tracker.py summary` |
| 查运动类型 | 运动类型统计（分布/总消耗排名） | `exercise_tracker.py stats` |
| 查运动趋势 | 运动热量趋势 | `exercise_tracker.py trend` |

### 💪 健身目标

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 设健身目标 | 添加健身目标（daily/weekly/monthly/longterm） | `fitness_goals.py add` |
| 查健身目标 | 查询健身目标（按类型/状态） | `fitness_goals.py list` |
| 改健身目标 | 更新健身目标 | `fitness_goals.py update` |
| 删健身目标 | 删除健身目标 | `fitness_goals.py delete` |

### 😴 睡眠

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记睡眠 | 记录睡眠时长和就寝/起床时间 | `sleep_tracker.py add` |
| 改睡眠记录 | 更新睡眠记录 | `sleep_tracker.py update` |
| 查睡眠记录 | 查询最近 N 天睡眠记录 | `sleep_tracker.py list` |
| 记录起床 | 起床唤醒：查录音机数据库 → 自动算时长 → 确认记录 | 录音机 → `sleep_tracker.py add` |

### 📊 分析

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 查热量趋势 | 热量摄入趋势（工作日 vs 周末/合规率） | `diet_analysis(calorie_trend)` |
| 查营养配比 | 营养素占比分析（蛋白/碳水/脂肪） | `diet_analysis(macro_ratio)` |
| 查热量缺口 | 热量缺口分析（饮食 vs 运动贡献） | `diet_analysis(deficit_analysis)` |
| 查食物排行 | 食物排行榜（默认高热量榜） | `diet_food_ranking(high_calorie)` |
| 查高热量榜 | 热量炸弹 TOP5 | `diet_food_ranking(high_calorie)` |
| 查低热量榜 | 低热量健康 TOP5 | `diet_food_ranking(low_calorie)` |
| 查频繁吃榜 | 最常吃的食物 TOP5 | `diet_food_ranking(frequent)` |
| 查高碳水榜 | 高碳水食物 TOP5 | `diet_food_ranking(high_carb)` |
| 查高蛋白榜 | 高蛋白食物 TOP5 | `diet_food_ranking(high_protein)` |
| 查运动分布 | 运动类型分布（消耗/频次/时长占比） | `exercise_analysis(type_breakdown)` |
| 查运动贡献 | 运动对热量缺口的贡献占比 | `exercise_analysis(deficit_contribution)` |

### 📋 综合

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 设营养目标 | 设置每日营养目标（热量/蛋白/碳水/脂肪/饮水ml） | `calorie_tracker.py goal` |
| 查营养目标 | 查看当前每日营养目标 | `calorie_tracker.py get_goal()` |
| 查健康报告 | 四维度综合健康仪表盘 | `dashboard()` |
| 查卡路里数据 | 数据健康检查（Lint 5 项） | Lint 检查流程 |

### 📸 身材照片

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记身材照 | 记录身材照片（支持批量） | `body_photo_tracker.py add` |
| 查身材照 | 查看照片历史 | `body_photo_tracker.py list` |
| 删身材照 | 删除照片 | `body_photo_tracker.py delete` |
| 改照片标签 | 修改照片标签 | `body_photo_tracker.py tag` |

---

# 卡路里 - 热量追踪技能 v2.0

## 功能概述

- **食物记录**：记录热量、蛋白质、碳水、脂肪（克为单位）
- **每日目标**：设置热量和三大宏量营养素目标
- **体重追踪**：记录体重，自动计算BMI
- **健身目标**：设置每日/每周/每月/长期健身目标，支持暂停/进行中状态
- **睡眠记录**：记录每日睡眠时长和就寝/起床时间，**睡眠归属于就寝那天**
- **数据分析**：3大类11种分析维度 + dashboard综合报告
- **身材照片**：记录身材照片，支持自定义标签（正面/背面/侧面/手臂等），可生成 GIF 变化动画

## 数据库结构

详见 [`references/database_schema.md`](references/database_schema.md)

共 7 张表：`entries`、`daily_goal`、`weight_log`、`exercise_log`、`nutrition_products`、`fitness_goals`、`sleep_records`

> **初始化说明**：`entries`/`daily_goal`/`weight_log`/`exercise_log`/`nutrition_products` 由 `calorie_tracker.py init_db()` 创建；`fitness_goals` 由 `fitness_goals.py init_table()` 创建；`sleep_records` 由 `sleep_tracker.py init_table()` 创建。

## 命令行用法

### 食物记录
```bash
python scripts/calorie_tracker.py add "鸡胸肉" 165 31 0 3 150   # 食物名 热量 蛋白 碳水 脂肪 克数
python scripts/calorie_tracker.py summary                        # 今日摘要（含饮水）
python scripts/calorie_tracker.py history 7                      # 最近7天历史
python scripts/calorie_tracker.py goal 1800 150 200 60 2000      # 设置目标：热量 蛋白 碳水 脂肪 饮水ml
python scripts/calorie_tracker.py water 500                      # 记录饮水 500ml
```

### 食品库
```bash
python scripts/calorie_tracker.py search-product "可乐"          # 搜索
python scripts/calorie_tracker.py add-product "可口可乐" "可口可乐" 42 0 0 0 10.6 10.6 0 20 "330ml"
python scripts/calorie_tracker.py update-product 1 --calories 45 # 更新
```

### 体重
```bash
python scripts/calorie_tracker.py weight 70 178                  # 记录体重(kg) 身高(cm)
python scripts/calorie_tracker.py weight-history 30              # 最近30天体重
```

### 运动
```bash
python scripts/exercise_tracker.py add --date 2026-05-23 --type 骑行 --calories 300 --minutes 40
python scripts/exercise_tracker.py list --days 7
python scripts/exercise_tracker.py summary --days 7
python scripts/exercise_tracker.py trend --days 7
```

### 健身目标
```bash
python scripts/fitness_goals.py add "每日俯卧撑" --type daily --exercise 俯卧撑 --unit 个 --target 50 --start 2026-05-23
python scripts/fitness_goals.py list --status active
python scripts/fitness_goals.py update 1 --target 60
python scripts/fitness_goals.py delete 1
```

### 睡眠记录
```bash
python scripts/sleep_tracker.py add 2026-05-22 --hours 7.5 --bed 23:30 --wake 07:00
python scripts/sleep_tracker.py update 2026-05-22 --hours 8 --note "睡得不错"
python scripts/sleep_tracker.py list --days 7
```

> **睡眠归属规则**：睡眠归属于**就寝那天**。例如"昨晚11:30睡的，今天7:00醒"，记录在就寝日。

### 身材照片
```bash
python scripts/body_photo_tracker.py add photo1.jpg photo2.jpg --tag 正面 --note "早起"
python scripts/body_photo_tracker.py list --days 30 --tag 正面
python scripts/body_photo_tracker.py delete 1
python scripts/body_photo_tracker.py tag 1 侧面
python scripts/body_photo_tracker.py gif --tag 正面 --start 2026-01-01 --end 2026-05-30
```

### 分析接口（11种维度）
```python
weight_analysis(start, end, 'trend')       # 趋势|compare|milestone|volatility
diet_analysis(start, end, 'calorie_trend') # calorie_trend|macro_ratio|food_ranking|deficit_analysis
exercise_analysis(start, end, 'exercise_trend') # exercise_trend|type_breakdown|deficit_contribution
dashboard(start, end)                      # 综合四维度仪表盘
```

---

## AI 路由规则

**重要提示**：所有命令使用技能目录下的 `scripts/` 路径前缀。

### Step 1：识别功能域

根据用户输入关键词判断功能域：

| 关键词 | 功能域 |
|--------|--------|
| 吃/食物/餐/喝/摄入/卡路里（食物相关） | 🍚 饮食记录 |
| 食品库/营养成分表/存食品 | 🏷️ 食品库 |
| 体重/公斤/kg/BMI/秤 | ⚖️ 体重 |
| 运动/跑步/骑行/俯卧撑/消耗（运动相关） | 🏃 运动 |
| 健身目标/每日目标/俯卧撑目标/深蹲目标 | 💪 健身目标 |
| 睡/觉/起床 | 😴 睡眠 |
| 趋势/排行/缺口/配比/分布/贡献 | 📊 分析 |
| 仪表盘/整体情况/报告/目标（营养） | 📋 综合 |
| 身材照/体型照/身体照片 | 📸 身材照片 |

### Step 2：域内精确匹配

在已识别的域内，按触发词速查表精确匹配唤醒词，执行对应 CLI。

### Step 3：歧义消解

| 歧义场景 | 判断规则 |
|---------|---------|
| "查热量" vs "查热量趋势" | 前者是搜索食品库，后者是分析模块 |
| "记运动" vs "查运动记录" | "记"=新增，"查"=查询 |
| "记体重" vs "查体重目标" | "记"=新增记录，"查"=查询进度 |
| "记睡眠" vs "记录起床" | 前者是手动记录，后者是起床唤醒自动流程 |
| "查食物排行" vs "查高热量榜" | 前者默认高热量，后者显式指定 |
| "设营养目标" vs "设体重目标" | 营养=每日摄入目标，体重=体重kg目标 |
| "设健身目标" vs "设营养目标" | 健身=运动类目标，营养=饮食类目标 |
| "记身材照" vs "查身材照" | "记"=新增，"查"=查询 |

---

## AI 触发场景详述

**所有 CLI 路径前缀**：`python scripts/`

### 🍚 饮食记录：记吃了

**完整流程（重要）**：

#### Step 1：解析用户输入
提取：食物名、克数（如有）

#### Step 2：模糊查询 nutrition_products 表
执行：`python scripts/calorie_tracker.py search-product <食物名>`

#### Step 3：根据查询结果分流

**Path A：找到匹配结果（≥1条）**
```
列表显示 → 用户选择 → 确认克数 → 计算热量/100 × 克数 → 执行 add → 返回今日汇总
```

**Path B：库中没找到，用户提供了营养成分表图片（拍营养表）**
```
调用 mmx vision describe 识别图片：
  mmx vision describe --image <图片路径> \
    --prompt "请识别这张营养成分表，提取：产品名称、品牌、热量(千卡)、蛋白质(克)、脂肪(克)、饱和脂肪(克)、碳水化合物(克)、糖(克)、膳食纤维(克)、钠(毫克)。请以JSON格式返回。"
→ 展示结果 → 用户确认 → add-product 存库 → 继续 Path A
```

**Path C：库中没找到，用户无法提供营养成分表**
```
讨论估算克数 → mmx search 查询参考数据：
  mmx search query --q "<食物名> 营养成分表 每100克热量"
→ 用户确认 → 执行 add（参考数据不存库）
```

#### Step 4：返回确认信息
```
✓ 已记录：<食物名> (<热量>卡, <克数>克)
餐次：<早/午/晚/下午茶/夜宵>
今日：<热量>/<目标>卡 | 蛋白<蛋白>/<目标>g | 碳<碳>/<目标>g | 脂<脂>/<目标>g
```

### 🏷️ 食品库：存食品 / 查热量 / 改食品 / 查食品库

- **存食品**：解析输入或图片 → 提取营养成分 → `calorie_tracker.py add-product <产品名> <品牌> <热量> <蛋白> <脂肪> <饱和脂肪> <碳水> <糖> <纤维> <钠> [备注]`
- **查热量**：`calorie_tracker.py search-product <关键词>`
- **改食品**：`calorie_tracker.py update-product <id> [--字段 值]`
- **查食品库**：`calorie_tracker.py list-products`

### ⚖️ 体重：记体重 / 查体重历史 / 查体重趋势 / 对比体重 / 查体重波动 / 设体重目标 / 查体重目标

- **记体重**：`calorie_tracker.py weight <体重> <身高>`（身高必传，BMI 必须计算）
- **查体重历史**：`calorie_tracker.py weight-history [天数]`
- **查体重趋势**：`weight_analysis(start, end, 'trend')`
- **对比体重**：`weight_analysis(start, end, 'compare', compare_start, compare_end)`
- **查体重波动**：`weight_analysis(start, end, 'volatility')`
- **设体重目标**：`set_weight_goal(weight_goal, deadline)`
- **查体重目标**：`weight_analysis(start, end, 'milestone')`

### 🏃 运动：记运动 / 改运动记录 / 查运动记录 / 查运动汇总 / 查运动类型 / 查运动趋势

- **记运动**：`exercise_tracker.py add --date <日期> --type <类型> --calories <卡> [--minutes <分钟>] [--reps <次数>]`
- **改运动记录**：`exercise_tracker.py update --id <ID> [--字段 值]`
- **查运动记录**：`exercise_tracker.py list [--days N] [--date <日期>] [--type <类型>]`
- **查运动汇总**：`exercise_tracker.py summary [--days N]`
- **查运动类型**：`exercise_tracker.py stats --type <breakdown|total>`
- **查运动趋势**：`exercise_tracker.py trend [--days N]`

### 💪 健身目标：设健身目标 / 查健身目标 / 改健身目标 / 删健身目标

- **设健身目标**：`fitness_goals.py add <名称> --type <daily|weekly|monthly|longterm> --exercise <运动> --unit <单位> --target <值> --start <日期>`
- **查健身目标**：`fitness_goals.py list [--type <类型>] [--status <状态>]`
- **改健身目标**：`fitness_goals.py update <ID> [--字段 值]`
- **删健身目标**：`fitness_goals.py delete <ID>`

### 😴 睡眠：记睡眠 / 改睡眠记录 / 查睡眠记录 / 记录起床

**记睡眠**：
解析输入 → `sleep_tracker.py add <就寝日期> --hours <时长> --bed <就寝时间> --wake <起床时间>`
睡眠归属于就寝那天。

**改睡眠记录**：`sleep_tracker.py update <日期> [--hours <时长>] [--note <备注>]`

**查睡眠记录**：`sleep_tracker.py list [--days N]`

**记录起床（起床唤醒处理流程）**：
1. 检测到唤醒词"记录起床" → 立即查询录音机数据库
2. 找到"最后一次人类消息"的时间（入睡信号）和当前唤醒消息的时间（起床信号）
3. 计算睡眠时长 = 起床时间 - 入睡前最后一条消息时间
4. 确认：「检测到你刚才睡了X小时，要不要记录？」（不提及"卡路里"三字）
5. 确认后执行：`sleep_tracker.py add <就寝日期> --hours <时长> --bed <就寝时间> --wake <起床时间>`
6. 睡眠归属于就寝那天

### 📊 分析：查热量趋势 / 查营养配比 / 查热量缺口 / 查食物排行 / 查运动分布 / 查运动贡献

- **查热量趋势**：`diet_analysis(start, end, 'calorie_trend')` — 工作日 vs 周末 / 合规率
- **查营养配比**：`diet_analysis(start, end, 'macro_ratio')` — 蛋白/碳水/脂肪占比
- **查热量缺口**：`diet_analysis(start, end, 'deficit_analysis')` — 饮食 vs 运动贡献
- **查食物排行**：`diet_food_ranking(start, end, category)` — category 可选：high_calorie / low_calorie / frequent / high_carb / high_protein
- **查运动分布**：`exercise_analysis(start, end, 'type_breakdown')` — 消耗/频次/时长占比
- **查运动贡献**：`exercise_analysis(start, end, 'deficit_contribution')` — 运动对缺口贡献

### 📋 综合：设营养目标 / 查营养目标 / 查健康报告 / 查卡路里数据

- **设营养目标**：`calorie_tracker.py goal <热量> [蛋白] [碳水] [脂肪]`
- **查营养目标**：读取 `daily_goal` 表返回当前目标
- **查健康报告**：`dashboard(start, end)` — 四维度综合仪表盘
- **查卡路里数据**：Lint 5 项检查（见下方）

---

## 示例对话

**用户**：记吃了 米饭 200克
**AI**：米饭大概 200克，232卡，4g蛋白，50g碳水，0.5g脂肪 → ✓ 已记录，今日 232/1800卡

**用户**：记体重 70公斤 178
**AI**：✓ 体重已记录 70.0公斤，BMI 22.1（正常范围）

**用户**：查热量 鸡胸肉
**AI**：找到 1 个匹配：鸡胸肉 | 165卡/100g | 蛋白31g | 脂肪3g

**用户**：记运动 骑行 40分钟 300卡
**AI**：✓ 已记录运动：骑行 40分钟 300卡

**用户**：查体重趋势
**AI**：📊 体重趋势（2026-04-28 ~ 2026-05-28）均重 70.2kg | 变化 -1.3kg | 趋势下降 ✓

---

## 联动说明

联动逻辑已集中到技能路由器（`图片路由/SKILL.md`），本技能不再单独维护联动规则。完成主操作后请检查路由器的联动规则表。

---

## Lint 检查（数据健康检查）

**触发词**：`"查卡路里数据"`

### 检查项

1. **数据新鲜度**：今日是否记录体重/饮食/运动
2. **体重目标进度**：调用 `weight_milestone()` 检查差距和预计达成时间
3. **热量趋势预警**：调用 `diet_calorie_trend()` 检查近7天，连续3天超标则预警
4. **热量缺口分析**：调用 `diet_deficit_analysis()` 检查缺口，长期为正需提示
5. **运动连续性**：调用 `exercise_trend()` 检查，连续7天以上未运动则预警

原则：发现问题列出清单，只建议不自动修改。

---

## TypeScript 配置生成

触发场景：表结构变了、表数量变了、数据库路径变了、SkillBoard 报错缺字段。

运行 `python scripts/generate_ts_config.py` 重新生成 `config-calorie.ts`，检查输出确认7张表都在。
