Status: ready-for-agent

# 04 — ADR-0002 contract: 查吃的记录 退役,默认 1 天

**What to build:** 完成 ADR-0002 contract 阶段:删除 `查吃的记录` 作为独立 wake word(降级为 alias),默认今日单日。

依据:ADR-0002 contract 阶段。

**Blocked by:** 03

- [ ] `_triggers.py` 中 `查吃的记录` 整条记录移除;只在 `查今天吃` 上保留 alias 映射
- [ ] SKILL.md §触发词速查表 L283-284:`查今天吃` 单行,`查吃的记录` 标为 alias(指向 `查今天吃`)
- [ ] render 脚本默认时间窗 1 天(若原 `--days 3`):`render_today_meals.py` 默认值改为 1(或直接退役复用 `render_today_diet.py`)
- [ ] mock 合并:`tests/fixtures/mock/mock_today_meals.json` 合并入 `mock_today_diet.json`(若 2 模板合并)或保留 2 份但默认走单日 fixture
- [ ] 前端模板合并:若决定 2 模板合一,删 `templates/today_meals.html`;否则保留但默认渲染参数改为 1 天
- [ ] 测试:`查吃的记录` 仍能跑通(走 alias);默认 1 天不再跨多日