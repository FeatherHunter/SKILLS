# 07 — `tests/test_payloads.py` 注入层安全回归

**What to build:** 模板的 `</` → `<\/` 转义 / 占位符唯一性 / `escapeHTML()` 函数都有单测；任何注入层改动不会引入 XSS 漏洞。

**Blocked by:** 01 — tests/ 测试地基

**Status:** ready-for-agent

- [ ] 单测覆盖 `escapeHTML()` 4 类输入（含 `<script>` 标签 / 引号 / 反斜杠 / 普通中文）
- [ ] 单测覆盖占位符 `<script id="payload">` 在 `query_view.html` 中恰好出现 1 次（`template.count(...) == 1`）
- [ ] 单测覆盖 `breakdown` 命令的 donut SVG 渲染非空（`<svg` 标签存在 + 至少 1 个 `<path>`）
- [ ] 单测覆盖 `</` 在 payload JSON 中被转义为 `<\/`（`assert "</script>" not in payload_str`）
- [ ] `python -m pytest tests/test_payloads.py` 退出码 0