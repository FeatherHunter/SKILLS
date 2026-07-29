# ADR-0004: 作息管家 HELP Toast UI 对齐卡路里 v2.4.12(scope creep 纳管)

作息管家 HELP HTML 的 Toast 提示元素升级为 iOS 通知风格(对标卡路里 v2.4.12)— 📋 icon + 绿色 em 标题(含已复制唤醒词) + "粘贴给 AI(微信/飞书/任何 AI 工具),作息管家技能会自动执行这个流程,完成后你会在飞书收到 HTML" 详情 + ✓ 知道了 关闭按钮 + backdrop-filter + elastic curve 动画。

## 背景

作息管家 v1.1.3 在 2026-07-28 Grilling Session 期间完成 Phase A-3 + Q5 + Q6 + Q7 重构(commit 6ebe69c / c17d490 / f092476 等),help_center.html 升级到 73 场景 + 5 模块 + 复制 prompt 按钮 + 折叠分组。Grilling Session 8 决策 + 3 份 ADR(0001/0002/0003)均**未涉及** Toast UI 的视觉风格 — spec §07 / §11 只要求"复制 prompt 按钮"+"剪贴板 fallback"+"Toast 视觉反馈"三层契约。

工作进行到 2026-07-29 时,用户口头要求"对齐卡路里 HELP 的 iOS 通知风格"。这是**计划外的工作**(scope creep),需本 ADR 纳管。

## 理由

1. **跨 Skill 一致性**:作息管家 / 卡路里 / 备忘录 三个 Skill 都用「打开浏览器看 HTML」心智模型;若 Toast 风格三家不一,用户跨 Skill 操作时体验割裂
2. **信息密度提升**:原 Toast 只有"已复制 · 粘贴给 AI"6 个字,iOS 风格 Toast 明确告知「粘给微信/飞书/任何 AI 工具,技能自动执行,完成后飞书收到 HTML」— 闭环叙事更完整
3. **设计语言现代化**:backdrop-filter + elastic curve(cubic-bezier(0.34, 1.56, 0.64, 1))是 2026 年 iOS 通知的标准,符合用户视觉预期

## 范围(实施内容)

### 1. HTML 结构(对标卡路里 v2.4.12)

```html
<div id="toast" class="toast" role="status" aria-live="polite">
  <div class="toast-icon">📋</div>
  <div class="toast-body">
    <div class="toast-title">已复制 <em id="toastWake">prompt</em></div>
    <div class="toast-detail">粘贴给 AI(微信/飞书/任何 AI 工具),作息管家技能会自动执行这个流程,完成后你会在飞书收到 HTML</div>
  </div>
  <button class="toast-close" id="toastClose">✓ 知道了</button>
</div>
```

### 2. CSS(iOS 通知风格)

```css
.toast {
  position: fixed; left: 50%; bottom: 32px;
  background: rgba(28, 28, 30, 0.94);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  backdrop-filter: blur(20px) saturate(180%);
  ...
  transition: ... cubic-bezier(0.34, 1.56, 0.64, 1);  /* 弹性曲线 */
}
.toast-title em { color: #4dd96b; }  /* 绿色 em 强调 */
@media (max-width: 640px) { ... }  /* 移动端适配 */
```

### 3. JS(全局事件代理)

`showToast(wake)` 函数从父级 `.ww-block > .ww-name` 取唤醒词名 + 拼接场景标题,toast 显示"已复制 #6 查作息 · 单日查看"。点击关闭按钮或 4.5s 自动消失。

### 4. 触发时机

- 复制 prompt 按钮点击 → 立即显示 toast(含具体唤醒词 + 场景标题)
- 4.5s 自动消失(或用户点 ✓ 知道了 立即关)

## 考虑过的替代方案

- **方案 A · 不做**:保持作息管家原 Toast 单字符串"已复制 · 粘贴给 AI"。**拒绝** — 与卡路里/备忘录跨 Skill 不一致,信息密度低
- **方案 B · 仅做 icon + 标题**:不做 backdrop-filter 和 elastic curve。**拒绝** — 失去了 iOS 通知风格的核心特征,只是半截改
- **方案 C · 完全对标卡路里**(本方案)— 所有视觉/文案/动效/响应式全对齐。**接受** — 跨 Skill 一致性优先

## 后果

1. **正面**:跨 Skill 一致体验 · iOS 风格现代化 · 闭环叙事完整(粘给 AI → AI 自动执行 → 飞书收 HTML)
2. **负面**:
   - 文案"完成后你会在飞书收到 HTML"对非飞书用户不友好(但本 Skill 主要用户就是飞书环境)
   - 新增 ~135 行 CSS / HTML(模板更大,HTML 离线文件 +~5KB)
3. **影响文件**:`templates/help_center.html`(+~135 行),作息管家.html 镜像同步(ADR-0001 自动)

## 触发重新评估的条件

满足任一即重新评估是否调整:

1. 跨 Skill 用户的反馈不一致(卡路里/备忘录投诉 Toast 风格不同)
2. 文案"飞书收到 HTML"被吐槽(改为通用"AI 工具"等)
3. iOS 通知风格被取代(2027 年新设计语言出现)

## 后续可改进点(scope creep,非本次)

- 把 4.5s 自动消失改为"用户主动关"或"点击页面任意处关"
- Toast 显示当前打开的飞书/微信会话名(需集成会话)
- Toast 支持链式(连点复制多个 prompt,Toast 队列展示)

## Status

`accepted` · 2026-07-29 · 用户口头要求 + ADR 纳管 · commit 5ceccb7 / 63cb8b6 落地