---
Status: ready-for-agent
Slug: weight-volatility-v2
Created: 2026-07-29
Source: /grilling session 2026-07-29 · Q8 design decisions · Issue 5.4 user feedback "整页 brainstorming"
Supersedes: weight_history.html `--mode volatility` (Q8 v1)
Related: ADR-0004 supersede (v2.5.5) · ADR-0006 test isolation · ADR-0007 AI verify
---

# 卡路里 · 体重波动 v2 · Spec

## Problem Statement

用户(本人)在 Issue 5 中实测反馈:`查体重波动` 现有实现"**整个页面的功能要做更多的开发和头脑风暴**"。当前页面只能给出**整段 σ**(被减肥 trend 污染,数值虚高 ~5kg) + 简单异常点列表(>0.5kg 阈值,误报多),不能区分:
- 今天的体重是否在我**最近的常态**里(A · 每日诊断)
- 我的减肥干预**是否让波动收窄**了(B · 干预评估)
- 今天称出 X kg 是否**值得紧张**(C · 早警告)

我用 daily 称重(σ 真实 ~0.93kg,绝对值与减肥期不可比),当前 volatility 视图不能回答以上任何问题。

## Solution

**新增独立 dashboard `weight_volatility_v2.html`**(单一新页面,不走 `--mode volatility` 老路径)。Canvas 重写图表(同步解决 Q7 chart 缩放 bug + 给 v2 文本正常比例 + 数据点像素精度)。一页三段式:

1. **顶部 KPI 卡**(1 行 3 卡)— A 诊断、B 趋势、C 早警告各 1 张,每张 1 句话 + 1 个数字
2. **中部 Canvas 主图**— 体重折线 + ±σ 带(滚动 30 天均值)+ 目标线 + 异常点(黄/红)+ (b)/(c) baseline 切换按钮
3. **底部异常列表**— 最近 7 天偏差最大的 3-5 条数据点(日期 + kg + 偏离 + 标签)

v2 触发词:`查体重波动 v2`(别名 `查体重稳定性`)。原 `查体重波动` 维持现有 weight_history.html volatility mode(不破坏向性,见 ADR-0004)。

## User Stories

### A. 每日诊断(核心 use case)
1. As a daily-weight 用户, I want 打开 dashboard 看到**我今天的体重 vs 我近 30 天常态**,so that 我知道"今天跟平时比是反常还是正常"
2. As a daily-weight 用户, I want 看到一个**±1σ 带**的可视化区间(滚动 30 天均值 ± σ),so that 我能直观判断今天的点是落在"常态范围"内还是外
3. As a 减肥期用户, I want v2 dashboard 不用我**手动设 σ**,so that σ 自动从最近数据算出来,反映我"现在的常态"
4. As a 关注目标的用户, I want 一个**"对标目标" toggle**,点击切换 baseline 视图:从"vs 我近期态"切到"vs 我的目标 73kg"
5. As a 视障/斜视用户, I want Canvas 文字用正常比例(不被横向拉伸),so that 文字可读

### B. 干预评估
6. As a 减肥/增肌用户, I want 看到**7-day rolling σ 随时间的变化**,so that 我知道"我的体重波动是在收窄(干预有效)还是扩大(无效/复胖)"
7. As a 长期复盘者, I want 一个**"近期 σ vs 早期 σ"对比**,so that 一眼看出"我这 4 周比上 4 周波动更小"
8. As a 干预者, I want v2 不**混淆"波动趋势"和"体重趋势"**,so that σ 缩小 ≠ 体重下降(可能体重没降但波动小了)

### C. 早警告
9. As a 早起称重用户, I want v2 在今天称出**异常值时立即显示警告**,so that 我能看到"今天偏离 ±1.9kg = 红"
10. As a 减肥用户, I want v2 区分**黄警告(轻微偏离 ±1.4kg)vs 红警告(明显偏离 ±1.9kg)**,so that 我知道"该不该紧张"
11. As a 日常用户, I want 异常点列表**按日期倒序 + 偏离度排序**,so that 我能快速找到"最该关注的几次"
12. As a daily-weight 用户, I want 异常点列表**只显示最近 7 天的**,so that 我不被 1 个月前的旧事件分散注意力

### D. 通用 / 跨场景
13. As a mobile 用户, I want v2 dashboard 在 375px 宽屏上**布局自适应**(KPI 卡堆叠 1 列 / 主图全宽 / 异常列表紧凑)
14. As a 慢网络用户, I want v2 HTML 含**完整 `window.__DATA__` 注入**,so that 客户端 JS 一次拿到所有数据,不需额外 API
15. As a 数据完整性重视者, I want v2 dashboard **不写数据库**,so that 查波动是纯只读操作,绝不污染 weight_log
16. As a 重度用户, I want v2 dashboard **渲染时间 < 500ms** for 90 天数据(Canvas 比 SVG DOM 操作快)
17. As a 老用户, I want v2 dashboard **不破坏 weight_history.html volatility mode**(v1 仍可访问)
18. As a pipeline 用户, I want v2 触发词也支持 `--text` flag 输出纯文本(无 Canvas),so that 我能用 `grep`/`awk` 处理
19. As a 防止 tech debt 用户, I want v2 **不写 `--legacy-volatility-mode` 之类逃生口**,遵循 v2.5.5 "不存 deprecation 库存" 哲学(ADR-0004 supersede)
20. As a 测试者, I want v2 有**专门的 seam 4 端到端测试**,follow `tests/test_food_search.py` 模式

## Implementation Decisions

### Backend(analysis.weight 新函数)
- 新函数 `weight_volatility_v2(start_date, end_date, baseline_mode='rolling'|'goal')` 返回 dict:
  - `data.baseline_mode`: 当前 baseline 类型
  - `data.baseline_value`: 滚动 30 天均值(rolling mode) 或 goal_weight(goal mode)
  - `data.baseline_sigma`: 滚动 7 天 σ(rolling mode) 或历史平均 σ(goal mode)
  - `data.thresholds`: `{yellow: ±1.5σ, red: ±2.0σ}`(派生自 baseline_sigma)
  - `data.points`: list of `{date, kg, deviation_kg, level: 'normal'|'yellow'|'red'}`
  - `data.recent_anomalies`: 过去 7 天 level != 'normal' 的点
  - `data.sigma_trend`: 7-day rolling σ 时间序列(`[{week_start, σ_kg}]`)
  - `data.early_warning`: 今日 kg + deviation_kg + level + 解读 1 句话
  - `data.baseline_toggle_label`: 显示当前 mode 的 1 句话("vs 你近 30 天常态" vs "vs 目标 73kg")

**σ 算法 — 关键决策**:用 **detrended σ**(滚动 7 天 σ),不用绝对值 σ。
- 理由:用户在减肥期,绝对值 σ ≈ 5kg(被 90kg→70kg trend 污染),没有意义。detrended σ ≈ 0.93kg 反映"今天的日常波动"。
- 算法:`statistics.stdev([weights[i] - weights[i-1] for i in range(1, N)])` 或 7-day rolling window 的 `statistics.stdev(weights[i:i+7])`

**baseline_mode 算法**:
- `rolling`: `mean(weights[-30:])` + `stdev(weights[-30:].diffs)`(detrended)
- `goal`: `goal_weight`(从 daily_goal 表) + 全程 detrended σ(goal 不依赖时间窗)

### Render 层
- 新脚本 `render_weight_volatility_v2.py`:
  - 接 `--start --end` (date range, 默认最近 30 天) + `--baseline rolling|goal` (默认 rolling) + `--text` (纯文本模式)
  - 调用 `weight_volatility_v2()` 拿数据 dict
  - 注入 `window.__DATA__ = <json>` 到新模板 `templates/weight_volatility_v2.html`
  - 输出路径:`calorie_html/查体重波动_v2_<YYYYMMDD>_<HHMMSS>.html`(同秒冲突自动 _2/_3 后缀)
  - stdout:`⚠️ ACTION=SEND_TO_USER | HTML=<绝对路径>`

### Template(`templates/weight_volatility_v2.html`)
- 单一 `<canvas id="chart">`(替代现有 SVG `viewBox="0 0 800 260"`):
  - 文本不会横向拉伸(Canvas 文本 API 渲染按像素)
  - 数据点用真实像素坐标,无 viewBox 缩放 bug(Q7 修复)
- 三段式 layout(详见 Solution):
  1. `<section class="kpis">` 3 张 KPI 卡(诊断 / 趋势 / 早警告)
  2. `<section class="chart">` Canvas + baseline toggle button
  3. `<section class="anomalies">` 最近异常点列表
- mobile `@media (max-width:640px)`:KPI 卡堆叠 1 列,Canvas 全宽
- 必须含 `<!--INJECT-DATA-->` 占位符(唯一,seam 6 校验)
- 必须通过 `scripts/check_html_responsive.py`(viewport meta + @media + Canvas 视口处理)

### Trigger 层
- 新触发词 `查体重波动 v2`(别名 `查体重稳定性`),在 `_triggers.py` 注册,CLI 指向 `render_weight_volatility_v2.py`
- 原 `查体重波动` 不变(继续指向 `render_weight_history.py --mode volatility`),不破坏向性

### ADR-0004 supersede 应用(v2.5.5 哲学)
- v2 dashboard 不写 `--legacy-volatility-mode` 之类逃生口
- baseline 切换默认 rolling,goal mode 是 toggle 一次性(用户切回 rolling 即可)
- v2 行为改变(算法从绝对 σ 改为 detrended σ)是**破坏性变更**,但属于"问题修复",不写 backward compat

### Schema 不变
- weight_log / weight_goal / daily_goal 表不变
- 纯只读查询,无需迁移

### 触发词集成
- `卡路里HELP` prompt 需更新 trigger 表(加入 `查体重波动 v2`)
- `卡路里.html` 根镜像自动 render_help_center 时同步
- `_triggers.py` docstring 声明 trigger

## Testing Decisions

### Seam 4(新)— `tests/test_weight_volatility_v2.py`
**测试原则**:只测外部行为,跟现有 `tests/test_food_search.py` 模式一致。

**测试 case 列表**:
1. `test_v2_html_passes_responsive_lint` — lint 36 模板全 PASS(已有 lint,无新增)
2. `test_v2_render_exits_zero` — subprocess 跑 `render_weight_volatility_v2.py --start 2026-07-01 --end 2026-07-31` exit 0 + HTML 生成
3. `test_v2_data_shape_contains_all_fields` — `window.__DATA__.data` 含 baseline_value / baseline_sigma / thresholds / points / recent_anomalies / sigma_trend / early_warning
4. `test_v2_anomaly_thresholds_1p5_2p0_sigma` — 断言 thresholds.yellow = 1.5 * baseline_sigma,thresholds.red = 2.0 * baseline_sigma(数学正确性)
5. `test_v2_detrended_sigma_calculation` — 注入已知 daily 数据,断言计算出的 detrended σ ≈ expected(用确定性输入验证算法)
6. `test_v2_baseline_toggle_rolling_vs_goal` — rolling vs goal mode 数据不同(baseline_value 不同)
7. `test_v2_does_not_write_db` — 跑 render 后 weight_log 记录数不变(防 R3 风险)
8. `test_v2_text_mode_emits_plain_text` — `--text` flag exit 0 + stdout 非 HTML(给 pipeline 用户)
9. `test_v2_canvas_present_in_html` — HTML 含 `<canvas id="chart">`,不依赖 `<svg viewBox>`(防退化)
10. `test_v2_recent_anomalies_window_7_days` — 断言 recent_anomalies 只含最近 7 天数据

### 复用 seams
- **Seam B**(`temp_db` fixture):自动给所有 weight_volatility_v2 测试隔离的临时 DB
- **Seam C**(`test_db_isolation`):硬约束 — v2 测试无 hardcode `D:\.db\calorie_data.db`
- **Seam A**(`analysis.weight.weight_volatility_v2` 函数):直接被 Seam 4 测试覆盖,不需要单独单测

### Test 类型分配
- **数学/逻辑**(`analysis.weight.weight_volatility_v2`):Seam 4 test 5,6 直接断言计算结果
- **HTML 渲染**:`templates/weight_volatility_v2.html` 验证 `window.__DATA__` 形状(Seam 4 test 3)
- **CLI 行为**:`render_weight_volatility_v2.py` 端到端(Seam 4 test 2,8)
- **响应式**:`check_html_responsive.py` 静态扫描(Seam 4 test 1)

### 失败模式(已识别)
- v2 算法 σ 计算错误 → Seam 4 test 5 用确定性输入验证
- Canvas 在 headless 浏览器不可测 → 不测 Canvas 内部像素,只测 `<canvas>` 元素存在
- `--text` flag 误删 → Seam 4 test 8 守住(跟 ticket 07 同等防回归)

## Out of Scope

- **体重目标 v2 配套**(目前 goal-only mode 是 1 行 toggle,不做"减肥预测完成日期"等额外特性)
- **多用户 / 多人共享波动数据**(卡路里仍单用户)
- **机器学习预测**(用户没要求;detrended σ + 滚动窗口足够日常用)
- **移动端原生 app**(v2 是响应式 HTML,不是 native app)
- **完整迁移其他 SVG 图表到 Canvas**(只迁移 weight_volatility_v2;其他模板如 calorie_trend 维持 SVG)
- **历史异常回放**(只显示最近 7 天,不做"过去 30 天的所有异常"列表)
- **v1 volatility mode 的移除**(v2 与 v1 共存,v1 在 weight_history.html --mode volatility 仍可用)
- **AI 自动解读波动原因**(v2 显示数据,AI 在用户对话中解读,不在页面写死解读)

## Further Notes

### 与已有 ADR 的关系
- **ADR-0004 supersede (v2.5.5)**:"不存 deprecation 库存"哲学 → v2 不写 `--legacy-volatility-mode`
- **ADR-0006 test isolation**:Seam 4 测试复用 temp_db,无需新增 infra
- **ADR-0007 AI verify protocol**:`weight_volatility_v2.py` 不写库 → 不触发 AI 验证协议(纯只读)

### 数据安全
- v2 是**只读视图**,任何对 weight_log 的写入走原 `weight log` 命令(已修 ADR-0004)
- v2 写库 = bug,Seam 4 test 7 守住

### 性能预算
- 数据点 < 365(1 年 daily):Canvas 渲染 < 100ms(JS 一次性 draw)
- HTML 含完整 JSON 注入,无需额外 API 调用
- 90 天 daily 数据:JSON ~30KB,HTML ~50KB,网络传输 < 200ms(本地)

### Phase 排期(预估)
- 单文件实现(analysis.weight + render 脚本 + template):预计 1 PR
- 测试覆盖(10 个 case):预计同 PR 包含
- 文档 / trigger 集成:同 PR

### 后续可探索(不在本 spec)
- 跨用户对比(社区均值 vs 个体)
- 体重预测模型(线性回归 trend + σ 置信区间)
- 异常原因自动归因("你偏离最大那天的 note 字段说了什么?")
- 多周期对比(过去 90 天 vs 再过去 90 天,等长周期对比)