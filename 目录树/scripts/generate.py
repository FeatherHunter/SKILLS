#!/usr/bin/env python3
"""
目录树生成器 - neo-Zen Light 版
D:\2Study\StudyNotes\SKILLS\目录树\scripts\generate.py

用法:
    python generate.py "/mnt/d/2Study/StudyNotes"
    python generate.py "/mnt/d/Work/Projects"
    python generate.py "D:\MyFolder"       (Windows path)

输出:
    docs/directory-tree/[ROOT_NAME].html
    同时写入 scripts/.last_scan_record 记录本次扫描元信息

样式: 单色米白背景 #f6f5f1，neo-Zen 新禅意科技美学
技术: find + zlib压缩 + lazy render，10万+条目专用优化
依赖: pako (CDN), 无需服务器
"""
import os
import sys
import time
import json
import zlib
import base64
import subprocess
import re
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# 配置
# ══════════════════════════════════════════════════════════════════════════════

# 大数据量阈值（条目），超过则启用压缩 lazy render 模式
LARGE_DIR_THRESHOLD = 50_000

# 样式主题: neo-Zen Light
BG_COLOR = "#f6f5f1"
ACCENT_COLOR = "#7a9ab8"

# ══════════════════════════════════════════════════════════════════════════════
# 工具函数
# ══════════════════════════════════════════════════════════════════════════════

def format_size(n: int) -> str:
    """人类可读文件大小"""
    if not n:
        return ""
    if n < 1024:
        return f"{n}B"
    if n < 1048576:
        return f"{n//1024}KB"
    if n < 1073741824:
        return f"{n//1048576}MB"
    return f"{n//1073741824}GB"


def html_esc(s: str) -> str:
    """HTML 实体转义"""
    s = str(s)
    s = s.replace("&", "&amp;")
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    return s


def js_esc(s: str) -> str:
    """JS 字符串字面量转义"""
    s = str(s)
    s = s.replace("\\", "\\\\")
    s = s.replace("'", "\\'")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    return s


def derive_output_name(root_path: str) -> str:
    """
    根据根目录派生输出文件名
    /mnt/d/2Study/StudyNotes         → 2Study_StudyNotes.html
    /mnt/d/Work/Projects             → Work_Projects.html
    D:\Work\Projects                  → Work_Projects.html
    """
    root = root_path.rstrip("/\\")
    parts = re.split(r"[/\\]", root)
    # 取最后两个有意义段
    meaningful = [p for p in parts if p and not p.startswith(".")]
    if len(meaningful) >= 2:
        name = f"{meaningful[-2]}_{meaningful[-1]}"
    elif len(meaningful) == 1:
        name = meaningful[0]
    else:
        name = "root"
    # 清理特殊字符
    name = re.sub(r'[<>:"/|?*]', "_", name)
    return f"{name}.html"


def resolve_root_path(input_path: str) -> str:
    """把 Windows 路径转换为 WSL 内部路径格式"""
    p = input_path.strip().strip('"').strip("'")
    # 如果是 /mnt/d/ 格式直接返回
    if p.startswith("/mnt/"):
        return p
    # Windows 盘符: D:\... → /mnt/d/...
    m = re.match(r"^([A-Za-z]):[/\\](.*)$", p)
    if m:
        drive = m.group(1).lower()
        rest = m.group(2).replace("\\", "/")
        return f"/mnt/{drive}/{rest}"
    # 已经是 Unix 风格路径
    return p


# ══════════════════════════════════════════════════════════════════════════════
# Step 1: find 流式扫描
# ══════════════════════════════════════════════════════════════════════════════

def scan_with_find(root: str, tmp_raw: str) -> int:
    """
    用 find 命令流式输出到文件，绕过 Python os.walk 在 WSL DrvFs 上的超时问题。
    输出格式: kind|name|path|size|parent
    返回扫描到的总条目数。
    """
    print(f"[Step 1] find {root} → {tmp_raw}")
    t0 = time.time()
    cmd = [
        "find", root,
        "-not", "-path", "*/.git/*",
        "-not", "-path", "*/node_modules/*",
        "-printf", "%y|%p|%s|%h\n"
    ]
    with open(tmp_raw, "wb") as f:
        proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.DEVNULL)
        proc.wait()
    count = sum(1 for _ in open(tmp_raw, "rb"))
    print(f"  find done: {count:,} entries in {time.time()-t0:.2f}s")
    return count


# ══════════════════════════════════════════════════════════════════════════════
# Step 2: 快速解析（不做路径操作，只字符串 split）
# ══════════════════════════════════════════════════════════════════════════════

def parse_raw_file(tmp_raw: str) -> tuple[dict, list]:
    """
    解析 find 输出，构建 nodes dict。
    返回: (nodes dict, root_children list of paths)
    """
    print("[Step 2] Parsing...")
    t0 = time.time()
    nodes = {}
    with open(tmp_raw, "rb") as f:
        for raw in f:
            line = raw.decode("utf-8", errors="replace").rstrip("\n")
            if not line:
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            kind = parts[0]
            path = parts[1]
            try:
                size = int(parts[2])
            except ValueError:
                size = 0
            si = path.rfind("/")
            name = path[si+1:] if si >= 0 else path
            nodes[path] = {
                "name": name,
                "path": path,
                "is_dir": kind.lower() == "d",
                "size": size,
                "children": [],
            }

    # 构建 children 引用
    for path in list(nodes.keys()):
        pi = path.rfind("/")
        parent = path[:pi] if pi >= 0 else ""
        if parent in nodes:
            nodes[parent]["children"].append(path)

    # 找根目录的直接子节点
    root = "/mnt/d/2Study/StudyNotes"  # caller overrides this
    # 发现 root 可能不在 nodes 里（find 输出根目录本身）
    # 用更通用的方式：找所有 path 的直接子节点
    # 即: path.startswith(root+"/") and "/" not in path[len(root)+1:]
    # caller 会重新计算 root_children
    print(f"  parsed {len(nodes):,} nodes in {time.time()-t0:.2f}s")
    return nodes, []


def build_root_children(nodes: dict, root: str) -> list:
    """找根目录的直接子节点（深度=1）"""
    root_rstrip = root.rstrip("/")
    root_len = len(root_rstrip)
    rc = [
        p for p in nodes
        if p.startswith(root_rstrip + "/")
        and "/" not in p[root_len+1:]
    ]
    rc.sort(key=lambda x: (not nodes[x]["is_dir"], nodes[x]["name"].lower()))
    return rc


def count_all(nodes: dict, paths: list) -> int:
    """递归统计总条目数"""
    c = 0
    for p in paths:
        c += 1
        if nodes[p]["is_dir"] and nodes[p]["children"]:
            c += count_all(nodes, nodes[p]["children"])
    return c


# ══════════════════════════════════════════════════════════════════════════════
# Step 3: 压缩树数据
# ══════════════════════════════════════════════════════════════════════════════

def compress_tree(nodes: dict, root_children: list) -> tuple[str, int, int]:
    """
    将树结构压缩为一行一目录的字符串，用 \\x00 分隔父子。
    返回: (base64 encoded compressed string, raw size, compressed size)
    """
    print("[Step 3] Compressing tree data...")
    t0 = time.time()
    dir_lines = []
    for path, n in nodes.items():
        if n["is_dir"] and n["children"]:
            line = path + "\x00" + "\x00".join(n["children"])
            dir_lines.append(line)
    all_lines = "\n".join(dir_lines)
    raw_size = len(all_lines.encode("utf-8"))
    compressed = zlib.compress(all_lines.encode("utf-8"), level=6)
    compressed_b64 = base64.b64encode(compressed).decode("ascii")
    print(f"  raw={raw_size/1024/1024:.1f}MB → compressed={len(compressed)/1024/1024:.1f}MB "
          f"→ b64={len(compressed_b64)/1024/1024:.1f}MB in {time.time()-t0:.2f}s")
    return compressed_b64, raw_size, len(compressed)


# ══════════════════════════════════════════════════════════════════════════════
# Step 4: 生成 HTML
# ══════════════════════════════════════════════════════════════════════════════

def build_html(
    root_children: list,
    nodes: dict,
    compressed_b64: str,
    total: int,
    output_path: str,
    elapsed_scan: float,
) -> None:
    """生成完整 HTML 文件"""
    print("[Step 4] Building HTML...")
    t0 = time.time()

    # ── SVG 资源 ──────────────────────────────────────────────────────────────
    SVG_CH = ('<svg viewBox="0 0 10 10" fill="none" stroke="currentColor" '
              'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
              '<path d="M3 2l4 3-4 3"/></svg>')
    SVG_FO = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
              '<path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a1 1 0 01-1 1H4a1 1 0 01-1-1V7z"/></svg>')
    SVG_FI = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
              '<path d="M9 3H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9M9 3l5 4v9a2 2 0 01-2 2H9M9 3v6"/></svg>')
    SVG_CP = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">'
              '<rect x="9" y="9" width="10" height="10" rx="2"/>'
              '<path d="M5 15V6a1 1 0 011-1h9"/></svg>')

    # 单线条三角 + 同心圆（居中几何体）
    SVG_GEO = (
        '<svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">'
        '<line x1="100" y1="20" x2="20" y2="170" stroke="#b8b8b0" stroke-width="0.6"/>'
        '<line x1="100" y1="20" x2="180" y2="170" stroke="#b8b8b0" stroke-width="0.6"/>'
        '<line x1="20" y1="170" x2="180" y2="170" stroke="#b8b8b0" stroke-width="0.6"/>'
        '<circle cx="100" cy="100" r="22" stroke="#c0c0b8" stroke-width="0.5"/>'
        '<circle cx="100" cy="100" r="48" stroke="#c8c8c0" stroke-width="0.35"/>'
        '<circle cx="100" cy="100" r="72" stroke="#d0d0c8" stroke-width="0.25"/>'
        '<line x1="100" y1="100" x2="100" y2="20" stroke="#c0c0b8" stroke-width="0.4"/>'
        '<line x1="100" y1="100" x2="20" y2="170" stroke="#c0c0b8" stroke-width="0.4"/>'
        '<line x1="100" y1="100" x2="180" y2="170" stroke="#c0c0b8" stroke-width="0.4"/>'
        '<line x1="100" y1="100" x2="20" y2="60" stroke="#c8c8c0" stroke-width="0.3"/>'
        '<line x1="100" y1="100" x2="180" y2="60" stroke="#c8c8c0" stroke-width="0.3"/>'
        '<line x1="100" y1="100" x2="100" y2="20" stroke="#d0d0c8" stroke-width="0.3"/>'
        '</svg>'
    )

    # 远山剪影（远红外热感成像风格）
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

    # ── 构建顶层节点 HTML ──────────────────────────────────────────────────────
    def build_top_nodes() -> str:
        out = []
        for path in root_children:
            n = nodes[path]
            is_dir = n["is_dir"]
            children = n["children"]
            is_leaf = not is_dir or not children
            jp = js_esc(path)
            name = html_esc(n["name"])
            badge = (f'<span class="badge">{len(children)}</span>'
                     if is_dir and children else "")
            meta = (f'<span class="meta">{format_size(n["size"])}</span>'
                    if not is_dir else "")
            icon = SVG_FO if is_dir else SVG_FI
            nc = "nm-dir" if is_dir else "nm-fi"
            col = "#6a6a66" if is_dir else "#9e9e9a"
            ei = (f'<span class="ex">{SVG_CH}</span>'
                  if not is_leaf else '<span class="ex" style="visibility:hidden"></span>')
            cb = (f'<button class="cp" onclick="window._dt_copy(\'{jp}\')">'
                  f'{SVG_CP}<span>复制</span></button>')
            oc = (f'window._dt_toggle(\'{jp}\');event.stopPropagation();'
                  if not is_leaf else "")
            ph = (f'<ul class="nl" data-path="{jp}"></ul>'
                  if is_dir and children else "")

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

    # ── CSS ──────────────────────────────────────────────────────────────────
    CSS = f"""
/* reset */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}

/* palette: zen light */
:root{{
  --bg:         {BG_COLOR};
  --ink:        #1c1b18;
  --ink-mid:    #5a5850;
  --ink-lt:      #a0a098;
  --ink-ghost:   #d8d6ce;
  --glass:       rgba(255,255,250,0.65);
  --glass-b:     rgba(180,178,170,0.32);
  --accent:      {ACCENT_COLOR};
  --accent-soft: rgba(100,140,180,0.1);
  --font:        'Geist','Satoshi',-apple-system,BlinkMacSystemFont,sans-serif;
  --font-mono:   'Geist Mono','JetBrains Mono','Fira Code',monospace;
  --r-sm:        5px;
  --r-md:        11px;
}}

html{{font-size:15px;}}
body{{
  background:var(--bg);color:var(--ink);font-family:var(--font);
  min-height:100dvh;overflow-x:hidden;-webkit-font-smoothing:antialiased;
}}

/* ink mist: faint horizontal ruling lines + cloud gradient */
body::before{{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    repeating-linear-gradient(180deg,transparent 0px,rgba(170,168,158,0.015) 1px,transparent 3px),
    radial-gradient(ellipse 50% 30% at 90% 8%,rgba(180,178,168,0.055) 0%,transparent 60%),
    radial-gradient(ellipse 100% 35% at 50% 100%,rgba(168,166,156,0.04) 0%,transparent 65%);
}}

/* mountains */
.mountains{{position:fixed;bottom:0;left:0;right:0;height:88px;pointer-events:none;z-index:1;opacity:0.5;}}

/* two-column layout */
.layout{{position:relative;z-index:10;display:grid;grid-template-columns:300px 1fr;min-height:100dvh;}}

/* left panel */
.panel-left{{
  position:sticky;top:0;height:100dvh;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:56px 48px;border-right:1px solid var(--ink-ghost);background:var(--bg);
}}
.panel-left-inner{{display:flex;flex-direction:column;align-items:center;gap:28px;}}
.geo-mark{{width:148px;height:148px;opacity:0.5;flex-shrink:0;}}
.circuit-line{{width:1px;height:40px;background:linear-gradient(to bottom,transparent,var(--ink-ghost),transparent);}}
.panel-title{{text-align:center;}}
.panel-title-main{{
  font-size:10.5px;font-weight:400;letter-spacing:0.28em;text-transform:uppercase;
  color:var(--ink-lt);margin-bottom:10px;
}}
.panel-title-sub{{font-size:20px;font-weight:300;letter-spacing:0.08em;color:var(--ink-mid);line-height:1.6;}}
.panel-stats{{margin-top:14px;font-size:10.5px;font-family:var(--font-mono);color:var(--ink-lt);letter-spacing:0.07em;}}

/* right panel */
.panel-right{{padding:64px 64px 96px;min-height:100dvh;}}

/* tree */
.tree{{list-style:none;}}
.nl{{display:none;padding-left:20px;list-style:none;position:relative;}}
.nl::before{{content:'';position:absolute;left:20px;top:0;bottom:8px;width:1px;background:var(--ink-ghost);}}
.ni{{position:relative;}}
.ni::before{{content:'';position:absolute;left:-20px;top:50%;width:20px;height:1px;background:var(--ink-ghost);}}
.ni.open>.nr>.ex{{transform:rotate(90deg);}}
.ni.open>.nl{{display:block;}}

/* row */
.nr{{
  display:flex;align-items:center;gap:8px;padding:6px 12px;border-radius:var(--r-sm);
  cursor:pointer;user-select:none;border:1px solid transparent;
  transition:background 0.14s ease,border-color 0.14s ease,box-shadow 0.14s ease;
}}
.nr:hover{{
  background:rgba(255,255,248,0.8);border-color:var(--glass-b);
  box-shadow:0 0 0 1px rgba(180,178,170,0.08),inset 0 1px 3px rgba(255,255,255,0.9);
}}
.nr:active{{transform:scale(0.993);}}

.ex{{width:16px;height:16px;flex-shrink:0;display:flex;align-items:center;justify-content:center;
    color:var(--ink-lt);transition:transform 0.2s cubic-bezier(0.16,1,0.3,1);}}
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

.cp{{
  display:flex;align-items:center;gap:4px;padding:3px 9px;border-radius:var(--r-sm);
  border:1px solid var(--ink-ghost);background:rgba(255,255,250,0.7);
  color:var(--ink-lt);font-size:10px;font-family:var(--font-mono);cursor:pointer;opacity:0;
  transition:opacity 0.15s,color 0.15s,border-color 0.15s,box-shadow 0.15s;
  white-space:nowrap;flex-shrink:0;letter-spacing:0.04em;backdrop-filter:blur(10px);
}}
.nr:hover .cp{{opacity:1;}}
.cp:hover{{color:var(--accent);border-color:rgba(100,140,180,0.35);box-shadow:0 0 10px rgba(100,140,180,0.1);}}
.cp:active{{transform:scale(0.94);}}
.cp svg{{width:10px;height:10px;}}

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
  });
})();
"""

    tree_html = build_top_nodes()
    html = (
        "<!DOCTYPE html>\n<html lang=\"zh-CN\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>StudyNotes \u00b7 目录导航</title>\n"
        "<style>\n" + CSS + "\n</style>\n"
        "</head>\n<body>\n"
        "<div class=\"mountains\">" + SVG_MTN + "</div>\n"
        "<div class=\"layout\">\n"
        "  <div class=\"panel-left\">\n"
        "    <div class=\"panel-left-inner\">\n"
        "      <div class=\"geo-mark\">" + SVG_GEO + "</div>\n"
        "      <div class=\"circuit-line\"></div>\n"
        "      <div class=\"panel-title\">\n"
        "        <div class=\"panel-title-main\">Directory Navigator</div>\n"
        "        <div class=\"panel-title-sub\">StudyNotes</div>\n"
        "      </div>\n"
        "      <div class=\"panel-stats\">" + f"{total:,} \u6761\u76ee \u00b7 {elapsed_scan:.1f}s</div>\n"
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
        "function toggle(path){window._dt_toggle(path);}\n"
        "</script>\n"
        "<script src=\"https://cdnjs.cloudflare.com/ajax/libs/pako/2.1.0/pako.min.js\"></script>\n"
        "</body>\n</html>"
    )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    sz = os.path.getsize(output_path)
    print(f"  HTML written: {sz/1024/1024:.2f}MB in {time.time()-t0:.2f}s")


# ══════════════════════════════════════════════════════════════════════════════
# Step 5: 写入扫描记录（可追溯历史）
# ══════════════════════════════════════════════════════════════════════════════

def write_scan_record(
    root: str,
    output_path: str,
    total: int,
    elapsed: float,
    raw_size: int,
    compressed_size: int,
) -> None:
    """保存本次扫描元信息到 .scan_record.json"""
    record_path = os.path.join(os.path.dirname(__file__), ".scan_record.json")
    record = {
        "root": root,
        "output": output_path,
        "total": total,
        "elapsed_s": round(elapsed, 2),
        "raw_mb": round(raw_size / 1024 / 1024, 2),
        "compressed_mb": round(compressed_size / 1024 / 1024, 2),
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    print(f"[+] Scan record saved: {record_path}")


# ══════════════════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    if len(sys.argv) < 2:
        print("用法: python generate.py /mnt/d/2Study/StudyNotes")
        sys.exit(1)

    root = resolve_root_path(sys.argv[1])

    if not os.path.isdir(root):
        print(f"错误: 路径不存在或不是目录: {root}")
        sys.exit(1)

    # 派生输出路径
    output_name = derive_output_name(root)
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "directory-tree")
    output_path = os.path.join(docs_dir, output_name)

    tmp_raw = "/tmp/dir-tree-raw.txt"
    t_start = time.time()

    # Step 1: find
    entry_count = scan_with_find(root, tmp_raw)

    # Step 2: parse
    nodes, _ = parse_raw_file(tmp_raw)
    root_children = build_root_children(nodes, root)

    # Step 3: compress
    compressed_b64, raw_size, compressed_size = compress_tree(nodes, root_children)
    total = count_all(nodes, root_children)

    # Step 4: HTML
    elapsed_scan = time.time() - t_start
    build_html(root_children, nodes, compressed_b64, total, output_path, elapsed_scan)

    # Step 5: record
    write_scan_record(root, output_path, total, elapsed_scan, raw_size, compressed_size)

    print(f"\n完成: {output_path}")
    print(f"  总条目: {total:,} | 扫描耗时: {elapsed_scan:.1f}s | HTML 大小: {os.path.getsize(output_path)/1024/1024:.2f}MB")


if __name__ == "__main__":
    main()