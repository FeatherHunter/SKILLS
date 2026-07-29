# 06 — 查热量 HTML 端到端(新模板 + render + ADR-0005 部分)

**What to build:**
A user saying 查热量 "牛肉" gets an HTML page with one card per matching food product (instead of 32 rows dumped to terminal). Each card shows calories / protein / carbs / fat / sodium / source and is mobile-readable. This is the root-cause fix for Issue 1 ("查热量 生的牛肉 没有 HTML").

**Blocked by:** 01 — test isolation needed so render tests don't pollute prod DB.

**Status:** ready-for-agent

- [ ] New file `templates/food_search.html` exists, follows the Apple-system styling already established by `food_ranking.html`, and has `@media (max-width:640px)` rules (passes check_html_responsive.py)
- [ ] Layout: header with query echo + match count; one card per food matching the search term; each card shows 4 macros prominently + brand + source + updated_at; mobile layout is single-column stacked
- [ ] New file `scripts/render_food_search.py` exists, takes `--query <str>` and `--output <path>` (default `calorie_html/查热量_<YYYYMMDD>_<HHMMSS>.html`), reads from the DB via `nutrition_products` table
- [ ] HTML contains `<!--INJECT-DATA-->` placeholder (per spec §"占位符唯一" rule), and the script substitutes it with `window.__DATA__ = { ... }` JSON
- [ ] `tests/test_food_search.py` covers seam 1+2: (a) `render_food_search.py --query 牛肉 --output /tmp/x.html` exits 0; (b) generated HTML contains 5+ food cards; (c) `window.__DATA__.query == '牛肉'`; (d) `window.__DATA__.items.length >= 5`
- [ ] `SKILL.md` §触发词速查表 entry for 查热量 updated to list `python scripts/render_food_search.py --query "<term>"` as the CLI
- [ ] `SKILL.md` §完整 HTML 模板清单 gains a row for `food_search.html` with trigger `查热量`