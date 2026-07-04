/**
 * Step 6: Replace old sequences functions with new v0.7 ones
 */
const fs = require('fs');
let html = fs.readFileSync('D:/2Study/StudyNotes/SKILLS/智剪工坊/intent.html', 'utf8');

const marker = '    // ===== Sequences =====';
const startIdx = html.indexOf(marker);
if (startIdx < 0) { console.log('ERROR: Sequences marker not found'); process.exit(1); }

// Find end: the closing of refreshAllSequenceDropdowns
const refreshMarker = '    function refreshAllSequenceDropdowns() {';
const refreshIdx = html.indexOf(refreshMarker, startIdx);
if (refreshIdx < 0) { console.log('ERROR: refreshAllSequenceDropdowns not found'); process.exit(1); }

// Count braces from refreshMarker to find end
let depth = 0, inFn = false, endIdx = 0;
for (let i = refreshIdx; i < html.length; i++) {
  if (html[i] === '{') { depth++; inFn = true; }
  if (html[i] === '}') depth--;
  if (inFn && depth === 0) { endIdx = i + 1; break; }
}
console.log(`Old sequences block: chars ${startIdx}-${endIdx} (${endIdx-startIdx} chars)`);

// New sequences functions
const newBlock = `    // ===== Sequences UI v0.7: 每个视频卡片内嵌 next-video =====
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

html = html.substring(0, startIdx) + newBlock + '\n' + html.substring(endIdx);
fs.writeFileSync('D:/2Study/StudyNotes/SKILLS/智剪工坊/intent.html', html, 'utf8');
console.log('Done. New size:', html.length);
