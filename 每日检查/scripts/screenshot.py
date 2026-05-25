#!/usr/bin/env python3
"""
每日检查 - Playwright截图脚本
将生成的HTML渲染并截图，用于发送到QQ

关键配置点：
1. 环境变量 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH 指定 chromium 路径
2. viewport width=800, scale=1 保证高清（1:1截图）
3. 截图保存路径必须在 ~/.openclaw/media/qqbot/ 下才能发送
"""

import os
import sys
import base64
import time

# 设置 chromium 路径（关键！）
os.environ['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = '/home/feather/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome'


def capture_html_to_image(html_path, output_path, viewport_width=800, scale=1):
    """
    使用Playwright将HTML截图

    Args:
        html_path: HTML文件路径
        output_path: 输出图片路径
        viewport_width: 视口宽度（默认800px）
        scale: 缩放比例（默认1，1:1截图）
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 计算缩放后的视口（物理像素）
        scaled_width = int(viewport_width * scale)
        scaled_height = int(1200 * scale)

        # 创建页面，设置视口
        page = browser.new_page(viewport={"width": scaled_width, "height": scaled_height})

        # 加载HTML文件
        page.goto(f"file://{html_path}")

        # 等待内容加载
        page.wait_for_load_state("networkidle")

        # 等待字体渲染
        page.wait_for_timeout(800)

        # 截图
        page.screenshot(path=output_path, full_page=True)

        browser.close()

        print(f"Screenshot saved: {output_path} ({scaled_width}x{scaled_height})")
        return output_path


def html_to_image_base64(html_content, viewport_width=800, scale=1):
    """
    直接从HTML内容渲染截图，返回base64

    Args:
        html_content: HTML字符串
        viewport_width: 视口宽度
        scale: 缩放比例
    Returns:
        base64编码的图片
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        scaled_width = int(viewport_width * scale)
        scaled_height = int(1200 * scale)

        page = browser.new_page(viewport={"width": scaled_width, "height": scaled_height})
        page.set_content(html_content)
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)

        screenshot = page.screenshot(full_page=True)
        browser.close()

        return base64.b64encode(screenshot).decode()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python screenshot.py <html_path> <output_path> [viewport_width] [scale]")
        sys.exit(1)

    html_path = sys.argv[1]
    output_path = sys.argv[2]
    viewport_width = int(sys.argv[3]) if len(sys.argv) > 3 else 800
    scale = int(sys.argv[4]) if len(sys.argv) > 4 else 1

    if not os.path.exists(html_path):
        print(f"ERROR: HTML file not found: {html_path}")
        sys.exit(1)

    capture_html_to_image(html_path, output_path, viewport_width, scale)