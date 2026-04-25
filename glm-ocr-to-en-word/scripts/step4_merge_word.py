#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段4：合并多个Word文档为一个最终文档

用法：
  python step4_merge_word.py <output.docx> <input1.docx> <input2.docx> ...
  python step4_merge_word.py <output.docx> --dir <directory>
"""

import sys
import os
import glob
import re
import logging
import json
from datetime import datetime
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def natural_sort_key(s):
    """自然排序key"""
    _nsre = re.compile(r'(\d+)')
    return [int(text) if text.isdigit() else text.lower() for text in _nsre.split(s)]


def setup_logging(temp_dir):
    """配置日志"""
    logs_dir = os.path.join(temp_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "step4_merge.log")
    
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


def merge_documents(output_path, input_paths, logger):
    """合并多个Word文档"""
    if not input_paths:
        logger.error("没有输入文件")
        return False

    valid_paths = [p for p in input_paths if os.path.exists(p)]
    if not valid_paths:
        logger.error("所有输入文件都不存在")
        return False

    logger.info(f"找到 {len(valid_paths)} 个Word文件")

    merged_doc = Document()

    for idx, doc_path in enumerate(valid_paths):
        if idx > 0:
            merged_doc.add_page_break()

        try:
            sub_doc = Document(doc_path)
            
            for element in sub_doc.element.body:
                if element.tag.endswith('}sectPr'):
                    continue
                merged_doc.element.body.append(element)

            logger.info(f"合并: {os.path.basename(doc_path)}")
        except Exception as e:
            logger.error(f"合并失败: {os.path.basename(doc_path)} - {e}")
            continue

    try:
        merged_doc.save(output_path)
        file_size = os.path.getsize(output_path) / 1024
        
        logger.info("=" * 50)
        logger.info("阶段4完成")
        logger.info("=" * 50)
        logger.info(f"输出文件: {output_path}")
        logger.info(f"文件大小: {file_size:.1f} KB")
        logger.info(f"合合文件数: {len(valid_paths)}")
        
        return True
    except Exception as e:
        logger.error(f"保存失败: {e}")
        return False


def main():
    if len(sys.argv) < 3:
        print("阶段4：合并多个Word文档")
        print("")
        print("用法:")
        print("  python step4_merge_word.py <output.docx> <input1.docx> <input2.docx> ...")
        print("  python step4_merge_word.py <output.docx> --dir <directory>")
        sys.exit(1)

    output_path = sys.argv[1]
    
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if "--dir" in sys.argv:
        temp_dir = os.path.normpath(os.path.join(output_dir, ".."))
    else:
        temp_dir = output_dir
    
    logger = setup_logging(temp_dir)
    
    logger.info("=" * 50)
    logger.info("阶段4：合并Word开始")
    logger.info("=" * 50)

    if sys.argv[2] == "--dir" and len(sys.argv) > 3:
        directory = sys.argv[3]
        docx_files = sorted(glob.glob(os.path.join(directory, "*.docx")), key=natural_sort_key)
        if not docx_files:
            logger.error(f"目录下没有.docx文件: {directory}")
            sys.exit(1)
        logger.info(f"输入目录: {directory}")
        for f in docx_files:
            logger.info(f"  找到: {os.path.basename(f)}")
        merge_documents(output_path, docx_files, logger)
    else:
        input_paths = sys.argv[2:]
        merge_documents(output_path, input_paths, logger)


if __name__ == "__main__":
    main()