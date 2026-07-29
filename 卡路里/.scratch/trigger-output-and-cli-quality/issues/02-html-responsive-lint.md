# 02 — HTML 响应式 lint 脚本(check_html_responsive.py + seam 6)

**What to build:**
A developer can run `python scripts/check_html_responsive.py` and get a clear pass/fail report naming every HTML template that lacks `@media` rules, viewport meta, or proper SVG height handling. This prevents new templates from shipping mobile-broken (the root cause of Issues 3-5).

**Blocked by:** None — can start immediately (lint script is self-contained, no dependency on test infra).

**Status:** resolved

- [ ] `scripts/check_html_responsive.py` uses BeautifulSoup to parse every `templates/*.html`
- [ ] It asserts each template contains `<meta name="viewport" ...>`
- [ ] It asserts each template contains at least one `@media (max-width:640px)` rule (or equivalent breakpoint)
- [ ] For each `<svg>` tag, it asserts the CSS `height` is not a fixed pixel value (must be `clamp()`, `auto`, `100%`, or viewport-relative)
- [ ] For each `<table>`, it asserts the table is wrapped in a `<div>` with `overflow-x:auto` styling (or has `overflow-x:auto` directly on table)
- [ ] Exit code 0 if all pass, 1 with detailed error list if any fail
- [ ] `tests/test_html_responsive.py` contains 3 cases: (a) lint passes against current templates that DO have @media (e.g., food_ranking.html); (b) lint fails against a synthetic template missing @media; (c) lint reports SVG height violation correctly
- [ ] `scripts/check_decision_matrix.py` and `scripts/check_decimal_precision.py` continue to pass (no regression)