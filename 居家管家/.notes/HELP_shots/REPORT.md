# HELP Playwright 端到端验证报告

## 截图清单

- `00_full_page.png` (659130 bytes)
- `01_initial.png` (191926 bytes)
- `02_after_toggle.png` (181086 bytes)
- `03_after_toc_jump.png` (181086 bytes)
- `04_after_copy.png` (659130 bytes)
- `05_mobile.png` (600048 bytes)

## 通过项 (13)

- ✓ h1 渲染: 居家管家 · 能力速查
- ✓ groups 渲染: 31 个
- ✓ 默认第一组展开
- ✓ scenarios 渲染: 34 个
- ✓ copy buttons: 34 个
- ✓ prompt 注入 OK: '[物品名] 坏了,在修。'...
- ✓ 折叠切换: True → False
- ✓ TOC 链接: 31 个
- ✓ TOC 跳转: 6ib8l5/help.html#g-4
- ✓ copy 成功: '[物品名] 坏了,在修。'...
- ✓ XSS 防护 OK: &lt;script&gt;alert(1)&lt;/script&gt;
- ✓ 移动端视口 h1 可见
- ✓ 无 console 错误

## 问题项 (1)

- ⚠ 第一个 group 是 '修物品'(scenarios.yaml 首项,非用户视角高频)
