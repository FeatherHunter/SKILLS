# HELP Playwright 端到端验证报告

## 截图清单

- `00_full_page.png` (711623 bytes)
- `01_initial.png` (185928 bytes)
- `02_after_toggle.png` (121132 bytes)
- `03_after_toc_jump.png` (121132 bytes)
- `04_after_copy.png` (711623 bytes)
- `05_mobile.png` (635379 bytes)

## 通过项 (13)

- ✓ h1 渲染: 居家管家 · 能力速查
- ✓ groups 渲染: 24 个(去重后 24,符合总纲 03 §铁律 2)
- ✓ 默认第一组展开
- ✓ 第一个 group 按用户视角高频: '查物品'
- ✓ scenarios 渲染: 32 个
- ✓ copy buttons: 32 个
- ✓ prompt 注入 OK: '我要查物品:\n\n请填入:\n  - 物品名: ___'...
- ✓ 折叠切换: True → False
- ✓ TOC 跳转: 6vqoe9/help.html#g-4
- ✓ copy 成功: '我要查物品:\n\n请填入:\n  - 物品名: ___'...
- ✓ XSS 防护 OK: &lt;script&gt;alert(1)&lt;/script&gt;
- ✓ 移动端视口 h1 可见
- ✓ 无 console 错误

## 问题项 (0)

