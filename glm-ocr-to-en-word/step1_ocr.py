#!/usr/bin/env python3
"""阶段1：调用GLM-OCR API识别PDF，保存结果和图片"""

import requests
import base64
import json
import os
import sys
from pathlib import Path


API_URL = "https://open.bigmodel.cn/api/paas/v4/layout_parsing"


def call_ocr_api(pdf_path, api_key, start_page=None, end_page=None):
    """调用GLM-OCR API"""
    with open(pdf_path, "rb") as f:
        pdf_base64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "model": "glm-ocr",
        "file": f"data:application/pdf;base64,{pdf_base64}",
        "return_crop_images": True,
        "need_layout_visualization": False
    }

    if start_page:
        payload["start_page_id"] = start_page
    if end_page:
        payload["end_page_id"] = end_page

    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    print(f"PDF大小: {file_size_mb:.1f}MB")

    if file_size_mb > 50:
        print("警告: PDF超过50MB，建议分页调用")

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
        raise Exception(f"API错误: {result['error'].get('message', str(result))}")

    return result


def download_images(result, temp_dir):
    """下载图片到本地，替换URL为本地路径"""
    images_dir = os.path.join(temp_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    for page_idx, page_elements in enumerate(result.get("layout_details", [])):
        for element in page_elements:
            if element.get("label") == "image" and element.get("content", "").startswith("http"):
                img_url = element["content"]
                img_name = f"page_{page_idx+1}_img_{element['index']}.png"
                img_path = os.path.join(images_dir, img_name)

                try:
                    img_response = requests.get(img_url, timeout=30)
                    with open(img_path, "wb") as f:
                        f.write(img_response.content)
                    element["content"] = img_path
                    print(f"  图片下载: {img_name}")
                except Exception as e:
                    print(f"  图片下载失败: {img_name} - {e}")
                    element["content"] = img_url  # 保留原URL

    return result


def main():
    if len(sys.argv) < 3:
        print("用法: python step1_ocr.py <pdf_path> <api_key>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    api_key = sys.argv[2]

    if not os.path.exists(pdf_path):
        print(f"错误: PDF文件不存在: {pdf_path}")
        sys.exit(1)

    # 准备temp目录
    pdf_dir = os.path.dirname(os.path.abspath(pdf_path))
    temp_dir = os.path.join(pdf_dir, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    response_path = os.path.join(temp_dir, "glm_ocr_response.json")

    # 断点续传：已存在则跳过
    if os.path.exists(response_path):
        print(f"OCR结果已存在，跳过: {response_path}")
        with open(response_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        pages = len(result.get("layout_details", []))
        print(f"共 {pages} 页")
        return

    # 调用API
    print("调用GLM-OCR API...")
    result = call_ocr_api(pdf_path, api_key)

    # 下载图片
    print("下载图片...")
    result = download_images(result, temp_dir)

    # 保存响应
    with open(response_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    pages = len(result.get("layout_details", []))
    usage = result.get("usage", {})
    print(f"OCR完成: {pages} 页")
    print(f"Token用量: {usage.get('total_tokens', 'N/A')}")
    print(f"结果保存: {response_path}")


if __name__ == "__main__":
    main()
