"""
intent.html v0.7 重写：
- 删除 视频序列 顶层区域
- 每张视频卡片可折叠 + 加「下一个视频」+「转场特效」字段
- collectFormData 从 next-video 链重建 sequences
"""
import re

with open(r'D:\2Study\StudyNotes\SKILLS\智剪工坊\intent.html', encoding='utf-8') as f:
    html = f.read()

# ============================================================
# 1. CSS: 添加折叠相关样式，替换 Sequences 相关样式
# ============================================================
old_css = """
    /* ============ Sequences ============ */
    .sequences-list { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
    .sequence {
      background: var(--gray-fill); border-radius: 10px; padding: 10px 12px;
    }
    .sequence-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
    .sequence-num {
      font-size: 12px; font-weight: 600; color: var(--blue);
      font-family: ui-monospace, monospace;
    }
    .sequence-name {
      flex: 1; padding: 5px 10px; border: 1px solid var(--border);
      border-radius: 6px; font-size: 13px; font-family: inherit; background: var(--card);
    }
    .sequence-remove {
      padding: 4px 10px; font-size: 12px; border: 1px solid var(--border);
      background: var(--card); border-radius: 6px; cursor: pointer; color: var(--red);
      font-family: inherit;
    }
    .sequence-remove:hover { background: #fff0f0; }
    .sequence-rows { display: flex; flex-direction: column; gap: 4px; margin-bottom: 6px; }
    .sequence-row { display: flex; align-items: center; gap: 6px; }
    .sequence-row .row-num {
      font-size: 11px; color: var(--secondary); min-width: 36px; font-family: ui-monospace, monospace;
    }
    .sequence-row select.video-select { flex: 1; }
    .sequence-row .row-remove {
      padding: 4px 10px; font-size: 12px; border: 1px solid var(--border);
      background: var(--card); border-radius: 6px; cursor: pointer; color: var(--secondary);
      font-family: inherit;
    }
    .sequence-row .row-remove:hover { background: #fff0f0; color: var(--red); border-color: #fcc; }
    .sequence-transition {
      display: flex; align-items: center; gap: 6px; padding: 4px 0 4px 38px;
      font-size: 12px; color: var(--secondary);
    }
    .sequence-transition .arrow { color: var(--blue); font-size: 14px; }
    .sequence-transition select { width: 110px; padding: 4px 8px; font-size: 12px; }
    .sequence-transition input[type="number"] { width: 60px; padding: 4px 8px; font-size: 12px; }
    .sequence-add-row {
      font-size: 12px; color: var(--blue); background: transparent; border: none;
      cursor: pointer; padding: 4px 0; font-family: inherit;
    }
    .sequence-add-row:hover { text-decoration: underline; }
    .sequence-actions { display: flex; gap: 8px; }"""

new_css = """
    /* ============ 可折叠视频卡片 ============ */
    .video-card { transition: max-height 0.25s ease, opacity 0.2s; overflow: hidden; }
    .video-card .card-toggle {
      width: 28px; height: 28px; border-radius: 50%; border: 1px solid var(--border);
      background: var(--card); cursor: pointer; font-size: 14px; color: var(--secondary);
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      transition: background 0.15s, color 0.15s; user-select: none;
    }
    .video-card .card-toggle:hover { background: var(--gray-fill); color: var(--label); }
    .video-card .card-toggle.expanded { transform: rotate(90deg); }
    .card-body { transition: opacity 0.2s; }
    .video-card.collapsed .card-body { display: none; }
    .video-card.collapsed .video-thumb { opacity: 0.7; }
    /* 折叠时隐藏 .video-head 里的 toggle，用缩略图区域 toggle */
    .video-card .card-toggle-placeholder {
      width: 28px; flex-shrink: 0;
    }

    /* ============ 视频序列（内嵌每个卡片） ============ */
    .seq-section {
      background: var(--gray-fill); border-radius: 8px; padding: 10px 12px; margin-top: 10px;
    }
    .seq-row {
      display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    }
    .seq-row label.seq-label {
      font-size: 12px; font-weight: 600; color: var(--label); min-width: 70px;
      margin-bottom: 0; display: inline-block;
    }
    .seq-row select.seq-select { width: auto; min-width: 160px; padding: 6px 10px; font-size: 12px; }
    .seq-row .seq-duration { width: 60px; padding: 6px 8px; font-size: 12px; }
    .seq-row .seq-hint { font-size: 11px; color: var(--secondary); }
    .seq-chain-preview {
      font-size: 11px; color: var(--blue); background: rgba(0,122,255,0.08);
      border-radius: 6px; padding: 4px 8px; margin-top: 6px; font-family: ui-monospace, monospace;
      word-break: break-all;
    }
    .seq-error { color: var(--red); font-size: 12px; margin-top: 4px; display: none; }
    .seq-error.show { display: block; }"""

html = html.replace(old_css, new_css)

# ============================================================
# 2. HTML: 删除视频序列 section
# ============================================================
# 删除从 <section> 含"视频序列" 到 </section>（下一个 <section> 之前）
seq_section_pattern = re.compile(
    r'\s*<section>\s*\n\s*<h2>视频序列[^<]*</h2>\s*.*?</section>',
    re.DOTALL
)
html = seq_section_pattern.sub('', html)

# ============================================================
# 3. renderVideoCard: 折叠 + 下一个视频 + 转场特效
# ============================================================
# 旧的 video-card 头部（替换展开状态）
old_card_head = """    .video-card {
      border: 1px solid var(--border); border-radius: 14px; padding: 14px;
      margin-bottom: 12px; background: #FBFBFD; position: relative; transition: opacity 0.2s;
    }
    .video-card:last-child { margin-bottom: 0; }
    .video-card.excluded { opacity: 0.45; }
    .video-number {
      position: absolute; top: -8px; left: 12px;
      background: var(--label); color: #fff; font-size: 11px; font-weight: 600;
      padding: 3px 8px; border-radius: 6px; font-family: ui-monospace, monospace;
    }
    .video-head { display: flex; gap: 12px; margin-bottom: 12px; align-items: flex-start; }
    .video-thumb {
      background: #000; border-radius: 8px; flex-shrink: 0; overflow: hidden;
      display: flex; align-items: center; justify-content: center;
      color: var(--secondary); font-size: 11px; cursor: pointer; position: relative;
      max-width: 160px; max-height: 90px;
    }
    .video-thumb img { width: 100%; height: 100%; object-fit: contain; display: block; }
    .video-thumb .play-hint {
      position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
      background: rgba(0,0,0,0.4); color: #fff; font-size: 12px; opacity: 0; transition: opacity 0.15s;
    }
    .video-thumb:hover .play-hint { opacity: 1; }
    .video-meta { flex: 1; min-width: 0; }
    .video-filename { font-weight: 600; font-size: 13px; color: var(--label); word-break: break-all; }
    .video-auto { font-size: 11px; color: var(--secondary); margin-top: 3px; }
    .video-actions { display: flex; gap: 6px; margin-top: 6px; }
    .video-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
    .video-grid .field { margin-bottom: 0; }
    @media (max-width: 640px) {
      .video-grid { grid-template-columns: 1fr; }
      .video-thumb { max-width: 130px; max-height: 80px; }
    }"""

new_card_head = """    .video-card {
      border: 1px solid var(--border); border-radius: 14px; padding: 14px;
      margin-bottom: 12px; background: #FBFBFD; position: relative; transition: opacity 0.2s;
    }
    .video-card:last-child { margin-bottom: 0; }
    .video-card.excluded { opacity: 0.45; }
    .video-number {
      position: absolute; top: -8px; left: 12px;
      background: var(--label); color: #fff; font-size: 11px; font-weight: 600;
      padding: 3px 8px; border-radius: 6px; font-family: ui-monospace, monospace;
    }
    .video-head { display: flex; gap: 12px; margin-bottom: 0; align-items: flex-start; }
    .video-thumb {
      background: #000; border-radius: 8px; flex-shrink: 0; overflow: hidden;
      display: flex; align-items: center; justify-content: center;
      color: var(--secondary); font-size: 11px; cursor: pointer; position: relative;
      max-width: 160px; max-height: 90px;
    }
    .video-thumb img { width: 100%; height: 100%; object-fit: contain; display: block; }
    .video-thumb .play-hint {
      position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
      background: rgba(0,0,0,0.4); color: #fff; font-size: 12px; opacity: 0; transition: opacity 0.15s;
    }
    .video-thumb:hover .play-hint { opacity: 1; }
    .video-meta { flex: 1; min-width: 0; }
    .video-filename { font-weight: 600; font-size: 13px; color: var(--label); word-break: break-all; }
    .video-auto { font-size: 11px; color: var(--secondary); margin-top: 3px; }
    .video-actions { display: flex; gap: 6px; margin-top: 6px; }
    .video-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }
    .video-grid .field { margin-bottom: 0; }
    @media (max-width: 640px) {
      .video-grid { grid-template-columns: 1fr; }
      .video-thumb { max-width: 130px; max-height: 80px; }
    }"""

html = html.replace(old_card_head, new_card_head)

# ============================================================
# 4. renderVideoCard JS: 重写函数体
# ============================================================
old_render_videocard = """    function renderVideoCard(entry, i) {
      const vw = entry.videoWidth || 1920;
      const vh = entry.videoHeight || 1080;
      const aspect = vw / vh;
      const maxW = 160, maxH = 90;
      let tw, th;
      if (aspect >= 1) { tw = Math.min(maxW, Math.round(maxH * aspect)); th = Math.round(tw / aspect); }
      else { th = Math.min(maxH, Math.round(maxW / aspect)); tw = Math.round(ch * aspect); }
      return `
        <div class="video-number">#${entry.index}</div>
        <div class="video-head">
          <div class="video-thumb" data-play="${i}" style="width:${tw}px;height:${th}px;" title="点击预览">
            ${entry.thumbDataUrl
              ? `<img src="${entry.thumbDataUrl}"><div class="play-hint">▶ 预览</div>`
              : '<span>无缩略图</span>'}
          </div>
          <div class="video-meta">
            <div class="video-filename">${escapeHtml(entry.name)}</div>
            <div class="video-auto">${formatDuration(entry.durationSec)} · ${(entry.file.size / 1024 / 1024).toFixed(1)} MB · ${vw}×${vh}</div>
            <div class="video-actions">
              <button class="exclude-btn" data-exclude-btn="${i}" type="button">🚫 <span class="exclude-text">不用</span></button>
            </div>
          </div>
        </div>
        <div class="video-grid">
          <div class="field">
            <label>内容简介 <span class="hint">这段视频拍的是啥</span></label>
            <textarea data-video="${i}.summary" rows="2"></textarea>
          </div>
          <div class="field">
            <label>使用意图 <span class="hint">为啥用这条</span></label>
            <textarea data-video="${i}.intent" rows="2"></textarea>
          </div>
          <div class="field">
            <label>声音 <span class="hint">原声音轨怎么处理</span></label>
            <select data-video="${i}.voice">
              <option value="">—</option>
              <option value="keep">保留</option>
              <option value="keep-with-filler-removed">保留+去水词</option>
              <option value="mute">静音</option>
              <option value="bgm-only">只留 BGM</option>
            </select>
            <textarea data-video="${i}.voice_note" rows="1" placeholder="补充说明（可选）— 例：原声音量小，需放大 1.5x"
                      style="margin-top:6px;font-size:12px;min-height:32px"></textarea>
          </div>
          <div class="field">
            <label>备注 <span class="hint">没归类的想法都写这</span></label>
            <textarea data-video="${i}.notes" rows="2"></textarea>
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
            ${renderOpRow('trim-head', '剪头', 'trim_head', 'number', '秒', '去掉前 N 秒', '', i)}
            ${renderOpRow('trim-tail', '剪尾', 'trim_tail', 'number', '秒', '去掉后 N 秒', '', i)}
            ${renderOpRowRange('cut-middle', '删中间', 'cut_middle', i, 'cut-from', 'cut-to', '从', '到')}
            ${renderOpRowRange('pin-range', '取时间段', 'pin_range', i, 'pin-start', 'pin-end', '从', '到', '只取这一段（vs 剪头尾=减头尾）')}
            ${renderOpRow('target-duration', '成片上限', 'target_duration', 'number', '秒', '最终成片这条最长 N 秒', 5, i)}
            ${renderOpRow('speed-up', '加速', 'speed_up', 'number', 'x', '高倍速用于缩时（如 60x 冥想缩到秒级）', 2, i, '100x 已很快')}
            ${renderOpRow('slow-down', '减速', 'slow_down', 'number', 'x', '', 0.5, i)}
            ${renderOpRow('reverse', '倒放', 'reverse', null, '', '从尾到头播', '', i)}
            ${renderOpRow('mute', '静音', 'mute', null, '', '原声 + 加的音频全静', '', i)}
            ${renderOpRow('fade-in', '淡入', 'fade_in', 'number', '秒', '', 1, i)}
            ${renderOpRow('fade-out', '淡出', 'fade_out', 'number', '秒', '', 1, i)}
            ${renderOpRowColor('color', '调色', 'color', i)}
            ${renderOpRowBgm(i)}
            ${renderOpRowReplace(i)}
            ${renderOpRowOpeningText(i)}
            ${renderOpRowInsertImage(i)}
          </div>
        </div>
      `;
    }"""

new_render_videocard = """    function renderVideoCard(entry, i) {
      const vw = entry.videoWidth || 1920;
      const vh = entry.videoHeight || 1080;
      const aspect = vw / vh;
      const maxW = 160, maxH = 90;
      let tw, th;
      if (aspect >= 1) { tw = Math.min(maxW, Math.round(maxH * aspect)); th = Math.round(tw / aspect); }
      else { th = Math.min(maxH, Math.round(maxW / aspect)); tw = Math.round(th * aspect); }
      return `
        <div class="video-number">#${entry.index}</div>
        <div class="video-head">
          <div class="card-toggle-placeholder"></div>
          <div class="card-toggle expanded" data-card-toggle="${i}" title="折叠/展开">▶</div>
          <div class="video-thumb" data-play="${i}" style="width:${tw}px;height:${th}px;" title="点击预览">
            ${entry.thumbDataUrl
              ? `<img src="${entry.thumbDataUrl}"><div class="play-hint">▶ 预览</div>`
              : '<span>无缩略图</span>'}
          </div>
          <div class="video-meta">
            <div class="video-filename">${escapeHtml(entry.name)}</div>
            <div class="video-auto">${formatDuration(entry.durationSec)} · ${(entry.file.size / 1024 / 1024).toFixed(1)} MB · ${vw}×${vh}</div>
            <div class="video-actions">
              <button class="exclude-btn" data-exclude-btn="${i}" type="button">🚫 <span class="exclude-text">不用</span></button>
            </div>
          </div>
        </div>
        <div class="card-body">
          <div class="video-grid">
            <div class="field">
              <label>内容简介 <span class="hint">这段视频拍的是啥</span></label>
              <textarea data-video="${i}.summary" rows="2"></textarea>
            </div>
            <div class="field">
              <label>使用意图 <span class="hint">为啥用这条</span></label>
              <textarea data-video="${i}.intent" rows="2"></textarea>
            </div>
            <div class="field">
              <label>声音 <span class="hint">原声音轨怎么处理</span></label>
              <select data-video="${i}.voice">
                <option value="">—</option>
                <option value="keep">保留</option>
                <option value="keep-with-filler-removed">保留+去水词</option>
                <option value="mute">静音</option>
                <option value="bgm-only">只留 BGM</option>
              </select>
              <textarea data-video="${i}.voice_note" rows="1" placeholder="补充说明（可选）"
                        style="margin-top:6px;font-size:12px;min-height:32px"></textarea>
            </div>
            <div class="field">
              <label>备注 <span class="hint">没归类的想法都写这</span></label>
              <textarea data-video="${i}.notes" rows="2"></textarea>
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
              ${renderOpRow('trim-head', '剪头', 'trim_head', 'number', '秒', '去掉前 N 秒', '', i)}
              ${renderOpRow('trim-tail', '剪尾', 'trim_tail', 'number', '秒', '去掉后 N 秒', '', i)}
              ${renderOpRowRange('cut-middle', '删中间', 'cut_middle', i, 'cut-from', 'cut-to', '从', '到')}
              ${renderOpRowRange('pin-range', '取时间段', 'pin_range', i, 'pin-start', 'pin-end', '从', '到', '只取这一段')}
              ${renderOpRow('speed-up', '加速', 'speed_up', 'number', 'x', '高倍速缩时（如冥想60x→秒级）', 2, i)}
              ${renderOpRow('slow-down', '减速', 'slow_down', 'number', 'x', '', 0.5, i)}
              ${renderOpRow('reverse', '倒放', 'reverse', null, '', '从尾到头播', '', i)}
              ${renderOpRow('mute', '静音', 'mute', null, '', '原声全静', '', i)}
              ${renderOpRow('fade-in', '淡入', 'fade_in', 'number', '秒', '', 1, i)}
              ${renderOpRow('fade-out', '淡出', 'fade_out', 'number', '秒', '', 1, i)}
              ${renderOpRowColor('color', '调色', 'color', i)}
              ${renderOpRowBgm(i)}
              ${renderOpRowReplace(i)}
            </div>
          </div>
          <div class="seq-section">
            <div class="seq-row">
              <label class="seq-label">接视频</label>
              <select class="seq-select" data-seq-next="${i}">
                <option value="">— 无（独立视频）—</option>
              </select>
              <span class="seq-hint">接在哪个视频之后播放</span>
            </div>
            <div class="seq-row" id="seq-transition-row-${i}" style="display:none">
              <label class="seq-label">转场</label>
              <select class="seq-select" data-seq-trans="${i}" style="min-width:120px">
                <option value="">默认（AI 选）</option>
                <option value="cut">直切</option>
                <option value="fade">淡入淡出</option>
                <option value="dissolve">溶解</option>
                <option value="wipe-left">左擦除</option>
                <option value="wipe-right">右擦除</option>
                <option value="slide-up">上滑</option>
                <option value="zoom-in">推进</option>
                <option value="blur">模糊过渡</option>
              </select>
              <input type="number" class="seq-duration" data-seq-dur="${i}" min="0" step="0.1" value="0.5" placeholder="秒">
              <span class="seq-hint">秒</span>
            </div>
            <div class="seq-chain-preview" id="seq-chain-${i}"></div>
            <div class="seq-error" id="seq-error-${i}"></div>
          </div>
        </div>
      `;
    }"""

html = html.replace(old_render_videocard, new_render_videocard)

# ============================================================
# 5. renderForm: 删除 sequences 处理和 addSequence 调用
# ============================================================
# 删除 sequences 加载逻辑（renderForm 中的相关代码）
old_seq_loading = """
        // 序列加载（向后兼容旧 chains / forced_order + transitions）
        if (Array.isArray(existingIntent.sequences) && existingIntent.sequences.length) {
          existingIntent.sequences.forEach(s => {
            addSequence(s.name || '', s.videos || [], existingIntent.videos || [], s.transitions || []);
          });
        } else if (Array.isArray(existingIntent.chains) && existingIntent.chains.length) {
          // 旧 v0.3 格式：chains + 独立的 transitions
          const oldTransitions = Array.isArray(existingIntent.transitions) ? existingIntent.transitions : [];
          existingIntent.chains.forEach(c => {
            const videos = Array.isArray(c.videos) ? c.videos : (Array.isArray(c) ? c : []);
            // 把属于这个序列内部的旧 transitions 拎出来
            const seqTransitions = [];
            for (let i = 0; i < videos.length - 1; i++) {
              const t = oldTransitions.find(t => t.from === videos[i] && t.to === videos[i+1]);
              if (t) seqTransitions.push({ after: videos[i], type: t.type, duration: t.duration });
            }
            addSequence(c.name || '', videos, existingIntent.videos || [], seqTransitions);
          });
        } else if (Array.isArray(existingIntent.forced_order) && existingIntent.forced_order.length) {
          addSequence('顺序', existingIntent.forced_order, existingIntent.videos || [], []);
        } else {
          addSequence('', null, null, []);
        }
      } else {
        addSequence('', null, null, []);
      }

      refreshAllSequenceDropdowns();"""

new_seq_loading = """
      } else {
        // 无 existingIntent，每个视频卡片默认折叠
      }

      // 初始化 sequences UI（用 next-video 字段）
      initSequencesUI();"""

html = html.replace(old_seq_loading, new_seq_loading)

# ============================================================
# 6. 删除旧 sequences JS 函数
# ============================================================
# 删除 addSequence, addSequenceRow, refreshAllSequenceDropdowns, rebuildSequenceTransitions 等
old_seq_funcs = re.compile(
    r'\n    // ===== Sequences =====.*?\n    function previewVideo\(entry\)',
    re.DOTALL
)
html = old_seq_funcs.sub('\n\n    function previewVideo(entry)', html)

# ============================================================
# 7. collectFormData: 从 next-video 链重建 sequences
# ============================================================
old_collect_end = """      // sequences
      sequencesListEl.querySelectorAll('.sequence').forEach(seqEl => {
        const name = seqEl.querySelector('.sequence-name').value.trim();
        const videos = [];
        const transitions = [];
        const rowEls = seqEl.querySelectorAll('.sequence-rows .sequence-row');
        rowEls.forEach((row, i) => {
          const v = row.querySelector('select.video-select').value;
          if (v) {
            // dropdown value = entry.index（1-based），找对应 entry 并存 filename
            const entry = videoEntries.find(e => String(e.index) === v);
            if (entry) videos.push(entry.name);
            // 找紧接着的 transition 行
            const tRow = row.nextElementSibling;
            if (tRow && tRow.classList.contains('sequence-transition') && i < rowEls.length - 1) {
              const type = tRow.querySelector('.transition-type').value;
              const dur = parseFloat(tRow.querySelector('.transition-duration').value);
              const t = { after: entry ? entry.name : v };
              if (type) t.type = type;
              if (!isNaN(dur)) t.duration = dur;
              transitions.push(t);
            }
          }
        });
        if (videos.length > 0) {
          const seq = { videos };
          if (name) seq.name = name;
          if (transitions.length > 0) seq.transitions = transitions;
          data.sequences.push(seq);
        }
      });
      if (data.sequences.length === 0) delete data.sequences;
"""

new_collect_end = """
      // sequences：从每个视频的"下一个视频"字段重建
      const nextMap = {};  // entryIndex → nextEntryIndex
      const transMap = {}; // entryIndex → {type, duration}
      videoEntries.forEach((_, i) => {
        const sel = document.querySelector(`[data-seq-next="${i}"]`);
        if (sel && sel.value) {
          nextMap[i] = parseInt(sel.value, 10);
          const tSel = document.querySelector(`[data-seq-trans="${i}"]`);
          const dEl = document.querySelector(`[data-seq-dur="${i}"]`);
          if (tSel && tSel.value) {
            transMap[i] = {
              type: tSel.value,
              duration: dEl ? parseFloat(dEl.value) || 0.5 : 0.5
            };
          }
        }
      });
      // 找所有起点（没有任何视频指向自己的）
      const hasParent = new Set(Object.values(nextMap));
      const roots = videoEntries.map((_, i) => i).filter(i => !hasParent.has(i));
      // 从每个起点顺着链走，重建 sequences
      roots.forEach(startIdx => {
        const chain = [];
        let cur = startIdx;
        while (cur !== undefined) {
          chain.push(videoEntries[cur].name);
          cur = nextMap[cur];
        }
        const transitions = [];
        for (let i = 0; i < chain.length - 1; i++) {
          const fromIdx = videoEntries.findIndex(e => e.name === chain[i]);
          if (transMap[fromIdx]) {
            transitions.push({
              after: chain[i],
              type: transMap[fromIdx].type,
              duration: transMap[fromIdx].duration
            });
          }
        }
        if (chain.length > 0) {
          data.sequences.push({ videos: chain, transitions });
        }
      });
      if (data.sequences.length === 0) delete data.sequences;
"""

html = html.replace(old_collect_end, new_collect_end)

# ============================================================
# 8. 在文件末尾 </script> 前添加新函数
# ============================================================
new_functions = """
    // ============================================================
    // Sequences UI v0.7: 每个视频卡片内嵌"下一个视频"字段
    // ============================================================

    function initSequencesUI() {
      // 渲染所有 next-video 下拉选项
      refreshAllSeqDropdowns();
      // 绑定每个下拉的 change 事件
      videoEntries.forEach((_, i) => {
        const sel = document.querySelector(`[data-seq-next="${i}"]`);
        if (sel) sel.addEventListener('change', () => onSeqNextChange(i));
      });
      // 第一个视频展开，其余折叠
      document.querySelectorAll('.video-card').forEach((card, i) => {
        if (i > 0) card.classList.add('collapsed');
        const btn = card.querySelector('.card-toggle');
        if (btn) {
          btn.classList.toggle('expanded', i === 0);
        }
      });
    }

    function refreshAllSeqDropdowns() {
      // 收集当前所有"下一个视频"的值（这些视频已被指向，不能再被选）
      const taken = new Set();
      videoEntries.forEach((_, i) => {
        const sel = document.querySelector(`[data-seq-next="${i}"]`);
        if (sel && sel.value) taken.add(sel.value);
      });
      videoEntries.forEach((entry, i) => {
        const sel = document.querySelector(`[data-seq-next="${i}"]`);
        if (!sel) return;
        const currentVal = sel.value;
        sel.innerHTML = '<option value="">— 无（独立视频）—</option>';
        videoEntries.forEach((e2, j) => {
          if (j === i) return;  // 不能选自己
          const opt = document.createElement('option');
          opt.value = String(j);
          opt.textContent = `#${e2.index} ${e2.name}`;
          if (!taken.has(String(j)) || currentVal === String(j)) {
            // 未被占用 或 当前已选中（允许保留）
            sel.appendChild(opt);
          }
        });
        if (currentVal && ![...sel.options].some(o => o.value === currentVal)) {
          sel.value = '';  // 当前值已不可选，清空
        } else if (currentVal) {
          sel.value = currentVal;
        }
      });
      // 更新所有 chain preview 和 transition row 可见性
      videoEntries.forEach((_, i) => onSeqNextChange(i));
    }

    function onSeqNextChange(i) {
      const sel = document.querySelector(`[data-seq-next="${i}"]`);
      const transRow = document.getElementById(`seq-transition-row-${i}`);
      const chainEl = document.getElementById(`seq-chain-${i}`);
      const errEl = document.getElementById(`seq-error-${i}`);
      const val = sel ? sel.value : '';

      // 显示/隐藏转场行
      if (transRow) transRow.style.display = val ? 'flex' : 'none';

      // 清除错误
      if (errEl) { errEl.textContent = ''; errEl.classList.remove('show'); }

      if (!val) {
        if (chainEl) chainEl.textContent = '';
        // 刷新所有下拉（可能解锁某些选项）
        refreshAllSeqDropdowns();
        return;
      }

      // 循环检测
      const chain = buildChain(i, val);
      const hasCycle = chain.includes(i);
      if (hasCycle) {
        if (errEl) { errEl.textContent = '⚠️ 形成循环，禁止！'; errEl.classList.add('show'); }
        sel.value = '';  // 拒绝
        if (chainEl) chainEl.textContent = '';
        refreshAllSeqDropdowns();
        return;
      }

      // 显示链预览
      if (chainEl) {
        const chainNames = chain.map(idx => {
          const e = videoEntries[idx];
          return `#${e.index} ${e.name}`;
        });
        chainEl.textContent = '▶ 链: ' + chainNames.join(' → ');
      }

      // 刷新所有下拉（更新 taken 集合）
      refreshAllSeqDropdowns();
    }

    function buildChain(currentIdx, initialNextVal) {
      // 从 currentIdx 顺着 next 链走到终点
      const visited = [];
      let cur = currentIdx;
      while (cur !== undefined) {
        if (visited.includes(cur)) break;  // 循环
        visited.push(cur);
        const sel = document.querySelector(`[data-seq-next="${cur}"]`);
        cur = (sel && sel.value) ? parseInt(sel.value, 10) : undefined;
      }
      // 如果 initialNextVal 形成循环（cur 已访问过），返回 currentIdx 在链中的位置之前
      if (visited.includes(currentIdx)) {
        const idx = visited.indexOf(currentIdx);
        return visited.slice(0, idx);
      }
      return visited;
    }

    function toggleCard(i) {
      const card = document.querySelector(`.video-card[data-card-idx="${i}"]`) ||
                   document.querySelectorAll('.video-card')[i];
      if (!card) return;
      const collapsed = card.classList.toggle('collapsed');
      const btn = card.querySelector('.card-toggle');
      if (btn) btn.classList.toggle('expanded', !collapsed);
    }
"""

html = html.replace('  </script>', new_functions + '\n  </script>')

# ============================================================
# 9. renderForm 末尾：绑定折叠按钮事件 + 调用 initSequencesUI
# ============================================================
old_renderform_end = """
      refreshAllSequenceDropdowns();
      updateAllOpsSummaries();
      updateLengthDashboard();
      updateRevisionUI((existingIntent?._meta?.revision || 0) + 1);
    }"""

new_renderform_end = """
      refreshAllSeqDropdowns();
      initSequencesUI();
      // 绑定折叠按钮
      document.querySelectorAll('[data-card-toggle]').forEach(btn => {
        btn.addEventListener('click', () => {
          const idx = parseInt(btn.dataset.cardToggle, 10);
          toggleCard(idx);
        });
      });
      updateAllOpsSummaries();
      updateLengthDashboard();
      updateRevisionUI((existingIntent?._meta?.revision || 0) + 1);
    }"""

html = html.replace(old_renderform_end, new_renderform_end)

# ============================================================
# 10. renderVideoCard 结果：加 data-card-idx 属性
# ============================================================
html = html.replace(
    '<div class="card-toggle expanded" data-card-toggle="${i}"',
    '<div class="card-toggle expanded" data-card-toggle="${i}" data-card-idx="${i}"'
)

# ============================================================
# 11. video-card 渲染时加 data-card-idx
# ============================================================
html = html.replace(
    '<div class="video-card">',
    '<div class="video-card" data-card-idx="${i}">'
)

# ============================================================
# 12. 加载 existingIntent.videos 的 summary/intent/voice/notes/exclude 字段
#    + 加载 sequences 到 next-video 字段
# ============================================================
old_video_restore = """        if (Array.isArray(existingIntent.videos)) {
          existingIntent.videos.forEach((v) => {
            const idx = videoEntries.findIndex(e => e.name === v.file);
            if (idx === -1) return;
            const card = videoListEl.querySelector(`[data-video-index="${idx+1}"]`);
            for (const key of ['summary', 'intent', 'voice', 'notes', 'voice_note']) {
              const el = document.querySelector(`[data-video="${idx}.${key}"]`);
              if (el && v[key] != null) el.value = v[key];
            }
            if (v.ops && card) {
              restoreOps(card, v.ops);
              if (Object.values(v.ops).some(o => o && o.on)) card.querySelector('.ops-group')?.classList.add('open');
            }
            if (v.exclude && card) {
              card.classList.add('excluded');
              const btn = card.querySelector('[data-exclude-btn]');
              if (btn) { btn.classList.add('active'); btn.querySelector('.exclude-text').textContent = '已排除'; }
              videoEntries[idx].excluded = true;
            }
          });
        }"""

new_video_restore = """        if (Array.isArray(existingIntent.videos)) {
          existingIntent.videos.forEach((v) => {
            const idx = videoEntries.findIndex(e => e.name === v.file);
            if (idx === -1) return;
            const card = videoListEl.querySelector(`[data-video-index="${idx+1}"]`);
            for (const key of ['summary', 'intent', 'voice', 'notes', 'voice_note']) {
              const el = document.querySelector(`[data-video="${idx}.${key}"]`);
              if (el && v[key] != null) el.value = v[key];
            }
            if (v.ops && card) {
              restoreOps(card, v.ops);
              if (Object.values(v.ops).some(o => o && o.on)) card.querySelector('.ops-group')?.classList.add('open');
            }
            if (v.exclude && card) {
              card.classList.add('excluded');
              const btn = card.querySelector('[data-exclude-btn]');
              if (btn) { btn.classList.add('active'); btn.querySelector('.exclude-text').textContent = '已排除'; }
              videoEntries[idx].excluded = true;
            }
          });
          // 从 existingIntent.sequences 加载"下一个视频"字段
          if (Array.isArray(existingIntent.sequences) && existingIntent.sequences.length) {
            loadSequencesFromIntent(existingIntent.sequences);
          }
        }"""

html = html.replace(old_video_restore, new_video_restore)

# ============================================================
# 13. 在 new_functions 末尾添加 loadSequencesFromIntent
# ============================================================
html = html.replace(
    new_functions.strip() + '\n\n  </script>',
    new_functions.strip() + """

    function loadSequencesFromIntent(sequences) {
      sequences.forEach(seq => {
        const videos = seq.videos || [];
        const transitions = seq.transitions || [];
        for (let i = 0; i < videos.length - 1; i++) {
          const fromName = videos[i];
          const toName = videos[i + 1];
          const fromIdx = videoEntries.findIndex(e => e.name === fromName);
          const toIdx = videoEntries.findIndex(e => e.name === toName);
          if (fromIdx < 0 || toIdx < 0) continue;
          const sel = document.querySelector(`[data-seq-next="${fromIdx}"]`);
          if (sel) {
            sel.value = String(toIdx);
            onSeqNextChange(fromIdx);
            const t = transitions.find(tr => tr.after === fromName);
            if (t) {
              const tSel = document.querySelector(`[data-seq-trans="${fromIdx}"]`);
              const dEl = document.querySelector(`[data-seq-dur="${fromIdx}"]`);
              if (tSel) tSel.value = t.type || '';
              if (dEl && t.duration != null) dEl.value = t.duration;
            }
          }
        }
      });
    }
  </script>"""
)

# ============================================================
# 14. 写回文件
# ============================================================
with open(r'D:\2Study\StudyNotes\SKILLS\智剪工坊\intent.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Done. Checking syntax...')

# ============================================================
# 语法检查
# ============================================================
import subprocess
result = subprocess.run(['node', '-e', f"""
const fs = require('fs');
const html = fs.readFileSync('D:/2Study/StudyNotes/SKILLS/智剪工坊/intent.html', 'utf8');
const match = html.match(/<script>([\\s\\S]*?)<\\/script>/);
if (!match) {{ console.log('No script'); process.exit(1); }}
try {{ new Function(match[1]); console.log('OK'); }}
catch(e) {{ console.log('SYNTAX ERROR:', e.message); process.exit(1); }}
"""], capture_output=True, text=True)
print(result.stdout.strip())
if result.returncode != 0:
    print('STDERR:', result.stderr[:500])
