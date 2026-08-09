/* 作息管家 · 复制 prompt 共享 helper(ADR-0002 Q6 · 总纲 §04 原则 10)
 *
 * 第一性:多个 HTML 模板(record 域 6 模板经 _record_engine.js,plan 域
 * schedule_list_events.html 独立)都需要"复制 4 部分 prompt"按钮 + 剪贴板
 * 降级 + 复制成功反馈。把同一份逻辑抄两遍 = 改一处忘另一处就出 bug,
 * 所以抽到本文件,所有模板末尾引用本文件(共享唯一一份逻辑)。
 *
 * 用法:
 *   1. 模板 <head> 或 <body> 末尾加本文件引用
 *   2. 模板渲染时调 CopyPromptHelper.renderBlock(data.copy_prompt) 拼到 html
 *   3. 模板渲染完调 CopyPromptHelper.bind() 绑定点击事件(全局事件代理,
 *      .copy-prompt-btn class + data-copy-prompt 属性,避免 id 冲突)
 *
 * 数据契约:HTML 含 id="payload" 的 JSON script 块(id 值 = payload.data),
 *          payload.data.copy_prompt 字段是 4 部分文本
 */
window.CopyPromptHelper = (function(){
  "use strict";

  var PREVIEW_CAP = 200;        // 预览字符数上限
  var RESET_DELAY_MS = 2200;    // 复制后按钮回退延迟

  function escapeHTML(s){
    return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){
      return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c];
    });
  }

  // 渲染复制 prompt 区(返回 HTML 字符串,不含 <script>)
  function renderBlock(copyPrompt){
    if (!copyPrompt) return "";
    var text = String(copyPrompt);
    var preview = text.substring(0, PREVIEW_CAP);
    if (text.length > PREVIEW_CAP) preview += "…";
    return '<div class="card copy-prompt-zone" style="background:linear-gradient(180deg,#f0f4ff 0%,#fff 100%);border:2px solid var(--blue);border-radius:14px;padding:18px 20px;margin:12px 0">' +
             '<div style="display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap">' +
               '<div style="flex:1;min-width:200px">' +
                 '<h3 style="font-size:15px;font-weight:700;color:var(--fg);margin-bottom:6px">📋 复制 4 部分 prompt 给 AI</h3>' +
                 '<pre class="copy-preview" style="background:#fff;border:1px dashed var(--line);border-radius:8px;padding:8px 12px;font-size:11.5px;color:var(--fg2);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;line-height:1.55;max-height:80px;overflow:auto;white-space:pre-wrap;margin:0">' + escapeHTML(preview) + '</pre>' +
               '</div>' +
               '<button class="copy-prompt-btn" type="button" data-copy-prompt="1" style="background:var(--blue);color:#fff;border:none;padding:12px 20px;border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;white-space:nowrap">复制完整 prompt</button>' +
             '</div>' +
           '</div>';
  }

  // 复制到剪贴板(带 fallback)
  function copyText(text, onDone, onFail){
    function fallback(){
      try {
        var ta = document.createElement("textarea");
        ta.value = text;
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        if (onDone) onDone();
      } catch(err){
        if (onFail) onFail(err);
      }
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(onDone).catch(fallback);
    } else {
      fallback();
    }
  }

  // 按钮视觉反馈:变绿 → RESET_DELAY_MS 后回退
  function flashButton(btn){
    if (!btn) return;
    var orig = btn.textContent;
    btn.textContent = "✅ 已复制 · 粘贴给 AI";
    btn.style.background = "var(--good)";
    setTimeout(function(){
      btn.textContent = orig || "复制完整 prompt";
      btn.style.background = "var(--blue)";
    }, RESET_DELAY_MS);
  }

  // 从最近的 <script id="payload"> 读 data.copy_prompt
  function readCopyPromptFromPayload(){
    var el = document.getElementById("payload");
    if (!el) return "";
    try {
      var p = JSON.parse(el.textContent || "{}");
      return (p && p.data && p.data.copy_prompt) || "";
    } catch(err){
      return "";
    }
  }

  // 全局事件代理:点 .copy-prompt-btn → 复制 payload.data.copy_prompt
  // 注意:只读 #payload 里的 copy_prompt,避免依赖全局变量(支持多模板)
  function bind(){
    document.addEventListener("click", function(e){
      var btn = e.target && e.target.closest ? e.target.closest(".copy-prompt-btn") : null;
      if (!btn) return;
      var text = btn.getAttribute("data-copy-text") || readCopyPromptFromPayload();
      if (!text) return;
      copyText(text, function(){ flashButton(btn); }, function(){
        btn.textContent = "✗ 复制失败";
        btn.style.background = "var(--danger)";
      });
    });
  }

  // 自动绑定(脚本加载即注册,幂等)
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }

  return {
    renderBlock: renderBlock,
    copyText: copyText,
    flashButton: flashButton,
    bind: bind,
    PREVIEW_CAP: PREVIEW_CAP,
    RESET_DELAY_MS: RESET_DELAY_MS,
  };
})();
