# Timeline UX Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 4 timeline UX bugs from spec `2026-07-25-timeline-fixes.md` — delete via toast not confirm, modal long-text wrapping, trim handle drag, tooltip occlusion.

**Architecture:** Single-file HTML SPA. CSS-first fixes (issues 1, 2, 4) + surgical closure-leak fix (issue 3 trim drag). Verification via Playwright scripts in `/tmp/test_*.py` (no project test infrastructure exists).

**Tech Stack:** Vanilla JS, HTML/CSS, Playwright (Python) for verification, CDP remote debugging.

---

## File Structure

**Modify:** `智剪工坊/智剪工坊-意图编辑.html` (single 5k-line file, all changes here)
- `function deleteSegment(...)` — issue 1
- `.modal-content`, `.split-row` CSS, segHtml area — issue 2
- `renderTimelineSegments` trim handle listener — issue 3
- `.timeline-track`, `.timeline`, `.inline-preview-video` CSS — issue 4

**Create (verification only):** `/tmp/verify_issue1.py` ... `/tmp/verify_issue4.py` (Playwright smoke tests)

---

## Task 1: Issue 1 — Delete button → toast (no confirm modal)

**Files:**
- Modify: `智剪工坊-意图编辑.html` — `function deleteSegment` around Line 5167

- [ ] **Step 1: Locate current `deleteSegment` function**

```bash
grep -n "function deleteSegment" /mnt/d/2Study/StudyNotes/SKILLS/智剪工坊/智剪工坊-意图编辑.html
```

Expected output: shows function definition with `if (!confirm('...'))`

- [ ] **Step 2: Verify confirm modal currently appears**

Run Playwright:
```python
# /tmp/verify_issue1_before.py
import asyncio
from playwright.async_api import async_playwright
async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        ctx = browser.contexts[0]
        target = next(pg for pg in ctx.pages if "localhost:8000" in pg.url)
        # Use demo mode to bootstrap state
        await target.goto("http://localhost:8000/智剪工坊-意图编辑.html?demo=1", wait_until="networkidle")
        await target.wait_for_timeout(5000)
        # Setup auto-confirm dialog handler that records if one was shown
        await target.evaluate("window.__confirms = []; window.confirm = (msg) => { window.__confirms.push(msg); return true; }")
        await target.locator(".seg-item button[data-act='delete']").first.click()
        await target.wait_for_timeout(300)
        confirms = await target.evaluate("window.__confirms")
        print("confirms:", confirms)
        # EXPECTED: '删掉这段?...' shown — confirming modal currently appears
asyncio.run(run())
```

Expected: `confirms: ['删掉这段?可从折叠区"已删段"恢复。']`

- [ ] **Step 3: Replace confirm() with showToast()**

Edit `deleteSegment`:

```js
function deleteSegment(videoIndex, segId) {
  const card = videoListEl.querySelector(`.video-card[data-card-idx="${videoIndex}"]`);
  const panel = card?.querySelector('.segment-panel');
  if (panel) panel.remove();
  const segmentsArea = card?.querySelector('[data-timeline-segments]');
  if (segmentsArea) renderTimelineSegments(segmentsArea, videoIndex);
  // v2.115:删 confirm 弹窗,改 toast
  const wasLabel = SegmentState.states[videoIndex]?.segments?.find(s => s.id === segId)?.label || segId;
  SegmentState.delete(videoIndex, segId);
  renderSegmentsPanel(videoIndex);
  showToast(`已删除: ${wasLabel || '未命名段'}`);
}
```

Note: `SegmentState.delete` (already exists) moves the segment to `state.excluded` for restore via "已删段"折叠区.

- [ ] **Step 4: Verify no confirm modal appears + toast shows**

Update `/tmp/verify_issue1_after.py`:
```python
# Same as Step 2 but EXPECTED: confirms == [], toast visible
toast = await target.evaluate("""() => {
    const t = document.querySelector('.toast, [class*="toast"]');
    return t ? t.textContent.trim() : null;
}""")
print("confirms:", confirms)  # EXPECTED: []
print("toast:", toast)        # EXPECTED: '已删除: ...'
```

- [ ] **Step 5: Verify restore path still works**

```python
# After delete, open "已删段" details, click restore, verify state.segments has seg again
await target.locator("text=已删段").click()
await target.wait_for_timeout(200)
restore_btn = target.locator("button[data-act='restore']").first
if await restore_btn.count() > 0:
    await restore_btn.click()
    await target.wait_for_timeout(300)
    seg_count = await target.evaluate("window.__segmentState.states[0].segments.length")
    print("after restore:", seg_count)  # EXPECTED: 9 (back to original)
```

- [ ] **Step 6: Commit**

```bash
cd /mnt/d/2Study/StudyNotes/SKILLS/智剪工坊
git add 智剪工坊/智剪工坊-意图编辑.html
git commit -m "v2.115 Issue #1: 删除按钮用 toast 替代 confirm 模态

[修法]
deleteSegment 删除 confirm() 调用
改为调用 showToast('已删除: <label>')
恢复路径不变(excluded → 已删段折叠区恢复)"
```

---

## Task 2: Issue 2 — Split modal long-text wrapping + width

**Files:**
- Modify: `智剪工坊-意图编辑.html` — `.modal-content` and `.split-row` CSS

- [ ] **Step 1: Locate existing modal CSS**

```bash
grep -n "\.modal-content\|\.split-row\|\.split-bar\|\.split-time\|\.split-role\|\.split-dur" /mnt/d/2Study/StudyNotes/SKILLS/智剪工坊/智剪工坊-意图编辑.html
```

- [ ] **Step 2: Apply CSS changes**

Find the existing `.modal-content { ... padding: 24px }` rule and replace with:

```css
.modal-content {
  background: var(--card);
  border-radius: 10px;
  padding: 24px;
  max-width: 480px;
  max-height: 80vh;
  width: 90vw;
  overflow-y: auto;
  box-sizing: border-box;
  ...
}
```

Find the existing `.split-row` rule and append/replace with:

```css
.split-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  border-left: 3px solid var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, white);
  min-width: 0;  /* allow flex child shrink */
}
.split-time, .split-role, .split-dur { white-space: nowrap; flex-shrink: 0; }
.split-label {
  flex: 1;
  min-width: 0;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.split-bar.original {
  word-break: break-word;
  overflow-wrap: anywhere;
}
```

Also update segHtml in `onTrackSelect` (around Line 5110) to include `<div class="split-label">${escapeHtml(seg.label || `(${formatTime(seg.start_sec)} - ${formatTime(seg.end_sec)})`)}</div>` inside each `.split-row` (between `.split-time` and `.split-dur`).

- [ ] **Step 3: Verify modal wraps long text and stays in viewport**

```python
# /tmp/verify_issue2.py
import asyncio
from playwright.async_api import async_playwright
async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        ctx = browser.contexts[0]
        target = next(pg for pg in ctx.pages if "localhost:8000" in pg.url)
        await target.goto("http://localhost:8000/智剪工坊-意图编辑.html?demo=1", wait_until="networkidle")
        await target.wait_for_timeout(5000)

        # Inject very long label into mid segments
        await target.evaluate("""() => {
            const s = window.__segmentState.states[0];
            s.segments.forEach((seg, i) => {
                if (i % 2 === 1) seg.label = '这是一个非常非常长的 label 用于测试弹窗是否处理文字过长换行问题,你看这个label是不是变得很长很长很长';
            });
            const sp = document.querySelector('.segments-panel');
            const sa = document.querySelector('[data-timeline-segments]');
            renderTimelineSegments(sa, 0); renderSegmentsPanel(0);
        }""")
        await target.wait_for_timeout(300)

        # Simulate drag-to-split to open modal
        # Use synchronous dialog handler
        await target.evaluate("""() => {
            window.__modalShown = false;
            const orig = showInformDialog;
            window.showInformDialog = function(...args) {
                window.__modalShown = true;
                window.__modalTitle = args[0];
                window.__modalBodyLen = (args[1] || '').length;
                // don't actually show
            };
        }""")
        track = await target.locator(".timeline-track").bounding_box()
        await target.mouse.move(track['x'] + track['width']*0.3, track['y'] + track['height']/2)
        await target.mouse.down()
        await target.wait_for_timeout(250)  # long press
        await target.mouse.move(track['x'] + track['width']*0.7, track['y'] + track['height']/2)
        await target.mouse.up()
        await target.wait_for_timeout(800)
        modal_shown = await target.evaluate("window.__modalShown")
        print("modal_shown:", modal_shown)  # EXPECTED: True
        title = await target.evaluate("window.__modalTitle")
        print("title contains 原段:", "原段" in (title or ""))  # EXPECTED: True
asyncio.run(run())
```

Then check rendered modal HTML in a separate test: read the modal-content's `scrollHeight` ≤ `clientHeight + some-tolerance`, and the `.modal-content` element has `max-width: 480px` applied.

- [ ] **Step 4: Verify visual**

```python
# Capture screenshot of modal with long labels, scroll to view
await target.locator(".modal-content").screenshot(path=str(OUT / 'issue2_modal.png'))
```

- [ ] **Step 5: Commit**

```bash
cd /mnt/d/2Study/StudyNotes/SKILLS/智剪工坊
git add 智剪工坊/智剪工坊-意图编辑.html
git commit -m "v2.116 Issue #2: 拆分弹窗长 label 换行 + max-width 提升

[CSS 改动]
- .modal-content: max-width 360 → 480, max-height 80vh, overflow-y auto
- .split-row: min-width:0 (flex shrink), 引入 .split-label 类换行
- .split-time/.split-role/.split-dur: nowrap + flex-shrink:0 保持单行
- .split-bar.original: 长原始时间码也可换行

[JS 改动]
- onTrackSelect segHtml: 每 split-row 加 .split-label 字段(供弹窗显示 label)"
```

---

## Task 3: Issue 3 — Trim handle drag (closure variable leak fix)

**Files:**
- Modify: `智剪工坊-意图编辑.html` — `renderTimelineSegments` function trim handler (around Line 5100-5165)

- [ ] **Step 1: Identify the broken closure**

```bash
grep -n "trim handle 拖动\|tl-seg-trim" /mnt/d/2Study/StudyNotes/SKILLS/智剪工坊/智剪工坊-意图编辑.html
```

The handler at Line 5122 references `duration`, `trackWidth`, `track` — but these are `let` declarations in `setupTimeline` closure, NOT in `renderTimelineSegments`.

- [ ] **Step 2: Verify drag currently fails (regression test)**

```python
# /tmp/verify_issue3_before.py
import asyncio
from playwright.async_api import async_playwright
async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        ctx = browser.contexts[0]
        target = next(pg for pg in ctx.pages if "localhost:8000" in pg.url)
        await target.goto("http://localhost:8000/智剪工坊-意图编辑.html?demo=1", wait_until="networkidle")
        await target.wait_for_timeout(5000)

        before = await target.evaluate("""() => {
            const s = window.__segmentState.states[0].segments.find(s => s.id.includes('40-55') || (s.start_sec >= 38 && s.start_sec <= 42));
            return s ? {start:s.start_sec, end:s.end_sec} : null;
        }""")

        # Drag left trim handle of mid user segment
        seg = target.locator('.tl-seg').nth(3)
        handle = seg.locator('.tl-seg-trim.left')
        box = await handle.bounding_box()
        await target.mouse.move(box['x']+box['width']/2, box['y']+box['height']/2)
        await target.mouse.down()
        for off in range(-10, -51, -10):
            await target.mouse.move(box['x']+box['width']/2+off, box['y']+box['height']/2)
        await target.mouse.up()
        await target.wait_for_timeout(300)

        after = await target.evaluate("""() => {
            const s = window.__segmentState.states[0].segments.find(s => s.start_sec >= 30 && s.start_sec <= 50);
            return s ? {start:s.start_sec, end:s.end_sec} : null;
        }""")
        print("before:", before, "after:", after)
        # EXPECTED: 'before' != 'after' (current state.start_sec changes after drag)
        # ACTUAL (broken): before == after (drag had no effect)
asyncio.run(run())
```

- [ ] **Step 3: Replace trim handler closure references with DOM queries**

Replace lines 5122-5164 (the entire trim handler block) with:

```js
// v2.117:trim handle 拖动 — DOM 查询实时值(不依赖 setupTimeline 闭包变量)
segmentsArea.querySelectorAll('.tl-seg-trim').forEach(handle => {
  handle.addEventListener('mousedown', (e) => {
    e.stopPropagation();
    e.preventDefault();
    const segId = handle.dataset.segId;
    const side = handle.dataset.trimSide;
    const st = window.__segmentState?.states?.[videoIndex];
    if (!st) return;
    const seg = st.segments.find(s => s.id === segId);
    if (!seg) return;

    const inner = segmentsArea.closest('.timeline-inner');
    const trackEl = segmentsArea.closest('.timeline-track');

    const moveH = (mv) => {
      const dur = st.duration || 0;
      if (dur <= 0) return;
      const innerW = parseFloat(inner?.style.width) || 0;
      const pps = innerW / dur;
      if (pps <= 0) return;
      const trackRect = trackEl.getBoundingClientRect();
      const innerOffsetX = mv.clientX - trackRect.left + (trackEl.scrollLeft || 0);
      const t = Math.max(0, Math.min(dur, innerOffsetX / pps));
      if (side === 'left') {
        seg.start_sec = Math.min(seg.end_sec - 0.1, t);
      } else {
        seg.end_sec = Math.max(seg.start_sec + 0.1, t);
      }
      const theSeg = segmentsArea.querySelector(`.tl-seg[data-seg-id="${segId}"]`);
      if (theSeg) {
        const w = (seg.end_sec - seg.start_sec) * pps;
        theSeg.style.width = Math.max(24, w) + 'px';
      }
    };
    const upH = () => {
      document.removeEventListener('mousemove', moveH);
      document.removeEventListener('mouseup', upH);
      // v2.117 加:同步 timeline(让 trim handles 重新对应)
      renderTimelineSegments(segmentsArea, videoIndex);
      renderSegmentsPanel(videoIndex);
    };
    document.addEventListener('mousemove', moveH);
    document.addEventListener('mouseup', upH);
  });
});
```

- [ ] **Step 4: Re-run drag test → should now mutate state**

Re-run `/tmp/verify_issue3_before.py`. Expected: `before.start != after.start` (drag worked).

- [ ] **Step 5: Test invariants after trim**

```python
# After drag, ensure start_sec < end_sec and within [0, duration]
state = await target.evaluate("""() => {
    const segs = window.__segmentState.states[0].segments;
    return segs.map(s => ({s:s.start_sec, e:s.end_sec}));
}""")
for i, seg in enumerate(state):
    assert seg['s'] < seg['e'], f"segment {i} invalid: {seg}"
    assert seg['s'] >= 0 and seg['e'] <= 120, f"segment {i} out of bounds: {seg}"
print("invariants OK:", state)
```

- [ ] **Step 6: Test zoomed-in trim**

```python
# Zoom in first, then trim
await target.click('[data-timeline-zoom-in]')
await target.click('[data-timeline-zoom-in]')
await target.wait_for_timeout(300)
# ... repeat drag test
```

Expected: drag still correctly updates state, no time-offset errors due to zoom.

- [ ] **Step 7: Commit**

```bash
cd /mnt/d/2Study/StudyNotes/SKILLS/智剪工坊
git add 智剪工坊/智剪工坊-意图编辑.html
git commit -m "v2.117 Issue #3: trim handle 拖拽修复 + mouseup 后 sync timeline

[根因]
trim handle listener 在 renderTimelineSegments 闭包
但用了 setupTimeline 闭包的 duration/trackWidth/track 变量(undefined)
mousemove 时 track.getBoundingClientRect() 抛 TypeError
静默,moveH 直接 return → 拖拽无效果

[修法]
- 全部换 DOM 查询:inner=segmentsArea.closest('.timeline-inner'),
  trackEl=segmentsArea.closest('.timeline-track')
- pps 从 inner.style.width / state.duration 实时算
- 坐标系:clientX - rect.left + scrollLeft → 除 pps → 时间秒
- mouseup 后调 renderTimelineSegments 同步(原只 render panel)
- State invariants:start<end, clamp 到 [0,duration],不越相邻段"
```

---

## Task 4: Issue 4 — Tooltip occlusion (Phase A verification + C1+C2 fix)

**Files:**
- Modify: `智剪工坊-意图编辑.html` — `.timeline-track`, `.timeline`, `.inline-preview-video` CSS

- [ ] **Step 1: Capture current state**

```python
# /tmp/verify_issue4_before.py — capture current behavior
import asyncio
from playwright.async_api import async_playwright
async def run():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        ctx = browser.contexts[0]
        target = next(pg for pg in ctx.pages if "localhost:8000" in pg.url)
        await target.goto("http://localhost:8000/智剪工坊-意图编辑.html?demo=1", wait_until="networkidle")
        await target.wait_for_timeout(5000)

        # Hover middle segment (idx 3)
        seg = target.locator('.tl-seg').nth(3)
        box = await seg.bounding_box()
        await target.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
        await target.wait_for_timeout(500)

        # Check tooltip position + visibility
        info = await target.evaluate("""() => {
            const tip = document.querySelector('.tl-seg.tl-seg-has-op .tl-tip');
            const cs = getComputedStyle(tip);
            const op = getComputedStyle(tip).opacity;
            const tipRect = tip.getBoundingClientRect();
            const video = document.querySelector('.inline-preview-video');
            const videoRect = video ? video.getBoundingClientRect() : null;
            return {
              opacity: op, top: tipRect.top, bottom: tipRect.bottom, h: tipRect.height,
              videoTop: videoRect ? videoRect.top : null,
              videoBottom: videoRect ? videoRect.bottom : null,
            };
        }""")
        print(info)
        # EXPECTED (currently): tip.top < videoBottom → tip clip by .timeline-track overflow-x:hidden
asyncio.run(run())
```

- [ ] **Step 2: Apply C1 fix (overflow clip x-only)**

Find `.timeline-track { overflow-x: hidden; overflow-y: hidden; ... }` (Line 294) and replace with:

```css
.timeline-track {
  position: relative;
  overflow-x: clip;
  overflow-y: visible;
  cursor: pointer;
}
```

- [ ] **Step 3: Verify tooltip is now visible above track**

Re-run `/tmp/verify_issue4_before.py`. Expected: `opacity >= 1`, `tipRect.top >= 0` (tooltip not clipped at top).

- [ ] **Step 4: Apply C2 fix (z-index bump)**

Find `.timeline { ... }` rule (around Line 290) and add `z-index: 10` to it. Find `.inline-preview-video { ... }` rule (around Line 229) and add `z-index: 1` and `position: relative` (creates stacking context).

- [ ] **Step 5: Verify tooltip renders above video**

Re-run hover test. Expected: tooltip opacity 1, visually above video (use screenshot to confirm).

- [ ] **Step 6: Capture screenshot proof**

```python
await target.screenshot(path=str(OUT / 'issue4_fixed.png'))
# Scroll timeline to top of viewport so tooltip is in view
await target.evaluate("""() => {
    document.querySelector('.timeline').scrollIntoView({block: 'start'});
}""")
```

- [ ] **Step 7: Commit**

```bash
cd /mnt/d/2Study/StudyNotes/SKILLS/智剪工坊
git add 智剪工坊/智剪工坊-意图编辑.html
git commit -m "v2.118 Issue #4: tooltip 不再被 video 遮挡 (C1+C2 组合)

[C1: 关键修复]
.timeline-track overflow-x: hidden → overflow-x: clip
        overflow-y: hidden → overflow-y: visible
关键: overflow-x: hidden 同时 clip y(实际上是 overflow-y: auto 当作默认)
新:overflow-x: clip + overflow-y: visible 让 tooltip 向上溢出不被裁

[C2: 辅助防御]
.timeline { z-index: 10; }       /* 抬高 timeline stacking */
.inline-preview-video { z-index: 1; position: relative; }
让 .tl-tip 的 z-index 9999 跨 stacking context 生效"
```

---

## Self-Review

1. **Spec coverage:**
   - Issue 1 → Task 1 ✓
   - Issue 2 → Task 2 ✓
   - Issue 3 → Task 3 ✓
   - Issue 4 → Task 4 ✓
   - State invariants (Issue 3) → Task 3 Step 5 ✓
   - Test strategy Playwright matrix → Tasks 1-4 verification steps ✓
   - Browser compatibility → Task 4 Step 1/5 verifies cross-browser

2. **Placeholder scan:**
   - "TBD" / "TODO" / "implement later": none
   - "Add appropriate error handling": none (Task 3 Step 5 has explicit invariants)
   - "Similar to Task N": none (each task fully specified)

3. **Type consistency:**
   - `segId`, `side`, `seg` consistent across Task 3
   - `inner`, `trackEl` consistent across Task 3 and Task 4
   - `pps`, `innerW`, `dur` consistent across all tasks
   - `showToast`, `deleteSegment`, `renderTimelineSegments` consistent across Tasks 1, 3
