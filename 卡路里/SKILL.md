---
name: 卡路里
description: >
  饮食热量、饮水、体重、运动、营养追踪与分析技能。
  触发词：记吃了、拍营养表、删吃的、查今天吃、查吃的记录、查热量历史、记喝水、查今天喝水、查热量、存食品、改食品、查食品库、记体重、改体重记录、查体重历史、查体重趋势、对比体重、查体重波动、设体重目标、查体重目标、记运动、改运动记录、查运动记录、查运动汇总、查运动类型、查运动趋势、查健身计划、制定健身计划、改健身计划、落地健身计划、同步健身计划、训记-覆盖X日的训练计划、回写训记、复盘训练、查热量趋势、查营养配比、查热量缺口、查食物排行、查高热量榜、查低热量榜、查频繁吃榜、查高碳水榜、查高蛋白榜、查运动分布、查运动贡献、设营养目标、查营养目标、查健康报告、查卡路里数据、记身材照、查身材照、删身材照、改照片标签
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

### 📚 nutrition_products 数据治理原则（2026-06-30 共识）

`source` 字段记录**"这条数据是怎么来的"**，不是"理想来源"：
- ❌ **不维护"推荐来源枚举"**——AI 想用什么字符串都行
- ✅ **AI 不知道就写 "未知" / "AI估算,未查证"**,不要编造权威来源
- ✅ **完全自由文本**,只要非空
- 数据示例：`"中国食物成分表第6版"` / `"USDA FoodData Central"` / `"包装标签实测 2025-06"` / `"AI估算,未查证"` / `"未知"`

`is_deprecated` 字段标记废弃条目：
- `0` = 有效,默认查询可见
- `1` = 废弃,默认查询不返回
- 替代旧的 note 字符串标记(如 `[已废弃]`)
- `dedupe` 命令会检查有效条目中的重复

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
| 改吃的 | 修改已记录饮食（克数/食物名/备注） | `calorie_tracker.py update-meal` |
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
| 批量导入 | 批量录入/更新食品库（JSONL）| `batch_import.py import <file>` |
| 校验批量 | 只校验 JSONL 不写入 | `batch_import.py validate <file>` |
| 查食品库去重 | 全库去重检查（只报告）| `batch_import.py dedupe` |

### ⚖️ 体重

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记体重 | 记录体重（自动算 BMI） | `calorie_tracker.py weight` |
| 改体重记录 | 修改历史体重记录 | `calorie_tracker.py weight-update` |
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

### 🏋️ 健身计划

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 查健身计划 | 查看训练计划 HTML 页面（DB 数据驱动，含今日复盘 section） | `render_workout_plan.py` |
| 制定健身计划 | AI 采访式对话 → 校验 → 写入 workout_plans | AI 路由（多轮对话） |
| 落地健身计划 | 将某天计划执行：补计划→查/记心愿→训记（仅今天） | `workout_plan.get_day_plan()` + 跨技能 AI 路由 |
| 同步健身计划 | 批量落地 3 天 + 调「回写训记」(Step 2 引用) | `workout_plan.get_day_plan()` + 跨技能 AI 路由 + 调「回写训记」 |
| 回写训记 | 拉训记数据回写 exercise_log(幂等),独立 Step 2 | `python scripts/xunji_bridge.py backfill [--date X] [--days N]` |
| 训记-覆盖X日的训练计划 | 用卡路里 plan 覆盖训记某天训练(localid 已有,start/end=0) | `xunji_bridge.py overlay-plan --date X` |
| 改健身计划 | AI 对话定位意图 → 改/增/删时段、调整周次、修改配置 | `plan_generator.py` 全部 CRUD |
| 复盘训练 | 对指定时间段的训练做 plan vs 实绩对比（完成率/漏做/超额/异常） | `python scripts/exercise_review.py --start X --end Y` |

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
- **数据分析**：3大类11种分析维度 + dashboard综合报告
- **身材照片**：记录身材照片，支持自定义标签（正面/背面/侧面/手臂等），可生成 GIF 变化动画

## 数据库结构

详见 [`references/database_schema.md`](references/database_schema.md)

共 8 张表：`food_log`（饮食记录）、`daily_goal`、`weight_log`、`exercise_log`、`nutrition_products`、`workout_plan_config`（健身计划元信息）、`workout_plans`（健身日程）、`body_photos`

> **2026-07-12 重构**：`entries` → `food_log`；`fitness_goals` 和 `sleep_records` 已删除，重构为 `workout_plan_config` + `workout_plans`。所有 8 张表均由 `db.py init_db()` 统一创建。

## 📂 脚本模块结构（v2.3 拆分后）

业务逻辑按"领域对象"拆分到独立文件，每个文件 ≤ 350 行，单屏可读。

### 核心模块（calorie_tracker.py 拆分）

| 文件 | 行数 | 职责 | 公共 API |
|---|---|---|---|
| `db.py` | ~145 | 数据库基础：路径解析、连接、初始化、迁移 | `find_db_path` / `connection` / `get_db` / `init_db` |
| `db_utils.py` | ~15 | 兼容层：re-export db.py（旧脚本继续可用） | — |
| `diet.py` | ~215 | 饮食记录 | `add_meal` / `delete_meal` / `list_meals` / `get_daily_summary` / `infer_meal_type` |
| `water.py` | ~65 | 饮水记录（复用 food_log 表，food_name='💧水'） | `add_water` |
| `nutrition_goal.py` | ~95 | 每日营养目标 | `set_nutrition_goal` / `get_nutrition_goal` |
| `weight.py` | ~190 | 体重记录 | `log_weight` / `update_weight` / `get_weight_history` |
| `weight_goal.py` | ~110 | 体重目标 + 进度 | `set_weight_goal` / `get_weight_goal` / `print_goal_progress` |
| `exercise.py` | ~110 | 运动记录 | `add_exercise` / `get_exercise_log` / `print_exercise_summary` |
| `product_library.py` | ~160 | 食品库 CRUD | `add_product` / `search_products` / `update_product` / `list_products` |
| `calorie_history.py` | ~55 | 热量历史 | `get_calorie_history` |
| `calorie_tracker.py` | ~250 | **CLI 入口**：main + argparse + usage | — |

### 分析包（analysis/）

11 个分析函数按维度拆分到子模块，4 个统一入口在 `__init__.py`。

| 文件 | 行数 | 职责 |
|---|---|---|
| `analysis/__init__.py` | ~125 | 4 统一入口 + 11 原子函数 re-export |
| `analysis/_utils.py` | ~55 | 共享工具：`_get_db` / `_parse_date` / `_days_between` / `BMR_ACTIVITY_FACTOR` |
| `analysis/weight.py` | ~210 | 4 个体重分析：`weight_trend` / `weight_compare` / `weight_milestone` / `weight_volatility` |
| `analysis/diet.py` | ~225 | 4 个饮食分析：`diet_calorie_trend` / `diet_macro_ratio` / `diet_food_ranking` / `diet_deficit_analysis` |
| `analysis/exercise.py` | ~135 | 3 个运动分析：`exercise_trend` / `exercise_type_breakdown` / `exercise_deficit_contribution` |
| `analysis/dashboard.py` | ~45 | 综合报告 `dashboard(start, end)` |

### 独立 CLI 脚本（已有，未拆分）

| 文件 | 行数 | 职责 |
|---|---|---|---|
| `exercise_tracker.py` | 442 | 运动更完整的 CLI（add/update/list/summary/stats/trend）|
| `body_photo_tracker.py` | 356 | 身材照片 CLI（add/list/delete/tag/gif）|
| `plan_generator.py` | 新建 | 健身计划生成（校验+写入）|
| `workout_plan.py` | 新建 | 计划循环逻辑 + 按日查询 |
| `render_workout_plan.py` | 新建 | HTML 渲染（DB→Apple 风格页面）|
| `adapters/xunji_adapter.py` | 新建 | 训记 API ↔ exercise_log 纯函数适配器（被 xunji_bridge 调用）|
| `xunji_bridge/` | 新建 | 训记训练拓展功能 CLI 入口包(verify/fetch/upsert/push-plan/overlay-plan/backfill/key/run-sync 8 子命令) |
| `generate_ts_config.py` | 269 | 从数据库生成 `config-calorie.ts` |

### 模块依赖图

```
calorie_tracker.py（CLI 入口）
   ├─ diet.py
   │    └─ nutrition_goal.py
   ├─ water.py
   │    └─ nutrition_goal.py
   ├─ nutrition_goal.py
   ├─ weight.py
   ├─ weight_goal.py
   ├─ exercise.py
   ├─ product_library.py
   └─ calorie_history.py
        └─ nutrition_goal.py

analysis/__init__.py
   ├─ analysis/weight.py
   │    └─ weight_goal.py（get_weight_goal）
   ├─ analysis/diet.py
   │    └─ nutrition_goal.py（get_nutrition_goal）
   ├─ analysis/exercise.py
   └─ analysis/dashboard.py
        └─ weight.py / diet.py / exercise.py

所有模块 → db.py（数据库基础）
```

### 拆分原则

1. **业务领域优先**：文件名 = 管什么（diet/weight/exercise），不叫 `entries.py`/`ops/` 等抽象名
2. **避免歧义命名**：`weight_goal` 比 `goal.py` 清晰（还有 `nutrition_goal.py`）
3. **CLI 入口稳定**：calorie_tracker.py / exercise_tracker.py 等保留同名入口，内部委托给各模块
4. **兼容层保留**：`db_utils.py` 转发到 `db.py`，旧脚本 import 路径不变

## 命令行用法

### 食物记录
```bash
python scripts/calorie_tracker.py add "鸡胸肉" 165 31 0 3 150   # 食物名 热量 蛋白 碳水 脂肪 克数
python scripts/calorie_tracker.py update-meal 5 --grams 180      # 修改记录5的克数为180g
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
python scripts/calorie_tracker.py weight 70 178                  # 记录体重(kg) 身高(cm)（身高必传）
python scripts/calorie_tracker.py weight-update 5 --weight 69.5   # 修改体重记录（按ID）
python scripts/calorie_tracker.py weight-history 30              # 最近30天体重
python scripts/calorie_tracker.py weight-goal 73 2026-12-31      # 设置体重目标 + 截止日期
python scripts/calorie_tracker.py weight-goal-progress           # 查看体重目标进度
```

### 运动
```bash
python scripts/calorie_tracker.py exercise-add 骑行 300 --minutes 40   # 快速记录运动
python scripts/calorie_tracker.py exercise-summary 7                   # 近7天运动汇总
python scripts/exercise_tracker.py add --date 2026-05-23 --type 骑行 --calories 300 --minutes 40
python scripts/exercise_tracker.py list --days 7
python scripts/exercise_tracker.py summary --days 7
python scripts/exercise_tracker.py trend --days 7
```

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
| 健身计划/训练计划/制定计划/改计划/落地计划 | 🏋️ 健身计划 |
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
| "记吃的" vs "改吃的" | "记"=新增，"改"=修改已有记录 |
| "记体重" vs "查体重目标" | "记"=新增记录，"查"=查询进度 |
| "制定健身计划" vs "落地健身计划" | 前者是对话制定，后者是执行到当天 |
| "查食物排行" vs "查高热量榜" | 前者默认高热量，后者显式指定 |
| "设营养目标" vs "设体重目标" | 营养=calorie/protein/carbs/fat/water_goal 5 字段;体重=weight_goal+deadline 2 字段 |
| "查食物排行" vs "查高热量榜" | 前者默认高热量，后者显式指定 |
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

### 📦 批量导入食品库（2026-06-30 新增）

适用场景:批量录入 / 批量更新 **10+ 条** 食品数据。

工具:`scripts/batch_import.py`

**子命令**:

| 子命令 | 用途 |
|--------|------|
| `validate <file.jsonl>` | 只校验 JSONL,不读写数据库 |
| `import <file.jsonl> [--dry-run]` | 批量导入(重复时逐条询问) |
| `dedupe` | 全库去重检查(只报告,不修改) |
| `export --source X --output F` | 按条件导出 JSONL |

**JSONL 字段规范**:

- **必填(7)**:`product_name`, `calories`, `protein`, `fat`, `carbohydrates`, `sodium`, `source`
- **可选(6)**:`brand`, `saturated_fat`, `sugar`, `dietary_fiber`, `note`, `is_deprecated`

**去重判定**:`product_name + brand` 完全相同视为同一条

**重复处理**(逐条交互):

| 快捷键 | 动作 |
|--------|------|
| `o` | 覆盖(更新数据) |
| `s` | 跳过 |
| `d` | 标废弃(is_deprecated=1) |
| `a` | 全部应用此选择(再问一次具体动作) |

**完整示例**:`python scripts/batch_import.py --help`

### ⚖️ 体重：记体重 / 查体重历史 / 查体重趋势 / 对比体重 / 查体重波动 / 设体重目标 / 查体重目标

- **记体重**：`calorie_tracker.py weight <体重> <身高>`（身高必传，BMI 必须计算）
- **改体重记录**：`calorie_tracker.py weight-update <ID> [--weight <公斤>] [--height <身高cm>] [--note <备注>]`
- **查体重历史**：`calorie_tracker.py weight-history [天数]`
- **查体重趋势**：`weight_analysis(start, end, 'trend')`
- **对比体重**：`weight_analysis(start, end, 'compare', compare_start, compare_end)`
- **查体重波动**：`weight_analysis(start, end, 'volatility')`
- **设体重目标**：`set_weight_goal(weight_goal, deadline)`
- **查体重目标**：`weight_analysis(start, end, 'milestone')`

### 🏃 运动：记运动 / 改运动记录 / 查运动记录 / 查运动汇总 / 查运动类型 / 查运动趋势

- **记运动**：`exercise_tracker.py add --date <日期> --type <类型> --calories <卡> [--minutes <分钟>] [--reps <次数>] [--category <类>] [--intensity <级>] [--distance <km>] [--heart-rate <bpm>] [--set <N>] [--load <kg>]`
- **改运动记录**：`exercise_tracker.py update --id <ID> [--字段 值]`
- **查运动记录**：`exercise_tracker.py list [--days N] [--date <日期>] [--type <类型>] [--category <类>]`
- **查运动汇总**：`exercise_tracker.py summary [--days N]`
- **查运动类型**：`exercise_tracker.py stats --type <breakdown|total>`
- **查运动趋势**：`exercise_tracker.py trend [--days N]`

#### 🎯 运动 AI 路由规则（必读 · 2026-06-29 扩展）

##### A · 卡路里综合考虑规则

用户可能给卡路里值、可能不给。AI 必须按以下流程处理：

```
Step 1  识别用户报的卡路里值（若有）
Step 2  AI 用 METs 公式独立推算（不依赖心率）
        - 有氧/柔韧/日常：cal = MET × 体重 × 时长(h)
        - 力量训练    ：cal = MET × 体重 × 组数 × 0.05h
        - 体重从 weight_log 最新一条取，不向用户追问
Step 3  对比两个值，按偏差处理：
        - 偏差 < 20%       → 取 AI 推算值入档
        - 偏差 20-50%      → 取两者中位 + note 标记
        - 偏差 > 50%       → 反问用户确认哪个对（不入档）
```

实现：`exercise.combined_calories(user_reported, estimated)` 返回 `(final, note_suffix, deviation)`。

##### B · 强度字段优先级

```
1. 用户口语明确说（如"很累"、"轻松"、"累死"） → AI 翻译成 4 档（最高优先）
2. AI 基于 METs 兜底（无口率）                 → 按 MET 范围估
3. 都没有                                       → NULL（不强制）
```

口语映射表（节选）：
| 用户说 | 4 档 |
|---|---|
| "挺轻松"、"没什么感觉"、"散步" | 低 |
| "一般"、"还行"、"中等" | 中 |
| "挺累"、"暴汗"、"喘" | 高 |
| "累死"、"力竭"、"撑不住" | 极限 |

METs 兜底映射：
| MET 范围 | 4 档 |
|---|---|
| < 3 | 低 |
| 3-6 | 中 |
| 6-9 | 高 |
| > 9 | 极限 |

实现：`exercise.parse_user_intensity(text)` + `exercise.estimate_intensity_met(met)`。

##### C · 心率询问规则（场景化）

| 场景 | AI 是否问心率 |
|---|---|
| 有氧（跑步/骑行/跳绳/八段锦） | ✅ 主动问 1 次 |
| 力量训练（哑铃/深蹲/俯卧撑） | ❌ 不问 |
| 日常活动（家务/做饭） | ❌ 不问 |

问法示例：`"顺便问下，平均心率有记到吗？没记就跳过"`
用户答"没记"或忽略 → 心率字段 NULL，不卡流程。

##### D · 运动分类路由

`category` 字段 4 个值，AI 根据动作名自动推断：

| 关键词 | category |
|---|---|
| 哑铃/杠铃/史密斯/弯举/推举/深蹲/卧推/划船/俯卧撑/引体/平板支撑 | 力量 |
| 八段锦/太极/瑜伽/拉伸 | 柔韧 |
| 家务/做饭/洗衣/打扫/通勤/走路/散步 | 日常 |
| 跑步/骑行/跳绳/椭圆机/游泳/其他 | 有氧（兜底） |

实现：`exercise._infer_category(exercise_type)`。

##### E · 力量训练流式录入

每组 = 1 行 exercise_log：

```bash
# 第 1 组
exercise_tracker.py add --date 2026-06-29 --type 哑铃弯举 \
  --set 1 --reps 10 --load 10 --category 力量 --calories 22

# 第 2 组
exercise_tracker.py add --date 2026-06-29 --type 哑铃弯举 \
  --set 2 --reps 10 --load 10 --category 力量 --calories 22
```

用户做完一组就告诉 AI 一组数据，AI 逐条 add。**绝对不要**等做完 N 组再汇总成一条记录。

### 🏋️ 健身计划：查 / 制定 / 改 / 落地 / 同步

- **查健身计划**：`python scripts/render_workout_plan.py` 输出 Apple 风格 HTML
- **制定健身计划**：AI 4 轮对话制→ 产出 JSON → `plan_generator.write_plan()` 写入
  ```
  贯穿规则：
    A. 安全止损 — 制止明显不安全的要求（如"每天 50 组胸"）
    B. 解释决策 — 每次建议必须说"因为..."
    C. 现状感知 — 利用基线信息在后续决策中引用
    D. start_date 必须是周一(2026-07-13 加) — 健身计划以自然周对齐;若用户给的不是周一,先 round 到最近周一再写入;不 round 会导致用户口语"第 N 周"跟算法返的 plan_week 错位(因为 n 周循环按距离 start 的整 7 天算)

  第1轮·基线建立：
    当前训练状态 + 目标 + 水平 + 伤病/保护部位 + 器材清单 + 讨厌的动作
    → 建立完整用户画像

  第2轮·结构性决策：
    每周几天 / 每天几时段 / 每时段多久
    部位优先级 + 周总组数（AI 建议 + 解释为什么）
    分化策略（推拉腿/部位分化/全身）
    AI 实时校验：时段数×时长÷3min ≥ 总组数
    → 确定时间框架和部位分配

  第3轮·精细化：
    周期化：几周循环 + 周权重方案
    递进协议：每周期内如何推进（RPE递增/rep递增/重量递增）
    热身 + 有氧如何嵌入
    评估指标：4周后怎么判断效果
    → 确定训练变量

  第4轮·动作落地：
    AI 推荐候选动作 → 用户确认 + 主备关系
    AI 校验：角度多样性/器材匹配/训记库中验证
    确认 → 生成 JSON → validate_plan() → write_plan()
  ```
- **改健身计划**：AI 对话定位意图 → 一个唤醒词覆盖所有写操作（改时段/加时段/删时段/调整周/改配置）
- **复盘训练**：`python scripts/exercise_review.py [--start YYYY-MM-DD --end YYYY-MM-DD | --today | --yesterday | --days N]` → 对 [start, end] 范围内每一天做 plan vs 实绩对比（完成率 / 漏做 / 超额 / 异常）。AI 路由负责解析"今日/昨天/前天/这周/X-Y"等口语化时间 → `--start` / `--end`。
  ```
  参数：
    --start      YYYY-MM-DD  开始日期
    --end        YYYY-MM-DD  结束日期
    --today                  今日（start=end=today）
    --yesterday              昨日（start=end=yesterday）
    --day-before-yesterday   前日（start=end=today-2）
    --days N                 最近 N 天（start=today-N+1, end=today）
  数据来源：
    - workout_plans（每日 sessions + total_sets）
    - exercise_log（每日实绩，set_index 计数）
  报告内容（每天）：
    - 计划组数 vs 实做组数
    - 完成率
    - 异常项：完成率 < 50% / 超额 > 130% / 计划未做 / 计划休息但实做
  使用场景：晚上 10 点同步健身计划 → 触发"复盘训练" → 看 plan vs 实绩差距 → 决定要不要改健身计划。
  ```
- **落地健身计划**：将指定日期的训练计划落地到作息/备忘/训记三个系统。执行必须全部完成三步，逐 session 独立执行，某条失败跳过继续。
  ```
  Step 1 · 数据准备
    调 workout_plan.get_day_plan(日期)。
    如果用户没说日期，默认今天。
    休息日 → 告知用户并退出。
    **未开始(2026-07-13 增)**:返回的 dict 含 `unstarted=True` 时,表示该日期早于 plan start_date,跳过后续 Step 2/3/4,告知用户"计划 X 月 X 日开始"并退出。

  Step 2 · 联动作息管家
    对每个 session 调「补计划 {日期} 健身 {session_label} {time_start}-{time_end}」
    附带 notes（前 3 动作名 + 总数），category="运动"。
    ensure-plan-event 已内置飞书日历同步（本地 DB 和飞书日历缺哪边建哪边）。
    接口幂等，重复调用自动跳过。

  Step 3 · 联动备忘录
    对每个 session，先构造心愿内容：
      心愿内容 = 「健身 {session_label} {time_start}-{time_end}」
    此字符串在"查"和"记"时必须完全一致，AI 不得自由改写措辞。

    **查重(2026-07-13 改为 content + due 双键精确查重)**：
      调备忘录「查心愿 {心愿内容} --category 心愿 --due {该日期}」
      → 有匹配 → 跳过(已存在,不动)
      → 无匹配 → 调「记心愿 {心愿内容} --category 心愿 --due {该日期}」创建
    不建过去日期的心愿。

  Step 4 · 联动训记
    检查训记 KEY 环境变量，权威名 `XUNJI_TRAINS_KEY`（兼容旧名 `XUNJI_API_KEY`）：
      未配置 → 调 `python scripts/xunji_bridge.py key status` 让用户看状态，
              再用 `python scripts/xunji_bridge.py key set <KEY>` 设置。
              KEY 申请：训记 App → 我的 → 设置 → 第三方接入。
      已配置(PRIMARY) → 提示「✅ 训记 KEY 已配（XUNJI_TRAINS_KEY），开始同步」
      已配置(LEGACY fallback) → 提示「⚠ 用了旧名 XUNJI_API_KEY，建议用 key set 迁移到 XUNJI_TRAINS_KEY」

    KEY 就绪后，**不再**手写 HTTP，改为调训记训练拓展 CLI：
      python scripts/xunji_bridge.py push-plan --date {YYYY-MM-DD}
    该命令内部完成：
      ① 读 workout_plans 中当天的所有 session
      ② 按以下规则转成训记 res[] 格式：
         - schema_version = "train_open_api_v2"
         - client_request_id = "{日期}_{session_label}_{uuid8}"（幂等键；uuid8 后缀满足训记 unique-id-from-agent 硬约束,避免同 label 重推被训记去重）
         - datestr / title / start=0 / end=0
         - movements 只保留 name + sets；每条 set 加 "done": false
      ③ 调 POST /api_upsert_trains_for_llm_v2
      ④ 多个 session 间自动等 45s（训记写 API 限频）
      ⑤ 输出每 session ok/fail 状态，JSON 格式

    ⏱ 训记推送约 3 分钟/天。

    训记写入失败的 session 重新调落地可重试（client_request_id 保证幂等）。

  末尾输出汇总：
    ✅ 补计划 4/4 已创建
    ✅ 心愿 3/4 已建（1 条已存在跳过）
    ⚠️ 训记推送 3/4（S3 超时，重新调落地可重试）
  ```

- **同步健身计划**：批量落地 3 天 + 训记回写 exercise_log。
  ```
  前置:KEY 检查同「落地健身计划」Step 4
    检查 XUNJI_TRAINS_KEY(优先,兼容 XUNJI_API_KEY)。
    未配置 → 调 `python scripts/xunji_bridge.py key status` 让用户看状态,
            再用 `python scripts/xunji_bridge.py key set <KEY>` 设置。
            KEY 申请:训记 App → 我的 → 设置 → 第三方接入。

  Step 1 · 批量落地(按天循环,顺序执行)
    固定 3 天,从今天起。按天依次执行。
    每天开始前汇报:「第 1/3 天(7月13日 周一)开始落地…」
    对当天调「落地健身计划」**完整流程**(每次必须执行全部三步:补计划+记心愿+训记推送)。
    每天完成后汇报:
      「第 1/3 天 ✅ 补计划 4 条 / 心愿 4 条 / 训记 3 条(S3 超时跳过)」

  Step 2 · 训记回写(2026-07-13 改:独立为「回写训记」trigger,此处引用)
    3 天都跑完后,调「回写训记」3 天(--days 3)。
    触发词路由:`python scripts/xunji_bridge.py backfill --days 3`
    实现细节见「回写训记」章节(幂等键 / 错误处理 / 体重推算都在那里)。
    完成后汇报:「训记回写 ✅ 新增 X 条,更新 Y 条」

  末尾输出模板:
    第 1/3 天 ✅ 补计划 4 条 / 心愿 4 条 / 训记 3 条(S3 超时跳过)
    第 2/3 天 ✅ 补计划 4 条 / 心愿 4 条 / 训记 4 条
    第 3/3 天 ✅ 补计划 4 条 / 心愿 4 条 / 训记 4 条
    训记回写 ✅ 新增 12 条,更新 0 条
  ```

- **回写训记**：`python scripts/xunji_bridge.py backfill [--date YYYY-MM-DD] [--days N]` → 拉训记数据回写 exercise_log(幂等)。
  ```
  行为:
    调训记 fetch(include_full_data=true)
    → xunji_adapter.py 解析 → upsert_exercise_log
    → 幂等键:xunji_localid + set_index(同组不会重复写)
    → 自动取最新体重推算热量

  参数:
    --date YYYY-MM-DD  单日(默认今天)
    --days N           范围 [date-N+1, date](默认 1)

  前置:KEY 检查同「落地健身计划」Step 4(XUNJI_TRAINS_KEY)

  使用场景:
    - 「同步健身计划」Step 2 自动调(--days 3)
    - 晚上 6 点已同步过、8 点又有新训练 → 「回写训记」单独跑
    - 周末补练漏写 → 「回写训记 --date X --days N」

  末尾输出(JSON):
    {
      "end_date": "2026-07-13",
      "days": 1,
      "results": [
        {
          "date": "2026-07-13",
          "fetch_ok": true,
          "trains_count": 3,
          "inserted": 2,
          "updated": 1,
          "skipped_empty": false,
          "body_weight_kg": 70.0,
          "errors": [],
          "err": null
        }
      ],
      "total_inserted": 2,
      "total_updated": 1
    }
  ```

- **训记-覆盖X日的训练计划**：用卡路里 plan 覆盖训记某天**已有**训练(localid 已有 + start/end=0,**等同新建语义**)。
  ```
  适用场景:
    - 训记那天的训练已经在(可能手建,可能 push-plan 建过),想用卡路里 plan 同步内容
    - 注意:跟「落地健身计划」的区别 —— 落地走 push-plan(新建 localid=0),
            本触发词走 overlay-plan(更新 localid 已有)
  跟「落地健身计划」Step 1/2/3 的区别:
    - 训记-覆盖只动训记,不动作息/备忘
    - 不调「补计划」、不调「记心愿」

  Step 1 · 解析日期
    用户说"覆盖7.13"/"训记-覆盖2026-07-13的训练计划"等
    → 解析成 YYYY-MM-DD
    → 昨天/前天拒绝(训记"覆盖历史"无意义,改 plan 才有意义)

  Step 2 · 调底层 CLI
    不手写 HTTP,直接调:
      python scripts/xunji_bridge.py overlay-plan --date {YYYY-MM-DD}
    可选参数:
      --dry-run       预览将要推什么(不实推)
      --missing fail  卡路里有但训记没的 title → 报错退出(默认)
      --missing skip  卡路里有但训记没的 title → 跳过,只推匹配的

  Step 3 · 内部做了什么
    ① fetch 训记 list(只拿 title → localid 映射,**不取 start/end**)
    ② 拉卡路里 plan(get_day_plan)
    ③ 按 title 对账
    ④ 缺 title → 按 --missing 策略处理
    ⑤ 训记有但卡路里没 → 报告保留(不删)
    ⑥ 构造 res[]:localid 已有,start=0, end=0
    ⑦ 调底层 upsert.upsert_trains(单次,训记 API 单次最多 4 条训练)
    ⑧ 输出对账结果 + 训记响应

  Step 4 · 训记响应处理
    success → 告知用户「✅ 覆盖 X 条训练(start/end 都改 0)」
    fail_count > 0 → 报告训记错误(error_type 路由见下方"训记 API 错误处理路由表")
    missing=fail 命中 → 报告哪些 title 训记找不到,让用户决定:
        - 是训记那边没建 → 改用 push-plan(新建)
        - 是 plan 改了 title → 同步改回去或忽略

  末尾输出模板:
    ✅ 训记覆盖 4/4 完成(上午·臂 / 下午·胸 / 晚上·肩+腿 / 居家·腹,start/end=0)
    或:
    ❌ 卡路里有但训记没:[title 列表](请先在训记 App 建对应训练,或用 push-plan 新建)
  ```

### 🚨 训记 API 错误处理路由表

所有训记 CLI 返回的错误都带 `error_type` 字段(来自 `xunji_bridge/errors.py`)。
AI 看到错误时按此表处理:

| error_type | 含义 | AI 应对 |
|---|---|---|
| `auth` | apikey 缺失/无效(401/403) | 提示用户去训记 App 重新生成 KEY(我的 → 设置 → 第三方接入 → 重置) |
| `rate_limit` | too frequent(429) | CLI 已自动 sleep retry_after + 重试 2 次。如果还是 fail,告诉用户"训记限频,等会儿重试" |
| `vip_required` | 仅 VIP 可用 | 告诉用户"训记 API 需要会员,普通账号无法用" |
| `validation` | 请求字段错(400) | CLI 已附 raw_body,告诉用户具体哪个字段错(基于 raw_body.message) |
| `server` | 5xx 服务端错 | CLI 已重试 2 次。如果还 fail,告诉用户"训记服务端临时挂,稍后重试" |
| `network` | 超时/连接错 | CLI 已重试 2 次。如果还 fail,告诉用户"网络问题,检查本地网络" |
| `unknown` | 其他 | 把 raw_body 完整给用户,让用户判断 |

**重试策略**(用户 2026-07-13 确认):**全部错误重试 2 次**(防网络抖动),但 `auth` / `vip_required` / `validation` 重试无意义,直接报。

**错误字段**(完整,err_full):
- `error_type`:7 种之一
- `message`:人类可读
- `retry_after`:服务端要求等待秒数(只 rate_limit 有)
- `raw_body`:API 原始响应(调试)
- `code`:HTTP code(如果有)

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
