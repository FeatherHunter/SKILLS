# 01 — 数学函数 `weight_volatility_v2()` + σ 算法

**What to build:**
体重波动 v2 的 backend 数学核心。新增 `analysis.weight.weight_volatility_v2(start_date, end_date, baseline_mode='rolling'|'goal')` 函数,返回包含 baseline_value / baseline_sigma / thresholds / points / recent_anomalies / sigma_trend / early_warning 的 dict。**关键算法决策**:用 **detrended σ**(滚动 7 天 daily 差值的 stdev 或 7-day rolling window stdev),不用绝对值 σ(被减肥 trend 污染,数值虚高)。

函数纯只读,不写库。

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `scripts/analysis/weight.py` 新增 `weight_volatility_v2(start_date, end_date, baseline_mode)` 函数(默认 `baseline_mode='rolling'`)
- [ ] rolling mode:返回 `baseline_value` = 最近 30 天 mean,`baseline_sigma` = detrended 7-day rolling σ
- [ ] goal mode:返回 `baseline_value` = `daily_goal.weight_goal`,`baseline_sigma` = 全程 detrended σ
- [ ] `thresholds` = `{yellow: 1.5 * baseline_sigma, red: 2.0 * baseline_sigma}`(派生)
- [ ] `points` = list of `{date, kg, deviation_kg, level: 'normal'|'yellow'|'red'}`(逐日标注异常级别)
- [ ] `recent_anomalies` = 过去 7 天 `level != 'normal'` 的点
- [ ] `sigma_trend` = 7-day rolling σ 时间序列,`[{week_start, σ_kg}]`
- [ ] `early_warning` = 今日 kg + deviation_kg + level + 1 句解读
- [ ] `tests/test_weight_volatility_v2.py` 新增 deterministic test:用已知 daily 数据断言 σ ≈ 0.93(以用户最近 7-day 实际数据为参考)
- [ ] seam 4 test 4:`test_v2_anomaly_thresholds_1p5_2p0_sigma` 断言 `thresholds.yellow == 1.5 * baseline_sigma`
- [ ] seam 4 test 5:`test_v2_detrended_sigma_calculation` 验证 detrended 算法
- [ ] 不修改 `analysis.weight.weight_volatility()`(v1 函数保留,v1 mode 仍可用)
- [ ] `python -m pytest tests/test_weight_volatility_v2.py` 全绿
