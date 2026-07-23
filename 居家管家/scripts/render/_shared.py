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
"""