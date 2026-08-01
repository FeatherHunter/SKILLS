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

### ⚠️ v1.0 场景重构期(2026-08-01 起 · 必读)

> **当前处于 v1.0 场景重设计阶段,`_triggers.py` 内 80 个 wake_word 是旧版运行时数据,不代表最终设计。**

**场景设计的唯一权威 = `.scratch/scene-index-recovered.md`**(每个场景含名称/描述/呈现数据 + 用户确认记录)。

**空白 agent 拿到 issue 后按此顺序**:
1. 读 `.scratch/scene-index-recovered.md` 对应分类章节(§1-§11)— 该分类的全部场景设计 + 用户已确认的决策
2. 读对应 `tickets/NN-分类.md`(每个 ticket 已含「权威清单」指针 + Success Criteria)
3. 按 schema `.scratch/scene_data/schema.json` 把场景填进 `.scratch/scene_data/NN-分类.json`(13 字段)
4. `python scripts/check_scene_data.py --only <分类>` 校验通过
5. **用户逐条确认后才同步**到 `scripts/_triggers.py`(最高优先级原则,不允许跳过)
6. 同步后跑 `python scripts/render_help_center.py` 重 render 卡路里.html

**已确认分类**(2026-08-01):主页 9 / 饮食 66 / 体重 58 / 运动 40(合计 173)。
**未确认分类**:健身计划 / 目标管理(已落盘 JSON 待同步)/ 基础信息 / 身体细节 / 身材照片 / 分析 / 技能协同。

**数字口径**(回答"有多少场景"时必须区分):
- 声称数 ~515(恢复文档表格) / 已确认数 173 / 已落盘 JSON 29(主页 9 + 目标管理 28 有重叠)

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

## 何时参考 SKILL开发总纲V1.0

> `D:\2Study\StudyNotes\SKILLS\SKILL开发总纲V1.0\` 是 **meta-skill 开发规范**(5-层骨架 / 触发词设计 / HTML-First / 工程仪式 / HELP 等 7 个 hook)。
> 卡路里 **已遵循** 这些规范(7 hook / SoT 链 / HTML 同步),不需要每次再读。

**只在以下情况参考总纲**:
| 场景 | 看什么 |
|---|---|
| 重构 skill 架构 / 5-层骨架 | `02-5层骨架.md` |
| 设计/调整 trigger 词 | `03-触发词设计v2.md` |
| 设计新 HTML 模板 / 改 rendering | `04-可视化与注入v2.md` |
| 新增 ticket 涉及 skill 级决策(HTML 同步 / SoT 链) | `05-工程仪式.md` + `07-HELP与场景完备性.md` |
| 概念原则(第一性原理 / 不存 deprecation 库存) | `01-第一性原理.md` |

**平时不读** — 日常修 BUG / 加 trigger / 改模板,总纲已内化,不必每次翻。

## Windows PowerShell 5.1 注意事项(2026-07-30 实战教训)

> opencode 在 win32 平台使用 **PowerShell 5.1**(非 bash,非 pwsh)。下面是踩过的坑,后续必看。

### 1. **永远用双引号包整段命令,变量内插别拆开**

```powershell
# ✅ 正确
powershell -NoProfile -Command "Get-ChildItem 'D:\2Study\foo'"

# ❌ 错误(变量被工具解析为空,导致命令被切成 4 行,前 3 行报 "is not recognized")
powershell -NoProfile -Command "$dir='D:\...'; if (-not (Test-Path $dir)) { ... }"
```

根因:工具在把命令拼到 shell 之前会做参数替换,`$dir=...` 被吃成空 → 残余 `=...` 进入 shell 被解析为 cmdlet 名。

### 2. **不要在 `-Command` 里用分号串多语句 + 变量 + 条件**

5.1 解析复杂 `if/else/foreach` 在 `-Command "..."` 单字符串里容易乱码。**拆成多行 here-doc 或直接用临时 `.ps1` 脚本**。

```powershell
# ✅ 复杂逻辑走临时脚本
$tmp = 'C:\Users\辰辰洋洋\AppData\Local\Temp\opencode\foo.ps1'
Set-Content -LiteralPath $tmp -Value @'
if (Test-Path "D:\foo") { ... }
'@
& $tmp
```

### 3. **路径含中文或空格 → 一律 `-LiteralPath` + 双引号**

```powershell
# ✅
Test-Path -LiteralPath "D:\2Study\SKILLS\卡路里\作者的笔记"
New-Item -ItemType Directory -Path "D:\2Study\SKILLS\卡路里\作者的笔记" -Force

# ❌(中文路径 + -Path 偶尔触发通配符展开)
Test-Path -Path 'D:\2Study\SKILLS\卡路里'
```

### 4. **避免 here-string (`@'...'@`) 中混用 `$` 变量**

```powershell
# ❌ $f 在 here-string 里仍会展开,但 opencode 工具链可能先一步把它换成空串
$tmp = "D:\foo"
@"
Get-Content $tmp
"@
# 输出:Get-Content  ← $tmp 被吃掉
```

**对策**:here-string 里要引用路径,先把变量拼到外层字符串,或用 `& "path with spaces.ps1" args` 调脚本。

### 5. **`&&` 不存在,用 `cmd1; if ($?) { cmd2 }`**

```powershell
# ❌
python foo.py && python bar.py   # bash 语法,5.1 不认

# ✅
python foo.py; if ($?) { python bar.py }
```

### 6. **别用 `cd`,用 `workdir` 参数**

opencode bash 工具自带 `workdir` 参数,不要在 `-Command` 里 `Set-Location`,否则下次调用又会回到默认目录。

### 7. **如需先看 PowerShell 版本**

```powershell
powershell -NoProfile -Command "$PSVersionTable.PSVersion"
# 应显示 5.1.xxxxx
```

### 8. **opencode 临时目录**

`C:\Users\辰辰洋洋\AppData\Local\Temp\opencode` 已存在且可写,可放心落临时 `.ps1` / `.html` / 截图等。

### 9. **如果命令反复报 "is not recognized",先看错误行首有没有 `=xxx` 或孤立变量**

这是工具链把命令里某段吃掉后留下的残骸。**改写命令结构**(拆变量、换 here-string、改 `-File` 调脚本)即可,不必调 PowerShell。
