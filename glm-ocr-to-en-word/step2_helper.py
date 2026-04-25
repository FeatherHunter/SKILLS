#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
阶段2辅助脚本

重要：此脚本不执行翻译！翻译由AI完成！

此脚本仅提供：
1. 分页读取：将glm_ocr_response.json按页拆分供AI读取
2. 质量验证：检查翻译后是否还有中文残留
3. 合并结果：将所有页翻译结果合并

AI翻译流程：
1. AI读取 glm_ocr_response.json 的 layout_details[page_idx]
2. AI在对话中直接翻译该页内容
3. AI将翻译后内容写入 page_X_translated.json
4. 循环处理所有页
5. AI调用本脚本的validate命令验证质量
6. AI调用本脚本的merge命令合并结果
"""

import json
import os
import re
import sys


def validate_translation(final_path):
    """验证翻译质量，检查残留中文"""
    if not os.path.exists(final_path):
        return {"status": "not_found", "chinese_count": -1}
    
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
                    "preview": content[:100]
                })
    
    return {
        "status": "validated",
        "total_pages": len(data),
        "chinese_count": len(issues),
        "issues": issues[:20]  # 只返回前20个问题
    }


def merge_pages(output_dir, total_pages):
    """合并所有翻译后的页面"""
    all_pages = []
    
    for page_num in range(1, total_pages + 1):
        page_path = os.path.join(output_dir, f"page_{page_num}_translated.json")
        if not os.path.exists(page_path):
            return {"status": "error", "missing_page": page_num}
        
        with open(page_path, "r", encoding="utf-8") as f:
            page_data = json.load(f)
            all_pages.append(page_data.get("elements", []))
    
    final_path = os.path.join(output_dir, "layout_details_final.json")
    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(all_pages, f, ensure_ascii=False, indent=2)
    
    return {
        "status": "merged",
        "total_pages": total_pages,
        "output": final_path
    }


def main():
    """命令行接口"""
    if len(sys.argv) < 2:
        print("阶段2辅助脚本 - 不执行翻译，仅提供验证和合并")
        print("")
        print("用法:")
        print("  python step2_helper.py validate <layout_details_final.json>")
        print("    验证翻译质量，检查残留中文")
        print("")
        print("  python step2_helper.py merge <output_dir> <total_pages>")
        print("    合并所有翻译后的页面")
        print("")
        print("重要：翻译必须由AI执行，AI需要:")
        print("  1. 读取 glm_ocr_response.json 的 layout_details")
        print("  2. 对每页元素执行翻译")
        print("  3. 保存翻译结果到 page_X_translated.json")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        if len(sys.argv) < 3:
            print("错误：请指定 layout_details_final.json 路径")
            sys.exit(1)
        final_path = sys.argv[2]
        result = validate_translation(final_path)
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
        result = merge_pages(output_dir, total_pages)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        print(f"未知命令: {command}")
        print("可用命令: validate, merge")
        sys.exit(1)


if __name__ == "__main__":
    main()
