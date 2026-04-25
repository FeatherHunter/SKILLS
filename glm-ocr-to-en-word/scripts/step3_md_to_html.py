#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段3：将翻译后的Markdown转换为HTML（保留HTML表格）

核心功能：
- 保留原始HTML表格（含colspan/rowspan）
- 非表格内容转为HTML标签
- 内嵌CSS样式
- 清理OCR乱码字符

用法：
  python step3_md_to_html.py <input.md> <output.html>
"""

import sys
import os
import re
import logging
from datetime import datetime


DEFAULT_CSS = """
body {
    font-family: "Times New Roman", Times, serif;
    font-size: 12pt;
    margin: 2.54cm;
    line-height: 1.5;
}
h1 {
    text-align: center;
    font-size: 16pt;
    font-weight: bold;
    margin: 14pt 0;
}
h2 {
    text-align: center;
    font-size: 14pt;
    font-weight: bold;
    margin: 12pt 0;
}
h3 {
    font-size: 12pt;
    font-weight: bold;
    margin: 10pt 0;
}
p {
    margin: 6pt 0;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 10pt 0;
}
td, th {
    border: 1px solid #000;
    padding: 4pt 6pt;
    font-size: 10pt;
    vertical-align: middle;
}
"""


OCR_GARBLED_CHARS = {
    '鈼咹': '◆',
    '鈼員': '◆',
    '鈼哊': '◆',
    '鈼哘': '◆',
    '鈼哛': '◆',
    '鈼': '◆',
    '鈻': '□',
}


def setup_logging(output_dir):
    logs_dir = os.path.join(output_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "step3_build_word.log")
    
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8', mode='a'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def clean_garbled_chars(text):
    for garbled, replacement in OCR_GARBLED_CHARS.items():
        text = text.replace(garbled, replacement)
    return text


def convert_md_to_html(md_content, title=None):
    lines = md_content.strip().split('\n')
    html_parts = [
        '<!DOCTYPE html>',
        '<html>',
        '<head>',
        '<meta charset="utf-8">',
    ]
    
    html_parts.append('<style>')
    html_parts.append(DEFAULT_CSS.strip())
    html_parts.append('</style>')
    html_parts.append('</head>')
    html_parts.append('<body>')
    
    in_table = False
    table_content = []
    
    for line in lines:
        stripped = line.strip()
        
        if not stripped:
            continue
        
        has_table_start = stripped.startswith('<table')
        has_table_end = stripped.endswith('</table>') or '</table>' in stripped
        
        if has_table_start and has_table_end:
            full_table = clean_garbled_chars(stripped)
            html_parts.append(full_table)
            in_table = False
            table_content = []
        elif has_table_start:
            in_table = True
            table_content = [stripped]
        elif has_table_end:
            table_content.append(stripped)
            in_table = False
            full_table = '\n'.join(table_content)
            full_table = clean_garbled_chars(full_table)
            html_parts.append(full_table)
            table_content = []
        elif in_table:
            table_content.append(stripped)
        elif stripped.startswith('## '):
            text = clean_garbled_chars(stripped[3:])
            html_parts.append(f'<h2>{text}</h2>')
        elif stripped.startswith('# '):
            text = clean_garbled_chars(stripped[2:])
            html_parts.append(f'<h1>{text}</h1>')
        elif stripped.startswith('### '):
            text = clean_garbled_chars(stripped[4:])
            html_parts.append(f'<h3>{text}</h3>')
        elif stripped.startswith('<div'):
            text = clean_garbled_chars(stripped)
            html_parts.append(text)
        elif stripped.startswith('</div>'):
            html_parts.append(stripped)
        elif stripped.startswith('<'):
            text = clean_garbled_chars(stripped)
            html_parts.append(text)
        else:
            text = clean_garbled_chars(stripped)
            html_parts.append(f'<p>{text}</p>')
    
    html_parts.append('</body>')
    html_parts.append('</html>')
    
    return '\n'.join(html_parts)


def main():
    if len(sys.argv) < 3:
        print("阶段3：Markdown转HTML（保留HTML表格）")
        print("")
        print("用法:")
        print("  python step3_md_to_html.py <input.md> <output.html>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    if not os.path.exists(input_path):
        print(f"错误: 文件不存在: {input_path}")
        sys.exit(1)
    
    output_dir = os.path.dirname(os.path.abspath(output_path))
    temp_dir = os.path.normpath(os.path.join(output_dir, ".."))
    logger = setup_logging(temp_dir)
    
    basename = os.path.basename(input_path)
    logger.info(f"转换: {basename} -> {os.path.basename(output_path)}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    html_content = convert_md_to_html(md_content)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    file_size = os.path.getsize(output_path)
    logger.info(f"HTML保存: {output_path} ({file_size} bytes)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
