# 查今天喝水 加 HTML 模板(§04 ❌ → ✅)

Status: proposed

查今天喝水 被 §04 决策矩阵判为 "single-day quick query, no template",text-only 回执。`<system-reminder>` 提醒 AI 受约束——把"设计决策"暴露给用户,体验受困于约束感。视觉化需求高(每日多次查,环形进度直觉远胜数字)。

我们决定 `查今天喝水` §04 行 ❌ 改 ✅,新增 `templates/today_water.html`(今日进度环 + 今日 ml 数字 + 本周 mini-chart)。`render_today_water.py` 接管渲染。

考虑过的选项:继续 text-only,改用更紧凑的文本格式(如 `进度 6/8 杯 · 750 ml / 2000 ml`)——同样信息,但 HTML 环的"完成感"与 weekly trend 是 text 不可替代的。Another option: 让 `<system-reminder>` 不再引用 §04,但仍 text-only——只是消除了"约束感",并未提升信息密度。

后果:多一个 HTML 模板 + render 脚本需维护,但与 §04 决策矩阵 中其它"✅" 模板(today_diet / today_meals 等)同等成本。Reversibility: §04 矩阵单元格回退为 ❌ 即可。
