# 视频卡片展开即内置预览 Implementation Plan

> 适用项目:智剪工坊 · 意图编辑 HTML  
> 文档定位:落地方案(与 SKILL开发总纲 V1.0 §05 配合)  
> 本次跳过 Fresh Agent 黑盒测试(用户参与人工验收)。

**Goal:** 视频卡片展开时自动出现并加载首帧的内嵌预览;多卡片并行存在时互斥播放,折叠/关闭时回收 Blob URL。

**Architecture:** 保留每张视频卡片独立的 `<video>` 元素,移除全局 `currentPreviewIdx` 互斥;播放互斥通过监听 `play` 事件实现;资源生命周期与卡片展开/折叠绑定。

**Tech Stack:** 原生 HTML + JS + CSS,无新依赖。

---

## 改动前 3 问

1. **影响哪些文件?**
   - `智剪工坊-意图编辑.html`(预览绑定、previewVideoInline、closeInlinePreview、toggleCard 内联预览逻辑、旧 previewVideo 死码)
2. **有没有数据迁移?**
   - 无,纯前端 DOM/事件调整
3. **回滚方案?**
   - `git reset --hard <上一 commit>`(HEAD 已在 v1.24.22 定版,可回退)

---

## 文件结构

| 文件 | 责任 |
|---|---|
| `智剪工坊-意图编辑.html` | 唯一改动文件:展开/折叠逻辑 + 预览生命周期 |

---

## Task 1: 解除全局单预览互斥,改为每卡片独立

**Files:**
- Modify: `智剪工坊-意图编辑.html`(JS 区域)

- [ ] **Step 1: 移除 `currentPreviewIdx` 与互斥分支**

定位以下旧实现(约 :2167 附近):

```javascript
let currentPreviewIdx = -1;
function previewVideoInline(i) {
  ...
  if (currentPreviewIdx !== -1 && currentPreviewIdx !== i) {
    // 暂停 + 释放旧 Blob
  }
  ...
  if (video.src !== entry._blobUrl) {
    video.src = entry._blobUrl;
    video.load();
  }
  previewEl.hidden = false;
  currentPreviewIdx = i;
  ...
}
function closeInlinePreview(i) {
  ...
  if (currentPreviewIdx === i) currentPreviewIdx = -1;
}
```

替换为:

```javascript
function previewVideoInline(i) {
  const entry = videoEntries[i];
  if (!entry || entry.isImage) { showToast('请用图片缩略图查看图片'); return; }
  const card = videoListEl.querySelector(`.video-card[data-card-idx="${i}"]`);
  if (!card) return;

  const wasCollapsed = card.classList.contains('collapsed');
  if (wasCollapsed) {
    card.classList.remove('collapsed');
    const toggleBtn = card.querySelector('.card-toggle');
    if (toggleBtn) toggleBtn.classList.add('expanded');
  }
  const opsGroup = card.querySelector('.ops-group');
  if (opsGroup && !opsGroup.classList.contains('open')) opsGroup.classList.add('open');

  const previewEl = document.getElementById(`inline-preview-${i}`);
  const video = previewEl.querySelector('video');
  if (!entry._blobUrl) entry._blobUrl = URL.createObjectURL(entry.file);
  if (video.src !== entry._blobUrl) { video.src = entry._blobUrl; video.load(); }
  previewEl.hidden = false;

  if (!previewEl.dataset.timelineInited) {
    setupTimeline(previewEl, video);
    previewEl.dataset.timelineInited = '1';
  }
  if (wasCollapsed) previewEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function closeInlinePreview(i) {
  const previewEl = document.getElementById(`inline-preview-${i}`);
  if (!previewEl) return;
  const video = previewEl.querySelector('video');
  if (video) video.pause();
  previewEl.hidden = true;
}
```

- [ ] **Step 2: JS 语法校验**

```bash
python3 - <<'PY'
import re, subprocess
PATH = '智剪工坊-意图编辑.html'
html = open(PATH, encoding='utf-8').read()
m = re.search(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
open('/tmp/script.js', 'w', encoding='utf-8').write(m.group(1))
print(subprocess.run(['node','--check','/tmp/script.js'], capture_output=True, text=True).returncode)
PY
```

期望输出: `0`

- [ ] **Step 3: 提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v1.25 重构:移除全局单预览互斥 currentPreviewIdx,改为每卡片独立 previewEl"
```

---

## Task 2: 折叠时释放 Blob URL + 暂停播放

**Files:**
- Modify: `智剪工坊-意图编辑.html`(toggleCard 区域)

- [ ] **Step 1: 折叠卡片时同步关闭预览 + 释放资源**

定位 `toggleCard` 函数内已有折叠逻辑(约 :2083 注释 `// v1.15 新增:卡片折叠时,自动隐藏该卡的内嵌预览`)。

在折叠分支末尾追加:

```javascript
const previewEl = document.getElementById(`inline-preview-${idx}`);
if (previewEl && !previewEl.hidden) {
  const v = previewEl.querySelector('video');
  if (v) v.pause();
  previewEl.hidden = true;
  const entry = videoEntries[idx];
  if (entry && entry._blobUrl) { URL.revokeObjectURL(entry._blobUrl); entry._blobUrl = null; }
}
```

- [ ] **Step 2: JS 语法校验**

同 Task 1 Step 2。

- [ ] **Step 3: 提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v1.25 折叠时回收:卡片折叠自动 pause + hidden + revokeObjectURL"
```

---

## Task 3: 卡片展开时自动触发预览初始化

**Files:**
- Modify: `智剪工坊-意图编辑.html`(toggleCard 展开分支)

- [ ] **Step 1: 展开分支末尾自动调用 `previewVideoInline`**

在 `toggleCard` 的“展开”分支(去掉 `collapsed` + 加 `expanded`)末尾调用:

```javascript
previewVideoInline(idx);
```

注意: 这是新增逻辑,与展开同步;`previewVideoInline` 自身已经处理“之前是折叠才滚动”,这里直接调用即可。

- [ ] **Step 2: JS 语法校验**

同 Task 1 Step 2。

- [ ] **Step 3: 提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v1.25 展开即预览:toggleCard 展开分支自动调 previewVideoInline"
```

---

## Task 4: 多视频播放互斥(只允许一个在播)

**Files:**
- Modify: `智剪工坊-意图编辑.html`(`previewVideoInline` 内或紧邻区域)

- [ ] **Step 1: 绑定一次性的 `play` 事件互斥**

在 `previewVideoInline` 函数末尾追加:

```javascript
if (!videoListEl.dataset.playExclusivityInited) {
  videoListEl.addEventListener('play', (e) => {
    const active = e.target;
    videoListEl.querySelectorAll('video').forEach(v => {
      if (v !== active && !v.paused) v.pause();
    });
  }, true);
  videoListEl.dataset.playExclusivityInited = '1';
}
```

- [ ] **Step 2: JS 语法校验**

同 Task 1 Step 2。

- [ ] **Step 3: 提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v1.25 多视频互斥:play 事件冒泡,除当前播放外其余 pause"
```

---

## Task 5: 删除旧 `previewVideo` 死函数

**Files:**
- Modify: `智剪工坊-意图编辑.html`(约 :2465)

- [ ] **Step 1: 删除 `previewVideo` 函数**

移除整段 `function previewVideo(entry) { ... }`。该函数无任何调用,只用来打开 `window.open` 新窗口,保留会误导后续维护。

- [ ] **Step 2: 全文件 grep 验证无残留引用**

```bash
grep -n "previewVideo(" 智剪工坊-意图编辑.html
```

期望输出: 仅有 `previewVideoInline` 与 `closeInlinePreview` 命中,无独立 `previewVideo(` 调用。

- [ ] **Step 3: JS 语法校验**

同 Task 1 Step 2。

- [ ] **Step 4: 提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v1.25 清理:删除旧 window.open 弹窗 previewVideo 死函数"
```

---

## Task 6: 人工验收 + 文档同步

- [ ] **Step 1: 重启 Chrome 加载最新版**

```bash
python3 - <<'PY'
from urllib.parse import quote
import time, subprocess
ts = int(time.time())
url = f"file:///D:/2Study/StudyNotes/SKILLS/{quote('智剪工坊')}/{quote('智剪工坊-意图编辑.html')}?v={ts}"
subprocess.run(['powershell.exe','-Command',
    f"Start-Process 'C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe' '{url}'"], check=True)
PY
```

- [ ] **Step 2: 验收清单(由用户执行)**

  1. 选中一个含 3+ 视频的项目
  2. 展开第一张卡 → 预览窗口出现 + 加载首帧(不自动播放)
  3. 点击预览 ▶ → 开始播放,其他已展开卡片保持暂停
  4. 展开第二张卡 → 该卡预览出现 + 首帧加载,第一张暂停不变
  5. 播放第二张 → 第一张应保持暂停
  6. 折叠任意一张 → 预览暂停 + 隐藏 + 释放 Blob
  7. 再次展开 → 重新加载首帧
  8. DevTools Memory 面板确认反复折叠/展开后 Blob 数稳定不增长

- [ ] **Step 3: SKILL.md 补 changelog(可选)**

  在 SKILL.md metadata 下方或变更说明章节追加 v1.25 摘要:多卡片预览独立、互斥播放、折叠释放 Blob。

- [ ] **Step 4: 提交并 tag(若需要)**

```bash
git tag -a v1.25 -m "v1.25: 视频卡片展开即内置预览"
```

---

## 风险与边界

- 浏览器 Blob 回收需要 reload 才完全释放;折叠已隐藏预览会主动 `revokeObjectURL`,可控。
- 播放互斥靠 `play` 事件,音频不会叠加;视频解码占用随展开数线性增长,正常流程 ≤ 6 视频无压力。
- 不影响图片(`data-zoom` 全屏)与 `ops-group` 行为。

---

## 自检

- [ ] 任务清单覆盖规格:展开即加载首帧 / 折叠回收 / 多卡并存 / 播放互斥 / 死函数清理
- [ ] 每步均有可执行命令 + 期望输出
- [ ] 改动前 3 问答齐
- [ ] 无占位符 / TODO / TBD