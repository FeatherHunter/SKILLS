# HELP Playwright 端到端验证报告

## 截图清单

- `00_full_page.png` (739934 bytes)
- `01_initial.png` (73969 bytes)
- `02_after_toggle.png` (246398 bytes)
- `03_after_toc_jump.png` (246398 bytes)
- `04_after_copy.png` (739934 bytes)
- `05_mobile.png` (661939 bytes)
- `07_prompt_empty.png` (1977 bytes)

## 通过项 (12)

- ✓ h1 渲染: 居家管家 · 能力速查
- ✓ groups 渲染: 11 个(按 A 套 11 类)
- ✓ 默认全部折叠
- ✓ 第一个 group 按 A 套任务导向: '找东西'
- ✓ scenarios 渲染: 32 个
- ✓ copy buttons: 32 个
- ✓ prompt 注入 OK (即使折叠也保留): '我要查物品:\n\n请填入:\n  - 物品名: ___'...
- ✓ 折叠切换: False → True
- ✓ copy 成功: '我要查物品:\n\n请填入:\n  - 物品名: ___'...
- ✓ XSS 防护 OK: &lt;script&gt;alert(1)&lt;/script&gt;
- ✓ 移动端视口 h1 可见
- ✓ 无 console 错误

## 问题项 (1)

- ✗ TOC 跳转 URL 未变: file:///tmp/tmpufrwqgea/help.html#cat-4
