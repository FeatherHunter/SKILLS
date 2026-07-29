# 04 — Baseline toggle(rolling↔goal)+ σ 趋势 + mobile

**What to build:**
3 个 use case 都已上线(03)后,加交互层 + 移动端 polish:
- Baseline toggle 按钮(rolling 30 天均值 ↔ 目标 73kg),点击后重画 Canvas + 更新 KPI 文字
- σ 趋势小图(7-day rolling σ 时间序列 sparkline),增强 KPI B 的视觉信息
- Mobile `@media (max-width:640px)` 布局:KPI 卡堆叠 1 列、Canvas 全宽、列表紧凑

**Blocked by:** 03(完整 dashboard)

**Status:** ready-for-agent

- [ ] Baseline toggle 按钮:点击切换 baseline_mode,重渲染 Canvas 与 KPI 文字
- [ ] 切换时显示"vs 你近 30 天常态" / "vs 目标 73kg" 等当前 mode 文字
- [ ] σ 趋势 sparkline:KPI B 卡片内嵌 mini line chart(7 个 σ 点)
- [ ] `@media (max-width:640px)`:KPI 1 列 / Canvas 全宽 / 异常列表压缩 padding
- [ ] toggle 状态持久化:URL `?baseline=rolling` 或 localStorage(让用户分享链接)
- [ ] seam 4 test 6:已覆盖(03 完成)
- [ ] 视觉:demo 时点 toggle,看到 KPI 文字 + Canvas baseline 改变;窄屏布局自适应
- [ ] `python -m pytest tests/test_weight_volatility_v2.py` 全绿
