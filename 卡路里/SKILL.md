---
name: 卡路里
description: >
  饮食热量、饮水、体重、运动、营养追踪与分析技能。
  触发词:记吃了、拍营养表、删吃的、查今天吃、查吃的记录、查热量历史、记喝水、查今天喝水、查热量、存食品、改食品、查食品库、记体重、改体重记录、查体重历史、查体重趋势、对比体重、查体重波动、设体重目标、查体重目标、记运动、改运动记录、查运动记录、查运动汇总、查运动类型、查运动趋势、查健身计划、制定健身计划、改健身计划、落地健身计划、卡路里同步、训记-覆盖X日的训练计划、回写训记、复盘训练、查热量趋势、查营养配比、查热量缺口、查食物排行、查高热量榜、查低热量榜、查频繁吃榜、查高碳水榜、查高蛋白榜、查运动分布、查运动贡献、设营养目标、查营养目标、查健康报告、查卡路里数据、记身材照、查身材照、删身材照、改照片标签、复盘、复盘今日、复盘本周、复盘本月、复盘本年、复盘日期范围、开启定时复盘、关闭定时复盘、查定时复盘、设置档案、查档案
metadata: { "openclaw": { "emoji": "🍎", "requires": { "python": ">=3.7" } } }
---

**🔗 联动提示:** 完成本技能主操作后,检查技能路由器(`图片路由/SKILL.md`)的联动规则,判断是否需要联动其他技能(如用户提到食物花费→询问是否记录支出;用户提到买了新食品→询问是否存入食品库)。详见路由器的联动规则表。

## ⚠️ 强制性规定(最高优先级)

1. **HTML 同步**:本技能的所有优化和变动、脚本的所有变动都必须体现在相应的 HTML 页面上。HTML 是技能功能的可视化镜像,任何功能变更若未同步到 HTML 视为未完成。
2. **优先级**:本强制性规定优先级最高,高于下方所有操作规范和功能说明。
3. **变更确认**:对该技能的所有文件、脚本的任何一行修改都需要明确得到用户的 1 次确认,未经确认不得执行写入操作。

---

## ⚠️ 操作规范(强制)

本技能所有数据操作必须通过 CLI,禁止直连数据库。

## 核心原则

- **数据操作只走 CLI**:所有增删改查通过 `scripts/` 下的 Python 脚本执行,禁止直接操作 SQLite
- **睡眠归属就寝日**:睡眠记录归属于就寝那天,不是起床日
- **Path C 参考数据不存库**:外部搜索到的营养数据仅用于本次记录,不写入 nutrition_products
- **起床确认不提卡路里**:唤醒词场景的确认语中不出现"卡路里"三字,直接问"要不要记录"
- **只建议不自动修改**:Lint 检查发现问题后列出清单,让用户决定

### 📚 nutrition_products 数据治理原则(2026-06-30 共识)

`source` 字段记录**"这条数据是怎么来的"**,不是"理想来源":
- ❌ **不维护"推荐来源枚举"**--AI 想用什么字符串都行
- ✅ **AI 不知道就写 "未知" / "AI估算,未查证"**,不要编造权威来源
- ✅ **完全自由文本**,只要非空
- 数据示例:`"中国食物成分表第6版"` / `"USDA FoodData Central"` / `"包装标签实测 2025-06"` / `"AI估算,未查证"` / `"未知"`

`is_deprecated` 字段标记废弃条目:
- `0` = 有效,默认查询可见
- `1` = 废弃,默认查询不返回
- 替代旧的 note 字符串标记(如 `[已废弃]`)
- `dedupe` 命令会检查有效条目中的重复

---

## 📦 安装与配置

### 依赖

- Python >= 3.7
- 无第三方依赖(仅用标准库 sqlite3、argparse、datetime)

### 配置项

| 环境变量 | 说明 |
|---------|------|
| `SKILLS_DB_PATH` | 数据库文件所在目录 |

DB 查找顺序:`SKILLS_DB_PATH` 环境变量 → 技能目录 → 父目录 `.db/` 文件夹 → 自动创建 `.db/` 目录。

### 一键安装 prompt

将以下内容发送给 AI 即可安装本技能:

```
请帮我安装卡路里技能:
1. 检查 Python 环境
2. 引导我配置环境变量
3. 显示当前环境变量配置
4. 告诉我如何更改数据目录
```

---

## 🤝 触发词速查表

> 用户说"卡路里 help"时显示本表。全部唤醒词为动词+名词结构。

**CLI 列规则(最严格标准 · 2026-07-13 修)**:
- **原子 trigger**(暴露 CLI): `python scripts/<file>.py <subcommand> [args]`
- **组合 trigger**(跨 skill): `组合:<trigger1> + <trigger2> + ...`(不写 Python 函数)
- **分析类 trigger**(Python API): `AI 路由(Python API)`
- **纯 AI 路由**(无 CLI): `AI 路由(无 CLI)`

**参数占位符**:统一用 `<X>` 尖括号(如 `<DATE>`、`<N>`),不写裸 `X` 或大括号 `{X}`

### 🍚 饮食记录

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记吃了 | 记录饮食(库匹配/图片识别/外部搜索统一入口) | `python scripts/calorie_tracker.py add` |
| 拍营养表 | 图片识别营养成分表并记录 | `mmx vision describe` → `python scripts/calorie_tracker.py add` |
| 删吃的 | 删除饮食记录 | `python scripts/calorie_tracker.py delete` |
| 改吃的 | 修改已记录饮食 | `python scripts/calorie_tracker.py update-meal` |
| 查今天吃 | 今日饮食摘要 | `python scripts/calorie_tracker.py summary` |
| 查吃的记录 | 今日逐条饮食记录 | `python scripts/calorie_tracker.py list` |
| 查热量历史 | 最近 N 天热量摄入历史 | `python scripts/calorie_tracker.py history` |
| 记喝水 | 记录饮水量 | `python scripts/calorie_tracker.py water` |
| 查今天喝水 | 今日饮水量 | `python scripts/calorie_tracker.py summary` |

### 🏷️ 食品库

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 查热量 | 搜索食品营养成分 | `python scripts/calorie_tracker.py search-product` |
| 存食品 | 添加食品营养成分表到库 | `python scripts/calorie_tracker.py add-product` |
| 改食品 | 更新食品营养成分 | `python scripts/calorie_tracker.py update-product` |
| 查食品库 | 列出全部食品营养成分 | `python scripts/calorie_tracker.py list-products` |
| 批量导入 | 批量录入/更新食品库 | `python scripts/batch_import.py import` |
| 校验批量 | 只校验 JSONL 不写入 | `python scripts/batch_import.py validate` |
| 查食品库去重 | 全库去重检查 | `python scripts/batch_import.py dedupe` |

### ⚖️ 体重

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记体重 | 记录体重(2026-07-20 改:身高从 user_profile 读;note 用 --note 标志) | `python scripts/calorie_tracker.py weight` |
| 改体重记录 | 修改历史体重记录 | `python scripts/calorie_tracker.py weight-update` |
| 查体重历史 | 体重历史记录 | `python scripts/calorie_tracker.py weight-history` |
| 查体重趋势 | 体重趋势分析 | `AI 路由(Python API)` |
| 对比体重 | 两时间段体重对比 | `AI 路由(Python API)` |
| 查体重波动 | 体重波动分析 | `AI 路由(Python API)` |
| 设体重目标 | 设定体重目标和截止日期 | `python scripts/calorie_tracker.py weight-goal` |
| 查体重目标 | 体重目标达成进度 | `AI 路由(Python API)` |

### 🏃 运动

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记运动 | 记录运动消耗 | `python scripts/exercise_tracker.py add` |
| 改运动记录 | 更新运动记录 | `python scripts/exercise_tracker.py update` |
| 查运动记录 | 查询运动记录 | `python scripts/exercise_tracker.py list` |
| 查运动汇总 | 运动汇总统计 | `python scripts/exercise_tracker.py summary` |
| 查运动类型 | 运动类型统计 | `python scripts/exercise_tracker.py stats` |
| 查运动趋势 | 运动热量趋势 | `python scripts/exercise_tracker.py trend` |

### 🏋️ 健身计划

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 查健身计划 | 查看训练计划 HTML 页面(DB 数据驱动,含今日复盘 section) | `python scripts/render_workout_plan.py` |
| 制定健身计划 | AI 采访式对话 → 校验 → 写入 | `AI 路由(无 CLI)` |
| 落地健身计划 | 将某天计划执行(补计划 + 记心愿 + 训记推送) | `组合:补计划 + 记心愿 + 训记推送` |
| 卡路里同步 | 批量落地 3 天 + 调「回写训记」 | `组合:落地健身计划 × 3 + 回写训记` |
| 回写训记 | 拉训记数据回写 exercise_log(幂等) | `python scripts/xunji_bridge.py backfill [--date <DATE>] [--days <N>]` |
| 训记-覆盖X日的训练计划 | 用卡路里 plan 覆盖训记某天训练 | `python scripts/xunji_bridge.py overlay-plan --date <DATE>` |
| 改健身计划 | AI 对话定位意图 → 改/增/删时段、调整周次 | `AI 路由 → python scripts/plan_generator.py` |
| 复盘训练 | 对指定时间段做 plan vs 实绩对比 | `python scripts/exercise_review.py [--start <DATE> --end <DATE>] [--today] [--yesterday] [--day-before-yesterday] [--days <N>]` |
| 扫禁忌 | 检测 plan/DB 中禁忌动作(腰/膝/肩) | `python scripts/scan_contraindications.py [--part {腰\|膝\|肩\|all}] [--strict]` |
| 审计动作名 | 扫描 plan 里非训记官方动作名(push-plan 前必跑) | `python scripts/audit_plan_names.py [--strict] [--fix-suggestions]` |

### 📊 分析

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 查热量趋势 | 热量摄入趋势 | `AI 路由(Python API)` |
| 查营养配比 | 营养素占比分析 | `AI 路由(Python API)` |
| 查热量缺口 | 热量缺口分析 | `AI 路由(Python API)` |
| 查食物排行 | 食物排行榜(默认高热量榜) | `AI 路由(Python API)` |
| 查高热量榜 | 热量炸弹 TOP5 | `AI 路由(Python API)` |
| 查低热量榜 | 低热量健康 TOP5 | `AI 路由(Python API)` |
| 查频繁吃榜 | 最常吃的食物 TOP5 | `AI 路由(Python API)` |
| 查高碳水榜 | 高碳水食物 TOP5 | `AI 路由(Python API)` |
| 查高蛋白榜 | 高蛋白食物 TOP5 | `AI 路由(Python API)` |
| 查运动分布 | 运动类型分布 | `AI 路由(Python API)` |
| 查运动贡献 | 运动对热量缺口的贡献占比 | `AI 路由(Python API)` |

### 📋 综合

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 设营养目标 | 设置每日营养目标 | `python scripts/calorie_tracker.py goal` |
| 查营养目标 | 查看当前每日营养目标 | `python scripts/calorie_tracker.py get-goal` |
| 查健康报告 | 四维度综合健康仪表盘 | `AI 路由(Python API)` |
| 查卡路里数据 | 数据健康检查 | `AI 路由(无 CLI)` |

### 📋 复盘(2026-07-15 新增)

> **核心定位**:运动表现(健身计划 vs 运动记录)是第 1 优先级,其次是饮食摄入和热量平衡。
> **设计**:从第一性原理出发,3 步公式 = 回顾 → 反思 → 改进。区别于"健康报告"(只给数据)。

| 唤醒词 | 功能 | 默认参数 | CLI |
|--------|------|---------|-----|
| `复盘` | 立即生成复盘 + 飞书发送 | 过去 7 天 | `python scripts/calorie_tracker.py review --full` |
| `今日复盘` / `复盘今日` / `日复盘` | 当日复盘 | 今天 | `python scripts/calorie_tracker.py review --full --type day` |
| `本周复盘` / `复盘本周` / `周复盘` | 本周复盘 | 本周一-今天 | `python scripts/calorie_tracker.py review --full --type week` |
| `本月复盘` / `复盘本月` / `月复盘` | 本月复盘 | 本月 1 号-今天 | `python scripts/calorie_tracker.py review --full --type month` |
| `本年复盘` / `复盘本年` / `年复盘` | 本年复盘 | 今年 1/1-今天 | `python scripts/calorie_tracker.py review --full --type year` |
| `复盘 7/1 到 7/14` | 自定义范围 | - | `python scripts/calorie_tracker.py review --full --range 2026-07-01:2026-07-14` |
| `定时复盘` | 入口(开/关/查) | - | - |
| `开启定时复盘` | 启动 cron(默认 23:00 / 过去 7 天) | - | `mavis cron create ...` |
| `关闭定时复盘` | 删除 cron | - | `mavis cron delete ...` |
| `查定时复盘` | 查看当前配置 | - | `mavis cron list` |

#### 复盘子命令(Q16=B 多子命令)

```bash
# 全跑(默认):生成 HTML → 上传飞书云盘 → 飞书发送摘要
# 注意:full 需要先有 HTML(--html-path)和飞书文本(--text),由 agent 提前生成
python scripts/calorie_tracker.py review --full --html-path <temp.html> --text "飞书摘要..." [--feishu-url <url>]

# 分步跑(推荐调试用)
# 1. 查数据 → 拿到 data_path(原始数据 JSON)+ prompt_path(LLM 提示模板)
python scripts/calorie_tracker.py review --gen [--range X:Y] [--type day|week|month|year]

# 2. agent 读 data_path,自己写 HTML 装填 70 个 data-field,保存到 temp

# 3. 上传 HTML 到飞书云盘 → 拿到飞书 URL
python scripts/calorie_tracker.py review --archive --html-path <temp.html>

# 4. 发飞书文本(纯文本,agent 自己写摘要,可选带飞书 URL)
python scripts/calorie_tracker.py review --send --text "飞书摘要..." [--feishu-url <url>]
```

#### 数据流(2026-07-16 重构:agent 直接处理,不调用户态 LLM)

```
calorie_tracker.py review --gen
    ↓
review_engine.py: 7 维 SQL(摄入/运动/体重/健身计划/profile/营养目标/Top 5 食物)+ 衍生计算(TDEE/缺口/理论减重/营养比例)
    ↓
review_cli.py gen: 保存 data_path + prompt_path 到 temp
    ↓
agent(我,小匠/M3)读 data → 写 HTML 装填 70 个 data-field
    ↓
calorie_tracker.py review --archive: 上传 HTML 到飞书云盘
    ↓
agent 写飞书摘要文本
    ↓
calorie_tracker.py review --send: 发送到群/IM
```

**为什么 agent 直接处理**:`llm_call.py` 在用户态跑永远 401(`apiKey: sk-xxx` 是 placeholder),
mavis 框架只在 IDE 进程内部自动注入真 token。手动复盘场景 agent(我)本来就在对话里,
**我就是 LLM**,不需要绕一圈调 API。`call_llm()` 已改为 `NotImplementedError`。

#### 8 个口语化 dim(从第一性原理)

| 顺序 | 标题 | 副标签 | 数据维度 |
|---|---|---|---|
| 1 | **总结** | 3 亮点 + 3 问题 + 3 建议 | 3+3+3 摘要 |
| 2 | **训练** ⭐P1 | 健身计划 vs 运动记录 | 完成率 / 频次 / 组数 / 时长 / 5-7 条 plan vs actual |
| 3 | **饮食** | 吃进去多少 | 平均热量 / 蛋白碳脂 / vs 目标 / 异常天 |
| 4 | **运动** | 消耗多少 | 运动消耗 / 日均 / TDEE / 类型 |
| 5 | **热量** | 缺口多少 | 周缺口 / 日均 / 预期 / 理论减重 |
| 6 | **体重** | 变化趋势 | 起 / 止 / 变化 / 波动 / 7 天折线 |
| 7 | **习惯** | 高频 + 异常 | 营养结构比例 / Top 5 食物 / 行为异常 |
| 8 | **目标** | 进度 | 进度条 / vs 体重 / vs 营养 / 预计还需 N 周 |

#### 环境变量

| 变量 | 用途 | 默认 |
|------|------|------|
| `REVIEW_FEISHU_TARGETS` | JSON 数组,例 `[{"type": "group", "group_name": "加油小分队🧸"}, {"type": "im", "open_id": "ou_xxx"}]` | 空(不发送,只走 gen+archive) |
| `USER_AGE` | **(已废弃)** review_engine.py 现走 user_profile 表,无需此 env | - |
| `USER_GENDER` | **(已废弃)** 同上 | - |

**注意**:`REVIEW_FEISHU_CHANNEL` / `REVIEW_FEISHU_WEBHOOK_URL` / `REVIEW_FEISHU_USER_OPEN_ID` 已废弃,
统一改为 `REVIEW_FEISHU_TARGETS` JSON 数组(支持多目标,失败降级)。

#### 相关文件

| 文件 | 角色 |
|------|------|
| `review_template.html` | 装填模板(70+ 个 data-field,8 个 dim,Apple 系统色,移动端自适应) |
| `scripts/review_cli.py` | 独立 CLI 入口(gen/archive/send/full 4 子命令) |
| `scripts/review_engine.py` | 7 维 SQL + 衍生计算 + 摘要提取 + **体重 SVG 渲染器(算法生成,2026-07-17)** |
| `scripts/review_prompts.py` | agent 装填参考 prompt(call_llm 已废弃 NotImplementedError) |
| `scripts/review_feishu.py` | 飞书发送(group/im)+ 飞盘上传(用 cwd= 而非 Set-Location) |

#### 📐 agent 装填协议(2026-07-17 增)

**核心原则**:agent 不调用户态 LLM(`llm_call.py` 永远 401),而是**自己在对话里读 enriched JSON,装填 data-field**。

**装填数据流**:

```
review_cli.py gen --type week
    ↓ 保存 raw_data + enriched 到 temp/data_*.json
agent 读 JSON
    ↓
装填 review_template.html 的 70+ 个 data-field
    ↓
保存到 temp/review_*.html
    ↓
review_cli.py archive --html-path <html>  → 飞书 URL
```

**关键字段类型**(2026-07-17 修订):

| data-field | 来源 | 类型 |
|---|---|---|
| 70 个普通字段(text/数字) | enriched 里的 derived 字段 | 直接装填 textContent |
| `weight_trend_svg` | **`enriched.weight_trend_svg`(算法渲染字符串)** | **完整 `<svg>` 字符串**(不要自己写) |
| `weight_trend_title` | `enriched.weight_trend_meta.title` | text |
| `weight_trend_range` | `enriched.weight_trend_meta.range_text` | text |
| `weight_trend_note` | 自己基于 meta + 实际数据写 | text(解释趋势 + 异常) |
| `top_food_1..5` | `enriched.top_foods[].name + cnt + avg` | text |
| `nutrition_goal_match_rate` | **`enriched.nutrition_match.summary`** | text(真实统计,不编) |
| `estimated_weeks_left` | 自己基于 weekly_deficit 算 | text |

**体重 SVG 自动渲染细节**(`_render_weight_trend_svg` 算法):

- **数据点**:每天取最后一条体重
- **Y 轴范围**:自动算(data min/max ± 0.3kg),goal_weight 距数据 > 5kg 不纳入(避免数据挤)
- **X 轴密度**:
  - ≤7 点:每天
  - ≤30 点:每 5 天
  - ≤90 点:每周
  - >90 点:每月
- **标记**:
  - 🔵 最低点:橙色 ▼
  - 🟢 第一天:绿色
  - 🔵 最后一天:蓝色 ▲
  - 🟣 最高点:紫色 ★(如果唯一)
- **目标虚线**:只在 goal 距数据 ≤ 5kg 时画(否则用文字说明 `vs_weight_goal`)

**enriched.today_partial** 字段(2026-07-17 增):
- `enriched.today_partial.intake` = 今日已摄入(数据未完整,**不纳入 avg**)
- `enriched.today_partial.burn` = 今日已运动
- `enriched.complete_days_count` = 完整日数(默认 = 7-1 = 6)
- **平均/缺口/营养达标率** 全部用 complete_days 算(避免今日污染)

**异常天装填**:
- 从 `enriched.daily_intake` 里挑"脂肪/碳水/热量"异常的 complete_days
- **不要把 today_partial 当异常**(今日数据未完整)

#### 🤖 AI 触发场景详述(2026-07-17 增)

**设计原则**:agent 在对话里负责自然语言 → CLI 参数的转换,本节列已实测和理论支持的映射,帮 agent / 接手者快速判断。

##### 自然语言 → CLI 映射表

| 自然语言(用户说) | CLI 参数 | 实测状态 |
|---|---|---|
| `复盘` | `--type week`(默认过去 7 天) | ✅ 实测 |
| `今日复盘` / `复盘今日` / `日复盘` | `--type day` | ✅ 实测 |
| `本周复盘` / `复盘本周` / `周复盘` | `--type week` | ✅ 实测 |
| `本月复盘` / `复盘本月` / `月复盘` | `--type month` | ✅ 实测(7/17 跑出 2026-07-01:2026-07-17) |
| `本年复盘` / `复盘本年` / `年复盘` | `--type year` | ✅ 实测(7/19 跑出 2026-01-01:2026-07-19) |
| `复盘 2026-07-17` | `--range 2026-07-17`(ISO 单日) | ✅ 实测 |
| `复盘 7/17` | `--range 7/17`(简写单日) | ✅ 实测 |
| `复盘 7/11 到 7/16` | `--range 2026-07-11:2026-07-16`(ISO 范围) | ✅ 实测 |
| `复盘 7/11-7/16` | `--range 7/11:7/16`(简写范围) | ✅ 实测 |
| `复盘过去 7 天` / `复盘最近一周` | `--range <7 天前>:今天` | ✅ 实测 |
| `复盘过去 30 天` / `复盘最近一个月` | `--range <30 天前>:今天` | ✅ 实测(30 天跨月) |
| `复盘上周` / `复盘上一周` | `--range <上周一>:<上周日>` | ✅ 实测(7/19 跑出 2026-07-06:2026-07-12) |
| `复盘 7 月` | `--range 2026-07-01:2026-07-31`(整月) | ✅ 实测(7/19 跑出 2026-07-01:2026-07-31) |

##### 解析规则(agent 参考)

**日期格式**:
- ISO 完整日期:`2026-07-17` ✓
- 简写日期:`7/17` / `7-17` → 当年(2026-07-17)
- 自然语言:`今天` / `昨天` / `上周` / `过去 N 天` → 相对计算
- 错误格式:`2026-7-17`(无前导 0)/ `7月17日` → 报错

**范围分隔符**:
- 中文:`7/11 到 7/16`
- 英文 dash:`7/11-7/16`
- 冒号:`7/11:7/16` (CLI 实际接受的格式)

##### 异常处理

| 情况 | 行为 |
|---|---|
| 日期范围无数据 | 提示"该范围无记录,请检查日期或更换范围" |
| 日期格式错 | 提示"日期格式应为 YYYY-MM-DD 或 M/D" |
| 单日无数据 | 同"日期范围无数据" |
| start > end | 提示"开始日期不能晚于结束日期" |

##### 实测覆盖(2026-07-17 完成)

7 个 case 全部 ✅ `status: ok`:

| 编号 | case | CLI | 数据范围 | 关键输出 |
|---|---|---|---|---|
| A1 | 复盘 7/17 | `--range 2026-07-17` | 7/17-7/17 | TDEE=2847,缺口=984 |
| A2 | 复盘 7/11 到 7/16 | `--range 2026-07-11:2026-07-16` | 7/11-7/16 | 缺口=9215,理论减重 1.2kg |
| A3 | 复盘过去 30 天 | `--range 2026-06-17:2026-07-17` | 6/17-7/17 | 缺口=40786,理论减重 5.3kg |
| A4 | 今日复盘 | `--type day` | 7/17-7/17 | 同 A1 |
| A5 | 复盘 7/17(简写) | `--range 7/17` | 7/17-7/17 | OK |
| A6 | 复盘 7/11:7/16 | `--range 7/11:7/16` | 7/11-7/16 | OK |
| A7 | 本月复盘 | `--type month` | 7/1-7/17 | OK |

### 📸 身材照片

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记身材照 | 记录身材照片 | `python scripts/body_photo_tracker.py add` |
| 查身材照 | 查看照片历史 | `python scripts/body_photo_tracker.py list` |
| 删身材照 | 删除照片 | `python scripts/body_photo_tracker.py delete` |
| 改照片标签 | 修改照片标签 | `python scripts/body_photo_tracker.py tag` |

---

# 卡路里 - 热量追踪技能 v2.0

## 功能概述

- **食物记录**:记录热量、蛋白质、碳水、脂肪(克为单位)
- **每日目标**:设置热量和三大宏量营养素目标
- **体重追踪**:记录体重,自动计算BMI
- **数据分析**:3大类11种分析维度 + dashboard综合报告
- **身材照片**:记录身材照片,支持自定义标签(正面/背面/侧面/手臂等),可生成 GIF 变化动画

## 数据库结构

详见 [`references/database_schema.md`](references/database_schema.md)

共 8 张表:`food_log`(饮食记录)、`daily_goal`、`weight_log`、`exercise_log`、`nutrition_products`、`workout_plan_config`(健身计划元信息)、`workout_plans`(健身日程)、`body_photos`

> **2026-07-12 重构**:`entries` → `food_log`;`fitness_goals` 和 `sleep_records` 已删除,重构为 `workout_plan_config` + `workout_plans`。所有 8 张表均由 `db.py init_db()` 统一创建。

## 📂 脚本模块结构(v2.3 拆分后)

业务逻辑按"领域对象"拆分到独立文件,每个文件 ≤ 350 行,单屏可读。

### 核心模块(calorie_tracker.py 拆分)

| 文件 | 行数 | 职责 | 公共 API |
|---|---|---|---|
| `db.py` | ~145 | 数据库基础:路径解析、连接、初始化、迁移 | `find_db_path` / `connection` / `get_db` / `init_db` |
| `db_utils.py` | ~15 | 兼容层:re-export db.py(旧脚本继续可用) | - |
| `diet.py` | ~215 | 饮食记录 | `add_meal` / `delete_meal` / `list_meals` / `get_daily_summary` / `infer_meal_type` |
| `water.py` | ~65 | 饮水记录(复用 food_log 表,food_name='💧水') | `add_water` |
| `nutrition_goal.py` | ~95 | 每日营养目标 | `set_nutrition_goal` / `get_nutrition_goal` |
| `weight.py` | ~190 | 体重记录 | `log_weight` / `update_weight` / `get_weight_history` |
| `weight_goal.py` | ~110 | 体重目标 + 进度 | `set_weight_goal` / `get_weight_goal` / `print_goal_progress` |
| `exercise.py` | ~110 | 运动记录 | `add_exercise` / `get_exercise_log` / `print_exercise_summary` |
| `product_library.py` | ~160 | 食品库 CRUD | `add_product` / `search_products` / `update_product` / `list_products` |
| `calorie_history.py` | ~55 | 热量历史 | `get_calorie_history` |
| `calorie_tracker.py` | ~250 | **CLI 入口**:main + argparse + usage | - |

### 分析包(analysis/)

11 个分析函数按维度拆分到子模块,4 个统一入口在 `__init__.py`。

| 文件 | 行数 | 职责 |
|---|---|---|
| `analysis/__init__.py` | ~125 | 4 统一入口 + 11 原子函数 re-export |
| `analysis/_utils.py` | ~55 | 共享工具:`_get_db` / `_parse_date` / `_days_between` / `BMR_ACTIVITY_FACTOR` |
| `analysis/weight.py` | ~210 | 4 个体重分析:`weight_trend` / `weight_compare` / `weight_milestone` / `weight_volatility` |
| `analysis/diet.py` | ~225 | 4 个饮食分析:`diet_calorie_trend` / `diet_macro_ratio` / `diet_food_ranking` / `diet_deficit_analysis` |
| `analysis/exercise.py` | ~135 | 3 个运动分析:`exercise_trend` / `exercise_type_breakdown` / `exercise_deficit_contribution` |
| `analysis/dashboard.py` | ~45 | 综合报告 `dashboard(start, end)` |

### 独立 CLI 脚本(已有,未拆分)

| 文件 | 行数 | 职责 |
|---|---|---|---|
| `exercise_tracker.py` | 442 | 运动更完整的 CLI(add/update/list/summary/stats/trend)|
| `body_photo_tracker.py` | 356 | 身材照片 CLI(add/list/delete/tag/gif)|
| `plan_generator.py` | 新建 | 健身计划生成(校验+写入)|
| `workout_plan.py` | 新建 | 计划循环逻辑 + 按日查询 |
| `render_workout_plan.py` | 新建 | HTML 渲染(DB→Apple 风格页面)|
| `adapters/xunji_adapter.py` | 新建 | 训记 API ↔ exercise_log 纯函数适配器(被 xunji_bridge 调用)|
| `xunji_bridge/` | 新建 | 训记训练拓展功能 CLI 入口包(verify/fetch/upsert/push-plan/overlay-plan/backfill/key/run-sync 8 子命令) |
| `generate_ts_config.py` | 269 | 从数据库生成 `config-calorie.ts` |

### 模块依赖图

```
calorie_tracker.py(CLI 入口)
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
   │    └─ weight_goal.py(get_weight_goal)
   ├─ analysis/diet.py
   │    └─ nutrition_goal.py(get_nutrition_goal)
   ├─ analysis/exercise.py
   └─ analysis/dashboard.py
        └─ weight.py / diet.py / exercise.py

所有模块 → db.py(数据库基础)
```

### 拆分原则

1. **业务领域优先**:文件名 = 管什么(diet/weight/exercise),不叫 `entries.py`/`ops/` 等抽象名
2. **避免歧义命名**:`weight_goal` 比 `goal.py` 清晰(还有 `nutrition_goal.py`)
3. **CLI 入口稳定**:calorie_tracker.py / exercise_tracker.py 等保留同名入口,内部委托给各模块
4. **兼容层保留**:`db_utils.py` 转发到 `db.py`,旧脚本 import 路径不变

## 命令行用法

### 食物记录
```bash
python scripts/calorie_tracker.py add "鸡胸肉" 165 31 0 3 150   # 食物名 热量 蛋白 碳水 脂肪 克数
python scripts/calorie_tracker.py update-meal 5 --grams 180      # 修改记录5的克数为180g
python scripts/calorie_tracker.py summary                        # 今日摘要(含饮水)
python scripts/calorie_tracker.py history 7                      # 最近7天历史
python scripts/calorie_tracker.py goal 1800 150 200 60 2000      # 设置目标:热量 蛋白 碳水 脂肪 饮水ml
python scripts/calorie_tracker.py water 500                      # 记录饮水 500ml
```

### 用户档案(profile,2026-07-16 新增)
```bash
python scripts/calorie_tracker.py profile set 30 male --height 177 --note "默认值"
python scripts/calorie_tracker.py profile get       # JSON 输出
python scripts/calorie_tracker.py profile show      # 人类可读
```

用途:review TDEE(Mifflin-St Jeor 公式)需要年龄+性别,优先从 user_profile 表读取。

### 用户档案(profile,2026-07-16 新增)
```bash
python scripts/calorie_tracker.py profile set 30 male --height 177 --note "默认值"
python scripts/calorie_tracker.py profile get       # JSON 输出
python scripts/calorie_tracker.py profile show      # 人类可读
```

用途:review TDEE(Mifflin-St Jeor 公式)需要年龄+性别,优先从 user_profile 表读取。

### 食品库
```bash
python scripts/calorie_tracker.py search-product "可乐"          # 搜索
python scripts/calorie_tracker.py add-product "可口可乐" "可口可乐" 42 0 0 0 10.6 10.6 0 20 "330ml"
python scripts/calorie_tracker.py update-product 1 --calories 45 # 更新
```

### 体重
```bash
# 2026-07-20 改:身高已不在 CLI 传;note 强制 --note 标志
python scripts/calorie_tracker.py weight 70                       # 不带备注
python scripts/calorie_tracker.py weight 70 --note "吃饱了"       # 带备注
# 旧用法 'weight 70 178' / 'weight 70 吃饱了' 都不再支持
python scripts/calorie_tracker.py weight-update 5 --weight 69.5   # 修改体重记录(按ID)
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

### 分析接口(11种维度)
```python
weight_analysis(start, end, 'trend')       # 趋势|compare|milestone|volatility
diet_analysis(start, end, 'calorie_trend') # calorie_trend|macro_ratio|food_ranking|deficit_analysis
exercise_analysis(start, end, 'exercise_trend') # exercise_trend|type_breakdown|deficit_contribution
dashboard(start, end)                      # 综合四维度仪表盘
```

---

## AI 路由规则

**重要提示**:所有命令使用技能目录下的 `scripts/` 路径前缀。

### Step 1:识别功能域

根据用户输入关键词判断功能域:

| 关键词 | 功能域 |
|--------|--------|
| 吃/食物/餐/喝/摄入/卡路里(食物相关) | 🍚 饮食记录 |
| 食品库/营养成分表/存食品 | 🏷️ 食品库 |
| 体重/公斤/kg/BMI/秤 | ⚖️ 体重 |
| 运动/跑步/骑行/俯卧撑/消耗(运动相关) | 🏃 运动 |
| 健身计划/训练计划/制定计划/改计划/落地计划 | 🏋️ 健身计划 |
| 趋势/排行/缺口/配比/分布/贡献 | 📊 分析 |
| 仪表盘/整体情况/报告/目标(营养) | 📋 综合 |
| 身材照/体型照/身体照片 | 📸 身材照片 |

### Step 2:域内精确匹配

在已识别的域内,按触发词速查表精确匹配唤醒词,执行对应 CLI。

### Step 3:歧义消解

| 歧义场景 | 判断规则 |
|---------|---------|
| "查热量" vs "查热量趋势" | 前者是搜索食品库,后者是分析模块 |
| "记运动" vs "查运动记录" | "记"=新增,"查"=查询 |
| "记吃的" vs "改吃的" | "记"=新增,"改"=修改已有记录 |
| "记体重" vs "查体重目标" | "记"=新增记录,"查"=查询进度 |
| "制定健身计划" vs "落地健身计划" | 前者是对话制定,后者是执行到当天 |
| "查食物排行" vs "查高热量榜" | 前者默认高热量,后者显式指定 |
| "设营养目标" vs "设体重目标" | 营养=calorie/protein/carbs/fat/water_goal 5 字段;体重=weight_goal+deadline 2 字段 |
| "查食物排行" vs "查高热量榜" | 前者默认高热量,后者显式指定 |
| "记身材照" vs "查身材照" | "记"=新增,"查"=查询 |

---

## AI 触发场景详述

**所有 CLI 路径前缀**:`python scripts/`

### 🍚 饮食记录:记吃了

**完整流程(重要)**:

#### Step 1:解析用户输入
提取:食物名、克数(如有)

#### Step 2:模糊查询 nutrition_products 表
执行:`python scripts/calorie_tracker.py search-product <食物名>`

#### Step 3:根据查询结果分流

**Path A:找到匹配结果(≥1条)**
```
列表显示 → 用户选择 → 确认克数 → 计算热量/100 × 克数 → 执行 add → 返回今日汇总
```

**Path B:库中没找到,用户提供了营养成分表图片(拍营养表)**
```
调用 mmx vision describe 识别图片:
  mmx vision describe --image <图片路径> \
    --prompt "请识别这张营养成分表,提取:产品名称、品牌、热量(千卡)、蛋白质(克)、脂肪(克)、饱和脂肪(克)、碳水化合物(克)、糖(克)、膳食纤维(克)、钠(毫克)。请以JSON格式返回。"
→ 展示结果 → 用户确认 → add-product 存库 → 继续 Path A
```

**Path C:库中没找到,用户无法提供营养成分表**
```
讨论估算克数 → mmx search 查询参考数据:
  mmx search query --q "<食物名> 营养成分表 每100克热量"
→ 用户确认 → 执行 add(参考数据不存库)
```

#### Step 4:返回确认信息
```
✓ 已记录:<食物名> (<热量>卡, <克数>克)
餐次:<早/午/晚/下午茶/夜宵>
今日:<热量>/<目标>卡 | 蛋白<蛋白>/<目标>g | 碳<碳>/<目标>g | 脂<脂>/<目标>g
```

### 🏷️ 食品库:存食品 / 查热量 / 改食品 / 查食品库

- **存食品**:解析输入或图片 → 提取营养成分 → `python scripts/calorie_tracker.py add-product <产品名> <品牌> <热量> <蛋白> <脂肪> <饱和脂肪> <碳水> <糖> <纤维> <钠> [备注]`
- **查热量**:`python scripts/calorie_tracker.py search-product <关键词>`
- **改食品**:`python scripts/calorie_tracker.py update-product <id> [--字段 值]`
- **查食品库**:`python scripts/calorie_tracker.py list-products`

### 📦 批量导入食品库(2026-06-30 新增)

适用场景:批量录入 / 批量更新 **10+ 条** 食品数据。

工具:`python scripts/batch_import.py`

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

### ⚠ 2026-07-20 改动:身高 SoT 迁移

- **之前**:weight_log.height_cm 是身高的实际存放处,user_profile.height_cm 是"同步过来的镜像"
- **现在**:user_profile.height_cm 是 SoT(单一来源),weight_log.height_cm 列保留但不再写入
- **旧数据 100% 保留**:101 条 weight_log 身高已一次性回填为 **177cm**(用户真身高),BMI 也按 177 重算
- **"记体重"不再需要传身高**:自动从 user_profile 读
- **旧 CLI `weight 70 178` 已删除**:直接报错(SKILL 层修,parser 自然拒绝未知参数)
- **旧 CLI `weight 70 "我吃饱了"` 已删除**:note 必须用 `--note` 标志
- **旧 CLI `weight-update 5 --height 178` 已删除**:直接报错
- **profile sync-height 命令已删除**:函数也删除(2026-07-20)
- **note 标志用法**:
  - ✅ `weight 70`(不带备注)
  - ✅ `weight 70 --note "我今天吃饱了"`(带备注)
  - ❌ `weight 70 178`(178 是未识别参数,parser 报错)
  - ❌ `weight 70 我今天吃饱了`(没 --note 标志,parser 报错)
- **首次使用流程**:
  1. `calorie_tracker.py profile set 30 male --height 177`(身高只在这里设)
  2. `calorie_tracker.py weight 70 [--note '<备注>']`(BMI 自动算)
  3. 不需要再设,以后 `weight 70` 即可
- **回滚**:从 git 找 `scripts/weight.py` `scripts/calorie_tracker.py` `scripts/profile.py` 2026-07-20 前版本

### ⚖️ 体重:记体重 / 查体重历史 / 查体重趋势 / 对比体重 / 查体重波动 / 设体重目标 / 查体重目标

- **记体重**:`python scripts/calorie_tracker.py weight <体重> [--note '<备注>']`(2026-07-20 改:身高从 user_profile 自动读;note 强制 --note 标志)
- **改体重记录**:`python scripts/calorie_tracker.py weight-update <ID> [--weight <公斤>] [--note <备注>]`(2026-07-20 改:--height 已删除,身高只能从 profile 改)
- **查体重历史**:`python scripts/calorie_tracker.py weight-history [天数]`
- **查体重趋势**:`AI 路由(Python API): weight_analysis(start, end, 'trend')`
- **对比体重**:`AI 路由(Python API): weight_analysis(start, end, 'compare', compare_start, compare_end)`
- **查体重波动**:`AI 路由(Python API): weight_analysis(start, end, 'volatility')`
- **设体重目标**:`AI 路由(Python API): set_weight_goal(weight_goal, deadline)`
- **查体重目标**:`AI 路由(Python API): weight_analysis(start, end, 'milestone')`

### 🏃 运动:记运动 / 改运动记录 / 查运动记录 / 查运动汇总 / 查运动类型 / 查运动趋势

- **记运动**:`python scripts/exercise_tracker.py add --date <日期> --type <类型> --calories <卡> [--minutes <分钟>] [--reps <次数>] [--category <类>] [--intensity <级>] [--distance <km>] [--heart-rate <bpm>] [--set <N>] [--load <kg>]`
- **改运动记录**:`python scripts/exercise_tracker.py update --id <ID> [--字段 值]`
- **查运动记录**:`python scripts/exercise_tracker.py list [--days N] [--date <日期>] [--type <类型>] [--category <类>]`
- **查运动汇总**:`python scripts/exercise_tracker.py summary [--days N]`
- **查运动类型**:`python scripts/exercise_tracker.py stats --type <breakdown|total>`
- **查运动趋势**:`python scripts/exercise_tracker.py trend [--days N]`

#### 🎯 运动 AI 路由规则(必读 · 2026-06-29 扩展)

##### A · 卡路里综合考虑规则

用户可能给卡路里值、可能不给。AI 必须按以下流程处理:

```
Step 1  识别用户报的卡路里值(若有)
Step 2  AI 用 METs 公式独立推算(不依赖心率)
        - 有氧/柔韧/日常:cal = MET × 体重 × 时长(h)
        - 力量训练    :cal = MET × 体重 × 组数 × 0.05h
        - 体重从 weight_log 最新一条取,不向用户追问
Step 3  对比两个值,按偏差处理:
        - 偏差 < 20%       → 取 AI 推算值入档
        - 偏差 20-50%      → 取两者中位 + note 标记
        - 偏差 > 50%       → 反问用户确认哪个对(不入档)
```

实现:`exercise.combined_calories(user_reported, estimated)` 返回 `(final, note_suffix, deviation)`。

##### B · 强度字段优先级

```
1. 用户口语明确说(如"很累"、"轻松"、"累死") → AI 翻译成 4 档(最高优先)
2. AI 基于 METs 兜底(无口率)                 → 按 MET 范围估
3. 都没有                                       → NULL(不强制)
```

口语映射表(节选):
| 用户说 | 4 档 |
|---|---|
| "挺轻松"、"没什么感觉"、"散步" | 低 |
| "一般"、"还行"、"中等" | 中 |
| "挺累"、"暴汗"、"喘" | 高 |
| "累死"、"力竭"、"撑不住" | 极限 |

METs 兜底映射:
| MET 范围 | 4 档 |
|---|---|
| < 3 | 低 |
| 3-6 | 中 |
| 6-9 | 高 |
| > 9 | 极限 |

实现:`exercise.parse_user_intensity(text)` + `exercise.estimate_intensity_met(met)`。

##### C · 心率询问规则(场景化)

| 场景 | AI 是否问心率 |
|---|---|
| 有氧(跑步/骑行/跳绳/八段锦) | ✅ 主动问 1 次 |
| 力量训练(哑铃/深蹲/俯卧撑) | ❌ 不问 |
| 日常活动(家务/做饭) | ❌ 不问 |

问法示例:`"顺便问下,平均心率有记到吗?没记就跳过"`
用户答"没记"或忽略 → 心率字段 NULL,不卡流程。

##### D · 运动分类路由

`category` 字段 4 个值,AI 根据动作名自动推断:

| 关键词 | category |
|---|---|
| 哑铃/杠铃/史密斯/弯举/推举/深蹲/卧推/划船/俯卧撑/引体/平板支撑 | 力量 |
| 八段锦/太极/瑜伽/拉伸 | 柔韧 |
| 家务/做饭/洗衣/打扫/通勤/走路/散步 | 日常 |
| 跑步/骑行/跳绳/椭圆机/游泳/其他 | 有氧(兜底) |

实现:`exercise._infer_category(exercise_type)`。

##### E · 力量训练流式录入

每组 = 1 行 exercise_log:

```bash
# 第 1 组
exercise_tracker.py add --date 2026-06-29 --type 哑铃弯举 \
  --set 1 --reps 10 --load 10 --category 力量 --calories 22

# 第 2 组
exercise_tracker.py add --date 2026-06-29 --type 哑铃弯举 \
  --set 2 --reps 10 --load 10 --category 力量 --calories 22
```

用户做完一组就告诉 AI 一组数据,AI 逐条 add。**绝对不要**等做完 N 组再汇总成一条记录。

### 🏋️ 健身计划:查 / 制定 / 改 / 落地 / 同步

- **查健身计划**:`python scripts/render_workout_plan.py` 输出 Apple 风格 HTML
- **制定健身计划**:AI 4 轮对话制→ 产出 JSON → `plan_generator.write_plan()` 写入
  ```
  贯穿规则:
    A. 安全止损 - 制止明显不安全的要求(如"每天 50 组胸")
    B. 解释决策 - 每次建议必须说"因为..."
    C. 现状感知 - 利用基线信息在后续决策中引用
    D. start_date 必须是周一(2026-07-13 加) - 健身计划以自然周对齐;若用户给的不是周一,先 round 到最近周一再写入;不 round 会导致用户口语"第 N 周"跟算法返的 plan_week 错位(因为 n 周循环按距离 start 的整 7 天算)

  第1轮·基线建立:
    当前训练状态 + 目标 + 水平 + 伤病/保护部位 + 器材清单 + 讨厌的动作
    → 建立完整用户画像

  第2轮·结构性决策:
    每周几天 / 每天几时段 / 每时段多久
    部位优先级 + 周总组数(AI 建议 + 解释为什么)
    分化策略(推拉腿/部位分化/全身)
    AI 实时校验:时段数×时长÷3min ≥ 总组数
    → 确定时间框架和部位分配

  第3轮·精细化:
    周期化:几周循环 + 周权重方案
    递进协议:每周期内如何推进(RPE递增/rep递增/重量递增)
    热身 + 有氧如何嵌入
    评估指标:4周后怎么判断效果
    → 确定训练变量

  第4轮·动作落地:
    AI 推荐候选动作 → 用户确认 + 主备关系
    AI 校验:角度多样性/器材匹配/训记库中验证
    确认 → 生成 JSON → validate_plan() → write_plan()
  ```
- **改健身计划**:AI 对话定位意图 → 一个唤醒词覆盖所有写操作(改时段/加时段/删时段/调整周/改配置)
- **复盘训练**:`python scripts/exercise_review.py [--start <DATE> --end <DATE>] [--today] [--yesterday] [--day-before-yesterday] [--days <N>]` → 对 [start, end] 范围内每一天做 plan vs 实绩对比(完成率 / 漏做 / 超额 / 异常)。AI 路由负责解析"今日/昨天/前天/这周/X-Y"等口语化时间 → `--start` / `--end`。
  ```
  参数:
    --start      <DATE>       开始日期
    --end        <DATE>       结束日期
    --today                  今日(start=end=today)
    --yesterday              昨日(start=end=yesterday)
    --day-before-yesterday   前日(start=end=today-2)
    --days N                 最近 N 天(start=today-N+1, end=today)
  数据来源:
    - workout_plans(每日 sessions + total_sets)
    - exercise_log(每日实绩,set_index 计数)
  报告内容(每天):
    - 计划组数 vs 实做组数
    - 完成率
    - 异常项:完成率 < 50% / 超额 > 130% / 计划未做 / 计划休息但实做
  使用场景:晚上 10 点卡路里同步 → 触发"复盘训练" → 看 plan vs 实绩差距 → 决定要不要改健身计划。
  ```
- **落地健身计划**:将指定日期的训练计划落地到作息/备忘/训记三个系统。执行必须全部完成三步,逐 session 独立执行,某条失败跳过继续。
  ```
  Step 1 · 数据准备
    调 workout_plan.get_day_plan(日期)。
    如果用户没说日期,默认今天。
    休息日 → 告知用户并退出。
    **未开始(2026-07-13 增)**:返回的 dict 含 `unstarted=True` 时,表示该日期早于 plan start_date,跳过后续 Step 2/3/4,告知用户"计划 X 月 X 日开始"并退出。

  Step 2 · 联动作息管家
    对每个 session 调「补计划 {日期} 健身 {session_label} {time_start}-{time_end}」
    附带 notes(前 3 动作名 + 总数),category="运动"。
    ensure-plan-event 已内置飞书日历同步(本地 DB 和飞书日历缺哪边建哪边)。
    接口幂等,重复调用自动跳过。

  Step 3 · 联动备忘录
    对每个 session,先构造心愿内容:
      心愿内容 = 「健身 {session_label} {time_start}-{time_end}」
    此字符串在"查"和"记"时必须完全一致,AI 不得自由改写措辞。

    **查重(2026-07-14 改为三步:本地 + 飞书,content + due 双键,都没有才新建)**:
      第一性:本地 notes 是 SoT,飞书 task 是镜像,二者必须 1:1 对应。
      任何"只建一边"都视为数据不一致,必须靠"三步查重"防止。

      Step 3.1 · 查本地 notes 表(备忘录的"查心愿")
        调备忘录「查心愿 {心愿内容} --category 心愿 --due {该日期}」
        → 有匹配 → 跳过(已存在,不动)

      Step 3.2 · 查飞书 task 列表(lark-cli)
        调「lark-cli task +search --query <心愿内容> --due <该日期>,<该日期> --format json」
        解析 `data.items[]`,找 `summary == 心愿内容` 且 `due_at` 以该日期开头的项
        → 有匹配(同 summary + due)→ 跳过(已存在,不动)
        (注:即使本地没查到,只要飞书查到也算已存在,避免重复)

      Step 3.3 · 都没有才新建
        调备忘录「记心愿 {心愿内容} --category 心愿 --due {该日期}」创建
        (add_wish_sync 内部会调 lark-cli task +create 同步到飞书)
    不建过去日期的心愿。

  Step 4 · 联动训记
    检查训记 KEY 环境变量,权威名 `XUNJI_TRAINS_KEY`(兼容旧名 `XUNJI_API_KEY`):
      未配置 → 调 `python scripts/xunji_bridge.py key status` 让用户看状态,
              再用 `python scripts/xunji_bridge.py key set <KEY>` 设置。
              KEY 申请:训记 App → 我的 → 设置 → 第三方接入。
      已配置(PRIMARY) → 提示「✅ 训记 KEY 已配(XUNJI_TRAINS_KEY),开始同步」
      已配置(LEGACY fallback) → 提示「⚠ 用了旧名 XUNJI_API_KEY,建议用 key set 迁移到 XUNJI_TRAINS_KEY」

    KEY 就绪后,**不再**手写 HTTP,改为调训记训练拓展 CLI:
      python scripts/xunji_bridge.py push-plan --date <DATE>
    该命令内部完成:
      1 读 workout_plans 中当天的所有 session
      2 按以下规则转成训记 res[] 格式:
         - schema_version = "train_open_api_v2"
         - client_request_id = "{日期}_{session_label}_{uuid8}"(幂等键;uuid8 后缀满足训记 unique-id-from-agent 硬约束,避免同 label 重推被训记去重)
         - datestr / title / start=0 / end=0
         - movements 只保留 name + sets;每条 set 加 "done": false
      3 调 POST /api_upsert_trains_for_llm_v2
      4 多个 session 间自动等 45s(训记写 API 限频)
      5 输出每 session ok/fail 状态,JSON 格式

    ⏱ 训记推送约 3 分钟/天。

    训记写入失败的 session 重新调落地可重试(client_request_id 保证幂等)。

  末尾输出汇总:
    ✅ 补计划 4/4 已创建
    ✅ 心愿 3/4 已建(1 条已存在跳过)
    ⚠️ 训记推送 3/4(S3 超时,重新调落地可重试)
  ```

- **卡路里同步**:批量落地 N 天(含飞书日历 + 心愿 + 训记推送)+ 训记回写。
  2026-07-20 改:一键脚本(sync_plan.py)封装 4 步,加 `--start-offset` 默认 0=今天;
  Step 4 训记回写默认 `--days 1`(只回写今天已打勾的;周末补练用 `--backfill-days 3`)。

  **快捷命令(2026-07-20 新增,推荐)**:
  ```
  bash scripts/sync_plan.sh              # 一键 4 步,无需手工拼装
  bash scripts/sync_plan.sh --start-offset 1   # 从明天起 3 天
  bash scripts/sync_plan.sh --days 7           # 推 7 天而非默认 3 天
  ```
  把跨 4 个工具的拼装下沉到脚本里,避免每次 AI 重新组装 + 漏步骤。

  **手动流程(仅 AI 路径没装好 sync_plan.sh 时用)**:
  ```
  前置:KEY 检查同「落地健身计划」Step 4
    检查 XUNJI_TRAINS_KEY(优先,兼容 XUNJI_API_KEY)。
    未配置 → 调 `python scripts/xunji_bridge.py key status` 让用户看状态,
            再用 `python scripts/xunji_bridge.py key set <KEY>` 设置。
            KEY 申请:训记 App → 我的 → 设置 → 第三方接入。

  Step 1 · 批量落地(按天循环,顺序执行)
    默认从今天起 3 天(--start-offset 0, --days 3;用户可改)。
    对每天调「落地健身计划」完整流程(补计划+记心愿+训记推送 3 步,不能跳)。
    每天完成后汇报:
      「第 N/3 天 ✅ 补计划 4 条 / 心愿 4 条 / 训记 4 条」

    ⚠ 训记推送只看 push-plan 报的 ok=true 不够:
      响应里 res.trains 经常是空数组(2026-07-20 实测,训记 v2 API 响应缺陷)。
      已修:push.py 自动加 verified 字段;verified=False 时
      必须 `fetch --full --date X` 二次确认才能算成功。

  Step 2 · 训记回写(默认 --days 1,今天打勾的就能回写)
    3 天 push 完后调:`xunji_bridge backfill --days 1`。
    backfill 范围是**回看 N 天**(end_date=today),和 push-plan 方向相反。
    用户当天练完打勾后,再调一次 backfill --days 1 就能看到 exercise_log 新增。
    完成后汇报:「训记回写 ✅ 新增 X 条,更新 Y 条」

  末尾输出模板:
    第 1/3 天 ✅ 补计划 4 条 / 心愿 4 条 / 训记 4 条
    第 2/3 天 ✅ 补计划 4 条 / 心愿 4 条 / 训记 4 条
    第 3/3 天 ✅ 补计划 4 条 / 心愿 4 条 / 训记 4 条
    训记回写 ✅ 新增 0 条,更新 0 条(用户还没打勾)
  ```

- **回写训记**:`python scripts/xunji_bridge.py backfill [--date <DATE>] [--days <N>]` → 拉训记数据回写 exercise_log(幂等)。
  ```
  行为:
    调训记 fetch(include_full_data=true)
    → xunji_adapter.py 解析 → upsert_exercise_log
    → 幂等键:xunji_localid + set_index(同组不会重复写)
    → 自动取最新体重推算热量

  参数:
    --date <DATE>  单日(默认今天)
    --days N           范围 [date-N+1, date](默认 1)

  前置:KEY 检查同「落地健身计划」Step 4(XUNJI_TRAINS_KEY)

  使用场景:
    - 「卡路里同步」Step 2 自动调(--days 1,只回写今天打勾的;
      如果用户在 W2 周末补练一次,再手动 --days 3 把周末 3 天补回来)
    - 晚上 6 点已同步过、8 点又有新训练 → 「回写训记」单独跑(--days 1)
    - 周末补练漏写 → 「回写训记 --date <DATE> --days <N>」(回看 N 天)

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

- **训记-覆盖X日的训练计划**:用卡路里 plan 覆盖训记某天**已有**训练(localid 已有 + start/end=0,**等同新建语义**)。
  ```
  适用场景:
    - 训记那天的训练已经在(可能手建,可能 push-plan 建过),想用卡路里 plan 同步内容
    - 注意:跟「落地健身计划」的区别 -- 落地走 push-plan(新建 localid=0),
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
      python scripts/xunji_bridge.py overlay-plan --date <DATE>
    可选参数:
      --dry-run       预览将要推什么(不实推)
      --missing fail  卡路里有但训记没的 title → 报错退出(默认)
      --missing skip  卡路里有但训记没的 title → 跳过,只推匹配的

  Step 3 · 内部做了什么
    1 fetch 训记 list(只拿 title → localid 映射,**不取 start/end**)
    2 拉卡路里 plan(get_day_plan)
    3 按 title 对账
    4 缺 title → 按 --missing 策略处理
    5 训记有但卡路里没 → 报告保留(不删)
    6 构造 res[]:localid 已有,start=0, end=0
    7 调底层 upsert.upsert_trains(单次,训记 API 单次最多 4 条训练)
    8 输出对账结果 + 训记响应

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

### 📊 分析:查热量趋势 / 查营养配比 / 查热量缺口 / 查食物排行 / 查运动分布 / 查运动贡献

- **查热量趋势**:`diet_analysis(start, end, 'calorie_trend')` - 工作日 vs 周末 / 合规率
- **查营养配比**:`diet_analysis(start, end, 'macro_ratio')` - 蛋白/碳水/脂肪占比
- **查热量缺口**:`diet_analysis(start, end, 'deficit_analysis')` - 饮食 vs 运动贡献
- **查食物排行**:`diet_food_ranking(start, end, category)` - category 可选:high_calorie / low_calorie / frequent / high_carb / high_protein
- **查运动分布**:`exercise_analysis(start, end, 'type_breakdown')` - 消耗/频次/时长占比
- **查运动贡献**:`exercise_analysis(start, end, 'deficit_contribution')` - 运动对缺口贡献

### 📋 综合:设营养目标 / 查营养目标 / 查健康报告 / 查卡路里数据

- **设营养目标**:`calorie_tracker.py goal <热量> [蛋白] [碳水] [脂肪]`
- **查营养目标**:读取 `daily_goal` 表返回当前目标
- **查健康报告**:`dashboard(start, end)` - 四维度综合仪表盘
- **查卡路里数据**:Lint 5 项检查(见下方)

---

## 示例对话

**用户**:记吃了 米饭 200克
**AI**:米饭大概 200克,232卡,4g蛋白,50g碳水,0.5g脂肪 → ✓ 已记录,今日 232/1800卡

**用户**:记体重 70(2026-07-20 改:身高从 user_profile 自动读,先 profile set)
**AI**:✓ 体重已记录 70.0公斤,BMI 22.1(正常范围)

**用户**:查热量 鸡胸肉
**AI**:找到 1 个匹配:鸡胸肉 | 165卡/100g | 蛋白31g | 脂肪3g

**用户**:记运动 骑行 40分钟 300卡
**AI**:✓ 已记录运动:骑行 40分钟 300卡

**用户**:查体重趋势
**AI**:📊 体重趋势(2026-04-28 ~ 2026-05-28)均重 70.2kg | 变化 -1.3kg | 趋势下降 ✓

---

## 联动说明

联动逻辑已集中到技能路由器(`图片路由/SKILL.md`),本技能不再单独维护联动规则。完成主操作后请检查路由器的联动规则表。

---

## Lint 检查(数据健康检查)

**触发词**:`"查卡路里数据"`

### 检查项

1. **数据新鲜度**:今日是否记录体重/饮食/运动
2. **体重目标进度**:调用 `weight_milestone()` 检查差距和预计达成时间
3. **热量趋势预警**:调用 `diet_calorie_trend()` 检查近7天,连续3天超标则预警
4. **热量缺口分析**:调用 `diet_deficit_analysis()` 检查缺口,长期为正需提示
5. **运动连续性**:调用 `exercise_trend()` 检查,连续7天以上未运动则预警

原则:发现问题列出清单,只建议不自动修改。

---

## TypeScript 配置生成

触发场景:表结构变了、表数量变了、数据库路径变了、SkillBoard 报错缺字段。

运行 `python scripts/generate_ts_config.py` 重新生成 `config-calorie.ts`,检查输出确认7张表都在。
