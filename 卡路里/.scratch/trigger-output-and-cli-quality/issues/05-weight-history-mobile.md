# 05 — weight_history.html 移动响应式(Q3 落地)

**What to build:**
A user opening 查体重历史 / 对比体重 / 查体重波动 on a phone sees a layout that fits: 4-column KPI grid stacks vertically, the SVG chart height adapts to viewport, and the data table scrolls horizontally inside its own section without breaking the page. This is the root-cause fix for Issues 3-5's "ugly on phone" complaints.

**Blocked by:** 02 — the lint script must exist so this ticket's changes can be verified against the seam 6 standard.

**Status:** resolved

- [ ] `templates/weight_history.html` CSS includes `@media (max-width:640px)` rules that:
  - collapse `.kpi-grid { grid-template-columns: repeat(4, 1fr) }` to a single column or 2-column layout on small screens
  - adjust `.section { padding: 22px 26px }` to smaller mobile-safe values
  - hide or compress non-essential UI elements (e.g., footer .src text)
- [ ] All `<svg>` tags in the template use `height: clamp(180px, 40vh, 320px)` or similar viewport-relative sizing (not fixed `260px`)
- [ ] Every `<table>` is wrapped in `<div class="table-wrap" style="overflow-x:auto">` so horizontal scroll stays inside the section
- [ ] The four weight modes (history / trend / compare / volatility) all share the responsive CSS without per-mode special cases (Q3 spirit: one template, one CSS)
- [ ] `python scripts/check_html_responsive.py` exits 0 against the modified `weight_history.html`
- [ ] `python scripts/render_weight_history.py --days 30 --mode history --output /tmp/test.html` produces a file that, when opened on a 375px-wide viewport (iOS), shows no horizontal page overflow (manual verification or Playwright snapshot if available)
- [ ] `tests/test_redesign.py` existing seam 1+2 tests still pass against the modified template (no DOM regression)