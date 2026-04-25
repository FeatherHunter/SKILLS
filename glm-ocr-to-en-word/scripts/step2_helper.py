#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段2辅助脚本（方案一）

重要：此脚本不执行翻译！翻译由AI完成！

此脚本仅提供：
1. 质量验证：检查翻译后是否还有中文残留（支持单页和整体）
2. 合并结果：将所有页翻译结果合并

用法：
  python step2_helper.py validate <page_N_translated.json>    # 单页验证
  python step2_helper.py validate <layout_details_final.json> # 整体验证
  python step2_helper.py merge <output_dir> <total_pages>     # 合并结果
"""

import json
import os
import re
import sys
import logging
from datetime import datetime


def setup_logging(temp_dir):
    """配置日志"""
    logs_dir = os.path.join(temp_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "step2_translate.log")
    
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


def validate_single_page(page_path, logger=None):
    """验证单页翻译质量"""
    if not os.path.exists(page_path):
        result = {"status": "not_found", "chinese_count": -1}
        if logger:
            logger.error(f"文件不存在: {page_path}")
        return result
    
    with open(page_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    page_num = data.get("page_number", "?")
    elements = data.get("elements", [])
    
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    issues = []
    
    for elem_idx, elem in enumerate(elements):
        if elem.get("label") == "image":
            continue
        
        content = elem.get("content", "")
        matches = chinese_pattern.findall(content)
        if matches:
            issues.append({
                "element": elem_idx,
                "chinese": matches[:5],
                "preview": content[:50]
            })
    
    result = {
        "status": "validated",
        "page": page_num,
        "elements": len(elements),
        "chinese_count": len(issues),
        "issues": issues[:10]
    }
    
    if logger:
        if len(issues) == 0:
            logger.info(f"[Page {page_num}] 验证通过，chinese_count: 0")
        else:
            logger.warning(f"[Page {page_num}] 验证发现问题，chinese_count: {len(issues)}")
    
    return result


def validate_translation(final_path, logger=None):
    """验证整体翻译质量"""
    if not os.path.exists(final_path):
        result = {"status": "not_found", "chinese_count": -1}
        if logger:
            logger.error(f"文件不存在: {final_path}")
        return result
    
    with open(final_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    issues = []
    
    for page_idx, page in enumerate(data):
        for elem_idx, elem in enumerate(page):
            if elem.get("label") == "image":
                continue
            
            content = elem.get("content", "")
            matches = chinese_pattern.findall(content)
            if matches:
                issues.append({
                    "page": page_idx + 1,
                    "element": elem_idx,
                    "chinese": matches[:5],
                    "preview": content[:50]
                })
    
    result = {
        "status": "validated",
        "total_pages": len(data),
        "chinese_count": len(issues),
        "issues": issues[:20]
    }
    
    if logger:
        if len(issues) == 0:
            logger.info(f"整体验证通过，chinese_count: 0")
        else:
            logger.warning(f"整体验证发现问题，chinese_count: {len(issues)}")
    
    return result


def merge_pages(output_dir, total_pages, logger=None):
    """合并所有翻译后的页面"""
    all_pages = []
    missing = []
    
    for page_num in range(1, total_pages + 1):
        page_path = os.path.join(output_dir, f"page_{page_num}_translated.json")
        if not os.path.exists(page_path):
            missing.append(page_num)
            if logger:
                logger.error(f"[Page {page_num}] 翻译文件不存在")
            continue
        
        with open(page_path, "r", encoding="utf-8") as f:
            page_data = json.load(f)
            all_pages.append(page_data.get("elements", []))
            if logger:
                logger.info(f"[Page {page_num}] 合并成功")
    
    if missing:
        result = {"status": "error", "missing_pages": missing}
        return result
    
    final_path = os.path.join(output_dir, "layout_details_final.json")
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, ensure_ascii=False, indent=2)
    
    if logger:
        logger.info(f"合并完成，输出: {final_path}")
    
    return {
        "status": "merged",
        "total_pages": total_pages,
        "output": final_path
    }


def main():
    """命令行接口"""
    if len(sys.argv) < 2:
        print("阶段2辅助脚本（方案一）- 不执行翻译，仅提供验证和合并")
        print("")
        print("用法:")
        print("  python step2_helper.py validate <page_N_translated.json>    # 单页验证")
        print("  python step2_helper.py validate <layout_details_final.json> # 整体验证")
        print("  python step2_helper.py merge <output_dir> <total_pages>     # 合并结果")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        if len(sys.argv) < 3:
            print("错误：请指定JSON文件路径")
            sys.exit(1)
        
        json_path = sys.argv[2]
        
        json_dir = os.path.dirname(os.path.abspath(json_path))
        temp_dir = os.path.normpath(os.path.join(json_dir, ".."))
        logger = setup_logging(temp_dir)
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, dict) and "page_number" in data:
            result = validate_single_page(json_path, logger)
        else:
            result = validate_translation(json_path, logger)
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        if result.get("chinese_count", 0) > 0:
            print(f"\n警告：发现 {result['chinese_count']} 个元素仍有中文！")
            print("AI必须补充翻译这些内容。")
    
    elif command == "merge":
        if len(sys.argv) < 4:
            print("错误：请指定输出目录和总页数")
            sys.exit(1)
        
        output_dir = sys.argv[2]
        total_pages = int(sys.argv[3])
        temp_dir = os.path.normpath(os.path.join(output_dir, ".."))
        logger = setup_logging(temp_dir)
        
        result = merge_pages(output_dir, total_pages, logger)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        print(f"未知命令: {command}")
        print("可用命令: validate, merge")
        sys.exit(1)


if __name__ == "__main__":
    main()