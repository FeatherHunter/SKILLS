/* Base Skill 图表组件 v1.3（公共组件/ · 唯一真相源 · 跨技能 · 领域无关）
 * 接口: charts.bar / charts.line / charts.donut / charts.progress
 * 来源: 居家管家 CHARTS_JS 提取（bar/line/progress 零行为变更 + token A 组化）
 *       + 饼干记账 donutSVG 重构为数据驱动（donut, 2026-08-12 新增）
 * 约束: 纯 CSS+SVG 无外部依赖 · 手机 375px 适配 · 语义色走 token A 组（带 fallback）
 *       · 数据空 → emptyState 联动（window.emptyState 存在则用之, 否则内联兜底）
 * 注入点: 由 injector.py --charts 参数注入 CHARTS-HELPERS 占位符（0 或 1）
 * 注意: 本资产注释/字符串不含脚本闭合标签字样（防被 HTML 解析提前截断, Base 契约要求）
 */
(function(){
if(window.__chartsLoaded)return;window.__chartsLoaded=true;
/* 自包含转义: 复用 window.esc（base.js 已注入）否则本地兜底, 保证 charts 可独立注入 */
var _esc=window.esc||function(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});};
var _num=function(v){var n=Number(v);return isNaN(n)?0:n;};
/* 空态联动: emptyState 存在用之, 否则内联兜底 */
function _empty(el,hint){
  if(typeof window.emptyState==='function'){el.innerHTML=window.emptyState({icon:'📊',text:'暂无数据',hint:hint||'有记录后自动生成图表'});}
  else{el.innerHTML='<div class="hm-c-empty">📊 暂无数据</div>';}
}
var _styleId='hm-charts-style';
if(!document.getElementById(_styleId)){
  var st=document.createElement('style');st.id=_styleId;
  st.textContent='.hm-chart{position:relative}.hm-c-empty{text-align:center;color:var(--fg3,#86868b);font-size:12.5px;padding:18px 8px}.hm-c-bar{display:flex;align-items:flex-end;gap:6px;height:150px;padding:26px 4px 0;overflow-x:auto}.hm-c-col{flex:1 1 0;min-width:22px;display:flex;flex-direction:column;align-items:center;height:100%;justify-content:flex-end}.hm-c-col .hm-c-v{font-size:10px;color:var(--fg3,#86868b);margin-bottom:2px;white-space:nowrap}.hm-c-col .hm-c-b{width:100%;max-width:34px;border-radius:6px 6px 2px 2px;background:var(--blue,#007aff);min-height:2px;cursor:pointer;transition:filter .15s}.hm-c-col .hm-c-b:hover{filter:brightness(.9)}.hm-c-col .hm-c-l{font-size:10px;color:var(--fg2,#6e6e73);margin-top:4px;white-space:nowrap;max-width:56px;overflow:hidden;text-overflow:ellipsis}.hm-c-line-wrap{position:relative;height:150px;padding:4px 0 20px}.hm-c-line-svg{position:relative;width:100%;height:100%}.hm-c-line-svg svg{width:100%;height:100%;display:block;overflow:visible}.hm-c-dot{position:absolute;width:8px;height:8px;margin:-4px 0 0 -4px;border-radius:50%;background:var(--blue,#007aff);pointer-events:none}.hm-c-line-wrap .hm-c-x{display:flex;justify-content:space-between;font-size:10px;color:var(--fg3,#86868b);margin-top:2px}.hm-c-donut-wrap{display:flex;align-items:center;gap:18px;flex-wrap:wrap;justify-content:center;padding:6px 0}.hm-c-donut{width:150px;height:150px;flex-shrink:0}.hm-c-donut svg{width:100%;height:100%;display:block}.hm-c-donut-legend{flex:1;min-width:150px;display:flex;flex-direction:column;gap:7px}.hm-c-donut-legend .hm-c-dl{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--fg2,#6e6e73)}.hm-c-donut-legend .hm-c-dot{width:10px;height:10px;border-radius:3px;flex-shrink:0}.hm-c-donut-legend .hm-c-dl-n{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.hm-c-donut-legend .hm-c-dl-v{font-weight:700;color:var(--fg,#1d1d1f);font-variant-numeric:tabular-nums}.hm-c-donut-legend .hm-c-dl-p{color:var(--fg3,#86868b);font-variant-numeric:tabular-nums;min-width:38px;text-align:right}.hm-c-progress{display:flex;align-items:center;gap:8px}.hm-c-progress .hm-c-p-track{flex:1;height:8px;background:#ececf1;border-radius:99px;overflow:hidden}.hm-c-progress .hm-c-p-fill{height:100%;border-radius:99px;background:var(--blue,#007aff);transition:width .4s}.hm-c-progress .hm-c-p-n{font-size:11px;font-weight:700;color:var(--fg2,#6e6e73);min-width:34px;text-align:right}@media(max-width:720px){.hm-c-bar{height:130px}.hm-c-line-wrap{height:130px}.hm-c-donut{width:130px;height:130px}.hm-c-donut-wrap{gap:12px}}';
  document.head.appendChild(st);
}
window.charts={
  /* ── 进度条: charts.progress(el, pct[, {color}]) ── pct 0~100 数字（非数兜底 0, 超界收敛） */
  progress:function(el,pct,opt){
    opt=opt||{};if(!el)return;
    pct=Math.max(0,Math.min(100,_num(pct)));
    var color=opt.color||'var(--blue,#007aff)';
    el.innerHTML='<div class="hm-c-progress"><div class="hm-c-p-track"><div class="hm-c-p-fill" style="width:'+pct+'%;background:'+color+'"></div></div><div class="hm-c-p-n">'+Math.round(pct)+'%</div></div>';
  },
  /* ── 柱状图: charts.bar(el, items[, {onclick,color}]) ── items:[{label,value,color?}] */
  bar:function(el,items,opt){
    opt=opt||{};if(!el)return;
    items=Array.isArray(items)?items:[];
    if(!items.length){_empty(el,'有物品/记录数据后自动生成');return;}
    var max=0;items.forEach(function(it){if(_num(it.value)>max)max=_num(it.value);});
    if(!max)max=1;
    el.innerHTML='<div class="hm-c-bar">'+items.map(function(it,i){
      var h=Math.max(2,Math.round(_num(it.value)/max*100));
      var color=it.color||opt.color||'var(--blue,#007aff)';
      return '<div class="hm-c-col" data-i="'+i+'"><div class="hm-c-v">'+_esc(_num(it.value))+'</div><div class="hm-c-b" data-i="'+i+'" style="height:'+h+'%;background:'+color+'"></div><div class="hm-c-l" title="'+_esc(it.label)+'">'+_esc(it.label)+'</div></div>';
    }).join('')+'</div>';
    if(opt.onclick){
      el.querySelectorAll('.hm-c-b,.hm-c-col').forEach(function(n){n.style.cursor='pointer';n.onclick=function(){opt.onclick(Number(n.getAttribute('data-i')));};});
    }
  },
  /* ── 折线图: charts.line(el, items[, {ondrill,color}]) ── items:[{label,value}] */
  line:function(el,items,opt){
    opt=opt||{};if(!el)return;
    items=Array.isArray(items)?items:[];
    if(!items.length){_empty(el,'有趋势数据后自动生成');return;}
    var W=320,H=110,P=6;
    var max=1;items.forEach(function(it){if(_num(it.value)>max)max=_num(it.value);});
    var pts=items.map(function(it,i){
      var x=i===0?P:(P+(W-2*P)*i/(Math.max(1,items.length-1)));
      var y=H-P-(_num(it.value)/max)*(H-2*P);
      return [x,y];
    });
    var last=pts[pts.length-1]||[0,0];
    var grid='';for(var g=0;g<3;g++){var gy=H-P-(H-2*P)*g/2;grid+='<line x1="0" y1="'+gy+'" x2="'+W+'" y2="'+gy+'" stroke="#ececf1" stroke-width="1"/>';}
    var poly=pts.map(function(p){return p[0].toFixed(1)+','+p[1].toFixed(1);}).join(' ');
    // 数据点用 HTML overlay(绝对定位圆形),避免 preserveAspectRatio=none 把 SVG circle 拉成椭圆
    var dots=pts.map(function(p,i){var lx=(p[0]/W*100).toFixed(2),ty=(p[1]/H*100).toFixed(2);return '<i class="hm-c-dot" style="left:'+lx+'%;top:'+ty+'%" title="'+_esc(items[i].label)+' · '+_esc(items[i].value)+'"></i>';}).join('');
    var lbls=items.map(function(it){return _esc(it.label);});
    var firstL=lbls[0]||'',lastL=lbls[lbls.length-1]||'';
    el.innerHTML='<div class="hm-c-line-wrap"><div class="hm-c-line-svg"><svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="none">'+grid+'<polyline points="'+poly+'" fill="none" stroke="'+(opt.color||'var(--blue,#007aff)')+'" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/></svg>'+dots+'</div><div class="hm-c-x"><span>'+_esc(firstL)+'</span><span>'+_esc(lastL)+'</span></div></div>';
    if(opt.ondrill){var svgEl=el.querySelector('svg');svgEl.style.cursor='pointer';svgEl.onclick=function(e){var r=svgEl.getBoundingClientRect();var x=e.clientX-r.left;var frac=Math.max(0,Math.min(1,x/r.width));var idx=Math.min(items.length-1,Math.round(frac*(items.length-1)));opt.ondrill(idx);};}
  },
  /* ── 环形图: charts.donut(el, items[, {centerLabel,centerValue,legend}]) ──
   * items:[{label,value,color?}]（color 缺省走内置 Apple 语义色板）
   * opt.centerLabel 中心上文案 · opt.centerValue 中心大数字（缺省=合计） · opt.legend=false 隐藏图例
   * 源: 饼干记账 donutSVG 重构为数据驱动（2026-08-12） */
  donut:function(el,items,opt){
    opt=opt||{};if(!el)return;
    items=Array.isArray(items)?items:[];
    if(!items.length){_empty(el,'有分类数据后自动生成');return;}
    var palette=['#007aff','#34c759','#ff9500','#ff3b30','#af52de','#5ac8fa','#ffcc00','#8e8e93','#ff2d55','#00c7be'];
    var total=0;items.forEach(function(it){total+=_num(it.value);});
    if(!total){_empty(el,'合计为零, 无环形数据');return;}
    var r=52,cx=60,cy=60,c=2*Math.PI*r;
    var acc=0;
    var segments=items.map(function(it,i){
      var pct=_num(it.value)/total;
      var dash=pct*c;
      var seg='<circle cx="'+cx+'" cy="'+cy+'" r="'+r+'" fill="none" stroke="'+(it.color||palette[i%palette.length])+'" stroke-width="16" stroke-dasharray="'+dash+' '+(c-dash)+'" stroke-dashoffset="'+(-acc)+'" transform="rotate(-90 '+cx+' '+cy+')"/>';
      acc+=dash;
      return seg;
    }).join('');
    var centerLabel=opt.centerLabel!=null?_esc(opt.centerLabel):'';
    var centerValue=opt.centerValue!=null?_esc(opt.centerValue):_esc(total);
    var legend=(opt.legend===false)?'':'<div class="hm-c-donut-legend">'+items.map(function(it,i){
      var pct=total?Math.round(_num(it.value)/total*100):0;
      return '<div class="hm-c-dl"><span class="hm-c-dot" style="background:'+(it.color||palette[i%palette.length])+'"></span><span class="hm-c-dl-n">'+_esc(it.label)+'</span><span class="hm-c-dl-v">'+_esc(_num(it.value))+'</span><span class="hm-c-dl-p">'+pct+'%</span></div>';
    }).join('')+'</div>';
    el.innerHTML='<div class="hm-c-donut-wrap"><div class="hm-c-donut"><svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg"><circle cx="'+cx+'" cy="'+cy+'" r="'+r+'" fill="none" stroke="#ececf1" stroke-width="16"/>'+segments+(centerLabel||centerValue!==''?'<text x="'+cx+'" y="'+(cy-(centerLabel?2:4))+'" text-anchor="middle" style="font-size:8px;fill:var(--fg3,#86868b)">'+centerLabel+'</text><text x="'+cx+'" y="'+(cy+(centerLabel?14:10))+'" text-anchor="middle" style="font-size:13px;font-weight:700;fill:var(--fg,#1d1d1f)">'+centerValue+'</text>':'')+'</svg></div>'+legend+'</div>';
  }
};
})();
