# 10 — ADR-0006 templates 静态扫描基础设施(决策沉淀)

**What to build:**
End-to-end behavioural change:无运行时行为变化 — 是决策沉淀。完成 = `docs/adr/0006-template-lint-infrastructure.md` 入库,记录"为什么 templates 层要加静态扫描 + 为什么选 Python 纯静态 lint(选 N/A · 待票决)"的决策依据。未来读者翻 templates/test_template_lint.py 时不会把它"修掉"。

**Blocked by:** #01 — can only start after lint infrastructure is in place (本 ADR 描述的就是 T01 落地的事,先有事实再有 ADR)

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `docs/adr/0006-template-lint-infrastructure.md` 存在,内容来自 `.scratch/templates-hardening/artifacts.md` L25-37 的预制草稿(可修改措辞,但三条件都要覆盖)。
- [ ] 包含三个被否的替代方案 + 被否理由:
  - ESLint(Node) — 引入跨运行时,违背 Python 纯栈约束
  - slimit(Python 绑定) — 维护弱,跨 Python 版本兼容性弱
  - Playwright 运行时测试 — 引入浏览器二进制,跨 OS 不可控
- [ ] 包含"何时复议"条款:D-spec-01 已写(规则 1 在 memo_query 复杂 JS 段失效率 > 30% 时考虑 slimit)。
- [ ] pre-commit hook 不需修改(确认 `.githooks/pre-commit` 仍运行 `pytest tests/`,自动覆盖 `tests/test_template_lint.py`)。
- [ ] `tests/` 中已确认 `test_template_lint.py` 跑通作为触发证据。

## 验证定义

完成 = ADR 入库 + pre-commit 验证全绿 + 无运行时行为变化(纯文档)。
