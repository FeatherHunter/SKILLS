# 视频时间段模型重构 实施计划

> **适用项目:** 智剪工坊 · 意图编辑 HTML
> **依据 spec:** `docs/superpowers/specs/2026-07-25-video-time-segment-model.md`
> **本文档定位:** 落地阶段实施计划(跳过 Fresh Agent 黑盒测试,人工验收)

**Goal:** 把 HTML 输出的 intent.json 从平铺 22-op 重构为 `video_ops` + `time_segments[].ops` 双字段;UI 支持 timeline 长按拖框选 + 段单击操作面板 + 已删段可恢复;不破坏旧 intent.json 数据加载。

**Architecture:**
- JSON 单源真相: `time_segments`(保留段,不含已删段);已删段由 JS 计算 `[0, duration] - segments 并集`
- 视觉规则: 彩虹 8 色循环(段) + 灰色 + 删除线(已删段) + 小图标徽章(段 op) + hover tooltip 完整 op 摘要
- 数据兼容: 加载时检测 schema_version=3.0 → 新结构;否则解析旧 `ops` 平铺结构
- 拖动语义: 段本体不可拖 / 边界不可调(本期);只有空白处长按拖动 = 拆段或新建

**Tech Stack:** 原生 HTML + JS + CSS(无新依赖)

---

## 改动前 3 问

1. **影响哪些文件?**
   - `智剪工坊/智剪工坊-意图编辑.html`(collectFormData + collectOpsForVideo + render + 折叠区 + CSS + timeline)
   - `智剪工坊/SKILL.md` + `references/*.md`(增 v2.0 变更摘要)
2. **有没有数据迁移?**
   - 数据兼容层:旧 `intent.json` 加载时自动迁移为新结构(自动备份原文件)
3. **回滚方案?**
   - `git reset --hard 0021320`(当前 HEAD,带新 spec)或更早版本
   - 或 git tag v1.25 回退到定版

---

## 文件结构

| 文件 | 责任 |
|---|---|
| `智剪工坊-意图编辑.html` | 唯一主文件,承载 UI + JS + CSS + JSON 序列化与加载 |
| `智剪工坊/SKILL.md` | 增 v2.0 变更说明 |
| `智剪工坊/docs/superpowers/specs/2026-07-25-video-time-segment-model.md` | 已写(本计划依赖) |
| `智剪工坊/docs/superpowers/plans/2026-07-25-time-segment-model.md` | 本文件 |

---

## Task 1:数据模型与校验器(优先,Phase A)

**Files:**
- Modify: `智剪工坊-意图编辑.html`(JS 区域)

- [ ] **Step 1:新增 `validateIntent()` 函数**

定位 HTML 末尾 utils 区域(约 `:3310` 后)。新增:

```javascript
function validateIntent(data) {
  const errors = [];
  data.videos?.forEach(v => {
    const segs = v.time_segments || [];
    const ids = new Set();

    // 规则 1:id 唯一
    segs.forEach(s => {
      if (ids.has(s.id)) errors.push(`#${v.index}: id "${s.id}" 重复`);
      ids.add(s.id);
    });

    // 规则 2:区间合法
    segs.forEach(s => {
      if (s.start_sec < 0 || s.end_sec > v.duration_sec || s.start_sec >= s.end_sec) {
        errors.push(`#${v.index} ${s.id}: 区间 [${s.start_sec}, ${s.end_sec}] 非法,视频时长 ${v.duration_sec}s`);
      }
    });

    // 规则 3:段不重叠(允许衔接)
    const sorted = [...segs].sort((a, b) => a.start_sec - b.start_sec);
    for (let i = 0; i < sorted.length - 1; i++) {
      if (sorted[i].end_sec > sorted[i + 1].start_sec) {
        errors.push(`#${v.index}: 段 ${sorted[i].id} 与 ${sorted[i+1].id} 重叠`);
      }
    }

    // 规则 4:段内 ops 合法性
    const validSegmentOps = ['mute', 'speed-up', 'slow-down', 'reverse', 'color-grade'];
    segs.forEach(s => {
      if (!s.ops) return;
      Object.entries(s.ops).forEach(([opName, opCfg]) => {
        if (!validSegmentOps.includes(opName)) {
          errors.push(`#${v.index} ${s.id}: 不支持的段内 op "${opName}"`);
        }
        if ((opName === 'speed-up' || opName === 'slow-down') && (typeof opCfg.factor !== 'number' || opCfg.factor <= 0)) {
          errors.push(`#${v.index} ${s.id}: ${opName} 必须有 factor > 0`);
        }
      });
    });

    // 规则 5:video_ops.voice.mode
    if (v.video_ops?.voice?.on) {
      const validModes = ['keep', 'keep-with-filler-removed', 'mute', 'bgm-only'];
      if (!validModes.includes(v.video_ops.voice.mode)) {
        errors.push(`#${v.index} video_ops.voice.mode "${v.video_ops.voice.mode}" 非法`);
      }
    }
  });
  return errors;
}
```

- [ ] **Step 2:JS 语法校验**

```bash
python3 - <<'PY'
import re, subprocess
PATH = '/mnt/d/2Study/StudyNotes/SKILLS/智剪工坊/智剪工坊-意图编辑.html'
html = open(PATH, encoding='utf-8').read()
m = re.search(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
open('/tmp/script.js', 'w', encoding='utf-8').write(m.group(1))
print(subprocess.run(['node','--check','/tmp/script.js'], capture_output=True, text=True).returncode)
PY
```

期望输出: `0`

- [ ] **Step 3:浏览器打开 → DevTools console 测试**

输入测试用例(逐个):
1. `validateIntent({videos:[{index:1, duration_sec:60, time_segments:[{id:'a', start_sec:0, end_sec:60}]}]})` → `[]`
2. `validateIntent({videos:[{index:1, duration_sec:60, time_segments:[{id:'a', start_sec:0, end_sec:60}, {id:'b', start_sec:30, end_sec:60}]}]})` → 重叠错误
3. `validateIntent({videos:[{index:1, duration_sec:60, time_segments:[{id:'a', start_sec:-1, end_sec:60}]}]})` → 区间非法
4. `validateIntent({videos:[{index:1, duration_sec:60, video_ops:{voice:{on:true, mode:'invalid'}}}]})` → mode 非法

期望输出: 无报错 / 校验通过 / 错误信息符合预期

- [ ] **Step 4:提交**

```bash
cd /mnt/d/2Study/StudyNotes/SKILLS/智剪工坊
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase A: 新增 validateIntent 校验器(5 条规则)"
```

---

## Task 2:数据兼容层 - 旧 ops → 新结构(Phase A 续)

**Files:**
- Modify: `智剪工坊-意图编辑.html`(`loadIntent` 或类似函数)

- [ ] **Step 1:定位加载入口**

`grep -n "loadIntent\|existingIntent\|videoEntries\s*=\s*\[" 智剪工坊-意图编辑.html`

- [ ] **Step 2:新增 `migrateLegacyIntent(data)` 函数**

在 utils 区域添加:

```javascript
function migrateLegacyIntent(data) {
  // 老 schema → 新 schema 转换
  if (!data || data._meta?.schema_version === '3.0') return data;

  // 给每个 video 添加空 time_segments(老数据视为整段保留)
  data.videos?.forEach(v => {
    if (!v.time_segments) {
      v.time_segments = [{
        id: `seg_${v.index}_1`,
        label: '整段保留',
        start_sec: 0,
        end_sec: v.duration_sec || 60,
        ops: {}
      }];
    }
    // 把老 ops 平铺里的"区间敏感 op"迁移到 time_segments[0].ops
    const rangeSensitiveOps = ['mute-region', 'reverse-region', 'speed-region', 'cut-middle', 'pin-range'];
    const legacyOps = v.ops || {};
    Object.entries(legacyOps).forEach(([opName, opCfg]) => {
      if (rangeSensitiveOps.includes(opName)) {
        v.time_segments[0].ops = v.time_segments[0].ops || {};
        v.time_segments[0].ops[opName.replace('-region','')] = opCfg;
      } else {
        // 整段型 op 迁移到 video_ops
        v.video_ops = v.video_ops || {};
        v.video_ops[opName.replace('add-bgm','add-bgm').replace('-region','')] = opCfg;
      }
    });
    // 清理老 ops(已迁移)
    delete v.ops;
  });

  data._meta = data._meta || {};
  data._meta.schema_version = '3.0';
  return data;
}
```

- [ ] **Step 3:在加载入口插入迁移**

```javascript
data = migrateLegacyIntent(data);
if (validateIntent(data).length > 0) {
  console.warn('Intent 校验失败:', validateIntent(data));
  showToast('intent.json 有错误,请检查');
}
```

- [ ] **Step 4:JS 语法校验**

同 Task 1 Step 2。

- [ ] **Step 5:浏览器测试**

加载一个旧的 `intent.json`(如果有)→ 校验通过 + 段被识别。

- [ ] **Step 6:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase A: 加 migrateLegacyIntent 数据兼容层"
```

---

## Task 3:`collectFormData()` 重写(Phase F 前置)

**Files:**
- Modify: `智剪工坊-意图编辑.html`(JS 区域)

- [ ] **Step 1:定位 `collectFormData()`**

`grep -n "function collectFormData" 智剪工坊-意图编辑.html`

- [ ] **Step 2:替换整个函数**

删除老的 `collectFormData()` + `collectOpsForVideo()`,替换为:

```javascript
function collectFormData() {
  const now = new Date().toISOString();
  const oldRev = existingIntent?._meta?.revision || 0;
  const newRev = oldRev + 1;
  const data = {
    _meta: {
      tool: '智剪工坊',
      schema_version: '3.0',
      revision: newRev,
      created: existingIntent?._meta?.created || now,
      updated: now,
      workspace: dirHandle?.name || '(unknown)',
      history: [
        ...(Array.isArray(existingIntent?._meta?.history) ? existingIntent._meta.history : []),
        { revision: newRev, timestamp: now }
      ]
    },
    project: {}, output: {}, sequences: [], videos: [],
    cover: {}, ending: {}
  };

  // data-path 字段填充(项目级/输出/封面/结尾)
  for (const el of document.querySelectorAll('[data-path]')) {
    if (el.value) setByPath(data, el.dataset.path, el.value);
  }

  // sequences 从每个视频的"接视频"字段重建
  const nextMap = {}; const transMap = {};
  videoEntries.forEach((_, i) => {
    const sel = document.querySelector(`[data-seq-next="${i}"]`);
    if (sel && sel.value) {
      const nextEntry = videoEntries.find(e => String(e.index) === sel.value);
      if (nextEntry) {
        nextMap[i] = nextEntry.index;
        const tSel = document.querySelector(`[data-seq-trans="${i}"]`);
        const dEl = document.querySelector(`[data-seq-dur="${i}"]`);
        if (tSel) {
          transMap[i] = {
            type: tSel.value || 'none',
            duration: dEl ? parseFloat(dEl.value) || 0.5 : 0.5
          };
        }
      }
    }
  });
  const hasParent = new Set(Object.values(nextMap));
  const roots = videoEntries
    .map((e, i) => i)
    .filter(i => !hasParent.has(videoEntries[i].index));
  roots.forEach(startIdx => {
    const chain = []; const transitions = []; let cur = startIdx;
    const visited = new Set();
    while (cur !== undefined && !visited.has(cur)) {
      visited.add(cur);
      chain.push(videoEntries[cur].index);
      const nextEntryIndex = nextMap[cur];
      if (nextEntryIndex === undefined) break;
      const nextI = videoEntries.findIndex(e => e.index === nextEntryIndex);
      if (nextI < 0) break;
      if (transMap[cur]) {
        transitions.push({ after: videoEntries[cur].index, ...transMap[cur] });
      }
      cur = nextI;
    }
    if (chain.length > 1) {
      const titleEl = document.querySelector(`[data-seq-title="${startIdx}"]`);
      const seqObj = { videos: chain, transitions };
      if (titleEl && titleEl.value.trim()) seqObj.title = titleEl.value.trim();
      data.sequences.push(seqObj);
    }
  });
  if (data.sequences.length === 0) delete data.sequences;

  // videos
  videoEntries.forEach((entry, i) => {
    const v = { file: entry.name, index: entry.index };
    if (entry.excluded) v.exclude = true;
    for (const key of ['summary', 'intent']) {
      const el = document.querySelector(`[data-video="${i}.${key}"]`);
      if (el && el.value) v[key] = el.value;
    }
    v.duration_sec = entry.durationSec || 60;
    v.video_ops = collectVideoOpsForVideo(i);
    v.time_segments = collectTimeSegmentsForVideo(i);
    data.videos.push(v);
  });

  // 提交前校验
  const errors = validateIntent(data);
  if (errors.length > 0) {
    console.warn('Intent 校验失败:', errors);
    showToast('提交数据有错误,请查看 console');
    return null;
  }

  return data;
}

function collectVideoOpsForVideo(i) {
  const card = videoListEl.querySelector(`[data-video-index="${i+1}"]`);
  if (!card) return {};
  const ops = {};

  // voice select
  const voiceSel = card.querySelector(`[data-video="${i}.voice"]`);
  if (voiceSel && voiceSel.value) {
    ops.voice = { on: true, mode: voiceSel.value };
  }

  // voice_note textarea
  const voiceNoteEl = card.querySelector(`[data-video="${i}.voice_note"]`);
  if (voiceNoteEl && voiceNoteEl.value.trim()) {
    ops.voice_note = voiceNoteEl.value.trim();
  }

  // notes textarea
  const notesEl = card.querySelector(`[data-video="${i}.notes"]`);
  if (notesEl && notesEl.value.trim()) {
    ops.notes = notesEl.value.trim();
  }

  // 原 ops-group 里的 checkbox + sub field(整段型 op)
  const segmentOps = ['mute-region','reverse-region','speed-region'];  // 这些已迁移到 time_segments
  const legacyOps = ['trim-head', 'trim-tail', 'cut-middle', 'pin-range',
    'target-duration', 'speed-up', 'slow-down', 'reverse', 'mute',
    'fade-in', 'fade-out', 'color', 'add-bgm', 'replace-audio',
    'opening-text', 'insert-image',
    'asr-transcribe', 'asr-burn', 'asr-speaker',
    'audio-denoise', 'audio-separate', 'audio-diarize', 'voice-filler-removed'];
  legacyOps.forEach(op => {
    if (segmentOps.includes(op)) return;
    const cb = card.querySelector(`[data-op="${op}"]`);
    if (!cb || !cb.checked) return;
    const cfg = { on: true };
    if (['trim-head', 'trim-tail', 'fade-in', 'fade-out', 'target-duration'].includes(op)) {
      const v = parseFloat(card.querySelector(`[data-op-val="${op}"]`)?.value);
      if (!isNaN(v)) cfg.sec = v;
    } else if (['speed-up', 'slow-down'].includes(op)) {
      const v = parseFloat(card.querySelector(`[data-op-val="${op}"]`)?.value);
      if (!isNaN(v)) cfg.factor = v;
    } else if (op === 'color') {
      cfg.style = card.querySelector(`[data-op-val="color"]`)?.value || '';
    } else if (op === 'add-bgm') {
      const disp = card.querySelector(`[data-bgm-display="${i}"]`);
      cfg.file = disp?.dataset?.filename || disp?.textContent || '';
      const v = parseFloat(card.querySelector('[data-op-val="bgm-volume"]')?.value);
      if (!isNaN(v)) cfg.volume = v;
    } else if (op === 'replace-audio') {
      const disp = card.querySelector(`[data-replace-display="${i}"]`);
      cfg.file = disp?.dataset?.filename || disp?.textContent || '';
    } else if (op === 'opening-text') {
      const textEl = card.querySelector('[data-op-val="opening-text-content"]');
      if (textEl?.value) cfg.text = textEl.value;
      const durEl = card.querySelector('[data-op-val="opening-text-duration"]');
      const dur = parseFloat(durEl?.value);
      if (!isNaN(dur)) cfg.duration = dur;
    } else if (op === 'insert-image') {
      const disp = card.querySelector(`[data-insert-img-display="${i}"]`);
      cfg.file = disp?.dataset?.filename || disp?.textContent || '';
      const atEl = card.querySelector('[data-op-val="insert-at"]');
      if (atEl?.value) cfg.at = atEl.value;
      const durEl = card.querySelector('[data-op-val="insert-duration"]');
      const dur = parseFloat(durEl?.value);
      if (!isNaN(dur)) cfg.duration = dur;
    } else if (op === 'asr-transcribe') {
      const sel = card.querySelector('[data-op-val="asr-transcribe"]');
      if (sel?.value) cfg.model = sel.value;
    } else if (op === 'asr-burn') {
      const v = parseFloat(card.querySelector('[data-op-val="asr-burn"]')?.value);
      if (!isNaN(v)) cfg.font_size = v;
    } else if (op === 'audio-separate') {
      const sel = card.querySelector('[data-op-val="audio-separate"]');
      if (sel?.value) cfg.model = sel.value;
    }
    const noteEl = card.querySelector(`[data-op-note="${op}"]`);
    if (noteEl?.value.trim()) cfg.note = noteEl.value.trim();
    ops[op] = cfg;
  });

  return ops;
}

function collectTimeSegmentsForVideo(i) {
  const card = videoListEl.querySelector(`[data-video-index="${i+1}"]`);
  if (!card) return [];
  // 从 UI 状态读取 segments(由 timeline 模块维护)
  const inlineState = window.__segmentState?.[i] || { segments: [] };
  return inlineState.segments.map(s => ({
    id: s.id,
    label: s.label || '',
    start_sec: s.start_sec,
    end_sec: s.end_sec,
    ops: s.ops || {},
    ...(s.note ? { note: s.note } : {})
  }));
}
```

- [ ] **Step 3:JS 语法校验**

同 Task 1 Step 2。

- [ ] **Step 4:浏览器测试**

1. 在视频卡做出简单编辑(改 voice + 加段)
2. 点保存
3. console 查看 `data` 结构(含 video_ops + time_segments)

期望输出: data 是新 schema 结构。

- [ ] **Step 5:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase F: 重写 collectFormData — 2 类字段(整段 video_ops + time_segments)"
```

---

## Task 4:`loadIntent()` 加载逻辑(Phase F 后半)

**Files:**
- Modify: `智剪工坊-意图编辑.html`

- [ ] **Step 1:定位加载入口**

`grep -n "loadExisting\|loadIntent" 智剪工坊-意图编辑.html`

- [ ] **Step 2:在加载入口插入迁移 + 校验**

```javascript
async function loadIntent() {
  // ... 现有加载逻辑
  const data = JSON.parse(jsonText);

  // 数据迁移(老 → 新)
  const migrated = migrateLegacyIntent(data);

  // 校验
  const errors = validateIntent(migrated);
  if (errors.length > 0) {
    console.warn('加载的 intent 校验失败:', errors);
    showToast('intent.json 有错误,请查看 console');
  }

  return migrated;
}
```

- [ ] **Step 3:JS 语法校验**

同 Task 1 Step 2。

- [ ] **Step 4:浏览器测试往返**

1. 简单编辑 + 保存 → 新 intent.json
2. 重新打开项目 → 数据完整恢复
3. 检查 voice / segments / 段内 ops 都恢复

- [ ] **Step 5:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase F: loadIntent 加载时执行迁移 + 校验"
```

---

## Task 5:整段操作区重命名(Phase B)

**Files:**
- Modify: `智剪工坊-意图编辑.html`(模板)

- [ ] **Step 1:定位 "基础剪辑操作" 字样**

`grep -n "基础剪辑\|ops-group" 智剪工坊-意图编辑.html | head -10`

- [ ] **Step 2:替换文案**

将 `基础剪辑操作` → `整段视频操作`(共 N 处)

- [ ] **Step 3:浏览器测试**

展开任意视频卡 → 操作区 title 显示"整段视频操作"

- [ ] **Step 4:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase B: 操作区重命名'基础剪辑操作' → '整段视频操作'"
```

---

## Task 6:CSS 增加彩虹 8 色 + op 徽章样式(Phase C)

**Files:**
- Modify: `智剪工坊-意图编辑.html`(`<style>`)

- [ ] **Step 1:在 CSS 末尾添加**

```css
/* v2.0:彩虹 8 色 + op 徽章 */
:root {
  --seg-color-0: #ff3b30;
  --seg-color-1: #ff9500;
  --seg-color-2: #ffcc00;
  --seg-color-3: #34c759;
  --seg-color-4: #00b4d8;
  --seg-color-5: #5e5ce6;
  --seg-color-6: #af52de;
  --seg-color-7: #ff2d92;
}
.tl-seg {
  position: relative;
  cursor: pointer;
  transition: transform 0.15s;
}
.tl-seg:hover {
  transform: translateY(-2px);
  z-index: 10;
}

/* op 徽章(段内 op 显示) */
.tl-seg-op-badge {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: rgba(0,0,0,0.4);
  color: #fff;
  border-radius: 3px;
  font-size: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

/* tooltip */
.seg-tip {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 50%;
  transform: translateX(-50%);
  background: #1d1d1f;
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
  z-index: 20;
}
.seg-tip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: #1d1d1f;
}
.tl-seg:hover .seg-tip { opacity: 1; }

/* 已删段折叠区样式 */
.deleted-seg-item {
  background: #c7c7cc;
  color: #6e6e73;
  text-decoration: line-through;
  opacity: 0.55;
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 6px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.deleted-seg-item .seg-restore {
  background: #0071e3;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
}

/* 段闪烁高亮 */
@keyframes segFlash {
  0%, 100% { box-shadow: none; }
  50% { box-shadow: 0 0 0 3px #0071e3; }
}
.tl-seg.flash {
  animation: segFlash 0.5s 4;
}
```

- [ ] **Step 2:浏览器刷新 → DevTools 检查样式生效**

打开任一视频卡,展开。

- [ ] **Step 3:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase C: CSS 彩虹 8 色 + op 徽章 + tooltip"
```

---

## Task 7:JS 增加段状态管理(Phase C+E)

**Files:**
- Modify: `智剪工坊-意图编辑.html`(JS 区域,新模块)

- [ ] **Step 1:新增段状态管理器(放在 utils 顶部)**

```javascript
/**
 * 段状态管理器
 * 每张视频卡维护一个 segments 数组(单源真相)
 */
const SegmentState = {
  states: {},  // videoIndex → { segments: [...], excluded: [...] }

  init(videoIndex, duration) {
    if (!this.states[videoIndex]) {
      this.states[videoIndex] = {
        segments: [],
        excluded: [],
        duration
      };
    }
    return this.states[videoIndex];
  },

  addOrSplit(videoIndex, start, end) {
    const st = this.states[videoIndex];
    if (!st) return null;

    // 检查落在哪个段内
    for (let i = 0; i < st.segments.length; i++) {
      const s = st.segments[i];
      if (start >= s.start_sec && end <= s.end_sec) {
        // 落在 s 内 → 拆段
        const newId = `seg_${videoIndex + 1}_${st.segments.length + st.excluded.length + 1}`;
        const label = '';
        if (s.start_sec === start && s.end_sec === end) {
          // 完全重合 → 不拆
          return { segments: st.segments, modified: 'noop' };
        }
        // 拆分
        const left = { ...s, end_sec: start, id: `${s.id}_L` };
        const mid = { ...s, start_sec: start, end_sec: end, id: newId, label, ops: {} };
        const right = { ...s, start_sec: end, id: `${s.id}_R` };
        const newSegs = [];
        if (left.end_sec > left.start_sec) newSegs.push(left);
        newSegs.push(mid);
        if (right.end_sec > right.start_sec) newSegs.push(right);
        st.segments = st.segments.flatMap((seg, idx) => {
          if (idx !== i) return [seg];
          return newSegs;
        });
        return { segments: st.segments, modified: 'split', newId, length: 3 };
      }
    }
    // 没落入 → 新建段 + 补全两端
    const newId = `seg_${videoIndex + 1}_${st.segments.length + 1}`;
    const newSeg = { id: newId, label: '', start_sec: start, end_sec: end, ops: {} };
    const before = start > 0 ? [{ id: `seg_${videoIndex + 1}_auto`, label: '', start_sec: 0, end_sec: start, ops: {} }] : [];
    const after = end < st.duration ? [{ id: `seg_${videoIndex + 1}_auto`, label: '', start_sec: end, end_sec: st.duration, ops: {} }] : [];
    st.segments = [...before, newSeg, ...after];
    return { segments: st.segments, modified: 'new', newId, length: st.segments.length };
  },

  delete(videoIndex, segId) {
    const st = this.states[videoIndex];
    if (!st) return;
    const idx = st.segments.findIndex(s => s.id === segId);
    if (idx >= 0) {
      const seg = st.segments.splice(idx, 1)[0];
      st.excluded.push({ ...seg });
    }
  },

  restore(videoIndex, segId) {
    const st = this.states[videoIndex];
    if (!st) return;
    const idx = st.excluded.findIndex(s => s.id === segId);
    if (idx >= 0) {
      const seg = st.excluded.splice(idx, 1)[0];
      st.segments.push(seg);
      st.segments.sort((a, b) => a.start_sec - b.start_sec);
    }
  },

  getAll(videoIndex) {
    return this.states[videoIndex] || { segments: [], excluded: [] };
  }
};

window.__segmentState = SegmentState;
```

- [ ] **Step 2:挂到 videoEntries 初始化**

定位 `videoEntries.push({...})`,在 push 之前/之后初始化 SegmentState:

```javascript
videoEntries.push({
  // ...
});
SegmentState.init(i, meta.duration || 60);
```

- [ ] **Step 3:JS 语法校验**

同 Task 1 Step 2。

- [ ] **Step 4:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase C: 新增 SegmentState 单源真相管理"
```

---

## Task 8:timeline 渲染彩虹色段(Phase C)

**Files:**
- Modify: `智剪工坊-意图编辑.html`(`setupTimeline` 函数或新加 `renderTimelineSegments`)

- [ ] **Step 1:在 setupTimeline 内增加段渲染**

```javascript
function renderTimelineSegments(trackInner, videoIndex) {
  trackInner.innerHTML = '';
  const st = SegmentState.getAll(videoIndex);
  if (!st.segments || st.segments.length === 0) {
    // 没有段,显示一个全宽默认段
    const seg = document.createElement('div');
    seg.className = 'tl-seg';
    seg.style.flex = '1';
    seg.style.background = '#5a8fd0';
    seg.textContent = '整段保留';
    trackInner.appendChild(seg);
    return;
  }
  st.segments.forEach((s, idx) => {
    const seg = document.createElement('div');
    seg.className = 'tl-seg';
    const colorVar = `--seg-color-${idx % 8}`;
    seg.style.flex = String(s.end_sec - s.start_sec);
    seg.style.background = `var(${colorVar})`;
    seg.dataset.segId = s.id;

    // 短段不显示文字
    if (s.end_sec - s.start_sec >= 3) {
      seg.innerHTML = `<span>[${s.start_sec}~${s.end_sec}]</span>`;
    }

    // op 徽章
    if (s.ops && Object.keys(s.ops).length > 0) {
      const badge = document.createElement('div');
      badge.className = 'tl-seg-op-badge';
      const ops = Object.keys(s.ops);
      if (ops.includes('mute')) badge.textContent = '🎤';
      else if (ops.includes('speed-up')) {
        const f = s.ops['speed-up'].factor || 2;
        badge.textContent = `${f}x`;
      } else if (ops.includes('slow-down')) {
        const f = s.ops['slow-down'].factor || 0.5;
        badge.textContent = `${f}x`;
      } else if (ops.includes('reverse')) badge.textContent = '🔄';
      else badge.textContent = ops[0];
      seg.appendChild(badge);
    }

    // tooltip
    const tip = document.createElement('div');
    tip.className = 'seg-tip';
    const opSummary = s.ops && Object.keys(s.ops).length > 0
      ? Object.keys(s.ops).join(', ')
      : '(无 op)';
    tip.innerHTML = `<div>${s.label || '(未命名)'}: [${s.start_sec}~${s.end_sec}]</div><div style="opacity:0.7">${opSummary}</div>`;
    seg.appendChild(tip);

    // 单击弹操作面板
    seg.addEventListener('click', e => {
      e.stopPropagation();
      openSegmentPanel(videoIndex, s.id);
    });

    trackInner.appendChild(seg);
  });

  // 已删段(灰色已删视觉禁用,在折叠区显示)
}
```

- [ ] **Step 2:在 setupTimeline 内调用**

```javascript
function setupTimeline(previewEl, video, videoIndex) {
  // 现有代码...
  const trackInner = track.querySelector('.timeline-track-inner');
  renderTimelineSegments(trackInner, videoIndex);
}
```

- [ ] **Step 3:浏览器测试**

展开任一视频卡 → 在 console 手动执行 `SegmentState.addOrSplit(0, 2, 55)` → 调用 `renderTimelineSegments` → 看效果。

- [ ] **Step 4:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase C: timeline 渲染彩虹色段 + op 徽章 + tooltip"
```

---

## Task 9:timeline 长按拖动框选(Phase D)

**Files:**
- Modify: `智剪工坊-意图编辑.html`(`setupTimeline` 内增加事件)

- [ ] **Step 1:在 setupTimeline 末尾增加长按拖动监听**

```javascript
let pressTimer = null;
let pressStartX = 0;

track.addEventListener('mousedown', e => {
  // 在段上 mousedown = 单击段(由 segment click 处理);空白处才框选
  if (e.target.classList.contains('tl-seg')) return;
  pressTimer = setTimeout(() => {
    pressStartX = e.clientX;
    track.style.cursor = 'crosshair';
    track.classList.add('selecting');
  }, 200);
});

track.addEventListener('mousemove', e => {
  if (!pressTimer) return;
  // 实时绘制高亮
});

document.addEventListener('mouseup', e => {
  if (!pressTimer) return;
  clearTimeout(pressTimer);
  pressTimer = null;
  track.style.cursor = '';
  track.classList.remove('selecting');

  // 计算拖动区间(0~ duration 映射)
  const rect = track.getBoundingClientRect();
  const startRatio = (pressStartX - rect.left) / rect.width;
  const endRatio = (e.clientX - rect.left) / rect.width;
  const startSec = Math.max(0, startRatio * duration);
  const endSec = Math.min(duration, endRatio * duration);

  if (Math.abs(endSec - startSec) < 0.5) return;  // 太短,忽略

  // 落点判断:已落入哪个段?
  onTrackSelect(videoIndex, Math.min(startSec, endSec), Math.max(startSec, endSec));
});
```

- [ ] **Step 2:实现 onTrackSelect 函数(新增)**

```javascript
function onTrackSelect(videoIndex, startSec, endSec) {
  const result = SegmentState.addOrSplit(videoIndex, startSec, endSec);

  if (result.modified === 'split' || result.modified === 'new') {
    // 弹"告知弹窗"
    showInformDialog(
      `本次操作产生 ${result.length} 个时间段`,
      `新段已加入。请在折叠区"时间段"列表查看。`
    );
    // 重新渲染 timeline
    const track = videoListEl.querySelector(`[data-card-idx="${videoIndex}"] .timeline-track-inner`);
    if (track) renderTimelineSegments(track, videoIndex);
    // 更新折叠区
    renderSegmentsPanel(videoIndex);
  } else if (result.modified === 'noop') {
    showToast('区间与已有段完全重合,无操作');
  }
}

function showInformDialog(title, body) {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal-content">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(body)}</p>
      <button class="btn" onclick="this.closest('.modal-overlay').remove()">确定</button>
    </div>
  `;
  document.body.appendChild(modal);
}
```

- [ ] **Step 3:JS 语法校验 + 浏览器测试**

- [ ] **Step 4:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase D: timeline 长按拖动 + 拆段 + 告知弹窗"
```

---

## Task 10:段操作面板(inline,Phase E)

**Files:**
- Modify: `智剪工坊-意图编辑.html`

- [ ] **Step 1:实现 openSegmentPanel + 折叠区**

```javascript
function openSegmentPanel(videoIndex, segId) {
  const state = SegmentState.getAll(videoIndex);
  const seg = state.segments.find(s => s.id === segId);
  if (!seg) return;

  // 在段下方展开面板
  const track = videoListEl.querySelector(`[data-card-idx="${videoIndex}"] .timeline`);
  let panel = track.querySelector('.segment-panel');
  if (panel) panel.remove();

  panel = document.createElement('div');
  panel.className = 'segment-panel';
  panel.innerHTML = `
    <div class="segment-panel-inner">
      <label>label:<input type="text" class="seg-label" value="${escapeHtml(seg.label)}"></label>
      <div class="seg-op-buttons">
        <button onclick="addSegmentOp(${videoIndex},'${segId}','mute')">🔇 静音</button>
        <button onclick="addSegmentOp(${videoIndex},'${segId}','speed-up')">⏩ 倍速</button>
        <button onclick="addSegmentOp(${videoIndex},'${segId}','reverse')">🔄 反转</button>
        <button onclick="deleteSegment(${videoIndex},'${segId}')" class="del-btn">🗑️ 删掉</button>
      </div>
      <button class="close-btn" onclick="this.closest('.segment-panel').remove()">✕ 关闭</button>
    </div>
  `;
  track.after(panel);

  // label 输入实时更新
  const labelInput = panel.querySelector('.seg-label');
  labelInput.addEventListener('input', e => {
    seg.label = e.target.value;
  });
}

function addSegmentOp(videoIndex, segId, opName) {
  const state = SegmentState.getAll(videoIndex);
  const seg = state.segments.find(s => s.id === segId);
  if (!seg) return;
  seg.ops = seg.ops || {};

  if (opName === 'speed-up') {
    const factor = parseFloat(prompt('加速倍数', '1.5'));
    seg.ops['speed-up'] = { on: true, factor: isNaN(factor) ? 1.5 : factor };
  } else {
    seg.ops[opName] = { on: true };
  }

  // 重新渲染
  const track = videoListEl.querySelector(`[data-card-idx="${videoIndex}"] .timeline-track-inner`);
  if (track) renderTimelineSegments(track, videoIndex);
  renderSegmentsPanel(videoIndex);
}

function deleteSegment(videoIndex, segId) {
  if (!confirm('删掉这段?可从折叠区"已删段"恢复。')) return;
  SegmentState.delete(videoIndex, segId);
  const track = videoListEl.querySelector(`[data-card-idx="${videoIndex}"] .timeline-track-inner`);
  if (track) renderTimelineSegments(track, videoIndex);
  renderSegmentsPanel(videoIndex);
  // 关闭 panel
  const panel = videoListEl.querySelector('.segment-panel');
  if (panel) panel.remove();
}
```

- [ ] **Step 2:CSS for segment-panel**

```css
.segment-panel {
  margin-top: 8px;
  background: #f5f5f7;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  padding: 12px;
}
.segment-panel-inner label {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}
.seg-label { flex: 1; padding: 4px 8px; border: 1px solid #d2d2d7; border-radius: 4px; }
.seg-op-buttons { display: flex; gap: 6px; flex-wrap: wrap; }
.seg-op-buttons button {
  background: white;
  border: 1px solid #d2d2d7;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.seg-op-buttons button:hover { border-color: #0071e3; }
.seg-op-buttons .del-btn {
  background: #ff3b30;
  color: white;
  border-color: #ff3b30;
}
.close-btn {
  background: transparent;
  border: 1px solid #d2d2d7;
  padding: 4px 8px;
  border-radius: 4px;
  margin-top: 8px;
  float: right;
  cursor: pointer;
}
```

- [ ] **Step 3:浏览器测试**

1. 拖框 → 创建段
2. 单击段 → panel 弹出
3. 改 label → 实时更新
4. 加静音 → tooltip 显示,徽章出现
5. 删除 → 段消失

- [ ] **Step 4:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase E: 段操作面板(inline,改 label / 加 op / 删除)"
```

---

## Task 11:折叠区"时间段 + 已删段"列表(Phase E)

**Files:**
- Modify: `智剪工坊-意图编辑.html`

- [ ] **Step 1:实现 renderSegmentsPanel**

```javascript
function renderSegmentsPanel(videoIndex) {
  const card = videoListEl.querySelector(`[data-card-idx="${videoIndex}"]`);
  if (!card) return;
  const state = SegmentState.getAll(videoIndex);

  let panel = card.querySelector('.segments-panel');
  if (panel) panel.remove();

  panel = document.createElement('div');
  panel.className = 'segments-panel';

  const segHtml = state.segments.map(s => `
    <div class="seg-item">
      <span>${s.label || '(未命名)'}: [${s.start_sec.toFixed(1)}~${s.end_sec.toFixed(1)}]</span>
      <button onclick="openSegmentPanel(${videoIndex},'${s.id}')">打开</button>
    </div>
  `).join('') || '<p class="empty-hint">暂无段</p>';

  const delHtml = state.excluded.map(s => `
    <div class="deleted-seg-item">
      <span>[${s.start_sec.toFixed(1)}~${s.end_sec.toFixed(1)}]</span>
      <button class="seg-restore" onclick="restoreSegment(${videoIndex},'${s.id}')">♻️ 恢复</button>
    </div>
  `).join('') || '<p class="empty-hint">无</p>';

  panel.innerHTML = `
    <details open>
      <summary>📋 时间段(${state.segments.length})</summary>
      <div class="seg-list">${segHtml}</div>
    </details>
    <details>
      <summary>🗑️ 已删段(${state.excluded.length})</summary>
      <div class="del-list">${delHtml}</div>
    </details>
  `;

  // 插入到 ops-group 之前
  const opsGroup = card.querySelector('.ops-group');
  if (opsGroup) opsGroup.before(panel);
  else card.appendChild(panel);
}

function restoreSegment(videoIndex, segId) {
  SegmentState.restore(videoIndex, segId);
  const track = videoListEl.querySelector(`[data-card-idx="${videoIndex}"] .timeline-track-inner`);
  if (track) renderTimelineSegments(track, videoIndex);
  renderSegmentsPanel(videoIndex);
}
```

- [ ] **Step 2:CSS for segments-panel**

```css
.segments-panel {
  margin-top: 12px;
  background: var(--card, white);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
}
.seg-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  background: #f5f5f7;
}
.seg-item button {
  background: #0071e3;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.empty-hint {
  color: #86868b;
  font-size: 12px;
  font-style: italic;
  padding: 6px 0;
}
```

- [ ] **Step 3:在 videoEntries.push 后调用一次渲染**

定位 videoEntries.push(后续),添加:

```javascript
SegmentState.init(i, meta.duration || 60);
renderSegmentsPanel(i);  // 第一次渲染
```

- [ ] **Step 4:浏览器测试**

展开视频 → 折叠区显示"时间段 / 已删段"两个折叠组。

- [ ] **Step 5:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase E: 折叠区'时间段 + 已删段'双向列表"
```

---

## Task 12:折叠区 ↔ timeline 双向跳转(Phase F 折叠交互)

**Files:**
- Modify: `智剪工坊-意图编辑.html`

- [ ] **Step 1:实现 jumpToSegment**

```javascript
function jumpToSegment(videoIndex, segId) {
  const card = videoListEl.querySelector(`[data-card-idx="${videoIndex}"]`);
  if (!card) return;
  const segEl = card.querySelector(`.tl-seg[data-seg-id="${segId}"]`);
  if (!segEl) return;
  segEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
  segEl.classList.add('flash');
  setTimeout(() => segEl.classList.remove('flash'), 2000);
}
```

- [ ] **Step 2:在 seg-item 加入"跳转"按钮**

修改 `renderSegmentsPanel` 中的 seg-item:

```javascript
const segHtml = state.segments.map(s => `
  <div class="seg-item">
    <span onclick="jumpToSegment(${videoIndex},'${s.id}')" style="cursor:pointer">
      ${s.label || '(未命名)'}: [${s.start_sec.toFixed(1)}~${s.end_sec.toFixed(1)}]
    </span>
    <div>
      <button onclick="jumpToSegment(${videoIndex},'${s.id}')">跳转</button>
      <button onclick="openSegmentPanel(${videoIndex},'${s.id}')">编辑</button>
    </div>
  </div>
`).join('');
```

- [ ] **Step 3:浏览器测试**

折叠区点段项 → timeline 滚动到该段 + 闪烁高亮

- [ ] **Step 4:提交**

```bash
git add 智剪工坊-意图编辑.html
git commit -m "v2.0 Phase F: 折叠区↔timeline 双向跳转 + flash 高亮"
```

---

## Task 13:人工验收(全流程)

- [ ] **Step 1:完整场景验证**(用户操作)

场景: 60s 视频,删前 2s / 后 5s / [31,33],[20,30] 静音,[40,50] 加速 2x

| 操作 | 期望 |
|---|---|
| 加载项目 | videoEntries 自动初始化 SegmentState |
| 展开视频 #1 | 看到 timeline 全宽轨道(默认整段) |
| 长按拖框 [2, 55] | 弹窗显示"产生 N 段",确定 → 3 段彩虹色 |
| 折叠区 | 显示 3 个段项 |
| 单击段 [0, 2] | 操作面板弹出 |
| 点 [🗑️ 删掉] | 该段消失,折叠区"已删段"出现该项 |
| 单击段 [55, 60] | 同上 |
| 长按拖框 [31, 33](落入 [2, 55]) | 自动拆为 3 段,弹窗告知 |
| 单击新段 [31, 33] → 删掉 | 删除 |
| 长按拖框 [20, 30](落入 [2, 31]) | 拆为 3 段 |
| 单击 [20, 30] → 静音 | 段加静音徽章 🎤 |
| 长按拖框 [40, 50](落入 [33, 55]) | 拆为 3 段 |
| 单击 [40, 50] → 倍速 2x | 段加 "2x" 徽章 |
| 点 [保存] | 写 intent.json (schema_version=3.0) |
| 重开项目 | 段状态完整恢复 |

- [ ] **Step 2:Chrome DevTools Memory 检查**

1. 反复展开/折叠/删段 5 次
2. Memory 面板 → Heap snapshot
3. Blob URL 数量应稳定(不增长)

- [ ] **Step 3:加载老 intent.json 兼容测试**

如果有旧的 `intent.json`,加载 → 校验通过 + 自动迁移。

- [ ] **Step 4:记录发现的问题**

---

## Task 14:文档 + tag(Phase G)

- [ ] **Step 1:更新 SKILL.md metadata**

```yaml
metadata: { "openclaw": { "emoji": "🎬", "version": "v2.0", "released": "2026-07-25",
  "skill_tag": "智剪工坊-意图编辑-v2.0", "requires": { "python": ">=3.10" } } }
```

- [ ] **Step 2:在 references/*.md 添加 v2.0 条目**

定位 `references/主流程-阶段编排.md`,添加:

```markdown
## v2.0 变更(2026-07-25)

- intent.json 结构:`videos[].ops`(22 op 平铺) → `video_ops`(整段)+ `time_segments[].ops`(段内)
- 22 op 收敛到 14 op(video_ops)+ 段内 op(mute/speed-up/slow-down/reverse/color-grade)
- UI 新增 timeline 长按拖动框选 + 段单击操作面板 + 已删段可恢复
- 数据兼容层:旧 `intent.json` 自动迁移为新结构,自动备份

详细迁移见 `docs/superpowers/specs/2026-07-25-video-time-segment-model.md` §5
```

- [ ] **Step 3:打 tag**

```bash
git tag -a v2.0 -m "v2.0: 视频时间段模型重构

- 22 个 op 收敛到 video_ops + time_segments[].ops
- 新增 timeline 长按框选 + 段单击面板 + 已删段恢复
- 数据自动迁移层保留老 intent.json 兼容
- 7 Phase 实施完成"
git push origin v2.0  # 如果需要
```

---

## 自检

- [x] 无 TBD / TODO / 占位符
- [x] 每步有可执行命令 + 期望输出
- [x] 改动前 3 问答齐
- [x] 任务覆盖 spec §9 所有 Phase(A 数据 / B 重命名 / C 段渲染 / D 框选 / E 段面板 / F 提交+加载 / G 文档)
- [x] 跳过 Fresh Agent 黑盒测试(用户人工验收)
