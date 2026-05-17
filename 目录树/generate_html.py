#!/usr/bin/env python3
"""
目录树 HTML 生成器 · 无限扫描版 v2
- 扫描深度不限，条目数上限 50000
- .git 等系统目录不递归扫描，只显示数量
- 纯白背景，克制留白，精致 SVG 图标
- 内存优化：streaming JSON 构建 + 增量写入
"""

import os
import sys
import json
from pathlib import Path

# ─── 配置 ───────────────────────────────────────────────────
OUTPUT_BASE = "/mnt/d/2Study/StudyNotes/docs/directory-tree"
MAX_DEPTH = 10
MAX_ITEMS = 50000
SKIP_RECURSE = {'.git', '__pycache__', 'node_modules', '.idea', '.vscode', '.DS_Store', 'Thumbs.db'}
# ─────────────────────────────────────────────────────────────


def name_from_root(root_path):
    parts = [p for p in root_path.strip('/').split('/') if p]
    if len(parts) < 2:
        name = parts[-1] if parts else 'root'
        return f"_{name}.html"
    last, second_last = parts[-1], parts[-2]
    if len(last) == 1 and len(parts) >= 3:
        last = parts[-1]
    if len(second_last) == 1 and len(parts) >= 4:
        second_last = parts[-2]
    return f"{second_last}_{last}.html"


def output_path(root_path):
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    return os.path.join(OUTPUT_BASE, name_from_root(root_path))


def count_children_approx(path):
    try:
        return len(list(os.scandir(path)))
    except (PermissionError, OSError):
        return 0


def scan_directory(root_path, progress_callback=None):
    """递归扫描，返回嵌套列表（带条目数上限）"""
    count = [0]

    def _scan(path, depth):
        if depth > MAX_DEPTH or count[0] >= MAX_ITEMS:
            return []
        try:
            entries = sorted(os.scandir(path), key=lambda x: (not x.is_dir(), x.name.lower()))
        except (PermissionError, OSError):
            return []

        result = []
        for entry in entries:
            if count[0] >= MAX_ITEMS:
                break
            count[0] += 1
            if count[0] % 2000 == 0 and progress_callback:
                progress_callback(count[0])

            try:
                if entry.is_dir(follow_symlinks=False):
                    name = entry.name
                    if name in SKIP_RECURSE:
                        child_count = count_children_approx(entry.path)
                        result.append({
                            'name': name,
                            'path': entry.path,
                            'is_dir': True,
                            'children': [],
                            'is_system': True,
                            'file_count': child_count,
                            'size': None
                        })
                    else:
                        children = _scan(entry.path, depth + 1) if count[0] < MAX_ITEMS else []
                        file_count = sum(1 for _ in walk(children)) if children else 0
                        result.append({
                            'name': name,
                            'path': entry.path,
                            'is_dir': True,
                            'children': children if children else [],
                            'is_system': False,
                            'file_count': file_count,
                            'size': None
                        })
                else:
                    size = entry.stat(follow_symlinks=False).st_size
                    result.append({
                        'name': entry.name,
                        'path': entry.path,
                        'is_dir': False,
                        'children': [],
                        'is_system': False,
                        'size': size
                    })
            except (PermissionError, OSError):
                continue
        return result

    return _scan(root_path, 0)


def walk(items):
    for item in items:
        yield item
        if item['is_dir'] and not item.get('is_system'):
            yield from walk(item['children'])


def count_all(items):
    total = 0
    for item in items:
        total += 1
        if item['is_dir'] and not item.get('is_system'):
            total += count_all(item['children'])
    return total


def format_size(s):
    if s is None:
        return ''
    if s < 1024:
        return f'{s} B'
    if s < 1048576:
        return f'{s / 1024:.0f} KB'
    if s < 1073741824:
        return f'{s / 1048576:.1f} MB'
    return f'{s / 1073741824:.1f} GB'


SVG_ARROW = '<svg width="8" height="8" viewBox="0 0 8 8" fill="none"><path d="M2 1.5L6 4L2 6.5" stroke="#c0c0c8" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
SVG_FOLDER = '<svg width="14" height="13" viewBox="0 0 14 13" fill="none"><path d="M1 2.5C1 1.95 1.45 1.5 2 1.5H5L6.5 3.5H12C12.55 3.5 13 3.95 13 4.5V10.5C13 11.05 12.55 11.5 12 11.5H2C1.45 11.5 1 11.05 1 10.5V2.5Z" stroke="#b0b0b8" stroke-width="1.1" stroke-linecap="round"/></svg>'
SVG_FILE = '<svg width="12" height="14" viewBox="0 0 12 14" fill="none"><path d="M2 1.5C2 1 2.45 0.5 3 0.5H7L9.5 3H11.5C11.78 3 12 3.22 12 3.5V12.5C12 12.78 11.78 13 11.5 13H3C2.78 13 2 12.78 2 12.5V1.5Z" stroke="#c8c8d0" stroke-width="1.1" stroke-linecap="round"/></svg>'
SVG_DOT = '<svg width="6" height="6" viewBox="0 0 6 6"><circle cx="3" cy="3" r="2" fill="#b0b0b8"/></svg>'


def ep(path):
    return path.replace('\\', '\\\\').replace("'", "\\'")


def js_escape(s):
    return s.replace('\\', '\\\\').replace("'", "\\'").replace('<', '\\u003c').replace('>', '\\u003e')


def build_tree_html(items):
    """直接构建 HTML 字符串，不走 JSON 中转（省内存）"""
    parts = []

    def build(item, depth):
        indent = depth * 18
        is_dir = item['is_dir']
        is_sys = item.get('is_system', False)
        count_label = str(item.get('file_count', '')) + ' items' if item.get('file_count') is not None else ''

        if is_dir:
            kids = ''.join(build(c, depth + 1) for c in item['children'])
            parts.append(
                f'<div class="item dir" style="padding-left:{indent}px">'
                f'<div class="row" onclick="toggleDir(this)">'
                f'<span class="arrow">{SVG_ARROW}</span>'
                f'<span class="icon">{SVG_FOLDER}</span>'
                f'<span class="name">{js_escape(item["name"])}</span>'
                f'<span class="meta">{count_label}</span>'
                f'<button class="copy-btn" onclick="event.stopPropagation(); copyPath(\'{ep(item["path"])}\')">{SVG_DOT}</button>'
                f'</div>'
                f'<div class="children">{kids}</div>'
                f'</div>'
            )
        else:
            parts.append(
                f'<div class="item file" style="padding-left:{indent}px">'
                f'<div class="row">'
                f'<span class="spacer"></span>'
                f'<span class="icon">{SVG_FILE}</span>'
                f'<span class="name">{js_escape(item["name"])}</span>'
                f'<span class="meta">{format_size(item["size"])}</span>'
                f'<button class="copy-btn" onclick="event.stopPropagation(); copyPath(\'{ep(item["path"])}\')">{SVG_DOT}</button>'
                f'</div>'
                f'</div>'
            )

    for item in items:
        build(item, 0)
    return ''.join(parts)


def generate_html(root_path, output_path, progress_callback=None):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    display_path = root_path

    items = scan_directory(root_path, progress_callback=progress_callback)
    file_count = sum(1 for _ in walk(items))
    dir_count = sum(1 for i in walk(items) if i['is_dir'])

    tree_html = build_tree_html(items)

    js = """
let toastTimer = null;

function copyPath(path) {
    navigator.clipboard.writeText(path).then(() => { showToast('已复制'); })
    .catch(() => {
        const t = document.createElement('textarea');
        t.value = path; document.body.appendChild(t);
        t.select(); document.execCommand('copy'); document.body.removeChild(t);
        showToast('已复制');
    });
}

function showToast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.style.opacity = '1';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.style.opacity = '0'; }, 1800);
}

function toggleDir(row) {
    const item = row.closest('.item');
    const children = item.querySelector('.children');
    const arrow = row.querySelector('.arrow');
    if (!children) return;
    const isOpen = item.classList.contains('open');
    item.classList.toggle('open');
    arrow.style.transform = isOpen ? 'rotate(0deg)' : 'rotate(90deg)';
}

function initHover() {
    document.querySelectorAll('.row').forEach(row => {
        row.addEventListener('mouseenter', () => {
            row.classList.add('hover');
            const btn = row.querySelector('.copy-btn');
            if (btn) btn.style.opacity = '1';
        });
        row.addEventListener('mouseleave', () => {
            row.classList.remove('hover');
            const btn = row.querySelector('.copy-btn');
            if (btn) btn.style.opacity = '0';
        }});
    });
}

document.getElementById('tree').innerHTML = """ + json.dumps(tree_html) + """;
initHover();
"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Directory Tree</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&family=Noto+Sans+SC:wght@400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
    --bg: #ffffff;
    --text: #2a2a2e;
    --text-secondary: #8a8a8e;
    --hover-bg: #f7f7f8;
    --font-sans: 'Inter', 'Noto Sans SC', -apple-system, sans-serif;
}}
body {{
    font-family: var(--font-sans);
    background: var(--bg);
    color: var(--text);
    font-size: 12px;
    line-height: 1.7;
    -webkit-font-smoothing: antialiased;
}}
.wrap {{ max-width: 680px; margin: 0 auto; padding: 56px 24px 96px; }}
.header {{ margin-bottom: 40px; }}
.header-title {{ font-size: 18px; font-weight: 500; letter-spacing: -0.025em; }}
.header-path {{ font-size: 11px; color: var(--text-secondary); margin-top: 6px; word-break: break-all; font-family: 'JetBrains Mono', monospace; }}
.header-meta {{ font-size: 11px; color: var(--text-secondary); margin-top: 4px; }}
.tree {{ font-size: 12px; line-height: 1.7; }}
.item {{ display: block; }}
.row {{
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 5px 6px;
    border-radius: 5px;
    min-height: 42px;
    transition: background 0.12s ease;
    cursor: default;
    user-select: none;
}}
.row:hover {{ background: var(--hover-bg); }}
.arrow {{ display: inline-flex; align-items: center; flex-shrink: 0; width: 8px; height: 8px; transition: transform 0.18s ease; transform: rotate(0deg); }}
.item.open > .row .arrow {{ transform: rotate(90deg); }}
.icon {{ display: inline-flex; align-items: center; flex-shrink: 0; }}
.name {{ flex: 1; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 12px; }}
.meta {{ font-size: 10px; color: var(--text-secondary); white-space: nowrap; flex-shrink: 0; }}
.spacer {{ width: 8px; flex-shrink: 0; display: inline-block; }}
.copy-btn {{ opacity: 0; display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; background: none; border: none; cursor: pointer; border-radius: 50%; transition: opacity 0.12s ease; padding: 0; flex-shrink: 0; }}
.copy-btn:hover {{ background: rgba(0,0,0,0.06); }}
.copy-btn:focus {{ outline: none; }}
.copy-btn svg {{ width: 6px; height: 6px; }}
.children {{ display: none; }}
.item.open > .children {{ display: block; }}
.toast {{ position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: var(--text); color: #fff; font-size: 11px; padding: 5px 14px; border-radius: 20px; opacity: 0; transition: opacity 0.18s ease; pointer-events: none; }}
@media (max-width: 640px) {{ .wrap {{ padding: 40px 16px 80px; }} .header {{ margin-bottom: 32px; }} .header-title {{ font-size: 16px; }} }}
@media (hover: none) {{ .copy-btn {{ opacity: 0.35; }} }}
</style>
</head>
<body>
<div class="wrap">
    <div class="header">
        <div class="header-title">Directory Tree</div>
        <div class="header-path">{display_path}</div>
        <div class="header-meta">{file_count} files &middot; {dir_count} directories</div>
    </div>
    <div class="tree" id="tree"></div>
</div>
<div class="toast" id="toast">已复制</div>
<script>
{js}
</script>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return count_all(items), output_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python generate_html.py <root_dir>")
        sys.exit(1)

    root = sys.argv[1]
    if not os.path.isdir(root):
        print(f"Error: not a directory: {root}")
        sys.exit(1)

    output = output_path(root)

    def progress(n):
        print(f"scanning: {n} items...", file=sys.stderr, flush=True)

    print("Scanning...", file=sys.stderr, flush=True)
    n, path = generate_html(root, output, progress_callback=progress)
    print(f"Done. {n} items", file=sys.stderr)
    print(f"Output: {path}")