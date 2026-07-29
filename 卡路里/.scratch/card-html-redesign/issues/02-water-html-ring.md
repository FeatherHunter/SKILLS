Status: ready-for-agent

# 02 — 查今天喝水 HTML ring + weekly chart

**What to build:** 用户说"查今天喝水"时,获得一个 HTML 页面(含今日进度环 + 今日 ml 数字 + 本周 mini-chart),不再收到 text-only 回执与 `<system-reminder>` 约束提示。

依据:ADR-0003。

**Blocked by:** None — can start immediately

- [ ] 新模板渲染今日饮水进度环(0-100% 圆环,目标 2000 ml,可配置)
- [ ] mini-chart 显示本周 7 天饮水(bar chart)
- [ ] 新 render 脚本组装 JSON `{summary: {today_ml, target_ml, week: [...]}}`
- [ ] 新 mock fixture(空 / 部分 / 已完成 三档)写入 `tests/fixtures/mock/`
- [ ] SKILL.md §04 决策矩阵 `查今天喝水` 行 cell 从 ❌ 改 ✅
- [ ] 系统层 `<system-reminder>` 中 `查今天喝水 ❌ 不做 HTML` 提示移除
- [ ] `check_decision_matrix.py` 识别 `查今天喝水` 已有完整路径(render + template + mock)