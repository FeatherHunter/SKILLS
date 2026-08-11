/* Base Skill 控件库 v1.2（唯一真相源 · 跨技能 · 领域无关）
 * 契约: docs/component-contract.md v1.2
 * v1.2 核心（#269 试点用户拍板）:
 *  - snapshot 结构化接口: buildDataText/buildLogText 领域无关（title/summary/sections）
 *  - toast 通用提示控件: 4 形态（徽章/操作/计数/留空）+ 队列 + 图标库 + 多操作 + 富详情 + 无障碍
 *  - 复制按钮控件化: 复制数据/日志 = Base 控件;预览/格式选择/脱敏/导出
 *  - 新控件 P0+P1: formPrompt/selectList/confirm/foldBox/statusBadge/emptyState/errorReceipt
 *  - 结构校验违规直接报错（硬拦截）
 * 注入点: SHARED-HELPERS 占位符（由 injector.py 替换本文件）
 * 修改必须走公共层 ISSUE（总纲 09）+ CHANGELOG（见 docs/component-contract.md §8）
 */

/* ── P0 守卫组 ── */
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function arr(v){return Array.isArray(v)?v:[];}
function val(v){return v===null||v===undefined||v===''?'<span style="color:var(--fg3)">未填写</span>':esc(v);}
function yes(v){return v?'<span class="ok">通过</span>':'<span class="bad">未通过</span>';}
function validate(p){if(!p||typeof p!=='object')return{ok:false,msg:'数据未注入'};if(p.status!=='ok')return{ok:false,msg:p.message||'数据状态非 ok'};if(!p.data||typeof p.data!=='object')return{ok:false,msg:'data 缺失'};return{ok:true};}
function _fbCopy(s){var ok=false;try{var t=document.createElement('textarea');t.value=s;t.style.cssText='position:fixed;left:-9999px;top:0;opacity:0';document.body.appendChild(t);t.focus();t.select();ok=document.execCommand('copy');document.body.removeChild(t);}catch(e){ok=false;}return ok;}

/* ── 复制动作 v2（不改按钮文字 + toast 反馈）── */
function copyText(s, opts){
  opts = opts || {};
  if(!s) return;
  function ok(){ if(!opts.silent) toast('已复制','粘贴给 AI'); }
  function fail(){ if(!opts.silent) toast('复制失败','长按选择文本手动复制',{badge:{text:'失败',type:'danger'}}); }
  if(navigator.clipboard&&navigator.clipboard.writeText){
    try{
      var pr=navigator.clipboard.writeText(s);
      if(pr&&pr.then){pr.then(function(){ok();}).catch(function(){_fbCopy(s)?ok():fail();});}
      else{ok();}
    }catch(e){_fbCopy(s)?ok():fail();}
  }else{_fbCopy(s)?ok():fail();}
}

/* ── toast 通用提示控件 v1.2 ──
 * toast(msg, detail?, options?)
 * options: { icon, badge:{text,type}, actions:[{label,onClick}], count, lines:[], code, timeout }
 * 向后兼容: toast(msg, detail) = 等价 v1.1
 * 队列管理: 连续触发排队显示, 不叠加
 */
(function(){
  var queue = [];
  var showing = false;
  var styleInjected = false;
  var ICONS = { copy:'📋', ok:'✅', warn:'⚠️', danger:'❌', info:'💡' };
  var CSS = '.hm-toast{position:fixed;left:50%;bottom:calc(24px + env(safe-area-inset-bottom,0));transform:translateX(-50%) scale(.9);opacity:0;background:rgba(28,28,30,.94);-webkit-backdrop-filter:blur(20px) saturate(180%);backdrop-filter:blur(20px) saturate(180%);color:#f0f0f0;border-radius:14px;padding:13px 14px 13px 16px;display:flex;align-items:flex-start;gap:12px;max-width:480px;min-width:300px;box-shadow:0 10px 32px rgba(0,0,0,.32),0 0 0 .5px rgba(255,255,255,.08) inset;pointer-events:none;transition:opacity .22s ease-out,transform .22s cubic-bezier(.34,1.56,.64,1);z-index:9999}.hm-toast.show{opacity:1;transform:translateX(-50%) scale(1);pointer-events:auto}.hm-toast-icon{font-size:20px;line-height:1;padding-top:1px;flex-shrink:0}.hm-toast-body{flex:1;min-width:0}.hm-toast-title-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.hm-toast-title{font-weight:600;font-size:12.5px;line-height:1.4;color:#fff;margin-bottom:2px}.hm-toast-detail{font-size:11px;line-height:1.5;color:#c8c8cc}.hm-toast-lines{font-size:11px;line-height:1.55;color:#c8c8cc}.hm-toast-code{background:rgba(0,0,0,.32);border-radius:8px;padding:8px 10px;font-size:10.5px;line-height:1.5;color:#aeb0b8;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;margin-top:6px;max-height:140px;overflow:auto}.hm-toast-chip{font-size:10px;font-weight:700;padding:2px 8px;border-radius:999px;letter-spacing:.02em;flex-shrink:0}.hm-toast-chip.ok{background:rgba(52,199,89,.18);color:#4dd96b}.hm-toast-chip.warn{background:rgba(255,149,0,.18);color:#ffb340}.hm-toast-chip.danger{background:rgba(255,59,48,.18);color:#ff6961}.hm-toast-chip.gray{background:rgba(255,255,255,.12);color:#c8c8cc}.hm-toast-count{font-size:10px;font-weight:700;color:#c8c8cc;background:rgba(255,255,255,.08);padding:2px 8px;border-radius:6px;font-variant-numeric:tabular-nums;flex-shrink:0}.hm-toast-act{font-size:11px;font-weight:600;color:#4dd96b;border:none;background:none;cursor:pointer;padding:2px 4px;flex-shrink:0;font-family:inherit}.hm-toast-act:active{opacity:.7}.hm-toast-close{background:rgba(255,255,255,.10);color:#34c759;border:0;border-radius:8px;padding:5px 9px;font-size:10.5px;font-weight:500;font-family:inherit;cursor:pointer;white-space:nowrap;margin-left:6px;flex-shrink:0}.hm-toast-close:active{background:rgba(255,255,255,.2)}@media(max-width:820px){.hm-toast{left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom,0));transform:translateX(0) scale(.95);max-width:none;min-width:0}.hm-toast.show{transform:translateX(0) scale(1)}}';

  function ensureStyle(){
    if(styleInjected) return;
    styleInjected = true;
    var st = document.createElement('style');
    st.id = 'hm-toast-style';
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function dismiss(t, timer){
    clearTimeout(timer);
    t.classList.remove('show');
    setTimeout(function(){
      if(!t.isConnected) return;  // 已被 flush/外部移除 → 不重置状态（防旧定时器误触发）
      t.remove();
      showing = false;
      if(queue.length) showNext();
    }, 250);
  }

  function showNext(){
    if(showing || !queue.length) return;
    showing = true;
    var item = queue.shift();
    ensureStyle();
    var msg = item.msg, detail = item.detail, opts = item.opts;
    var t = document.createElement('div');
    t.className = 'hm-toast';
    t.setAttribute('role','status');
    t.setAttribute('aria-live','polite');
    var icon = ICONS[opts.icon] || opts.icon || '📋';
    var titleRow = '<span class="hm-toast-title">'+esc(msg)+'</span>';
    if(opts.badge){
      var b = opts.badge;
      var btype = ['ok','warn','danger'].indexOf(b.type)>=0 ? b.type : 'ok';
      titleRow += '<span class="hm-toast-chip '+btype+'">'+esc(b.text)+'</span>';
    }
    if(opts.count){
      titleRow += '<span class="hm-toast-count">'+esc(opts.count)+'</span>';
    }
    if(opts.actions && opts.actions.length){
      opts.actions.slice(0,2).forEach(function(a){
        titleRow += '<button class="hm-toast-act" data-act="'+esc(a.label)+'">'+esc(a.label)+'</button>';
      });
    }
    var bodyHtml = '<div class="hm-toast-title-row">'+titleRow+'</div>';
    if(detail){
      bodyHtml += '<div class="hm-toast-detail">'+esc(detail)+'</div>';
    }
    if(opts.lines && opts.lines.length){
      bodyHtml += '<div class="hm-toast-lines">'+opts.lines.map(function(l){return esc(l);}).join('<br>')+'</div>';
    }
    if(opts.code){
      bodyHtml += '<div class="hm-toast-code">'+esc(opts.code)+'</div>';
    }
    t.innerHTML = '<div class="hm-toast-icon">'+icon+'</div><div class="hm-toast-body">'+bodyHtml+'</div><button class="hm-toast-close">✓ 知道了</button>';
    document.body.appendChild(t);
    if(opts.actions && opts.actions.length){
      var actBtns = t.querySelectorAll('.hm-toast-act');
      opts.actions.slice(0,2).forEach(function(a, i){
        actBtns[i].addEventListener('click', function(){
          var f = a.onClick;
          dismiss(t, timer);
          if(f) setTimeout(f, 0);
        });
      });
    }
    t.querySelector('.hm-toast-close').addEventListener('click', function(){ dismiss(t, timer); });
    var timer = setTimeout(function(){ dismiss(t, timer); }, opts.timeout || 4500);
    requestAnimationFrame(function(){ t.classList.add('show'); });
  }

  window.toast = function(msg, detail, options){
    options = options || {};
    queue.push({ msg: msg, detail: detail || '', opts: options });
    showNext();
  };
  /* 队列清空（技能页面销毁/测试用）：清空排队 + 移除当前显示 */
  window.__hmToastFlush = function(){
    queue.length = 0;
    document.querySelectorAll('.hm-toast').forEach(function(t){ t.remove(); });
    showing = false;
  };
})();

/* ── snapshot 结构校验（违规直接报错）── */
function _validateSnapshot(s){
  if(!s || typeof s !== 'object'){
    throw new Error('snapshot 违规: scene.snapshot 必须是对象');
  }
  if(typeof s.title !== 'string' || !s.title.trim()){
    throw new Error('snapshot 违规: title 必须是非空字符串');
  }
  if(!Array.isArray(s.summary)){
    throw new Error('snapshot 违规: summary 必须是数组');
  }
  if(!Array.isArray(s.sections)){
    throw new Error('snapshot 违规: sections 必须是数组');
  }
  s.sections.forEach(function(sec, i){
    if(!sec || typeof sec !== 'object' || typeof sec.heading !== 'string' || !Array.isArray(sec.rows)){
      throw new Error('snapshot 违规: sections['+i+'] 必须含 heading(字符串) + rows(数组)');
    }
  });
  return true;
}

/* 行渲染: 支持字符串 或 {text, sensitive}（脱敏）*/
function _rowText(r){
  if(r && typeof r === 'object' && !Array.isArray(r)){
    if(r.sensitive) return '****（敏感字段已脱敏）';
    return String(r.text ?? '');
  }
  return String(r ?? '');
}

/* ── buildDataText v1.2（snapshot 结构化 · 领域无关 · format 支持）──
 * buildDataText(p, format?)  format: 'text'(默认) | 'json' | 'csv'
 */
function buildDataText(p, format){
  var d = p && p.data || {};
  var me = d.meta || {};
  var s = d.scene || {};
  var snap = s.snapshot;
  _validateSnapshot(snap);
  format = format || 'text';

  if(format === 'json'){
    return JSON.stringify(snap, null, 2);
  }
  if(format === 'csv'){
    var out = [];
    out.push(snap.title);
    out.push(snap.summary.map(_rowText).join('; '));
    snap.sections.forEach(function(sec){
      out.push('[' + sec.heading + ']');
      sec.rows.forEach(function(r){ out.push(_rowText(r)); });
    });
    return out.join('\n');
  }

  var L = ['【'+(me.skill_name||me.command_cn||'')+' · '+(me.command_cn||'')+'】'];
  L.push('场景: '+(me.command_cn||'')+(s.scene_id?('('+s.scene_id+')'):'')+(me.wake_word?(' · 唤醒词「'+me.wake_word+'」'):''));
  L.push('时间: '+(me.occurred_at||''));
  if(snap.summary.length){
    snap.summary.forEach(function(x){ L.push(_rowText(x)); });
  }
  snap.sections.forEach(function(sec){
    if(!sec.rows.length) return;
    L.push('▍'+sec.heading);
    sec.rows.forEach(function(r){ L.push('  · '+_rowText(r)); });
  });
  return L.join('\n');
}

/* ── buildLogText v1.2（6 段日志 · format 支持）── */
function buildLogText(p, format){
  var d = p && p.data || {};
  var me = d.meta || {};
  var s = d.scene || {};
  var cl = d.copy_log || s.copy_log || {};
  format = format || 'text';

  var L = ['① 场景标识'];
  L.push('  命  令: '+(me.command_cn||''));
  L.push('  唤醒词: '+(me.wake_word||'(未知)'));
  L.push('  场景名: '+(me.command_cn||'')+(s.scene_id?('('+s.scene_id+')'):''));
  L.push('');
  L.push('② AI 思考链');
  L.push('  '+(cl.thinking||'(本地渲染 · 无 AI 链)'));
  L.push('');
  L.push('③ 底层数据结构');
  L.push('  '+(cl.data_structure||'(只读查询)'));
  L.push('');
  L.push('④ 调用链');
  L.push('  '+(cl.call_chain||'(未知)'));
  L.push('');
  L.push('⑤ 时间戳 + 版本');
  L.push('  本地时间: '+(cl.timestamp||me.occurred_at||'(未知)'));
  L.push('  版  本: '+(me.skill_version||'(未知)'));
  L.push('');
  L.push('⑥ 异常信息');
  L.push('  '+(cl.exception||'无'));
  return L.join('\n');
}

/* ── metaHeader / remindersBlock（v1.1 保留）── */
function metaHeader(p, m){var me=p.data.meta||{};var stage=m&&m.stage?('<span class="stage">'+esc(m.stage)+'</span>'):'';return '<header class="hero"><div class="eyebrow" style="color:#8e8e93;font-size:11px;font-weight:600">'+esc(me.command_cn||'')+' · '+esc(me.occurred_at||'')+'</div><h1>'+esc(m&&m.title||me.command_cn||'')+'</h1>'+(m&&m.lead?'<p class="lead">'+esc(m.lead)+'</p>':'')+stage+'</header>';}
function remindersBlock(p){var rs=arr(p.data.reminders);if(!rs.length)return '';return '<section class="remind"><h2>顺路提醒</h2>'+rs.map(r=>'<div class="remind-item '+(r.type==='warn'?'warn':r.type==='danger'?'bad':'')+'">'+esc(r.text)+'</div>').join('')+'</section>';}

/* ── actionBar v1.2（场景按钮 + 复制数据/日志 ghost）──
 * actionBar(p, extra?, opts?)  opts: { preview, formatMenu, download }
 */
function actionBar(p, extra, opts){
  window.__hmPayload = p;
  opts = opts || {};
  var btns = arr(extra || []);
  var sb = opts.noSb ? [] : arr(p && p.data && p.data.scene && p.data.scene.buttons || []);
  var html = '<div class="actions">';
  btns.concat(sb).forEach(function(b){
    html += '<button class="copy '+(b.kind||'')+'" onclick="copyText(this.dataset.t)" data-t="'+esc(b.text).replace(/"/g,'&quot;')+'">'+esc(b.label)+'</button>';
  });
  html += '<button class="copy ghost" onclick="'+(opts.preview?'window.__hmCopyData(true)':'copyText(buildDataText(window.__hmPayload))')+'">复制数据</button>';
  html += '<button class="copy ghost" onclick="'+(opts.preview?'window.__hmCopyLog(true)':'copyText(buildLogText(window.__hmPayload))')+'">复制日志</button>';
  html += '</div>';
  if(opts.preview){
    html += '<div class="hm-preview-overlay" id="hm-preview" style="display:none">'
      + '<div class="hm-preview-panel"><div class="hm-preview-head"><span id="hm-preview-title">复制预览</span>'
      + '<button class="hm-preview-close" onclick="document.getElementById(\'hm-preview\').style.display=\'none\'">✕</button></div>'
      + '<pre class="hm-preview-body" id="hm-preview-body"></pre>'
      + '<div class="hm-preview-actions"><button class="copy primary" id="hm-preview-confirm">复制</button>'
      + '<button class="copy" onclick="document.getElementById(\'hm-preview\').style.display=\'none\'">取消</button></div>'
      + '</div></div>';
  }
  return html;
}

/* 复制预览面板（actionBar preview 模式） */
function _showCopyPreview(kind){
  var p = window.__hmPayload;
  var body = document.getElementById('hm-preview-body');
  var title = document.getElementById('hm-preview-title');
  if(!body) return;
  var text = kind === 'log' ? buildLogText(p) : buildDataText(p);
  title.textContent = kind === 'log' ? '复制日志 · 预览' : '复制数据 · 预览';
  body.textContent = text;
  document.getElementById('hm-preview').style.display = 'flex';
  document.getElementById('hm-preview-confirm').onclick = function(){
    copyText(text);
    document.getElementById('hm-preview').style.display = 'none';
  };
}
window.__hmCopyData = function(){ _showCopyPreview('data'); };
window.__hmCopyLog = function(){ _showCopyPreview('log'); };

/* ── formPrompt（P0 · 用户填参数表单 + 实时预览 + 空值拦截）──
 * formPrompt(fields, template) → HTML 字符串
 * fields: [{ key, label, type:'text'|'number'|'select', options?, default?, placeholder? }]
 * template: 含 {key} 占位符的 prompt 模板
 */
function formPrompt(fields, template){
  fields = arr(fields);
  var uid = 'fp' + Math.random().toString(36).slice(2,7);
  var html = '<div class="fp" id="'+uid+'">';
  fields.forEach(function(f, i){
    var fid = uid + '-f' + i;
    html += '<div class="fp-field"><label class="fp-label">'+esc(f.label)+'</label>';
    if(f.type === 'select'){
      html += '<select class="fp-input" id="'+fid+'" data-key="'+esc(f.key)+'">';
      arr(f.options).forEach(function(o){
        var sel = (String(o.value ?? o) === String(f.default ?? '')) ? ' selected' : '';
        html += '<option value="'+esc(o.value ?? o)+'"'+sel+'>'+esc(o.label ?? o)+'</option>';
      });
      html += '</select>';
    } else {
      html += '<input class="fp-input" id="'+fid+'" type="'+(f.type==='number'?'number':'text')+'" data-key="'+esc(f.key)+'" value="'+esc(f.default ?? '')+'" placeholder="'+esc(f.placeholder ?? '')+'">';
    }
    html += '</div>';
  });
  html += '<div class="fp-preview"><div class="fp-preview-label">Prompt 预览</div><pre class="fp-preview-body" id="'+uid+'-preview"></pre></div>';
  html += '<div class="fp-actions"><button class="copy primary" id="'+uid+'-btn">复制 prompt</button></div>';
  html += '</div>';

  function renderPreview(){
    var vals = {};
    fields.forEach(function(f, i){
      var el = document.getElementById(uid + '-f' + i);
      vals[f.key] = el ? el.value : '';
    });
    var text = String(template || '').replace(/\{(\w+)\}/g, function(_, k){ return vals[k] ?? ''; });
    document.getElementById(uid + '-preview').textContent = text;
    var btn = document.getElementById(uid + '-btn');
    var emptyRequired = fields.some(function(f){ return f.required && !vals[f.key]; });
    if(emptyRequired){
      btn.disabled = true;
      btn.textContent = '请填写必填项';
    } else {
      btn.disabled = false;
      btn.textContent = '复制 prompt';
    }
  }

  setTimeout(function(){
    fields.forEach(function(f, i){
      var el = document.getElementById(uid + '-f' + i);
      if(el){
        el.addEventListener('input', renderPreview);
        el.addEventListener('change', renderPreview);
      }
    });
    document.getElementById(uid + '-btn').addEventListener('click', function(){
      if(this.disabled) { toast('请先填写','必填字段未填写',{badge:{text:'提示',type:'warn'}}); return; }
      var text = document.getElementById(uid + '-preview').textContent;
      copyText(text);
    });
    renderPreview();
  }, 0);

  return html;
}

/* ── selectList（P0 · 勾选列表 + 批量操作 + 计数联动）──
 * selectList(items, batchActions?, opts?)
 * items: [{ id, title, sub?, group? }]
 * batchActions: [{ label, kind:'ok'|'danger', onClick(ids) }]
 */
function selectList(items, batchActions, opts){
  items = arr(items);
  batchActions = arr(batchActions);
  opts = opts || {};
  var uid = 'sl' + Math.random().toString(36).slice(2,7);
  var groups = {};
  items.forEach(function(it){
    var g = it.group || '';
    (groups[g] = groups[g] || []).push(it);
  });
  var groupNames = Object.keys(groups);
  var html = '<div class="sl" id="'+uid+'">';
  if(batchActions.length){
    html += '<div class="sl-batchbar" id="'+uid+'-batch">';
    batchActions.forEach(function(a){
      html += '<button class="copy '+(a.kind==='danger'?'red':'primary')+'" data-batch="'+esc(a.label)+'">'+esc(a.label)+'</button>';
    });
    html += '<span class="sl-count" id="'+uid+'-count">已选 0/'+items.length+'</span>';
    html += '</div>';
  }
  groupNames.forEach(function(g){
    var gItems = groups[g];
    html += '<div class="sl-group"><div class="sl-group-head">'+esc(g||'全部');
    html += ' <span class="sl-group-count">本组已选 0/'+gItems.length+'</span></div>';
    html += '<div class="sl-group-items">';
    gItems.forEach(function(it, idx){
      html += '<label class="sl-item"><input type="checkbox" data-id="'+esc(it.id)+'" data-g="'+esc(g)+'">'
        + '<span class="sl-item-body"><span class="sl-item-title">'+esc(it.title)+'</span>'
        + (it.sub?'<span class="sl-item-sub">'+esc(it.sub)+'</span>':'')
        + '</span></label>';
    });
    html += '</div></div>';
  });
  html += '</div>';

  setTimeout(function(){
    var root = document.getElementById(uid);
    var checkboxes = root.querySelectorAll('input[type="checkbox"]');
    var globalCount = document.getElementById(uid + '-count');
    function update(){
      var total = checkboxes.length;
      var checked = root.querySelectorAll('input[type="checkbox"]:checked').length;
      if(globalCount) globalCount.textContent = '已选 '+checked+'/'+total;
      root.querySelectorAll('.sl-group').forEach(function(gEl){
        var boxes = gEl.querySelectorAll('input[type="checkbox"]');
        var c = gEl.querySelectorAll('input[type="checkbox"]:checked').length;
        var lbl = gEl.querySelector('.sl-group-count');
        if(lbl) lbl.textContent = '本组已选 '+c+'/'+boxes.length;
      });
      return checked;
    }
    checkboxes.forEach(function(cb){
      cb.addEventListener('change', update);
    });
    root.querySelectorAll('[data-batch]').forEach(function(btn){
      btn.addEventListener('click', function(){
        var ids = root.querySelectorAll('input[type="checkbox"]:checked');
        if(!ids.length){ toast('请先勾选','勾选要处理的条目',{badge:{text:'提示',type:'warn'}}); return; }
        var idList = Array.prototype.map.call(ids, function(x){ return x.getAttribute('data-id'); });
        var a = batchActions.filter(function(x){ return x.label === btn.getAttribute('data-batch'); })[0];
        if(a && a.onClick) a.onClick(idList);
      });
    });
    update();
  }, 0);

  return html;
}

/* ── confirm（P0 · 危险操作二次确认）──
 * confirm({ title, detail?, danger?, onOk })
 */
function confirm(cfg){
  cfg = cfg || {};
  var overlay = document.createElement('div');
  overlay.className = 'hm-confirm-overlay';
  overlay.innerHTML = '<div class="hm-confirm-panel">'
    + '<div class="hm-confirm-title">'+(cfg.danger?'⚠️ ':'')+esc(cfg.title||'确认操作')+'</div>'
    + (cfg.detail?'<div class="hm-confirm-detail">'+esc(cfg.detail)+'</div>':'')
    + '<div class="hm-confirm-actions">'
    + '<button class="copy '+(cfg.danger?'red':'primary')+'" data-c="1">'+(cfg.danger?'确认删除':'确认')+'</button>'
    + '<button class="copy" data-c="0">取消</button>'
    + '</div></div>';
  document.body.appendChild(overlay);
  overlay.querySelector('[data-c="1"]').addEventListener('click', function(){
    overlay.remove();
    if(cfg.onOk) cfg.onOk();
  });
  overlay.querySelector('[data-c="0"]').addEventListener('click', function(){ overlay.remove(); });
  overlay.addEventListener('click', function(e){
    if(e.target === overlay) overlay.remove();
  });
}

/* ── foldBox（P1 · 折叠区）── */
function foldBox(title, contentHtml){
  return '<details class="hm-fold"><summary>'+esc(title)+'</summary><div class="hm-fold-body">'+(contentHtml||'')+'</div></details>';
}

/* ── statusBadge（P1 · 状态徽章）── */
function statusBadge(status, text){
  status = status || 'empty';
  var txt = text || ({ ok:'成功', warn:'警告', danger:'失败', empty:'无数据' }[status] || '');
  return '<span class="hm-status '+esc(status)+'">'+esc(txt)+'</span>';
}

/* ── emptyState（P1 · 空状态）── */
function emptyState(cfg){
  cfg = cfg || {};
  return '<div class="hm-empty">'
    + (cfg.icon?'<div class="hm-empty-icon">'+esc(cfg.icon)+'</div>':'')
    + '<div class="hm-empty-text">'+esc(cfg.text||'暂无数据')+'</div>'
    + (cfg.hint?'<div class="hm-empty-hint">'+esc(cfg.hint)+'</div>':'')
    + (cfg.action?('<div class="hm-empty-action">'+cfg.action+'</div>'):'')
    + '</div>';
}

/* ── errorReceipt（P1 · 错误回执）── */
function errorReceipt(cfg){
  cfg = cfg || {};
  var html = '<div class="hm-error">'
    + '<div class="hm-error-title">❌ '+esc(cfg.message||'操作失败')+'</div>'
    + (cfg.retryPrompt?('<button class="copy primary" onclick="copyText(this.dataset.t)" data-t="'+esc(cfg.retryPrompt).replace(/"/g,'&quot;')+'">修正重试</button>'):'')
    + '<button class="copy ghost" onclick="copyText('+(cfg.data?('buildDataText(window.__hmPayload)'):'this.dataset.t')+')" '+(cfg.data?'':'data-t="'+esc(cfg.data||'')+'"')+'>复制数据</button>'
    + '<button class="copy ghost" onclick="copyText(buildLogText(window.__hmPayload))">复制日志</button>'
    + '</div>';
  return html;
}
