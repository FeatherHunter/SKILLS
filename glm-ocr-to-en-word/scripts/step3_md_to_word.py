#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段3：Markdown转Word（优化版：MD → HTML → pandoc → Word）

流程：
1. 调用 step3_md_to_html.py 将MD转为HTML（保留HTML表格+CSS）
2. 调用 pandoc -f html 将HTML转为Word

依赖：
- pandoc 已安装并加入PATH

用法：
  python step3_md_to_word.py <input.md> <output.docx>
  python step3_md_to_word.py <input.md> <output.docx> <reference.docx>
"""

import subprocess
import sys
import os
import shutil
import logging
import tempfile
from datetime import datetime


def setup_logging(temp_dir):
    logs_dir = os.path.join(temp_dir, "logs")
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


def find_pandoc():
    if shutil.which("pandoc"):
        return "pandoc"
    try:
        import pypandoc
        pandoc_path = pypandoc.get_pandoc_path()
        if os.path.exists(pandoc_path):
            return pandoc_path
    except Exception:
        pass
    common_paths = [
        os.path.expanduser(r"~\AppData\Local\Pandoc\pandoc.exe"),
        r"C:\Program Files\Pandoc\pandoc.exe",
        r"C:\Users\Public\AppData\Local\Pandoc\pandoc.exe",
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None


def md_to_html(md_path, html_path, logger=None):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_script = os.path.join(script_dir, "step3_md_to_html.py")
    
    if not os.path.exists(html_script):
        if logger:
            logger.error(f"step3_md_to_html.py 未找到: {html_script}")
        return False
    
    cmd = [sys.executable, html_script, md_path, html_path]
    
    if logger:
        logger.info(f"MD转HTML: {os.path.basename(md_path)} -> {os.path.basename(html_path)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            if logger:
                logger.error(f"MD转HTML失败: {result.stderr}")
            return False
        if os.path.exists(html_path):
            if logger:
                logger.info(f"HTML生成成功: {html_path}")
            return True
        else:
            if logger:
                logger.error("HTML文件未生成")
            return False
    except subprocess.TimeoutExpired:
        if logger:
            logger.error("MD转HTML超时")
        return False
    except Exception as e:
        if logger:
            logger.error(f"MD转HTML异常: {e}")
        return False


def html_to_word(html_path, output_path, reference_doc=None, logger=None):
    pandoc_exe = find_pandoc()
    if not pandoc_exe:
        if logger:
            logger.error("pandoc未找到")
        return False
    
    cmd = [pandoc_exe, html_path, "-o", output_path, "-f", "html", "-t", "docx"]
    
    if reference_doc and os.path.exists(reference_doc):
        cmd.extend(["--reference-doc", reference_doc])
    
    if logger:
        logger.info(f"HTML转Word: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            if logger:
                logger.error(f"pandoc错误: {result.stderr}")
            return False
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / 1024
            if logger:
                logger.info(f"Word保存: {output_path} ({file_size:.1f} KB)")
            return True
        else:
            if logger:
                logger.error("Word文件未生成")
            return False
    except subprocess.TimeoutExpired:
        if logger:
            logger.error("pandoc超时")
        return False
    except Exception as e:
        if logger:
            logger.error(f"HTML转Word异常: {e}")
        return False


def convert_md_to_word(md_path, output_path, reference_doc=None, logger=None):
    if reference_doc is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        default_template = os.path.normpath(os.path.join(script_dir, "..", "templates", "reference.docx"))
        if os.path.exists(default_template):
            reference_doc = default_template
    
    temp_dir = os.path.dirname(os.path.abspath(output_path))
    basename = os.path.basename(md_path)
    html_path = os.path.join(temp_dir, basename.replace('.md', '.html'))
    
    if not md_to_html(md_path, html_path, logger):
        return False
    
    result = html_to_word(html_path, output_path, reference_doc, logger)
    
    try:
        if os.path.exists(html_path):
            os.remove(html_path)
    except Exception:
        pass
    
    return result


def main():
    if len(sys.argv) < 3:
        print("阶段3：Markdown转Word（MD → HTML → pandoc → Word）")
        print("")
        print("用法:")
        print("  python step3_md_to_word.py <input.md> <output.docx> [reference.docx]")
        sys.exit(1)
    
    md_path = sys.argv[1]
    output_path = sys.argv[2]
    reference_doc = sys.argv[3] if len(sys.argv) > 3 else None
    
    output_dir = os.path.dirname(os.path.abspath(output_path))
    temp_dir = os.path.normpath(os.path.join(output_dir, ".."))
    logger = setup_logging(temp_dir)
    
    basename = os.path.basename(md_path)
    logger.info(f"转换: {basename} -> {os.path.basename(output_path)}")
    
    success = convert_md_to_word(md_path, output_path, reference_doc, logger)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
