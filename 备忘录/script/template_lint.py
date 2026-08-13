"""备忘录 templates/*.html 内嵌 JS 静态扫描(纯 Python,无 Node/npm 依赖)。

Seam 暴露 3 个独立 lint 入口 + 1 个 file-fan-out helper:

- lint_undefined_funcs(text) -> list[Finding]
    规则 1:inline `<script>` 内 `funcName(` 调用但文件内无 `function funcName` 定义 → 报警

- lint_escape_asymmetry(text) -> list[Finding]
    规则 2:`esc(...)` 调用输出 5 entity,但反序列化 `.replace(/&[#\\w]+;/g,...)` 处理
    的 entity 集合不全 → 报警

- lint_copy_fallback(text) -> list[Finding]
    规则 3:`<button class="...">` 节点无对应 `.addEventListener('click'` 或
    `onclick=` handler → 报警(违反总纲 §04 原则 10 HTML 单工铁律)

- lint_templates_dir(templates_path) -> dict[file_name, list[Finding]]
    整合入口,把规则 1+2+3 在 templates/ 下所有 .html 上跑一遍

为什么 Python 纯静态:
- 仓库是 Python 主导,引入 Node/npm 跨运行时
- slimit 等 Python 绑定维护弱
- 这三类规则本质是字符串/正则匹配够用,不必 AST

ADR 详见 docs/adr/0006-template-lint-infrastructure.md
"""
import re
from pathlib import Path
from typing import Iterable

# 5 个被 esc() 函数输出的 HTML entity(去前缀 & 去 ;)。详见总纲 §04 原则 4
ESC_ENTITY_SET = {"amp", "lt", "gt", "quot", "#39"}
ESC_ENTITY_PATTERN = re.compile(r"&(" + "|".join(re.escape(e) for e in ESC_ENTITY_SET) + r");")
# 反序列化 regex 通用形态(用于规则 2 检测 entity 集合)
REVERSE_RE_PATTERN = re.compile(r"/&\[#\\w\]+;/g")

# 白名单:globally-known 函数/对象,不计未定义
_GLOBAL_NAMESPACES = {
    "window", "document", "navigator", "console", "alert", "Object", "Array",
    "String", "JSON", "Math", "Promise", "localStorage", "sessionStorage",
    "history", "location", "setTimeout", "setInterval", "clearTimeout",
    "clearInterval", "parseInt", "parseFloat", "isNaN", "isFinite",
    "requestAnimationFrame", "fetch", "Promise", "Map", "Set",
    "Number", "Boolean", "Date", "Error", "RegExp", "Symbol", "Proxy",
    "Reflect", "WeakMap", "WeakSet",
}
# 已知作为 window.<X> 方法会被调用的,即使不用 window. 前缀也认作全局
_WINDOW_METHODS = {
    "scrollTo", "scrollBy", "scroll", "alert", "confirm", "prompt",
    "open", "close", "focus", "blur", "getComputedStyle",
    "getSelection", "requestAnimationFrame", "cancelAnimationFrame",
    "setTimeout", "setInterval", "clearTimeout", "clearInterval",
}
# DOM/系统方法可能漏写 window/document/navigator 前缀的(粗识别)
_DOM_METHODS = {
    "getElementById", "querySelector", "querySelectorAll",
    "addEventListener", "removeEventListener", "dispatchEvent",
    "classList", "writeText", "readText", "log", "warn", "error",
    "then", "catch", "finally", "JSON", "parse", "stringify",
    "filter", "map", "forEach", "reduce", "find", "findIndex",
    "indexOf", "includes", "slice", "split", "replace", "trim",
    "toLowerCase", "toUpperCase", "startsWith", "endsWith",
    "push", "pop", "shift", "unshift", "concat", "join",
    "setAttribute", "getAttribute", "removeAttribute",
    "appendChild", "removeChild", "insertBefore", "cloneNode",
    "preventDefault", "stopPropagation",
    # v1.1.5 扩展:Array / String / Object / Math / Date 全方法(粗识别)
    "isArray", "from", "of", "fill", "copyWithin",
    "match", "matchAll", "search", "normalize",
    "keys", "values", "entries", "assign", "create", "defineProperty",
    "freeze", "seal", "getPrototypeOf", "setPrototypeOf",
    "min", "max", "abs", "floor", "ceil", "round", "random", "sqrt",
    "pow", "log", "exp", "sin", "cos", "tan", "atan2",
    "now", "getTime", "getDate", "getDay", "getFullYear", "getMonth",
    "parse", "stringify", "decodeURI", "decodeURIComponent",
    "encodeURI", "encodeURIComponent",
    "closest", "matches", "scrollIntoView", "animate",
    "getBoundingClientRect", "contains",
    # v1.1.5+:memo_help 兼容(DOM 文档创建 + clipboard 兜底)
    "createElement", "createTextNode",
    # toast / 旧 inline fallbackCopy(memo_help.html 还保留一些旧形态)
    "toast", "showToast", "hideToast",
    # HTMLTextAreaElement / HTMLInputElement 旧 inline 形态
    "select", "execCommand", "rangeCount", "getSelection",
    # v1.1.5+:本仓库共享 clipboard helper(由 injector 注入)
    "safeWriteText", "flashBtn", "fallbackCopy",
    # v1.3.0+#299 Base 公共组件注入(base.js:esc/copyText/toast/状态层控件)
    "esc", "escapeHTML", "copyText", "buildDataText", "buildLogText",
    "emptyState", "errorReceipt", "actionBar", "statusBadge", "foldBox",
    "formPrompt", "selectList", "arr", "val", "yes", "validate", "metaHeader",
    # v1.1.5+:DOM 元素方法(classList.toggle 等)
    "toggle", "add", "remove", "replace",
    # v1.1.5+:Array.prototype 方法补全
    "sort", "reverse", "every", "some", "flat", "flatMap", "fill",
}


def _is_known_global(name: str) -> bool:
    """识别名字是否属于 JS 全局(浏览器/语言内置)。"""
    if name in _GLOBAL_NAMESPACES or name in _WINDOW_METHODS or name in _DOM_METHODS:
        return True
    return False


def _strip_script_blocks(html: str) -> Iterable[tuple[int, str]]:
    """逐 `<script>` 块返回 (start_line, body_text)。"""
    line_counter = 0
    open_idx = 0
    while True:
        m = re.search(r"<script[^>]*>", html[open_idx:], re.IGNORECASE)
        if not m:
            return
        body_start = open_idx + m.end()
        close = html.lower().find("</script>", body_start)
        if close < 0:
            return
        body = html[body_start:close]
        # 计算行号:从原始 html 头到 body_start 的换行数
        line_counter = html.count("\n", 0, body_start) + 1
        yield (line_counter, body)
        open_idx = close + len("</script>")


def _defined_function_names(text: str) -> set[str]:
    """提取 `<script>` 内 `function name(` 定义集合(包含赋给 var/const/let 的函数表达式)。"""
    names = set(re.findall(r"function\s+(\w+)\s*\(", text))
    names |= set(re.findall(r"(?:const|let|var)\s+(\w+)\s*=\s*function", text))
    names |= set(re.findall(r"(?:const|let|var)\s+(\w+)\s*=\s*\(", text))
    names |= set(re.findall(r"(\w+)\s*=\s*function", text))
    return names


def lint_undefined_funcs(html: str) -> list[dict]:
    """规则 1:inline `<script>` 内调用函数未在文件内定义 → 报警。

    v1.1.5:定义集合跨所有 <script> 块合并提取(模板内多 script 块时,
    块 A 的 function 定义对块 B 的调用是合法的)。
    """
    findings = []
    # 先把所有 script 块合并成一个 body 收集定义集合
    all_bodies = " ".join(b for _, b in _strip_script_blocks(html))
    global_defined = _defined_function_names(all_bodies)
    for start_line, body in _strip_script_blocks(html):
        # 块内定义 + 全局定义合并
        defined = _defined_function_names(body) | global_defined
        # 提取 `name(` 调用
        # 排除 .method() / 'string calls' / 关键字 / 数字
        # 模式:[边界字符] + 标识符 + 空白? + (
        # v1.1.5:跳过字符串字面('...' / "...")内部的 `(` — 防止 prompt 文案里的
        # `complete-wish(` `set-due(` `batch-update-category(` 等命令名字面触发误报
        # 粗略处理:把字符串字面整段替换成等长空格,保留行号偏移但不报警
        scrubbed = re.sub(r"'[^'\n]*'|\"[^\"\n]*\"", lambda m: " " * len(m.group(0)), body)
        calls = re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", scrubbed)
        # 去重保序
        seen = set()
        ordered = []
        for c in calls:
            if c not in seen:
                seen.add(c)
                ordered.append(c)
        for call in ordered:
            if call in defined:
                continue
            # 跳过全局/内置/白名单
            if _is_known_global(call):
                continue
            # 跳过疑似属性(.method 调用因 regex 已剥离前缀不命中)或纯别名
            # 跳过 JS 关键字
            if call in {"if", "for", "while", "switch", "return", "typeof", "new", "throw",
                        "try", "catch", "function", "var", "let", "const", "class",
                        "this", "true", "false", "null", "undefined"}:
                continue
            # 找到调用在 body 里的行号
            line_offset = body[:body.find(call + "(")].count("\n")
            findings.append({
                "rule": "undefined_func",
                "line": start_line + line_offset,
                "name": call,
                "msg": f"未定义函数调用: {call}()",
            })
    return findings


def lint_escape_asymmetry(html: str) -> list[dict]:
    """规则 2:`esc(...)` 输出 entity 集合 vs 反序列化 regex 实体集合,前者超过后者 → 报警。"""
    findings = []
    for start_line, body in _strip_script_blocks(html):
        # 是否有 esc 调用?
        if "esc(" not in body and "escapeHTML(" not in body:
            continue
        # 反序列化 regex:扫描所有 `.replace(/&XXX;/g, '...')` 形式,以及链式
        # `.replace(/&lt;/g, '<').replace(/&gt;/g, '>')` 形式 — 任一形态都累加 entity 集合
        reverse_entities: set[str] = set()

        # 形态 1:链式 replace,每个只处理 1 个 entity
        single_replaces = re.findall(r"\.replace\(\s*/&([a-z0-9#]+);/g", body)
        for e in single_replaces:
            reverse_entities.add(e)
        # 形态 2:聚合式 regex `/&[#\\w]+;/g`(占位无法知道具体覆盖哪些,需用规则 2 反解才能知道)
        # 形态 2 在 lint 看来"集合不可知",所以不加入已知集合(保守,只算 1 的字面)
        # 这意味:用了 .replace(/&[#\\w]+;/g, X) 的反向写法,lint 不报警(警觉但不引发报警)
        # 但如果同时还有显式 replace 字面,可以两个一起算
        # 如果没有反序列化 regex → 没有不对称问题可查(不报警)
        if not reverse_entities:
            continue
        missing = ESC_ENTITY_SET - reverse_entities
        if missing:
            findings.append({
                "rule": "escape_asymmetry",
                "line": start_line,
                "msg": f"esc 转义 5 entity ({sorted(ESC_ENTITY_SET)}),"
                       f"反序列化只处理 ({sorted(reverse_entities)}) — 不对称,"
                       f"缺少: {sorted(missing)}。这会导致用户备忘含 < 等字符时"
                       f"反解失败 → 静默 catch → 用户感知到'复制失败'",
            })
    return findings


def lint_copy_fallback(html: str) -> list[dict]:
    """规则 3:`<button ...>` 节点无 click handler → 报警(违反 HTML 单工铁律)。"""
    findings = []
    # 在整文件层面提取所有 button 的 class 列表
    button_pattern = re.compile(
        r"<button\b[^>]*class=[\"']([^\"']+)[\"'][^>]*>",
        re.IGNORECASE,
    )
    buttons = button_pattern.findall(html)
    if not buttons:
        return findings
    # 在 <script> 内提取所有 handler 引用
    script_text = " ".join(b for _, b in _strip_script_blocks(html))
    handlers = set()
    # onclick= 字面
    handlers |= set(re.findall(r'onclick\s*=\s*[\"\']([^\"\'(]+)\(', html))
    # .addEventListener('click', ...) / "click"
    handlers |= set(re.findall(r"addEventListener\s*\(\s*['\"]click['\"]", script_text))
    # 提取通过 .class 调用(粗糙判定:handler 提到任一 button class 即对应)
    # 对每个 button class,检查是否出现在 <script> 的 querySelector / click 关联
    for cls_raw in buttons:
        # class 可能含多类,任一匹配即视为有 handler(粗糙识别)
        classes = cls_raw.split()
        for cls in classes:
            if cls in script_text:
                # 进一步粗过滤:必须在 click / onclick 上下文出现
                ctx_pattern = re.compile(
                    rf"\.(?:{re.escape(cls)})[^\n;]{{0,80}}(?:onclick|click|addEventListener)",
                    re.IGNORECASE,
                )
                if ctx_pattern.search(html) or f"onclick" in cls:
                    break
        else:
            # 没有任何 class 出现在 click / onclick 上下文 → 报警
            # 简化:如果 button class 出现 querySelector + click 已守住;否则报警
            # 取 button 字面所在行号
            line_no = html[: html.find(f'class="{cls_raw}"')].count("\n") + 1
            findings.append({
                "rule": "copy_fallback",
                "line": line_no,
                "source": f'<button class="{cls_raw}">',
                "msg": f"<button class='{cls_raw}'> 节点无明显 click handler "
                       f"(违反总纲 §04 原则 10 HTML 单工铁律:过程型 HTML 按钮必须有"
                       f"复制路径或 navigator.clipboard fallback)",
            })
    return findings


def lint_templates_dir(templates_path: Path) -> dict[str, list[dict]]:
    """整合入口:跑规则 1+2+3,返回 {filename: findings_list}。"""
    templates_path = Path(templates_path)
    out = {}
    for f in sorted(templates_path.glob("*.html")):
        text = f.read_text(encoding="utf-8")
        findings = (lint_undefined_funcs(text)
                    + lint_escape_asymmetry(text)
                    + lint_copy_fallback(text))
        if findings:
            out[f.name] = findings
    return out
