# 合并 查今天吃 与 查吃的记录 为单一 wake word

Status: proposed

两个 wake word 输出几乎重叠:均呈现今日/近日饮食,只是 UI 布局略不同。SKILL.md §触发词速查表 L283-284 与 `_triggers.py` / `templates/*.html` 的 HTML spec 不一致。`render_today_meals.py` 默认 `--days 3` 与"今天"语义直接冲突,用户被 multi-day 结果困扰。

我们决定合并为单一 wake word `查今天吃`,默认今日单日。`查吃的记录` 留作 alias(同 render 脚本 + 模板)。

考虑过的选项:继续保留两个 wake word 但分别承担"按餐次"与"逐条 list"的两种 UI 视图——两套渲染脚本/模板维护成本 × 用户认知负担,与价值不对称。Single wake word, single intent, single output 是 HTML-first 设计的一致原则。

后果:默认窗口由 3 天收缩为 1 天——multi-day view 留待未来 wake word(可显式 `--days N`)。Migration 通过 `check_trigger_consistency.py` alias 关系校验守护。

## Q3 决策落地(ticket 16 · 2026-07-29)

Q3 问题:`today_diet` / `today_meals` 模板合并策略?

**决策:维持双模板,不彻底合并。** 分工:
- `templates/today_diet.html` + `render_today_diet.py` = 单日 4 餐摘要视图(`查今天吃` / `查吃的记录` 默认走这个)
- `templates/today_meals.html` + `render_today_meals.py` = 多日 list 视图(`查吃的记录 7/1 到 7/14` 显式区间走这个)

理由:两个视图 UI 差异显著(4 餐分组 vs 逐条 list),partial 共享(提取 common block)反而增加维护负担。双模板各自单一职责更清晰。Q3 关闭。
