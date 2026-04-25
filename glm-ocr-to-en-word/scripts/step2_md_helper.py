#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段2辅助脚本（方案二：Markdown）

重要：此脚本不执行翻译！翻译由AI完成！

此脚本仅提供：
1. 质量验证：检查翻译后的Markdown是否还有中文残留
2. 分批读取：将Markdown按段落分批供AI翻译

用法：
  python step2_md_helper.py validate <page_N_translated.md>     # 单页验证
  python step2_md_helper.py validate <md_results_translated.md> # 整体验证
  python step2_md_helper.py split <md_results.md> [batch_size]  # 分批
"""

import re
import sys
import os
import logging


def setup_logging(md_path):
    """配置日志"""
    md_dir = os.path.dirname(os.path.abspath(md_path))
    temp_dir = os.path.normpath(os.path.join(md_dir, ".."))
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


def validate_translation(md_path, logger=None):
    """验证Markdown翻译质量，检查残留中文"""
    if not os.path.exists(md_path):
        result = {"status": "not_found", "chinese_count": -1}
        if logger:
            logger.error(f"文件不存在: {md_path}")
        return result
    
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    matches = chinese_pattern.findall(content)
    
    lines = content.split('\n')
    issues = []
    for i, line in enumerate(lines, 1):
        line_matches = chinese_pattern.findall(line)
        if line_matches:
            issues.append({
                "line": i,
                "chinese": line_matches[:5],
                "preview": line[:80]
            })
    
    basename = os.path.basename(md_path)
    page_match = re.search(r'page_(\d+)', basename)
    page_info = f"Page {page_match.group(1)}" if page_match else basename
    
    result = {
        "status": "validated",
        "file": basename,
        "total_lines": len(lines),
        "chinese_count": len(matches),
        "unique_chinese": len(set(matches)),
        "issues": issues[:20]
    }
    
    if logger:
        if len(matches) == 0:
            logger.info(f"[{page_info}] 验证通过，chinese_count: 0")
        else:
            logger.warning(f"[{page_info}] 验证发现问题，chinese_count: {len(matches)}")
    
    return result


def split_markdown(md_path, batch_size=50):
    """将Markdown按行数分批，返回分批信息"""
    if not os.path.exists(md_path):
        return {"status": "not_found"}
    
    with open(md_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    batches = []
    
    for i in range(0, total_lines, batch_size):
        end_line = min(i + batch_size, total_lines)
        batches.append({
            "batch": len(batches) + 1,
            "start_line": i + 1,
            "end_line": end_line,
            "line_count": end_line - i
        })
    
    return {
        "status": "split",
        "total_lines": total_lines,
        "total_batches": len(batches),
        "batch_size": batch_size,
        "batches": batches
    }


def main():
    """命令行接口"""
    if len(sys.argv) < 2:
        print("阶段2辅助脚本（Markdown方案）- 不执行翻译，仅提供验证")
        print("")
        print("用法:")
        print("  python step2_md_helper.py validate <page_N_translated.md>     # 单页验证")
        print("  python step2_md_helper.py validate <md_results_translated.md> # 整体验证")
        print("  python step2_md_helper.py split <md_results.md> [batch_size]  # 分批")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        if len(sys.argv) < 3:
            print("错误：请指定翻译后的Markdown文件路径")
            sys.exit(1)
        
        md_path = sys.argv[2]
        logger = setup_logging(md_path)
        result = validate_translation(md_path, logger)
        
        print(f"状态: {result['status']}")
        print(f"总行数: {result.get('total_lines', 'N/A')}")
        print(f"中文残留数: {result['chinese_count']}")
        
        if result.get('unique_chinese'):
            print(f"不重复中文字符数: {result['unique_chinese']}")
        
        if result.get("issues"):
            print(f"\n发现 {len(result['issues'])} 处中文残留:")
            for issue in result["issues"][:10]:
                print(f"  行{issue['line']}: {' '.join(issue['chinese'][:3])}")
        
        if result.get("chinese_count", 0) > 0:
            print(f"\n警告：发现 {result['chinese_count']} 个中文字符！")
            print("AI必须补充翻译这些内容。")
    
    elif command == "split":
        if len(sys.argv) < 3:
            print("错误：请指定Markdown文件路径")
            sys.exit(1)
        
        md_path = sys.argv[2]
        batch_size = int(sys.argv[3]) if len(sys.argv) > 3 else 50
        
        result = split_markdown(md_path, batch_size)
        
        if result["status"] == "not_found":
            print("错误：文件不存在")
            sys.exit(1)
        
        print(f"总行数: {result['total_lines']}")
        print(f"分批数: {result['total_batches']}")
        print(f"每批行数: {result['batch_size']}")
        print("\n分批信息:")
        for batch in result["batches"]:
            print(f"  批次{batch['batch']}: 行{batch['start_line']}-{batch['end_line']} ({batch['line_count']}行)")
    
    else:
        print(f"未知命令: {command}")
        print("可用命令: validate, split")
        sys.exit(1)


if __name__ == "__main__":
    main()