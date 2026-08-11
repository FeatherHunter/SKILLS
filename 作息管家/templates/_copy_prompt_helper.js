/* 作息管家 · 复制 prompt 共享 helper（ADR-0002 Q6 · 总纲 §04 原则 10）
 *
 * #269 Base 试点改造（2026-08-11 用户拍板）:
 * - 复制动作统一走 Base copyText(v2: 按钮文字恒定 + toast 反馈)
 * - 原自研 copyText/fallbackCopy/flashButton 变绿反馈已删除（Base 契约: 按钮文字恒定,
 *   反馈走独立 Toast「已复制 · 粘贴给 AI」/「复制失败 · 长按选择文本手动复制」）
 * - 本文件只保留「渲染复制 prompt 按钮块」逻辑;点击绑定委托 Base copyText
 *
 * 第一性:多个 HTML 模板(record 域 6 模板经 _record_engine.js,plan 域
 * schedule_list_events.html 独立)都需要"复制 4 部分 prompt"按钮。逻辑抽到本文件
 * 共享唯一一份,所有模板末尾引用本文件。
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
                 '<pre class="copy-preview" style="background:#fff;border:1px dashed var(--line);border-radius:8px;padding:8px 12px;font-size:11.5px;color:var(--fg2);font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;line-height:1.55;max-height:80px;overflow:auto;white-space:pre-wrap;margin:0;word-break:break-all">' + escapeHTML(preview) + '</pre>' +
               '</div>' +
               '<button class="copy-prompt-btn" type="button" data-copy-prompt="1" style="background:var(--blue);color:#fff;border:none;padding:12px 20px;border-radius:10px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;white-space:nowrap">复制完整 prompt</button>' +
             '</div>' +
           '</div>';
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
  // 复制动作 = Base copyText(v2: 按钮文字恒定 + toast 反馈, 不改按钮文字)
  function bind(){
    document.addEventListener("click", function(e){
      var btn = e.target && e.target.closest ? e.target.closest(".copy-prompt-btn") : null;
      if (!btn) return;
      var text = btn.getAttribute("data-copy-text") || readCopyPromptFromPayload();
      if (!text) return;
      // Base copyText: clipboard + fallback + 成功/失败双 toast,按钮文字恒定
      if (window.copyText) {
        window.copyText(text);
      } else {
        // 极端兜底:Base 未注入时自研复制(仅复制,无 toast)——正常情况 Base 必已注入
        try {
          var ta = document.createElement("textarea");
          ta.value = text;
          ta.style.position = "fixed";
          ta.style.left = "-9999px";
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
        } catch(err){}
      }
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
    bind: bind,
    PREVIEW_CAP: PREVIEW_CAP,
  };
})();
