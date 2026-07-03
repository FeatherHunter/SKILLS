# -*- coding: utf-8 -*-
"""
智剪工坊 · style_transfer 子技能
风格迁移(用 Stable Diffusion API / 本地模型)

依赖:requests(API 调用)

用法:
  # 用 API 风格迁移(每 N 帧采样 1 张,生成风格化参考图)
  python style_transfer.py --input in.mp4 --style "oil painting" --out out.mp4 --api stability

  # 用本地 OpenCV 简单风格化(快,但效果一般)
  python style_transfer.py --input in.mp4 --style "vintage" --mode opencv --out out.mp4
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run, SKILL_ROOT,
)


def extract_keyframes(video_path, output_dir, interval=1.0):
    """提取关键帧(每 N 秒一帧)"""
    log_section(f"提取关键帧: {Path(video_path).name}")
    ensure_dir(output_dir)

    run_ffmpeg([
        "-i", str(video_path),
        "-vf", f"fps=1/{interval}",
        "-q:v", "2",
        str(Path(output_dir) / "frame_%04d.jpg"),
    ])

    frames = sorted(Path(output_dir).glob("frame_*.jpg"))
    log_info(f"提取 {len(frames)} 张关键帧")
    return frames


def style_transfer_api(frame_path, style_prompt, output_path, api="matrix"):
    """用 API 做风格迁移(简化:用 matrix 生图)"""
    log_info(f"风格迁移 {api}: {Path(frame_path).name} ← {style_prompt}")

    if api == "matrix":
        # 用 matrix MCP 的图生图
        req = {
            "requests": [{
                "prompt": f"Apply this style: {style_prompt}, keep the original subject/composition",
                "input_files": [str(frame_path)],
            }]
        }
        req_file = Path(tempfile.gettempdir()) / "style_req.json"
        req_file.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")

        result = subprocess.run(
            ["mavis", "mcp", "call", "matrix", "matrix_generate_image", "--file", str(req_file)],
            capture_output=True, text=True, encoding="utf-8"
        )
        if result.returncode != 0:
            log_warn(f"API 失败: {result.stderr}")
            return None

        # 解析 output_url
        import re
        match = re.search(r'"output_url":\s*"([^"]+)"', result.stdout)
        if not match:
            return None

        output_url = match.group(1)
        if output_url.startswith("C:\\"):
            src = Path(output_url)
            if src.exists():
                import shutil
                shutil.copy2(src, output_path)
                return output_path
    return None


def style_transfer_opencv(frame_path, style, output_path):
    """用 OpenCV 简单风格化(快,无 API)"""
    log_info(f"OpenCV 风格化: {Path(frame_path).name}")

    try:
        import cv2
        import numpy as np
    except ImportError:
        log_warn("opencv-python 未安装")
        return None

    img = cv2.imread(str(frame_path))

    if style == "oil":
        # 油画:双边滤波
        styled = cv2.bilateralFilter(img, 9, 75, 75)
    elif style == "watercolor":
        # 水彩:多次均值模糊
        styled = cv2.medianBlur(img, 7)
    elif style == "sketch":
        # 素描:灰度 + 反转 + 模糊 + 除法
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        inv = 255 - gray
        blur = cv2.GaussianBlur(inv, (21, 21), 0)
        sketch = cv2.divide(gray, 255 - blur, scale=256)
        styled = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
    elif style == "emboss":
        # 浮雕
        kernel = np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]])
        styled = cv2.filter2D(img, -1, kernel)
    else:
        # 默认:复古
        styled = cv2.bilateralFilter(img, 5, 50, 50)

    cv2.imwrite(str(output_path), styled)
    return output_path


def reassemble_video(styled_frames, video_path, output_path, fps=30):
    """把风格化的帧重新组合成视频"""
    log_section(f"重组视频: {len(styled_frames)} 帧")
    ensure_dir(Path(output_path).parent)

    # 先把帧转成视频
    temp_video = Path(tempfile.gettempdir()) / "styled_temp.mp4"
    run_ffmpeg([
        "-framerate", str(fps),
        "-i", str(styled_frames[0].parent / "frame_%04d.jpg"),
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(temp_video),
    ])

    # 用原视频的音频 + 风格化的视频
    run_ffmpeg([
        "-i", str(temp_video),
        "-i", str(video_path),
        "-map", "0:v",
        "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output_path),
    ])

    log_info(f"输出: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 风格迁移",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--style", required=True, help="风格描述(prompt)或预设(oil/watercolor/sketch/emboss)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--mode", choices=["api", "opencv"], default="opencv", help="api 慢但好,opencv 快但一般")
    parser.add_argument("--api", default="matrix", help="API 提供商(matrix)")
    parser.add_argument("--interval", type=float, default=1.0, help="采样间隔(秒)")
    args = parser.parse_args()

    # 1. 提取关键帧
    frames_dir = Path(args.out).parent / "frames_tmp"
    frames = extract_keyframes(args.input, frames_dir, args.interval)

    # 2. 风格化每帧
    styled_dir = Path(args.out).parent / "styled_tmp"
    ensure_dir(styled_dir)

    if args.mode == "api":
        for frame in frames:
            out_frame = styled_dir / frame.name
            style_transfer_api(frame, args.style, out_frame, args.api)
    else:
        for frame in frames:
            out_frame = styled_dir / frame.name
            style_transfer_opencv(frame, args.style, out_frame)

    # 3. 重组
    styled_frames = sorted(styled_dir.glob("frame_*.jpg"))
    reassemble_video(styled_frames, args.input, args.out)


if __name__ == "__main__":
    safe_run(main)()
