# P1-9c-fix-2 · Playwright 闭环发现 3 个真 P0 + 修复

## 来源
`HELP_playwright_test.py` 用 Chromium 1223 headless 真实渲染 + 截图。
LLM 看图 (`01_initial.png`) 直接识别 P0。

## 修复 3 个真 P0

### P0-A · shared.js 函数源码泄漏到页面顶部
- **症状**:截图顶部显示 `function esc(s){return String(...)...` raw JS
- **根因**:模板 `<script><!--SHARED-HELPERS--></script>` 被 renderer `string.replace` 注入 SHARED_JS,但**占位符之前**又有 `<!--INJECT-DATA-->` 被 JSON payload 替换——两个占位符**都在 body 内裸的**,JSON 被当文本显示,SHARED_JS 也被当文本显示
- **修复**:把两个占位符都放进 `<script>` 标签:
  ```html
  <script id="payload" type="application/json"><!--INJECT-DATA--></script>
  <script><!--SHARED-HELPERS--></script>
  ```

### P0-B · help_center.py 按字母序排序(而不是 yaml 顺序)
- **症状**:`sort(grouped.items(), key=lambda x: x[0])` → '合标签'(h)排第一,而不是'查物品'
- **根因**:sorted 默认字符串字典序
- **修复**:用 `seen` set 按 yaml 第一次出现顺序遍历
  ```python
  for s in scenarios:
      if ww not in seen:
          seen.add(ww)
          groups.append({"wake_word": ww, "scenarios": grouped[ww]})
  ```
- **现在首 5 wake_word**:`查物品 / 看物品 / 录物品 / 拍物品 / 改物品`(用户视角高频)

### P0-C · 违反总纲 03 §铁律 2(同义合并)
- **症状**:scenarios.yaml 有 7 个 update 子项 wake_word(修/借/废/移/补/减/标物品)
- **修法**:scenarios.yaml 重排为 13 章节(查询→录入→更新→盘点→穿搭→旅游→统计→标签→快递→账号→元数据→HELP),update 7 子项合并到 6 个 "改物品" 变体场景

## 净效果
- groups: 31 → **24**(7 个 update 子项合并)
- scenarios: 34 → **32**(2 个旧场景被新 6 个变体场景替代)
- 一致性:首 group 是查物品(用户视角),不是修物品(yaml 写入顺序)

## Playwright 验证结果
```
passed: 13, issues: 0
```

13 项断言全过:
- ✓ h1 渲染: 居家管家 · 能力速查
- ✓ groups 渲染: 24 个(去重后)
- ✓ 默认第一组展开
- ✓ 第一个 group 按用户视角高频: 查物品
- ✓ scenarios 渲染: 32 个
- ✓ copy buttons: 32 个
- ✓ prompt 注入 OK
- ✓ 折叠切换
- ✓ TOC 链接: 24 个
- ✓ TOC 跳转
- ✓ copy 成功
- ✓ XSS 防护 OK
- ✓ 移动端视口

## 截图清单
- `01_initial.png` (20:20) — 首屏全页
- `02_after_toggle.png`
- `03_after_toc_jump.png`
- `04_after_copy.png`
- `05_mobile.png`
- `00_full_page.png`

## 用户测试方法
```bash
python3 /mnt/d/2Study/StudyNotes/SKILLS/居家管家/.notes/HELP_playwright_test.py
```

修改 `help_center.html` 或 `scenarios.yaml` 后跑一次即自动验证全闭环。