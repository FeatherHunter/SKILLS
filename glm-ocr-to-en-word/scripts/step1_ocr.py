#!/usr/bin/env python3
"""阶段1：逐页调用GLM-OCR API识别PDF，保存结果、图片和日志

用法：
  python step1_ocr.py <pdf_path> <api_key>
  python step1_ocr.py <pdf_path> <api_key> --page 5    # 只处理第5页
"""

import requests
import base64
import json
import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path


API_URL = "https://open.bigmodel.cn/api/paas/v4/layout_parsing"


def setup_logging(temp_dir):
    """配置日志"""
    logs_dir = os.path.join(temp_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "step1_ocr.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


def call_ocr_api(pdf_path, api_key, page_num, logger):
    """调用GLM-OCR API识别单页
    
    注意：当start_page_id=0时，API可能返回整个PDF。
    解决方案：对于page 1，请求page 0-1，然后只用第一页的数据。
    """
    with open(pdf_path, "rb") as f:
        pdf_base64 = base64.b64encode(f.read()).decode("utf-8")

    if page_num == 1:
        start_page_id = 0
        end_page_id = 1
    else:
        start_page_id = page_num - 1
        end_page_id = page_num - 1

    payload = {
        "model": "glm-ocr",
        "file": f"data:application/pdf;base64,{pdf_base64}",
        "return_crop_images": True,
        "need_layout_visualization": False,
        "start_page_id": start_page_id,
        "end_page_id": end_page_id
    }

    try:
        response = requests.post(
            API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=300
        )
        result = response.json()

        if "error" in result:
            error_msg = result['error'].get('message', str(result))
            logger.error(f"[Page {page_num}] API错误: {error_msg}")
            raise Exception(f"API错误: {error_msg}")

        return result
    except requests.exceptions.Timeout:
        logger.error(f"[Page {page_num}] API超时")
        raise
    except Exception as e:
        logger.error(f"[Page {page_num}] API调用失败: {e}")
        raise


def download_images_for_page(page_elements, page_num, temp_dir, logger):
    """下载单页的图片到本地"""
    images_dir = os.path.join(temp_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    downloaded = 0
    for element in page_elements:
        if element.get("label") == "image" and element.get("content", "").startswith("http"):
            img_url = element["content"]
            img_idx = element.get('index', 0)
            img_name = f"page_{page_num}_img_{img_idx}.png"
            img_path = os.path.join(images_dir, img_name)

            try:
                img_response = requests.get(img_url, timeout=30)
                with open(img_path, "wb") as f:
                    f.write(img_response.content)
                element["content"] = img_path
                logger.info(f"[Page {page_num}] 图片下载: {img_name}")
                downloaded += 1
            except Exception as e:
                logger.warning(f"[Page {page_num}] 图片下载失败: {img_name} - {e}")
                element["content"] = img_url

    return page_elements, downloaded


def process_single_page(pdf_path, api_key, page_num, temp_dir, logger):
    """处理单页PDF"""
    output_json = os.path.join(temp_dir, f"page_{page_num}_ocr.json")
    output_md = os.path.join(temp_dir, f"page_{page_num}.md")

    if os.path.exists(output_json):
        logger.info(f"[Page {page_num}] 已存在，跳过OCR")
        return True

    logger.info(f"[Page {page_num}] 开始OCR")
    
    try:
        result = call_ocr_api(pdf_path, api_key, page_num, logger)
        
        layout_details = result.get("layout_details", [])
        if not layout_details:
            logger.warning(f"[Page {page_num}] OCR结果为空")
            return False

        page_elements = layout_details[0] if layout_details else []
        page_elements, img_count = download_images_for_page(page_elements, page_num, temp_dir, logger)

        usage = result.get("usage", {})
        tokens = usage.get("total_tokens", 0)

        if page_num == 1 and len(layout_details) > 1:
            page2_elements = layout_details[1]
            page2_tokens_est = len(str(page2_elements)) // 4
            tokens = max(tokens - page2_tokens_est, 0)

        page_result = {
            "page_number": page_num,
            "elements": page_elements,
            "usage": usage
        }

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(page_result, f, ensure_ascii=False, indent=2)
        logger.info(f"[Page {page_num}] OCR完成，元素数: {len(page_elements)}，Token: {tokens}，图片: {img_count}")
        logger.info(f"[Page {page_num}] 保存: {output_json}")

        md_content = result.get("md_results", "")
        if md_content:
            if page_num == 1 and len(layout_details) > 1:
                separator_pattern = '\n---\n' if '\n---\n' in md_content else '\n\n---\n\n'
                parts = md_content.split(separator_pattern)
                md_content = parts[0] if parts else md_content
                logger.info(f"[Page {page_num}] 从多页Markdown中提取第1页内容")
            with open(output_md, "w", encoding="utf-8") as f:
                f.write(md_content)
            logger.info(f"[Page {page_num}] 保存: {output_md}")

        return True

    except Exception as e:
        logger.error(f"[Page {page_num}] 处理失败: {e}")
        return False


def get_total_pages(pdf_path, api_key, logger):
    """获取PDF总页数"""
    try:
        with open(pdf_path, "rb") as f:
            pdf_base64 = base64.b64encode(f.read()).decode("utf-8")

        payload = {
            "model": "glm-ocr",
            "file": f"data:application/pdf;base64,{pdf_base64}",
            "return_crop_images": False,
            "need_layout_visualization": False,
            "start_page_id": 0,
            "end_page_id": 0
        }

        response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=300
        )
        result = response.json()

        if "error" in result:
            logger.warning(f"获取页数失败: {result['error']}")
            return None

        return len(result.get("layout_details", []))
    except Exception as e:
        logger.warning(f"获取页数失败: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="阶段1：逐页OCR识别")
    parser.add_argument("pdf_path", help="PDF文件路径")
    parser.add_argument("api_key", help="GLM-OCR API Key")
    parser.add_argument("--page", type=int, help="只处理指定页")
    
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"错误: PDF文件不存在: {args.pdf_path}")
        sys.exit(1)

    pdf_dir = os.path.dirname(os.path.abspath(args.pdf_path))
    temp_dir = os.path.join(pdf_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    logger = setup_logging(temp_dir)
    
    file_size = os.path.getsize(args.pdf_path) / (1024 * 1024)
    
    logger.info("=" * 50)
    logger.info("阶段1：逐页OCR开始")
    logger.info("=" * 50)
    logger.info(f"PDF路径: {args.pdf_path}")
    logger.info(f"PDF大小: {file_size:.1f}MB")

    if args.page:
        start_page = end_page = args.page
        logger.info(f"处理模式: 单页模式，页码: {args.page}")
    else:
        total = get_total_pages(args.pdf_path, args.api_key, logger)
        if total and total > 0:
            start_page = 1
            end_page = total
            logger.info(f"PDF总页数: {total}")
        else:
            logger.warning("无法获取总页数，尝试逐页处理直到失败")
            start_page = 1
            end_page = 1000

    processed_pages = []
    failed_pages = []
    total_tokens = 0

    for page_num in range(start_page, end_page + 1):
        success = process_single_page(args.pdf_path, args.api_key, page_num, temp_dir, logger)
        if success:
            processed_pages.append(page_num)
            json_path = os.path.join(temp_dir, f"page_{page_num}_ocr.json")
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    total_tokens += data.get("usage", {}).get("total_tokens", 0)
        else:
            failed_pages.append(page_num)
            if not args.page and page_num == start_page:
                logger.error("第一页处理失败，停止处理")
                break
            if not args.page:
                logger.info(f"页{page_num}处理失败，可能已到末尾，停止处理")
                break

    manifest = {
        "mode": "per_page",
        "pdf_path": args.pdf_path,
        "pdf_size_mb": file_size,
        "total_pages": len(processed_pages),
        "processed_pages": processed_pages,
        "failed_pages": failed_pages,
        "total_tokens": total_tokens,
        "timestamp": datetime.now().isoformat()
    }
    manifest_path = os.path.join(temp_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    logger.info("=" * 50)
    logger.info("阶段1完成")
    logger.info("=" * 50)
    logger.info(f"成功页数: {len(processed_pages)}")
    if failed_pages:
        logger.info(f"失败页数: {len(failed_pages)}，页码: {failed_pages}")
    logger.info(f"总Token: {total_tokens}")
    logger.info(f"清单文件: {manifest_path}")


if __name__ == "__main__":
    main()
