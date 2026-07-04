"""
intent.html v0.7 最终版：
1. 修 video-number 显示（移到卡片内部左上角）
2. 每个卡片可折叠（点击 ▶ 按钮）
3. 每个卡片内嵌「接下一个视频」+「转场特效」
4. 删除顶层「视频序列」section
5. sequences 从 next-video 链重建
"""
import re

with open(r'D:\2Study\StudyNotes\SKILLS\智剪工坊\intent.html', encoding='utf-8') as f:
    html = f.read()

# ============================================================
# 1. renderVideoCard: 折叠结构 + 折叠按钮 + 序列字段 + video-number 修复
# ============================================================
old_render = """    function renderVideoCard(entry, i) {
      const vw = entry.videoWidth || 1920;
      const vh = entry.videoHeight || 1080;
      const aspect = vw / vh;
      const maxW = 160, maxH = 90;
      let tw, th;
      if (aspect >= 1) { tw = Math.min(maxW, Math.round(maxH * aspect)); th = Math.round(tw / aspect); }
      else { th = Math.min(maxH, Math.round(maxW / aspect)); tw = Math.round(th * aspect); }
      return \`
        <div class="video-number">#\${entry.index}</div>
        <div class="video-head">
          <div class="video-thumb" data-play="\${i}" style="width:\${tw}px;height:\${th}px;" title="点击预览">
            \${entry.thumbDataUrl
              ? \`<img src="\${entry.thumbDataUrl}"><div class="play-hint">▶ 预览</div>\`
              : '<span>无缩略图</span>'}
          </div>
          <div class="video-meta">
            <div class="video-filename">\${escapeHtml(entry.name)}</div>
            <div class="video-auto">\${formatDuration(entry.durationSec)} · \${(entry.file.size / 1024 / 1024).toFixed(1)} MB · \${vw}×\${vh}</div>
            <div class="video-actions">
              <button class="exclude-btn" data-exclude-btn="\${i}" type="button">🚫 <span class="exclude-text">不用</span></button>
            </div>
          </div>
        </div>
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
          <div class="seq-row seq-transition-row" data-seq-trans-row="\${i}" style="display:none">
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
      \`;
    }"""
          </div>
        </div>
      \`;
    }"""

new_render = """    function renderVideoCard(entry, i) {
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
                \${renderOpBgm(i)}
                \${renderOpReplace(i)}
                \${renderOpOpeningText(i)}
                \${renderOpInsertImage(i)}
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
              <div class="seq-row seq-transition-row" data-seq-trans-row="\${i}" style="display:none">
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
    }"""

# 用精确字符串匹配（template 里变量名有转义，需要用不同策略）
# 改用 line-by-line 替换
old_lines = old_render.split('\n')
new_lines = new_render.split('\n')
# 找到在 html 中的位置并替换
# 先找 function renderVideoCard 的开始行
pattern = re.compile(r'    function renderVideoCard\(entry, i\) \{')
start_idx = None
for i, line in enumerate(html.split('\n')):
    if pattern.match(line):
        start_idx = i
        break
if start_idx is None:
    print("ERROR: renderVideoCard not found!")
else:
    html_lines = html.split('\n')
    # 找结束行：数大括号配对，从 start_idx 开始
    depth = 0
    end_idx = start_idx
    for i in range(start_idx, len(html_lines)):
        for ch in html_lines[i]:
            if ch == '{': depth += 1
            elif ch == '}': depth -= 1
        if depth == 0 and i > start_idx:
            end_idx = i
            break
    print(f"Found renderVideoCard at lines {start_idx+1}-{end_idx+1}")
    # 替换
    html_lines = html_lines[:start_idx] + new_lines + html_lines[end_idx+1:]
    html = '\n'.join(html_lines)

# ============================================================
# 2. renderForm 里构建卡片时：绑定折叠按钮 + 初始化序列
# ============================================================
old_form_card_loop = """        videoEntries.forEach((entry, i) => {
          const card = document.createElement('div');
          card.className = 'video-card';
          card.dataset.videoIndex = entry.index;
          card.innerHTML = renderVideoCard(entry, i);
          videoListEl.appendChild(card);
        });"""

new_form_card_loop = """        videoEntries.forEach((entry, i) => {
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
        // 初始化序列 UI（刷新下拉 + 绑定 change 事件）
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
        });"""

html = html.replace(old_form_card_loop, new_form_card_loop)

# ============================================================
# 3. 删除旧 renderForm 里的 sequences 相关调用（addSequence / refreshAllSequenceDropdowns）
# ============================================================
# 删除 sequences-section 的旧渲染调用
old_seq_load = """          // 从 existingIntent.sequences 加载已有序列（addSequence 内部处理 index/filename 两种格式）
          if (Array.isArray(existingIntent.sequences) && existingIntent.sequences.length) {
            existingIntent.sequences.forEach(s => {
              addSequence(s.name || '', s.videos || [], existingIntent.videos || [], s.transitions || []);
            });
          } else if (Array.isArray(existingIntent.chains) && existingIntent.chains.length) {
            // 旧 v0.3 格式
            const oldTransitions = Array.isArray(existingIntent.transitions) ? existingIntent.transitions : [];
            existingIntent.chains.forEach(c => {
              const videos = Array.isArray(c.videos) ? c.videos : (Array.isArray(c) ? c : []);
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

new_seq_load = """          // 从 existingIntent.sequences 加载 per-card next-video 字段
          if (Array.isArray(existingIntent.sequences) && existingIntent.sequences.length) {
            loadSequencesFromIntent(existingIntent.sequences);
          }"""

html = html.replace(old_seq_load, new_seq_load)

# ============================================================
# 4. 删除 sequences 顶层 section 的 HTML
# ============================================================
seq_section_pattern = re.compile(
    r'      <section>\s*\n\s*<h2>视频序列[^<]*</h2>.*?</section>',
    re.DOTALL
)
html = seq_section_pattern.sub('', html)

# ============================================================
# 5. 删除 sequences-list 绑定代码（add-sequence 按钮事件）
# ============================================================
html = html.replace(
    "document.getElementById('add-sequence').addEventListener('click', () => addSequence('', null, null, []));",
    ""
)

# ============================================================
# 6. 删除旧的 sequences 函数（addSequence / addSequenceRow 等）
# ============================================================
# 找到 "Sequences UI (v0.6 恢复版)" 开始并删除到文件末尾的 sequences 函数
seq_func_pattern = re.compile(
    r"    // ===== Sequences[^\n]*\n.*?(?=\n    // ===== |\n    // ==== |\n    function [a-z]+\(|\n  \</script)",
    re.DOTALL
)
# 简单点：找到 addSequence 函数开头并删除整个块
add_seq_start = html.find("    function addSequence(name, prefillVideos")
if add_seq_start == -1:
    print("addSequence not found (already removed)")
else:
    # 找这个函数的结束（数括号配对）
    depth = 0
    end = add_seq_start
    html_lines_list = html.split('\n')
    for i in range(len(html_lines_list)):
        line = html_lines_list[i]
        for ch in line:
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and i > 0:
                    end = sum(len(l)+1 for l in html_lines_list[:i+1])
                    break
        if depth == 0 and i > 0:
            break
    # 计算 end 行
    pos = 0
    end_line = 0
    for li, line in enumerate(html.split('\n')):
        pos += len(line) + 1
        if pos > end:
            end_line = li
            break
    end_line = end_line + 1
    print(f"Removing sequences functions from line ~{html[:add_seq_start].count(chr(10))+1} to end of functions block")
    # 删除从 addSequence 到下一个独立函数之间
    # 找 refreshAllSequenceDropdowns 之后（它是最后一个 sequences 函数）
    refresh_end = html.find("    function refreshAllSequenceDropdowns() {")
    if refresh_end == -1:
        print("refreshAllSequenceDropdowns not found")
    else:
        # 数它的括号
        depth = 0
        refresh_end_line = 0
        count = 0
        for ch in html[refresh_end:]:
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    refresh_end_pos = refresh_end + count + 1
                    break
            count += 1
        # 找这个行号
        line_num = 0
        for li, line in enumerate(html.split('\n')):
            if html.find("    function refreshAllSequenceDropdowns() {") < len('\n'.join(html.split('\n')[:li+1])):
                line_num = li
                break
        pos2 = 0
        for li, line in enumerate(html.split('\n')):
            pos2 += len(line) + 1
            if pos2 >= refresh_end_pos:
                refresh_end_line = li
                break
        # 删除从 addSequence 开始到 refreshAllSequenceDropdowns 结束
        start_line = html[:add_seq_start].count('\n')
        html_lines = html.split('\n')
        print(f"Removing lines {start_line+1}-{refresh_end_line+1} ({refresh_end_line-start_line+1} lines)")
        html_lines = html_lines[:start_line] + html_lines[refresh_end_line+1:]
        html = '\n'.join(html_lines)

# ============================================================
# 7. collectFormData: sequences 改为从 next-video 链重建
# ============================================================
old_collect_seq = """      // sequences：从 sequences-list 的 select.video-select 读取（v0.6 格式）
      sequencesListEl.querySelectorAll('.sequence').forEach(seqEl => {
        const name = seqEl.querySelector('.sequence-name').value.trim();
        const videos = [];
        const transitions = [];
        const rowEls = seqEl.querySelectorAll('.sequence-rows .sequence-row');
        rowEls.forEach((row, i) => {
          const v = row.querySelector('select.video-select').value;
          if (v) {
            // dropdown value = entry.index（1-based），找对应 entry 并存 entry.index（数字格式）
            const entry = videoEntries.find(e => String(e.index) === v);
            if (entry) videos.push(entry.index);  // 存数字而非文件名，兼容 DAY2 格式
            // 找紧接着的 transition 行
            const tRow = row.nextElementSibling;
            if (tRow && tRow.classList.contains('sequence-transition') && i < rowEls.length - 1) {
              const type = tRow.querySelector('.transition-type').value;
              const dur = parseFloat(tRow.querySelector('.transition-duration').value);
              const t = { after: entry ? entry.index : v };
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
      if (data.sequences.length === 0) delete data.sequences;"""

new_collect_seq = """      // sequences：从每个视频的"接视频"字段重建
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
      if (data.sequences.length === 0) delete data.sequences;"""

html = html.replace(old_collect_seq, new_collect_seq)

# ============================================================
# 8. 新增 sequences UI 函数（在 renderVideoCard 之后添加）
# ============================================================
seq_ui_funcs = """
    // ===== Sequences UI v0.7: 每个视频卡片内嵌 next-video =====
    function initSequencesUI() {
      // 刷新所有下拉选项（排除已被其他视频占用的）
      refreshAllSeqDropdowns();
      // 绑定每个下拉的 change 事件
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
      // 收集当前所有"接视频"的值（这些目标已被占用）
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
          if (j === i) return;  // 不能选自己
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

      // 显示/隐藏转场行
      if (transRow) transRow.style.display = val ? 'flex' : 'none';

      // 清除错误
      if (errEl) { errEl.textContent = ''; errEl.classList.remove('show'); }

      if (!val) {
        if (chainEl) chainEl.textContent = '';
        refreshAllSeqDropdowns();
        return;
      }

      // 循环检测：顺着 val 这条链走一遍
      const chain = buildSeqChain(i, val);
      if (chain.includes(i)) {
        if (errEl) { errEl.textContent = '⚠️ 形成循环，禁止！'; errEl.classList.add('show'); }
        sel.value = '';
        if (chainEl) chainEl.textContent = '';
        refreshAllSeqDropdowns();
        return;
      }

      // 显示链预览
      if (chainEl) {
        const chainNames = chain.map(idx => {
          const e = videoEntries[idx];
          return \`#\${e.index} \${e.name}\`;
        });
        chainEl.textContent = '▶ 链: ' + chainNames.join(' → ');
      }

      refreshAllSeqDropdowns();
    }

    function buildSeqChain(currentIdx, initialNextVal) {
      const visited = [];
      let cur = currentIdx;
      while (cur !== undefined) {
        if (visited.includes(cur)) break;
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

    function loadSequencesFromIntent(sequences) {
      // 从 sequences 数组构建 nextMap（intent.videos.index → intent.videos.index）
      // 然后设置每个视频卡片的 seq-next dropdown
      sequences.forEach(seq => {
        const videos = seq.videos || [];
        const transitions = seq.transitions || [];
        for (let i = 0; i < videos.length - 1; i++) {
          const fromIndex = videos[i];  // 这是 intent.videos 里的 index 字段
          const toIndex = videos[i + 1];
          // 找 videoEntries 里 entry.index === fromIndex 的 i
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
      // 刷新所有 dropdown
      videoEntries.forEach((_, i) => onSeqNextChange(i));
    }
"""

# 在 renderVideoCard 函数之后插入
insert_after = "    function renderVideoCard(entry, i) {"
insert_pos = html.find(insert_after)
if insert_pos == -1:
    print("ERROR: renderVideoCard not found for insertion")
else:
    # 找到这个函数的结束（数括号）
    depth = 0
    end_pos = insert_pos
    for ci, ch in enumerate(html[insert_pos:]):
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end_pos = insert_pos + ci + 1
                break
    html = html[:end_pos] + "\n" + seq_ui_funcs + "\n" + html[end_pos:]

# ============================================================
# 9. toggleCard 函数
# ============================================================
toggle_card_func = """
    function toggleCard(i) {
      const card = videoListEl.querySelector(\`.video-card[data-card-idx="\${i}"]\`);
      if (!card) return;
      const collapsed = card.classList.toggle('collapsed');
      const btn = card.querySelector('.card-toggle');
      if (btn) btn.classList.toggle('expanded', !collapsed);
    }
"""

# 找到 initSequencesUI 函数，在它之前插入 toggleCard
toggle_insert = "    function initSequencesUI() {"
toggle_pos = html.find(toggle_insert)
if toggle_pos > 0:
    # 找前一个换行
    prev_newline = html.rfind('\n', 0, toggle_pos)
    html = html[:prev_newline+1] + toggle_card_func + "\n" + html[prev_newline+1:]
else:
    print("WARNING: initSequencesUI not found for toggleCard insertion")

# ============================================================
# 10. version 改为 0.7
# ============================================================
html = html.replace('"tool": \'智剪工坊\', version: \'0.6\'', '"tool": \'智剪工坊\', version: \'0.7\'')

# ============================================================
# 写回
# ============================================================
with open(r'D:\2Study\StudyNotes\SKILLS\智剪工坊\intent.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Done.')
