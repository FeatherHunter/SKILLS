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

/* ── 复制动作 v2（不改按钮文字 + toast 反馈 · v1.10 #328 文案钩子）──
 * copyText(s, opts?)
 * opts: { silent, toast:{ok:{msg,detail,icon?}, fail:{msg,detail,icon?}}, onOk, onFail }
 *  - toast 文案配置: 只覆盖提供的字段, 缺省回落默认文案（08 规范: 文案由技能按场景自设计）
 *  - onOk/onFail 回调: 成功/最终失败必触发; silent 时不弹 toast 仍触发回调
 *  - 未传新选项: 行为与 v1.9 逐字一致（向后兼容）
 */
function copyText(s, opts){
  opts = opts || {};
  if(!s) return;
  var t = opts.toast || {}, okCfg = t.ok || {}, failCfg = t.fail || {};
  var okMsg = okCfg.msg !== undefined ? okCfg.msg : '已复制';
  var okDetail = okCfg.detail !== undefined ? okCfg.detail : '粘贴给 AI';
  var failMsg = failCfg.msg !== undefined ? failCfg.msg : '复制失败';
  var failDetail = failCfg.detail !== undefined ? failCfg.detail : '长按选择文本手动复制';
  function ok(){
    if(opts.onOk) opts.onOk();
    if(!opts.silent){
      var o = {};
      if(okCfg.icon) o.icon = okCfg.icon;
      toast(okMsg, okDetail, Object.keys(o).length ? o : undefined);
    }
  }
  function fail(){
    if(opts.onFail) opts.onFail();
    if(!opts.silent){
      var o = {badge:{text:'失败',type:'danger'}};
      if(failCfg.icon) o.icon = failCfg.icon;
      toast(failMsg, failDetail, o);
    }
  }
  if(navigator.clipboard&&navigator.clipboard.writeText){
    try{
      var pr=navigator.clipboard.writeText(s);
      if(pr&&pr.then){pr.then(function(){ok();}).catch(function(){_fbCopy(s)?ok():fail();});}
      else{ok();}
    }catch(e){_fbCopy(s)?ok():fail();}
  }else{_fbCopy(s)?ok():fail();}
}

/* ── toast 通用提示控件 v1.8（堆叠模式 · #304）──
 * toast(msg, detail?, options?)
 * options: { icon, badge:{text,type}, actions:[{label,onClick}], count, lines:[], code, timeout, maxStack }
 * 向后兼容: toast(msg, detail) = 等价 v1.1
 * 堆叠模式（v1.8 · #304 用户拍板）: 同屏最多 N 条同时可见（N 默认 5, opts.maxStack 可配,
 *   栈容量取栈内各 toast maxStack 最大值; ≤820px 视口自动收窄为 3）; 老上旧下（新 toast
 *   贴屏幕底部出现, 旧的向上顶, 间距 8px）; 超 N 挤掉最旧（FIFO）; 单条独立计时消失
 */
(function(){
  var stack = null;
  var styleInjected = false;
  var DEFAULT_MAX = 5;
  var MOBILE_MAX = 3;
  var ICONS = { copy:'📋', ok:'✅', warn:'⚠️', danger:'❌', info:'💡' };
  var CSS = '.hm-toast-stack{position:fixed;left:50%;bottom:calc(24px + env(safe-area-inset-bottom,0));transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:8px;z-index:9999;pointer-events:none}.hm-toast{position:relative;transform:scale(.9);opacity:0;background:rgba(28,28,30,.94);-webkit-backdrop-filter:blur(20px) saturate(180%);backdrop-filter:blur(20px) saturate(180%);color:#f0f0f0;border-radius:14px;padding:13px 14px 13px 16px;display:flex;align-items:flex-start;gap:12px;max-width:480px;min-width:300px;box-shadow:0 10px 32px rgba(0,0,0,.32),0 0 0 .5px rgba(255,255,255,.08) inset;pointer-events:none;transition:opacity .22s ease-out,transform .22s cubic-bezier(.34,1.56,.64,1)}.hm-toast.show{opacity:1;transform:scale(1);pointer-events:auto}.hm-toast-icon{font-size:20px;line-height:1;padding-top:1px;flex-shrink:0}.hm-toast-body{flex:1;min-width:0}.hm-toast-title-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.hm-toast-title{font-weight:600;font-size:12.5px;line-height:1.4;color:#fff;margin-bottom:2px}.hm-toast-detail{font-size:11px;line-height:1.5;color:#c8c8cc}.hm-toast-lines{font-size:11px;line-height:1.55;color:#c8c8cc}.hm-toast-code{background:rgba(0,0,0,.32);border-radius:8px;padding:8px 10px;font-size:10.5px;line-height:1.5;color:#aeb0b8;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;white-space:pre-wrap;margin-top:6px;max-height:140px;overflow:auto}.hm-toast-chip{font-size:10px;font-weight:700;padding:2px 8px;border-radius:999px;letter-spacing:.02em;flex-shrink:0}.hm-toast-chip.ok{background:rgba(52,199,89,.18);color:#4dd96b}.hm-toast-chip.warn{background:rgba(255,149,0,.18);color:#ffb340}.hm-toast-chip.danger{background:rgba(255,59,48,.18);color:#ff6961}.hm-toast-chip.gray{background:rgba(255,255,255,.12);color:#c8c8cc}.hm-toast-count{font-size:10px;font-weight:700;color:#c8c8cc;background:rgba(255,255,255,.08);padding:2px 8px;border-radius:6px;font-variant-numeric:tabular-nums;flex-shrink:0}.hm-toast-act{font-size:11px;font-weight:600;color:#4dd96b;border:none;background:none;cursor:pointer;padding:2px 4px;flex-shrink:0;font-family:inherit}.hm-toast-act:active{opacity:.7}.hm-toast-close{background:rgba(255,255,255,.10);color:#34c759;border:0;border-radius:8px;padding:5px 9px;font-size:10.5px;font-weight:500;font-family:inherit;cursor:pointer;white-space:nowrap;margin-left:6px;flex-shrink:0}.hm-toast-close:active{background:rgba(255,255,255,.2)}@media(max-width:820px){.hm-toast-stack{left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom,0));transform:none;align-items:stretch}.hm-toast{transform:scale(.95);max-width:none;min-width:0}.hm-toast.show{transform:scale(1)}}';

  function ensureStyle(){
    if(styleInjected) return;
    styleInjected = true;
    var st = document.createElement('style');
    st.id = 'hm-toast-style';
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function getStack(){
    if(!stack){
      stack = document.createElement('div');
      stack.id = 'hm-toast-stack';
      document.body.appendChild(stack);
    }
    return stack;
  }

  function isMobile(){
    return window.matchMedia('(max-width: 820px)').matches;
  }

  /* 栈容量 = 栈内各 toast maxStack 的最大值（空栈默认 5）; 移动端 ≤820px 收窄为 3 */
  function stackCap(){
    var cap = 0;
    if(stack) stack.querySelectorAll('.hm-toast').forEach(function(t){
      var m = parseInt(t.getAttribute('data-max')||DEFAULT_MAX, 10);
      if(m > cap) cap = m;
    });
    if(cap === 0) cap = DEFAULT_MAX;
    if(isMobile() && cap > MOBILE_MAX) cap = MOBILE_MAX;
    return cap;
  }

  /* 超 N 挤掉最旧（FIFO） */
  function evictOldest(){
    var cap = stackCap();
    while(stack.querySelectorAll('.hm-toast').length > cap){
      var oldest = stack.querySelector('.hm-toast');
      if(!oldest) break;
      clearTimeout(oldest._timer);
      oldest.remove();
    }
  }

  function dismiss(t){
    if(!t || !t.isConnected) return;
    clearTimeout(t._timer);
    t.classList.remove('show');
    setTimeout(function(){
      if(t.isConnected) t.remove();
    }, 250);
  }

  function show(item){
    var opts = item.opts;
    var container = getStack();
    ensureStyle();
    var msg = item.msg, detail = item.detail;
    var t = document.createElement('div');
    t.className = 'hm-toast';
    t.setAttribute('role','status');
    t.setAttribute('aria-live','polite');
    t.setAttribute('data-max', String(opts.maxStack || DEFAULT_MAX));
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
    container.appendChild(t);
    evictOldest();
    if(opts.actions && opts.actions.length){
      var actBtns = t.querySelectorAll('.hm-toast-act');
      opts.actions.slice(0,2).forEach(function(a, i){
        actBtns[i].addEventListener('click', function(){
          var f = a.onClick;
          dismiss(t);
          if(f) setTimeout(f, 0);
        });
      });
    }
    t.querySelector('.hm-toast-close').addEventListener('click', function(){ dismiss(t); });
    var timer = setTimeout(function(){ dismiss(t); }, opts.timeout || 4500);
    t._timer = timer;
    requestAnimationFrame(function(){ t.classList.add('show'); });
  }

  window.toast = function(msg, detail, options){
    options = options || {};
    show({ msg: msg, detail: detail || '', opts: options });
  };
  /* 清空栈（技能页面销毁/测试用）：移除当前全部显示 */
  window.__hmToastFlush = function(){
    if(!stack) return;
    stack.querySelectorAll('.hm-toast').forEach(function(t){ clearTimeout(t._timer); t.remove(); });
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
  var html = '<div class="hm-actions">';
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

/* ── selectList（P0 · 勾选列表 + 批量操作 + 计数联动 + 行内控件 v1.9）──
 * selectList(items, batchActions?, opts?)
 * items: [{ id, title, sub?, group?, widget? }]
 *   widget（v1.9 · #327）: { type:'date'|'text'|'select', key, label?, placeholder?, options? }
 *     - options: [ {value,label} | '原始值' ]（select 用; 缺省渲染占位「请选择」）
 *     - 非法 type 降级 text（宽容渲染, 不报错）; key 缺省 'w'+行号
 * batchActions: [{ label, kind:'ok'|'danger', onClick(ids, values?) }]
 *   - v1.9: onClick 第二参 values = 勾选条目对应的行内值 { [id]: { [key]: value } }
 *     （只读勾选条目; 未填 → null, 不报错; 未勾选条目不参与）
 * opts: { onSubmit(selectedIds, values) }  —— v1.9 读取接口（选定形态, 等价 getValues）
 *   - 任意批量操作按钮点击后触发（与 onClick 并列; 无勾选时不触发, 与既有拦截一致）
 *   - values = 全部行内值 { [id]: { [key]: value } }（含未勾选条目; 未填 → null; 无 widget 条目不出现）
 * 安全: 行内 label/placeholder/option value+label 渲染一律 esc, 零注入面
 * 兼容: 未声明 widget 的既有调用渲染输出与行为完全不变（守卫测试回归 outerHTML）
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

  /* 行内控件 HTML（v1.9 · #327）: 未声明 widget → 空串, 渲染零变化 */
  function widgetHtml(it, idx){
    var w = it.widget;
    if(!w || typeof w !== 'object') return '';
    var t = w.type === 'date' ? 'date' : (w.type === 'select' ? 'select' : 'text');  // 非法 type 降级 text
    var key = w.key != null ? String(w.key) : ('w' + idx);
    var lbl = w.label ? '<span class="sl-widget-label">'+esc(w.label)+'</span>' : '';
    var inner;
    if(t === 'select'){
      inner = '<select class="sl-widget-input" data-wkey="'+esc(key)+'">';
      var os = arr(w.options);
      if(!os.length) inner += '<option value="">请选择</option>';
      os.forEach(function(o){
        var ov = (o && typeof o === 'object') ? (o.value != null ? o.value : o.label) : o;
        var ol = (o && typeof o === 'object') ? (o.label != null ? o.label : o.value) : o;
        inner += '<option value="'+esc(String(ov == null ? '' : ov))+'">'+esc(String(ol == null ? '' : ol))+'</option>';
      });
      inner += '</select>';
    } else {
      inner = '<input class="sl-widget-input" data-wkey="'+esc(key)+'" type="'+t+'"'
        + (w.placeholder ? ' placeholder="'+esc(w.placeholder)+'"' : '')
        + '>';
    }
    return '<span class="sl-widget">'+lbl+inner+'</span>';
  }

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
        + widgetHtml(it, idx)
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
    /* 行内值读取（v1.9 · #327）: 计数只随勾选态, 控件值变化不干扰 */
    function widgetVal(el){
      var v = el.value;
      return (v === '' || v === null || v === undefined) ? null : v;  // 未填统一归一 null
    }
    function readAll(){
      var out = {};
      root.querySelectorAll('.sl-item').forEach(function(itemEl){
        var cb = itemEl.querySelector('input[type="checkbox"]');
        var id = cb ? cb.getAttribute('data-id') : null;
        if(id == null) return;
        itemEl.querySelectorAll('.sl-widget-input').forEach(function(el){
          var key = el.getAttribute('data-wkey');
          if(key == null) return;
          (out[id] = out[id] || {})[key] = widgetVal(el);
        });
      });
      return out;
    }
    function readChecked(){
      var out = {};
      root.querySelectorAll('input[type="checkbox"]:checked').forEach(function(cb){
        var id = cb.getAttribute('data-id');
        var itemEl = cb.closest('.sl-item');
        itemEl.querySelectorAll('.sl-widget-input').forEach(function(el){
          var key = el.getAttribute('data-wkey');
          if(key == null) return;
          (out[id] = out[id] || {})[key] = widgetVal(el);
        });
      });
      return out;
    }
    root.querySelectorAll('[data-batch]').forEach(function(btn){
      btn.addEventListener('click', function(){
        var ids = root.querySelectorAll('input[type="checkbox"]:checked');
        if(!ids.length){ toast('请先勾选','勾选要处理的条目',{badge:{text:'提示',type:'warn'}}); return; }
        var idList = Array.prototype.map.call(ids, function(x){ return x.getAttribute('data-id'); });
        var a = batchActions.filter(function(x){ return x.label === btn.getAttribute('data-batch'); })[0];
        if(a && a.onClick) a.onClick(idList, readChecked());  // v1.9: 第二参 = 勾选条目行内值
        if(opts.onSubmit) opts.onSubmit(idList, readAll());   // v1.9: 读取接口 = 全部行内值
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

/* ── statusBadge（P1 · 状态徽章）──
 * statusBadge(status, text?)
 *   status: 'ok'|'warn'|'danger'|'empty'（非法值降级 'empty', 防无样式徽章）
 *   text:   自定义文案（缺省用语义默认: 成功/警告/失败/无数据）
 * 安全: status 白名单后直拼 class（无注入面）; text 经 esc
 */
var STATUS_BADGE_MAP = { ok:'成功', warn:'警告', danger:'失败', empty:'无数据' };
function statusBadge(status, text){
  status = STATUS_BADGE_MAP[status] ? status : 'empty';  // 非法/未知值降级 empty
  var txt = (text === null || text === undefined || text === '') ? STATUS_BADGE_MAP[status] : String(text);
  return '<span class="hm-status '+status+'">'+esc(txt)+'</span>';
}

/* ── emptyState（P1 · 空状态）──
 * emptyState({icon?, text, hint?, action?})
 *   icon:   emoji/文本图标（esc）
 *   text:   主文案（缺省 '暂无数据', esc）
 *   hint:   次要提示（esc）
 *   action: 操作区 HTML —— 受信 HTML 透传（调用方负责其内容安全, 通常为按钮;
 *           如含用户数据必须先 esc）。其余字段一律 esc, 防 XSS。
 */
function emptyState(cfg){
  cfg = cfg || {};
  return '<div class="hm-empty">'
    + (cfg.icon?'<div class="hm-empty-icon">'+esc(cfg.icon)+'</div>':'')
    + '<div class="hm-empty-text">'+esc(cfg.text||'暂无数据')+'</div>'
    + (cfg.hint?'<div class="hm-empty-hint">'+esc(cfg.hint)+'</div>':'')
    + (cfg.action?('<div class="hm-empty-action">'+cfg.action+'</div>'):'')
    + '</div>';
}

/* ── errorReceipt（P1 · 错误回执 · 08 规范 §6.1 三层反馈）──
 * errorReceipt({message, retryPrompt?, data?, log?, payload?})
 *   message:     错误描述（esc, 缺省 '操作失败'）
 *   retryPrompt: 修正重试按钮文案（有则渲染「修正重试」按钮, 复制该 prompt）
 *   data:        复制数据按钮内容（字符串直传; 或省略时从 payload 生成）
 *   log:         复制日志按钮内容（字符串直传; 或省略时从 payload 生成）
 *   payload:     数据信封 {status, data:{meta, scene}} —— 显式传入, 优先于全局
 *   __hmPayload: 兼容全局兜底（actionBar 已设置; 显式 payload 优先）
 * 布局: 修正重试 primary 独立一行 + 复制数据/日志 ghost 一行 2 个（08 规范奇数按钮）
 * 安全: message/data/log 经 esc + data-t 中转（onclick 仅 copyText(this.dataset.t), 零注入面）
 */
function errorReceipt(cfg){
  cfg = cfg || {};
  var payload = cfg.payload || window.__hmPayload || null;
  var dataText = cfg.data != null ? String(cfg.data) : '';
  var logText = cfg.log != null ? String(cfg.log) : '';
  // 有效数据源 = payload 含 scene.snapshot（残缺 payload 视为无数据, 不生成垃圾复制内容）
  var pValid = !!(payload && payload.data && payload.data.scene && payload.data.scene.snapshot);
  if(!dataText && pValid){
    try { dataText = buildDataText(payload); } catch(e){ dataText = ''; }  // 数据不完整 → 不渲染复制数据按钮（错误回执容错）
  }
  if(!logText && pValid){
    try { logText = buildLogText(payload); } catch(e){ logText = ''; }     // 同上
  }
  var html = '<div class="hm-error">'
    + '<div class="hm-error-title">❌ '+esc(cfg.message||'操作失败')+'</div>';
  if(cfg.retryPrompt){
    html += '<div class="hm-actions"><button class="copy primary wide" onclick="copyText(this.dataset.t)" data-t="'+esc(cfg.retryPrompt).replace(/"/g,'&quot;')+'">修正重试</button></div>';
  }
  var btns = '';
  if(dataText) btns += '<button class="copy ghost" onclick="copyText(this.dataset.t)" data-t="'+esc(dataText).replace(/"/g,'&quot;')+'">复制数据</button>';
  if(logText) btns += '<button class="copy ghost" onclick="copyText(this.dataset.t)" data-t="'+esc(logText).replace(/"/g,'&quot;')+'">复制日志</button>';
  if(btns) html += '<div class="hm-actions">'+btns+'</div>';
  return html + '</div>';
}
