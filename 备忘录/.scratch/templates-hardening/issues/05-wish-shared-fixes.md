# 05 — wish_* / change_category 复制 / race / sticky 采纳按钮

**What to build:**
End-to-end behavioural change:
1. 任何 wish_plan / wish_complete / change_category 用户点 "采纳并复制" 按钮 — **无论浏览器环境如何**(桌面浏览器 / 飞书 webview / 移动端),按钮即时反馈"已复制"+ 100% 复制成功。用户不会卡在"alert:"浏览器不支持剪贴板"。
2. 用户在 wish 列表里快速勾 / 取消时,上一个 timer 不会污染下一个按钮文字(不再 race)。
3. 长 wish 列表(50 条)时,"采纳"按钮被 sticky 浮动到 viewport 底部(fixed positioning, safe-area-inset),用户无需滚到 fold 之外也能随时采纳。

**Blocked by:** None — can start immediately(独立模块,与其他 ticket 无依赖)

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `templates/wish_plan.html` / `templates/wish_complete.html` / `templates/change_category.html` 三个文件:
  - `copyToClipboard()` 函数体统一升级:`navigator.clipboard.writeText(t).then(...)` 失败 fallback 到 `document.execCommand('copy')` textarea 选区实现(防 webview clipboard 拒绝)。
  - btn 文字 timer 链路加 `clearTimeout`(每个 ticket 自己的 btn timer 互不污染)。
  - 「采纳」按钮 (`<button class="primary" onclick="adopt()">`) CSS 升级为 `position:fixed; bottom:calc(env(safe-area-inset-bottom, 12px) + 12px); right:12px;`,不破坏原 visual 比例。
- [ ] 测试断言:`tests/test_template_lint.py` 加 fixture 验三个文件的 `copyToClipboard` 函数体都含 `execCommand('copy')` 字符串(规则 3 自检通过)— 钉死"复制 fallback 必存在"语义。
- [ ] 测试断言:`tests/test_render.py` 加正则断言三个文件 HTML 里 sticky CSS 字面同时出现。
- [ ] pytest 全绿。
- [ ] 浏览器 smoke:本地手测桌面浏览器 + 模拟飞书 webview 模式,确认采纳按钮始终可见且复制成功。

## 验证定义

完成 = 三个文件的复制路径都通过 lint 守护 + 采纳按钮永远在 viewport-bottom 可见 + pytest 全绿。
