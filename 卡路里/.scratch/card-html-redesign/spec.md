---
Status: ready-for-agent
Slug: card-html-redesign
Created: 2026-07-28
Source: /grilling session 2026-07-28 · issues 一-七 · 14 个子决策
---

# 卡路里 HTML 重设计 · Spec

> 第一性原理(贯穿全文)
>
> 1. **三支柱模型**: 卡路里 = 记录 / 查询 / 复盘,UI 全部 Apple 设计语言。
> 2. **One wake word → one intent → one output shape**。重复 = 合并信号。
> 3. **HTML = canvas;数字必须说话**。每个数字要么 self-explanatory 要么配句子。
> 4. **Mobile-first**。大部分用户在手机上开卡路里。
> 5. **SoT 链**: data layer(`_triggers.py`, DB)> presentation layer(`templates/*.html`)> generated artifacts(`<skill>.html` mirror at root)。根镜像 = 最新 render。

## Problem Statement

当前卡路里技能 7 类 HTML 缺陷,影响日常使用与数据可信度:

- **HELP HTML(`<skill>_HELP`)** — 复制按钮埋在 L3 内层;prompt 没有"填字段提示";hero 字号小;`卡路里.html` 根镜像 ≠ HELP 渲染最新版,SoT 漂移。
- **主页 dashboard** — "缺口 -1640 卡/日" 含义不清;快捷命令是 script 而非 prompt;mobile 上 HH:MM:SS 与 食物名 重叠;今日待办 信息密度低。
- **记吃了** — AI 跳过 verify step 直接写库;`600ml` 误识别为 `600g`;无食品库匹配步骤。
- **今日饮食** — 默认跨多日(3 天),与 wake word "今天" 语义冲突;无 mobile 适配;顶部 4 KPI 涵盖不全(含饮水但忽略 碳水/脂肪)。
- **查吃的记录** — 与 查今天吃 重叠,wake word 重复;`--date` 不支持,`--start/--end` 体验差。
- **热量趋势** — 浮点精度泄漏(`-141.6550000000002`,`2905.255` 等);4 大模块 mobile 全坏(曲线被拉、表格超出、底部文字挤压)。
- **查今天喝水** — text-only 回执,无视觉反馈(`<system-reminder>` 提示设计约束,用户感受受限)。

## Solution

3 个架构决策(ADR-0001/0002/0003)+ 14 项实现细节,围绕"single-source-of-truth + mobile-first + number-literacy"三轴重塑。

- 把根目录 `<skill>.html` 重定义为 `_triggers.py` + `templates/help_center.html` 的最新 render 重命名(退役 SKILL.md 镜像契约)。[**ADR-0001**]
- 合并 `查今天吃` 与 `查吃的记录` 为单一 wake word `查今天吃`(单日默认)。[**ADR-0002**]
- 为 `查今天喝水` 新增 HTML 模板(进度环 + 周小图),§04 决策矩阵 `❌` → `✅`。[**ADR-0003**]
- 复制按钮下沉到 `.word-card > summary` 可见层;每个 TRIGGER 加 `fill_hints` 字段在 prompt 尾部追加填空提示。
- 主页 4 个 KPI 卡片全部自解释(其中 缺口 加 size_label badge + math breakdown);快捷命令改用 `_triggers.py` 的 prompt 文本;`.log-row` 收紧 mobile 列宽与 overflow 兜底。
- 今日饮食 顶部 6 KPI(新增 总碳水/总脂肪);mobile 单列堆叠 + `table-wrap` overflow。
- `render_calorie_trend.py` 后端 round 浮点精度;HTML `@media (max-width: 640px)` 全面收缩。
- 记吃了 prompt body 显式声明"食品库查询 → 展示营养 → 用户确认 → 写库"的 4 步流程。

## User Stories

### A. 卡路里 user(本人)

1. As a user opening 卡路里根目录的 `卡路里.html`, I want it to be the latest render of the wake-word lookup table, so that I don't see stale SKILL.md-mirrored content.
2. As a user opening the wake-word lookup, I want each wake word's copy button to be visible at the summary level (not buried inside expand-to-detail), so that copying takes 1 click.
3. As a user after copying a prompt, I want the prompt to end with a fill hint (e.g. `食物名称为: `), so that I know exactly what to type before sending.
4. As a user reading the hero region of the wake-word lookup, I want the title font, stats font, and subline to be large enough on both desktop and mobile, so that the page doesn't feel cramped.
5. As a user opening the home dashboard, I want the 缺口 KPI to display the math that produced the number (TDEE + 运动 vs 摄入), so that I understand my deficit direction.
6. As a user on a phone opening the home dashboard, I want the recent-records list (time + 食物名 + 热量) to fit without overlap, so that each row is fully readable.
7. As a user opening the home dashboard on a phone, I want the 今日待办 list to be compact (label + state icon, no overflowing rows), so that the 4 todo items fit on one screen.
8. As a user copying a "quick command" from the home dashboard, I want it to be a natural-language prompt, so that I can paste it directly into AI chat.
9. As a user with a new food (e.g. `元气森林 冰红茶汽水 600ml`), I want the AI to first show me which fields it extracted and consult the food library, so that I can verify before committing the entry.
10. As a user saying "查今天吃", I want today's food records grouped by meal (single day, today only), so that I'm not surprised by multi-day data.
11. As a user opening the diet view on a phone, I want 6 nutritional KPIs (记录数, 总热量, 总蛋白, 总碳水, 总脂肪, 总饮水) stacked vertically, so that each is readable.
12. As a user opening the diet view, I want the table rows scrollable inside its own section (not the whole page), so that horizontal scroll doesn't break the page.
13. As a user opening the calorie trend, I want every number rounded to 2 decimal places max, so that I never see floating-point precision artifacts.
14. As a user opening the calorie trend on a phone, I want the chart not to be vertically stretched, the KPI grid not to overflow, and the table to fit, so that the page is fully readable on phone.
15. As a user saying "查今天喝水", I want a visual progress ring (and a weekly mini chart) so that I can see at a glance whether I'm on track.
16. As a user with the redesigned `查今天喝水` HTML, I no longer receive `<system-reminder>` saying `此唤醒词不做 HTML`, so that the AI no longer speaks to me as if constrained.

### B. AI agent(协助 loop)

17. As the AI, I want each wake word to map to exactly one render-or-CLI path (no double-routing), so that I don't violate §04 决策矩阵.
18. As the AI, when 记吃了 is invoked, I want the prompt body to dictate a 4-step flow (查食品库 → 展示营养 → user 确认 → 写库) so that I never blind-write.
19. As the AI, I want the home dashboard's quick commands and the wake-word lookup's prompts to share the same data source (`_triggers.py`), so that prompt UI never drifts between surfaces.

### C. Skill developer / maintainer

20. As a maintainer, I want the root-level `卡路里.html` mirror to be auto-updated by the render pipeline (or by a single rename step), so that there is no manual sync burden.
21. As a maintainer, I want two wake words producing nearly identical outputs (`查今天吃` / `查吃的记录`) merged, so that I don't maintain two render scripts and two templates.
22. As a maintainer, I want a programmatic check that every §04 `✅` trigger has a corresponding render script + template, so that the constraint is hard to violate accidentally.
23. As a maintainer, I want a programmatic check that no rendered JSON contains floating-point precision leaks (> 2 decimals) for numeric display fields, so that the trend_value bug class cannot recur.
24. As a maintainer, I want all three ADR files (`docs/adr/0001..0003.md`) written and committed before any code changes, so that future readers see why the migration was decided.

### D. Acceptance / acceptance sub-stories

25. As a user, when I expand a category in the wake-word lookup, the first L1 list sits flush with the hero (no visible gap).
26. As a user on a phone, the home dashboard's KPI grid becomes 2×2 instead of 4×1.
27. As a user on a phone, the home dashboard's quick-commands rows copy the prompt (not the script command).
28. As a user, the calorie trend chart no longer shows `today -141.6550000000002` text — it shows `今天 -142` (integer rounded).
29. As a user, the diet view's top KPI strip is 2 rows × 3 cols on desktop, 6 rows × 1 col on phone.
30. As a developer, `查吃的记录` continues to work as an alias of `查今天吃`, and any stale 3-day default behavior has been removed.
31. As a user, `卡路里.html` at the skill root, when opened, is byte-equivalent to the latest `卡路里_HELP_<TS>.html` (within compressible whitespace tolerance).

## Implementation Decisions

### D1. Architectural Decisions(ADR)

#### ADR-0001 — 卡路里.html is the latest HELP render(退役 SKILL.md 镜像契约)

- Background: 旧 `卡路里.html` 是 SKILL.md 的 101KB 镜像;新版 `卡路里_HELP_<TS>.html` 是 `_triggers.py` + `templates/help_center.html` 的 60KB 渲染。两者并存引起 SoT 漂移。
- Decision: `卡路里.html` = 最新 `卡路里_HELP_<TS>.html` 的拷贝重命名。旧 SKILL.md 镜像契约(`docs/superpowers/specs/2026-07-25-body-metrics-design.md` L23)退役。
- Module changes:
  - 一段 rename 操作随 `render_help_center.py` 跑:`cp` 最新 `卡路里_HELP_<TS>.html` → `<SKILL_DIR>/卡路里.html`(可选:commit hook 触发)。
  - `help_center.html` 模板的 `__data__.summary.by_category` 已成为 hero stats 的展示入口,无需另增字段。
- Trade-off: 失去 SKILL.md 镜像可读性。SKILL.md 本身仍为 markdown SoT,根 HTML 镜像 = 最新 render。
- Reversibility: git revert 可恢复旧 镜像。

#### ADR-0002 — 合并 `查今天吃` 与 `查吃的记录`

- Background: 两个 wake word 输出几乎重叠(均显示今日/近日饮食,只是 UI 略不同)。SKILL.md §触发词速查表 L283-284 与 `_triggers.py`/`templates/*.html` 的 HTML spec 不一致。`render_today_meals.py` 默认 `--days 3` 与"今天"语义冲突。
- Decision: 单一 wake word `查今天吃`,默认今日单日。`查吃的记录` 留作 alias(同 render 脚本)。
- Module changes:
  - `render_today_meals.py` 可退役 或 用于未来"区间查" wake word;`render_today_diet.py` 接过 single-day 渲染。
  - `templates/today_meals.html` 与 `templates/today_diet.html` 可合并为单一模板(共享 partial)。
  - `check_trigger_consistency.py` 增加 alias 校验:`查吃的记录` 必须声明 aliasOf `查今天吃`。
- Trade-off: 默认窗口由 3 天收缩为 1 天。Multi-day view 留待未来 wake word(可显式 `--days N`)。

#### ADR-0003 — `查今天喝水` 加 HTML 模板(§04 `❌` → `✅`)

- Background: §04 决策矩阵把"单日快查"判为 text-only。系统 `<system-reminder>` 提醒 AI 受约束。视觉化需求高(每日多次查),改为 HTML 报告型。
- Decision: `查今天喝水` 与 `查今天吃` 同级(均为 §04 `✅`)。新建 `templates/today_water.html`(进度环 + 今日 ml 数字 + 本周 mini-chart)。
- Module changes:
  - 新 `scripts/render_today_water.py`(输入 DB / food_log 中 food_name='💧水' 的 grams 聚合)。
  - 新 mock fixture `tests/fixtures/mock/mock_today_water.json`。
  - SKILL.md §04 决策矩阵行 更新 `查今天喝水` 单元格。
  - 移除针对 `查今天喝水` 的 `<system-reminder>` 约束(AI 自动遵守新 spec)。
- Trade-off: 多一个 HTML 模板 + render 脚本需维护。日查询频次高,视觉化价值大。

### D2. HELP HTML 层级(layout + content)

- `.word-card > summary` 右侧添加 `.copy-btn.copy-main`(右贴,`margin-left: auto`)。统一复制 main prompt。Variant 级 copy 按钮保留在 L3 内(用户进 L3 后看到多场景)。
- `_triggers.py` 中每个 TRIGGER 加 `fill_hints: [...]` 字段(默认 `[]`)。`_prompt_skeleton(wake, body, variant, fill_hints=[])` 拼接顺序:`head + body + tail + "\n" + "\n".join(fill_hints)`。
- 仅"需要补字段"的 TRIGGER 需填充 `fill_hints`(规则由后续 spec Q1 决策)。其余 TRIGGER 留空。
- Hero 区域 CSS 调整:`h1: 150% → 220%`;`stats: 100% → 115%`;`sub: 100% → 105%`;`.cat-block:first-of-type { margin-top: 2px → 0 }`;hero 与 首 category 背景微连续(去 border,渐变接 bg-card)。

### D3. 主页 dashboard(4 主题)

- **缺口 KPI(自解释化)**:
  - badge = `size_label`("过大" warn, "适中" ok, "适宜" good)。
  - Detail text: `TDEE {BMR} + 运动 {ex_burn} = 应烧 {total_burn} vs 摄入 {intake}`。
  - 修 kg/期 标签 bug:`N=1` 时显示 `理论 X kg(本日)`;`N>1` 时显示 `理论 X kg(N 天) · 折合 Y kg/周`,其中 `Y = X * 7 / N`(由前端 JS 或 后端 round 计算)。
  - 数字符号保留 `avg_deficit` 正向 = 减重方向,符号用 `−`(Unicode),与 label "缺口" 配套。
- **快捷命令**:
  - `.cmd-row .cmd` 改为 `_triggers.py` 中的 prompt 文本(import `_triggers` 后按 wake_word 查找 `main_prompt.text`)。
  - `render_home.py` 增加 `quick_actions` 数据组装逻辑:从 `_triggers` 取 prompt,作为 `quick_actions[i].prompt`(替换原 `a.command`)。
  - `.copy-mini` 把 `a.prompt` 写入剪贴板(原写 `a.command`)。
- **`.log-row` 改 overflow 收紧**:
  - 一套 CSS 通用(mobile & desktop):`grid-template-columns: 44px 1fr auto; gap: 10px`。
  - time 显示 HH:MM(后端保留 HH:MM:SS;前端 `time.slice(0,5)`)。
  - `.log-row .name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }`。
  - `.log-row .time, .log-row .cal { white-space: nowrap; font-variant-numeric: tabular-nums; }`。
- **`.todo-row` 紧凑 + 右贴 state icon**:
  - padding `14px → 11px`,label `15px → 14px`,meta `12px → 11.5px`,check `22px → 20px`。
  - 新增 `.state`(默认 green dot for done / hollow for pending;priority badge 仍可叠加)。
  - meta 文案简化(可选):"已记录 12 条" → 与 state icon 共占一行(由后续 spec Q4 决定是否合并)。

### D4. 今日饮食 模板(KPI 6 化 + mobile)

- 顶部 KPI 数量从 4 改 6:**记录数, 总热量, 总蛋白, 总碳水, 总脂肪, 总饮水**。
- 桌面布局:`grid-template-columns: repeat(3, 1fr)`,2 行。
- 移动 (`@media (max-width: 640px)`) 布局:`grid-template-columns: 1fr`,6 行。
- 日期筛选默认 今日(无"全部"选项;或保留"全部"但加重提示"已显示 N 天")。
- `table` 外套 `.table-wrap`,`overflow-x: auto`;整页 `overflow-x: hidden`。
- `.section padding` 24/28 → 16/20 mobile。

### D5. 热量趋势(精度 + mobile)

- 后端 fix(`render_calorie_trend.py` 中 `summary` JSON 序列化前):
  - `start_avg`, `end_avg`, `trend_value` 全部 `round(2)` 后再写入(避免浮点 imprecision 落到前端)。
  - `series[i].calorie` 同样 `round(2)`(保持全库小数 ≤ 2 位)。
  - `trend_value` 若是 `-141.6550000000002`,后端截为 `-141.66`。
- 前端 `chart` SVG 渲染可继续使用 raw 值(精度不显示);表格 `tr:nth-child(n) td.num` 全部 `font-variant-numeric: tabular-nums`。
- 移动 CSS:
  - `.kpi-grid` 4 列 → 2 列。
  - `.section padding 24/28 → 16/20`。
  - `.table-wrap` overflow-x:auto。
  - `svg height 220 → 180`(`preserveAspectRatio` 保留)。

### D6. 记吃了 prompt body(4 步流程)

`_triggers.py` 中 `main_prompt` body 改写(同时调整 aliases / variants 的 prompt 一致):

```
我刚吃了一顿,需要写进 food_log。

AI 流程:
1. 在食品库查询食物名(如 "元气森林 冰红茶汽水")。
2. 若命中:展示营养数据(每 100g 的热量/蛋白/碳水/脂肪),等我确认后写库。
3. 若无命中:区分单位(ml vs g),如必要请我提供克数或包装营养数据,标注估算来源。
4. 完成后给 1 句话总结,不需要过多文字解释。
```

不开 HTML 回执(§04 `❌` contract 保留)。Text-only 设计不变。

### D7. 跨页面一致性(SoT)

- `render_home.py` import `_triggers`(同 source-of-truth for prompts)。
- `help_center.html` / dashboard quick actions / 未来 command palette 共享 `_triggers` 单一数据源。
- `scripts/check_prompt_quality.py` 增加 cross-file 检查:同一 wake_word 在 `_triggers.py` / `SKILL.md` / `templates/*.html` 三处的 prompt 文本应一致。

## Testing Decisions

### 测试 seam 架构(从高到低)

1. **End-to-end HTML render**(highest seam):外部命令启动 render 脚本,用 mock JSON 输入,断言生成 HTML 文件存在 + 文件大小合理 + 用轻量 HTML parser(如 BeautifulSoup)验证关键 DOM 节点(`.copy-btn`, `.kpi-grid`, `.ring`, `.todo-row` 等)。
2. **JSON data-shape assertion**(mid seam):从渲染 HTML 抽取 `<script>window.__DATA__ = {...}</script>`,parse 后断言 schema + decimal precision + 关键字段非空。
3. **§04 决策矩阵一致性**(low seam):`check_trigger_consistency.py` 扩展为 `scripts/check_decision_matrix.py`,扫描 §04 表格 + 对应 render 脚本 + 模板文件存在性 + mock fixture 存在性。
4. **小数精度巡检**(lowest,新增):`scripts/check_decimal_precision.py` 扫描 `calorie_html/` 下所有生成 HTML,parse JSON,断言数字字段小数位 ≤ 2。

### 现有测试先例(prior art)

- `tests/test_write_contract.py` —— 验证写库子命令的 stdout 契约。本次新增 `tests/test_redesign.py` 复用该 pattern:对每个 affected wake word 写一组 mock,run render script,assert JSON shape。
- `tests/fixtures/mock/` 已有 23 个 fixture(JSON)。本次新增 `mock_today_water.json`(ADR-0003)。
- `scripts/check_trigger_consistency.py` —— 3 边单向对照。扩展为 4 边:add "对应 mock fixture 存在"。

### 什么是"好测试"

- 仅断言外部行为(rendered DOM / parsed JSON shape),不测内部 Python 函数。
- mock fixture 是 render 脚本的可独立验证输入(必须已存在,未过期)。
- 任何 numeric field 都要有显式 `precision assertion`(避免 `-141.6550000000002` 类回归)。

### 哪些模块需测试

- ADR-0001 触发:rename 步骤(独立 shell test)。
- ADR-0002 触发:`查吃的记录` alias 解析(decision matrix check)。
- ADR-0003 触发:`render_today_water.py` 单元测试 + 模板渲染断言。
- Issue 一 / 二 / 三 / 六 的所有 UI/CSS/数据流改动,在 HTML 渲染测试里覆盖。

## Out of Scope

- 数据库 schema 变更(无 migration)。
- 新增 wake word(超出 3 个 ADR)。
- 跨技能教学 — 用户在 issue 七 提到的 `xxxxxx 技能 学习 卡路里 HELP`(被用户明确告知放弃)。
- Web / Cloud 部署(保持 CLI + 本地 HTML 输出)。
- 离线模式改动 — 沿用 `find_db_path` 路径查找逻辑。
- 新营养维度(维生素、钠、纤维等)— 6 KPI 包含总脂肪/总碳水足够,新增维度推迟。
- 国际化(i18n)— 所有 prompt 与 UI 文案默认中文,英文 i18n 推迟。
- AI agent prompt template 工程化(把 SKILL.md 全文拆给模型)—— 这次 spec 仅 §04 决策矩阵 / 路径。

## Further Notes

### 第一性原理(贯穿 spec)

1. **三支柱**:记录 / 查询 / 复盘 = 三个出口。HTML 化查询与复盘。
2. **One wake word → one intent → one output shape**。重复 = 信号合并(查今天吃 / 查吃的记录)。
3. **HTML = canvas;数字必须说话**。每数字要么 self-explanatory 要么配句子(缺口、kg/期 都是反例)。
4. **Mobile-first**。所有 KPI / table / chart 须 ≤ 640px 适配。
5. **SoT 链**:data layer > presentation layer > generated artifacts。Root mirror = 最新 render。

### Migration plan(commit order)

1. 写 3 ADR 到 `docs/adr/0001-help-html-as-root-mirror.md` / `0002-diet-wake-words-merge.md` / `0003-water-html-first.md`。
2. ADR-0003 实现(`templates/today_water.html` + `render_today_water.py` + §04 行 cell 更新)。
3. ADR-0002 实现(查吃的记录 alias + render_today_meals 退役 / 复用)。
4. ADR-0001 实现(rename 步骤,集成进 render pipeline)。
5. HELP HTML 布局改动(`.copy-btn` 进 summary, `fill_hints` 字段, hero 字号)。
6. 主页 dashboard 视觉 4 主题(缺口 / 快捷命令 / log-row / 今日待办)。
7. 今日饮食 6 KPI + mobile + alias 同步。
8. 热量趋势 精度 + mobile。
9. 记吃了 prompt body 改写。
10. 重新生成所有 `calorie_html/*<TS>.html` snapshot,确认无 stale 副本。

### Risk & Reversibility

- ADR-0001:`git revert` 可恢复旧 镜像;无数据丢失。
- ADR-0002:`查吃的记录` 作 alias,用户已 保存 prompt 仍能跑。默认窗口 收缩 是 设计 choose。
- ADR-0003:`<system-reminder>` 取消可能让某些 AI 行为偏离 → 由 `check_decision_matrix` 守护。

### Open questions(parked for follow-up tickets)

- Q1. `_triggers.py` 中 `fill_hints` 是否独立字段,或合并进 `body`?
- Q2. 重命名后的 `卡路里.html` 根镜像是否也包含 dashboard quick-actions 摘要(类似 iOS App Switcher)?
- Q3. `today_diet` / `today_meals` 模板彻底合并,还是 partial 共享?
- Q4. `.todo-row` meta 文案("已记录 12 条")是否完全 删,仅靠 state icon 表达?

### Acceptance gates

- `pytest tests/test_redesign.py` pass。
- `scripts/check_decision_matrix.py` exit 0。
- `scripts/check_decimal_precision.py` exit 0。
- 9 份现有 HTML(`卡路里_HELP_*`, `主页仪表盘_*`, `今日饮食_*`, `热量趋势_*`)经 review 后符合 spec。
- 用户在桌面端 + 移动端(iOS Safari, Android Chrome)各做一次 happy path 走查。

## Comments
