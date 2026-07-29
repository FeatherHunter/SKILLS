/* 共享 clipboard helper · 单一真相源
 *
 * 由 injector.py 在 render 阶段 inline 注入到所有 templates/ 模板(占位符
 * <!--INJECT-SHARED-->)。任何模板都不应再 inline 重复实现 fallbackCopy /
 * copyTimer · 修改只改此文件即可全局生效。
 *
 * 设计要点:
 * - copyTimer 全局变量 · 防 btn 文字 timer race(连续采纳/复制时)
 * - fallbackCopy(text) 用 textarea + document.execCommand('copy') 兜底
 *   防 navigator.clipboard.writeText 在飞书 webview 等环境下被拒
 * - 调用方式:任意模板的 <button onclick="..."> 或 .addEventListener('click')
 *   内直接调 fallbackCopy(text) / 操作 copyTimer
 */
var copyTimer = null;

function fallbackCopy(text) {
    try {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;left:-9999px;top:0';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        var ok = false;
        try {
            ok = document.execCommand('copy');
        } catch (e) {
            ok = false;
        }
        document.body.removeChild(ta);
        return ok;
    } catch (e) {
        return false;
    }
}

/* 安全包装:navigator.clipboard.writeText 失败时自动 fallback。
 * 返回 Promise<boolean>:成功 true,失败 false(让调用方决定如何 UI 反馈)
 */
function safeWriteText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text).then(function () {
            return true;
        }).catch(function () {
            return fallbackCopy(text);
        });
    }
    return Promise.resolve(fallbackCopy(text));
}

/* 简化 btn 文字反馈 · 配合 safeWriteText 使用:
 *   safeWriteText(text).then(function(ok){
 *     if(ok){ flashBtn(btn, '✓ 已复制', 2000) }
 *     else { flashBtn(btn, '✗ 复制失败', 2000) }
 *   })
 */
function flashBtn(btn, msg, ms) {
    if (!btn) return;
    if (copyTimer) { clearTimeout(copyTimer); }
    var old = btn.textContent;
    btn.textContent = msg;
    copyTimer = setTimeout(function () { btn.textContent = old; }, ms || 2000);
}