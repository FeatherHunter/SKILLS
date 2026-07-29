# 09 — sync_report UI 一致性(状态卡 / KPI / 信息流 / 中文化)

**What to build:**
End-to-end behavioural change:
1. 用户打开同步报告,第一屏状态卡左侧出现 6px 明显 accent bar(OK=绿 / warn=橙 / err=红 / idle=灰),一眼分清状态。
2. 状态卡 OK / warn 渐变色相近 → 强化色相:OK 偏绿豆沙色,err 偏粉红色,数量级差异 ≥ 2(肉眼下能区分)。
3. 4 KPI 卡的顶条从 3px 升到 4px(更显眼),状态卡下方紧邻 4 卡 KPI(不再 KPI→详情→KPI→详情 跳动)。
4. 命令字段(command 字符串 `sync-from-feishu`)中文化显示(用户看"同步飞书"而非 `sync-from-feishu`),保留 CLI 实际参数原样。

**Blocked by:** None — can start immediately(独立模块)

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `templates/sync_report.html` 状态卡 `.status-card` 加 `.status-card::before{content:"";position:absolute;left:0;top:0;bottom:0;width:6px;border-radius:...}`.ok::before{background:var(--ok)} 等。
- [ ] `.status-card.ok{background:linear-gradient(180deg,#fff 0%,#f7fdf9 100%)}` 改为更明显的色相:`linear-gradient(180deg,#fff 0%, #ebfaef 100%)`(更绿豆沙)。
- [ ] `.status-card.err` 同理收紧红。
- [ ] `.kpi{position:relative;overflow:hidden}` 加 `.kpi-bar{height:4px}`(原 3px 升 4px)。
- [ ] DOM 顺序:状态卡 → KPI 4 卡 section → 明细区(原生 `<details>`)— 不再混插。
- [ ] command 字段(`d.command || 'sync-from-feishu'`)中文化映射表:
  ```
  const CMD_CN = { 'sync-from-feishu': '同步飞书', ... };
  ```
  显示时取 `CMD_CN[d.command] || d.command`。
- [ ] 测试断言:`tests/test_template_lint.py` 加 fixture 验 sync_report 状态卡 CSS 字符串含 `::before{width:6px}` 字面,KPI `.kpi-bar` 字面是 `height:4px`。
- [ ] 测试断言:`tests/test_render.py` 加 fixture:用真实历史 payload(backfilled=0, synced=4, skipped_no_local_note=174)渲染,断言 HTML 文本含"同步飞书"(中文 alias)且不再含 `'sync-from-feishu'` 字面(在 DOM 显式节点里)。
- [ ] pytest 全绿。

## 验证定义

完成 = 状态一眼区分 + KPI 顶条 4px + 信息流无跳动 + command 显示中文 + pytest 全绿。
