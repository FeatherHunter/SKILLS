# 02 — Dashboard 单页(KPI + Canvas 主图 + σ 带)

**What to build:**
`templates/weight_volatility_v2.html` 单页 dashboard 第一版。**Canvas 替代 SVG**(同步解决 Q7 chart 缩放 bug + 文字不被横向拉伸 + 数据点像素精度)。三段式 layout 起头:顶部 1 张 KPI 卡(诊断,展示 baseline + 今日值)+ 中部 Canvas 主图(体重折线 + ±σ 带 + 目标线)+ 底部预留异常区(本 ticket 暂留空)。

数据通过 `window.__DATA__` 注入。模板遵守 seam 6 契约(`<!--INJECT-DATA-->` 唯一占位符 + viewport + @media + table-wrap 模式如果用 table)。本 ticket 完成 03 的 dashboard 框架。

**Blocked by:** 01(v2 math 函数)

**Status:** ready-for-agent

- [ ] `templates/weight_volatility_v2.html` 新建,Apple 风格 + 单一 `<canvas id="chart">`
- [ ] Canvas JS:画 baseline 线 + 体重折线 + ±σ 带阴影 + 目标线(虚线)
- [ ] 1 张 KPI 卡(诊断):"今天 X kg vs 近期常态 Y ± Z kg"+ 1 句解读
- [ ] 模板含 `<!--INJECT-DATA-->` 占位符(唯一,seam 6 校验)
- [ ] viewport meta + `@media (max-width:640px)` 移动适配
- [ ] seam 4 test 1:`check_html_responsive.py` lint 通过
- [ ] seam 4 test 9:HTML 含 `<canvas id="chart">` 元素
- [ ] seam 4 test 3:`window.__DATA__.data` 含 baseline_value / baseline_sigma / thresholds
- [ ] `python -m pytest tests/test_weight_volatility_v2.py` 全绿
- [ ] 视觉:demo 时 render 默认数据后,Canvas 内可见 baseline / 体重线 / ±σ 带阴影
