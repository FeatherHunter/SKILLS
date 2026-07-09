# -*- coding: utf-8 -*-
"""
lib/ffmpeg/video/watermark.py — 水印

封装 ffmpeg 水印滤镜（overlay）。
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import run_ffmpeg  # noqa: E402


# 位置映射
POSITIONS = {
    "topleft":     "10:10",
    "topright":    "main_w-overlay_w-10:10",
    "bottomleft":  "10:main_h-overlay_h-10",
    "bottomright": "main_w-overlay_w-10:main_h-overlay_h-10",
    "center":      "(main_w-overlay_w)/2:(main_h-overlay_h)/2",
}


def add_watermark(video, logo, output,
                  position="topright", opacity=0.7):
    """加 logo 水印（overlay）。

    Args:
        video: 输入视频
        logo: 水印图片
        output: 输出
        position: 位置（topleft/topright/bottomleft/bottomright/center）
        opacity: 透明度（0-1）
    Returns:
        (True, output_path)
    """
    if position not in POSITIONS:
        raise ValueError(f"position 必须是 {list(POSITIONS.keys())} 之一")
    pos = POSITIONS[position]

    fc = (
        f"[1:v]format=rgba,colorchannelmixer=aa={opacity}[logo];"
        f"[0:v][logo]overlay={pos}"
    )
    run_ffmpeg([
        "-i", str(video), "-i", str(logo),
        "-filter_complex", fc,
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "copy", "-y", str(output),
    ])
    return True, str(output)


def add_text_watermark(video, output, text, position="bottomright",
                       fontsize=20, fontcolor="white",
                       opacity=0.7, shadow=1):
    """加文字水印（drawtext）。

    Args:
        text: 文字内容
        position: 位置
        fontsize: 字号
        fontcolor: 颜色
        opacity: 透明度（0-1）
        shadow: 阴影深度
    """
    pos = POSITIONS.get(position, POSITIONS["bottomright"])

    font_path = "C\\:/Windows/Fonts/msyh.ttc"
    text_escaped = text.replace(":", r"\:").replace("'", r"\'")

    drawtext = (
        f"drawtext=text='{text_escaped}':fontfile='{font_path}':"
        f"fontsize={fontsize}:fontcolor={fontcolor}@{opacity}:"
        f"x={pos.split(':')[0]}:y={pos.split(':')[1]}:shadow={shadow}"
    )
    run_ffmpeg(["-i", str(video), "-vf", drawtext,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)