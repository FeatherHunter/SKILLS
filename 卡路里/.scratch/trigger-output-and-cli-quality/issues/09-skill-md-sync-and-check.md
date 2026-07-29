# 09 — SKILL.md 全面同步 + check_trigger_consistency 升级(ADR-0005 enforcement)

**What to build:**
After all the upstream slices land, SKILL.md and the trigger-consistency checker reflect the new reality: every 查询 trigger is mapped to an HTML template, the §⚠️ 强制性规定 contains 7 numbered rules, and `check_trigger_consistency.py` rejects any drift (new trigger added without a template). This is the consolidation ticket — it cannot land until the upstream tickets that introduce new triggers/templates have landed.

**Blocked by:** 04 (CLI changes are stable), 05 (mobile CSS shipped), 06 (查热量 HTML shipped), 07 (查食品库 HTML shipped), 08 (AI protocol documented).

**Status:** ready-for-agent

- [ ] `SKILL.md` §完整 HTML 模板清单 has rows for `food_search.html` and `food_library.html` added (incremental from prior spec card-html-redesign)
- [ ] `SKILL.md` §触发词速查表 entries for 查热量, 查食品库, 体重三件套(历史/对比/波动), 查体重目标 all reference the correct render script (CLI column updated)
- [ ] `scripts/check_trigger_consistency.py` is upgraded from "3-edge consistency" to "3-edge + HTML-First enforcement": it scans §完整 HTML 模板清单, identifies every trigger marked ✅, and asserts that the corresponding `scripts/render_*.py` exists AND that the SKILL.md frontmatter trigger list contains that trigger name. New triggers without templates cause exit code 1
- [ ] `scripts/check_decision_matrix.py` still passes (no regression from the spec's §04 决策矩阵 updates)
- [ ] `tests/test_trigger_consistency.py` (or extend existing) covers 2 cases: (a) all current triggers pass HTML-First check; (b) a synthetic trigger added without a template causes exit code 1
- [ ] `SKILL.md` §⚠️ 强制性规定 has exactly 7 numbered rules (HTML同步 / 优先级 / 变更确认 / HTML-First / Wizard Verify / 写库回执契约 / AI 验证协议)
- [ ] `python scripts/check_trigger_consistency.py` exits 0 against current state
- [ ] `pytest tests/` exits 0 with all 9+ ticket test files passing