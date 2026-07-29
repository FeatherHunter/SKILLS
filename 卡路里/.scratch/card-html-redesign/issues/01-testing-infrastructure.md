Status: ready-for-agent

# 01 — 测试基础设施

**What to build:** 给后续 14 个 ticket 提供守护网:
- 中心化 `§04 决策矩阵` 一致性检查(每个 §04 `✅` 的 wake word 必须有对应的 render 脚本 + 模板 + mock fixture)
- 浮点精度巡检器(扫描生成的 HTML,parse JSON,断言数字字段小数位 ≤ 2)
- 顶层 `tests/test_redesign.py` 骨架(后续 ticket 通过它加 acceptance)

**Blocked by:** None — can start immediately

- [ ] `scripts/check_decision_matrix.py` 跑通:列出 §04 ✅ 列表,逐项核对 render 脚本 + 模板 + mock fixture 存在
- [ ] `scripts/check_decimal_precision.py` 跑通:扫描 `calorie_html/` 下生成 HTML,断言 `summary.trend_value` / `summary.start_avg` / `summary.end_avg` / `series[*].calorie` 等字段小数位 ≤ 2
- [ ] `tests/test_redesign.py` 骨架存在(可空 test 集合)
- [ ] 3 个新脚本加入 pre-commit hook(若该 hook 存在)
- [ ] `pytest tests/test_redesign.py` exit 0