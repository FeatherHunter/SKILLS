# ADR-0003: 月度汇总顶层 count 口径 = 全量记录（含收入）

## Status

accepted — 2026-08-10（issue #246 修复 · commit 937a24c）

## Context

「看月度」唤醒词生成的月度汇总 HTML 顶部 KPI「笔数」显示 0 笔，但分类明细合计有 19 笔（2026-08 实测，支出 3569.43 元正常显示）。

根因：`analyze.py::monthly_summary()` 返回结构 `{month, categories, expense, income, net}` **缺顶层 `count`**；`analysis/cli.py::cmd_monthly()` 用 `result.get("count", 0)` 兜底 → 恒为 0 → 模板 `analysis_view.html` KPI 渲染 `${kpiCard('笔数', data.count || 0, ...)}` 显示 0 笔。

修复前曾有两个候选口径，需锁死语义，避免未来重构时再次踩坑：

1. **全量记录数**：`totals['count']`（`_get_totals` 的 `COUNT(*)`，含收入与支出）
2. **分类 count 合计**：`sum(c['count'] for c in categories)`（分类明细只查 `amount < 0`，仅支出）

## Decision

**顶层 `count` = 全量记录数（口径 1）**，即 `monthly_summary()` 返回值补 `"count": totals["count"]`。

理由：

- 与「看年度」「看总览」的 KPI 笔数口径一致（`_calc_kpi` 的 `len(records)` 也是全量含收入）
- 分类明细天然只列支出（`amount < 0` 聚合），若顶层 count 取分类合计，则月份有收入记录时 KPI 与「支出+收入」总量自相矛盾
- `_get_totals` 的 `count` 与 `expense/income` 同源同查，不存在二次聚合漂移

由此推断测试断言：**`count >= 分类 count 合计`**（而非 `==`）——当某月含收入记录时，全量 count 必然 ≥ 支出分类合计；用 `==` 会在有收入的月份误报失败。

## Consequences

- **优点**：
  - 月度汇总 KPI 笔数与年度/总览口径统一，无歧义
  - 顶层 count 由 `totals` 直接给出，与 expense/income 同源，无漂移
  - 分类明细仍是支出侧聚合，语义不变（「钱花在哪些分类」）
- **代价**：
  - count 与分类合计在含收入月份不一致（如 2026-05：count=116，分类合计=108）——这是设计使然，非 bug
  - 消费者若想算「支出笔数」必须自行过滤，不能直接用顶层 count（顶层是全量）
- **验证**：
  - `tests/test_analysis.py::TestSummaryFamily::test_monthly_kpi_and_categories` 断言 `count >= sum(c['count'])`（2026-08-11 #254 退役 run_tests.py 时补入 pytest 体系）
  - 复现命令实测：`monthly --month 2026-08` → 顶层 count=19，分类合计=19，expense=3569.43（2026-08 无收入，两口径重合）
  - 全量 pytest：421 pass / 1 fail（fail 为 pre-existing `test_summary_today`，与本改动无关，基线对照一致）

## Follow-up

- [ ] 若未来「看月度」需要展示「支出笔数」独立 KPI，应从分类明细聚合推导，不动顶层 count 口径
