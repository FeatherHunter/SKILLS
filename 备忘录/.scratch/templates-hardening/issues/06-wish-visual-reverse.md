# 06 — wish_* checkbox 视觉方向反转

**What to build:**
End-to-end behavioural change:
1. wish 列表里,用户看到"已勾选心愿"—— 这条心愿 visual 是 line-through + opacity:.5 状态(代表已纳入采纳,准备执行)。
2. 用户看到"未勾选心愿"—— 这条心愿 visual 是正常 font + 正常 opacity(代表未纳入,不被采纳)。
3. 用户切换 checkbox 时,视觉变化方向与"已操作"语义一致(已勾 = 划掉,未勾 = 正常)。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `templates/wish_plan.html` 第 28-30 行 `.wish.off` 样式改为 `.wish.on`(语义从"关闭"反转到"打开/已采纳")。CSS:`.wish.on{opacity:.5}.wish.on .content{text-decoration:line-through}`。其他位置引 `.off` 同步改 `.on`。
- [ ] `templates/wish_complete.html` 同步:本文件 `.wish.off` 一并反转。
- [ ] JS event handler(`renderList()` 里的 `e=>{...classList.toggle('off',!e.target.checked)}`)同步改为 `classList.toggle('on',e.target.checked)` — 语义反转。
- [ ] 已有注释里"opacity:.5 (.off class) 仅在用户切换 checkbox 时由 event handler 动态加"的描述同步改 `.on`。
- [ ] 测试断言:`tests/test_template_lint.py` 加 fixture 验 wish_plan / wish_complete `renderList` 内 event handler 含 `classList.toggle('on'` 字面(钉死反转后语义一致)。
- [ ] pytest 全绿。

## 验证定义

完成 = 用户切 checkbox 时 line-through 出现在"已勾选"行 + pytest 全绿。
