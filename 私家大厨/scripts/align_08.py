# align_08.py - 08-HTML 交互规范对齐公共层(T3 · 2026-08-09)
#
# 职责(08-HTML交互规范v1 跨技能契约,私家大厨落地):
#   1. 复制数据(5 段 JSON): {scene_id, command_cn, occurred_at, target, payload}
#   2. 复制日志(6 段): 场景标识 / AI 思考链 / 底层数据结构 / 调用链 / 时间戳+版本 / 异常
#   3. 输出命名 `_N` 后缀防覆盖(12.X 共同基础 · N=1 起步,绝不覆盖)
#   4. 共享动作层 HTML/CSS/JS(复制数据/复制日志双按钮 + 5 状态)
#
# 设计:
#   - 模板通过 <!--INJECT-08--> 占位符接收共享动作层(独立于各模板的 INJECT-DATA)
#   - 每个 render 脚本负责构造本场景的 copy_data/copy_log,再调 inject_08_layer()
#   - 5 状态: loading(注入前) / empty(无数据) / error(注入失败/渲染异常)
#             / confirm(确认动作·写操作) / normal(正常内容)
import json
import re
from datetime import datetime
from pathlib import Path

SKILL_VERSION = "v4.0"

# ── 1. 复制数据 5 段 / 复制日志 6 段 ──────────────────────────────
def now_str() -> str:
    """本地时间(ADR-0001)"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_copy_data(scene_id: str, command_cn: str, target, payload) -> dict:
    """复制数据(硬标准): 结构化 JSON 固定 5 段"""
    return {
        "scene_id": scene_id,
        "command_cn": command_cn,
        "occurred_at": now_str(),
        "target": target or "",
        "payload": payload or {},
    }


def build_copy_log(scene_id: str, command_cn: str, wake_word: str,
                   thinking: str = "", data_structure: str = "",
                   call_chain: str = "", exception: str = "") -> dict:
    """复制日志(硬标准): 6 段(场景标识/思考链/数据结构/调用链/时间戳+版本/异常)"""
    return {
        "scene": f"{command_cn} · 唤醒词「{wake_word}」 · 场景「{scene_id}」",
        "thinking": thinking or "意图理解 → 决策点 → 关键判断(摘要级)",
        "data_structure": data_structure or "payload JSON(输入/输出)+ DB 操作类型",
        "call_chain": call_chain or "渲染脚本 / CLI 命令(完整,可复制执行)",
        "timestamp": f"{now_str()} · {SKILL_VERSION}",
        "exception": exception or "",
    }


# ── 2. `_N` 后缀防覆盖(12.X 共同基础 · N=1 起步)────────────────
def unique_output_path(out_dir: Path, stem: str, ext: str = ".html") -> Path:
    """生成绝不覆盖的输出路径:
    首次 → <stem><ext>;冲突 → <stem>_1<ext> / <stem>_2<ext> ...(N=1 起步)
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"{stem}{ext}"
    if not base.exists():
        return base
    n = 1
    while (out_dir / f"{stem}_{n}{ext}").exists():
        n += 1
    return out_dir / f"{stem}_{n}{ext}"


# ── 3. 共享动作层(双按钮 + 5 状态 · 独立于模板主题)──────────────
A08_CSS = r"""
.a08-layer{--a08-blue:#007AFF;--a08-green:#34C759;--a08-orange:#FF9500;--a08-red:#FF3B30;
  --a08-bg:rgba(242,242,247,.96);--a08-card:#FFFFFF;--a08-text:#1C1C1E;--a08-text2:#6E6E73;
  --a08-line:rgba(60,60,67,.12);--a08-shadow:0 1px 3px rgba(0,0,0,.06)}
.a08-layer *{box-sizing:border-box;margin:0;padding:0}
.a08-layer{position:fixed;inset:0;z-index:9990;display:none;align-items:center;justify-content:center;
  background:var(--a08-bg);font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","PingFang SC",sans-serif;
  -webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px)}
.a08-layer.show{display:flex}
.a08-card{background:var(--a08-card);border-radius:18px;box-shadow:var(--a08-shadow);max-width:min(560px,88vw);
  width:100%;padding:28px 24px;text-align:center;max-height:82vh;overflow:auto}
.a08-icon{font-size:44px;margin-bottom:10px}
.a08-title{font-size:17px;font-weight:700;color:var(--a08-text);margin-bottom:8px}
.a08-msg{font-size:13px;color:var(--a08-text2);line-height:1.6;margin-bottom:16px;word-break:break-word}
.a08-bar{position:fixed;left:0;right:0;bottom:0;z-index:9980;display:flex;gap:10px;justify-content:center;
  padding:12px 16px calc(12px + env(safe-area-inset-bottom,0px));
  background:rgba(255,255,255,.94);-webkit-backdrop-filter:blur(20px) saturate(180%);backdrop-filter:blur(20px) saturate(180%);
  border-top:.5px solid var(--a08-line);box-shadow:0 -2px 12px rgba(0,0,0,.06)}
.a08-btn{flex:0 1 auto;min-width:150px;padding:12px 18px;border:none;border-radius:12px;font-size:14px;
  font-weight:600;cursor:pointer;font-family:inherit;background:#F2F2F7;color:var(--a08-text);transition:background .15s}
.a08-btn:hover{background:#E5E5EA}
.a08-btn.primary{background:var(--a08-blue);color:#fff}
.a08-btn.primary:hover{background:#0A84FF}
.a08-btn.confirm{background:var(--a08-green);color:#fff}
.a08-btn.danger{background:var(--a08-red);color:#fff}
.a08-btn.dark{background:#1C1C1E;color:#fff}
.a08-spinner{width:36px;height:36px;border:3px solid rgba(0,122,255,.18);border-top-color:var(--a08-blue);
  border-radius:50%;margin:6px auto 12px;animation:a08spin .8s linear infinite}
@keyframes a08spin{to{transform:rotate(360deg)}}
@media (max-width:480px){.a08-bar{flex-direction:column;padding:10px 12px}.a08-btn{width:100%;min-width:0}}
"""

A08_JS = r"""
/* 共享 08 动作层(align_08.py 注入 · 5 状态 + 双按钮) */
(function(){
'use strict';
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
function copyText(text,okMsg){
  var done=function(){toast(okMsg||'已复制');};
  var fallback=function(){var ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);ta.select();try{document.execCommand('copy');done();}catch(e){toast('复制失败,请手动复制',true);}document.body.removeChild(ta);};
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(done).catch(fallback);}else{fallback();}
}
function toast(msg,isErr){
  var t=document.createElement('div');t.textContent=msg;
  t.style.cssText='position:fixed;bottom:86px;left:50%;transform:translateX(-50%);background:'+(isErr?'#FF3B30':'rgba(28,28,30,.92)')+';color:#fff;padding:10px 18px;border-radius:999px;font-size:14px;z-index:9999;box-shadow:0 4px 12px rgba(0,0,0,.2);transition:opacity .3s';
  document.body.appendChild(t);
  setTimeout(function(){t.style.opacity='0';setTimeout(function(){t.remove();},320);},1800);
}
/* 5 状态: loading / empty / error / confirm / normal */
var ST={
  layer:null,
  ensure:function(){
    if(this.layer)return this.layer;
    this.layer=document.createElement('div');
    this.layer.className='a08-layer';
    this.layer.innerHTML='<div class="a08-card"><div class="a08-icon" id="a08-icon"></div>'+
      '<div class="a08-title" id="a08-title"></div><div class="a08-msg" id="a08-msg"></div></div>';
    document.body.appendChild(this.layer);
    return this.layer;
  },
  show:function(type,title,msg,btns){
    var l=this.ensure();
    var icon='';var color='';
    if(type==='loading'){icon='<div class="a08-spinner"></div>';title=title||'加载中…';}
    else if(type==='empty'){icon='📭';title=title||'暂无数据';}
    else if(type==='error'){icon='⚠️';title=title||'出错了';color='color:#FF3B30';}
    else if(type==='confirm'){icon='❓';title=title||'确认操作';}
    else{icon='✅';title=title||'完成';}
    document.getElementById('a08-icon').innerHTML=icon;
    var t=document.getElementById('a08-title');t.innerHTML=esc(title);t.style.color='';
    if(type==='error')t.style.color='#FF3B30';
    document.getElementById('a08-msg').innerHTML=esc(msg||'');
    l.classList.add('show');
    this._buttons(btns||[]);
  },
  _buttons:function(btns){
    var l=this.layer;var old=l.querySelector('.a08-card .a08-btns');
    if(old)old.remove();
    if(!btns.length)return;
    var wrap=document.createElement('div');wrap.className='a08-btns';
    wrap.style.cssText='display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:6px';
    btns.forEach(function(b){
      var btn=document.createElement('button');
      btn.className='a08-btn '+(b.kind||'');
      btn.textContent=b.label;
      btn.onclick=function(){if(b.onclick)b.onclick();if(!b.keep)l.classList.remove('show');};
      wrap.appendChild(btn);
    });
    l.querySelector('.a08-card').appendChild(wrap);
  },
  hide:function(){if(this.layer)this.layer.classList.remove('show');}
};
/* 动作条: 复制数据(5 段 JSON)/ 复制日志(6 段) */
function bar(copyData,copyLog,extra){
  var wrap=document.createElement('div');
  wrap.className='a08-bar';
  var cd=copyData?JSON.stringify(copyData,null,2):'';
  var cl=copyLog?JSON.stringify(copyLog,null,2):'';
  var mk=function(label,text,kind){
    var b=document.createElement('button');b.className='a08-btn '+(kind||'');b.textContent=label;
    b.onclick=function(){copyText(text);};
    return b;
  };
  if(cd)wrap.appendChild(mk('📋 复制数据',cd,'dark'));
  if(cl)wrap.appendChild(mk('🧾 复制日志',cl));
  (extra||[]).forEach(function(e){wrap.appendChild(mk(e.label,e.text,e.kind||''));});
  document.body.appendChild(wrap);
}
window.A08={esc:esc,copyText:copyText,toast:toast,state:ST,bar:bar};
})();
"""

A08_PLACEHOLDER = "<!--INJECT-08-->"


def inject_08_layer(template_html: str, copy_data: dict, copy_log: dict,
                    extra_buttons: list = None) -> str:
    """把共享 08 动作层注入模板的 <!--INJECT-08--> 占位符(唯一 1 次)

    extra_buttons: [{label, text, kind}] 追加按钮(如「复制 prompt」)
    """
    count = template_html.count(A08_PLACEHOLDER)
    if count != 1:
        raise ValueError(f"占位符 {A08_PLACEHOLDER} 必须唯一 1 次,实际 {count} 次")

    payload = {
        "copy_data": copy_data,
        "copy_log": copy_log,
        "extra_buttons": extra_buttons or [],
    }
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str)
    payload_json = payload_json.replace("</", "<\\/")

    block = (
        "<style>" + A08_CSS + "</style>\n"
        "<script>window.__A08__ = " + payload_json + ";</script>\n"
        "<script>" + A08_JS + "</script>\n"
        "<script>window.A08.bar(window.__A08__.copy_data, window.__A08__.copy_log, window.__A08__.extra_buttons);</script>"
    )
    return template_html.replace(A08_PLACEHOLDER, block, 1)


def json_pretty(obj) -> str:
    """带缩进的 JSON(复制数据/日志内容)"""
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
