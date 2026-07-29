# 02 — memo_query 搜索与复制硬化

**What to build:**
End-to-end behavioural change:
1. 用户在搜索框输入 "心愿",**只命中 `note.content` 里含 "心愿" 的记录**,不再被 ID=37 或 UUID=abc… 全命中。
2. 用户点 "复制" 按钮,无论备忘里含 `<b>` / `<script>` 片段 / 任何 HTML entity 字符,**100% 复制成功**且剪贴板内容 = 完整原始数据。
3. 用户点页脚"复制查询回执"按钮,功能正常(不再报 `copyText is not defined` ReferenceError)。

**Blocked by:** #01 — can only start after lint infrastructure is in place (lint rules first detect → T02 fix verifies)

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `templates/memo_query.html` 第 50 行 `rows.filter(x => JSON.stringify(x).toLowerCase().includes(q))` 改为字段级,只匹配 `x.content` (与 `x.category` `x.sub_category` if 你拍板 B+;目前 A 方案 = 仅 content,且这是 user 拍板的,绝不可逆)。
- [ ] `templates/memo_query.html` 第 60 行 `data-item` 反序列化逻辑补全 5 个 entity 反解(`&lt;` `&gt;` `&quot;` `&#39;` `&amp;`),与 `esc()` 函数输出集合严格对称。
- [ ] `templates/memo_query.html` 第 61 行 `copyText` 函数被定义(命名可换:`copyText` 或 `copyToClipboard`,自己选名),功能 = `navigator.clipboard.writeText(receiptText())` + `document.execCommand('copy')` textarea fallback。
- [ ] 测试断言:`tests/test_template_lint.py` 加 fixture,输入 content 不含搜索词 + id/UUID 含搜索词的样本记录,assert filter 返回空数组(钉死决策 4 不可逆)。
- [ ] 测试断言:`tests/test_render.py` 新增或扩展,跑一遍 memo_query 渲染结果,人工肉眼确认搜 "心愿" 时 id=37 的样本不出现。
- [ ] lint 跑过:`pytest tests/test_template_lint.py` 在改完 memo_query 后仍是绿。
- [ ] pre-commit hook 跑全量测试(`pytest tests/`)全绿。
- [ ] 浏览器 smoke:用户角度手测 / 通过截图 / 通过 curl + html parse 验证 — 搜索框输入 `<script>alert(1)</script>`(用户可能写过这种 content),点"复制"按钮不报错且剪贴板 = 原文。

## 验证定义

完成 = 用户搜"37"返回 0 结果(因 content 都无"37")+ 复制含 `<` 的备忘 100% 成功 + `pytest tests/` 全绿。
