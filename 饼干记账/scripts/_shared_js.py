# -*- coding: utf-8 -*-
"""共享 JS helper(复制自居家管家 render/_shared.py · B2 模板依赖)

validate / esc / arr / val / yes 等前端守卫函数,由 render_help.py 注入
模板 <!--SHARED-HELPERS--> 占位符。与居家管家保持同源,勿手改。
"""

SHARED_JS = """
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
