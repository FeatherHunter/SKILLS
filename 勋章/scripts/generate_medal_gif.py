#!/usr/bin/env python3
"""
勋章GIF生成器

AI根据视觉描述生成HTML，脚本负责：
1. 启动Playwright渲染HTML
2. 截图PNG帧序列
3. ffmpeg合成GIF

用法：
    python3 generate_medal_gif.py --html "<html代码>" --output <输出文件名> [--fps 20] [--duration 3]
    
    # 或者读取HTML文件
    python3 generate_medal_gif.py --html-file <html文件路径> --output <输出文件名>
"""

import os
import sys
import tempfile
import argparse
import subprocess
from pathlib import Path

# 依赖检查
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print('错误：缺少 playwright，请运行: pip install playwright && playwright install chromium')
    sys.exit(1)

# 配置
DEFAULT_FPS = 20
DEFAULT_DURATION = 3  # 秒


def html_to_gif(html_content: str, output_path: str, fps: int = DEFAULT_FPS, duration: int = DEFAULT_DURATION):
    """
    将HTML内容转换为GIF
    
    Args:
        html_content: HTML代码（可以包含内联CSS和动画）
        output_path: 输出GIF路径
        fps: 帧率（默认20）
        duration: 时长秒数（默认3）
    """
    MEDAL_RESOURCE_PATH = os.getenv('MEDAL_RESOURCE_PATH')
    if not MEDAL_RESOURCE_PATH:
        raise ValueError('缺少环境变量：MEDAL_RESOURCE_PATH')
    
    os.makedirs(MEDAL_RESOURCE_PATH, exist_ok=True)
    
    # 计算总帧数
    total_frames = fps * duration
    print(f'帧率: {fps}fps, 时长: {duration}秒, 总帧数: {total_frames}')
    
    # 创建临时目录存放帧
    with tempfile.TemporaryDirectory() as tmpdir:
        frame_pattern = os.path.join(tmpdir, 'frame_%04d.png')
        
        print(f'启动浏览器渲染...')
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 400, 'height': 450})
            page = context.new_page()
            
            # 设置内容
            page.set_content(html_content, wait_until='networkidle')
            
            # 等待动画开始
            page.wait_for_timeout(500)
            
            # 逐帧截图
            print(f'截图 {total_frames} 帧...')
            for i in range(total_frames):
                frame_path = frame_pattern % i
                page.screenshot(path=frame_path, full_page=True)
                if i % 10 == 0:
                    print(f'  帧 {i+1}/{total_frames}')
                    
            browser.close()
        
        # 用ffmpeg合成GIF
        print('合成GIF...')
        output_full = os.path.join(MEDAL_RESOURCE_PATH, output_path)
        
        # 使用palettegen优化颜色
        palette_file = os.path.join(tmpdir, 'palette.png')
        subprocess.run([
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-i', frame_pattern,
            '-vf', f'fps={fps},palettegen=max_colors=256:stats_mode=full',
            palette_file
        ], capture_output=True)
        
        # 合成最终GIF
        subprocess.run([
            'ffmpeg', '-y',
            '-framerate', str(fps),
            '-i', frame_pattern,
            '-i', palette_file,
            '-lavfi', f'fps={fps}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5',
            '-loop', '0',
            output_full
        ], capture_output=True)
        
        print(f'GIF已保存: {output_full}')
        return output_full


def main():
    parser = argparse.ArgumentParser(description='勋章GIF生成器')
    parser.add_argument('--html', help='HTML代码（直接传入）')
    parser.add_argument('--html-file', help='HTML文件路径（二选一）')
    parser.add_argument('--output', required=True, help='输出文件名')
    parser.add_argument('--fps', type=int, default=DEFAULT_FPS, help=f'帧率（默认{DEFAULT_FPS}）')
    parser.add_argument('--duration', type=int, default=DEFAULT_DURATION, help=f'时长秒数（默认{DEFAULT_DURATION}）')
    
    args = parser.parse_args()
    
    if args.html:
        html_content = args.html
    elif args.html_file:
        with open(args.html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
    else:
        print('错误：必须提供 --html 或 --html-file')
        sys.exit(1)
    
    html_to_gif(html_content, args.output, args.fps, args.duration)


if __name__ == '__main__':
    main()