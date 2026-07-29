# 01 — templates 静态扫描基础设施

**What to build:**
End-to-end behavioural change:从此以后,任何人改 `templates/*.html` 内嵌 JS 时,如果写出"调用未定义函数 / escape-unescape 不对称 / 隐藏复制按钮(违反 HTML 单工铁律)"三类典型 bug,pre-commit hook 会自动阻断并指出具体行号。用户不再遇到"点按钮就崩"或"复制失败这种静默失败"。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `tools/template_lint.py` 存在,实现三个独立入口:`lint_undefined_funcs(text) → list[(line, severity, msg)]` / `lint_escape_asymmetry(text)` / `lint_copy_fallback(text)`。每个函数纯 Python,无 Node / npm 依赖。
- [ ] `tests/test_template_lint.py` 存在并接入 pytest 栈,跑命令 `pytest tests/test_template_lint.py -q` 全绿。
- [ ] 测试类 `TestUndefinedFuncs` 至少含 1 个正例(故意引用未定义函数触发报警)+ 1 个反例(模板现有合法代码不报警)。
- [ ] 测试类 `TestEscapeAsymmetry` 至少含 1 个正例(故意构建反解 entity 集合 < 转义 entity 集合触发报警)。
- [ ] 测试类 `TestCopyFallback` 至少含 1 个正例(故意构造 `<button>` 节点无任何 handler 触发报警)。
- [ ] 三个 lint 函数实测当前 6 个 templates(memo_query / sync_report / wish_plan / wish_complete / change_category / memo_help),不产生误报(在白名单内的 HTML 按钮不报警)。
- [ ] pytest 已有 `tests/test_render.py` / `tests/test_4_state_fallback.py` 在新增后仍全绿(不破回归)。
- [ ] ADR `docs/adr/0006-template-lint-infrastructure.md` 创建,内容来自 spec.md §Further Notes 的草稿(已预制在 `.scratch/templates-hardening/artifacts.md` 中)。
- [ ] 现有 `.githooks/pre-commit` 无需修改 — 它的 `cd "$skill" && PYTHONUTF8=1 python3 -m pytest tests/` 已自动覆盖新测试文件。

## 验证定义

完成 = `pytest tests/test_template_lint.py -q` 全绿 + 当前 6 模板误报率 = 0 + ADR-0006 入库。
