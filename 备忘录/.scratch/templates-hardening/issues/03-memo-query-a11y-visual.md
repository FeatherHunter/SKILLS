# 03 — memo_query 视觉 / a11y / 长列表

**What to build:**
End-to-end behavioural change:
1. 屏幕阅读器用户可以 Tab 到搜索框并听到"在结果内搜索"。
2. 100 条结果时,页面默认显示前 50 条,提供一个"显示全部 / 前 50"切换按钮,用户可主动展开。
3. KPI 卡(总数 / 有排期 / 有附件 / 有提醒)字号比例稳定 — 数字 ≤ 24px,标签 ≥ 13px,视觉权重平衡。

**Blocked by:** #01 — can only start after lint infrastructure is in place

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `templates/memo_query.html` 给 `<input id="filter">` 加 `<label for="filter">` 节点(显式 label,而非仅 placeholder)。`<label>` 默认隐藏(用于屏幕阅读器,sr-only)或可显(可访问性优先)。
- [ ] `templates/memo_query.html` 加 JS:列表渲染时若总行数 > 50,默认只渲染前 50 条;HTML 上显示一个"显示全部"按钮(绿色 chip 样式),点击切换到全量;若用户输入搜索关键字,搜索结果不受 50 限制。
- [ ] `templates/memo_query.html` KPI 卡的 `.stat b` 字号降至 ≤ 24px(当前 24px 已是上限,不增大)。
- [ ] 测试断言:`tests/test_template_lint.py` 测试 `测试 fixture 50 条样本 + assert 默认 list 里 < li > 数 ≤ 50 + assert 切换后 = 50`。
- [ ] 测试断言:`tests/test_render.py` 渲染 memo_query 后,文本里包含 `<label for="filter"` 字面。
- [ ] pytest 全绿。
- [ ] a11y 烟雾测:用 axe-core CLI(若可用)或 lhci 验证搜索框有 name / label。无 axe 时跳过 a11y 自动化,但保留 label 手动代码检查的 commit message。

## 验证定义

完成 = 搜索框可被屏幕阅读器读出 + 长列表有 50/全部切换 + 视觉密度平衡 + pytest 全绿。
