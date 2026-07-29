Status: ready-for-agent

# 10 — 主页 dashboard log-row mobile

**What to build:** `主页仪表盘` "最近记录" 区,手机(≤640px)与桌面端都不再出现 time(HH:MM:SS)与食物名重叠;time 改 HH:MM 简化。

依据:D3(spec 实现细节)。

**Blocked by:** None — can start immediately

- [ ] `.log-row` CSS 一套(桌面 + 手机统一):`grid-template-columns: 44px 1fr auto; gap: 10px`
- [ ] `.log-row .name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }`
- [ ] time 显示 HH:MM(后端保留 HH:MM:SS;前端 `time.slice(0,5)` 或 render 时截取)
- [ ] `.log-row .time, .log-row .cal { white-space: nowrap; font-variant-numeric: tabular-nums; }`
- [ ] 测试:360px 视口下,长食物名截断;time 列不超 44px;无 horizontal overflow