/**
 * intent.html v0.7 - 用行号范围替换 renderVideoCard + 更新 sequences JS
 */
const fs = require('fs');

const html = fs.readFileSync('D:/2Study/StudyNotes/SKILLS/智剪工坊/intent.html', 'utf8');
const lines = html.split('\n');

console.log('Total lines:', lines.length);

// ============================================================
// Step A: 找 renderVideoCard 函数开始行
// ============================================================
let renderVideoCardStart = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('function renderVideoCard(entry, i) {')) {
    renderVideoCardStart = i;
    break;
  }
}
if (renderVideoCardStart < 0) { console.log('ERROR: renderVideoCard not found'); process.exit(1); }
console.log('renderVideoCard starts at line', renderVideoCardStart + 1);

// 找函数结束行（数大括号配对）
let depth = 0, renderVideoCardEnd = -1;
for (let i = renderVideoCardStart; i < lines.length; i++) {
  for (const ch of lines[i]) {
    if (ch === '{') depth++;
    if (ch === '}') depth--;
  }
  if (depth === 0 && i > renderVideoCardStart) {
    renderVideoCardEnd = i;
    break;
  }
}
console.log('renderVideoCard ends at line', renderVideoCardEnd + 1);

// ============================================================
// Step B: 找 renderForm 里构建卡片的循环
// ============================================================
let cardLoopStart = -1, cardLoopEnd = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes("videoEntries.forEach((entry, i) => {")) {
    // 找这个 forEach 块的开始和结束
    let d = 0, started = false;
    for (let j = i; j < lines.length; j++) {
      for (const ch of lines[j]) {
        if (ch === '{') { d++; started = true; }
        if (ch === '}') d--;
      }
      if (started && d === 0) {
        cardLoopStart = i;
        cardLoopEnd = j;
        break;
      }
    }
    break;
  }
}
if (cardLoopStart < 0) { console.log('ERROR: card forEach not found'); process.exit(1); }
console.log('cardLoop at lines', cardLoopStart + 1, '-', cardLoopEnd + 1);

// ============================================================
// Step C: 找 sequences 旧加载代码（existingIntent.sequences.forEach(s => { addSequence）
// ============================================================
let seqLoadStart = -1, seqLoadEnd = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('从 existingIntent.sequences 加载已有序列')) {
    seqLoadStart = i;
    // 找这个块的结束：下一个 } else { 后再下一个 }
    // 或者直接找到 refreshAllSequenceDropdowns() 调用之前
    break;
  }
}
if (seqLoadStart < 0) {
  // Try alternative marker
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('addSequence(s.name')) {
      // 往前找缩进为 10 个空格的块开始
      for (let j = i; j >= 0; j--) {
        if (lines[j].includes('existingIntent.sequences.forEach') ||
            lines[j].includes('existingIntent.chains.forEach') ||
            lines[j].includes('existingIntent.forced_order')) {
          seqLoadStart = j - 1; // includes comment line
          break;
        }
      }
      break;
    }
  }
}
if (seqLoadStart < 0) { console.log('WARNING: old seq load code not found'); }

// ============================================================
// Step D: 找 sequences section HTML
// ============================================================
let seqSectionStart = -1, seqSectionEnd = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('<h2>视频序列')) {
    seqSectionStart = i - 1; // include <section>
    // Find </section>
    for (let j = i; j < lines.length; j++) {
      if (lines[j].includes('</section>')) {
        seqSectionEnd = j;
        break;
      }
    }
    break;
  }
}
if (seqSectionStart < 0) { console.log('WARNING: sequences section HTML not found'); }
else console.log('sequences section at lines', seqSectionStart + 1, '-', seqSectionEnd + 1);

// ============================================================
// Step E: 找旧的 sequences 函数（addSequence）
// ============================================================
let addSeqStart = -1, refreshAllEnd = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('function addSequence(name, prefillVideos')) {
    addSeqStart = i;
  }
  if (lines[i].includes('function refreshAllSequenceDropdowns()')) {
    // 找这个函数的结束
    let d = 0, started = false;
    for (let j = i; j < lines.length; j++) {
      for (const ch of lines[j]) {
        if (ch === '{') { d++; started = true; }
        if (ch === '}') d--;
      }
      if (started && d === 0) {
        refreshAllEnd = j;
        break;
      }
    }
    break;
  }
}
if (addSeqStart < 0) { console.log('WARNING: addSequence not found'); }
else console.log('addSequence at line', addSeqStart + 1, ', refreshAll ends at', refreshAllEnd + 1);

// ============================================================
// Step F: 找 collectFormData sequences 块
// ============================================================
let collectSeqStart = -1, collectSeqEnd = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].includes('sequences：从 sequences-list')) {
    collectSeqStart = i - 1;
    break;
  }
}
if (collectSeqStart < 0) { console.log('WARNING: collectFormData seq block not found'); }
else console.log('collectFormData seq at line', collectSeqStart + 1);

// ============================================================
// NOW: Build all the replacement content
// ============================================================

// New renderVideoCard function body
const newRenderVideoCard = `    function renderVideoCard(entry, i) {
      const vw = entry.videoWidth || 1920;
      const vh = entry.videoHeight || 1080;
      const aspect = vw / vh;
      const maxW = 160, maxH = 90;
      let tw, th;
      if (aspect >= 1) { tw = Math.min(maxW, Math.round(maxH * aspect)); th = Math.round(tw / aspect); }
      else { th = Math.min(maxH, Math.round(maxW / aspect)); tw = Math.round(th * aspect); }
      return \`
        <div class="video-card" data-card-idx="\${i}" data-video-index="\${entry.index}">
          <div class="video-head">
            <button class="card-toggle expanded" data-card-toggle="\${i}" title="折叠/展开">▶</button>
            <div class="video-thumb" data-play="\${i}" style="width:\${tw}px;height:\${th}px;" title="点击预览">
              \${entry.thumbDataUrl
                ? \`<img src="\${entry.thumbDataUrl}"><div class="play-hint">▶ 预览</div>\`
                : '<span>无缩略图</span>'}
            </div>
            <div class="video-meta">
              <div class="video-filename">#\${entry.index} \${escapeHtml(entry.name)}</div>
              <div class="video-auto">\${formatDuration(entry.durationSec)} · \${(entry.file.size / 1024 / 1024).toFixed(1)} MB · \${vw}×\${vh}</div>
              <div class="video-actions">
                <button class="exclude-btn" data-exclude-btn="\${i}" type="button">🚫 <span class="exclude-text">不用</span></button>
              </div>
            </div>
          </div>
          <div class="card-body">
            <div class="video-grid">
              <div class="field">
                <label>内容简介 <span class="hint">这段视频拍的是啥</span></label>
                <textarea data-video="\${i}.summary" rows="2"></textarea>
              </div>
              <div class="field">
                <label>使用意图 <span class="hint">为啥用这条</span></label>
                <textarea data-video="\${i}.intent" rows="2"></textarea>
              </div>
              <div class="field">
                <label>声音 <span class="hint">原声音轨怎么处理</span></label>
                <select data-video="\${i}.voice">
                  <option value="">—</option>
                  <option value="keep">保留</option>
                  <option value="keep-with-filler-removed">保留+去水词</option>
                  <option value="mute">静音</option>
                  <option value="bgm-only">只留 BGM</option>
                </select>
                <textarea data-video="\${i}.voice_note" rows="1" placeholder="补充说明（可选）— 例：原声音量小，需放大 1.5x"
                          style="margin-top:6px;font-size:12px;min-height:32px"></textarea>
              </div>
              <div class="field">
                <label>备注 <span class="hint">没归类的想法都写这</span></label>
                <textarea data-video="\${i}.notes" rows="2"></textarea>
              </div>
            </div>
            <div class="ops-group">
              <button class="ops-header" type="button" data-toggle-ops>
                <div class="ops-header-left">
                  <span class="disclosure">▶</span>
                  <span>基础剪辑操作</span>
                </div>
                <span class="ops-summary" data-ops-summary></span>
              </button>
              <div class="ops-body">
                \${renderOpRow('trim-head', '剪头', 'trim_head', 'number', '秒', '去掉前 N 秒', '', i)}
                \${renderOpRow('trim-tail', '剪尾', 'trim_tail', 'number', '秒', '去掉后 N 秒', '', i)}
                \${renderOpRowRange('cut-middle', '删中间', 'cut_middle', i, 'cut-from', 'cut-to', '从', '到')}
                \${renderOpRowRange('pin-range', '取时间段', 'pin_range', i, 'pin-start', 'pin-end', '从', '到', '只取这一段（vs 剪头尾=减头尾）')}
                \${renderOpRow('target-duration', '成片上限', 'target_duration', 'number', '秒', '最终成片这条最长 N 秒', 5, i)}
                \${renderOpRow('speed-up', '加速', 'speed_up', 'number', 'x', '高倍速用于缩时（如 60x 冥想缩到秒级）', 2, i, '100x 已很快')}
                \${renderOpRow('slow-down', '减速', 'slow_down', 'number', 'x', '', 0.5, i)}
                \${renderOpRow('reverse', '倒放', 'reverse', null, '', '从尾到头播', '', i)}
                \${renderOpRow('mute', '静音', 'mute', null, '', '原声 + 加的音频全静', '', i)}
                \${renderOpRow('fade-in', '淡入', 'fade_in', 'number', '秒', '', 1, i)}
                \${renderOpRow('fade-out', '淡出', 'fade_out', 'number', '秒', '', 1, i)}
                \${renderOpRowColor('color', '调色', 'color', i)}
                \${renderOpRowBgm(i)}
                \${renderOpRowReplace(i)}
                \${renderOpRowOpeningText(i)}
                \${renderOpRowInsertImage(i)}
              </div>
            </div>
            <div class="seq-section">
              <div class="seq-row">
                <label class="seq-label">接视频</label>
                <select class="seq-select" data-seq-next="\${i}">
                  <option value="">— 无（独立视频）—</option>
                </select>
                <span class="seq-hint">选完后可设转场</span>
              </div>
              <div class="seq-row" data-seq-trans-row="\${i}" style="display:none">
                <label class="seq-label">转场</label>
                <select class="seq-select" data-seq-trans="\${i}">
                  <option value="">默认（AI 选）</option>
                  <option value="none">无</option>
                  <option value="cut">直切</option>
                  <option value="fade">淡入淡出</option>
                  <option value="dissolve">溶解</option>
                  <option value="wipe-left">左擦除</option>
                  <option value="wipe-right">右擦除</option>
                  <option value="slide-up">上滑</option>
                  <option value="zoom-in">推进</option>
                  <option value="blur">模糊过渡</option>
                </select>
                <input type="number" min="0" step="0.1" value="0.5" class="seq-duration"
                       data-seq-dur="\${i}" placeholder="秒">
                <span class="seq-hint">秒</span>
              </div>
              <div class="seq-chain-preview" id="seq-chain-\${i}"></div>
              <div class="seq-error" id="seq-error-\${i}"></div>
            </div>
          </div>
        </div>
      \`;
    }`;

// New card loop in renderForm
const newCardLoop = `        videoEntries.forEach((entry, i) => {
          const card = document.createElement('div');
          card.innerHTML = renderVideoCard(entry, i);
          videoListEl.appendChild(card);
        });
        // 绑定折叠按钮（初始第一个展开，其余折叠）
        document.querySelectorAll('[data-card-toggle]').forEach(btn => {
          btn.addEventListener('click', () => {
            const idx = parseInt(btn.dataset.cardToggle, 10);
            toggleCard(idx);
          });
        });
        initSequencesUI();
        // 默认第一个展开，其余折叠
        videoEntries.forEach((_, i) => {
          const card = videoListEl.querySelector(\`.video-card[data-card-idx="\${i}"]\`);
          if (!card) return;
          if (i > 0) {
            card.classList.add('collapsed');
            const btn = card.querySelector('.card-toggle');
            if (btn) btn.classList.remove('expanded');
          }
        });`;

// New sequences load in renderForm
const newSeqLoad = `          // 从 existingIntent.sequences 加载 per-card next-video 字段（v0.7）
          if (Array.isArray(existingIntent.sequences) && existingIntent.sequences.length) {
            loadSequencesFromIntent(existingIntent.sequences);
          }`;

// New sequences UI functions
const newSeqUIFuncs = `
    // ===== Sequences UI v0.7: 每个视频卡片内嵌 next-video =====
    function initSequencesUI() {
      refreshAllSeqDropdowns();
      videoEntries.forEach((_, i) => {
        const sel = document.querySelector(\`[data-seq-next="\${i}"]\`);
        if (sel) sel.addEventListener('change', () => onSeqNextChange(i));
        const tSel = document.querySelector(\`[data-seq-trans="\${i}"]\`);
        if (tSel) tSel.addEventListener('change', () => onSeqNextChange(i));
        const dEl = document.querySelector(\`[data-seq-dur="\${i}"]\`);
        if (dEl) dEl.addEventListener('input', () => onSeqNextChange(i));
      });
    }

    function refreshAllSeqDropdowns() {
      const taken = new Set();
      videoEntries.forEach((_, i) => {
        const sel = document.querySelector(\`[data-seq-next="\${i}"]\`);
        if (sel && sel.value) taken.add(sel.value);
      });
      videoEntries.forEach((entry, i) => {
        const sel = document.querySelector(\`[data-seq-next="\${i}"]\`);
        if (!sel) return;
        const currentVal = sel.value;
        sel.innerHTML = '<option value="">— 无（独立视频）—</option>';
        videoEntries.forEach((e2, j) => {
          if (j === i) return;
          const opt = document.createElement('option');
          opt.value = e2.index;
          opt.textContent = \`#\${e2.index} \${e2.name}\`;
          if (!taken.has(String(e2.index)) || currentVal === String(e2.index)) {
            sel.appendChild(opt);
          }
        });
        if (currentVal && ![...sel.options].some(o => o.value === currentVal)) {
          sel.value = '';
        } else if (currentVal) {
          sel.value = currentVal;
        }
      });
    }

    function onSeqNextChange(i) {
      const sel = document.querySelector(\`[data-seq-next="\${i}"]\`);
      const transRow = document.querySelector(\`[data-seq-trans-row="\${i}"]\`);
      const chainEl = document.getElementById(\`seq-chain-\${i}\`);
      const errEl = document.getElementById(\`seq-error-\${i}\`);
      const val = sel ? sel.value : '';

      if (transRow) transRow.style.display = val ? 'flex' : 'none';
      if (errEl) { errEl.textContent = ''; errEl.classList.remove('show'); }

      if (!val) {
        if (chainEl) chainEl.textContent = '';
        refreshAllSeqDropdowns();
        return;
      }

      const chain = buildSeqChain(i, val);
      if (chain.includes(i)) {
        if (errEl) { errEl.textContent = '⚠️ 形成循环，禁止！'; errEl.classList.add('show'); }
        sel.value = '';
        if (chainEl) chainEl.textContent = '';
        refreshAllSeqDropdowns();
        return;
      }

      if (chainEl) {
        const chainNames = chain.map(idx => \`#\${videoEntries[idx].index} \${videoEntries[idx].name}\`);
        chainEl.textContent = '▶ 链: ' + chainNames.join(' → ');
      }

      refreshAllSeqDropdowns();
    }

    function buildSeqChain(currentIdx, initialNextVal) {
      const visited = [];
      let cur = currentIdx;
      while (cur !== undefined && !visited.includes(cur)) {
        visited.push(cur);
        const sel = document.querySelector(\`[data-seq-next="\${cur}"]\`);
        if (!sel || !sel.value) break;
        const nextEntry = videoEntries.find(e => String(e.index) === sel.value);
        if (!nextEntry) break;
        const nextI = videoEntries.findIndex(e => e.index === nextEntry.index);
        cur = nextI >= 0 ? nextI : undefined;
      }
      return visited;
    }

    function toggleCard(i) {
      const card = videoListEl.querySelector(\`.video-card[data-card-idx="\${i}"]\`);
      if (!card) return;
      const collapsed = card.classList.toggle('collapsed');
      const btn = card.querySelector('.card-toggle');
      if (btn) btn.classList.toggle('expanded', !collapsed);
    }

    function loadSequencesFromIntent(sequences) {
      sequences.forEach(seq => {
        const videos = seq.videos || [];
        const transitions = seq.transitions || [];
        for (let i = 0; i < videos.length - 1; i++) {
          const fromIndex = videos[i];
          const toIndex = videos[i + 1];
          const fromI = videoEntries.findIndex(e => e.index === fromIndex);
          if (fromI < 0) continue;
          const sel = document.querySelector(\`[data-seq-next="\${fromI}"]\`);
          if (sel) {
            sel.value = String(toIndex);
            const t = transitions.find(tr => tr.after === fromIndex);
            if (t) {
              const tSel = document.querySelector(\`[data-seq-trans="\${fromI}"]\`);
              const dEl = document.querySelector(\`[data-seq-dur="\${fromI}"]\`);
              if (tSel && t.type) tSel.value = t.type;
              if (dEl && t.duration != null) dEl.value = t.duration;
            }
          }
        }
      });
      videoEntries.forEach((_, i) => onSeqNextChange(i));
    }
`;

// New collectFormData sequences block
const newCollectSeq = `      // sequences：从每个视频的"接视频"字段重建（v0.7）
      const nextMap = {};  // videoEntries index → next entry.index
      const transMap = {}; // videoEntries index → {type, duration}
      videoEntries.forEach((_, i) => {
        const sel = document.querySelector(\`[data-seq-next="\${i}"]\`);
        if (!sel || !sel.value) return;
        const nextEntry = videoEntries.find(e => String(e.index) === sel.value);
        if (nextEntry) {
          nextMap[i] = nextEntry.index;
          const tSel = document.querySelector(\`[data-seq-trans="\${i}"]\`);
          const dEl = document.querySelector(\`[data-seq-dur="\${i}"]\`);
          if (tSel && tSel.value) {
            transMap[i] = {
              type: tSel.value,
              duration: dEl ? parseFloat(dEl.value) || 0.5 : 0.5
            };
          }
        }
      });
      // 找所有链起点（没有任何视频指向自己的）
      const hasParent = new Set(Object.values(nextMap));
      const roots = videoEntries.map((_, i) => i).filter(i => !hasParent.has(i));
      // 从每个起点顺着链走，重建 sequences
      roots.forEach(startIdx => {
        const chain = [];
        const transitions = [];
        let cur = startIdx;
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
          data.sequences.push({ videos: chain, transitions });
        }
      });
      if (data.sequences.length === 0) delete data.sequences;`;

// ============================================================
// NOW: Apply all replacements
// ============================================================

// Build replacement arrays
const result = [...lines];

// A. Replace renderVideoCard
result.splice(renderVideoCardStart, renderVideoCardEnd - renderVideoCardStart + 1, newRenderVideoCard);
console.log('A. renderVideoCard replaced');

// Need to recalculate line indices after each splice
// Instead of doing multiple splices, let's do all replacements in one pass
// Re-read from original
const origLines = [...lines];

// Clear result and rebuild
const newLines = [];
let i = 0;

while (i < origLines.length) {
  // A. renderVideoCard
  if (i === renderVideoCardStart) {
    newLines.push(...newRenderVideoCard.split('\n'));
    i = renderVideoCardEnd + 1;
    console.log('A done');
    continue;
  }

  // B. cardLoop (check before seqLoadStart since they might overlap)
  if (i === cardLoopStart) {
    newLines.push(...newCardLoop.split('\n'));
    i = cardLoopEnd + 1;
    console.log('B done');
    continue;
  }

  // C. seqLoadStart (sequences load code in renderForm)
  if (i === seqLoadStart) {
    // Find the end: the closing of the if block containing addSequence calls
    // We need to find the line that has "refreshAllSequenceDropdowns();" and the
    // following "}" that closes the "if (Array.isArray(existingIntent.videos))" block
    let j = i;
    let ifDepth = 0;
    // Count depth from the "if (Array.isArray(existingIntent.videos))" line
    let foundIf = false;
    while (j < origLines.length) {
      if (origLines[j].includes('if (Array.isArray(existingIntent.videos))')) { foundIf = true; }
      if (foundIf) {
        for (const ch of origLines[j]) { if (ch === '{') ifDepth++; if (ch === '}') ifDepth--; }
        if (ifDepth === 0 && j > i) break;
      }
      j++;
    }
    newLines.push(newSeqLoad);
    i = j;
    console.log('C done (seq load replaced)');
    continue;
  }

  // D. sequences section HTML
  if (i === seqSectionStart) {
    i = seqSectionEnd + 1;
    console.log('D done (removed sequences HTML section)');
    continue;
  }

  // E. old sequences functions (addSequence → refreshAllSequenceDropdowns)
  if (i === addSeqStart) {
    i = refreshAllEnd + 1;
    console.log('E done (removed old sequences functions)');
    continue;
  }

  // F. collectFormData sequences block
  if (i === collectSeqStart) {
    // Find the end: the "if (data.sequences.length === 0) delete data.sequences;" line
    let j = i;
    while (j < origLines.length) {
      if (origLines[j].includes('if (data.sequences.length === 0) delete data.sequences')) {
        j++; break;
      }
      j++;
    }
    newLines.push(...newCollectSeq.split('\n'));
    i = j;
    console.log('F done (collectFormData seq replaced)');
    continue;
  }

  // Default: copy line
  newLines.push(origLines[i]);
  i++;
}

// ============================================================
// Insert new sequences UI functions after renderVideoCard
// ============================================================
let afterRenderVBInsert = -1;
for (let li = 0; li < newLines.length; li++) {
  // Find the closing of renderVideoCard: "    }" followed by blank then next function
  if (newLines[li] === '    }' && newLines[li-1] && newLines[li-1].includes('`;')) {
    // Check this is the renderVideoCard close (next line should be blank or a new function)
    afterRenderVBInsert = li + 1;
    break;
  }
}

if (afterRenderVBInsert > 0) {
  const before = newLines.slice(0, afterRenderVBInsert);
  const after = newLines.slice(afterRenderVBInsert);
  const finalLines = [...before, ...newSeqUIFuncs.split('\n'), '', ...after];
  newLines.length = 0;
  newLines.push(...finalLines);
  console.log('G done (inserted new seq UI functions)');
} else {
  console.log('WARNING: Could not find insertion point for new seq UI functions');
}

// Version bump
const finalHtml = newLines.join('\n')
  .replace("version: '0.6'", "version: '0.7'");

fs.writeFileSync('D:/2Study/StudyNotes/SKILLS/智剪工坊/intent.html', finalHtml, 'utf8');
console.log(`\nDone. Lines: ${origLines.length} → ${newLines.length}`);
console.log(`Chars: ${origLines.join('\n').length} → ${finalHtml.length}`);
