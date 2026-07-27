# P1-9c fix · HELP 页面 5 个 BUG 全部修复

## 5 处修复
1. **payload script 移出 wrap**(放在 `<body>` 直接子元素)→ `wrap.innerHTML = html` 不再摧毁
2. **group id 改纯英文序号**(g-0, g-1, ...)+ `data-idx` 属性 → 避免中文 id 不可靠
3. **删除所有 inline onclick**,改用 `wrap.addEventListener('click', event delegation)` → 任何特殊字符不破
4. **prompt 用 JS 第二遍 `textContent` 注入**(避免属性值 escape 问题)+ 用 `data-sid` 而非整段 prompt 存 attr
5. **默认第一组直接渲染时给 `.open` 类**(`html += '<div class="group open"...')`,不再依赖后置查找

## 实现细节
- payload 注入走 `<script id="payload" type="application/json">` 标签(renderer 已支持)
- event delegation 在 `wrap` 上单次监听
- copyText() fallback: clipboard.writeText → textarea + execCommand 降级
- group 折叠靠 CSS `.group.open .scenarios { display: block }`

## 验证
- `tests/test_help_center.py` 3 用例:
  - test_help_html_static: 静态结构 + 4 处修复断言
  - test_help_html_renders: scenarios.yaml 契约合规(prompt 不暴露实现路径,7 字段齐)
  - test_help_payload_via_skills_dir: 实际跑 `home_manager.py help` 验证 payload 解析
- pytest 101/101 全过(71 + 27 routing + 3 help)

## 生成的 HTML
- 17.6 KB,31 groups,34 scenarios
- Chrome 打开路径:`.notes/HELP_fixed.html`