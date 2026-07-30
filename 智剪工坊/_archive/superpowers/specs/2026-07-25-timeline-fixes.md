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
- `showToast` 函数已存在(Line 4783),无需新增
- 已删段仍归入 `excluded` 列表(可恢复),行为不变

**删除按钮调用链路**(确保 toast 后用户知道怎么恢复):
- list 删除 → deleteSegment → state.segments 移除该 seg + 加入 state.excluded → renderSegmentsPanel 重画 → list 显示更新 → 已删段折叠区出现该 entry
- 用户打开"已删段"折叠区,看到「♻️ 恢复」按钮可恢复

**风险**:
- 误删无法撤销(已通过"已删段"面板恢复,保留这条路径)

**Toast 复用**:
- 用现有 `showToast(msg)` 函数(全代码库已有)

### 2.2 拆分弹窗长文本换行 + 美感(Issue #2)

**现状**:`onTrackSelect` 弹窗(Line 5098)渲染的 `segHtml` 包含:
- `.split-original`:1 个 `.split-bar.original` 显示原段时间码(短)
- `.split-results`:3 个 `.split-row`,每行有 `.split-role`(角色标签)/ `.split-time`(时间码)/ `.split-dur`(时长)

**当前无 segment label 字段**。label 实际出现在"段落列表"的 label input,而非拆分预览弹窗。如果未来要在弹窗显示段 label(供用户编辑用),再加 renderSplitRow 多一个字段 `<div class="split-label">...</div>`。

**修改点(纯 CSS,不修改 JS data 渲染)**:
- `.split-row` 容器:`word-break: break-word; overflow-wrap: anywhere; min-width: 0`(允许 flex child 收缩)
- `.split-time` / `.split-role`:`white-space: nowrap`(短字段不换行)
- `.split-bar.original`:`white-space: nowrap; max-width: 100%`(段段时间码保持单行)
- `.modal-content`:`max-width: 480px`(从现有 360 提到 480);`max-height: 80vh; overflow-y: auto`(高度长时滚动);`box-sizing: border-box`(padding 不溢出)

**Modal 现有样式**:
- 当前 `.modal-content { max-width: 360px; padding: 24px }`(Line ~1596 area)
- max-width 360 → 480 改 modal 默认宽度(visual 上更宽松)— 这是有意的提升,因为现在 modal 显示 3 行 split-row

**风险**:
- 短段无视觉变化;长 segment label 在未来加进弹窗时自动换行;modal 在窄视口(<480)下不被裁(fallback 到 viewport)

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

**坐标系正确性论证**:
- `inner.style.width` = pps × duration(直接对应 viewport 到 timeline 的秒坐标 scale)
- `trackEl.getBoundingClientRect().left` = track 可见区域左边界在屏幕的 x 坐标
- `mv.clientX - rect.left` = 鼠标在 track 可见区内的偏移
- + `trackEl.scrollLeft` = 加上已滚动的量,得到鼠标在 **inner 完整内容** 内的 x 坐标 = "绝对" 内坐标
- 除以 pps = 时间秒

各坐标系在 timeline 横向滚动 / zoom / padding 各种情况下都一致:
- 无 zoom、无滚动:`innerW == trackWidth`,scrollLeft=0,直接 clientX - rect.left 就是 inner x
- zoom 后:`innerW > trackWidth`,但 pp 和 scrollLeft 同时调整,公式仍准
- 横向滚动后:`trackEl.scrollLeft > 0`,加上即校正

**State invariants(trim 后必满足)**:
- `seg.start_sec < seg.end_sec`(永远)
- `seg.start_sec >= 0`、`seg.end_sec <= st.duration`(clamp 到 video 范围)
- 两个连续段:`A.end_sec === B.start_sec`(addOrSplit 保证,但 trim 也要保持 — 必须 clamp:left 拖动不能越过右边 - 0.1,right 同理)
- 不修改相邻段(trim 只动自己的边界)

**mouseup 后**:`renderTimelineSegments(segmentsArea, videoIndex)` 让 trim handles 重新对应 + `renderSegmentsPanel(videoIndex)` 同步 list panel(原代码只 render panel,**bug**)

### 2.4 tooltip 部分遮挡(Issue #4 — B)

**现状**:
- `.tl-tip` 在 v2.123 改回 `bottom: calc(100% + 8px)`(段条上方),`z-index: 9999`
- 复现:被遮区域是 tooltip 上半部分(超出 video area 边界)

**根因(hypothesis,需先最小复现验证)**:
- `.timeline` 容器 `overflow: visible`(v2.120),不 clip — 不是它
- `.timeline-track`(scroll-wrap)是 `overflow-x: hidden`(line 296),CSS 规范 `overflow-x: hidden` 等价 `overflow-y: auto`,会同时 clip y — tooltip 向上超出被隐
- z-index battle 候选:video 是 inline-preview-child(sibling of timeline-track),后渲染 → stacking 顺序更高。`.tl-tip` 的 z-index 9999 仍在 timeline-track stacking context 内,比不上同级 video

**审查员指出**:B1 + B2 跨浏览器行为未验证、未最小复现。**采用新路径**:先写最小 DOM repro(只用 HTML/CSS),验证遮挡原因,再选方案。

**Plan**:
1. **Phase A**:写最小 repro(伪 `.timeline-track { overflow-x: hidden }` + 上下溢出的 absolute 子),在 Chrome / Firefox / Safari 最新稳定版测试,确认是 overflow clip 还是 z-index
2. **Phase B**:基于 repro 结果选方案。两种候选:
   - **C1**:`.timeline-track { overflow-x: clip; overflow-y: visible }`(Chrome 90+、`overflow: clip` 在 Chrome 90+/Firefox 81+/Safari 16+)— 只 clip x,不 clip y
   - **C2**:`.timeline { z-index: 10 }; .inline-preview-video { z-index: 1 }` — 抬高 timeline stacking,z-index 9999 才能跨级生效
3. **采用 C1 + C2 组合**(改动小,两层防御):
   - C1 是主修复(overflow 是确认的 clip 原因)
   - C2 是辅助(让未来其他 absolute 子元素更容易 escape video)
4. **回退**:如果任一方案验证失败,只保留 C1(更简单的修复)

**不在本次范围**:
- tooltip 在 timeline 顶部空间不足时的翻转(`bottom` 改 `top`)— 简单语义,后续补
- tooltip 不得导致 timeline-track 横向滚动区域改变(tooltip 用 `left: 50%; transform: translateX(-50%)`,对内宽无影响;但修复查时手动 mousedown/mousemove 不得改 scrollLeft)

## 3. 测试策略

### 3.1 自动化(Playwright 测,必须)

| Issue | 测试 | 验证 |
|-------|------|------|
| 1 | `await page.click('seg-item 删除按钮')` | 无 confirm 模态,2 秒内 toast 出现 + state.excluded 增 1 |
| 2 | 注入超长 label 段 + 模拟 drag-to-split | 弹窗 `.modal-content` 高度 ≤ 80vh,不出现水平滚动条,长 label 换行可见 |
| 3 | `await page.locator('.tl-seg.tl-seg-has-op').nth(N).locator('.tl-seg-trim.left').dragTo(...)` | state.start_sec 改变 + width 更新;反向拖回再测 |
| 4 | `await page.hover('.tl-seg.tl-seg-has-op')` | `.tl-tip` 完全显示(top 不被裁,bottom 不被 video 遮挡) |

### 3.2 边界 case(Playwright)

- zoom 后 pps != minPps:trim 拖动仍正确(验证坐标系)
- 横向滚动后 trim 拖动仍正确
- 拖动到边界(segment 接近 0 或 duration):不崩、不越界
- tooltip 在第一段(第一个 segment) hover:不被 timeline 顶部 clip
- tooltip 在最后段 hover:不被 segments-area 底部 clip

### 3.3 视觉验证

- 三个浏览器的最新版:Chrome / Firefox / Safari(都支持 `overflow-x: clip` 和 `z-index` 简单语义)

---

## 4. 不在本次范围

- trim handle 拖拽时画面同步 video.currentTime
- 段条 click 编辑面板重新设计
- 段条拖动 reorder
- zoom 锚点保持的边界 case
- tooltip 顶部空间不足时的翻转(`bottom` → `top`)— 后续补
- tooltip 不得导致 timeline-track 横向滚动改变(已确认不影响)
- modal 在窄视口(<480) 的具体行为(由 modal-content `max-width:480 + box-sizing: border-box` 自动 fallback)
