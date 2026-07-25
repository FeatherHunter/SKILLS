# 智剪工坊 Timeline UX 修复 Spec

**作者:** AI(经 brainstorming 流程)
**创建日期:** 2026-07-25
**对应 Skill:** 智剪工坊-意图编辑
**状态:** 待用户审阅

---

## 1. 背景

用户在 2026-07-25 当前会话(v2.132 之后)反馈 4 项 timeline 相关问题:

1. 删除按钮点击时仍弹 `confirm()` 模态 — 期望仅 toast 提示
2. 拆分确认弹窗未处理长文本换行 — 段多时内容可能溢框
3. timeline 段条的左右 trim handle 拖拽无效果
4. 段条 hover 的气泡 `.tl-tip` 被部分遮挡(用户反馈为"上半被遮")

本 spec 给出 4 项的最小修复方案(贴合现有代码结构,避免大改)。

---

## 2. 设计

### 2.1 删除按钮 toast 化(Issue #1)

**现状**:`deleteSegment(videoIndex, segId)` 函数(line ~5167)开头有 `if (!confirm(...)) return;`

**修复**:
- 删 `confirm()` 调用,改为直接执行删除
- 调用 `showToast('已删除: 「' + label + '」')` 通知用户
- 已删段仍归入 `excluded` 列表(可恢复),行为不变

**风险**:
- 误删无法撤销(已通过"已删段"面板恢复,保留这条路径)

**Toast 复用**:
- 用现有 `showToast(msg)` 函数(全代码库已有)

### 2.2 拆分弹窗长文本换行 + 美感(Issue #2)

**现状**:`onTrackSelect` 弹窗用 `showInformDialog` + `segHtml`,内容是简单 `<div>[start~end] label</div>` 列表段 3 段。CSS 已加 `.split-preview` / `.split-row`(v2.126),但内容里只有 `seg-start~end role` 字段,无 overflow 处理。

**修复 CSS**:
```css
.split-row { word-break: break-word; overflow-wrap: anywhere; }
.split-time, .split-role { white-space: nowrap; }  /* 时间 / 角色保持单行 */
.split-bar.original { white-space: nowrap; }  /* 标签也单行 */
.modal-content { max-width: 480px; max-height: 80vh; overflow-y: auto; }
```

即:时间码 / role / 标题不换(短),长 label 才换行。

**风险**:
- 短段无变化,长段现在换行美观

### 2.3 trim handle 拖拽(Issue #3 — 根因已查明)

**根因**(已 Phase 1 复现+v2.114 修复验证):
- trim handle listener 在 `renderTimelineSegments` 函数闭包内(Line 5100+)
- 闭包内引用了 `duration` / `trackWidth` / `track` — **这些在 `renderTimelineSegments` 闭包中不存在(undefined)**
- `track.getBoundingClientRect()` 抛 TypeError: Cannot read properties of undefined
- 静默 catch,moveH 直接 return → state 不变

**修复**:
```js
const inner = segmentsArea.closest('.timeline-inner');
const trackEl = segmentsArea.closest('.timeline-track');
const moveH = (mv) => {
  const innerW = parseFloat(inner?.style.width) || 0;
  const pps = innerW / (st.duration || 1);
  const trackRect = trackEl.getBoundingClientRect();
  const innerOffsetX = mv.clientX - trackRect.left + (trackEl.scrollLeft || 0);
  const t = Math.max(0, Math.min(st.duration, innerOffsetX / pps));
  ...
};
```

不依赖 setupTimeline 闭包变量,全部 DOM/state 实时取。

**mouseup 后**:增加 `renderTimelineSegments(segmentsArea, videoIndex)` 让 trim handles 重新对应(原代码只 render panel)

### 2.4 tooltip 部分遮挡(Issue #4 — B)

**现状**:
- `.tl-tip` 在 v2.123 改回 `bottom: calc(100% + 8px)`(段条上方),`z-index: 9999`
- 复现:被遮区域是 tooltip 上半部分(超出 video area 边界)

**根因**:
- `.timeline` 容器 `overflow: visible`(v2.120),不 clip — 不是这个原因
- `.timeline-track`(scroll-wrap)是 `overflow-x: hidden` 但 tooltip 是 `.timeline-inner` 内的 absolute 元素 — clip 来自这里!
- `overflow-x: hidden` 也会 clip `overflow-y`,导致 tooltip 上下方向超出后被隐藏
- 加上 z-index battle: video 是 inline-preview 子(sibling of timeline),后渲染 → 在 stacking 顺序更高。`.tl-tip` z-index 9999 不够,因为 stacking context 的边界问题

**修复两步**:
1. `.timeline-track { overflow-x: clip }`(只 clip x,不 clip y)— 或者 `overflow: clip`(明确 clip)
2. `.tl-tip { position: fixed }` 改 fixed 定位,脱离 `.timeline` stacking context;JS 计算位置 = clientX, top = segmentRect.top - tooltipHeight - 8

固定定位方案成本高(re-render 时 segment DOM 变化需重计算)。轻量方案:
- **B1**:**只 clip x 不 clip y**:`.timeline-track { overflow-x: clip; overflow-y: visible; }`(或 `overflow: clip`,Chrome 90+ 支持)— 简单
- **B2**:z-index fight:给 video 设 `z-index: 1` 给 `.timeline` 设 `z-index: 10`,tooltip 自动在新 stacking context 中最高

**采用方案**:B1 + B2 组合(改动小,两层防御)
- B1:`.timeline-track { overflow-x: clip; overflow-y: visible }`(关键修复)
- B2:`.timeline { z-index: 10 }` + `.inline-preview-video { z-index: 1 }`(进一步防御)

---

## 3. 测试策略

- issue 1:手动点击 list 删除按钮 → 应立即看到 toast,无 confirm 模态
- issue 2:label 设超长字符串(50 字符),触发拆分 → 弹窗正常换行,无溢出
- issue 3:鼠标拖动中间段左 trim handle 向左 50px → state 改变,segment 宽度更新
- issue 4:hover 较长 label 段 → tooltip 完整显示,不被 video 遮挡

---

## 4. 不在本次范围

- trim handle 拖拽时画面同步 video.currentTime
- 段条 click 编辑面板重新设计
- 段条拖动 reorder
- zoom 锚点保持的边界 case
