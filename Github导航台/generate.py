#!/usr/bin/env python3
"""
Github导航台 - docs/index.html 生成器
扫描 docs/ 目录，生成带侧边栏层级目录树的 index.html
符合 taste-skill 审美规范：纯白、克制、优雅
"""
import os
import re
from datetime import datetime
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"
INDEX_FILE = DOCS_DIR / "index.html"
STYLE_VERSION = "1.0"


def scan_docs():
    """扫描 docs/ 目录结构"""
    entries = []
    for item in sorted(DOCS_DIR.iterdir()):
        if item.name.startswith('.') or item.name.startswith('_'):
            continue
        if item.is_dir():
            files = sorted([
                f for f in item.iterdir()
                if f.is_file() and f.suffix == '.html' and f.name != 'index.html'
            ])
            entries.append({
                "type": "dir",
                "name": item.name,
                "path": item.name,
                "files": [{"name": f.name, "path": f"{item.name}/{f.name}"} for f in files]
            })
        elif item.is_file() and item.suffix == '.html' and item.name != 'index.html':
            entries.append({
                "type": "file",
                "name": item.name,
                "path": item.name
            })
    return entries


def build_sidebar_tree(entries):
    """构建侧边栏目录树 HTML"""
    items = []
    for entry in entries:
        if entry["type"] == "dir":
            file_count = len(entry["files"])
            items.append(
                f'<li class="tree-item dir">'
                f'<div class="tree-row" onclick="toggleSection(this)">'
                f'<svg class="arrow" width="10" height="10" viewBox="0 0 10 10" fill="none">'
                f'<path d="M3 2L7 5L3 8" stroke="#a1a1a6" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>'
                f'</svg>'
                f'<svg width="14" height="14" viewBox="0 0 14 14" fill="none">'
                f'<path d="M1.5 3.5C1.5 2.67 2.17 2 3 2H5.5L6.5 4H11.5C12.33 4 13 4.67 13 5.5V10.5C13 11.33 12.33 12 11.5 12H2.5C1.67 12 1 11.33 1 10.5V3.5Z" stroke="#a1a1a6" stroke-width="1.1" stroke-linecap="round"/>'
                f'</svg>'
                f'<span class="tree-label">{entry["name"]}</span>'
                f'<span class="tree-count">{file_count}</span>'
                f'</div>'
                f'<ul class="tree-children">'
            )
            for f in entry["files"]:
                items.append(
                    f'<li class="tree-item file">'
                    f'<a class="tree-row tree-link" href="{f["path"]}">'
                    f'<span class="spacer"></span>'
                    f'<svg width="12" height="14" viewBox="0 0 12 14" fill="none">'
                    f'<path d="M1.5 1.5C1.5 0.67 2.17 0 3 0H7L10 3V12.5C10 13.33 9.33 14 8.5 14H3.5C2.67 14 2 13.33 2 12.5V1.5Z" stroke="#c7c7cc" stroke-width="1.1" stroke-linecap="round"/>'
                    f'</svg>'
                    f'<span class="tree-label">{f["name"]}</span>'
                    f'</a>'
                    f'</li>'
                )
            items.append('</ul></li>')
        else:
            items.append(
                f'<li class="tree-item file">'
                f'<a class="tree-row tree-link" href="{entry["path"]}">'
                f'<span class="spacer"></span>'
                f'<svg width="12" height="14" viewBox="0 0 12 14" fill="none">'
                f'<path d="M1.5 1.5C1.5 0.67 2.17 0 3 0H7L10 3V12.5C10 13.33 9.33 14 8.5 14H3.5C2.67 14 2 13.33 2 12.5V1.5Z" stroke="#c7c7cc" stroke-width="1.1" stroke-linecap="round"/>'
                f'</svg>'
                f'<span class="tree-label">{entry["name"]}</span>'
                f'</a>'
                f'</li>'
            )
    return '\n'.join(items)


def build_content(entries):
    """构建内容区 HTML"""
    if not entries:
        return '<div class="empty"><p>暂无文件</p></div>'

    sections = []
    for entry in entries:
        if entry["type"] == "dir":
            if not entry["files"]:
                file_items = '<div class="empty"><p>暂无文件</p></div>'
            else:
                file_items = '\n'.join(
                    f'<li class="file-item">'
                    f'<a class="file-link" href="{f["path"]}">'
                    f'<div class="file-info">'
                    f'<svg class="file-icon" width="14" height="16" viewBox="0 0 12 14" fill="none">'
                    f'<path d="M1.5 1.5C1.5 0.67 2.17 0 3 0H7L10 3V12.5C10 13.33 9.33 14 8.5 14H3.5C2.67 14 2 13.33 2 12.5V1.5Z" stroke="#c7c7cc" stroke-width="1.1" stroke-linecap="round"/>'
                    f'</svg>'
                    f'<span class="file-name">{f["name"]}</span>'
                    f'</div>'
                    f'<svg class="link-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none">'
                    f'<path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="#c7c7cc" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
                    f'</svg>'
                    f'</a>'
                    f'</li>'
                    for f in entry["files"]
                )
                file_items = f'<ul class="file-list">{file_items}</ul>'

            sections.append(
                f'<section class="content-section">'
                f'<div class="section-header" onclick="toggleSection(this)">'
                f'<div class="section-title">'
                f'<svg class="folder-icon" width="16" height="16" viewBox="0 0 14 14" fill="none">'
                f'<path d="M1.5 3.5C1.5 2.67 2.17 2 3 2H5.5L6.5 4H11.5C12.33 4 13 4.67 13 5.5V10.5C13 11.33 12.33 12 11.5 12H2.5C1.67 12 1 11.33 1 10.5V3.5Z" stroke="#6b6b6b" stroke-width="1.1" stroke-linecap="round"/>'
                f'</svg>'
                f'<span>{entry["name"]}</span>'
                f'<span class="section-count">{len(entry["files"])} 个文件</span>'
                f'</div>'
                f'<svg class="section-arrow" width="12" height="12" viewBox="0 0 12 12" fill="none">'
                f'<path d="M3 2L9 6L3 10" stroke="#a1a1a6" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
                f'</svg>'
                f'</div>'
                f'<div class="section-body">{file_items}</div>'
                f'</section>'
            )
    return '\n'.join(sections)


def generate_html():
    """生成 index.html"""
    entries = scan_docs()
    sidebar_tree = build_sidebar_tree(entries)
    content = build_content(entries)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>工作台</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Noto+Sans+SC:wght@400;500&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg: #ffffff;
      --bg-secondary: #f5f5f7;
      --text: #1d1d1f;
      --text-secondary: #6b6b6b;
      --border: #e5e5e5;
      --accent: #1d1d1f;
      --hover-bg: #f5f5f7;
      --font-sans: 'Inter', 'Noto Sans SC', system-ui, sans-serif;
    }}

    html, body {{ height: 100%; }}

    body {{
      font-family: var(--font-sans);
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
    }}

    /* Header */
    .header {{
      padding: clamp(1rem, 3vw, 1.5rem) clamp(1rem, 3vw, 2rem);
      border-bottom: 1px solid var(--border);
      background: var(--bg);
      flex-shrink: 0;
    }}

    .header-inner {{ max-width: 1200px; margin: 0 auto; }}

    .header h1 {{
      font-size: clamp(1rem, 3vw, 1.25rem);
      font-weight: 600;
      letter-spacing: -0.02em;
    }}

    .header-meta {{
      margin-top: 0.25rem;
      font-size: 0.75rem;
      color: var(--text-secondary);
    }}

    /* Layout */
    .layout {{
      display: flex;
      flex: 1;
      max-width: 1200px;
      margin: 0 auto;
      width: 100%;
    }}

    /* Sidebar */
    .sidebar {{
      width: 220px;
      flex-shrink: 0;
      border-right: 1px solid var(--border);
      padding: 1rem 0;
      overflow-y: auto;
    }}

    .sidebar-label {{
      font-size: 0.6875rem;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-secondary);
      padding: 0 1rem 0.5rem;
    }}

    .tree-list {{
      list-style: none;
    }}

    .tree-item.file .tree-row {{
      padding-left: 1rem;
    }}

    .tree-row {{
      display: flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.5rem 1rem;
      min-height: 44px;
      cursor: pointer;
      user-select: none;
      font-size: 0.875rem;
      color: var(--text);
      border-radius: 0;
      transition: background 0.15s ease;
    }}

    .tree-row:hover {{
      background: var(--hover-bg);
    }}

    .tree-link {{
      text-decoration: none;
      color: inherit;
      display: flex;
      align-items: center;
      gap: 0.375rem;
    }}

    .tree-children {{
      display: none;
      list-style: none;
    }}

    .tree-item.open > .tree-children {{
      display: block;
    }}

    .tree-item.open > .tree-row .arrow {{
      transform: rotate(90deg);
    }}

    .arrow {{
      flex-shrink: 0;
      transition: transform 0.2s ease;
    }}

    .tree-label {{
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .tree-count {{
      font-size: 0.6875rem;
      color: var(--text-secondary);
      flex-shrink: 0;
    }}

    .spacer {{
      width: 10px;
      flex-shrink: 0;
    }}

    /* Main */
    .main {{
      flex: 1;
      padding: 1.5rem clamp(1rem, 3vw, 2rem);
      overflow-y: auto;
    }}

    /* Content Sections */
    .content-section {{
      margin-bottom: 1.5rem;
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
    }}

    .section-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem 1.25rem;
      background: var(--bg-secondary);
      cursor: pointer;
      min-height: 56px;
      user-select: none;
      transition: background 0.15s ease;
    }}

    .section-header:hover {{
      background: #eeeeef;
    }}

    .section-title {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.9375rem;
      font-weight: 500;
    }}

    .section-count {{
      font-size: 0.75rem;
      color: var(--text-secondary);
      font-weight: 400;
    }}

    .section-arrow {{
      flex-shrink: 0;
      transition: transform 0.2s ease;
    }}

    .content-section.open > .section-header .section-arrow {{
      transform: rotate(90deg);
    }}

    .section-body {{
      display: none;
      border-top: 1px solid var(--border);
    }}

    .content-section.open > .section-body {{
      display: block;
    }}

    /* File List */
    .file-list {{
      list-style: none;
    }}

    .file-item {{
      border-bottom: 1px solid var(--border);
    }}

    .file-item:last-child {{
      border-bottom: none;
    }}

    .file-link {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.875rem 1.25rem;
      text-decoration: none;
      color: var(--text);
      min-height: 56px;
      gap: 1rem;
      transition: background 0.15s ease;
    }}

    .file-link:hover {{
      background: var(--hover-bg);
    }}

    .file-info {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex: 1;
      min-width: 0;
    }}

    .file-name {{
      font-size: 0.875rem;
      font-weight: 400;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}

    .link-arrow {{
      flex-shrink: 0;
      opacity: 0;
      transition: opacity 0.15s ease;
    }}

    .file-link:hover .link-arrow {{
      opacity: 1;
    }}

    /* Empty */
    .empty {{
      padding: 2rem;
      text-align: center;
      color: var(--text-secondary);
      font-size: 0.875rem;
    }}

    /* Mobile */
    @media (max-width: 640px) {{
      .sidebar {{
        display: none;
      }}
    }}
  </style>
</head>
<body>

<header class="header">
  <div class="header-inner">
    <h1>工作台</h1>
    <p class="header-meta">最后更新：{now}</p>
  </div>
</header>

<div class="layout">
  <aside class="sidebar">
    <div class="sidebar-label">docs/</div>
    <ul class="tree-list">
      {sidebar_tree}
    </ul>
  </aside>

  <main class="main">
    {content}
  </main>
</div>

<script>
function toggleSection(el) {{
  const section = el.closest('.content-section, .tree-item');
  if (section) {{
    section.classList.toggle('open');
  }}
}}

// Open first section by default
document.querySelector('.content-section')?.classList.add('open');
document.querySelector('.tree-item.dir')?.classList.add('open');
</script>

</body>
</html>"""

    INDEX_FILE.write_text(html, encoding='utf-8')
    return len(entries)


def main():
    count = generate_html()
    print(f"[OK] Github导航台: 生成 index.html，包含 {count} 个条目")


if __name__ == "__main__":
    main()