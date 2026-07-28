# 合并 查今天吃 与 查吃的记录 为单一 wake word

Status: proposed

两个 wake word 输出几乎重叠:均呈现今日/近日饮食,只是 UI 布局略不同。SKILL.md §触发词速查表 L283-284 与 `_triggers.py` / `templates/*.html` 的 HTML spec 不一致。`render_today_meals.py` 默认 `--days 3` 与"今天"语义直接冲突,用户被 multi-day 结果困扰。

我们决定合并为单一 wake word `查今天吃`,默认今日单日。`查吃的记录` 留作 alias(同 render 脚本 + 模板)。

考虑过的选项:继续保留两个 wake word 但分别承担"按餐次"与"逐条 list"的两种 UI 视图——两套渲染脚本/模板维护成本 × 用户认知负担,与价值不对称。Single wake word, single intent, single output 是 HTML-first 设计的一致原则。

后果:默认窗口由 3 天收缩为 1 天——multi-day view 留待未来 wake word(可显式 `--days N`)。Migration 通过 `check_trigger_consistency.py` alias 关系校验守护。
