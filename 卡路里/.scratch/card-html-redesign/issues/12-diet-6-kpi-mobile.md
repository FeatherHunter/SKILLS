Status: ready-for-agent

# 12 — 今日饮食 6 KPI + mobile + 1-day default

**What to build:** `查今天吃`(合并后)HTML 顶部 KPI 从 4 个扩展为 6 个(记录数 / 总热量 / 总蛋白 / 总碳水 / 总脂肪 / 总饮水);默认 1 天(今日);mobile 适配。

依据:D4(spec 实现细节);与 04 互不阻塞,默认 1 天由各自约定。

**Blocked by:** None — can start immediately

- [ ] render 脚本输出 summary 含 6 个字段(`total_calorie` / `total_protein` / `total_carb` / `total_fat` / `total_water` + 记录数)
- [ ] 模板 KPI grid 6 个:桌面 `grid-template-columns: repeat(3, 1fr)`(2 行 × 3 列);mobile `grid-template-columns: 1fr`(6 行 × 1 列)
- [ ] 默认日期筛选 `今日`,无 `全部` 选项(若 04 启用单日,则与之一致)
- [ ] `table` 外套 `.table-wrap`,`overflow-x: auto`;整页 `overflow-x: hidden`
- [ ] mobile `@media (max-width: 640px)`:`.section padding` 24/28 → 16/20
- [ ] 测试:6 KPI 全部显示 + 顺序正确;360px 视口下表格横滚、整页不滚;默认筛选今日