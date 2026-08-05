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
function copyText(s){if(!s)return;if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(s).catch(()=>{});}else{var t=document.createElement('textarea');t.value=s;document.body.appendChild(t);t.select();document.execCommand('copy');document.body.removeChild(t);}toast('已复制');}
function toast(msg){var t=document.createElement('div');t.textContent=msg;t.style.cssText='position:fixed;bottom:26px;left:50%;transform:translateX(-50%);background:rgba(29,29,31,.92);color:#fff;padding:10px 18px;border-radius:999px;font-size:14px;z-index:999;animation:fadeup .25s ease';document.body.appendChild(t);setTimeout(()=>{t.style.opacity='0';t.style.transition='opacity .4s';setTimeout(()=>t.remove(),420);},1400);}
function metaHeader(p,m){var me=p.data.meta||{};var stage=m&&m.stage?('<span class="stage">'+esc(m.stage)+'</span>'):'';return '<header class="hero"><div class="eyebrow">'+esc(me.command_cn||'')+' · 唤醒词「'+esc(me.wake_word||'')+'」 · '+esc(me.occurred_at||'')+'</div><h1>'+esc(m&&m.title||me.command_cn||'')+'</h1>'+(m&&m.lead?'<p class="lead">'+esc(m.lead)+'</p>':'')+stage+'</header>';}
function remindersBlock(p){var rs=arr(p.data.reminders);if(!rs.length)return '';return '<section class="remind"><h2>顺路提醒</h2>'+rs.map(r=>'<div class="remind-item '+(r.type==='warn'?'warn':r.type==='danger'?'bad':'')+'">'+esc(r.text)+'</div>').join('')+'</section>';}
function actionBar(p,extra){var d=p.data;var cd=JSON.stringify(d.copy_data||{},null,2);var cl=JSON.stringify(d.copy_log||{},null,2);var btns=arr(extra||[]);var sb=arr(d.scene&&d.scene.buttons||[]);var html='<div class="actions"><button class="copy" onclick="copyText(this.dataset.t)" data-t="'+esc(cd).replace(/"/g,'&quot;')+'">复制数据</button><button class="copy alt" onclick="copyText(this.dataset.t)" data-t="'+esc(cl).replace(/"/g,'&quot;')+'">复制日志</button>';btns.concat(sb).forEach(b=>{html+='<button class="copy '+(b.kind||'')+'" onclick="copyText(this.dataset.t)" data-t="'+esc(b.text).replace(/"/g,'&quot;')+'">'+esc(b.label)+'</button>';});return html+'</div>';}
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
  st.textContent='.hm-chart{position:relative}.hm-c-bar{display:flex;align-items:flex-end;gap:6px;height:150px;padding:26px 4px 0;overflow-x:auto}.hm-c-col{flex:1 1 0;min-width:22px;display:flex;flex-direction:column;align-items:center;height:100%;justify-content:flex-end}.hm-c-col .hm-c-v{font-size:10px;color:var(--fg3,#86868b);margin-bottom:2px;white-space:nowrap}.hm-c-col .hm-c-b{width:100%;max-width:34px;border-radius:6px 6px 2px 2px;background:var(--blue,#007aff);min-height:2px;cursor:pointer;transition:filter .15s}.hm-c-col .hm-c-b:hover{filter:brightness(.9)}.hm-c-col .hm-c-l{font-size:10px;color:var(--fg2,#6e6e73);margin-top:4px;white-space:nowrap;max-width:56px;overflow:hidden;text-overflow:ellipsis}.hm-c-line-wrap{position:relative;height:150px;padding:4px 0 20px}.hm-c-line-wrap svg{width:100%;height:100%;display:block;overflow:visible}.hm-c-line-wrap .hm-c-x{display:flex;justify-content:space-between;font-size:10px;color:var(--fg3,#86868b);margin-top:2px}.hm-c-progress{display:flex;align-items:center;gap:8px}.hm-c-progress .hm-c-p-track{flex:1;height:8px;background:#ececf1;border-radius:99px;overflow:hidden}.hm-c-progress .hm-c-p-fill{height:100%;border-radius:99px;background:var(--blue,#007aff);transition:width .4s}.hm-c-progress .hm-c-p-n{font-size:11px;font-weight:700;color:var(--fg2,#6e6e73);min-width:34px;text-align:right}@media(max-width:720px){.hm-c-bar{height:130px}.hm-c-line-wrap{height:130px}}';
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
    var dots=pts.map(function(p,i){return '<circle cx="'+p[0].toFixed(1)+'" cy="'+p[1].toFixed(1)+'" r="3" fill="'+(opt.color||'var(--blue,#007aff)')+'"><title>'+esc(items[i].label)+' · '+esc(items[i].value)+'</title></circle>';}).join('');
    var lbls=items.map(function(it){return esc(it.label);});
    var firstL=lbls[0]||'',lastL=lbls[lbls.length-1]||'';
    el.innerHTML='<div class="hm-c-line-wrap"><svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none">'+grid+'<polyline points="'+poly+'" fill="none" stroke="'+(opt.color||'var(--blue,#007aff)')+'" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>'+dots+'</svg><div class="hm-c-x"><span>'+esc(firstL)+'</span><span>'+esc(lastL)+'</span></div></div>';
    if(opt.ondrill){el.querySelector('svg').style.cursor='pointer';el.querySelector('svg').onclick=function(e){var r=el.getBoundingClientRect();var x=e.clientX-r.left;var frac=Math.max(0,Math.min(1,x/r.width));var idx=Math.min(items.length-1,Math.round(frac*(items.length-1)));opt.ondrill(idx);};}
  }
};
})();
"""