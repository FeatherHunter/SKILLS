"""模板共享 JS 助手 (R9 DRY 单一权威源)

被 templates/*.html 通过 <!--SHARED-HELPERS--> 占位符引用
render_page 自动把 SHARED_JS 字符串注入到该占位符

包含函数:
  - esc(s)        HTML 转义防 XSS
  - arr(v)        安全数组访问 (非数组返回 [])
  - val(v)        显示占位符 '未填写'
  - yes(v)        通过/未通过徽章
  - validate(p)   payload 守门: status==='ok' + data 是对象

修改这里 = 修改所有 6 模板的共享行为
"""
SHARED_JS = r"""
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function arr(v){return Array.isArray(v)?v:[];}
function val(v){return v===null||v===undefined||v===''?'<span style="color:var(--fg3)">未填写</span>':esc(v);}
function yes(v){return v?'<span class="ok">通过</span>':'<span class="bad">未通过</span>';}
function validate(p){if(!p||typeof p!=='object')return{ok:false,msg:'数据未注入'};if(p.status!=='ok')return{ok:false,msg:p.message||'数据状态非 ok'};if(!p.data||typeof p.data!=='object')return{ok:false,msg:'data 缺失'};return{ok:true};}
function _fbCopy(s){var ok=false;try{var t=document.createElement('textarea');t.value=s;t.style.cssText='position:fixed;left:-9999px;top:0;opacity:0';document.body.appendChild(t);t.focus();t.select();ok=document.execCommand('copy');document.body.removeChild(t);}catch(e){ok=false;}return ok;}
function copyText(s){if(!s)return;function ok(){toast('已复制','粘贴给 AI,居家管家技能会自动执行这个流程,完成后你会拿到结果 HTML + 一句话总结。');}function fail(){toast('复制失败','请长按选择文本手动复制,或检查浏览器剪贴板权限。');}if(navigator.clipboard&&navigator.clipboard.writeText){try{var pr=navigator.clipboard.writeText(s);if(pr&&pr.then){pr.then(function(){ok();}).catch(function(){_fbCopy(s)?ok():fail();});}else{ok();}}catch(e){_fbCopy(s)?ok():fail();}}else{_fbCopy(s)?ok():fail();}}
function toast(msg,detail){if(!document.getElementById('hm-toast-style')){var st=document.createElement('style');st.id='hm-toast-style';st.textContent='.hm-toast{position:fixed;left:50%;bottom:calc(24px + env(safe-area-inset-bottom,0));transform:translateX(-50%) scale(.9);opacity:0;background:rgba(28,28,30,.94);-webkit-backdrop-filter:blur(20px) saturate(180%);backdrop-filter:blur(20px) saturate(180%);color:#f0f0f0;border-radius:14px;padding:13px 14px 13px 16px;display:flex;align-items:flex-start;gap:12px;max-width:480px;min-width:300px;box-shadow:0 10px 32px rgba(0,0,0,.32),0 0 0 .5px rgba(255,255,255,.08) inset;pointer-events:none;transition:opacity .22s ease-out,transform .22s cubic-bezier(.34,1.56,.64,1);z-index:9999}.hm-toast.show{opacity:1;transform:translateX(-50%) scale(1);pointer-events:auto}.hm-toast-icon{font-size:20px;line-height:1;padding-top:1px;flex-shrink:0}.hm-toast-body{flex:1;min-width:0}.hm-toast-title{font-weight:600;font-size:12.5px;line-height:1.4;color:#fff;margin-bottom:2px}.hm-toast-detail{font-size:11px;line-height:1.5;color:#c8c8cc}.hm-toast-close{background:rgba(255,255,255,.10);color:#34c759;border:0;border-radius:8px;padding:5px 9px;font-size:10.5px;font-weight:500;font-family:inherit;cursor:pointer;white-space:nowrap;margin-left:6px;flex-shrink:0}.hm-toast-close:active{background:rgba(255,255,255,.2)}@media(max-width:820px){.hm-toast{left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom,0));transform:translateX(0) scale(.95);max-width:none;min-width:0}.hm-toast.show{transform:translateX(0) scale(1)}}';document.head.appendChild(st);}var t=document.createElement('div');t.className='hm-toast';t.innerHTML='<div class="hm-toast-icon">📋</div><div class="hm-toast-body"><div class="hm-toast-title">'+esc(msg)+'</div>'+(detail?'<div class="hm-toast-detail">'+esc(detail)+'</div>':'')+'</div><button class="hm-toast-close">✓ 知道了</button>';document.body.appendChild(t);requestAnimationFrame(function(){t.classList.add('show');});var timer=setTimeout(function(){t.classList.remove('show');setTimeout(function(){t.remove();},260);},4500);t.querySelector('.hm-toast-close').onclick=function(){t.classList.remove('show');clearTimeout(timer);setTimeout(function(){t.remove();},260);};}
function metaHeader(p,m){var me=p.data.meta||{};var stage=m&&m.stage?('<span class="stage">'+esc(m.stage)+'</span>'):'';return '<header class="hero"><div class="eyebrow" style="color:#8e8e93;font-size:11px;font-weight:600">'+esc(me.command_cn||'')+' · '+esc(me.occurred_at||'')+'</div><h1>'+esc(m&&m.title||me.command_cn||'')+'</h1>'+(m&&m.lead?'<p class="lead">'+esc(m.lead)+'</p>':'')+stage+'</header>';}
function remindersBlock(p){var rs=arr(p.data.reminders);if(!rs.length)return '';return '<section class="remind"><h2>顺路提醒</h2>'+rs.map(r=>'<div class="remind-item '+(r.type==='warn'?'warn':r.type==='danger'?'bad':'')+'">'+esc(r.text)+'</div>').join('')+'</section>';}
function buildDataText(p){var d=p.data||{},me=d.meta||{},s=d.scene||{};var L=['【居家管家 · '+(me.command_cn||'')+'】'];L.push('场景: '+(me.command_cn||'')+'('+(s.scene_id||me.scene_id||'')+') · 唤醒词「'+(me.wake_word||'')+'」');L.push('时间: '+(me.occurred_at||''));var it=s.item;if(it){L.push('物品: '+(it.name||'')+(it.category_name?' · 分类:'+it.category_name:'')+(it.location?' · 位置:'+it.location:'')+(it.quantity!=null?' · 数量:'+it.quantity:'')+(it.status?' · 状态:'+it.status:'')+((it.tags||[]).length?' · 标签:'+it.tags.join('/'):''));}var r=s.receipt;if(r){if(r.summary)L.push('结果: '+r.summary);if(r.diff&&r.diff.length)L.push('变更: '+r.diff.map(function(x){return (x.field||'')+' '+(x.before??'')+' → '+(x.after??'');}).join('; '));if(r.next)L.push('下一步: '+r.next);}if(s.items&&s.items.length&&!s.item){var isForm=s.mode||s.items[0].draft;L.push((isForm?'清单 '+s.items.length+' 条:':'命中 '+s.items.length+' 件:'));s.items.slice(0,12).forEach(function(x){var d0=x.draft||{};var nm=d0.name||x.name||'';var q=d0.quantity!=null?d0.quantity:(x.quantity!=null?x.quantity:'');L.push(' · '+(nm||'#')+((d0.category_name||x.category_name)?' · 分类:'+(d0.category_name||x.category_name):'')+(q!==''?' · 数量:'+q:'')+((d0.location||x.location)?' @'+(d0.location||x.location):'')+((x.status||d0.location_status)?' ['+(x.status||d0.location_status)+']':''));});}if(s.groups&&!it&&!r&&!s.items){L.push('分组 '+s.groups.length+' 组:');s.groups.slice(0,10).forEach(function(g){L.push(' · '+(g.name||'')+' ×'+(g.count||g.items&&g.items.length||0));});}if(!it&&!r&&!s.items&&!s.groups){var cp=d.copy_data||{};if(cp.target)L.push('目标: '+cp.target);var pp=cp.payload||{};try{var _lines=[];function _flatten(o,pre){if(o&&typeof o==='object'&&!Array.isArray(o)){Object.keys(o).forEach(function(k){var v=o[k];if(v&&typeof v==='object'){_flatten(v,pre+k+'.');}else{_lines.push((pre||'')+k+': '+(v===null||v===undefined?'':v));}});}else if(Array.isArray(o)){_lines.push(pre.slice(0,-1)+': '+o.length+' 条');}}_flatten(pp,'');L.push('数据: ');L.push.apply(L,_lines.slice(0,30));}catch(e){L.push('数据: '+String(pp));}}return L.join('\n');}
function buildLogText(p){var d=p.data||{},me=d.meta||{},s=d.scene||{},cl=d.copy_log||{};var L=['① 场景标识'];L.push('  command_cn: '+(me.command_cn||''));L.push('  唤醒词: '+(me.wake_word||'(未知)'));L.push('  场景名: '+(me.command_cn||'')+'('+(s.scene_id||me.scene_id||'')+')');L.push('');L.push('② AI 思考链');L.push('  '+(cl.thinking||'(本地渲染 · 无 AI 链)'));L.push('');L.push('③ 底层数据结构');L.push('  '+(cl.data_structure||'(只读查询)'));L.push('');L.push('④ 调用链');L.push('  '+(cl.call_chain||'(未知)'));L.push('');L.push('⑤ 时间戳 + 版本');L.push('  本地时间: '+(cl.timestamp||me.occurred_at||'(未知)'));L.push('  skill 版本: '+(me.skill_version||'v2.0-SM1'));L.push('');L.push('⑥ 异常信息');L.push('  '+(cl.exception||'无'));return L.join('\n');}
function actionBar(p,extra){window.__hmPayload=p;var btns=arr(extra||[]);var sb=arr(p.data&&p.data.scene&&p.data.scene.buttons||[]);var html='<div class="actions">';btns.concat(sb).forEach(b=>{html+='<button class="copy '+(b.kind||'')+'" onclick="copyText(this.dataset.t)" data-t="'+esc(b.text).replace(/"/g,'&quot;')+'">'+esc(b.label)+'</button>';});html+='<button class="copy alt" onclick="copyText(buildDataText(window.__hmPayload))">复制数据</button><button class="copy alt" onclick="copyText(buildLogText(window.__hmPayload))">复制日志</button></div>';return html;}
"""

# ── 图表共享组件(柱状/折线/进度 · 手机适配)────────────────────────
# 归属: T5 创建并冻结(2026-08-05 · map 并发约定「图表=T5」);
# 后续域复用/演进 = 公共层 ISSUE。
# 纯 CSS+SVG,无外部依赖,单文件自包含;样式全部内联,不依赖模板级 CSS。
CHARTS_JS = r"""
(function(){
if(window.__chartsLoaded)return;window.__chartsLoaded=true;
var _styleId='hm-charts-style';
if(!document.getElementById(_styleId)){
  var st=document.createElement('style');st.id=_styleId;
  st.textContent='.hm-chart{position:relative}.hm-c-bar{display:flex;align-items:flex-end;gap:6px;height:150px;padding:26px 4px 0;overflow-x:auto}.hm-c-col{flex:1 1 0;min-width:22px;display:flex;flex-direction:column;align-items:center;height:100%;justify-content:flex-end}.hm-c-col .hm-c-v{font-size:10px;color:var(--fg3,#86868b);margin-bottom:2px;white-space:nowrap}.hm-c-col .hm-c-b{width:100%;max-width:34px;border-radius:6px 6px 2px 2px;background:var(--blue,#007aff);min-height:2px;cursor:pointer;transition:filter .15s}.hm-c-col .hm-c-b:hover{filter:brightness(.9)}.hm-c-col .hm-c-l{font-size:10px;color:var(--fg2,#6e6e73);margin-top:4px;white-space:nowrap;max-width:56px;overflow:hidden;text-overflow:ellipsis}.hm-c-line-wrap{position:relative;height:150px;padding:4px 0 20px}.hm-c-line-svg{position:relative;width:100%;height:100%}.hm-c-line-svg svg{width:100%;height:100%;display:block;overflow:visible}.hm-c-dot{position:absolute;width:8px;height:8px;margin:-4px 0 0 -4px;border-radius:50%;background:var(--blue,#007aff);pointer-events:none}.hm-c-line-wrap .hm-c-x{display:flex;justify-content:space-between;font-size:10px;color:var(--fg3,#86868b);margin-top:2px}.hm-c-progress{display:flex;align-items:center;gap:8px}.hm-c-progress .hm-c-p-track{flex:1;height:8px;background:#ececf1;border-radius:99px;overflow:hidden}.hm-c-progress .hm-c-p-fill{height:100%;border-radius:99px;background:var(--blue,#007aff);transition:width .4s}.hm-c-progress .hm-c-p-n{font-size:11px;font-weight:700;color:var(--fg2,#6e6e73);min-width:34px;text-align:right}@media(max-width:720px){.hm-c-bar{height:130px}.hm-c-line-wrap{height:130px}}';
  document.head.appendChild(st);
}
window.charts={
  progress:function(el,pct,opt){
    opt=opt||{};pct=Math.max(0,Math.min(100,Number(pct)||0));
    el.innerHTML='<div class="hm-c-progress"><div class="hm-c-p-track"><div class="hm-c-p-fill" style="width:'+pct+'%"></div></div><div class="hm-c-p-n">'+Math.round(pct)+'%</div></div>';
  },
  bar:function(el,items,opt){
    opt=opt||{};var max=0;items.forEach(function(it){if(Number(it.value)>max)max=Number(it.value);});
    if(!max)max=1;
    el.innerHTML='<div class="hm-c-bar">'+items.map(function(it,i){
      var h=Math.max(2,Math.round(Number(it.value)/max*100));
      var color=it.color||'var(--blue,#007aff)';
      return '<div class="hm-c-col" data-i="'+i+'"><div class="hm-c-v">'+esc(Number(it.value))+'</div><div class="hm-c-b" data-i="'+i+'" style="height:'+h+'%;background:'+color+'"></div><div class="hm-c-l" title="'+esc(it.label)+'">'+esc(it.label)+'</div></div>';
    }).join('')+'</div>';
    if(opt.onclick){
      el.querySelectorAll('.hm-c-b,.hm-c-col').forEach(function(n){n.style.cursor='pointer';n.onclick=function(){opt.onclick(Number(n.getAttribute('data-i')));};});
    }
  },
  line:function(el,items,opt){
    opt=opt||{};var W=320,H=110,P=6;
    var max=1;items.forEach(function(it){if(Number(it.value)>max)max=Number(it.value);});
    var pts=items.map(function(it,i){
      var x=i===0?P:(P+(W-2*P)*i/(Math.max(1,items.length-1)));
      var y=H-P-(Number(it.value)/max)*(H-2*P);
      return [x,y];
    });
    var last=pts[pts.length-1]||[0,0];
    var grid='';for(var g=0;g<3;g++){var gy=H-P-(H-2*P)*g/2;grid+='<line x1="0" y1="'+gy+'" x2="'+W+'" y2="'+gy+'" stroke="#ececf1" stroke-width="1"/>';}
    var poly=pts.map(function(p){return p[0].toFixed(1)+','+p[1].toFixed(1);}).join(' ');
    // 数据点用 HTML overlay(绝对定位圆形),避免 preserveAspectRatio=none 把 SVG circle 拉成椭圆
    var dots=pts.map(function(p,i){var lx=(p[0]/W*100).toFixed(2),ty=(p[1]/H*100).toFixed(2);return '<i class="hm-c-dot" style="left:'+lx+'%;top:'+ty+'%" title="'+esc(items[i].label)+' · '+esc(items[i].value)+'"></i>';}).join('');
    var lbls=items.map(function(it){return esc(it.label);});
    var firstL=lbls[0]||'',lastL=lbls[lbls.length-1]||'';
    el.innerHTML='<div class="hm-c-line-wrap"><div class="hm-c-line-svg"><svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none">'+grid+'<polyline points="'+poly+'" fill="none" stroke="'+(opt.color||'var(--blue,#007aff)')+'" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/></svg>'+dots+'</div><div class="hm-c-x"><span>'+esc(firstL)+'</span><span>'+esc(lastL)+'</span></div></div>';
    if(opt.ondrill){var svgEl=el.querySelector('svg');svgEl.style.cursor='pointer';svgEl.onclick=function(e){var r=svgEl.getBoundingClientRect();var x=e.clientX-r.left;var frac=Math.max(0,Math.min(1,x/r.width));var idx=Math.min(items.length-1,Math.round(frac*(items.length-1)));opt.ondrill(idx);};}
  }
};
})();
"""