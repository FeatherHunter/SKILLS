---
name: 卡路里
description: >
  饮食热量、饮水、体重、运动、营养追踪与分析技能(11 分类 446 场景)。
  说「卡路里HELP」打开完整能力速查台(一键复制 prompt)。
  触发词:看今日主页、看今日热量预算、记一餐、拍营养表记一餐、看今日饮食、记喝水、补记饮食、复制昨日饮食、改饮食记录、删饮食记录、看本周饮食、查食品、存食品、改食品、下架食品、批量导入食品、看营养结构、看今日营养、看饮食总览、看营养素深度、看高热量榜、看低热量榜、看频繁吃榜、看高碳水榜、看高蛋白榜、饮食复盘（本周）、看全部餐别分布（最近 7 天）、记体重、补录体重、看今日体重、看体重曲线、对比体重：最近 30 天 vs 之前 30 天、体重复盘（本周）、记运动、记力量训练、记有氧运动、补记运动、看今日运动、看运动趋势、运动复盘（本周）、看计划概览、定训练计划、落地训练、同步到训记、定营养目标、定体重目标、定饮水目标、看今日目标进度、记体脂（皮褶钳）、记围度、看体脂趋势、看围度趋势、记身材照、查身材照、生成身材照GIF、对比两张照片、设置档案、改档案、查档案、查健康报告、查热量趋势、查热量缺口、复盘、开启定时复盘、本周复盘、本月复盘
  完整触发词见 SKILL.md §触发词速查表(权威:scripts/_triggers.py)。
metadata: { "openclaw": { "emoji": "🍎", "version": "2.4.19", "requires": { "python": ">=3.10" } } }
---

**🔗 联动提示:** 完成本技能主操作后,检查技能路由器(`图片路由/SKILL.md`)的联动规则,判断是否需要联动其他技能(如用户提到食物花费→询问是否记录支出;用户提到买了新食品→询问是否存入食品库)。详见路由器的联动规则表。

## ⚠️ 强制性规定(最高优先级)

1. **HTML 同步**:本技能的所有优化和变动、脚本的所有变动都必须体现在相应的 HTML 页面上。HTML 是技能功能的可视化镜像,任何功能变更若未同步到 HTML 视为未完成。
2. **优先级**:本强制性规定优先级最高,高于下方所有操作规范和功能说明。
3. **变更确认**:对该技能的所有文件、脚本的任何一行修改都需要明确得到用户的 1 次确认,未经确认不得执行写入操作。
4. ⭐ **HTML-First 铁则(V1.3 原则 11)**:唤醒词命中 SKILL 后,**只要 §已实现模板表 列出对应 HTML 模板,AI 必须 invoke HTML 工作流(渲染 → 打开)**。**严禁文字答**。trigger 无对应 HTML 模板时可文字答(但默认推荐 §输出位置 生成 HTML)。违反 = 协议 fail mode,改 SKILL.md 不改正,循环 ≤ 3 次。详见 §AI 行为:HTML-First 表。
   - ⭐ **渲染失败处理契约(v2.4.19 增 · #242)**:render 脚本执行**必须** invoke,不得手写 HTML 兜底。判定成功 = 退出码 0 且产物 HTML 文件存在(不是看 stdout 有无表情符号——GBK 控制台下 emoji 输出可能被替换但渲染已成功,脚本已内置 `_io_guard` 防崩)。渲染失败(退出码非 0 / 产物缺失)→ 向用户输出**错误回执**(说明失败原因 + 建议命令),**严禁**手写 HTML 代替渲染产物。违反 = 协议 fail mode。
5. ⭐ **Wizard Verify 决策铁则(v2.4.3 增,用户实测反馈)**:对 `记围度` / `记体脂` 等**配置型 wizard** 的 trigger,AI **必须**根据用户输入决定走哪条流程:

   | 场景 | 触发 | AI 行为 | 命令模板 |
   |---|---|---|---|
   | **场景 1**(主动填) | 用户说 "记围度" / "记体脂" 但**没给数据** | render 脚本**不传预填 args**(空 wizard)→ 用户手动填 → 复制 prompt → AI 调 CLI | `python scripts/render_body_measurements_wizard.py` |
   | **场景 2**(预填 verify) ⭐ | 用户说 "记围度 胸 95 腰 80 臀 100..." **给数据** | render 脚本**传预填 args**(wizard 已填好)→ 用户打开 verify → 复制 prompt → AI 调 CLI | `python scripts/render_body_measurements_wizard.py --date 2026-07-26 --chest-cm 95 --waist-cm 80 ...` |
   | 场景 3(信任) | 用户**明确说** "直接录" / "我信你" | 跳过 wizard,直接调 `body_measurements.py add` 写库 + 返回 crud_receipt.html 回执 | `python scripts/body_measurements.py add ...` |

   **禁止**:**不**判断用户场景就**直接调 CLI** 写库(跳过 verify)— 即使数据看起来对。这是 v2.4.2 → v2.4.3 修复的根因:用户实测反馈 "我的维度 XXXXXXX" 后 AI 应走场景 2(预填 verify)而不是直接 CLI。违反 = 协议 fail mode。

6. ⭐ **写入后回执契约(v2.4.14 增 · V1.0 §02 第②特性)**:**所有写库类 CLI 子命令必须按固定契约返 stdout**(满足 V1.0 §02 第②特性"写入后回执 = ID + 时间戳 + 影响行数"):

   | 子命令类 | 调用 | 必须 stdout 包含 |
   |---|---|---|
   | **写库类**(`weight` / `add` / `delete` / `update-meal` 等) | `calorie_tracker.py weight 70 --note '...'` | `id=<N>` + `日期 <YYYY-MM-DD> <HH:MM:SS>` + `影响 N 行` + 写入字段摘要 |
   | **HTML 模板类触发**(`查今天吃` / `扫禁忌` 等 §04 决策矩阵 ✅ 的) | `calorie_tracker.py list` | `⚠️ ACTION=SEND_TO_USER \| HTML=<绝对路径>`(V1.3 §HTML 交付协议) |
   | **v1.0 场景类单条记录**(`记体重` / `记运动` / `记一餐` 等,v1.0 场景设计 446 已定稿) | `calorie_tracker.py weight`(底层 CLI) | 场景化 HTML 回执:按场景 data_source 渲染(如 `render_weight_receipt.py --live` / `render_exercise_receipt.py --live-add` / `render_crud_receipt.py --live-diet-add`);AI 不得退回纯文字回执(2026-08-03 修 · ticket #43 场景 1 终审)

   **硬约束**(违反触发协议 fail mode,V1.0 §04 第④特性):
   - **单条 CRUD 不加 HTML(旧契约)** — 总纲 §04 决策矩阵 ❌ 不做,AI 自作主张接通 render = 违反 §⚠️ 强制性规定 第 4 条(HTML-First 反模式)。⚠️ **v1.0 场景化例外**(2026-08-03 · ticket #43 终审):`记体重` / `记运动` / `记一餐` 等已入 446 场景清单,HTML 回执以 `.scratch/scene-index-recovered.md` + `docs/scene-prompts/` 为准,不再受本条约束
   - **模板类必加 HTML** — 总纲 §04 决策矩阵 ✅ 必做,AI 跳过渲染 = 违反 §⚠️ 强制性规定 第 4 条
   - **写库回执必有 ID** — V1.0 §02 第②特性"ID + 时间戳 + 影响行数"是 Verifiable 的硬规则

   验证脚本:`scripts/check_write_contract.py`(待加 V2.4.15) — 扫所有子命令,确保每个写库类 CLI 都 print id+timestamp+rows_affected。

7. ⭐ **AI 验证协议(v2.5 增,Issue 6 反馈)**:AI 在 SKILL 内声称"用户没 X / 用户从未 Y"前,**必须**先对该 X/Y 对应的 DB 表执行 SELECT 验证。3 个 fail mode 红线示例:
   - (a) **写脏数据后断言原值** — 如 `daily_goal.weight_goal` 被某次 `weight-goal --help` 误写为字符串 `'--help'`,AI 应先 SELECT 看到字符串就识别为损坏数据,而不是回写字符串或假装"原值是 None"。
   - (b) **空值误判'从未设过'** — `NULL` / `0` / 空字符串 ≠ "从未设过";可能是过期数据 / 损坏数据 / 字段尚未初始化。
   - (c) **类型误判** — 当 DB 返回非预期类型(如字符串而非数字)时,AI 不得假设其为 0 或"未设"。
- 违反 = 协议 fail mode,等同 HTML-First 反模式(第 4 条)。详见 ADR-0007。

---

## ⚠️ 操作规范(强制)

本技能所有数据操作必须通过 CLI,禁止直连数据库。

## 核心原则

- **数据操作只走 CLI**:所有增删改查通过 `scripts/` 下的 Python 脚本执行,禁止直接操作 SQLite
- **睡眠归属就寝日**:睡眠记录归属于就寝那天,不是起床日
- **Path C 参考数据不存库**:外部搜索到的营养数据仅用于本次记录,不写入 nutrition_products
- **起床确认不提卡路里**:唤醒词场景的确认语中不出现"卡路里"三字,直接问"要不要记录"
- **只建议不自动修改**:Lint 检查发现问题后列出清单,让用户决定
- ⭐ **HTML-First(V1.3 原则 11)**:AI 收到 trigger 词后,先查 §已实现模板表 是否有对应 HTML。有则**强制 invoke HTML**(渲染 → 打开),无则可文字答。详见 §⚠️ 强制性规定 第 4 条 + §已实现模板表 强制 trigger 列。
- ⭐ **不存 deprecation 库存(v2.5.5 增,ADR-0004 supersede)**:卡路里所有破坏性变更**立即生效**,不写 `--legacy-positional` 之类的逃生口。老脚本必须随 schema 升级而升级。详见 ADR-0004 附录"CLI 演进史"。
- ⭐ **AI 验证协议(v2.5 增,ADR-0007)**:AI 声称"用户没 X"前必先 SELECT 验证。空值 ≠ "从未设过",写脏 ≠ "原值是 None",类型错 ≠ "视为 0"。详见 §⚠️ 强制性规定 第 7 条。

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

## 🎨 视觉增强（HTML 模板 + 数据注入）

> 详见《预置HTML+注入数据指导手册》第一性原理。"模板稳定、数据流动、样式预置、内容注入"。

### 📌 输出位置(2026-07-24 起 · 手册 §4.1 跨 Skill 通用 · v2.4.8 中文化)

所有 `render_*.py` 默认输出到 **`calorie_html/`** 子目录(与 `calorie_data.db` 同级,跟随 `$SKILLS_DB_PATH` 环境变量,fallback `D:/.db/`)。

<!-- 遵守 V1.0 原则 12.B · HELP HTML 输出约定(v2.4.18b 起,卡路里_HELP 加 `<skill 中文名>` 前缀对齐原则 12.1;原则 12.A 数据/过程 80+ render 走 calorie_html/<command_cn>_<datetime>.html 默认合规) -->

**v2.4.8 起 · `<command>` 字段全量中文化**(静态部分 + 动态拼接部分):

| 旧规则(已下线) | 新规则(手册 §4.1 · 中文化) |
|---|---|
| `/tmp/<feature>_<range>.html` | `<DATA_DIR>/calorie_html/<中文command>_<YYYYMMDD>_<HHMMSS>[_<N>].html` |
| `calorie_html/home_dashboard_*.html` | `calorie_html/主页仪表盘_*.html` |
| `calorie_html/weight_history_live.html` (无时间戳) | `calorie_html/体重_历史_*.html` (mode → 中文) |
| `calorie_html/exercise_summary_*.html` | `calorie_html/运动_汇总_*.html` (mode → 中文) |
| `calorie_html/food_ranking_high_calorie_*.html` | `calorie_html/食物排行_高热量_*.html` (category → 中文) |
| 覆盖式写入 `卡路里/健身计划.html` | 同秒冲突自动追加 `_2` / `_3` 后缀 |
| 无冲突保护 | `--output <path>` 仍可显式覆盖到任意路径 |

**动态映射表**(scripts/_cmd_maps.py · 维护在 4 张字典):
- `WEIGHT_MODE_MAP` — 查体重历史/趋势/对比/波动
- `EXERCISE_SUMMARY_MODE_MAP` — 查运动记录/汇总/类型/趋势
- `EXERCISE_DISTRIBUTION_MODE_MAP` — 查运动分布/贡献
- `FOOD_RANKING_CATEGORY_MAP` — 查食物排行 5 榜单
- `CONTRAINDICATION_PART_MAP` — 扫禁忌 · 部位

完整规范 + 实际示例见 [`references/html_templates.md`](references/html_templates.md) §"输出目录与命名规范"。


### 已实现模板（2026-07-23）

| 模板 | 唤醒词 | 数据源 | 渲染器 |
|---|---|---|---|
| `templates/contraindication_report.html` | 扫禁忌 | `scan_contraindications.py --format json` | `scripts/render_contraindication.py` |
| `templates/review_template.html` | 复盘（含今日/本周/本月/本年/日期范围） | `review_cli.py gen` enriched JSON | `scripts/render_review.py --range / --type` |
| `templates/workout_plan_view.html` | 看本周计划 / 看今天练什么 / 看计划概览 / 看计划 vs 实际 / 看计划完成率 / 看未完成训练 / 看动作完成率(多模式) | DB 直接 query workout_plans + exercise_log | `python scripts/render_workout_plan.py --mode {...}` |
| `templates/health_dashboard.html` | 查健康报告 | `analysis.dashboard(as_dict=True)` 4 维 | `python scripts/render_health_dashboard.py [--range / --days]` |
| `templates/food_ranking.html` | 5 个食物排行（1 模板 5 榜单） | `analysis.diet_food_ranking(as_dict=True)` × 5 | `python scripts/render_food_ranking.py --category / --all` |
| `templates/exercise_review.html` | 计划复盘（本周/本月/全部） | `exercise_review.py --format json` | `python scripts/render_exercise_review_html.py [--days]` |

### 模板设计原则（与《手册》第 7 节对齐）

- **占位符唯一**：模板含 `<!--INJECT-DATA-->` 恰好 1 次（注入器会校验）
- **首屏**：状态徽章 + 关键 KPI 卡片（4-6 个）
- **主体**：按维度分组（折叠 `details/summary` 让长内容可折叠）
- **尾部**：复制回 AI 按钮（让用户回填数据）
- **空态 / 错误态**：明确显示（不要白屏）

### 数据契约

```json
{
  "status": "ok" | "warn" | "fail",
  "data": { ... },
  "message": "..."
}
```

所有 `status` 必须严格用 `"ok" | "warn" | "fail"`（"fail" 对应 error 级禁忌；与《优秀 Skill 指导手册》第④层接口层规范一致）。

### 完整 HTML 模板清单(V1.3 原则 11 · 2026-07-25 扩)

> 48 行模板清单:每行可对应 1+ 个 trigger 词(强制走 HTML);无 trigger 的为配置辅助页/内部工具(如 body_photo_log_wizard / gif_planner 规划器)。

| 模板 | 强制 trigger(走 HTML) | 数据源 | 渲染器 |
|---|---|---|---|
| `templates/nutrition_label_wizard.html` | 拍营养表记一餐 / 拍营养表补记一餐 | `mmx vision describe` → `add` | `scripts/render_nutrition_label.py` |
| `templates/today_diet.html` / `today_meals.html` | 看今日饮食 | `diet.list_meals()` | `scripts/render_today_meals.py` |
| `templates/today_water.html` | 看今日喝水 | `food_log` 中 `food_name='💧水'` 的 grams 聚合 + `daily_goal.water_goal` | `scripts/render_today_water.py [--date YYYY-MM-DD] [--mock <json>]` |
| `templates/calorie_trend.html` | 查热量趋势 | `analysis.diet_calorie_trend(as_dict=True)` | `scripts/render_calorie_trend.py` |
| `templates/nutrition_ratio.html` | 查营养结构 | `analysis.diet_nutrition_ratio(as_dict=True)` | `scripts/render_nutrition_ratio.py` |
| `templates/calorie_deficit.html` | 查热量缺口 | `analysis.diet_deficit_analysis(as_dict=True)` | `scripts/render_calorie_deficit.py` |
| `templates/food_ranking.html` | 看高热量榜 / 看低热量榜 / 看频繁吃榜 / 看高碳水榜 / 看高蛋白榜 / 看高热量榜（最近 30 天）/ 看高热量榜（本月）/ 看高热量榜（自定义）/ 看低热量榜（最近 30 天）/ 看低热量榜（本月）/ 看低热量榜（自定义）/ 看频繁吃榜（最近 30 天）/ 看频繁吃榜（本月）/ 看频繁吃榜（自定义）/ 看高碳水榜（最近 30 天）/ 看高碳水榜（本月）/ 看高碳水榜（自定义）/ 看高蛋白榜（最近 30 天）/ 看高蛋白榜（本月）/ 看高蛋白榜（自定义） | `analysis.diet_food_ranking(as_dict=True)` × 5 | `scripts/render_food_ranking.py --category / --all` |
| `templates/food_search.html` | 查食品 | `nutrition_products` LIKE 搜索 | `scripts/render_food_search.py --query "<term>"` |
| `templates/food_library.html` | 查食品（按分类） | `nutrition_products` 列表 + 客户端搜索/分页 | `scripts/render_food_library.py [--limit 200 | --all]` |
| `templates/weight_history.html` | 看本周体重、看上周体重、看本月体重、看上月体重、看最近 7 天体重、看最近 90 天体重、看某段时间体重、看体重曲线、看体重曲线（带目标）、看体重曲线（带里程碑）、看体重曲线（带异常点）、看最近 90 天体重曲线、看最近 180 天体重曲线、看最近 365 天体重曲线、看某段时间体重曲线、看「有备注」的体重记录 | `analysis.weight_*` 系列 | `scripts/render_weight_history.py [--mode]` |
| `templates/weight_compare.html` | 对比体重：最近 30 天 vs 之前 30 天、对比体重：自定义两段时间、对比体重：本周 vs 上周、对比体重：本月 vs 上月、对比体重：近 N 天 vs 上一个 N 天、对比体重：今天 vs 一年前今天、对比体重：今天 vs 半年前今天、对比体重：今天 vs 三月前今天、对比体重：当前 vs 目标体重、对比体重：当前 vs 平台期首日、对比体重：当前 vs 历史最低、对比体重：当前 vs 历史最高、对比体重：减重 5kg 那天 vs 今天、对比体重：减重 10kg 那天 vs 今天、对比体重：当前 vs 入夏最低、对比体重：当前 vs 入冬最低、对比体重：运动多 vs 运动少的两个月、对比体重：工作日 vs 周末 | `analysis.weight_compare` | `scripts/render_weight_compare.py --scenario` |
| `templates/weight_dashboard.html` | 看体重总览、看今日体重 | `weight_log + daily_goal.weight_goal` | `scripts/render_weight_dashboard.py --view` |
| `templates/weight_review.html` | 体重复盘（本周）、体重复盘（本月）、体重复盘（最近 90 天）、体重复盘（今年）、体重复盘（自定义时间）、看里程碑回溯 | `weight_log` | `scripts/render_weight_review.py --type` |
| `templates/weight_batch_receipt.html` | 批量补录体重 | `weight_log` | `scripts/render_weight_receipt.py --live-batch` |
| `templates/weight_log_receipt.html` | 记体重、记体重（含备注）、补录体重 | `weight.log_weight()` + 趋势图 | `scripts/render_weight_receipt.py --live` |
| `templates/exercise_summary.html` | 看今日运动 / 看昨日运动 / 看本周运动 / 看上周运动 / 看本月运动 / 看上月运动 / 看最近 7 天运动 / 看最近 30 天运动 / 看某段时间运动 / 看最近 60 天运动 / 看最近 180 天运动 / 看最近 365 天运动 / 看运动记录（有备注）/ 看运动记录（按力量筛选）/ 看运动记录（按有氧筛选） | `exercise_log + daily_goal.exercise_goal` | `scripts/render_exercise_summary.py` |
| `templates/exercise_goal_view.html` | 看今日运动（vs 目标）/ 看本周运动（vs 目标） | `exercise_log + daily_goal.exercise_goal` | `scripts/render_exercise_goal_view.py --period` |
| `templates/exercise_strength.html` | 看力量训练总览 | `exercise_log` | `scripts/render_exercise_strength.py` |
| `templates/exercise_cardio.html` | 看有氧训练总览 | `exercise_log` | `scripts/render_exercise_cardio.py` |
| `templates/exercise_trend.html` | 看运动趋势 | `exercise_log` | `scripts/render_exercise_trend.py` |
| `templates/exercise_recap.html` | 运动复盘（本周）/ 运动复盘（本月）/ 运动复盘（最近 90 天）/ 运动复盘（今年）/ 运动复盘（自定义时间） | `exercise_log` | `scripts/render_exercise_recap.py --period` |
| `templates/exercise_distribution.html` | 查运动分布 / 查运动贡献 | `analysis.exercise_*` | `scripts/render_exercise_distribution.py` |
| `templates/exercise_review.html` | 计划复盘（本周） / 计划复盘（本月） / 计划复盘（全部） | `exercise_review.py --format json` | `scripts/render_exercise_review_html.py` |
| `templates/workout_plan_view.html` | 看本周计划 / 看下周计划 / 看上周计划 / 看指定周计划 / 看今天练什么 / 看计划概览 / 看计划 vs 实际 / 看计划完成率 / 看未完成训练 / 看动作完成率(多模式 · 2026-08-02 ticket #6) | DB 直接 query workout_plans + exercise_log | `python scripts/render_workout_plan.py --mode {full,week,today,overview,vs,completion,missed,movement}` |
| `templates/plan_builder_wizard.html` | 定训练计划 | DB query + 计划生成 | `scripts/render_plan_builder.py` |
| `templates/health_dashboard.html` | 查健康报告 | `analysis.dashboard(as_dict=True)` 4 维 | `scripts/render_health_dashboard.py [--range / --days]` |
| `templates/lint_health.html` | 查卡路里数据 | `lint_health()` | `scripts/render_lint_health.py` |
| `templates/goal_config_nutrition.html` | 定营养目标 / 改营养目标 | `daily_goal` + `food_log` | `scripts/render_goal_config.py` |
| `templates/goal_config_water.html` | 定饮水目标 / 改饮水目标 | `daily_goal` + `food_log` | `scripts/render_goal_config.py` |
| `templates/goal_recommend.html` | 定营养目标(自动算) / 定饮水目标(自动算) / 一键定全套目标 | `recommend_nutrition_goal` / `recommend_water_goal` | `scripts/render_goal_recommend.py` |
| `templates/goal_weight.html` | 定体重目标 / 定体重目标(自动算截止) / 定体重目标(含起始日) / 改体重目标 | `weight_goal` | `scripts/render_goal_weight.py` |
| `templates/goal_weight_result.html` | 定体重目标 / 定体重目标(自动算截止) / 定体重目标(含起始日) / 改体重目标(写库后结果回执 · #79) | `daily_goal(weight_goal/goal_deadline/start_weight/start_date)` + `weight_log` | `scripts/render_goal_weight.py --live` |
| `templates/goal_status.html` | 暂停所有目标 / 重启所有目标 | `goal_manager` | `scripts/render_goal_status.py` |
| `templates/goal_progress.html` | 看今日目标 / 看本周目标 / 看营养目标进度 / 看饮水目标进度 / 看目标对比实际 / 看目标完成度 / 看即将到期的目标 / 看目标完成率(按周) / 看目标完成率(按月) / 看目标历史完成 / 看目标预测达成 | `daily_goal` + `food_log` 聚合 + `weight_goal` | `scripts/render_goal_progress.py` |
| `templates/profile_setup.html` | (设置档案 · 配置辅助页) | `profile.get/set` | `scripts/render_profile_setup.py [--live]` |
| `templates/cron_setup.html` | 开启定时复盘 / 关闭定时复盘 | `mavis cron list/create/delete` (AI 自动查状态) | `scripts/render_cron_setup.py` |
| `templates/crud_view.html` | 查档案 / 查定时复盘 | `profile.get` / `mavis cron list` | `scripts/render_crud_view.py` |
| `templates/crud_receipt.html` | 记一餐 / 记一餐（含备注） / 补记饮食 / 批量补记饮食 / 记喝水 / 复制昨日饮食 / 改饮食记录 / 改某日饮食 / 删饮食记录 / 删一餐 / 删某日饮食 / 批量删饮食 / 存食品 / 改食品 / 下架食品 / 改体重记录 / 改某日体重 / 删体重记录 / 删某日体重 / 批量删体重 / 改运动记录 / 设置档案 / 设活动量 / 改档案 / 删体脂 / 删围度 | 各 CRUD 函数返回 diff | `scripts/render_crud_receipt.py [--live-diet-add/--live-diet-batch/--live-diet-batch-meal/--live-diet-copy/--live-diet-update/--live-diet-update-date/--live-diet-delete/--live-diet-delete-meal/--live-diet-delete-date/--live-diet-delete-range/--live-water-add/--live-product-add/--live-product-update/--live-product-deprecate/--live-profile-set/--live-profile-activity/--live-profile-update]` |

| `templates/diet_review.html` | 饮食复盘（本周）/ 饮食复盘（本月）/ 饮食复盘（最近 90 天）/ 饮食复盘（今年）/ 饮食复盘（自定义时间） | `food_log` 聚合(总热量/日均/总蛋白/趋势/高频 TOP5) | `scripts/render_diet_review.py --type {week,month,quarter,year,range}` |
| `templates/diet_overview.html` | 看饮食总览 | `food_log` 周期累计(本周/本月 + 趋势,不含今日) | `scripts/render_diet_overview.py` |
| `templates/nutrition_detail.html` | 看营养素深度 | `food_log × nutrition_products`(纤维/钠/糖 vs 推荐) | `scripts/render_nutrition_detail.py [--days N]` |
| `templates/meal_distribution.html` | 看早餐（最近 7 天）/ 看午餐（最近 7 天）/ 看晚餐（最近 7 天）/ 看加餐（最近 7 天）/ 看全部餐别分布（最近 7 天） | `food_log` 按餐别时间窗聚合 | `scripts/render_meal_distribution.py --meal {breakfast,lunch,dinner,snack,all}` |
| `templates/source_stats.html` | 看食品来源统计 | `nutrition_products` GROUP BY source | `scripts/render_source_stats.py` |
| `templates/dedupe_report.html` | 看食品库（去重） | `nutrition_products` 重复组 | `scripts/render_dedupe_report.py` |
| `templates/body_photo_log_wizard.html` | (记身材照 · 配置辅助页,飞书交互用) | 无(纯配置) | `scripts/render_body_photo_log_wizard.py` |
| `templates/body_photo_viewer.html` | 查身材照(单图子路径) | `body_photos` 单行 | `scripts/render_body_photo_viewer.py --id N` |
| `templates/body_photo_gif_planner.html` | 生成身材照GIF（规划器 · 框选裁剪 · 内部工具） | `body_photos` 多行 + base64 | `scripts/render_body_photo_gif_planner.py` |
| `templates/body_photo_receipt.html` | 记身材照 / 删身材照 / 改照片标签 / 加照片标签 / 删照片标签 | `body_photos` 写库回执(缩略图/diff) | `scripts/render_body_photo_receipt.py --live-*` |
| `templates/body_photo_gallery.html` | 查身材照(浏览网格) | `body_photos` 列表 + 计数 | `scripts/render_body_photo_gallery.py` |
| `templates/body_photo_compare.html` | 对比两张照片 | `body_photos` 两行并排 | `scripts/render_body_photo_compare.py` |
| `templates/body_photo_gif_result.html` | 生成身材照GIF(结果) | GIF 文件 + 合成信息 | `scripts/render_body_photo_gif_result.py` |
| `templates/weight_log_receipt.html` | 记体重 | `weight.log_weight()` + 趋势图 | `scripts/render_weight_receipt.py` |
| `templates/body_photo_viewer.html` | (查身材照 · 子页)| `body_photo_tracker.get_photo(id)` | `scripts/render_body_photo_viewer.py --id N` |
| `templates/body_photo_log_wizard.html` | 记身材照 | 纯配置型(无需 DB,用户填 → 生成 prompt) | `scripts/render_body_photo_log_wizard.py` |
| `templates/body_photo_gif_planner.html` | 查身材照 / 生成身材照GIF(报告型 + 过程型 · v2.3.1 兼任 gallery + cropper.js 框选)
| `templates/body_composition_wizard.html` | 记体脂（皮褶钳） / 记体脂（外部测量） / 补记体脂 / 看体脂 / 看体脂趋势 / 对比体脂(配置型 · 单页 + `<details>` 分组 · 飞书 webview 兼容 v2.3.5 教训)| `validators.validate_composition_input` | `scripts/render_body_composition_wizard.py` |
| `templates/body_composition_view.html` | 看体脂 / 看体脂趋势 / 对比体脂 | `body_composition` 实读 DB | `scripts/render_body_composition_view.py` |
| `templates/body_measurements_view.html` | 看围度 / 看围度趋势 / 对比围度 | `body_measurements` 实读 DB | `scripts/render_body_measurements_view.py` |
| `templates/body_measurements_wizard.html` | 记围度 / 补记围度 / 看围度 / 看围度趋势 / 对比围度(同上 · 13 围度 3 分组)| `validators.validate_measurement_input` | `scripts/render_body_measurements_wizard.py` |
| `templates/body_photo_gif_planner.html` | 查身材照 / 生成身材照GIF(报告型 + 过程型 · v2.3.5 cropper.js 移除 + 4 数字裁剪输入 · 飞书 webview 兼容)| `body_photo_tracker.get_photos_by_ids([id1,id2,...])` + `validate_files` 自动跳过丢失 | `scripts/render_body_photo_gif_planner.py --tag 正面 (推荐)\|--ids id1,id2,... [--no-validate-files]` |
| `templates/batch_import_preview.html` | 批量导入食品 / 校验批量导入 | `batch_import.validate` JSONL | `scripts/render_batch_import.py` |
| `templates/review_template.html` | 复盘 / 今日复盘 / 本周复盘 / 本月复盘 / 复盘日期范围 | `review_cli.gen` enriched JSON | `scripts/render_review.py --range / --type` |
| `templates/contraindication_report.html` | 扫禁忌 | `scan_contraindications.py --format json` | `scripts/render_contraindication.py` |
| `templates/process_progress.html` | 落地训练 / 落地到本周末 / 落地到本月底(4 步流程进度 · 2026-08-02 ticket #6) | 流程结构化 JSON(tests/fixtures/mock/mock_process_progress.json 演示) | `scripts/render_process_progress.py --input <json>` |
| `templates/home_dashboard.html` | 看今日主页 / 看今日饮食概览 / 看今日运动概览 / 看今日体重概览 / 看今日目标进度 / 看本周主页 / 看本月主页 / 看连续记录天数 / 看今日热量预算(主页 9 场景 · 2026-08-02 ticket #2) | `analysis.dashboard(as_dict=True)` + 今日检测 + section/period 聚合 | `scripts/render_home.py [--section diet\|exercise\|weight\|goals\|streak\|budget] [--period week\|month] --chain <思考链>` |
| `templates/help_center.html` | 卡路里HELP(唤醒词速查台·80 词·109 prompt·3 层折叠 + 搜索 + 一键复制) | `_triggers.py` 静态表 | `scripts/render_help_center.py` |

**强制规则**:表中"强制 trigger"列出的所有 trigger 词命中后,**AI 必须** invoke 对应 HTML(渲染 → 打开),**严禁文字答**。

---

### 🔍 trigger 一致性检查脚本(V1.3 · 2026-07-25 加)

`scripts/check_trigger_consistency.py` — 机械化验证 SKILL.md 与 render 脚本的 trigger 一致性,**V1.3 协议硬要求**:

3 边单向对照:
1. §完整 HTML 模板清单 的"强制 trigger"列  ⊆  frontmatter 触发词
2. `scripts/render_*.py` docstring 声明的 trigger  ⊆  frontmatter 触发词

```bash
python scripts/check_trigger_consistency.py
# exit 0 = 一致, exit 1 = 有 drift
```

**当前状态**:
- frontmatter trigger: **73**
- HTML 模板表 trigger: **63**(= 73 - 10 个可文字答)
- render docstring trigger: **64**
- ✅ **3 边一致**(v2.2.2 验证)

**用法**:
- commit 前**手动跑一次**,确保 drift 已修
- 可挂 pre-commit hook(见 §⚠️ 强制性规定 第 5 条建议)
- 维护规则:**新增/删 trigger 时同步 3 处**(frontmatter + §触发词速查表 + render docstring)

**发现过的 drift(已修)**:
- v2.2.2 扫出:4 个 trigger 在 §触发词速查表 / HTML 表但 frontmatter 缺(扫禁忌 / 批量导入 / 改吃的 / 校验批量 / 查食品库去重)
- v2.2.2 扫出:3 个 render docstring 注释错误(查营养配比旧名 / 训记-覆盖X日 简写 / 存食品 缺声明 / 查健身计划 缺声明)

---

## 📦 安装与配置

### 依赖

- Python >= 3.10(v2.4.19 起 · 原因:scripts 使用 PEP 604 联合类型 `X | Y` 与内置泛型 `list[...]`,3.9 及以下 import 即崩)
- 标准库:sqlite3、argparse、datetime、json
- 第三方依赖(可选):`beautifulsoup4` — 仅 `scripts/check_html_responsive.py`(HTML 响应式 lint,seam 6)使用。`pip install beautifulsoup4` 即可。其它脚本不依赖。

### 配置项

| 环境变量 | 说明 |
|---------|------|
| `SKILLS_DB_PATH` | 数据库文件所在目录(最高优先级;未设置时走下方跨平台 fallback) |
| `SKILLS_DB_PATH_TEST` | (v2.5 增,ADR-0006)测试用临时 DB 目录。`tests/conftest.py` 的 `temp_db` fixture 自动设置;**生产 `calorie_data.db` 永不被测试触碰**。 |

DB 查找顺序(跨平台 · v2.4.19 修):
1. `SKILLS_DB_PATH` 环境变量(所有平台)
2. Windows → `D:/.db`(**用户规定,保持不变**);WSL → `/mnt/d/.db`
3. macOS / Linux(无 /mnt/d)→ `~/.db`(用户主目录,不再因缺 D 盘而崩溃)

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

> 用户说"卡路里 help"(v2.4.10 起注册为正式唤醒词"卡路里HELP")时显示本表 + 一键复制 prompt 给 AI。全部唤醒词为动词+名词结构。

**HTML 强制度(V1.3 原则 11)**:有 HTML 模板的 trigger 强制走 HTML(详见 §完整 HTML 模板清单 + §⚠️ 强制性规定 第 4 条)。

### 📚 速查台(v2.4.10 起)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 卡路里HELP | 打开唤醒词速查台(80 唤醒词 / 109 prompt / 3 层折叠 + 搜索 + 一键复制) | `python scripts/render_help_center.py` |

**CLI 列规则(最严格标准 · 2026-07-13 修)**:
- **原子 trigger**(暴露 CLI): `python scripts/<file>.py <subcommand> [args]`
- **组合 trigger**(跨 skill): `组合:<trigger1> + <trigger2> + ...`(不写 Python 函数)
- **分析类 trigger**(Python API): `AI 路由(Python API)`
- **纯 AI 路由**(无 CLI): `AI 路由(无 CLI)`

**参数占位符**:统一用 `<X>` 尖括号(如 `<DATE>`、`<N>`),不写裸 `X` 或大括号 `{X}`

### 🏠 主页(2026-08-02 · 9 场景 · ticket #2)

> 场景数量与场景名已定稿;prompt 定稿见 `docs/scene-prompts/01-主页.md`(修改须重新用户确认)。
> **交互规则(常驻,AI 执行本分类任一场景必须遵守)**:
> - 全部为结果型(只读),渲染走 `render_home.py`(必须带 `--chain` 思考链)
> - 唤醒词「看今日主页」的 aliases:开卡路里 / 卡路里面板 / 今日卡路里
> - 视图 = 6 张 KPI 卡(饮食/运动/体重/目标/进度/连续)+ 最近 7 天趋势小图 + 一句话总结(移动端 2x3 网格)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 看今日主页 | 今日 dashboard(6 KPI 卡 + 趋势 + 一句话) | `python scripts/render_home.py --chain <思考链>` |
| 看今日饮食概览 | 饮食 widget(累计热量/蛋白 vs 目标) | `python scripts/render_home.py --section diet --chain <思考链>` |
| 看今日运动概览 | 运动 widget(累计消耗/时长 vs 目标) | `python scripts/render_home.py --section exercise --chain <思考链>` |
| 看今日体重概览 | 体重 widget(最新/距目标/Δ7天) | `python scripts/render_home.py --section weight --chain <思考链>` |
| 看今日目标进度 | 4 项目标完成度(热量/蛋白/饮水/运动) | `python scripts/render_home.py --section goals --chain <思考链>` |
| 看本周主页 | 本周 dashboard(累计 + 体重趋势) | `python scripts/render_home.py --period week --chain <思考链>` |
| 看本月主页 | 本月 dashboard(累计 + 趋势) | `python scripts/render_home.py --period month --chain <思考链>` |
| 看连续记录天数 | streak(当前连续 + 历史最长) | `python scripts/render_home.py --section streak --chain <思考链>` |
| 看今日热量预算 | TDEE + 运动 − 已摄入 = 剩余可吃 | `python scripts/render_home.py --section budget --chain <思考链>` |

### 🍚 饮食(2026-08-02 新增 · 68 场景 · ticket #3)

> 场景数量与场景名已定稿;prompt 定稿见 `docs/scene-prompts/02-饮食.md`(修改须重新用户确认)。
> **交互规则(常驻,AI 执行本分类任一场景必须遵守)**:
> - 信息缺失才补问:用户表达清晰直接执行;缺失的克数/营养/日期顶多做几句确认(记/补记类)
> - 改/删类用户没指明是哪条时:先列最近记录让用户选 → 改前/删除前给快照确认 → 操作 → 回执(同 #9 身体细节格式)
> - 写库类走 `render_crud_receipt.py --live-*`(写库 + 回执 HTML 一体,必须带 --chain 思考链)
> - 看类走 HTML 渲染(有模板必走 HTML,§⚠️ 强制性规定 第 4 条)
> - 记喝水:用户说「几杯」按一杯约 250ml 折算;只说杯子大小先问确认
> - 记一餐:先在食品库查食物 → 命中展示每 100g 营养确认 → 未命中补克数/包装营养(标注估算来源)→ 写库(4 步流程落 SKILL.md §记一餐)

#### 记饮食(8)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记一餐 | 记录一餐(查库确认 → 写库 → 回执) | `python scripts/render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --chain <思考链>` |
| 记一餐（含备注） | 记录一餐 + 备注 | 同上 + `[备注]` |
| 补记饮食 | 补录某天饮食(冲突提示) | `python scripts/render_crud_receipt.py --live-diet-add ... --date <日期> --time <时间> --meal <餐别> --chain <思考链>` |
| 批量补记饮食 | 一次录多餐(JSON 数组) | `python scripts/render_crud_receipt.py --live-diet-batch --input <meals.json> --chain <思考链>` |
| 拍营养表记一餐 | 拍照识别营养成分表(wizard 确认) | `mmx vision describe <图片>` → `python scripts/render_nutrition_label.py --ai-json <json>` → 确认后 `python scripts/calorie_tracker.py add` |
| 拍营养表补记一餐 | 拍 + 补录指定日期 | 同上 + `--date <日期>` |
| 记喝水 | 记录饮水(多杯解析) | `python scripts/render_crud_receipt.py --live-water-add <ml> [--date <日期>] --chain <思考链>` |
| 复制昨日饮食 | 昨天/某天 → 今天/某天 | `python scripts/render_crud_receipt.py --live-diet-copy [--from <日期>] [--to <日期>] --chain <思考链>` |

#### 改饮食(6)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 改饮食记录 | 改某条(先列候选 → 快照 → 改) | `python scripts/render_crud_receipt.py --live-diet-update <id> [--food] [--grams] [--calories] [--protein] [--carbs] [--fat] [--date] [--time] [--note] --chain <思考链>` |
| 改某日饮食 | 按日期批量改(命中条数/改前/改后) | `python scripts/render_crud_receipt.py --live-diet-update-date <日期> [--字段 新值 ...] --chain <思考链>` |
| 删饮食记录 | 删某条(快照确认 → 回执) | `python scripts/render_crud_receipt.py --live-diet-delete <id> --chain <思考链>` |
| 删一餐 | 删某天某餐(5+1 类) | `python scripts/render_crud_receipt.py --live-diet-delete-meal <日期> <餐别> --chain <思考链>` |
| 删某日饮食 | 清空某天 | `python scripts/render_crud_receipt.py --live-diet-delete-date <日期> --chain <思考链>` |
| 批量删饮食 | 按日期范围删 | `python scripts/render_crud_receipt.py --live-diet-delete-range <开始> <结束> --chain <思考链>` |

#### 看饮食(11)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 看今日饮食 | 今日按餐别分组明细 + 累计 vs 目标 | `python scripts/render_today_diet.py --chain <思考链>` |
| 看昨日饮食 | 昨日明细 | `python scripts/render_today_diet.py --date <昨天> --chain <思考链>` |
| 看本周饮食 | 本周自然周明细 + 汇总 | `python scripts/render_today_meals.py --week current --chain <思考链>` |
| 看上周饮食 | 上周自然周 | `python scripts/render_today_meals.py --week last --chain <思考链>` |
| 看本月饮食 | 本月自然月 | `python scripts/render_today_meals.py --month current --chain <思考链>` |
| 看上月饮食 | 上月自然月 | `python scripts/render_today_meals.py --month last --chain <思考链>` |
| 看最近 7 天饮食 | 滚动 7 天 | `python scripts/render_today_meals.py --days 7 --chain <思考链>` |
| 看最近 30 天饮食 | 滚动 30 天(按日汇总) | `python scripts/render_today_meals.py --days 30 --chain <思考链>` |
| 看某段时间饮食 | 自定义区间 | `python scripts/render_today_meals.py --start <开始> --end <结束> --chain <思考链>` |
| 看今日喝水 | 累计/距目标/每杯时间/进度环 | `python scripts/render_today_water.py --chain <思考链>` |
| 看「有备注」的饮食记录 | 带备注的记录表 | `python scripts/render_today_meals.py --with-note --days <N> --chain <思考链>` |

#### 查食品(9)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 查食品 | 查食物营养(名称/品牌/分类/热量/蛋白/碳水/脂肪/来源) | `python scripts/render_food_search.py --query <关键词>` |
| 查食品（按分类） | 按分类查食品库 | `python scripts/render_food_search.py --category <分类>` |
| 存食品 | 添加营养数据到库(每 100g) | `python scripts/render_crud_receipt.py --live-product-add <名称> <品牌> <热量> <蛋白> <脂肪> <饱和脂肪> <碳水> <糖> <纤维> <钠> [备注] --chain <思考链>` |
| 改食品 | 改食品库某条 | `python scripts/render_crud_receipt.py --live-product-update <id> [--字段 新值 ...] --chain <思考链>` |
| 下架食品 | 标废弃(查询/搜索/去重不再出现) | `python scripts/render_crud_receipt.py --live-product-deprecate <id> --chain <思考链>` |
| 看食品库（去重） | 全库重复组检查 + 处理建议 | `python scripts/render_dedupe_report.py` |
| 批量导入食品 | JSONL 批量导入(预览确认) | `python scripts/render_batch_import.py --input <preview.json>` → 确认后 `python scripts/batch_import.py import <file.jsonl>` |
| 校验批量导入 | 只校验不写入(失败原因) | `python scripts/batch_import.py validate <file.jsonl> --json-output <out.json>` → `python scripts/render_batch_import.py --input <out.json>` |
| 看食品来源统计 | 按来源分组计数 + 占比 | `python scripts/render_source_stats.py` |

#### 看营养(4)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 看营养结构 | 蛋白/碳水/脂肪占比 + 实际 vs 目标 | `python scripts/render_nutrition_ratio.py --days 7 --chain <思考链>` |
| 看今日营养 | 4 项营养实际 vs 目标 + 完成度 | `python scripts/render_today_diet.py --chain <思考链>` |
| 看饮食总览 | 本周/本月累计 + 趋势(不含今日) | `python scripts/render_diet_overview.py --chain <思考链>` |
| 看营养素深度 | 纤维/钠/糖 vs 推荐(缺数据标注) | `python scripts/render_nutrition_detail.py --days 7 --chain <思考链>` |

#### 看排行(20 · 5 榜 × 4 窗口)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 看高热量榜 / 看低热量榜 / 看频繁吃榜 / 看高碳水榜 / 看高蛋白榜 | TOP10(默认 7 天) | `python scripts/render_food_ranking.py --category <high_calorie\|low_calorie\|frequent\|high_carb\|high_protein> --top-n 10 --days 7 --chain <思考链>` |
| 5 榜 ×（最近 30 天） | TOP10 · 滚动 30 天 | 同上 + `--days 30` |
| 5 榜 ×（本月） | TOP10 · 自然月 | 同上 + `--start <月初> --end <月末>` |
| 5 榜 ×（自定义） | TOP10 · 自定义区间 | 同上 + `--start <开始> --end <结束>` |

#### 饮食复盘(5)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 饮食复盘（本周/本月/最近 90 天/今年/自定义时间） | 总热量/日均/总蛋白 + 趋势 + 高频 TOP5 + 一句话 | `python scripts/render_diet_review.py --type <week\|month\|quarter\|year\|range> [--start <开始> --end <结束>] --chain <思考链>` |

#### 餐别分布(5)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 看早餐（最近 7 天）/ 看午餐（最近 7 天）/ 看晚餐（最近 7 天）/ 看加餐（最近 7 天） | 单餐别明细 + 日均 + 一句话 | `python scripts/render_meal_distribution.py --meal <breakfast\|lunch\|dinner\|snack> --days 7 --chain <思考链>` |
| 看全部餐别分布（最近 7 天） | 各餐别热量占比 + 明细 | `python scripts/render_meal_distribution.py --meal all --days 7 --chain <思考链>` |

### ⚖️ 体重(58 场景 · 2026-08-02 ticket #4 落地)

**量体重(5)**:记体重 / 记体重（含备注）/ 补录体重 / 批量补录体重 / 看今日体重
**改体重记录(5)**:改体重记录 / 改某日体重 / 删体重记录 / 删某日体重 / 批量删体重
**看体重明细(7)**:看本周体重 / 看上周体重 / 看本月体重 / 看上月体重 / 看最近 7 天体重 / 看最近 90 天体重 / 看某段时间体重
**看体重曲线(10)**:看体重曲线 / 看体重曲线（带目标）/ 看体重曲线（带里程碑）/ 看体重曲线（带异常点）/ 看本月体重曲线 / 看上月体重曲线 / 看最近 90 天体重曲线 / 看最近 180 天体重曲线 / 看最近 365 天体重曲线 / 看某段时间体重曲线
**看体重稳不稳(5)**:看体重稳不稳（增强版）/ 看本月波动 / 看最近 90 天波动 / 看最近 180 天波动 / 看波动异常点
**看体重备注(1)**:看「有备注」的体重记录
**对比体重(18)**:对比体重：最近 30 天 vs 之前 30 天 / 对比体重：自定义两段时间 / 对比体重：本周 vs 上周 / 对比体重：本月 vs 上月 / 对比体重：近 N 天 vs 上一个 N 天 / 对比体重：今天 vs 一年前今天 / 对比体重：今天 vs 半年前今天 / 对比体重：今天 vs 三月前今天 / 对比体重：当前 vs 目标体重 / 对比体重：当前 vs 平台期首日 / 对比体重：当前 vs 历史最低 / 对比体重：当前 vs 历史最高 / 对比体重：减重 5kg 那天 vs 今天 / 对比体重：减重 10kg 那天 vs 今天 / 对比体重：当前 vs 入夏最低 / 对比体重：当前 vs 入冬最低 / 对比体重：运动多 vs 运动少的两个月 / 对比体重：工作日 vs 周末
**体重复盘(7)**:看体重总览 / 体重复盘（本周）/ 体重复盘（本月）/ 体重复盘（最近 90 天）/ 体重复盘（今年）/ 体重复盘（自定义时间）/ 看里程碑回溯

**交互规则(2026-08-02 用户拍板 · 规则落地本段,不写进 prompt)**:
- 改体重记录 / 删体重记录:用户未指明记录 → 列出最近候选(日期/体重/备注)供选择;删除前**快照确认**再删
- 补录体重:目标日已有记录 → 提示冲突(已有值 vs 新值),询问覆盖/保留后写入
- 批量补录体重:用户给「连续天数 + 起始体重」→ AI 生成每日条目;已有记录自动跳过并计入跳过数
- 删某日体重 / 批量删体重:删除前告知命中条数 → 用户确认 → 删除
- 对比体重：本周 vs 上周:每段记录数 ≥3 才显示对比,否则「样本不足」提示
- 对比体重：今天 vs 一年前/半年前/三月前:同期对比 ±3 天容差;未命中 → 容差命中说明(实际取到哪条/无数据)
- 对比体重：当前 vs 平台期首日:平台期 = 至少连续 14 天波动 ≤ ±0.5kg;取最近一次;统计第几次 + 历史平均突破耗时
- 对比体重：减重 5/10kg 那天:里程碑 = 从历史最高起累计减重 N kg 的第一个达标日;未达成 → 提示当前已减多少
- 对比体重：当前 vs 入夏/入冬最低:入夏 = 当年 6/1-8/31;入冬 = 12/1-次年 2/28(最近一个冬天)
- 对比体重：运动多 vs 运动少的两个月:极端月 = 运动总量最高/最低的自然月;睡眠数据只读外部技能(作息管家),缺失标注「缺失(外部技能未记录)」
- 「对比体重」裸词 = 「对比体重：最近 30 天 vs 之前 30 天」(A1)的别名

**核心 CLI**(详情见 §CLI 手册体重节):
- 记体重 / 补录体重:render_weight_receipt.py --live --kg <kg> [--note] [--date](chain 强制)
- 批量补录体重:render_weight_receipt.py --live-batch --input <jsonl>(写入/跳过/失败条数+明细回执)
- 改/删体重:render_crud_receipt.py --live-weight-update / --live-weight-delete <id|date|start end>(命中条数/快照/undo_cli)
- 明细/曲线/备注:render_weight_history.py --mode history|trend|notes + --week/--month/--days/--show-target/--show-milestones/--show-anomalies
- 对比体重 18:render_weight_compare.py --scenario <a1|a2|...|d4> --chain
- 总览/今日:render_weight_dashboard.py --view overview|today --chain
- 复盘/里程碑:render_weight_review.py --type week|month|90d|year|range|milestones --chain
- 稳不稳/异常点:render_weight_volatility_v2.py [--days N] [--view full|anomalies-only]
- 文本兜底:calorie_tracker.py weight [--date] / weight-update [--date] / weight-delete / weight-batch --input

### 🎯 目标管理(2026-08-02 新增 · 25 场景)

> 目标 = 用户的「终点」;闭环 = 定 → 看进度 → 改(+ 到期 + 预测)。
> 场景数量与场景名已定稿;prompt 定稿见 `docs/scene-prompts/06-目标管理.md`(修改须重新用户确认)。
> **交互规则(常驻,AI 执行本分类任一场景必须遵守)**:
> - 信息缺失才补问:用户表达清晰直接执行,不强制采访式引导;需要补的信息顶多做几句确认
> - 定/改类写库前给回执(改前/改后),自动算类给出依据与推荐理由再采纳
> - 看类走 HTML 渲染(有模板必走 HTML,§⚠️ 强制性规定 第 4 条)
> - 「看今日目标」的体重是累计目标,引导用户到「看体重目标进度」,不算今日完成度

#### 定目标(8)

> **体重目标闭环(#78/#79 · 2026-08-05)**:
> `填 HTML(输入侧)` → 用户填表 → `复制 prompt 给 AI`(含页面预计算的「建议速率」行:公式透明 + 极端目标警示)→ `AI 写库 set_weight_goal` → `渲染结果 HTML(输出侧)` 回给用户(✅ 已写入 + 已写入字段 + 进度 KPI + 极端警示 + 一句话)。
> - 速率一律用页面/脚本预计算值(`Δkg ÷ 天数 × 7`),**AI 禁止自行推算或编造数字**(算式透明,用户能反推验证)。
> - 极端目标判定:建议速率 ≥ 1.0 kg/周 → 回执必须出现「⚠️ 这是极端目标,建议速率 X kg/周(健康带 0.25–1.0)」。
> - 用户拿到结果 HTML 可:收藏对比、转发飞书、截图追踪;「复制数据」给任何 AI 复述口径一致。

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 定营养目标 | 设 4 项宏量营养目标(热量/蛋白/碳水/脂肪)+ 饮水;热量低于 BMR 提示 | `python scripts/render_goal_config.py --live --chain <思考链>` |
| 定营养目标(自动算) | 按档案 + 方向(减脂/维持/增肌)自动算 4 项,给依据与推荐理由 | `python scripts/render_goal_recommend.py --profile <减脂/维持/增肌> --chain <思考链>` |
| 定体重目标 | 目标 kg + 可选截止日期,显示当前体重/Δkg/建议速率;写库后渲染结果回执 | `python scripts/render_goal_weight.py --mode basic --chain <思考链>` → 写库后 `python scripts/render_goal_weight.py --live --kg <目标> [--deadline <日期>] --scene basic --chain <思考链>` |
| 定体重目标(自动算截止) | 目标 kg + 期望速率 → 推算截止日 + 速率校验;写库后渲染结果回执 | `python scripts/render_goal_weight.py --mode auto_deadline --chain <思考链>` → 写库后 `python scripts/render_goal_weight.py --live --kg <目标> --deadline <日期> --scene auto_deadline --chain <思考链>` |
| 定体重目标(含起始日) | 完整 setup:目标 + 起始日 + 截止日 + 起点体重;写库后渲染结果回执 | `python scripts/render_goal_weight.py --mode with_start --chain <思考链>` → 写库后 `python scripts/render_goal_weight.py --live --kg <目标> --deadline <日期> [--start-kg <起点>] [--start-date <起始日>] --scene with_start --chain <思考链>` |
| 定饮水目标 | 每天饮水目标(ml) | `python scripts/render_goal_config.py --live --water-only --chain <思考链>` |
| 定饮水目标(自动算) | 按体重 + 季节推推荐值,与旧值对比 | `python scripts/render_goal_recommend.py --water-only --chain <思考链>` |
| 一键定全套目标 | 营养+体重+饮水 3 类一键自动算,展示后确认采纳 | `python scripts/render_goal_recommend.py --full-kit --profile <减脂/维持/增肌> --chain <思考链>` |

#### 看目标(10)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 看今日目标 | 今日 5 项(热量/蛋白/碳水/脂肪/饮水)目标/实际/完成度 | `python scripts/render_goal_progress.py --mode today --chain <思考链>` |
| 看本周目标 | 日均 vs 日目标 + 周总量 vs 周目标 | `python scripts/render_goal_progress.py --mode week --chain <思考链>` |
| 看营养目标进度 | 4 项宏量进度条 + 完成度% + 缺口 | `python scripts/render_goal_progress.py --mode nutrition --chain <思考链>` |
| 看体重目标进度 | 当前/目标/Δ/完成%/预测 + 剩余天数/建议速率 | `python scripts/render_goal_progress.py --mode weight_progress --chain <思考链>` |
| 看饮水目标进度 | 累计/目标/完成度 + 剩余 ml | `python scripts/render_goal_progress.py --mode water --chain <思考链>` |
| 看目标对比实际 | 目标线 vs 实际线 + 偏差 + 时间窗口(默认 30 天) | `python scripts/render_goal_progress.py --mode vs_actual --chain <思考链>` |
| 看目标完成度 | 5 项完成度% + 缺口 + 总评分 | `python scripts/render_goal_progress.py --mode completion --chain <思考链>` |
| 看即将到期的目标 | 到期目标列表(默认 14 天内)+ 紧迫度 | `python scripts/render_goal_progress.py --mode weight --expiring 14 --chain <思考链>` |
| 看目标完成率(按周) | 本周 7 天每日完成率柱状 + 达标天数 | `python scripts/render_goal_progress.py --mode nutrition --period week --chain <思考链>` |
| 看目标完成率(按月) | 本月 30 天每日完成率柱状 + 达标天数 | `python scripts/render_goal_progress.py --mode nutrition --period month --chain <思考链>` |

#### 改目标(5)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 改营养目标 | 改某项/多项营养目标,显示改前/改后 + 影响预估 | `python scripts/render_goal_config.py --modify-nutrition --chain <思考链>` |
| 改体重目标 | 改体重目标值/截止日,显示改前/改后 + 新建议速率;写库后渲染结果回执 | `python scripts/render_goal_weight.py --mode modify --chain <思考链>` → 写库后 `python scripts/render_goal_weight.py --live --kg <新目标> [--deadline <新截止>] --scene modify --chain <思考链>` |
| 改饮水目标 | 只改饮水目标,其他不变 | `python scripts/render_goal_config.py --modify-water --chain <思考链>` |
| 暂停所有目标 | 临时冻结全部目标(记录照常),给恢复入口提示 | `python scripts/render_goal_status.py --status paused --chain <思考链>` |
| 重启所有目标 | 从暂停恢复全部目标 | `python scripts/render_goal_status.py --status resumed --chain <思考链>` |

#### 看目标(续)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 看目标历史完成 | 每日达成列表 + 完成/未完成天数统计 | `python scripts/render_goal_progress.py --mode history --chain <思考链>` |
| 看目标预测达成 | 预测达成日 + 置信度(体重部分复用对比体重预测) | `python scripts/render_goal_progress.py --mode predict --chain <思考链>` |

### 🏃 运动(2026-08-02 重写 · 39 场景)

> 第一性原理:运动 = 减肥 + 健康双驱动。场景数/名已定稿;prompt 定稿见 `docs/scene-prompts/04-运动.md`(修改须重新用户确认)。
> **运动目标 = 每日消耗卡**(`daily_goal.exercise_goal`):未设目标时「看今日/本周运动（vs 目标）」先问用户目标值并写库,周目标 = 日目标×7。
> **交互规则(常驻,AI 执行本分类任一场景必须遵守)**:
> - 热量缺失:按「A·卡路里综合考虑规则」估算并标注(见下方)
> - 记力量训练:每组一行流式录入,绝不合并
> - 补记运动:目标日期已有同类型记录 → 先提示用户再确认;回执带补录标识
> - 复制昨日运动:目标日期已有相同记录(同类型+同热量+同时长)则跳过并计入跳过条数
> - 改/删未指明记录:AI 先列最近候选让用户指认;删前快照确认
> - 批量删:删除前先预览范围内记录数,确认后执行
> - 看 60/180/365 天:降采样(每天一行 / 每 3 天 / 每周)

#### 记运动(8)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记运动 | 记一次运动(类型/时长/消耗/时间,热量估算会标注) | `python scripts/render_exercise_receipt.py --live-add --type <T> --calories <C> [--minutes <M>] --chain <思考链>` → **HTML:crud_receipt.html** |
| 记运动（含备注） | 同 记运动 + 备注 | `--live-add ... --note <N>` |
| 记力量训练 | 每组一行(N 组 × kg × reps) | `python scripts/render_exercise_receipt.py --live-add-strength --type <T> --sets <N> --load <KG> --reps <R> --chain <思考链>` |
| 记有氧运动 | 时长/距离/配速/平均+最高心率 | `--live-add --category 有氧 --minutes <M> --distance <KM> [--avg-hr <BPM>] [--max-hr <BPM>]` |
| 记日常活动 | 步数/时段/消耗 | `python scripts/render_exercise_receipt.py --live-add-daily --type <T> [--steps <N>] [--period <时段>] --minutes <M>` |
| 补记运动 | 补录历史某天(冲突提示 + 补录标识) | `--live-backfill --date <D> --type <T> --calories <C>` |
| 批量补记运动 | 一次多天(写入/跳过/失败) | `--live-batch-add --items "<日期 类型 热量 [时长];...>"` |
| 复制昨日运动 | 昨天 → 今天/指定日(复制/跳过) | `--live-copy [--target <D>]` |

#### 改运动(5)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 改运动记录 | 改某条(改前/改后) | `--live-update --id <ID> [--field <X> --value <Y>]` |
| 改某日运动 | 按日期(命中条数/改前/改后) | `--live-update-day --date <D> [--field <X> --value <Y>]` |
| 删运动记录 | 删某条(软删除 + 快照) | `--live-delete --id <ID>` |
| 删某日运动 | 删某天(删除条数) | `--live-delete-day --date <D>` |
| 批量删运动 | 按范围(范围/删除条数) | `--live-delete-range --from <F> --to <T>` |

#### 看运动(17)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 看今日运动 | 明细 + 今日累计 vs 目标 | `python scripts/render_exercise_summary.py --mode records --today --chain <思考链>` |
| 看昨日运动 | 同今日(昨天) | `--mode records --yesterday` |
| 看本周运动 | 表格 + 总时长/总消耗/日均 + 运动天数 | `--mode summary --week` |
| 看上周运动 | 同本周(上周) | `--mode summary --last-week` |
| 看本月运动 | 同本周(本月) | `--mode summary --month` |
| 看上月运动 | 同本周(上月) | `--mode summary --last-month` |
| 看最近 7 天运动 | 滚动 7 天 | `--mode summary --days 7` |
| 看最近 30 天运动 | 滚动 30 天 | `--mode summary --days 30` |
| 看某段时间运动 | 自定义区间 | `--mode summary --from <F> --to <T>` |
| 看今日运动（vs 目标） | 大进度环 + 差额 + 判断 + 一句话(未设目标先问) | `python scripts/render_exercise_goal_view.py --period today --chain <思考链>` |
| 看本周运动（vs 目标） | 同今日(周目标 = 日目标×7) | `--period week` |
| 看运动记录（有备注） | 表(日期/类型/时长/消耗/备注) | `--mode records --has-note` |
| 看运动记录（按力量筛选） | 表(日期/动作/组数/重量/次数) | `--mode records --category 力量` |
| 看运动记录（按有氧筛选） | 表(日期/类型/时长/距离/配速) | `--mode records --category 有氧` |
| 看最近 60 天运动 | 每天一行 | `--mode summary --days 60` |
| 看最近 180 天运动 | 每 3 天降采样 | `--mode summary --days 180 --downsample 3` |
| 看最近 365 天运动 | 每周降采样 | `--mode summary --days 365 --downsample week` |

#### 运动分析(4)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 看运动类型分布 | 饼图 + 各类条数/消耗/占比% | `python scripts/render_exercise_distribution.py --mode distribution` |
| 看力量训练总览 | 按动作聚合(总组数/总重量/次数)+ 轨迹 | `python scripts/render_exercise_strength.py --chain <思考链>` |
| 看有氧训练总览 | 按类型聚合(次数/时长/距离/配速) | `python scripts/render_exercise_cardio.py --chain <思考链>` |
| 看运动趋势 | 折线(每日时长/消耗/每周频次) | `python scripts/render_exercise_trend.py [--days 30] --chain <思考链>` |

#### 运动复盘(5)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 运动复盘（本周） | KPI + 趋势 + 高频 | `python scripts/render_exercise_recap.py --period week --chain <思考链>` |
| 运动复盘（本月） | 同本周(本月) | `--period month` |
| 运动复盘（最近 90 天） | 同本周(90 天) | `--period 90d` |
| 运动复盘（今年） | 同本周(今年) | `--period year` |
| 运动复盘（自定义时间） | 同本周(自定义) | `--period range --from <F> --to <T>` |

### 🏋️ 健身计划(29 场景 · 2026-08-02 ticket #6 落地)

**定训练计划(5)**:定训练计划 / 复制训练计划 / 定休息日 / 加训练动作 / 定一周计划
**看训练计划(7)**:看本周计划 / 看下周计划 / 看上周计划 / 看指定周计划 / 看今天练什么 / 看计划概览 / 看计划 vs 实际
**改训练计划(5)**:改训练计划 / 改某天训练 / 删某天训练 / 改动作 / 撤销训练计划
**落地训练(5)**:落地训练 / 落地到本周末 / 落地到本月底 / 同步到训记 / 拉训记实绩
**计划复盘(6)**:计划复盘（本周）/ 计划复盘（本月）/ 计划复盘（全部）/ 看计划完成率 / 看未完成训练 / 看动作完成率
**安全检查(1)**:扫禁忌

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 定训练计划 | AI 采访式对话(目标/经验/频率/部位)→ 预览确认 → 写入回执 | `python scripts/render_plan_receipt.py --live-plan-set --plan-json <JSON> --chain "..."` · 预览:`python scripts/render_plan_builder.py --mock <plan.json>` |
| 复制训练计划 | 复制整计划/某周为新模板 | `python scripts/render_plan_receipt.py --live-plan-copy [--new-title <T>] --chain "..."` |
| 定休息日 | 标记某天休息(或取消) | `python scripts/render_plan_receipt.py --live-plan-rest --week <W> --day <D> --rest <1|0> --chain "..."` |
| 加训练动作 | 给某天/时段加动作(默认所有周) | `python scripts/render_plan_receipt.py --live-plan-add --week <W> --day <D> --name <动作> --sets <N> --chain "..."` |
| 定一周计划 | 快速设置一周 7 天安排 | `python scripts/render_plan_receipt.py --live-plan-set-week --week <W> --days-json <JSON> --chain "..."` |
| 看本周/下周/上周/指定周计划 | 单周 7 天表 + 完成度 | `python scripts/render_workout_plan.py --mode week --week <N>` |
| 看今天练什么 | 今日动作 + 实时完成进度(接 exercise_log) | `python scripts/render_workout_plan.py --mode today` |
| 看计划概览 | KPI(总周数/完成率/训练日/动作数)+ 每周完成率 | `python scripts/render_workout_plan.py --mode overview` |
| 看计划 vs 实际 | 完成度 + 偏差 + 动作级对比表 | `python scripts/render_workout_plan.py --mode vs --start <D1> --end <D2>` |
| 改训练计划 | 改 config 字段(标题/总周数/开始日期/描述) | `python scripts/render_plan_receipt.py --live-plan-update --field <X> --value <Y> --chain "..."` |
| 改某天训练 | 改某天时段/动作/组数 | `python scripts/render_plan_receipt.py --live-plan-update-day --week <W> --day <D> --session <S> --chain "..."` |
| 删某天训练 | 删某天(快照确认 → 回执) | `python scripts/render_plan_receipt.py --live-plan-delete-day --week <W> --day <D> --chain "..."` |
| 改动作 | 替换动作/改组数(默认所有周) | `python scripts/render_plan_receipt.py --live-plan-update-movement --week <W> --day <D> --session <S> --old-name <A> --new-name <B> --chain "..."` |
| 撤销训练计划 | 删整个计划(确认 → 回执) | `python scripts/render_plan_receipt.py --live-plan-delete --chain "..."` |
| 落地训练 | 4 步落地(补计划/记心愿/推送/回写)+ 逐动作确认 | `python scripts/sync_plan.py --days 1` · 进度:`render_process_progress.py` |
| 落地到本周末/月底 | 批量落地到周日/月末 | `python scripts/sync_plan.py --days <N>` |
| 同步到训记 | Step 3 单做(审计动作名前置) | `python scripts/xunji_bridge.py push-plan --date <D>` |
| 拉训记实绩 | Step 4 单做(回写 exercise_log) | `python scripts/xunji_bridge.py backfill --date <D>` |
| 计划复盘（本周/本月/全部） | 完成率/训练日/消耗 + 趋势 + 对比 | `python scripts/render_exercise_review_html.py --days 7 / --start --end` |
| 看计划完成率 | 每周完成率折线 | `python scripts/render_workout_plan.py --mode completion` |
| 看未完成训练 | 漏练日期 + 应练动作 | `python scripts/render_workout_plan.py --mode missed --days <N>` |
| 看动作完成率 | 动作 TOP 榜 | `python scripts/render_workout_plan.py --mode movement --days <N>` |
| 扫禁忌 | 禁忌动作扫描(腰/膝/肩)+ 替代建议 | `python scripts/render_contraindication.py [--part {腰\|膝\|肩}]` |

### 📊 分析(154 场景 · 2026-08-02 ticket #11 落地)

> 场景数量与场景名已定稿;prompt 定稿见 `docs/scene-prompts/10-分析.md`(修改须重新用户确认)。
> 旧版分析唤醒词(查热量趋势 / 查营养结构 / 查热量缺口 / 查食物排行 / 查健康报告 / 查卡路里数据 等 13 条)已被本分类取代,legacy 流程见 §AI 触发场景详述旧段(过渡期可用)。

**A1 组合分析(60)**:看体重 vs 摄入(最近 7/15/30/60/90/180/365 天 · 本周 · 本月 · 自定义)、看体重 vs 运动(同 10 窗)、看体重 vs 蛋白(同 10 窗)、看体重 vs 缺口(同 10 窗)、看摄入 vs 运动(最近 7/30/90/180/365 天 · 自定义)、看体重 vs 体脂(同 6 窗)、看体重 vs 围度(同 6 窗)、看饮水 vs 体重(最近 30 天 · 自定义)
**A2 健康报告(19)**:看健康报告(本周 / 上周 / 最近 7/30/90/180/365 天 / 本月 / 上月 / 今年 / 自定义)、看BMI报告、看TDEE报告、看BMR报告、看蛋白质摄入报告、看水分摄入报告、看综合评分、看健康趋势、看健康报告(含对比)
**A3 整体趋势(15)**:看整体趋势(体重+摄入+运动 / 体重+体脂+围度 / 饮食+蛋白+纤维 / 运动+力量+有氧 / BMI+体脂+肌肉量 / 摄入+蛋白+运动 / 体重+蛋白+缺口 / 体重+摄入+缺口 / 体重+摄入+运动+缺口 / 蛋白+运动 / 综合多指标)+ 周期对比 4(含月度 / 季度 / 年度 / 目标对比)
**A4 自动分析(23)**:诊断体重波动原因 / 诊断体重停滞(含平台期判断) / 诊断体重反弹 / 诊断体重下降原因 / 诊断体重异常点 / 诊断体重vs体脂围度背离 / 诊断饮食超标 / 诊断饮食不足 / 诊断营养不均衡(含均衡判断) / 诊断饮食结构问题 / 诊断运动不足 / 诊断运动过量 / 诊断运动类型失衡 / 诊断运动效率(含有效判断) / 诊断运动建议(含类型推荐) / 为什么我没瘦 / 为什么我瘦太快 / 我的减重速度合理吗 / 我的减肥策略对吗 / 我距离目标还差什么 / 我这个月做得好的 / 我这个月需要改的 / 综合健康评估
**A5 营养分析(16)**:看蛋白 vs 碳水(最近 7/30/90 天 · 自定义)、看蛋白 vs 脂肪(最近 30/90 天 · 自定义)、看碳水 vs 脂肪(同 3 窗)、看三大营养交叉(最近 30/90 天 · 自定义)、看钠糖纤维趋势、看钠糖纤维综合、看营养建议
**A6 预测模拟(20)**:预测体重(1 周 / 1 月 / 3 月 / 6 月后 · 自定义时间 · 自定义目标)、模拟减重(每天-300/-500/-700卡 · 30/60/90天减Xkg · 自定义天数减Xkg)、摄入预测(按当前速率 1 周 / 1 月 / 3 月 · 自定义 · 营养目标达成 · 卡路里缺口 · 摄入稳定性)
**单点(1)**:看每日 6 因素综合

**交互规则(2026-08-02 用户拍板 · 规则落地本段,不写进 prompt)**:
- 时间窗口:场景名带窗口(最近 7 天等)直接用;「自定义」类先问起止日期再算;A3 整体趋势默认最近 90 天,用户可改选 7/30/90/180/365/自定义
- 诊断类(A4):口语问法由 AI 语义匹配到场景(如「我是不是平台期」→ 诊断体重停滞(含平台期判断);「为什么体重不动了」「我吃太多了吗」「我应该加哪种运动」同理),**无需用户说完整场景名**;诊断输出 = 原因假设 + 证据链 + 置信度 + 行动建议;数据不足(<7 天)明确降级提示
- 预测/模拟类(A6):体重数据 <14 天 → 明确提示「数据不足,不预测」,不硬算;自定义参数(天数 / 目标 kg / 每天缺口)先问后算
- 结果型 HTML:统一走 `render_analysis.py`,输出到 calorie_html/(场景名_结果_TS.html),必须 SEND_TO_USER

**核心 CLI**(统一入口):
- `python scripts/render_analysis.py --view combined --pair <weight_calorie|weight_exercise|weight_protein|weight_deficit|calorie_exercise|weight_bodyfat|weight_waist|water_weight|protein_carbs|protein_fat|carbs_fat> --window <7d|15d|30d|60d|90d|180d|365d|week_cur|month_cur|custom> [--start <D> --end <D>]`
- `python scripts/render_analysis.py --view report --kind <full|bmi|tdee|bmr|protein|water|score|trend|compare> --window <...>`
- `python scripts/render_analysis.py --view trend --group <g1..g11> --window <...> [--period <monthly|quarterly|yearly|target>]`
- `python scripts/render_analysis.py --view anomaly --diagnose <weight_volatility|weight_plateau|weight_rebound|weight_loss_cause|weight_anomaly|weight_divergence|diet_over|diet_under|diet_unbalanced|diet_structure|exercise_insufficient|exercise_overload|exercise_type_imbalance|exercise_efficiency|exercise_advice|why_not_losing|why_losing_fast|rate_reasonable|strategy_check|gap_to_goal|month_highlights|month_improve|overall> --window <...>`
- `python scripts/render_analysis.py --view nutrition --group <macro3|sodium_fiber|sodium_combined|advice> --window <...>`
- `python scripts/render_analysis.py --view predict --kind <weight_week|weight_month|weight_3m|weight_6m|weight_custom_t|weight_target|sim_cut_300|sim_cut_500|sim_cut_700|sim_target_30|sim_target_60|sim_target_90|sim_target_custom|cal_week|cal_month|cal_3m|cal_custom|cal_goal|cal_deficit|cal_stability> [--days <N>] [--target <kg>] [--cut <卡>]`
- `python scripts/render_analysis.py --view six --date <YYYY-MM-DD>`

### 🛠 基础信息(2026-08-02 新增 · 4 场景)

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 设置档案 | 填 4 项(身高/年龄/性别/活动量);**采访式引导 = AI 默认交互**:用户没说全时逐项问 + 按日常情况推荐活动量 | `python scripts/render_crud_receipt.py --live-profile-set --age <A> --gender <G> --height <H> --activity <L>`(写库 + 回执) |
| 设活动量 | 只设活动量(5 档),显示系数变化与影响 | `python scripts/render_crud_receipt.py --live-profile-activity <level>` |
| 改档案 | 单字段/多字段修改(身高/年龄/性别/活动量/备注),改前/改后对比 + 影响提示 | `python scripts/render_crud_receipt.py --live-profile-update --field <X> --value <Y> [--field <X2> --value <Y2> ...]` |
| 查档案 | 查看完整档案(含活动量/最新体重/BMI/BMR/TDEE + 系数说明) | `python scripts/render_crud_view.py --entity profile` |

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

> **⚠️ 新旧词对照(2026-08-09 · #235/#242 对抗审查补)**:本节及以下各 legacy 小节(v2.x 时代写法)
> 的旧触发词已由 v1.0 场景体系取代,权威词表 = `scripts/_triggers.py`(check_trigger_consistency.py 校验)。
> **AI 路由优先级:新词 > 旧词**——用户口语命中旧词时,先映射到新词场景再执行;旧词 CLI 仅作过渡兼容。
>
> | 旧词(本节 legacy) | 新词(v1.0 权威源) | 说明 |
> |---|---|---|
> | 查热量趋势 | 看热量趋势 / 查热量趋势 | 分析分类 · 见 §分析 |
> | 查吃的记录 / 查今天吃 | 看今日饮食 | 饮食分类 · render_today_diet.py |
> | 改吃的 / 删吃的 | 改饮食记录 / 删饮食记录 | 饮食分类 · render_crud_receipt.py |
> | 查热量 | 查食品 | 食品库搜索 · render_food_search.py |
> | 查食品库 | 看食品库（去重） / 查食品（按分类） | 食品库 · render_dedupe_report / render_food_library |
> | 批量导入 / 校验批量 | 批量导入食品 / 校验批量导入 | 食品库 · render_batch_import.py |
> | 拍营养表 | 拍营养表记一餐 / 拍营养表补记一餐 | 饮食分类 · render_nutrition_label.py |
> | 复盘今日 | 今日复盘 | 复盘 · render_review.py --type day |
> | 复盘本周 / 复盘本月 / 复盘本年 | 本周复盘 / 本月复盘 / 复盘(默认周) | 复盘 · render_review.py |
> | 查运动记录 / 查运动汇总 | 看今日运动 / 看运动趋势 / 运动复盘（本周） | 运动分类 |
> | 查健康报告 | 看健康报告 | 分析分类 · render_health_dashboard.py |
> | 查食物排行 | 看高热量榜 / 看低热量榜 / 看频繁吃榜 / 看高碳水榜 / 看高蛋白榜 | 分析分类 · render_food_ranking.py |

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

##### 其他时间区间类 trigger · 用户说法 → CLI 参数映射

下列 6 个 trigger 支持任意日期区间(单日 / 区间 / 相对 / 整月 / 整年)。AI 收到用户说法后,先看本表,再选择 CLI 参数。

**通用日期格式**(所有 trigger 共享):
- ISO:`2026-07-17` ✓
- 简写:`7/17` / `7-17`(默认当年 2026)
- 相对:`今天` / `昨天` / `上周` / `过去 N 天` / `最近 N 天`
- 整月:`2026-07` / `7 月`
- 范围:`7/1 到 7/14` / `7/1-7/14` / `7/1:7/14`

---

###### 查热量趋势(已实现 · render_calorie_trend.py)

| 用户说法 | CLI 参数 | 备注 |
|---|---|---|
| `查热量趋势` | `--days 7`(默认) | 近 7 天 |
| `查热量趋势 上周` | `--days 7`(已过去) | |
| `查热量趋势 昨天` | `--start 昨天 --end 昨天` | 单日 |
| `查热量趋势 7/1 到 7/14` | `--start 2026-07-01 --end 2026-07-14` | |
| `查热量趋势 7 月` | `--start 2026-07-01 --end 2026-07-31` | 整月 |
| `查热量趋势 最近 30 天` | `--days 30` | |
| `查热量趋势 2026 上半年` | `--start 2026-01-01 --end 2026-06-30` | 跨月 |

---

###### 查营养结构(已实现 · render_nutrition_ratio.py)

**注意**:曾用名"查营养配比",2026-07-24 改名为"查营养结构"(语义更准:查的是"我的饮食结构",非单品食物)。

| 用户说法 | CLI 参数 |
|---|---|
| `查营养结构` | `--days 7`(默认) |
| `查营养结构 7/1 到 7/14` | `--start 2026-07-01 --end 2026-07-14` |
| `查营养结构 7 月` | `--start 2026-07-01 --end 2026-07-31` |
| `查营养结构 最近 30 天` | `--days 30` |
| `查营养结构 2026 Q2` | `--start 2026-04-01 --end 2026-06-30` |

---

###### 查热量缺口 / 查运动分布 / 查运动贡献(待实现)

> ⏳ **占位说明**:这三个 trigger 的 renderer 待 Phase H.4-H.6 实现。
> AI 路由表里已标注支持任意日期区间,但 CLI 层 renderer 尚未交付。
> 当前用户询问时 AI 应回答"该功能正在开发,完成后可支持任意区间"。

预计 CLI:
- `查热量缺口` → `render_calorie_deficit.py --start --end --days`
- `查运动分布` → `render_exercise_distribution.py --start --end --days`
- `查运动贡献` → `render_exercise_distribution.py --type contribution --start --end --days`

---

###### 查健康报告(已实现 · render_health_dashboard.py)

| 用户说法 | CLI 参数 |
|---|---|
| `查健康报告` | `--days 7`(默认) |
| `查健康报告 本月` | `--start 本月1号 --end 今天` |
| `查健康报告 2026 上半年` | `--start 2026-01-01 --end 2026-06-30` |
| `查健康报告 2026-07-13:2026-07-19` | `--start 2026-07-13 --end 2026-07-19` |

---

###### 查食物排行 + 5 榜单(已实现 · render_food_ranking.py)

> 6 个 trigger 共用同一模板,只是 category 参数不同。

| 用户说法 | CLI 参数 |
|---|---|
| `查食物排行` | `--days 7`(默认 high_calorie) |
| `查高热量榜` | `--days 7 --category high_calorie`(默认) |
| `查低热量榜` | `--days 7 --category low_calorie` |
| `查频繁吃榜` | `--days 7 --category frequent` |
| `查高碳水榜` | `--days 7 --category high_carb` |
| `查高蛋白榜` | `--days 7 --category high_protein` |
| `查食物排行 7 月` | `--start 2026-07-01 --end 2026-07-31 --category high_calorie` |

---

###### 计划复盘（本周/本月/全部）(已实现 · render_exercise_review_html.py)

| 用户说法 | CLI 参数 |
|---|---|
| `计划复盘（本周）` | `--days 7`(默认) |
| `计划复盘（本月）` | `--start <月初> --end <今天>` |
| `计划复盘（全部）` | `--start <计划起始> --end <今天>` |
| `计划复盘 今天` | `--start 今天 --end 今天` |
| `计划复盘 7/1 到 7/14` | `--start 2026-07-01 --end 2026-07-14` |

---

##### H.7-H.14 新增 trigger · 用户说法 → CLI 参数映射(v2.1.4 同步)

以下 12 个 trigger 是 Phase H 新增的,统一按"用户说法 → CLI 参数"格式记录。

---

###### 查体重历史 / 趋势 / 波动 / 对比(已实现 · render_weight_history.py,4 mode 共用)

| 用户说法 | CLI 参数 | 备注 |
|---|---|---|
| `查体重历史` | `--days 30`(默认 mode=history) | 历史列表 |
| `查体重趋势` | `--days 30`(默认 mode=trend) | 折线图 + 起始结束对比 |
| `查体重波动` | `--days 30`(默认 mode=volatility) | 标准差 + 异常点 (2σ) |
| `对比体重` | `--days 30`(默认 mode=compare) | 前期 vs 后期均重对比 |
| `查体重历史 上周` | `--days 7 --mode history` | 缩小区间 |
| `查体重趋势 最近 90 天` | `--days 90 --mode trend` | 拉长区间 |
| `对比体重 7/1 到 7/31` | `--start 2026-07-01 --end 2026-07-31 --mode compare` | 整月对比 |

---

###### 查运动记录 / 汇总 / 类型 / 趋势(已实现 · render_exercise_summary.py,4 mode 共用)

| 用户说法 | CLI 参数 | 备注 |
|---|---|---|
| `查运动记录` | `--days 7`(默认 mode=records) | 详细记录列表 |
| `查运动汇总` | `--days 7`(默认 mode=summary) | 天数/总热量/总时长 |
| `查运动类型` | `--days 7`(默认 mode=stats) | 按 4 类占比 |
| `查运动趋势` | `--days 7`(默认 mode=trend) | 每日热量面积图 |
| `查运动汇总 7 月` | `--start 2026-07-01 --end 2026-07-31 --mode summary` | 整月 |
| `查运动类型 上周` | `--days 7 --mode stats` | 缩小区间 |

---

###### 查吃的记录(已实现 · render_today_meals.py)

| 用户说法 | CLI 参数 |
|---|---|
| `查吃的记录` | `--date 今天`(默认单日) |
| `查吃的记录 昨天` | `--date 昨天` |
| `查吃的记录 2026-07-15` | `--date 2026-07-15` |
| `查吃的记录 最近 3 天` | `--start 2026-07-22 --end 2026-07-24` |
| `查吃的记录 7/1 到 7/14` | `--start 2026-07-01 --end 2026-07-14` |

---

###### 查档案 / 查定时复盘(已实现 · render_crud_view.py,报告型)

**重要**:状态查询不归 render 管 — AI 收到 prompt 后会自己调 `mavis cron list` 查实际状态。

| 用户说法 | CLI 参数 |
|---|---|
| `查档案` | (无需参数,展示 user_profile + 最新体重) |
| `查定时复盘` | (无需参数,展示 mavis cron 当前状态) |

---

###### 设置档案 / 设活动量 / 改档案(已实现 · render_crud_receipt.py live 模式,回执型)

> **设置档案**:AI 采访式引导逐项询问(或 profile_setup.html --live 配置页辅助) → 执行 `render_crud_receipt.py --live-profile-set --age <A> --gender <G> --height <H> --activity <L>`(写库 + 回执)
> **设活动量**:`calorie_tracker.py profile activity <level>`(5 档,显示系数 旧→新 + 影响)
> **改档案**:`render_crud_receipt.py --live-profile-update --field <X> --value <Y>`(可多对 --field/--value,一次生成合并回执,逐字段显示改前/改后 + 影响提示)

| 用户说法 | 触发方式 |
|---|---|
| `设置档案` | 打开 HTML(--live),填年龄/性别/身高/活动量 → 生成 prompt;或 AI 逐项采访询问 |
| `设置档案 30 male 177 --activity moderate` | AI 解析后直接调 `render_crud_receipt.py --live-profile-set`,无需配置页 |
| `设活动量 活跃` | AI 调 `profile activity active` |
| `改档案 把身高改成 180` | AI 调 `profile update --field height --value 180` |

---

###### 开启 / 关闭定时复盘(已实现 · render_cron_setup.py / render_cron_setup.py,配置型)

> **关键**:状态查询由 AI 自动完成 — 用户填好参数 → 生成 prompt → AI 先 `mavis cron list` 查现有 → 决定 create/update/delete

| 用户说法 | 触发方式 |
|---|---|
| `开启定时复盘` | 打开 HTML,填任务名/Schedule/时区/命令 → 生成 prompt |
| `关闭定时复盘` | (状态卡显示当前 → 点"关闭" → 复制 prompt) |

---

##### 7 个 CRUD trigger 通用(已实现 · render_crud_receipt.py,回执型)

> 任何"删/改"操作后,生成回执 HTML 让用户安心。

| 用户说法 | 实际行为 |
|---|---|
| `删吃的` / `改吃的` | DB delete/update + 返回回执 HTML |
| `改食品` | 食品库 update + 回执 |
| `删身材照` / `改照片标签` | body_photos update/delete + 回执 |
| `改运动记录` / `改体重记录` | exercise_log/weight_log update + 回执 |

回执含:**操作类型 ID + 字段对比(旧→新)+ 撤销指令复制 + 10 秒后失效**。

#### 改吃的(已实现 · `calorie_tracker.py update-meal`,v2.2.0 接口对齐)

**v2.2.0 重大变更**:`update-meal` 从 3 字段扩展到 **8 字段**,与 `add-meal` 接口完全对称。

**支持字段**(`**kwargs`):
| 字段 | CLI 参数 | 类型 | 场景 |
|---|---|---|---|
| `food_name` | `--food` | str | 改名 |
| `grams` | `--grams` | float | 改克数 |
| `note` | `--note` | str | 改备注 |
| `date` | `--date` | YYYY-MM-DD | 补录场景改日期 |
| `time` | `--time` | HH:MM[:SS] | 补录场景改时间 |
| `calories` | `--calories` | float | AI 估错热量,只改热量 |
| `protein` | `--protein` | float | 只改蛋白 |
| `carbs` | `--carbs` | float | 只改碳水 |
| `fat` | `--fat` | float | 只改脂肪 |

**不支持**:`meal_type`(从 `time` 自动推断,不存 DB)

**关键设计**:
- `**kwargs` 风格:任意字段可单独或组合改
- 返回 `before/after/changed` diff:对接 H.10 `crud_receipt.html` 回执 UI
- 校验:负值拒绝、非法字段名明确报错、空调用报错

**用户说法 → CLI 映射**:
| 用户说法 | CLI 命令 |
|---|---|
| `改吃的 5 克数改成 180` | `update-meal 5 --grams 180` |
| `改吃的 5 热量改成 180 卡` | `update-meal 5 --calories 180` |
| `改吃的 5 错了,实际是 200/15/30/8` | `update-meal 5 --calories 200 --protein 15 --carbs 30 --fat 8` |
| `改吃的 5 补录成昨天 18:30 晚饭` | `update-meal 5 --date 2026-07-19 --time 18:30` |
| `改吃的 5 改名鸡胸(去皮)` | `update-meal 5 --food "鸡胸(去皮)"` |
| `改吃的 5 加备注"妈妈做的"` | `update-meal 5 --note "妈妈做的"` |

**测试套**:`tests/diet_update_meal.py` 7 个 case(24 assertions 全过)


##### 单日类 trigger · `--date` 参数

以下 trigger 用单日参数,不支持任意区间。

| Trigger | 用户说法 | CLI 参数 |
|---|---|---|
| `查今天吃` | 默认 | `--date 今天` |
| `查今天吃 昨天` | 单日查询 | `--date 昨天` |
| `查今天吃 2026-07-15` | 任意单日 | `--date 2026-07-15` |
| 主页(查今日/查主页) | 默认 | `--date 今天` |
| `记体重` | 默认 | `--date 今天` |

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

### 🧬 身体细节(体脂 + 围度 · v1.0 13 场景 · 2026-08-02 ticket #9)

**第一性原理**:体脂 + 围度 = 身体成分追踪;来源不可直接比;部位独立轨迹。

| 唤醒词 | 功能 | CLI |
|---|---|---|
| 记体脂（皮褶钳） | 皮褶钳测 7 点(自动算体脂率 Jackson-Pollock)| `python scripts/body_composition.py add ...` → **HTML:`body_composition_wizard.html`** · **场景 1/2 决策见 §⚠️ 强制性规定 第 5 条** |
| 记体脂（外部测量） | 外部设备体脂(健身房 InBody/医院/其他)| `python scripts/body_composition.py add --source gym/hospital ...` → **HTML:`body_composition_wizard.html`** |
| 记围度 | 13 部位(至少 1 项必填)| `python scripts/body_measurements.py add ...` → **HTML:`body_measurements_wizard.html`** · **场景 1/2 决策见 §⚠️ 强制性规定 第 5 条** |
| 补记体脂 | 补录历史某天(冲突提示 + 循环补)| `python scripts/body_composition.py add --date <D> ...` → **HTML:`body_composition_wizard.html`** |
| 补记围度 | 补录历史某天(冲突提示 + 循环补)| `python scripts/body_measurements.py add --date <D> ...` → **HTML:`body_measurements_wizard.html`** |
| 看体脂 | 历史 + 来源筛选(皮褶钳/健身房/医院/全部)| `python scripts/render_body_composition_view.py --mode list [--source <s>] --chain "1.识别→2.读DB→3.渲染"` → **HTML:`body_composition_view.html`** |
| 看体脂趋势 | 折线(默认最近来源,可切换)| `python scripts/render_body_composition_view.py --mode trend [--source <s>] --chain "1.识别→2.读DB→3.渲染"` → **HTML:`body_composition_view.html`** |
| 看围度 | 历史 + 部位筛选 | `python scripts/render_body_measurements_view.py --mode list [--metric <col>] --chain "1.识别→2.读DB→3.渲染"` → **HTML:`body_measurements_view.html`** |
| 看围度趋势 | 折线(先选部位)| `python scripts/render_body_measurements_view.py --mode trend --metric <col> --chain "1.识别→2.选部位→3.读DB→4.渲染"` → **HTML:`body_measurements_view.html`** |
| 对比体脂 | 两段时间对比(注明同来源)| `python scripts/render_body_composition_view.py --mode compare --start1 <D1> --end1 <D2> --start2 <D3> --end2 <D4> [--source <s>] --chain "1.识别→2.读DB→3.渲染"` → **HTML:`body_composition_view.html`** |
| 对比围度 | 两个日期 13 项 Δ | `python scripts/render_body_measurements_view.py --mode compare --date1 <D1> --date2 <D2> --chain "1.识别→2.读DB→3.渲染"` → **HTML:`body_measurements_view.html`** |
| 删体脂 | 软删除(先列候选 → 快照确认 → 回执)| `python scripts/render_body_delete_receipt.py --entity composition --id <ID> --chain "1.列候选→2.确认→3.删除→4.回执"` → **HTML:`crud_receipt.html`**(删除前快照+回执) |
| 删围度 | 软删除(先列候选 → 快照确认 → 回执)| `python scripts/render_body_delete_receipt.py --entity measurements --id <ID> --chain "1.列候选→2.确认→3.删除→4.回执"` → **HTML:`crud_receipt.html`**(删除前快照+回执) |

**交互规则(v1.0 · ticket #9 用户拍板)**:
- 用户只说「记体脂」没说方式 → AI 先问:皮褶钳还是外部设备?
- 补记类:日期冲突先提示再确认;补完问「还要补其他日期吗」循环
- 删除类:用户不提供 ID——AI 先列最近几条候选,用户指认 → 快照确认 → 删 → 回执
- 对比体脂支持日期或时间段;对比围度单点日期(13 项 Δ)

**7 皮褶字段**(单位 mm,严格 (0, 100) exclusive,必填 7 项):
- `caliper_chest_mm`(胸皮褶 / pectoral)
- `caliper_abdominal_mm`(腹皮褶 / abdominal,脐旁 2cm)
- `caliper_thigh_mm`(大腿前中线)
- `caliper_tricep_mm`(肱三头肌 / 上臂后中线,肩峰-鹰嘴中点)
- `caliper_subscapular_mm`(肩胛下角下方)
- `caliper_suprailiac_mm`(髂嵴上方,腋前线)
- `caliper_midaxillary_mm`(腋中线,胸骨柄水平)

**Jackson-Pollock 7 点法自动算**(男/女公式不同):
- 男:BD = 1.112 - 0.00043499×Σ + 0.00000055×Σ² - 0.00028826×年龄
- 女:BD = 1.097 - 0.00046971×Σ + 0.00000056×Σ² - 0.00012828×年龄
- 体脂率 % = (495 / BD) − 450(范围 (0, 60) exclusive)

**source 维度**(`scripts/source_constants.py`):`home_caliper`(家测皮褶钳)/ `hospital`(医院测)/ `gym`(健身房 InBody,2026-08-02 加)

**13 围度字段**(单位 cm,记录级必填 ≥1 项,列级可 NULL,范围见括号):
- **上身(5 项)**:`chest_cm`(胸, 20–200)、`waist_cm`(腰, 20–200)、`abdomen_cm`(腹, 20–200)、`hip_cm`(臀, 20–200)、`shoulder_cm`(肩, 20–200)
- **下身(4 项)**:`left_thigh_cm`(左大腿, 10–100)、`right_thigh_cm`(右大腿, 10–100)、`left_calf_cm`(左小腿, 10–80)、`right_calf_cm`(右小腿, 10–80)
- **手臂(4 项)**:`left_arm_cm`(左上臂, 10–60)、`right_arm_cm`(右上臂, 10–60)、`left_forearm_cm`(左前臂, 10–50)、`right_forearm_cm`(右前臂, 10–50)

### 📸 身材照片

| 唤醒词 | 功能 | CLI | HTML |
|--------|------|-----|------|
| 记身材照 | 存一张/含备注/批量存照片(发图或路径双模式) | `render_body_photo_receipt.py --live-add <照片...> --tag <标签> [--note <备注>] --chain "..."` | `body_photo_receipt.html`(回执,内嵌缩略图) |
| 查身材照 | 浏览照片网格(时间/标签筛选 + 总数/标签计数/距上次拍照) | `render_body_photo_gallery.py [--days N \| --start D --end D] [--tag X] --chain "..."` | `body_photo_gallery.html`(结果) |
| 对比两张照片 | 两张并排对比(日期/间隔/标签/备注) | `render_body_photo_compare.py --id1 N --id2 M --chain "..."` | `body_photo_compare.html`(结果) |
| 生成身材照GIF | 时间段多张合成变化 GIF(帧数/首末日期) | `render_body_photo_gif_result.py --tag X [--start D --end D \| --days N \| --photo-id N ...] --chain "..."` | `body_photo_gif_result.html`(结果) |
| 删身材照 | 删除照片(先列候选 → 快照确认 → 回执,物理删不可恢复) | `render_body_photo_receipt.py --live-delete --id N --chain "..."` | `body_photo_receipt.html`(回执) |
| 改照片标签 | 标签覆盖整套(可多个) | `render_body_photo_receipt.py --live-tag-set --id N --tag-list "正面,侧面" --chain "..."` | `body_photo_receipt.html`(回执) |
| 加照片标签 | 追加标签(可多个,判重) | `render_body_photo_receipt.py --live-tag-add --id N --tag 正面 --chain "..."` | `body_photo_receipt.html`(回执) |
| 删照片标签 | 移除标签(可多个,至少保留 1 个) | `render_body_photo_receipt.py --live-tag-remove --id N --tag 正面 --chain "..."` | `body_photo_receipt.html`(回执) |

#### 📱 手机/飞书发图录入规则(2026-08-02 · ticket #10 · 必读)

> 第一性:照片本体 = 数据;路径只是电脑上的表达。手机上「发文字」与「发图片」是两条独立消息,**顺序不定**。

**双模式输入**:
- **发图模式**(手机/飞书·主):用户直接发照片 → AI 把收到的图片保存为本地文件(消息附件自带路径;只有 URL 则先下载到临时目录)→ 作为 `--live-add` 输入
- **路径模式**(电脑·辅):用户给文件路径 → 直接用

**分离到达处理**:
1. 文字先到(如「接下来有张照片」)→ AI 确认并**等待图片**,不催、不卡流程
2. 图片先到 → AI 先收图,等待/追问文字上下文(标签/备注/意图)
3. **同一轮对话内用户发的所有图片 = 本次要存的照片**(除非用户另有说明);连发多张 = 批量存
4. 标签是硬规则必填(筛选/对比的第一性维度)→ 缺标签逐张追问

**多标签模型(字符串编码)**:
- 存储:`tag` 列逗号分隔,如 `正面,侧面`(单个标签 ≤ 20 字,单张 ≤ 10 个)
- 语义分层(一字之差别混淆):`改` = 覆盖整套 / `加` = 追加(判重) / `删` = 移除(至少保留 1 个,删空报错;想清空全部用「改照片标签」)
- 筛选/对比按「包含匹配」:含该标签的照片都算

#### 身材照 GIF `--crops` JSON schema(v2.3.0)

`--crops` 接收 JSON dict,**key 是照片 ID**,**value 是 `[x1, y1, x2, y2]` 矩形坐标**(像素,左上原点):

```json
{
  "12": [120, 240, 400, 600],
  "15": [100, 200, 380, 600],
  "22": [150, 260, 420, 600]
}
```

- `x1 < x2`, `y1 < y2`(若不满足,会被边界 clamp)
- 不传 `--crops` = 全部用原图
- 坐标来自 `body_photo_gif_planner.html` 的 cropper.js 框选(用户手动调整)

#### HTML 交付协议(V1.3 · 必须 send · 2026-07-25 强化)

> **Agent 铁律**:跑完 render 后,**必须主动 send HTML 给用户**,不是告诉路径让用户自己找。

**完整流程**:

```bash
# 1. 跑 render → stdout 末行是 HTML 路径
python scripts/render_body_photo_gif_planner.py --tag 正面 2>&1 | tail -1
# 典型输出: ⚠️ ACTION=SEND_TO_USER | HTML=/path/body_photo_gif_planner_xxx.html

# 2. Agent 必须:
#    a) 解析 stdout 末行的 HTML 路径
#    b) 调飞书 send(默认) 或 Chrome 打开(用户不在飞书时)
#    c) **不只是告诉用户路径**,必须 send 文件
```

**send 优先级**(按用户实际可用工具):
1. **飞书**(默认 · 用户主要通讯工具 · 用 `send_file_to_feishu` 或 `feishu_im_file`)
2. 微信/QQ(若有 MCP)
3. Chrome 打开(用户在电脑前 · 仅 fallback)
4. 仅告诉路径(**禁止** · 违背协议)

**render stdout 协议**(v2.3.1 加):
- stdout 末行固定格式:`⚠️ ACTION=SEND_TO_USER | HTML=<绝对路径>`
- Agent 解析后**主动 send**,不是单纯 echo 给用户

**常见 fail mode**(agent 自检):
- ❌ "HTML 已生成在 /tmp/xxx.html"(只给路径,无 send) → fail
- ❌ "请打开 /tmp/xxx.html"(让用户自己找) → fail
- ✅ "HTML 已发到你飞书([链接])"(主动 send) → pass

**禁止**:只跑 render 不主动 send(违背 V1.3 主动交付原则)。

**失败回执(08 规范 §6.1 三层反馈 · 2026-08-05)**:写库失败 / 补记冲突 / 校验不过时,AI 必须渲染错误回执 HTML(python scripts/render_error_receipt.py --scene-name ... --op ... --reason ... --data ... --suggestion ... --fix-prompt ... --chain ...),含:操作名 / 失败原因(人类可读)/ 关键数据 / 建议下一步 + 修正重试(复制修正 prompt)/ 复制数据 / 复制日志。禁止只回文字报错。

**图片预置(v2.3.3)**:HTML 默认 base64 嵌图(PIL 缩放到 800x1200 · q85),
飞书 / IM / 任意环境打开都能看照片,不被本地路径限制。
不嵌:加 (本地 Chrome 可选)。

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
python scripts/calorie_tracker.py update-meal 5 --grams 180                    # 修改记录5的克数为180g
python scripts/calorie_tracker.py update-meal 5 --calories 180                  # 只改热量
python scripts/calorie_tracker.py update-meal 5 --calories 200 --protein 15 --carbs 30 --fat 8  # 改 4 营养(同源)
python scripts/calorie_tracker.py update-meal 5 --date 2026-07-20 --time 18:30   # 补录场景改日期/时间
python scripts/calorie_tracker.py summary                        # 今日摘要(含饮水)
python scripts/calorie_tracker.py history 7                      # 最近7天历史
python scripts/calorie_tracker.py goal 1800 150 200 60 2000      # 设置目标:热量 蛋白 碳水 脂肪 饮水ml
python scripts/calorie_tracker.py water 500                      # 记录饮水 500ml
```

### 用户档案(profile,2026-07-16 新增)
```bash
python scripts/calorie_tracker.py profile set 30 male --height 177 --activity moderate --note "默认值"  # 全量设置(2026-08-02 加 --activity)
python scripts/render_crud_receipt.py --live-profile-set --age 30 --gender male --height 177 --activity moderate  # 设置档案(写库+回执)
python scripts/render_crud_receipt.py --live-profile-activity <level>  # 设活动量(写库+回执)
python scripts/render_crud_receipt.py --live-profile-update --field height --value 180 --field activity --value active  # 改档案多字段(写库+合并回执)
python scripts/calorie_tracker.py profile activity <level>       # 只设活动量(纯文本,底层)
python scripts/calorie_tracker.py profile update --field height --value 180   # 单字段更新(改档案)
python scripts/calorie_tracker.py profile get       # JSON 输出
python scripts/calorie_tracker.py profile show      # 人类可读
```

用途:review TDEE(Mifflin-St Jeor 公式)需要年龄+性别,优先从 user_profile 表读取。
活动量 5 档(sedentary/light/moderate/active/very_active)决定 TDEE 系数(1.2/1.375/1.55/1.725/1.9,默认 moderate=1.55)。

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
python scripts/calorie_tracker.py weight-goal --weight-goal 73 --deadline 2026-12-31    # 设置体重目标 + 截止日期(v2.5.5 起仅 flag 形式)
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
# 写操作统一走 live 渲染器(写库 + 回执 HTML 一体,--chain 强制)
python scripts/render_body_photo_receipt.py --live-add photo1.jpg --tag 正面 --note "早起" --chain "1.解析→2.写库→3.回执"
python scripts/render_body_photo_receipt.py --live-add p1.jpg p2.jpg --tag 正面,侧面 --chain "..."
python scripts/render_body_photo_receipt.py --live-delete --id 1 --chain "..."
python scripts/render_body_photo_receipt.py --live-tag-set --id 1 --tag-list "正面,侧面" --chain "..."
python scripts/render_body_photo_receipt.py --live-tag-add --id 1 --tag 背部 --chain "..."
python scripts/render_body_photo_receipt.py --live-tag-remove --id 1 --tag 正面 --chain "..."
# 查询/结果
python scripts/render_body_photo_gallery.py --days 30 --chain "..."
python scripts/render_body_photo_gallery.py --start 2026-07-01 --end 2026-07-31 --tag 正面 --chain "..."
python scripts/render_body_photo_compare.py --id1 1 --id2 2 --chain "..."
python scripts/render_body_photo_gif_result.py --tag 正面 --days 90 --chain "..."
# 底层 CLI(纯写/纯查,供 live 渲染器内部调用)
python scripts/body_photo_tracker.py add photo1.jpg --tag 正面
python scripts/body_photo_tracker.py list --days 30 --tag 正面 --date-from 2026-07-01 --date-to 2026-07-31
python scripts/body_photo_tracker.py delete 1
python scripts/body_photo_tracker.py tag 1 正面,侧面
python scripts/body_photo_tracker.py tag-add 1 背部
python scripts/body_photo_tracker.py tag-remove 1 正面
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
| 档案/身高/年龄/活动量/基础信息/设活动量/改档案/查档案 | 🛠 基础信息 |

### Step 2:域内精确匹配

在已识别的域内,按触发词速查表精确匹配唤醒词,执行对应 CLI。

### Step 3:歧义消解

| 歧义场景 | 判断规则 |
|---------|---------|
| "查热量" vs "查热量趋势" | 前者是搜索食品库,后者是分析模块 |
| "记运动" vs "查运动记录" | "记"=新增,"查"=查询 |
| "记吃的" vs "改吃的" | "记"=新增,"改"=修改已有记录 |
| "记体重" vs "看体重目标进度" | "记"=新增记录,"看"=查询进度 |
| "定训练计划" vs "落地训练" | 前者是对话制定,后者是执行到当天 |
| "查食物排行" vs "查高热量榜" | 前者默认高热量,后者显式指定 |
| "定营养目标" vs "定体重目标" | 营养=calorie/protein/carbs/fat/water_goal 5 字段;体重=weight_goal+deadline 2 字段 |
| "查食物排行" vs "查高热量榜" | 前者默认高热量,后者显式指定 |
| "记身材照" vs "查身材照" | "记"=新增,"查"=查询 |
| "改照片标签" vs "加照片标签" vs "删照片标签" | 改=覆盖整套(可多个);加=追加(判重);删=移除(至少保留 1 个) |
| "生成身材照GIF" vs "对比两张照片" | 前者=动态(多张合成 GIF);后者=静态(两张并排) |
| "我的身材照" | 默认 → 查身材照(浏览);若用户说"记我的身材照"则 记身材照 |
| "设置档案" vs "改档案" | 设置=填全量 4 项(采访式引导);改=单字段/多字段修改,走 `profile update --field` |
| "设活动量" vs "改档案(活动量)" | 设活动量=只改活动量 1 项(走 `profile activity`);改档案=可同时改多项 |

---

## AI 触发场景详述

**所有 CLI 路径前缀**:`python scripts/`

### 🍚 饮食记录:记一餐(v1.0 · 2026-08-02)

**完整流程(重要)**:

#### Step 1:解析用户输入
提取:食物名、克数(如有)、备注(如有)、日期(补记时)

#### Step 1.5:同餐多食物判定(issue #158 · 2026-08-09)
用户一句话包含 **≥2 个食物且属同一餐** 时(用「和 / 、/ 同时 / 一起 / 都」连接),**必须合并为 1 个回执**:
- 每个食物先走 Step 2/3 查库确认营养(可复用查询,不必逐条重新问)
- 全部确认后,**一次调用** `--live-diet-batch-meal`,传入同餐 JSON(每项一个食物,同 date/time):
  ```
  python scripts/render_crud_receipt.py --live-diet-batch-meal --input <json> --chain "1.解析→2.查库→3.同餐批量写库→4.合并回执"
  # json 示例(同餐 N 食物):
  # [{"food_name":"米饭","grams":200,"calories":232,"protein":4.3,"carbs":50,"fat":0.5},
  #  {"food_name":"清蒸鱼","grams":150,"calories":165,"protein":28,"carbs":0,"fat":6}]
  ```
- **禁止**逐食物调用 `--live-diet-add`(那是 N 个回执,issue #158 根因)
- 跨餐(「然后 / 之后 / 又 / 再」分隔)仍分别回执;用户显式说「一个一个回」→ 尊重,逐条回

#### Step 2:模糊查询 nutrition_products 表
执行:`python scripts/calorie_tracker.py search-product <食物名>`

#### Step 3:根据查询结果分流

**Path A:找到匹配结果(≥1条)**
```
列表显示 → 用户选择 → 确认克数 → 计算热量/100 × 克数
→ 执行 render_crud_receipt.py --live-diet-add <食物> <热量> <蛋白> [碳水] [脂肪] [克数] [备注] --chain "1.解析→2.写库→3.回执"
→ 生成回执 HTML(食物/克数/营养 + 餐别 + 时间 + 今日累计 vs 目标)
```

**Path B:库中没找到,用户提供了营养成分表图片(拍营养表记一餐)**
```
调用 mmx vision describe 识别图片:
  mmx vision describe --image <图片路径> \
    --prompt "请识别这张营养成分表,提取:产品名称、品牌、热量(千卡)、蛋白质(克)、脂肪(克)、饱和脂肪(克)、碳水化合物(克)、糖(克)、膳食纤维(克)、钠(毫克)。请以JSON格式返回。"
→ render_nutrition_label.py --ai-json <json> 展示确认向导(wizard)
→ 用户确认 → add-product 存库 → 继续 Path A
```

**Path C:库中没找到,用户无法提供营养成分表**
```
讨论估算克数 → mmx search 查询参考数据:
  mmx search query --q "<食物名> 营养成分表 每100克热量"
→ 用户确认 → 标注估算来源 → 执行 render_crud_receipt.py --live-diet-add(参考数据不存库)
```

#### Step 4:回执 HTML(写库契约)
```
✅ 记一餐回执 HTML:食物名/克数/热量/蛋白/碳水/脂肪 + 餐别 + 时间 + 今日累计 vs 目标
(由 render_crud_receipt.py --live-diet-add 生成,含 --chain 思考链)
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

### ⚖️ 体重:记体重 / 查体重历史 / 查体重趋势 / 对比体重 / 查体重波动

- **记体重**:`python scripts/calorie_tracker.py weight <体重> [--note '<备注>']`(2026-07-20 改:身高从 user_profile 自动读;note 强制 --note 标志)
- **改体重记录**:`python scripts/calorie_tracker.py weight-update <ID> [--weight <公斤>] [--note <备注>]`(2026-07-20 改:--height 已删除,身高只能从 profile 改)
- **查体重历史**:`python scripts/calorie_tracker.py weight-history [天数]`
- **查体重趋势**:`AI 路由(Python API): weight_analysis(start, end, 'trend')`
- **对比体重**:`AI 路由(Python API): weight_analysis(start, end, 'compare', compare_start, compare_end)`
- **查体重波动**:`AI 路由(Python API): weight_analysis(start, end, 'volatility')`
- **定体重目标**:`AI 路由(Python API): set_weight_goal(weight_goal, deadline)`
- **看体重目标进度**:`AI 路由(Python API): weight_analysis(start, end, 'milestone')`

### 🏃 运动:39 场景(2026-08-02 · ticket #5)

> **完整流程(v1.0)**:
>
> #### Step 1:识别场景
>
> | 用户说法 | 唤醒词 |
> |---|---|
> | "刚跑了 5 公里" / "做了运动" | 记运动 / 记有氧运动 |
> | "练了深蹲 3 组 60kg" / "记力量" | 记力量训练 |
> | "走了 8000 步" / "通勤走路" | 记日常活动 |
> | "补记前天游泳" / "昨天没记" | 补记运动 / 批量补记运动 |
> | "把昨天的运动复制到今天" | 复制昨日运动 |
> | "改一下昨天那跑步" / "把 7 月 1 日的运动都改掉" | 改运动记录 / 改某日运动 |
> | "删掉那条骑行" / "删 7 月 2 日的运动" / "删最近一周的运动" | 删运动记录 / 删某日运动 / 批量删运动 |
> | "今天练得够不够" / "本周运动怎么样" | 看今日运动（vs 目标）/ 看本周运动（vs 目标） |
> | "看看我这周运动" / "近 30 天运动" | 看本周运动 / 看最近 30 天运动 |
> | "力量训练总结" / "有氧训练总结" | 看力量训练总览 / 看有氧训练总览 |
> | "运动复盘本周" | 运动复盘（本周） |
>
> #### Step 2:按场景执行
>
> **写类(记/改/删)**:`python scripts/render_exercise_receipt.py --live-<op> ... --chain "1.解析意图→2.写库→3.生成回执"`(写库 + 回执 HTML 一体;--chain 必传,不传/无效 → CLI 报错 exit 2)
> - 记运动/记运动（含备注）/记有氧运动 → `--live-add`;记力量训练 → `--live-add-strength`(每组一行);记日常活动 → `--live-add-daily`
> - 补记运动 → `--live-backfill`(同日同类型自动标冲突提示);批量补记 → `--live-batch-add`;复制昨日 → `--live-copy`
> - 改运动记录 → `--live-update --id <ID> --field <X> --value <Y>`(可多对);改某日 → `--live-update-day --date <D>`
> - 删运动记录 → `--live-delete --id <ID>`(软删除 + 快照);删某日 → `--live-delete-day`;批量删 → `--live-delete-range`
>
> **看类(明细/汇总)**:`python scripts/render_exercise_summary.py --mode records|summary <窗口> --chain "1.识别唤醒词→2.读DB→3.渲染报表"`(--chain 必传)
> - 窗口:--today / --yesterday / --week / --last-week / --month / --last-month / --days 7|30|60|180|365(--downsample 3|week)/ --from <F> --to <T>
> - 筛选:--category 力量|有氧 / --has-note / --type
>
> **达成视图**:`python scripts/render_exercise_goal_view.py --period today|week --chain "..."` — 未设运动目标时输出空状态,AI 必须先问用户「每天运动消耗目标(卡)」并写库(`INSERT OR REPLACE INTO daily_goal (id, exercise_goal, updated_at) VALUES (1, <目标>, CURRENT_TIMESTAMP)`),再重新渲染
>
> **分析/复盘**:`render_exercise_strength.py` / `render_exercise_cardio.py` / `render_exercise_trend.py` / `render_exercise_recap.py --period week|month|90d|year|range` / `render_exercise_distribution.py --mode distribution`(全部 --chain 必传)

#### 🎯 运动 AI 路由规则(必读 · 2026-06-29 扩展,2026-08-02 保留)

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

### 🏋️ 健身计划(29 场景 · 2026-08-02 ticket #6 落地)

**看训练计划(7)**:看本周/下周/上周/指定周计划 = `python scripts/render_workout_plan.py --mode week --week <N>`(N 由当前周推算:本周=当前,下周=N+1,上周=N-1);看今天练什么 = `--mode today`(接 exercise_log 实时完成);看计划概览 = `--mode overview`;看计划 vs 实际 = `--mode vs --start <D1> --end <D2>`
- **循环计划周次语义**:加/改动作默认作用于**所有周**(填空明确时才按指定周);看周计划时 `--week` 必须传用户想要的周次

- **定训练计划**:AI 4 轮对话制(目标/经验/频率/部位)→ 产出 JSON → 预览(`render_plan_builder.py --mock <plan.json>`)→ 确认后写库(`render_plan_receipt.py --live-plan-set --plan-json <JSON> --chain "..."` → 回执)
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
    → 生成预览 HTML(render_plan_builder.py --mock <plan.json>)给用户看,确认后 write_plan() 写库 + 回执
  ```
- **复制训练计划**:整计划 = `render_plan_receipt.py --live-plan-copy [--new-title <T>] --chain "..."`(底层 `plan_generator.copy_plan`,单计划模型另存新标题)→ 回执
- **定休息日**:用户说"周X休息" → `render_plan_receipt.py --live-plan-rest --week <W> --day <D> --rest <1|0> --chain "..."`(底层 `plan_generator.update_session`)→ 回执显示改前/改后
- **加训练动作**:定位 (week, day) → `render_plan_receipt.py --live-plan-add --week <W> --day <D> --name <动作> --sets <N> --chain "..."`(底层 `plan_generator.add_session`)→ 回执。**默认所有周都加**(用户指定"第 N 周"才限单周)
- **定一周计划**:用户给"周一胸、周三腿…" → AI 解析为 7 天安排 → 空天 = 休息 → `render_plan_receipt.py --live-plan-set-week --week <W> --days-json <JSON> --chain "..."` → 回执
- **改训练计划**:config 字段(标题/总周数/开始日期/描述)= `render_plan_receipt.py --live-plan-update --field <X> --value <Y> --chain "..."`;改 start_date 会影响周次计算,回执须提示
- **改某天训练**:定位日期 → 当天 sessions 现状 → `render_plan_receipt.py --live-plan-update-day --week <W> --day <D> --session <S> [--label <L>] --chain "..."` → 回执改前/改后
- **删某天训练**:先查当天快照给用户确认 → `render_plan_receipt.py --live-plan-delete-day --week <W> --day <D> --chain "..."`(底层 `plan_generator.delete_day`)→ 确认回执
- **改动作**:定位 (week, day, session) 内旧动作名 → `render_plan_receipt.py --live-plan-update-movement --week <W> --day <D> --session <S> --old-name <A> --new-name <B> --chain "..."` → 回执。**默认所有周都改**
- **撤销训练计划**:先给用户看计划概要(标题/总周数/起始日)确认 → `render_plan_receipt.py --live-plan-delete --chain "..."`(底层 `plan_generator.delete_plan`)→ 删除回执 + 提示"可用定训练计划重新制定"
- **计划复盘（本周/本月/全部）**:`python scripts/render_exercise_review_html.py`(本周=`--days 7`,本月=`--start <月初> --end <今天>`,全部=`--start <计划起始> --end <今天>`),数据来自 `exercise_review.py`(含完成率/训练日/消耗/异常)
- **看计划完成率**:`python scripts/render_workout_plan.py --mode completion`(每周完成率)
- **看未完成训练**:`python scripts/render_workout_plan.py --mode missed --days <N>`(默认 28)
- **看动作完成率**:`python scripts/render_workout_plan.py --mode movement --days <N>`(默认 28)
- **扫禁忌**:`python scripts/render_contraindication.py [--part {腰|膝|肩}]`(默认 all,输出禁忌动作 + 替代建议 HTML)
- **复盘训练**(旧词已并入计划复盘):`python scripts/exercise_review.py [--start <DATE> --end <DATE>] [--today] [--yesterday] [--day-before-yesterday] [--days <N>]` → 对 [start, end] 范围内每一天做 plan vs 实绩对比(完成率 / 漏做 / 超额 / 异常)。AI 路由负责解析"今日/昨天/前天/这周/X-Y"等口语化时间 → `--start` / `--end`。
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
  使用场景:晚上 10 点卡路里同步 → 触发"落地到本周末" → 看 plan vs 实绩差距 → 决定要不要改训练计划。
  ```
- **落地训练**:将指定日期的训练计划落地到作息/备忘/训记三个系统。执行必须全部完成三步,逐 session 独立执行,某条失败跳过继续。**落地前逐动作跟用户确认(做了吗/重量/组数,可跳过/替换),确认后调 `python scripts/sync_plan.py --days 1`;落地到本周末/月底 = `sync_plan.py --days <N>`(N=到周日/月末的天数,今天已是边界则只落地今天)。进度 HTML = render_process_progress.py 注入 4 步结果(已补计划/已记心愿/已推送/已回写)。**
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

- **落地到本周末 / 落地到本月底**(旧词"卡路里同步"已并入):批量落地 N 天(含飞书日历 + 心愿 + 训记推送)+ 训记回写。
  2026-07-20 改:一键脚本(sync_plan.py)封装 4 步,加 `--start-offset` 默认 0=今天;
  Step 4 训记回写默认 `--days 1`(只回写今天已打勾的;周末补练用 `--backfill-days 3`)。
  **N 的计算**:落地到本周末 = 今天到周日天数;落地到本月底 = 今天到月末天数;今天已是周日/月末 → N=1(只落地今天)。

  **快捷命令(2026-07-20 新增,推荐)**:
  ```
  bash scripts/sync_plan.sh              # 一键 4 步,无需手工拼装
  bash scripts/sync_plan.sh --start-offset 1   # 从明天起 3 天
  bash scripts/sync_plan.sh --days 7           # 推 7 天而非默认 3 天
  ```
  把跨 4 个工具的拼装下沉到脚本里,避免每次 AI 重新组装 + 漏步骤。

   **手动流程(仅 AI 路径没装好 sync_plan.sh 时用)**:
  ```
  前置:KEY 检查同「落地训练」Step 4
    检查 XUNJI_TRAINS_KEY(优先,兼容 XUNJI_API_KEY)。
    未配置 → 调 `python scripts/xunji_bridge.py key status` 让用户看状态,
            再用 `python scripts/xunji_bridge.py key set <KEY>` 设置。
            KEY 申请:训记 App → 我的 → 设置 → 第三方接入。

  Step 1 · 批量落地(按天循环,顺序执行)
    默认从今天起 3 天(--start-offset 0, --days 3;用户可改)。
    对每天调「落地训练」完整流程(补计划+记心愿+训记推送 3 步,不能跳)。
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

- **拉训记实绩**(旧词"回写训记"已并入):`python scripts/xunji_bridge.py backfill [--date <DATE>] [--days <N>]` → 拉训记数据回写 exercise_log(幂等)。
  ```
  行为:
    调训记 fetch(include_full_data=true)
    → xunji_adapter.py 解析 → upsert_exercise_log
    → 幂等键:xunji_localid + set_index(同组不会重复写)
    → 自动取最新体重推算热量

  参数:
    --date <DATE>  单日(默认今天)
    --days N           范围 [date-N+1, date](默认 1)

  前置:KEY 检查同「落地训练」Step 4(XUNJI_TRAINS_KEY)

  使用场景:
    - 「落地训练/落地到本周末」Step 4 自动调(--days 1,只回写今天打勾的;
      如果用户在周末补练一次,再手动 --days 3 把周末 3 天补回来)
    - 晚上 6 点已同步过、8 点又有新训练 → 「拉训记实绩」单独跑(--days 1)
    - 周末补练漏写 → 「拉训记实绩 --date <DATE> --days <N>」(回看 N 天)

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

- **同步到训记**(落地 Step 3 单做):把某天的计划推送到训记 App。**前置:审计动作名**——推送前先检查 plan 里的动作名训记能否识别。
  ```
  Step 1 · 审计动作名(前置校验)
    调 `python scripts/audit_plan_names.py --strict`(扫描 plan 里非训记官方动作名)。
    有识别不了的动作 → 先告诉用户哪些动作名有问题,等用户决定(改名/跳过)后再推;
    全部可识别 → 继续。

  Step 2 · 推送
    调 `python scripts/xunji_bridge.py push-plan --date <DATE>`(日期默认今天)。
    该命令内部完成(同「落地训练」Step 4):
      1 读 workout_plans 中当天的所有 session
      2 转成训记 res[] 格式(schema_version / client_request_id 幂等键 / movements 只留 name+sets)
      3 调 POST /api_upsert_trains_for_llm_v2
      4 多 session 间自动等 45s(限频)
      5 输出每 session ok/fail 状态,JSON 格式
    ⏱ 约 3 分钟/天。

  Step 3 · 结果汇报
    给用户看同步结果:推了几条、每条成功/失败、哪些动作名有问题。
    ⚠ push-plan 报 ok=true 不够:响应里 res.trains 经常是空数组(训记 v2 API 响应缺陷),
      verified=False 时必须 `fetch --full --date X` 二次确认才能算成功。
  ```
- **训记-覆盖X日的训练计划**(底层工具,非 29 场景唤醒词;AI 在「同步到训记」遇到训记已有同名训练时可选用):用卡路里 plan 覆盖训记某天**已有**训练(localid 已有 + start/end=0,**等同新建语义**)。
  ```
  适用场景:
    - 训记那天的训练已经在(可能手建,可能 push-plan 建过),想用卡路里 plan 同步内容
    - 注意:跟「落地训练」的区别 -- 落地走 push-plan(新建 localid=0),
             本工具走 overlay-plan(更新 localid 已有)
  跟「落地训练」Step 1/2/3 的区别:
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

### 📊 分析:查热量趋势 / 查营养结构 / 查热量缺口 / 查食物排行 / 查运动分布 / 查运动贡献

- **查热量趋势**:`diet_analysis(start, end, 'calorie_trend')` - 工作日 vs 周末 / 合规率
- **查营养结构**:`diet_analysis(start, end, 'macro_ratio')` - 蛋白/碳水/脂肪占比
- **查热量缺口**:`diet_analysis(start, end, 'deficit_analysis')` - 饮食 vs 运动贡献
- **查食物排行**:`diet_food_ranking(start, end, category)` - category 可选:high_calorie / low_calorie / frequent / high_carb / high_protein
- **查运动分布**:`exercise_analysis(start, end, 'type_breakdown')` - 消耗/频次/时长占比
- **查运动贡献**:`exercise_analysis(start, end, 'deficit_contribution')` - 运动对缺口贡献

### 🛠 基础信息:设置档案 / 设活动量 / 改档案 / 查档案

> **采访式引导规则(2026-08-02 落地 · 设置档案)**:用户只说部分信息时,AI 必须逐项询问补齐(身高/年龄/性别/活动量),并根据用户日常活动情况推荐活动量档位(久坐/轻度/中度/活跃/高度活跃),说明推荐理由;活动量影响 TDEE 系数(1.2/1.375/1.55/1.725/1.9),必须展示系数变化与每日消耗影响。

- **设置档案**:`render_crud_receipt.py --live-profile-set --age <A> --gender <G> --height <H> --activity <L>`(写库 + 回执 HTML)
- **设活动量**:`profile activity <level>` - 单字段设置,显示 系数旧→新 + TDEE 影响
- **改档案**:`render_crud_receipt.py --live-profile-update --field <X> --value <Y>`(可多对) - 一次写库生成合并回执,逐字段 改前/改后 + 影响提示
- **查档案**:`render_crud_view.py --entity profile` - 档案字段(含活动量)+ 最新体重 + BMI/BMR/TDEE(含系数说明)

### 📋 综合:查健康报告 / 查卡路里数据

- **查健康报告**:`dashboard(start, end)` - 四维度综合仪表盘
- **查卡路里数据**:Lint 5 项检查(见下方)

### 🛠 基础信息:设置档案 / 设活动量 / 改档案 / 查档案

**完整流程(2026-08-02 · ticket #8)**:

#### Step 1:识别场景

| 用户说法 | 唤醒词 |
|---|---|
| "帮我设一份档案 / 填下信息 / 身高 175 男 30" | 设置档案 |
| "改活动量为活跃 / 我的活动量是久坐" | 设活动量 |
| "把身高改成 180 / 改一下我的年龄" | 改档案 |
| "看看我的档案 / 我的资料" | 查档案 |

#### Step 2:按场景执行

**设置档案**(采访式引导 = AI 默认交互):
1. 用户信息不全 → 逐项问(身高/年龄/性别/活动量),活动量根据日常情况推荐(久坐/轻度/中度/活跃/高度活跃)并说明理由
2. 信息齐 → 调 `render_crud_receipt.py --live-profile-set --age <A> --gender <G> --height <H> --activity <L> --chain "1.解析意图→2.写库→3.生成回执" --reason "推荐理由"`(写库 + 回执 HTML 一体;--chain/--reason 必传,reason=活动量推荐依据)
3. 回执 HTML(呈现:身高/年龄/性别/活动量 + 设置时间;已存在档案时含改前/改后)

**设活动量**:
1. 调 `render_crud_receipt.py --live-profile-activity <level> --chain "1.解析意图→2.写库→3.生成回执" --reason "映射依据"`(写库 + 回执 HTML,level ∈ sedentary/light/moderate/active/very_active;--chain/--reason 必传,reason=语义→档位映射依据,如 运动量很大→活跃)
2. 回执 HTML(呈现:活动等级 + 影响(TDEE 系数旧→新)+ 对每日消耗影响)

**改档案**:
1. 先确认当前旧值(`profile get`)
2. 调 `render_crud_receipt.py --live-profile-update --field <X> --value <Y> --chain "1.解析意图→2.写库→3.生成回执"`(可追加多对 --field/--value,一次写库生成一个合并回执 HTML;--chain 必传)
3. 回执 HTML(呈现:改前/改后对比 + 影响提示:改身高→BMI 重算,改活动量→TDEE 系数变化)

**查档案**:
1. 调 `render_crud_view.py --entity profile --wake-word 查档案 --chain "1.识别唤醒词→2.调CLI读DB→3.算BMI/BMR/TDEE"` → HTML(呈现:档案字段含活动量 + 最新体重 + BMI/BMR/TDEE 含系数说明)
2. **--chain 强制规则(2026-08-02 拍板)**:渲染类场景 **必须** 传 `--chain`(AI 实际处理步骤)与 `--wake-word`;不传/传无效 → CLI 报错退出(exit 2)。未传 = AI 未按流程执行,行为不可控。思考链不进 UI,用户点「复制日志」带出用于排障对比

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
