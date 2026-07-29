Status: ready-for-agent

# 13 — 热量趋势 precision + mobile

**What to build:** `查热量趋势` HTML 修复浮点精度泄漏(`-141.6550000000002`),并解决 4 大模块手机适配问题(曲线拉伸、表格超出、底部文字挤压、KPI 4 列溢出)。

依据:D5(spec 实现细节)。

**Blocked by:** None — can start immediately

- [ ] render 脚本 `summary.start_avg` / `end_avg` / `trend_value` / `series[*].calorie` 全部 `round(2)` 后再序列化
- [ ] `check_decimal_precision.py` 把这 4 个字段加入断言白名单(回归用)
- [ ] mobile `@media (max-width: 640px)`:
  - `.kpi-grid` 4 列 → 2 列
  - `.section padding 24/28 → 16/20`
  - `.table-wrap` + `overflow-x: auto`
  - `svg height 220 → 180`(`preserveAspectRatio` 保留)
- [ ] 表格 `td.num` 全部 `font-variant-numeric: tabular-nums`(避免水平抖动)
- [ ] 测试:`trend_value=-141.655` 输入 → 输出 `-141.66`(或 `-142` 若 round 到整数);360px 视口下 4 模块均无溢出