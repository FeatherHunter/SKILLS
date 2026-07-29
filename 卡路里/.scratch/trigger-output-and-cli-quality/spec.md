---
Status: ready-for-agent
Slug: trigger-output-and-cli-quality
Created: 2026-07-29
Source: /grilling session 2026-07-29 · 9 decisions · covers 6 user-reported issues
Supersedes: (none)
Related: .scratch/card-html-redesign/spec.md (complementary, this spec covers CLI/data; that one covers dashboard/diet/calorie-trend visuals)
---

# 卡路里 · Trigger 输出与 CLI/数据质量重建 · Spec

> 第一性原理(贯穿全文)
>
> 1. **Symptom ≠ root cause**。Issue 6 表面是"AI 说错",根因是 CLI 无校验 + AI 无验证协议 — 修一处不够。
> 2. **Default ≠ escape hatch**。HTML 是默认(用户实测期望)不等于"不能 text";CLI 标志化是默认不等于"不能 positional" — 都要保留 escape hatch。
> 3. **One seam per concern**。复用 card-html-redesign 的 4 个 seam(HTML render / JSON shape / 决策矩阵 / 精度);只为本 spec 新增 3 个 seam(CLI 校验 / Mobile CSS / 测试隔离)。
> 4. **ADR 三条件**:每个 ADR 必须满足"难逆 + 反直觉 + 真权衡"。本 spec 产出 ADR-0004 ~ 0007。

## Problem Statement

用户实测卡路里技能 6 类问题,影响日常使用、数据可信度与开发循环:

- **CLI 写库零校验** — `weight-goal --help` 把字面值 `'--help'` 当 kg 写进 `daily_goal.weight_goal`;`list-products --help` 触发 `int()` 崩溃;`weight-history --days 1` 触发 `int('--days')` 崩溃。同一类 bug 模式扩散到所有 subcommand。
- **查询类输出碎片化** — `查热量` 返回纯文本表格(32 行塞进 stdout),`查食品库` 默认 LIMIT 50 强迫用户绕 SQL。`查今天喝水` 早被升级到 HTML(ADR-0003)但 `查热量` / `查食品库` 没跟上。
- **Mobile 体验断裂** — `templates/weight_history.html` 没有任何 `@media` 断点(对比 `templates/food_ranking.html:142` 有);`weight-history` / `对比体重` / `查体重波动` 三个 mode 共享这同一模板,4 列 KPI 在手机上被压扁,SVG 固定 260px 高度被拉伸,table 无 `overflow-x:auto` 包装溢出屏幕。
- **生产库被测试数据污染** — 2026-07-27 的 4 条体重记录(note "测试" / "P2 测试" / "P1+P2 测试" / "现状核实")混入真实数据;`weight_log` 表无 `is_test` 列,只能靠 note 关键词区分(脆弱)。
- **AI 断言无验证** — Issue 6 的副因:AI 说"你还没设定体重目标"前没查 DB,凭直觉(或损坏数据)就断言"没设过"。
- **体重波动页架构未成熟** — Issue 5.4 用户原话"整个页面的功能要做更多的开发和头脑风暴" — 现有 4 mode 共用模板、波动可视化(±σ 带 / 异常点色块)、信息层级都未设计。

## Solution

围绕 **4 个 ADR + 5 项落地动作** 重塑:

### ADR(难逆决策)

- **ADR-0004 · CLI 标志化**(Q1)— `daily_goal.weight_goal` 仍存同表,但 `weight-goal` 命令用 `--weight-goal <kg> --deadline <date>` 标志位;positional `weight_goal` 标志彻底消失,杜绝 `--help` 误写。
- **ADR-0005 · 查询类 HTML 默认**(Q2)— 所有"查询类 trigger"(返回 ≥1 行)强制 HTML;text 只用于单条 CRUD 回执 / 单值状态查询 / 嵌入日志。`check_trigger_consistency.py` 升级为强制校验,违反 = 协议 fail mode。
- **ADR-0006 · 测试数据隔离**(Q6)— 引入 `SKILLS_DB_PATH_TEST` 环境变量;测试 fixture 走独立 DB,生产 DB 零测试数据。删除 `weight_log` 中 id 132-135 的 4 条残留测试记录。**不需要 `is_test` 列**。
- **ADR-0007 · AI 验证协议**(Q7)— SKILL.md §⚠️ 强制性规定新增第 7 条:"AI 声称'用户没 X'前必须先 SELECT 验证",附 3 个 fail mode 示例(写脏数据 / 空值误判 / 类型误判)。违反 = 协议 fail mode。

### 落地动作(非 ADR 决策,但 spec 范围内)

- **Mobile 单模板响应式**(Q3)— `templates/weight_history.html` 加 `@media (max-width:640px)` + SVG 高度 `clamp()` + table `overflow-x:auto`。**单一模板同时适配 PC + 手机**,不维护双版本。
- **list-products 默认 200 + `--all`**(Q5)— 默认行数从 50 提到 200;加 `--all` 显式全量;与 Q2 HTML 渲染配合自动分页。
- **体重波动页 v2**(Q8)— 新模板 `templates/weight_volatility_v2.html`,±σ 带可视化 + 异常点色块 + 趋势箭头 + KPI→曲线→异常→解读信息层级。设计冲刺单独进行(不在本 spec batch 1-3 内)。
- **3-batch 落地**(Q9)— P0 防事故 → P1 UX 修复 → P2 架构 / 文档。每 batch ≤3 文件,独立 review。

## User Stories

### A. CLI 用户(直接跑命令的人)

1. As a CLI user, when I type `<command> --help`, I want argparse to print usage and exit code 0, so that I can discover what flags are valid.
2. As a CLI user, when I type `weight-goal 73 2026-12-31`, I want the parser to reject the bare positional arguments with a clear error, so that I learn to use `--weight-goal` and `--deadline`.
3. As a CLI user, when I type `weight-goal --weight-goal abc --deadline 2026-12-31`, I want an immediate type error pointing to `--weight-goal`, so that I don't accidentally write `'abc'` to the DB.
4. As a CLI user, when I type `list-products --help`, I want the help text to appear, not an `int()` traceback, so that I can understand the command.
5. As a CLI user, when I run `list-products`, I want to see up to 200 rows by default, so that I don't have to guess and retry.
6. As a CLI user, when I run `list-products --all`, I want to see every row in the nutrition_products table, so that I can export the full library.
7. As a CLI user, when I run any calorie_tracker subcommand with a bad flag combination, I want a single-line error message naming the flag, so that I can fix my command without reading the source.

### B. 移动端用户(在手机上查数据的人)

8. As a mobile user, when I open 查体重历史 on my phone, I want the 4-column KPI grid to stack vertically, so that each metric is readable.
9. As a mobile user, when I open 查体重历史, I want the chart height to adapt to my viewport, so that it's not stretched to 260px regardless of screen size.
10. As a mobile user, when I open 查体重历史 / 对比体重 / 查体重波动, I want the data table to scroll horizontally inside its own section, so that the page itself doesn't overflow.
11. As a mobile user, when I open 查体重波动 v2, I want to see ±σ bands and anomaly point color-coding, so that I can visually identify outliers without reading numbers.
12. As a desktop user, when I open the same weight_history page, I want to see the full 4-column KPI grid and chart at full width, so that I get more density on a larger screen.

### C. 食品库 / 营养查询用户

13. As a user asking 查热量 "牛肉", I want an HTML card per match with macros and source, so that I can scan 32 results without scrolling terminal output.
14. As a user asking 查食品库, I want an HTML page with all 1924 entries (paginated if needed), so that I don't have to write SQL to bypass a 50-row limit.
15. As a user opening the food library HTML, I want to filter or search by category / brand, so that I can find what I need in 1924 entries.

### D. AI 助手(被 skill 调用的 agent)

16. As an AI agent, when a user asks 查体重目标, I want the skill to enforce that I run a SELECT before claiming "you haven't set a goal", so that I never lie to the user about state.
17. As an AI agent, when a user asks any 查询 trigger, I want the skill to remind me to invoke the HTML workflow (render + open), so that I don't accidentally fall back to text.
18. As an AI agent, when a user asks 查热量 "牛肉" and gets 32 matches, I want the skill to provide a `food_name LIKE '%牛肉%'` HTML list with confidence indicators, so that I can help the user pick the right one.

### E. 开发者 / 测试者

19. As a developer running `pytest`, I want every test to use a temporary test DB via `SKILLS_DB_PATH_TEST`, so that my test data never reaches the production DB.
20. As a developer writing a new test, I want a `conftest.py` fixture that auto-creates and cleans up a test DB, so that I don't have to set up the fixture by hand.
21. As a developer, when I run `python scripts/check_cli_validation.py`, I want a list of subcommands that lack `--help` or `type=*` declarations, so that I know what to fix.
22. As a developer, when I run `python scripts/check_html_responsive.py`, I want a list of HTML templates lacking `@media (max-width:640px)`, so that I know what mobile-breakers exist.

### F. 数据完整性保证

23. As a user with a `daily_goal.weight_goal`, I want it to never be silently overwritten by a CLI typo or `--help` invocation, so that my goal progress calculation stays trustworthy.
24. As a user with test data in my production DB, I want the skill to help me delete it (one-shot cleanup script), so that my analytics aren't distorted.
25. As a user opening a stale HTML template, I want the render script to refresh it with the latest data shape, so that I never see a mismatched UI.

## Implementation Decisions

### 1. ADR-0004 · CLI 标志化(Q1)

- **范围**:`calorie_tracker.py weight-goal` 与所有新增/修改的 subcommand。
- **接口**:从 `weight-goal <kg> [deadline]` 改为 `weight-goal --weight-goal <kg> --deadline <date>`。
- **默认值**:若 `--weight-goal` 未提供,argparse 报 `error: --weight-goal required`(不要回退到 positional)。
- **回退路径**:为不熟悉 flags 的老用户提供 `--legacy-positional` 一次性 escape hatch,带 deprecation warning;3 个月后删除。
- **例外**:`--help` 始终由 argparse 原生支持(只要 subcommand 是 argparse parser,无需额外代码)。

### 2. ADR-0005 · 查询类 HTML 默认(Q2)

- **判据**(机器可验证):
  - "查询类 trigger" = `return code 0` + `stdout 含 ≥1 行数据 + stdout 非回执格式`。
  - "单条 CRUD 回执" = `stdout 含 'id=' + '影响 N 行'`。
  - "单值状态查询" = `stdout 单行单值`。
- **范围**:所有触发器分类见 SKILL.md §触发词速查表。新增 trigger 默认 HTML。
- **强制校验**:`scripts/check_trigger_consistency.py` 升级,从"3 边一致性"扩展为"查询类 ⊆ HTML 模板"硬约束。退出码 1 = 有 drift,CI 必跑。
- **Escape hatch**:`--text` 标志保留 CLI 用户的 text 输出能力(满足"CLI 直接跑"场景)。
- **回退路径**:若 render 脚本缺失,AI 应回退到 text + 推荐补 HTML,不是直接报错(V1.3 §⚠️ 第 4 条已允许)。

### 3. ADR-0006 · 测试数据隔离(Q6)

- **环境变量**:`SKILLS_DB_PATH_TEST`(默认 `<SKILLS_DB_PATH>/test_calorie_data_<pid>.db`)。
- **conftest.py**:`tests/conftest.py` 提供 `temp_db` fixture,自动创建临时 DB 并在 session 结束清理。
- **CLI 加载逻辑**:`calorie_tracker.py` 启动时检测 `pytest` 进程名 → 自动用 `SKILLS_DB_PATH_TEST`;否则用 `SKILLS_DB_PATH`。
- **立即动作**(Batch 1):删除 `weight_log.id IN (132,133,134,135)` 4 条测试记录(用户已确认)。
- **不引入 `is_test` 列**:直接隔离,不增加 schema 复杂度。
- **审计**:迁移前扫描所有 `tests/*.py` 的 fixture / setUp,确保都走 `SKILLS_DB_PATH_TEST`。

### 4. ADR-0007 · AI 验证协议(Q7)

- **协议条文**(SKILL.md §⚠️ 第 7 条草案):
  > "AI 声称'用户没 X'前必须先 SELECT 验证。违反 = 协议 fail mode,等同 HTML-First 反模式。3 个 fail mode 红线示例:(a) 写脏数据后断言'原值'(本次实测);(b) 空值误判'从未设过'(空值 ≠ '没设过');(c) 类型误判(字符串被 int() 时报 '0')。"
- **执行点**:每次 AI 输出涉及"用户状态"的断言前。
- **检测**:不强制 lint(成本高),依赖 AI 自身遵守 + 用户反馈触发 review。
- **回退路径**:若 AI 误判,用户在对话中指出 → AI 必须立刻 SELECT 重新回答并道歉。

### 5. Mobile 单模板响应式(Q3)

- **CSS 标准**:`@media (max-width:640px)` 是断点(对齐 `templates/food_ranking.html` 已有惯例)。
- **强制项**:每个 HTML 模板必须包含 `@viewport` meta + 至少一个 `@media` 断点 + SVG 高度 `clamp()` 或 viewport-based 单位。
- **表格策略**:每张 `<table>` 外包 `<div class="table-wrap" style="overflow-x:auto">`。
- **检测**:`scripts/check_html_responsive.py` 新增 — 用 `BeautifulSoup` 解析每个 `templates/*.html`,检查 `@media` 存在 + viewport meta 存在。

### 6. list-products 默认 200 + `--all`(Q5)

- **默认行为**:返回前 200 行(按 id 升序,稳定排序)。
- **`--all` 标志**:返回全部行(无 LIMIT)。
- **HTML 配合**:若走 HTML(ADR-0005 默认),自动分页 50/页 + 搜索框。
- **性能保证**:1924 行 + HTML 渲染 < 500ms;10000+ 行 + HTML 仍可用(分页)。

### 7. 体重波动页 v2(Q8)

- **设计冲刺**(Batch 3 之后单独进行):与用户一起 brainstorm — 信息层级 / 可视化 / 异常点定义。
- **占位策略**:Batch 1-3 内只修 mobile + 语义;v2 设计在 spec 之外。
- **不在本 spec 范围**:v2 的具体设计 / 模板结构 / 数据契约 — 单独 spec 处理。

### 8. 3-Batch 落地(Q9)

> **Batch 切分原则**:每 batch 最多 3 文件,优先把"防事故"放 Batch 1,"用户感知"放 Batch 2,"架构 / 文档"放 Batch 3。Q4(全 CLI 校验)落在 Batch 2 的 calorie_tracker.py 单文件多修改;Q8 体重波动 v2 不在本 spec(Out of Scope)。

- **Batch 1 · P0 防事故(数据完整性 + 测试隔离,2 文件)**:
  1. `tests/conftest.py` 新增 `temp_db` fixture — 用 `SKILLS_DB_PATH_TEST` 临时 DB,自动 setup/teardown
  2. `tests/test_db_isolation.py` 新增 — 扫所有 `tests/*.py` 断言无 hardcode 真实 DB 路径,作为 seam 7 守门
  3. **SQL 一次性操作**(不算文件,执行后归档到 `.scratch/trigger-output-and-cli-quality/migrations/2026-07-29_recovery.sql`):
     - DELETE FROM `weight_log` WHERE id IN (132, 133, 134, 135)
     - UPDATE `daily_goal` SET `weight_goal`=69.95, `goal_deadline`='2026-10-30' WHERE id=1
     - 备份原 DB 到 `calorie_data.db.pre-recovery.20260729_HHMMSS`
- **Batch 2 · P1 CLI 校验(2 文件)**:
  4. `calorie_tracker.py` 多处修改(1 个文件):
     - `weight-goal` 改为 `--weight-goal --deadline` 标志位(ADR-0004)
     - 所有 subcommand 加 `type=float/int/str` + 启用 `--help`(Q4)
     - `list-products` 默认 LIMIT 200 + 新增 `--all`(Q5)
     - 查询类 subcommand 加 `--text` escape hatch(ADR-0005)
  5. `tests/test_cli_validation.py` 新增 — seam 5:subprocess 跑 `<cmd> --help` 断言 exit 0 + stdout 含 usage;`weight-goal --weight-goal abc` 断言 exit 非 0 + 含类型错误
- **Batch 3 · P2 架构 / 文档(3 文件)**:
  6. `templates/weight_history.html` 加 `@media (max-width:640px)` + SVG `clamp()` + table `overflow-x:auto` 包装(Q3)
  7. `templates/food_search.html` + `scripts/render_food_search.py` 新增(查热量 HTML 化,ADR-0005 部分)
  8. ADR-0004 / 0005 / 0006 / 0007 写入 `docs/adr/`(4 个 .md 文件,合并视为 1 个 batch 单元)+ `SKILL.md` §⚠️ 第 7 条 + §已实现模板表更新
- **每 batch 收尾**:`pytest tests/` 全绿 + `check_decision_matrix.py` + `check_decimal_precision.py` + `check_trigger_consistency.py` 3 个 lint 全绿 + 用户 review + 点头 → 进入下一 batch。

## Testing Decisions

### 复用现有 seams(`tests/test_redesign.py` 已建立的 4 层)

- **Seam 1 · End-to-end HTML render**:subprocess 跑 `render_*.py` + mock JSON + assert DOM 节点。
- **Seam 2 · JSON data-shape assertion**:parse `window.__DATA__` + 校验 schema。
- **Seam 3 · §04 决策矩阵一致性**:`scripts/check_decision_matrix.py` exit code 0。
- **Seam 4 · 小数精度巡检**:`scripts/check_decimal_precision.py` exit code 0。

### 新增 seams(本 spec 引入,3 个)

- **Seam 5 · CLI 校验**:subprocess 跑 `<command> --help` + 断言 `exit code 0` + stdout 含 usage;新增 `tests/test_cli_validation.py`。
- **Seam 6 · HTML 响应式**:BeautifulSoup 解析每个 `templates/*.html` + 断言 `@media` 存在 + viewport meta 存在;新增 `scripts/check_html_responsive.py`。
- **Seam 7 · 测试隔离**:扫描 `tests/*.py` 中 fixture / setUp + 断言所有 DB 写入走 `SKILLS_DB_PATH_TEST`;新增 `tests/test_db_isolation.py`。

### 什么是好测试(本 spec 范围)

- **只测外部行为**:测试 CLI 退出码、stdout 关键字段、HTML DOM 节点、CSS 规则存在性;**不测** argparse 内部结构、SQL 查询计划、Python 字典顺序。
- **不依赖生产 DB**:所有测试走 `SKILLS_DB_PATH_TEST`;**禁止** hardcode 真实路径如 `D:\.db\calorie_data.db`。
- **fixture 可重复**:`temp_db` fixture 保证每个测试独立 DB,互不污染。

### Prior art(同类测试)

- `tests/test_redesign.py` 已经定义了 seam 1-4 的 pattern,新 seam 5-7 复用其 `_run_script` / `_extract_payload` 工具函数。
- `scripts/check_trigger_consistency.py` 是 seam 3 的实现样本。

## Out of Scope

- **体重波动页 v2 具体设计**(Q8)— 单独 brainstorming spec,不在本 spec。
- **新增 trigger / 新增实体** — 本 spec 只覆盖现有 6 个 issue。
- **多用户 / 权限 / 云同步** — 卡路里仍是 SQLite 本地。
- **CLI 框架重写**(click / typer)— ADR-0004 维持 argparse,不做大改。
- **`is_test` 列** — ADR-0006 走 DB 隔离路线,不增加 schema。
- **回退老 CLI 行为** — 不保留 `weight-goal <kg> <deadline>` 的 positional 形式(escape hatch `--legacy-positional` 临时保留 3 个月)。
- **国际化 / 多语言** — HTML 仍是中文。
- **性能压测** — 1924 行是当前规模,10000+ 行的性能优化不进本 spec。

## Further Notes

### 关联 spec

- `.scratch/card-html-redesign/spec.md`(2026-07-28)— 覆盖 HELP / 主页 / 今日饮食 / 热量趋势视觉,本 spec 互补不重叠。本 spec 处理 CLI / Mobile / 测试 / 协议。
- `.scratch/diag/` — 诊断痕迹(weight_goal='--help' 污染记录、SQL 验证脚本)。

### ADR 编号衔接

- 已有 ADR-0001 / 0002 / 0003(2026-07-28)。
- 本 spec 产出 ADR-0004(CLI 标志化)/ 0005(HTML 默认)/ 0006(测试隔离)/ 0007(AI 验证协议)。

### 顺序与依赖

```
Batch 1 (P0) ── 无依赖
   ↓
Batch 2 (P1) ── 依赖 Batch 1 的 CLI 校验(seam 5 必需)
   ↓
Batch 3 (P2) ── 依赖 Batch 2 的 HTML 模板(seam 6 校验目标)
```

### 风险与开放问题(对抗式审查)

> **R1 · CLI 标志化的 ergonomic 风险**
> ADR-0004 把所有 weight-goal 参数改成标志位。若用户已有 shell alias / 脚本调老接口,会立刻失效。**缓解**:`--legacy-positional` 临时保留 + deprecation warning + CHANGELOG 醒目公告。3 个月后删。

> **R2 · HTML 默认可能误伤 CLI 用户**
> ADR-0005 默认 HTML 后,直接跑 `calorie_tracker.py list-products | grep 牛肉` 的 pipeline 会失败(stdout 是 HTML 不是 text)。**缓解**:`--text` 标志 + 文档明示"pipeline 场景用 `--text | grep`。

> **R3 · Q3 单模板响应式的迁移成本**
> `weight_history.html` 当前无 `@media`,且 4 mode 共用同一模板,改动一处可能影响所有 mode。**缓解**:先在 `templates/weight_history_mobile_prototype.html` 做 prototype,review 后再 merge 到主模板。

> **R4 · 测试隔离要求审计所有现有测试**
> 现有 9 个 test 文件(共 11KB+)可能 fixture 写法不一,有些可能 hardcode 真实路径。**缓解**:Batch 1 包含 `tests/test_db_isolation.py`,先跑 lint 列出所有违规 fixture,逐个迁移。

> **R5 · AI 验证协议是软约束**
> ADR-0007 写进 SKILL.md 是文档性约束,不会自动检测 AI 是否违反。**缓解**:把"先 SELECT"写进 `卡路里HELP` 的 prompt 模板顶部,让 AI 触发 wake word 时看到提示。

> **R6 · Q8 体重波动 v2 未定义**
> 本 spec 把 v2 推到 Batch 3 之后单独 brainstorming,但 brainstorming 的人 / 时间 / 输出物没定义。**缓解**:在 Batch 3 完成时新增 `.scratch/weight-volatility-v2/` 目录,发起新的 `/grilling` session。

> **R7 · 3-batch 顺序的刚性**
> 若 Batch 1 揭示更深层问题(例如 ADR-0005 与某个现有 trigger 不兼容),需要中断 3-batch 计划。**缓解**:每 batch 收尾时 review + 决定是否继续 / 调整顺序。

### 验收标准(spec 完成判定)

- [ ] **Batch 1**:`tests/conftest.py` + `tests/test_db_isolation.py` 2 文件落地;`pytest` 全绿;`daily_goal.weight_goal=69.95` + `goal_deadline='2026-10-30'` 已恢复;`weight_log.id 132-135` 已删除;备份存在。
- [ ] **Batch 2**:`calorie_tracker.py` 改动落地(weight-goal flag + 全 subcommand type 检查 + `--text` + list-products 200);`tests/test_cli_validation.py` 存在且覆盖 4 个 subcommand 的 `--help` + 1 个 type 错误用例;`pytest` 全绿。
- [ ] **Batch 3**:`weight_history.html` mobile OK(`@media` + SVG `clamp()` + `overflow-x:auto`);`templates/food_search.html` + `render_food_search.py` 存在;ADR-0004 ~ 0007 4 文件存在;`SKILL.md` §⚠️ 第 7 条存在;`check_trigger_consistency.py` 升级后 exit 0。
- [ ] **跨 batch**:`check_decision_matrix.py` + `check_decimal_precision.py` + `check_trigger_consistency.py` 3 个 lint 脚本全绿。`check_html_responsive.py` 在 Batch 3 收尾时新增(seam 6)并通过。