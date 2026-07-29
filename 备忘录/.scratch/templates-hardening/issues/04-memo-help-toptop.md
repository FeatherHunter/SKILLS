# 04 — memo_help 命名统一与回顶按钮

**What to build:**
End-to-end behavioural change:
1. 用户从 SKILL.md 链接点 / 从 URL 直接打开 memo_help.html 时,浏览器 tab 标题 / hero eyebrow / h1 主标题三处文案一致并符合视觉层级。
2. 用户滚到第 5 屏 (29 个场景全部展开) 后,右下角出现 sticky "回到顶部" 按钮,点一下平滑滚回 hero。

**Blocked by:** None — can start immediately(独立模块,与其他 ticket 无依赖)

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `templates/memo_help.html` 三处文案统一为:`<title>备忘录 · HELP 使用手册</title>` / eyebrow `Memo Help` / h1 `备忘录 · 使用手册`(其他别名固定)。三处不再出现不同的版本号 / 不同的全名/缩写。
- [ ] `templates/memo_help.html` 加右下角 sticky 按钮(节点 `<button class="back-to-top" aria-label="回到顶部">↑</button>`),CSS 浮动,fade-in 显示(用户滚 200px 后才出现)。
- [ ] JS:点击 `back-to-top` 按钮 → `window.scrollTo({top:0, behavior:'smooth'})`。
- [ ] 测试断言:`tests/test_render.py` 加正则断言三处文案字面同时出现。
- [ ] 测试断言:`tests/test_template_lint.py` 加 fixture 验 `back-to-top` 按钮有对应 `.addEventListener('click'` handler(规则 3 自检通过)。
- [ ] pytest 全绿。

## 验证定义

完成 = 三处文案一致 + 回顶按钮可点 + pytest 全绿。
