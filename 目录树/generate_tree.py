#!/usr/bin/env python3
"""
目录树 HTML 生成器
生成交互式 HTML 目录树，支持展开/折叠、路径复制
"""

import os
import sys
import json


def scan_directory(root_path):
    """递归扫描目录，返回嵌套树结构"""
    items = []
    try:
        entries = sorted(os.listdir(root_path), key=lambda x: (
            not os.path.isdir(os.path.join(root_path, x)), x.lower()))
    except PermissionError:
        return []

    for name in entries:
        full_path = os.path.join(root_path, name)
        try:
            if os.path.isdir(full_path):
                children = scan_directory(full_path)
                items.append({
                    'name': name,
                    'path': full_path,
                    'is_dir': True,
                    'children': children,
                    'size': None
                })
            else:
                size = os.path.getsize(full_path)
                items.append({
                    'name': name,
                    'path': full_path,
                    'is_dir': False,
                    'children': [],
                    'size': size
                })
        except (PermissionError, OSError):
            continue
    return items


def build_js_tree(items):
    """构建 JS 渲染逻辑"""
    items_json = json.dumps(items, ensure_ascii=False)

    js = f"""
const items = {items_json};

function formatSize(s) {{
  if (s === null) return '';
  if (s < 1024) return s + ' B';
  if (s < 1024*1024) return (s/1024).toFixed(1) + ' KB';
  if (s < 1024*1024*1024) return (s/1024/1024/1024).toFixed(1) + ' GB';
  return (s/1024/1024/1024).toFixed(1) + ' TB';
}}

function getFileIcon(name, isDir) {{
  if (isDir) return '📂';
  const ext = name.split('.').pop().toLowerCase();
  const icons = {{
    'md': '📝', 'txt': '📄', 'pdf': '📕', 'doc': '📘', 'docx': '📘',
    'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'svg': '🖼️',
    'mp3': '🎵', 'mp4': '🎬', 'zip': '📦', 'tar': '📦', 'gz': '📦',
    'py': '🐍', 'js': '📜', 'html': '🌐', 'css': '🎨', 'json': '📋'
  }};
  return icons[ext] || '📄';
}}

function copyPath(path) {{
  const txt = document.createElement('textarea');
  txt.value = path;
  document.body.appendChild(txt);
  txt.select();
  document.execCommand('copy');
  document.body.removeChild(txt);
  const toast = document.getElementById('toast');
  toast.textContent = '✅ 已复制：' + path;
  toast.style.display = 'block';
  setTimeout(() => toast.style.display = 'none', 2000);
}}

function renderItem(item, depth) {{
  const indent = depth * 20;
  const isDir = item.is_dir;
  const icon = getFileIcon(item.name, isDir);
  const sizeStr = item.size !== null ? '<span class="size">' + formatSize(item.size) + '</span>' : '';
  const escapedPath = item.path.replace(/\\\\\\\\/g, '\\\\\\\\\\\\\\\\').replace(/'/g, "\\\\'");
  const btn = '<button class="btn" onclick="event.stopPropagation(); copyPath(\\'' + escapedPath + '\\')">复制路径</button>';

  if (isDir) {{
    const childrenHtml = item.children.map(c => renderItem(c, depth + 1)).join('');
    return '<div class="item" style="padding-left:' + indent + 'px">' +
      '<span class="folder" onclick="this.parentElement.classList.toggle(\\'open\\'); this.querySelector(\\'.toggle-icon\\').textContent = this.parentElement.classList.contains(\\'open\\') ? \\'📂\\' : \\'📁\\';">' +
      '<span class="toggle-icon">📁</span> ' + icon + ' ' + item.name + '</span>' + btn +
      '<div class="children">' + childrenHtml + '</div></div>';
  }} else {{
    return '<div class="item" style="padding-left:' + indent + 'px">' +
      '<span class="file">' + icon + ' ' + item.name + '</span>' + sizeStr + btn + '</div>';
  }}
}}

const tree = document.getElementById('tree');
items.forEach(item => {{
  tree.insertAdjacentHTML('beforeend', renderItem(item, 0));
}});

// 默认展开第一层子目录
document.querySelectorAll('.children').forEach(el => {{
  el.classList.add('open');
  const icon = el.previousElementSibling && el.previousElementSibling.querySelector && el.previousElementSibling.querySelector('.toggle-icon');
  if (icon) icon.textContent = '📂';
}});
"""
    return js


def generate_html(root_path, output_path):
    """生成 HTML 文件"""
    root_name = os.path.basename(root_path) or root_path

    # 判断路径格式
    if root_path.startswith('/mnt/'):
        display_path = root_path
    elif len(root_path) >= 2 and root_path[1] == ':':
        display_path = root_path.replace('/', '\\')
    else:
        display_path = root_path

    items = scan_directory(root_path)
    js_code = build_js_tree(items)

    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>目录树 - {root_name}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ color: #569cd6; margin-bottom: 10px; font-size: 18px; }}
  .root-path {{ color: #6a9955; font-size: 13px; margin-bottom: 20px; word-break: break-all; }}
  .tree {{ font-size: 14px; line-height: 1.8; }}
  .item {{ padding-left: 0; white-space: nowrap; display: block; }}
  .folder {{ color: #dcdcaa; cursor: pointer; user-select: none; border-radius: 3px; padding: 0 4px; }}
  .folder:hover {{ color: #fff; background: #2d2d2d; }}
  .file {{ color: #ce9178; }}
  .children {{ display: none; }}
  .children.open {{ display: block; }}
  .open {{ display: block; }}
  .btn {{ background: #0e639c; color: #fff; border: none; border-radius: 3px; padding: 1px 6px; font-size: 11px; cursor: pointer; margin-left: 8px; vertical-align: middle; }}
  .btn:hover {{ background: #1177bb; }}
  .size {{ color: #6a9955; font-size: 12px; margin-left: 6px; }}
  .toast {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: #0e639c; color: #fff; padding: 8px 20px; border-radius: 4px; font-size: 14px; display: none; z-index: 999; }}
  .legend {{ color: #6a9955; font-size: 12px; margin-top: 20px; }}
  .legend span {{ margin-right: 20px; }}
</style>
</head>
<body>
<div class="container">
  <h1>📁 目录树</h1>
  <div class="root-path">{display_path}</div>
  <div class="tree" id="tree"></div>
  <div class="legend">
    <span>📂 文件夹：点击展开/折叠</span>
    <span>📄 文件</span>
    <span>📋 复制路径</span>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
{js_code}
</script>
</body>
</html>""".format(root_name=root_name, display_path=display_path, js_code=js_code)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    def count_items(items):
        total = 0
        for item in items:
            total += 1
            if item['is_dir']:
                total += count_items(item['children'])
        return total

    return count_items(items)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python generate_tree.py <根目录> [输出路径]")
        sys.exit(1)

    root = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) >= 3 else os.path.join(root, 'directory-navigator.html')

    if not os.path.isdir(root):
        print(f"错误: 目录不存在或无法访问: {root}")
        sys.exit(1)

    count = generate_html(root, output)
    print(f"✅ 扫描完成，共 {count} 个条目")
    print(f"📂 {output}")