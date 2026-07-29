# 03 — 完整 dashboard(3 KPIs + 异常列表)

**What to build:**
完成 v2 dashboard 三段式:顶部 3 张 KPI 卡(诊断 / 趋势 / 早警告)+ 中部 Canvas(已在 02 落地)+ 底部异常点列表(过去 7 天,按偏离度倒序,黄色 / 红色徽章)。这是 3 个 use case 全部上线的状态。

**Blocked by:** 02(dashboard 单页)

**Status:** ready-for-agent

- [ ] KPI 卡 2(趋势,use case B):"近 7 天 σ = X kg"+ 解读"σ 在收紧 / 扩大"
- [ ] KPI 卡 3(早警告,use case C):"今天偏离 ±X kg = 黄色 / 红色"+ 解读
- [ ] 异常点列表区域:过去 7 天非 normal 的点,按 `|deviation_kg|` 降序
- [ ] 每行显示:日期 / kg / 偏离值 / level 徽章
- [ ] 列表空时显示"过去 7 天无异常 ✓"
- [ ] seam 4 test 6:`test_v2_baseline_toggle_rolling_vs_goal` 数据不同
- [ ] seam 4 test 10:`test_v2_recent_anomalies_window_7_days` 只含 7 天
- [ ] 视觉:demo 时 3 张 KPI 卡 + 异常列表完整可见,Canvas 主图正常
- [ ] `python -m pytest tests/test_weight_volatility_v2.py` 全绿
