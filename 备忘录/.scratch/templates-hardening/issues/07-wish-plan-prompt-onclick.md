# 07 — wish_plan prompt 完整 + onclick 修复

**What to build:**
End-to-end behavioural change:
1. 用户采纳 50 条 wish 排期时,生成的 prompt 文本**完整可见**(不被 340px 截断),用户能完整复制 AI 指令。
2. wish 列表旁任何 `category` 字段含单引号 / `<` 等特殊字符时,`onclick="setCat('${esc(c)}')"` 不再因 HTML attribute context 下 entity 不被 JS 解析而 SyntaxError。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `templates/wish_plan.html` `<style>` 中 `pre{...max-height:340px}` 删除(或改为 `max-height:80vh`,自适应)。
- [ ] `templates/wish_plan.html` 第 53 行 `renderChips` 函数 / `onclick="setCat('${esc(c)}')"` 模式替换为 event delegation 模式:
  - 渲染时改 `data-cat="${esc(c)}"` 属性存储值(无 `onclick=` 字符串内嵌)
  - 新增一次性监听:`document.getElementById('chips').addEventListener('click', e => { if(e.target.matches('.pill')) setCat(e.target.dataset.cat) })`
- [ ] 因为 memo_query.html 内 `setCat` 函数仍存在,wish_plan 不引用 setCat,无需改 memo_query。但 wish_plan 自己的 chip 状态机不再依赖 memo_query 的 `chips` 节点(以防 setCat 找不到 `chips` DOM)。
- [ ] 测试断言:`tests/test_template_lint.py` 加 fixture 验 wish_plan 内 `pre` 元素不再有 `max-height:340px` 字面,验 `onclick=setCat` 字面不在 memo_query 之外的模板里(防止新模板写错)。
- [ ] pytest 全绿。

## 验证定义

完成 = 长 wish prompt 完整可见 + 不再有 attribute 内嵌实体解析 JS 错误 + pytest 全绿。
