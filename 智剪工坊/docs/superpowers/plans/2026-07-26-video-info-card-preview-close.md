# Video Info Card and Preview Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the video information section look and behave like an inner card, show a right-pointing collapse icon, and remove the inline preview close button.

**Architecture:** Keep the existing single-file HTML template and data bindings unchanged. Add scoped CSS for `.video-info-details`, remove the preview close button and its listener/styles, and preserve the existing preview rendering and playback logic.

**Tech Stack:** HTML template literals, CSS, browser JavaScript, Python structural checks, Node.js syntax check.

---

### Task 1: Add the video information card treatment and disclosure icon

**Files:**
- Modify: `智剪工坊-意图编辑.html:2683` and the CSS section near the existing video-card styles
- Test: one-off structural assertions run from the skill directory

- [ ] **Step 1: Write the failing structural check**

Run a Python check that requires `.video-info-details` to have scoped card styles and a `summary::before` rule with `content: '▶'`, while requiring the existing default-collapsed markup to remain without `open`.

```bash
python3 - <<'PY'
from pathlib import Path
html = Path('智剪工坊-意图编辑.html').read_text(encoding='utf-8')
assert '.video-info-details {' in html
assert ".video-info-details > summary::before { content: '▶';" in html
assert '<details class="video-info-details">' in html
assert '<details class="video-info-details" open>' not in html
print('PASS')
PY
```

Expected: FAIL because the scoped card and disclosure CSS do not yet exist.

- [ ] **Step 2: Implement the scoped card and icon styles**

Add CSS beside the existing video-card styles:

```css
.video-info-details {
  margin-bottom: 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--card);
  overflow: hidden;
}
.video-info-details > summary {
  padding: 10px 14px;
  color: var(--label);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  list-style: none;
}
.video-info-details > summary::-webkit-details-marker { display: none; }
.video-info-details > summary::before {
  content: '▶';
  display: inline-block;
  width: 12px;
  margin-right: 6px;
  color: var(--secondary);
  font-size: 9px;
  transition: transform 0.15s;
}
.video-info-details[open] > summary::before { transform: rotate(90deg); }
.video-info-details > .video-grid,
.video-info-details > .seq-section {
  margin-left: 14px;
  margin-right: 14px;
}
```

- [ ] **Step 3: Run the structural check again**

Run the Python command from Step 1.

Expected: PASS.

### Task 2: Remove the inline preview close control

**Files:**
- Modify: `智剪工坊-意图编辑.html:222-228`, `:2528-2533`, and `:2741`
- Test: the same structural check plus JavaScript syntax validation

- [ ] **Step 1: Write the failing structural check**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
html = Path('智剪工坊-意图编辑.html').read_text(encoding='utf-8')
assert 'class="inline-preview-close"' not in html
assert 'data-inline-preview-close' not in html
assert 'closeInlinePreview(' not in html
print('PASS')
PY
```

Expected: FAIL because the close button, listener, and helper still exist.

- [ ] **Step 2: Remove only the close-control implementation**

Delete the `.inline-preview-close` and `.inline-preview-close:hover` CSS rules, delete the `videoListEl.querySelectorAll('[data-inline-preview-close]')` listener block, and delete the close button from the inline preview header. Leave the preview video, timeline, thumbnail-triggered opening, and all playback controls unchanged.

- [ ] **Step 3: Run the structural and JavaScript checks**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import re
html = Path('智剪工坊-意图编辑.html').read_text(encoding='utf-8')
assert 'class="inline-preview-close"' not in html
assert 'data-inline-preview-close' not in html
assert 'closeInlinePreview(' not in html
scripts = re.findall(r'<script(?:\s[^>]*)?>(.*?)</script>', html, re.S | re.I)
assert scripts
for i, script in enumerate(scripts):
    path = f'/tmp/zhijian-plan-{i}.js'
    Path(path).write_text(script, encoding='utf-8')
print('STRUCTURE PASS')
PY
for file in /tmp/zhijian-plan-*.js; do node --check "$file"; done
```

Expected: structural check and `node --check` both pass.

### Task 3: Verify the complete requested behavior

**Files:**
- Verify: `智剪工坊-意图编辑.html`

- [ ] **Step 1: Run the complete regression check**

Verify that the video info details remains default collapsed and closed after the Sequence section, that its card/icon CSS exists, that the voice controls retain `data-video="${i}.voice"` and `data-video="${i}.voice_note"`, that basic editing and visual adjustment remain default collapsed, and that `.seg-ops-group` remains default collapsed.

```bash
python3 - <<'PY'
from pathlib import Path
import re
html = Path('智剪工坊-意图编辑.html').read_text(encoding='utf-8')
info = re.search(r'<details class="video-info-details">(.*?)<!-- v1\\.15 新增:内嵌预览区', html, re.S)
assert info and info.group(1).rstrip().endswith('</details>')
assert '<details class="video-info-details" open>' not in html
assert '.video-info-details {' in html
assert ".video-info-details > summary::before {\n  content: '▶';" in html
voice = re.search(r'<div class="ops-body.*?>(.*?)<details class="ops-subgroup">', html, re.S)
assert voice and 'data-video="${i}.voice"' in voice.group(1)
assert 'data-video="${i}.voice_note"' in voice.group(1)
assert '<details class="seg-ops-group" open>' not in html
assert '<details class="ops-subgroup" open>\n                  <summary>📐 基础剪辑 (7)</summary>' not in html
assert '<details class="ops-subgroup" open>\n                  <summary>🎨 画面调节 (5)</summary>' not in html
print('PASS')
PY
git diff --check
```

Expected: all assertions pass and `git diff --check` produces no errors. No commit is required.
