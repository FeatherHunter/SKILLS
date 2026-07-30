# AGENTS.md — 卡路里

## Agent skills

### Issue tracker

Issues 以本地 markdown 文件形式存放在 `.scratch/<feature>/` 目录下。详见 `docs/agents/issue-tracker.md`。

### Triage labels

沿用 5 个默认 triage 标签(见 `docs/agents/triage-labels.md`)。

### Domain docs

单一上下文(single-context)布局。详见 `docs/agents/domain.md`。

### SoT 链(ADR-0001 · 2026-07-29)

- `卡路里.html`(根目录)= `render_help_center.py` 自动产出的最新 HELP render,**不是 SKILL.md 镜像**。
- SoT 链:`scripts/_triggers.py`(data)+ `templates/help_center.html`(presentation)→ `calorie_html/卡路里_HELP_<TS>.html`(artifact)→ `卡路里.html`(根 mirror)。
- 旧 101KB SKILL.md 镜像契约退役(详见 `docs/adr/0001-help-html-as-root-mirror.md`)。

## 视觉与 BUG 排查工作流(2026-07-30)

> 任何涉及 **HTML / CSS 渲染 / mobile 适配 / 视觉 BUG** 的工作,按以下顺序。

### 工具栈定位

| 工具 | 角色 | 准确度 | 用法 |
|---|---|---|---|
| **Playwright** (`sync_playwright`) | **主工具** | ✅ 100% 客观 | 拿 `getBoundingClientRect` / `getComputedStyle` / `scrollWidth` / `scrollHeight` / 截图 |
| **mmx vision describe** | **辅助** | ⚠️ VLM 有幻觉 | 大致感观,**不当作事实**; 后续用 Playwright 验证 |

**Playwright 是真理来源,mmx 描述是辅助信号。** 一切 VLM 报告必须经 Playwright 实测确认才采用。

### 标准流程(必走)

1. **生成 sample.html**(若需要) — 写 `sample.html` 包含真实数据 + 触发 BUG 的元素(如 `晨起空腹` 长 note)。
2. **Playwright 实测**:
   ```python
   from playwright.sync_api import sync_playwright
   with sync_playwright() as p:
       browser = p.chromium.launch()
       ctx = browser.new_context(
           viewport={'width': 375, 'height': 667},  # iPhone SE 默认
           device_scale_factor=2, is_mobile=True, has_touch=True,
       )
       page = ctx.new_page()
       page.goto(f'file:///{path.resolve()}')
       page.wait_for_load_state('networkidle')

       # 1. 测关键元素(getComputedStyle 拿真 CSS 值)
       info = page.evaluate("""() => {
         const el = document.querySelector('.target');
         const s = getComputedStyle(el);
         const r = el.getBoundingClientRect();
         return { width: r.width, color: s.color, overflow: r.scrollWidth > r.width };
       }""")

       # 2. 截图作存档
       page.screenshot(path='mobile.png', full_page=True)
       page.locator('.target-section').screenshot(path='section.png')
   ```
3. **mmx vision 看截图**(若需更广视角)— 仅用作辅助,**不当事实**:
   ```bash
   mmx vision describe screenshot.png
   ```
4. **VLM 报告必须经 Playwright 验证** — VLM 经常误读颜色 / 位置 / 文字内容。
5. **写 TDD test 锁住 fix**:
   ```python
   # 不要测 VLM 描述,测真实 CSS / DOM
   assert 'preserveAspectRatio="none"' not in html  # 测结构
   assert measured_value < threshold  # 测测量值
   ```
6. **verify_vlm_claim.py** 反例 — 每次 VLM 给一个断言,先写一个 Playwright 验证它。

### 反例(2026-07-30 教训)

VLM 说"**target 73kg dashed line isn't visibly displayed**"。听起来像"被截断"。**实际**(Playwright):

- `goalLineCount: 0` — **目标线根本没渲染**
- 真原因:JS guard `if (target && target > minY && target < maxY)` 当 `target < minY` 时不画
- VLM 误判:不是"显示但被截断",是"完全不画"

**经验**:VLM 描述 ≠ 真实状态。**永远用 Playwright 数据作准**。

### Playwright 真值清单(常用测量)

| 想测的 | 怎么测 |
|---|---|
| 元素宽高 | `el.getBoundingClientRect()` → `width/height/top/left` |
| 元素 CSS 实际值 | `getComputedStyle(el).color/background/etc` |
| 内容是否被裁切 | `el.scrollWidth > el.clientWidth` → true = 溢出 |
| 元素是否可见 | `el.getBoundingClientRect().height > 0` |
| 元素文本 | `el.textContent` |
| 整体 overflow | `document.body.scrollWidth > document.body.clientWidth` |
| mobile 模拟 | `viewport={'width': 375, 'height': 667}, device_scale_factor=2, is_mobile=True` |
| 多 viewport 测试 | 循环 3 种 viewport: 375 / 768 / 1280 |

### Playwright 工具快捷调用

```python
# 测 BUG(查真实数据)
from playwright.sync_api import sync_playwright
from pathlib import Path
with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(viewport={'width': 375, 'height': 667}, device_scale_factor=2, is_mobile=True)
    page = ctx.new_page()
    page.goto(f'file:///{Path("sample.html").resolve()}')
    page.wait_for_load_state('networkidle')
    # 测 + 截图
    info = page.evaluate("() => { ... }")
    page.screenshot(path='full.png', full_page=True)
    browser.close()

# 描述截图(辅助,不当事实)
# mmx vision describe full.png
```

### 何时 NOT 用 mmx

- ❌ 测 "是 4 列还是 5 列"(用 Playwright `getBoundingClientRect`)
- ❌ 测 "颜色是红是绿"(用 Playwright `getComputedStyle().color`)
- ❌ 测 "文字是否截断"(用 Playwright `scrollWidth > clientWidth`)
- ❌ 写 fix 后的 TDD test(VLM 描述不够精准)
- ✅ 大致感观 / 给你快速印象 / 单次偶尔用

### 提交到本 skill 的测试文件位置

`.scratch/<feature-slug>/` 下的 Playwright 测量脚本(命名 `inspect_*.py` / `verify_*.py`)+ 截图(`*.png`)+ 测量结果 JSON。

## 触发词更新

每次 BUG 修完,需在 `_triggers.py` 对应 trigger 的 cli 字段更新(如改 render script),然后 `python scripts/render_help_center.py` 重 render。详见 ADR-0001 SoT 链。
