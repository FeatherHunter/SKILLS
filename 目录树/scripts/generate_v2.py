#!/usr/bin/env python3
"""
增强版目录树生成器
D:\2Study\StudyNotes\SKILLS\目录树\scripts\generate_v2.py

新增能力：
- 4K 墨烟背景图（可定制）
- Canvas 墨烟扩散动画
- 真实磨砂玻璃行材质
- 电路纹理装饰线
"""
import os, sys, time, json, zlib, base64, subprocess, re
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════
BG_COLOR = "#f6f5f1"
BG_IMAGE_B64 = None  # None = 用 CSS 渐变；str = base64 图片
BG_IMAGE_MIME = "image/jpeg"
INK_MIST_ANIMATION = True  # Canvas 墨烟动画

# ═══════════════════════════════════════════════════════════════
# 工具
# ═══════════════════════════════════════════════════════════════
def format_size(n):
    if not n: return ""
    if n < 1024: return f"{n}B"
    if n < 1048576: return f"{n//1024}KB"
    if n < 1073741824: return f"{n//1048576}MB"
    return f"{n//1073741824}GB"

def html_esc(s):
    s = str(s)
    s = s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    return s

def js_esc(s):
    s = str(s)
    s = s.replace("\\","\\\\").replace("'","\\'").replace("\n","\\n").replace("\r","")
    return s

def derive_output_name(root):
    parts = re.split(r"[/\\]", root.rstrip("/\\"))
    meaningful = [p for p in parts if p and not p.startswith(".")]
    if len(meaningful) >= 2: name = f"{meaningful[-2]}_{meaningful[-1]}"
    elif len(meaningful) == 1: name = meaningful[0]
    else: name = "root"
    name = re.sub(r'[<>:"/|?*]', "_", name)
    return f"{name}.html"

def resolve_root(root):
    p = root.strip().strip('"').strip("'")
    if p.startswith("/mnt/"): return p
    m = re.match(r"^([A-Za-z]):[/\\](.*)$", p)
    if m: return f"/mnt/{m.group(1).lower()}/{m.group(2).replace(chr(92),'/')}"
    return p

# ═══════════════════════════════════════════════════════════════
# Step 1: find 扫描
# ═══════════════════════════════════════════════════════════════
def scan(root, tmp_raw):
    print(f"[Step1] find {root}")
    t0 = time.time()
    with open(tmp_raw, "wb") as f:
        subprocess.Popen([
            "find", root, "-not", "-path", "*/.git/*",
            "-not", "-path", "*/node_modules/*", "-printf", "%y|%p|%s|%h\n"
        ], stdout=f, stderr=subprocess.DEVNULL).wait()
    count = sum(1 for _ in open(tmp_raw, "rb"))
    print(f"  → {count:,} entries in {time.time()-t0:.2f}s")
    return count

# ═══════════════════════════════════════════════════════════════
# Step 2: 解析
# ═══════════════════════════════════════════════════════════════
def parse(tmp_raw):
    print("[Step2] Parsing...")
    t0 = time.time()
    nodes = {}
    with open(tmp_raw, "rb") as f:
        for raw in f:
            parts = raw.decode("utf-8","replace").rstrip().split("|")
            if len(parts) < 4: continue
            kind, path = parts[0], parts[1]
            try: size = int(parts[2])
            except: size = 0
            si = path.rfind("/")
            name = path[si+1:] if si >= 0 else path
            nodes[path] = {"name":name,"path":path,"is_dir":kind.lower()=="d","size":size,"children":[]}
    for path in list(nodes):
        pi = path.rfind("/")
        parent = path[:pi] if pi >= 0 else ""
        if parent in nodes: nodes[parent]["children"].append(path)
    print(f"  → {len(nodes):,} nodes in {time.time()-t0:.2f}s")
    return nodes

def root_children(nodes, root):
    root_rstrip = root.rstrip("/")
    root_len = len(root_rstrip)
    rc = [p for p in nodes if p.startswith(root_rstrip+"/") and "/" not in p[root_len+1:]]
    rc.sort(key=lambda x: (not nodes[x]["is_dir"], nodes[x]["name"].lower()))
    return rc

def count_all(nodes, paths):
    c = 0
    for p in paths:
        c += 1
        if nodes[p]["is_dir"] and nodes[p]["children"]: c += count_all(nodes, nodes[p]["children"])
    return c

# ═══════════════════════════════════════════════════════════════
# Step 3: 压缩
# ═══════════════════════════════════════════════════════════════
def compress(nodes):
    print("[Step3] Compressing...")
    t0 = time.time()
    dir_lines = []
    for path, n in nodes.items():
        if n["is_dir"] and n["children"]:
            line = path + "\x00" + "\x00".join(n["children"])
            dir_lines.append(line)
    all_lines = "\n".join(dir_lines)
    compressed = zlib.compress(all_lines.encode("utf-8"), level=6)
    b64 = base64.b64encode(compressed).decode("ascii")
    print(f"  → raw={len(all_lines)/1024/1024:.1f}MB compressed={len(compressed)/1024/1024:.1f}MB b64={len(b64)/1024/1024:.1f}MB [{time.time()-t0:.2f}s]")
    return b64, len(all_lines), len(compressed)

# ═══════════════════════════════════════════════════════════════
# Step 4: 生成 HTML（含 Canvas 墨烟动画）
# ═══════════════════════════════════════════════════════════════
def build_html(root_children, nodes, compressed_b64, total, out_path, elapsed):
    print("[Step4] Building HTML...")
    t0 = time.time()

    # ── SVG 图标 ─────────────────────────────────────────────────────────────
    SVGF_CH = '<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2l4 3-4 3"/></svg>'
    SVGF_FO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a1 1 0 01-1 1H4a1 1 0 01-1-1V7z"/></svg>'
    SVGF_FI = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9M9 3l5 4v9a2 2 0 01-2 2H9M9 3v6"/></svg>'
    SVGF_CP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="10" height="10" rx="2"/><path d="M5 15V6a1 1 0 011-1h9"/></svg>'

    # ── 几何装饰 SVG（细线三角 + 同心圆）────────────────────────────────────
    SVG_GEO = (
        '<svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<line x1="100" y1="20" x2="20" y2="170" stroke="#c0c0b8" stroke-width="0.6"/>'
        '<line x1="100" y1="20" x2="180" y2="170" stroke="#c0c0b8" stroke-width="0.6"/>'
        '<line x1="20" y1="170" x2="180" y2="170" stroke="#c0c0b8" stroke-width="0.6"/>'
        '<circle cx="100" cy="100" r="22" stroke="#c8c8c0" stroke-width="0.5"/>'
        '<circle cx="100" cy="100" r="48" stroke="#c8c8c0" stroke-width="0.35"/>'
        '<circle cx="100" cy="100" r="72" stroke="#d0d0c8" stroke-width="0.25"/>'
        '<line x1="100" y1="100" x2="20" y2="60" stroke="#c8c8c0" stroke-width="0.3"/>'
        '<line x1="100" y1="100" x2="180" y2="60" stroke="#c8c8c0" stroke-width="0.3"/>'
        '<line x1="100" y1="100" x2="100" y2="20" stroke="#d0d0c8" stroke-width="0.3"/>'
        '<line x1="100" y1="100" x2="20" y2="140" stroke="#c0c0b8" stroke-width="0.3"/>'
        '<line x1="100" y1="100" x2="180" y2="140" stroke="#c0c0b8" stroke-width="0.3"/>'
        '</svg>'
    )

    # ── 电路纹理 SVG（书法笔触解构为电路线条）──────────────────────────────
    SVG_CIRCUIT = (
        '<svg viewBox="0 0 200 300" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M20 20 L80 20 L80 80 L140 80" stroke="#d0cfc8" stroke-width="0.5" stroke-linecap="round"/>'
        '<path d="M80 20 L80 80 L140 80" stroke="#c8c7c0" stroke-width="0.4"/>'
        '<circle cx="80" cy="20" r="2" fill="#d0cfc8"/>'
        '<circle cx="80" cy="80" r="2" fill="#c8c7c0"/>'
        '<path d="M20 100 L60 100 L60 150 L100 150 L100 200 L160 200" stroke="#d0cfc8" stroke-width="0.4"/>'
        '<circle cx="60" cy="100" r="1.5" fill="#d0cfc8"/>'
        '<circle cx="60" cy="150" r="1.5" fill="#c8c7c0"/>'
        '<circle cx="100" cy="150" r="1.5" fill="#c8c7c0"/>'
        '<circle cx="100" cy="200" r="2" fill="#c0bfb8"/>'
        '<path d="M20 240 L100 240 L100 270" stroke="#c8c7c0" stroke-width="0.35"/>'
        '<circle cx="100" cy="240" r="1.5" fill="#c8c7c0"/>'
        '</svg>'
    )

    # ── 远山剪影 SVG ──────────────────────────────────────────────────────────
    SVG_MTN = (
        '<svg viewBox="0 0 1440 110" preserveAspectRatio="none" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M0 82 Q90 48 180 68 Q270 88 360 55 Q450 25 540 60 Q630 85 720 50 '
        'Q810 18 900 52 Q990 78 1080 42 Q1170 10 1260 48 Q1350 75 1440 58 '
        'L1440 110 L0 110 Z" fill="#e4e3de" opacity="0.75"/>'
        '<path d="M0 92 Q120 68 240 85 Q360 98 480 75 Q600 52 720 80 Q840 95 960 70 '
        'Q1080 45 1200 78 Q1320 92 1440 78 L1440 110 L0 110 Z" '
        'fill="#deddd8" opacity="0.5"/>'
        '</svg>'
    )

    # ── 构建顶层 HTML ─────────────────────────────────────────────────────────
    def build_top():
        out = []
        for path in root_children:
            n = nodes[path]
            is_dir = n["is_dir"]
            children = n["children"]
            is_leaf = not is_dir or not children
            jp = js_esc(path)
            name = html_esc(n["name"])
            badge = (f'<span class="badge">{len(children)}</span>' if is_dir and children else "")
            meta = (f'<span class="meta">{format_size(n["size"])}</span>' if not is_dir else "")
            icon = SVGF_FO if is_dir else SVGF_FI
            nc = "nm-dir" if is_dir else "nm-fi"
            col = "#6a6a66" if is_dir else "#9e9e9a"
            ei = (f'<span class="ex">{SVGF_CH}</span>' if not is_leaf else '<span class="ex" style="visibility:hidden"></span>')
            cb = f'<button class="cp" onclick="window._dt_copy(\'{jp}\')">{SVGF_CP}<span>复制</span></button>'
            oc = (f'window._dt_toggle(\'{jp}\');event.stopPropagation();' if not is_leaf else "")
            ph = (f'<ul class="nl" data-path="{jp}"></ul>' if is_dir and children else "")
            out.append(
                f'<li class="ni" data-path="{jp}">\n'
                f'  <div class="nr" onclick="{oc}">\n'
                f'    {ei}\n'
                f'    <span class="ic" style="color:{col}">{icon}</span>\n'
                + (f'    {badge}\n' if badge else '') +
                f'    <span class="nn {nc}">{name}</span>\n'
                + (f'    {meta}\n' if meta else '') +
                f'    {cb}\n'
                f'  </div>\n'
                + (ph + '\n' if ph else '') +
                f'</li>'
            )
        return "\n".join(out)

    tree_html = build_top()

    # ── CSS（含 Canvas 墨烟动画）─────────────────────────────────────────────
    if BG_IMAGE_B64:
        bg_url = f"url(data:{BG_IMAGE_MIME};base64,{BG_IMAGE_B64})"
    else:
        # CSS fallback 墨烟纹理
        bg_url = (
            "radial-gradient(ellipse 60% 35% at 88% 5%,rgba(185,182,175,0.06) 0%,transparent 55%),"
            "radial-gradient(ellipse 90% 25% at 50% 95%,rgba(175,172,165,0.05) 0%,transparent 50%)"
        )

    CSS = f"""
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}

:root{{
  --bg:         {BG_COLOR};
  --ink:        #1c1b18;
  --ink-mid:    #5a5850;
  --ink-lt:      #a0a098;
  --ink-ghost:   #d8d6ce;
  --glass:       rgba(255,255,250,0.65);
  --glass-b:     rgba(180,178,170,0.32);
  --accent:      #7a9ab8;
  --accent-soft: rgba(100,140,180,0.1);
  --font:        'Geist','Satoshi',-apple-system,BlinkMacSystemFont,sans-serif;
  --font-mono:   'Geist Mono','JetBrains Mono','Fira Code',monospace;
  --r-sm:        5px;
  --r-md:        11px;
}}

html{{font-size:15px;}}
body{{
  background:var(--bg);background-image:{bg_url};background-size:cover;
  background-attachment:fixed;color:var(--ink);font-family:var(--font);
  min-height:100dvh;overflow-x:hidden;-webkit-font-smoothing:antialiased;
}}

/* 墨烟 Canvas 动画覆盖层 */
#ink-canvas{{
  position:fixed;top:0;left:0;width:100%;height:100%;
  pointer-events:none;z-index:2;opacity:0.35;mix-blend-mode:multiply;
}}

/* 远山剪影 */
.mountains{{position:fixed;bottom:0;left:0;right:0;height:88px;pointer-events:none;z-index:3;opacity:0.45;}}

/* 电路纹理装饰 */
.circuit{{position:fixed;top:50%;left:0;transform:translateY(-50%);height:60vh;
  pointer-events:none;z-index:3;opacity:0.25;}}

/* 两栏布局 */
.layout{{position:relative;z-index:10;display:grid;grid-template-columns:300px 1fr;min-height:100dvh;}}

/* 左面板 */
.panel-left{{
  position:sticky;top:0;height:100dvh;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:56px 48px;border-right:1px solid var(--ink-ghost);
}}
.panel-left-inner{{display:flex;flex-direction:column;align-items:center;gap:28px;}}
.geo-mark{{width:148px;height:148px;opacity:0.5;flex-shrink:0;}}
.circuit-mark{{width:120px;height:180px;opacity:0.4;flex-shrink:0;}}
.circuit-line{{width:1px;height:32px;
  background:linear-gradient(to bottom,transparent,var(--ink-ghost),transparent);}}
.panel-title{{text-align:center;}}
.panel-title-main{{
  font-size:10.5px;font-weight:400;letter-spacing:0.28em;text-transform:uppercase;
  color:var(--ink-lt);margin-bottom:10px;
}}
.panel-title-sub{{font-size:20px;font-weight:300;letter-spacing:0.08em;color:var(--ink-mid);line-height:1.6;}}
.panel-stats{{margin-top:14px;font-size:10.5px;font-family:var(--font-mono);
  color:var(--ink-lt);letter-spacing:0.07em;}}

/* 右面板 */
.panel-right{{padding:64px 64px 96px;min-height:100dvh;}}

/* 树 */
.tree{{list-style:none;}}
.nl{{display:none;padding-left:20px;list-style:none;position:relative;}}
.nl::before{{content:'';position:absolute;left:20px;top:0;bottom:8px;width:1px;background:var(--ink-ghost);}}
.ni{{position:relative;}}
.ni::before{{content:'';position:absolute;left:-20px;top:50%;width:20px;height:1px;background:var(--ink-ghost);}}
.ni.open>.nr>.ex{{transform:rotate(90deg);}}
.ni.open>.nl{{display:block;}}

/* 行：磨砂玻璃质感 */
.nr{{
  display:flex;align-items:center;gap:8px;padding:6px 12px;border-radius:var(--r-sm);
  cursor:pointer;user-select:none;border:1px solid rgba(180,178,170,0.18);
  background:rgba(255,255,252,0.55);backdrop-filter:blur(12px);
  box-shadow:0 1px 3px rgba(0,0,0,0.035),inset 0 1px 2px rgba(255,255,255,0.9),inset 0 -0.5px 0 rgba(180,178,170,0.08);
  transition:background 0.14s ease,border-color 0.14s ease,box-shadow 0.14s ease,transform 0.1s ease;
}}
.nr:hover{{
  background:rgba(255,255,252,0.78);border-color:rgba(180,178,170,0.3);
  box-shadow:0 0 0 1px rgba(180,178,170,0.1),inset 0 1px 4px rgba(255,255,255,0.95),inset 0 -0.5px 0 rgba(180,178,170,0.1);
}}
.nr:active{{transform:scale(0.99);}}

.ex{{width:16px;height:16px;flex-shrink:0;display:flex;align-items:center;justify-content:center;
    color:var(--ink-lt);transition:transform 0.22s cubic-bezier(0.16,1,0.3,1);}}
.ex svg{{width:9px;height:9px;}}
.ic{{width:18px;height:18px;flex-shrink:0;display:flex;align-items:center;justify-content:center;}}
.ic svg{{width:15px;height:15px;}}
.nn{{flex:1;font-size:13.5px;font-weight:400;letter-spacing:0.01em;
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;}}
.nm-dir{{color:var(--ink-mid);}}
.nm-fi{{color:var(--ink-lt);}}
.badge{{
  font-size:9.5px;font-family:var(--font-mono);padding:1px 5px;border-radius:4px;
  background:rgba(170,168,158,0.1);border:1px solid var(--ink-ghost);
  color:var(--ink-lt);white-space:nowrap;margin-right:2px;flex-shrink:0;letter-spacing:0.04em;
}}
.meta{{font-size:10.5px;font-family:var(--font-mono);color:var(--ink-lt);opacity:0;
    transition:opacity 0.15s;white-space:nowrap;margin-right:6px;}}
.nr:hover .meta{{opacity:1;}}

/* 复制按钮：冷调银蓝微光 */
.cp{{
  display:flex;align-items:center;gap:4px;padding:3px 9px;border-radius:var(--r-sm);
  border:1px solid var(--ink-ghost);background:rgba(255,255,250,0.6);
  color:var(--ink-lt);font-size:10px;font-family:var(--font-mono);cursor:pointer;opacity:0;
  transition:opacity 0.15s,color 0.15s,border-color 0.15s,box-shadow 0.15s;
  white-space:nowrap;flex-shrink:0;letter-spacing:0.04em;backdrop-filter:blur(10px);
}}
.nr:hover .cp{{opacity:1;}}
.cp:hover{{
  color:var(--accent);border-color:rgba(100,140,180,0.35);
  box-shadow:0 0 10px rgba(100,140,180,0.12),inset 0 0 6px rgba(100,140,180,0.05);
}}
.cp:active{{transform:scale(0.94);}}
.cp svg{{width:10px;height:10px;}}

/* toast */
.toast{{
  position:fixed;bottom:36px;left:50%;transform:translateX(-50%) translateY(14px);
  padding:8px 20px;border-radius:var(--r-md);font-size:11.5px;font-family:var(--font-mono);
  opacity:0;transition:opacity 0.2s,transform 0.2s cubic-bezier(0.16,1,0.3,1);
  pointer-events:none;z-index:1000;white-space:nowrap;letter-spacing:0.04em;
  backdrop-filter:blur(20px);border:1px solid var(--glass-b);
  background:rgba(255,255,250,0.88);color:var(--ink-mid);box-shadow:0 4px 20px rgba(0,0,0,0.055);
}}
.toast.show{{opacity:1;transform:translateX(-50%) translateY(0);}}
"""

    # ── JS ──────────────────────────────────────────────────────────────────
    JS = r"""
(function(){
  var expanded = new Set();
  var treeIndex = null;

  var SVGF_CH = '<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2l4 3-4 3"/></svg>';
  var SVGF_FO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a1 1 0 01-1 1H4a1 1 0 01-1-1V7z"/></svg>';
  var SVGF_FI = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9M9 3l5 4v9a2 2 0 01-2 2H9M9 3v6"/></svg>';
  var SVGF_CP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="10" height="10" rx="2"/><path d="M5 15V6a1 1 0 011-1h9"/></svg>';

  function init() {
    try {
      var bstr = atob(window.__treeData);
      var buf = new Uint8Array(bstr.length);
      for (var i = 0; i < bstr.length; i++) buf[i] = bstr.charCodeAt(i);
      var decompressed = new Uint8Array(pako.inflate(buf));
      var text = new TextDecoder().decode(decompressed);
      var lines = text.split('\n');
      treeIndex = {};
      for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        if (!line) continue;
        var nullIdx = line.indexOf('\x00');
        if (nullIdx < 0) continue;
        var parent = line.slice(0, nullIdx);
        var children = line.slice(nullIdx + 1).split('\x00').filter(Boolean);
        treeIndex[parent] = children;
      }
    } catch(e) { treeIndex = {}; }
  }

  function renderChildren(childPaths) {
    var out = [];
    for (var i = 0; i < childPaths.length; i++) {
      var path = childPaths[i];
      var slash = path.lastIndexOf('/');
      var name = slash >= 0 ? path.slice(slash + 1) : path;
      var childCount = treeIndex[path] ? treeIndex[path].length : 0;
      var isLeaf = childCount === 0;
      var jp = path.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
      var escName = name.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      var badge = (childCount > 0) ? '<span class="badge">' + childCount + '</span>' : '';
      var ei = !isLeaf ? '<span class="ex">' + SVGF_CH + '</span>' : '<span class="ex" style="visibility:hidden"></span>';
      var cb = '<button class="cp" onclick="window._dt_copy(\'' + jp + '\')">' + SVGF_CP + '<span>复制</span></button>';
      var oc = !isLeaf ? 'window._dt_toggle(\'' + jp + '\');event.stopPropagation();' : '';
      var ph = (!isLeaf) ? '<ul class="nl" data-path="' + jp + '"></ul>' : '';
      out.push('<li class="ni" data-path="' + jp + '">');
      out.push('  <div class="nr" onclick="' + oc + '">');
      out.push('    ' + ei);
      out.push('    <span class="ic" style="color:#9e9e9a">' + SVGF_FI + '</span>');
      if (badge) out.push('    ' + badge);
      out.push('    <span class="nn nm-fi">' + escName + '</span>');
      out.push('    ' + cb);
      out.push('  </div>');
      if (ph) out.push(ph);
      out.push('</li>');
    }
    return out.join('\n');
  }

  function toggle(path) {
    var item = document.querySelector('[data-path="' + path.replace(/\\/g, '\\\\') + '"]');
    if (!item) return;
    if (expanded.has(path)) {
      expanded.delete(path);
      item.classList.remove('open');
    } else {
      expanded.add(path);
      item.classList.add('open');
      var nested = item.querySelector('.nl');
      if (nested && !nested.innerHTML) {
        nested.innerHTML = renderChildren(treeIndex[path] || []);
      }
    }
    try { sessionStorage.setItem('dt_exp', JSON.stringify([...expanded])); } catch(e) {}
  }
  window._dt_toggle = toggle;

  window._dt_copy = async function(path) {
    try {
      await navigator.clipboard.writeText(path);
      showToast('\u5df2\u590d\u5236: ' + (path.length > 70 ? path.slice(0, 70) + '\u2026' : path));
    } catch(e) {
      showToast('\u590d\u5236\u5931\u8d25', true);
    }
  };

  function showToast(msg, isErr) {
    var t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = 'toast' + (isErr ? ' err' : '');
    t.classList.add('show');
    if (window._dt_tTimer) clearTimeout(window._dt_tTimer);
    window._dt_tTimer = setTimeout(function() { t.classList.remove('show'); }, 2500);
  }

  function restore() {
    try {
      var raw = sessionStorage.getItem('dt_exp');
      if (!raw) return;
      var saved = JSON.parse(raw);
      saved.forEach(function(p) {
        expanded.add(p);
        var item = document.querySelector('[data-path="' + p.replace(/\\/g, '\\\\') + '"]');
        if (item) {
          item.classList.add('open');
          var nested = item.querySelector('.nl');
          if (nested && !nested.innerHTML) {
            nested.innerHTML = renderChildren(treeIndex[p] || []);
          }
        }
      });
    } catch(e) {}
  }

  document.addEventListener('DOMContentLoaded', function() {
    init();
    restore();
    initInkAnimation();
  });

  // ── Canvas 墨烟扩散动画 ──────────────────────────────────────────────────
  function initInkAnimation() {
    var canvas = document.getElementById('ink-canvas');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var W, H;
    var particles = [];
    var t = 0;

    function resize() {
      W = canvas.width = window.innerWidth;
      H = canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    // 创建墨烟粒子
    function spawn() {
      var cx = W * (0.5 + Math.random() * 0.4);
      var cy = H * (0.1 + Math.random() * 0.3);
      for (var i = 0; i < 3; i++) {
        particles.push({
          x: cx + (Math.random() - 0.5) * 80,
          y: cy + (Math.random() - 0.5) * 30,
          vx: (Math.random() - 0.5) * 0.4,
          vy: Math.random() * 0.15 + 0.05,
          r: Math.random() * 180 + 80,
          opacity: Math.random() * 0.025 + 0.01,
          life: 0,
          maxLife: Math.random() * 400 + 300,
        });
      }
    }

    function draw() {
      ctx.clearRect(0, 0, W, H);
      t++;
      if (t % 8 === 0) spawn();

      for (var i = 0; i < particles.length; i++) {
        var p = particles[i];
        p.life++;
        p.x += p.vx;
        p.y += p.vy;
        var progress = p.life / p.maxLife;
        var curOp = p.opacity * (1 - Math.pow(progress, 1.5)) * (1 - progress * 0.5);
        var grd = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * (1 + progress * 0.3));
        grd.addColorStop(0, 'rgba(160,158,152,' + curOp + ')');
        grd.addColorStop(0.5, 'rgba(170,168,160,' + (curOp * 0.4) + ')');
        grd.addColorStop(1, 'rgba(180,178,170,0)');
        ctx.fillStyle = grd;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r * (1 + progress * 0.2), 0, Math.PI * 2);
        ctx.fill();
        if (p.life >= p.maxLife) { particles.splice(i, 1); i--; }
      }
      requestAnimationFrame(draw);
    }
    draw();
  }
})();
"""

    html = (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>StudyNotes \u00b7 目录导航</title>\n"
        "<style>\n" + CSS + "\n</style>\n"
        "</head>\n<body>\n"
        "<canvas id=\"ink-canvas\"></canvas>\n"
        "<div class=\"mountains\">" + SVG_MTN + "</div>\n"
        "<div class=\"circuit\"><div class=\"circuit-mark\">" + SVG_CIRCUIT + "</div></div>\n"
        "<div class=\"layout\">\n"
        "  <div class=\"panel-left\">\n"
        "    <div class=\"panel-left-inner\">\n"
        "      <div class=\"geo-mark\">" + SVG_GEO + "</div>\n"
        "      <div class=\"circuit-line\"></div>\n"
        "      <div class=\"panel-title\">\n"
        "        <div class=\"panel-title-main\">Directory Navigator</div>\n"
        "        <div class=\"panel-title-sub\">StudyNotes</div>\n"
        "      </div>\n"
        "      <div class=\"panel-stats\">" + f"{total:,} \u6761\u76ee \u00b7 {elapsed:.1f}s</div>\n"
        "    </div>\n"
        "  </div>\n"
        "  <div class=\"panel-right\">\n"
        "    <ul class=\"tree\">\n" + tree_html + "\n"
        "    </ul>\n"
        "  </div>\n"
        "</div>\n"
        "<div id=\"toast\" class=\"toast\"></div>\n"
        "<script>\n"
        "window.__treeData = " + repr(compressed_b64) + ";\n"
        + JS + "\n"
        "</script>\n"
        "<script src=\"https://cdnjs.cloudflare.com/ajax/libs/pako/2.1.0/pako.min.js\"></script>\n"
        "</body>\n</html>"
    )

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    sz = os.path.getsize(out_path)
    print(f"  → {sz/1024/1024:.2f}MB HTML in {time.time()-t0:.2f}s")
    return sz


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════
def main():
    if len(sys.argv) < 2:
        print("用法: python generate_v2.py /mnt/d/2Study/StudyNotes [bg_image.jpg]")
        sys.exit(1)

    root = resolve_root(sys.argv[1])
    bg_img = sys.argv[2] if len(sys.argv) > 2 else None

    global BG_IMAGE_B64
    if bg_img and os.path.exists(bg_img):
        with open(bg_img, "rb") as f:
            data = f.read()
        BG_IMAGE_B64 = base64.b64encode(data).decode()
        ext = os.path.splitext(bg_img)[-1].lower()
        BG_IMAGE_MIME = f"image/{'jpeg' if ext in ['.jpg','.jpeg'] else ext[1:]}"
        print(f"[Image] {bg_img} → {len(BG_IMAGE_B64)/1024:.1f}KB base64 embedded")
    elif bg_img:
        print(f"[WARN] Image not found: {bg_img}, using CSS fallback")

    if not os.path.isdir(root):
        print(f"错误: 路径不存在: {root}")
        sys.exit(1)

    output_name = derive_output_name(root)
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "directory-tree")
    out_path = os.path.join(docs_dir, output_name)

    tmp_raw = "/tmp/dir-tree-raw.txt"
    t_start = time.time()
    scan(root, tmp_raw)
    nodes = parse(tmp_raw)
    rc = root_children(nodes, root)
    b64, raw_sz, comp_sz = compress(nodes)
    total = count_all(nodes, rc)
    elapsed = time.time() - t_start
    build_html(rc, nodes, b64, total, out_path, elapsed)
    print(f"\n完成: {out_path}\n  总条目: {total:,} | 耗时: {elapsed:.1f}s")


if __name__ == "__main__":
    main()