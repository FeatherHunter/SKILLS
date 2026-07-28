# 06 — `tests/test_render.py` 端到端覆盖 9 类 query_type

**What to build:** 跑 `python -m pytest tests/test_render.py` 即可验证「9 类 query_type + 空数据 + 错误 CLI 输出」都生成合法 HTML —— 模板改动有回归保护；同时覆盖 HTML BOM 字节序列。

**Blocked by:** 01 — tests/ 测试地基

**Status:** ready-for-agent

- [ ] 覆盖 9 类 query_type：summary / list / recent / search / monthly / compare / breakdown / overview / stats
- [ ] 覆盖空数据场景（DB 0 条 → HTML 含「暂无记录」卡片）
- [ ] 覆盖错误 CLI 输出（CLI 抛异常 → HTML 含 `.error-card`）
- [ ] 输出 HTML 含 `<meta charset="UTF-8">` 与 BOM（`bytes[0:3] == b'\xef\xbb\xbf'`）
- [ ] `python -m pytest tests/test_render.py` 退出码 0