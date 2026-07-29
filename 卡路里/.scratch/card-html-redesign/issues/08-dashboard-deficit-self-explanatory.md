Status: ready-for-agent

# 08 — 主页 dashboard 缺口 KPI 自解释

**What to build:** `主页仪表盘` 中 "缺口" 卡片不再只是 "−1640 卡/日",而是给出完整 math breakdown + size_label badge + 修 kg/期 显示 bug。

依据:D3(spec 实现细节)。

**Blocked by:** None — can start immediately

- [ ] detail text:`TDEE {BMR} + 运动 {ex_burn} = 应烧 {total_burn} vs 摄入 {intake}`(各值整数,localized 千分位)
- [ ] badge 用 size_label(`过大` warn / `适中` ok / `适宜` good)— 数据源:deficit 分析模块的 size_label 字段(确认已输出)
- [ ] kg/期 标签 fix:
  - `N=1` → `理论 X kg(本日)`
  - `N>1` → `理论 X kg(N 天) · 折合 Y kg/周`,`Y = X * 7 / N`
- [ ] 主数值保留 `avg_deficit` 正向 = 减重方向(用 Unicode `−` 而非 ASCII `-`)
- [ ] 测试:三种 size_label 各 render 一遍 fixture;N=1 / N=7 两档分支各跑一遍