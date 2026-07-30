---
Status: ready-for-agent
Slug: weight-history-mobile-fixes
Created: 2026-07-30
Source: /triage session · user BUG report · 查体重趋势 页面 mobile 适配
---

# Triage Notes · AGENT BRIEF

## What's broken

用户跑 `查体重趋势` 触发词,生成的 HTML (`体重_趋势_*.html`) 在手机浏览器上看有 2 个 BUG:

### BUG 1: 体重曲线在 mobile 被垂直拉伸,文字也上下拉伸
- **文件**: `templates/weight_history.html`
- **行号 95**: `<svg id="chart" viewBox="0 0 800 260" preserveAspectRatio="none">`
- **行号 34**: `svg { width:100%; height:clamp(180px, 40vh, 320px); ... }`
- **根因**: `preserveAspectRatio="none"` 让 X/Y 独立缩放。手机浏览器(高 dpi)渲染时,SVG buffer 高度 260 被 `clamp(180, 40vh, 320)` 拉到 320,viewBox 0-260 拉伸到 0-320,viewBox 内文字的 Y 坐标被拉伸(文字本身像素变扁)
- **影响**: 体重折线 + 文字标签都变形
- **重灾区**: 移动端 Safari/Chrome 100% 触发

### BUG 2: 最下方明细表格 4 列不满宽,最后一行"晨起空腹"几个字被裁切
- **文件**: `templates/weight_history.html`
- **行号 41**: `table { width:100%; ... }` (width 100%, 但内部列没定义宽度)
- **行号 207-217**: 表格行用 `insertAdjacentHTML` 拼,列宽由内容自然撑开
- **行号 44**: `tr:last-child td { border-bottom:none }` 不解决宽度问题
- **行号 100-106**: 表格在 `.table-wrap { overflow-x:auto }` 内(mobile 该滚动)
- **根因**: mobile 视口 ≤ 360px,4 列(日期/BMI/kg/delta) + note 字段总宽 > viewport。表格可滚,但用户看到最右列(注:"晨起空腹")被 viewport 右边裁切
- **影响**: 用户认为"表格没设计好",实际是 mobile 表太宽

## What's established so far

- 已确认 reproduce: 2 个 BUG 都基于真实用户 HTML(`D:\Users\辰辰洋洋\Downloads\体重_趋势_20260730_083833.html`)
- 数据完整(24 条 weight_log 记录,last: 2026-07-30 86.9kg 晨起空腹)
- 问题仅在 mobile viewport(桌面显示正常)
- 模板 line 34 SVG height clamp(commit 089e10b Phase H.7 mobile fix 引入) → 触发拉伸

## What we need from you (@implement agent)

### Fix 1: chart vertical stretch
- 把 `preserveAspectRatio="none"` 改为 `preserveAspectRatio="xMidYMid meet"` 或 `xMidYMid slice`
- 或者改 SVG `viewBox` 为动态 `containerWidth x containerHeight` + JS 端用真实容器宽算 xStep
- 推荐:用 `xMidYMid meet` + 删 `clamp()`(保留 360px 固定 height)— 简单且不破坏 viewBox 数据计算
- 同时加 `text-rendering: geometricPrecision` 改善文字清晰度

### Fix 2: table column 满宽 + mobile 适配
- `table { width:100%; table-layout: fixed }` (强制等宽分布)
- 给每列 `<th class='num' style='width:X%'>` 显式宽度
- 例如:`日期 25%` `BMI 15%` `体重 20%` `vs 上次 20%` `注 20%`
- mobile `@media (max-width:640px)`:`注` 列改 `display: none`(隐藏),或 `font-size` 调小
- 增强 `note` 列在 mobile 用 `text-overflow: ellipsis` 截断

## Acceptance criteria

- [ ] `python -m pytest tests/ -k weight_history` 全过
- [ ] `python scripts/check_html_responsive.py` 36 模板全 PASS(包括 weight_history.html)
- [ ] 用真实 user HTML(86.9kg 24天数据)在 Chrome DevTools mobile 模拟(iPhone SE 375x667):
  - [ ] chart 折线视觉正常,文字不拉伸
  - [ ] table 4 列满宽,最后一行"晨起空腹"完整可见
- [ ] 桌面 viewport (1280x800) 视觉无 regression
- [ ] commit + push(用 commit message 格式 `[卡路里] v2.5.X · weight_history mobile BUG fix`)

## Out of scope

- ticket 05 完成的 Q8 v2 dashboard(weight_volatility_v2.html)已 Canvas 化,不受此 BUG 影响
- 不改 weight_history.html 之外的模板

## Blocked by

- None — 直接 implement

## Notes

- 这是 089e10b Phase H.7 引入 mobile 适配时的"二次 bug"(加了 height:clamp 但未改 preserveAspectRatio)
- 与 ticket 05 (v2.5.7) 解 Bug 不同(v2 是 Canvas 全新模板,这里是修旧 SVG 模板的拉伸)