# 08 — change_category `.from` 中性化 + 复制 fallback

**What to build:**
End-to-end behavioural change:
1. 用户看到 "原分类 → 新分类" 的 flow 视觉时,"原分类"chip 不再用红色(不再暗示"危险 / 警告")—— 改为中性灰 + 1px border,显得只是"原状态"。
2. 用户在 change_category 页面点 "采纳并复制" 按钮,任何浏览器下 100% 复制成功(已含在 T05 里,本 ticket 范围重叠)。

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `templates/change_category.html` 第 32 行 `.flow .from{background:var(--err-soft);color:var(--err);padding:8px 16px;border-radius:14px}` 改为中性:
  ```
  .flow .from{background:var(--bg);color:var(--fg2);padding:8px 16px;border-radius:14px;border:1px solid var(--line)}
  ```
- [ ] `.flow .to` 同样从绿色 `#ecfff2/#178a3a` 收敛为同等亮度的中性色(避免情绪化二极)。新 `.to`:
  ```
  .flow .to{background:var(--soft);color:var(--blue2);padding:8px 16px;border-radius:14px}
  ```
- [ ] (本 ticket 与 T05 范围重叠的复制 fallback 部分由 T05 全量处理,本 ticket 在 T05 落地后不再重复改。) lint 规则不重复检查——T05 一致。
- [ ] 测试断言:`tests/test_template_lint.py` 加 fixture 验 change_category `.flow .from` CSS 不再含 `var(--err-soft)` 字面。
- [ ] 测试断言:`tests/test_render.py` 加正则断言新 CSS 字面字串 `border:1px solid var(--line)` 同时出现在 `.from` 块。
- [ ] pytest 全绿。

## 验证定义

完成 = 原分类 chip 不再红色 + 分类之间视觉无道德化暗示 + pytest 全绿。
