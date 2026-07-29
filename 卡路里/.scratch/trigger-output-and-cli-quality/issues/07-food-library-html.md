# 07 — 查食品库 HTML 端到端 + list-products 默认 200(ADR-0005 部分)

**What to build:**
A user saying 查食品库 gets an HTML page listing 200 food products by default, with pagination + a search box to filter, and a `--all` CLI flag for the rare case of full 1924-row export. This is the root-cause fix for Issue 2 ("查食品库 默认只 50 条" + "返回 txt 而不是 html").

**Blocked by:** 01 (test isolation), 06 (shares the new-HTML-template pattern established by 查热量 — reuses template style and render script structure).

**Status:** resolved

- [ ] `calorie_tracker.py list-products` default LIMIT is 200 (Q5); add `--all` flag to disable LIMIT and return all rows; add `--text` flag (paired with 04's escape hatch) to return plain text for pipeline users (R2 mitigation)
- [ ] New file `templates/food_library.html` exists, follows the Apple-system styling; layout: header with row count + search box + pagination controls; table-style or card-grid of all food products; mobile-responsive (passes check_html_responsive.py)
- [ ] Pagination strategy: 50 rows per page client-side (full data in `window.__DATA__`, JS does pagination); search box filters live on the client
- [ ] New file `scripts/render_food_library.py` exists, takes `--limit <int>` (default 200), `--all`, `--text`, and `--output <path>` (default `calorie_html/查食品库_<YYYYMMDD>_<HHMMSS>.html`)
- [ ] HTML uses `<!--INJECT-DATA-->` placeholder and `window.__DATA__` JSON injection (consistent with 06)
- [ ] `tests/test_food_library.py` covers seam 1+2: (a) `render_food_library.py` exits 0 with default 200; (b) `--all` returns all 1924 rows; (c) HTML contains pagination controls; (d) `window.__DATA__.total_count == 1924`; (e) `--text` returns plain text (not HTML) — important for pipeline users (R2 mitigation verification)
- [ ] `tests/test_cli_validation.py` extended with case: `calorie_tracker.py list-products --help` exits 0 and mentions `--all` and `--text`
- [ ] `SKILL.md` §触发词速查表 entry for 查食品库 updated; §完整 HTML 模板清单 gains a row