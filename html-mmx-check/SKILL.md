---
name: html-mmx-check
description: 验证 HTML 视觉故障是否修复 — 用户作为判官,AI 强制走完 8 步:锁 symptom / mirror 闭环 / 视觉捕获 / 三方比对 / verdict 引用证据。改 DOM 不等于修好。
disable-model-invocation: true
---

# html-mmx-check

> **用户看屏幕才是事实。**  
> DOM 数字、模型判断、修复者的口头承诺,都不是事实。

## 第一性原理

`/implement` 跑完后,AI 改 DOM → 测 DOM 数字 → 自评"已修"。但用户看的是屏幕,不是 DOM。

**根问题**:修复流程绕过了用户视角,AI 在 DOM 数字自我闭环。修复者(AI)既是选手又是裁判。

**本技能的核心**:强制让用户视角成为不可绕过的回路。所有 8 步都是为了把"用户看屏幕"变成事实。

---

## 何时使用

**全部满足**:
- `/implement` 已完成,改了 HTML 模板或渲染脚本
- 用户(你自己)有视觉症状未消除的怀疑
- 你想要硬证据:不是 AI 自评,是第三方视觉证据 + 你自己判断

## 不适用

- 改了但**没有**视觉症状(纯逻辑 bug、API 错误)
- 输出**不是** HTML(JSON / 文本 / 视频导出)
- 症状只在控制台/日志,不在屏幕

---

## 流程(8 步,不可跳)

### Step 1: 锁 symptom

读用户原话。**verbatim,一字不改**。

存为 `symptom_raw`。例:
> "体重曲线在手机上显示很小,几乎看不清楚"

**完成判据**:用户原话已被 verbatim 记录,未被改写。

不得改词。不得精简。不得"标准化"。

### Step 2: 锁 expected

问用户:
> "修好后,你期望看到什么样?"

存为 `expected_raw`。

**完成判据**:用户已回答"修好长什么样",即使只回答一个词(比如"大一点")。

### Step 3: Mirror 闭环(核心)

AI 用用户原话复述:
> "我理解您的症状是:______。修好后期望:______。对吗?"

用户:
- **确认** → 进入 Step 4
- **纠正** → AI 重新复述,循环

**完成判据**:用户**明确**说"对"或"是这个"——**不接受**"差不多"或"行吧"。

存 `symptom_aligned` + `expected_aligned`(用户确认后的版本,**逐字保留**)。

### Step 4: 渲染

Playwright 加载 HTML 文件。

**viewport 规则**:
- 用户说过具体设备(iPhone XR / iPad mini)/尺寸 → **完全匹配**
- 用户说"手机上"未明确 → 跑 **375 + 414** 两个 viewport
- 用户说"电脑"未明确 → 跑 **1280** 一个 viewport

设置 `device_scale_factor` 模拟真实设备 DPR(常用 2 或 3)。

**完成判据**:每个 viewport 成功加载 HTML,无 JS 错误,无白屏。

### Step 5: 截图

每个 viewport 出:
- 全页截图(`full_page`)
- 用户提到的元素所在 section(如有多个,都截)

命名规范:`capture_<viewport>_<section>.png`
例:`capture_414_chart.png`, `capture_414_full.png`

**完成判据**:截图文件存在,体积合理(>5KB,非空白)。

### Step 6: 视觉描述

用 `mmx vision describe` 描述截图。

**只描述,不判断**:
- ✅ "图表占据容器高度 30%,Y 轴标签 93/91/89/87/85kg,数据线粗约 2px"
- ❌ "图表看起来较小"(这是判断)

存为 `vision_raw`,逐句保留后续比对。

**完成判据**:mmx 输出存为 `vision_raw`,可逐句引用。

### Step 7: 三方比对

构造矩阵:

```
| symptom_aligned 项 | vision_raw 对应句 | expected_aligned 项 | 判定 |
| --- | --- | --- | --- |
| "很小" | "占容器 30%" | "明显大" | ❌ |
| "几乎看不清楚" | "数据线粗约 2px" | "数据清晰" | ❌ |
```

逐项映射:
- **symptom 项** == vision 中**不应有**(因为已修复)
- **expected 项** == vision 中**应有**(因为修复应达到)

**完成判据**:至少 1 个 symptom 项 + 1 个 expected 项被映射(否则 = 不可比对 = 未验收)。

### Step 8: Verdict + 引用

**Verdict 公式**:
- **PASS**: 所有 symptom 项在 vision 中**不存在** + 所有 expected 项在 vision 中**存在**
- **FAIL**: 任一 symptom 项在 vision 中**存在** OR 任一 expected 项在 vision 中**不存在**
- **PARTIAL**: 部分匹配(需说明哪些 PASS,哪些 FAIL)

**输出格式** (强制结构):

```markdown
## 验收报告

**Verdict**: PASS / FAIL / PARTIAL

**Symptom 复述** (用户确认):
> <symptom_aligned 原文>

**Expected 复述** (用户确认):
> <expected_aligned 原文>

**视觉证据** (mmx vision 描述):
> <vision_raw 关键句 1>
> <vision_raw 关键句 2>
> ...

**三方比对**:
| symptom | vision | expected | 判定 |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

**总结**: 一句话给出最终判定 + 证据链
```

**Verdict 必须引用 mmx 描述中的具体词句**。不允许"看起来 OK""应该好了""基本修复"。

**完成判据**:verdict 已输出 + 至少 1 处 mmx 描述引用 + 用户本人认可(用户是最终判官)。

---

## 守护规则(Guardrails)

1. **Mirror 不换词**:把"几乎看不清楚"改为"显示问题"或"视觉问题" = **违规**
2. **DOM 不是视觉证据**:DOM 数据(列宽、height、stroke-width)可作支持,不可单独证明"用户看得舒服"
3. **多 viewport**:用户说"手机"未明确 → 375 + 414 都跑。**单 viewport 通过 = 不可信**
4. **用户是最终判官**:即使 verdict 是 PASS,用户仍可推翻。**不要争论,以用户为准**
5. **Verdict 必带引用**:禁止"看起来 OK""应该好了""基本修复"等无证据 verdict

---

## 边界场景

### Symptom 太模糊

| 用户说 | 处理 |
| --- | --- |
| "看着不舒服" | 回到 Step 2 追问:"具体哪个元素不舒服?" |
| "不对" | 回到 Step 2:"和什么比不对?" |
| "差不多" | 回到 Step 2:"'差不多'指什么?期望值是什么?" |

### 多个 bug

每个 bug 跑独立 8 步。**不要试图一次验证多个**。

### 修复后页面崩溃

Step 4 Playwright 加载失败 / 显示白屏 → **直接 FAIL,出 Step 8 报告**。不进 Step 5-8。

### 用户修正了 symptom

Mirror 闭环中用户说"不是这个",回到 Step 1 重新读用户原话,然后重新锁 expected。

### 多次修改后验收

每次修改后**重新跑全套 8 步**。上次 PASS 不代表这次 PASS。

---

## 工具备忘

| 工具 | 用途 |
| --- | --- |
| Playwright | 加载 HTML,设 viewport,截屏 |
| `mmx vision describe` | 客观描述截图(只描述不判断) |
| `getBoundingClientRect` / `getComputedStyle` | **辅助证据**(列宽、height),不替代视觉证据 |

---

## 全流程完成判据

- [ ] Step 3: 用户**明确**说"对"或类似肯定
- [ ] Step 4: 至少 1 个 viewport 成功加载
- [ ] Step 6: mmx 输出存为 `vision_raw`,可逐句引用
- [ ] Step 8: verdict 输出 + 至少 1 处 mmx 描述引用
- [ ] 用户本人认可 verdict(用户是最终判官,verdict 是 AI 的判断而非最终判定)
