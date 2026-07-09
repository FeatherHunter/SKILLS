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
# 注意：drawtext 表达式只认 main_w/main_h/tw/th，没有 overlay_w/overlay_h
# 改用 `tw` (text width) / `th` (text height) 替代
POSITIONS = {
    "topleft":     "10:10",
    "topright":    "main_w-tw-10:10",
    "bottomleft":  "10:main_h-th-10",
    "bottomright": "main_w-tw-10:main_h-th-10",
    "center":      "(main_w-tw)/2:(main_h-th)/2",
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
        shadow: 是否显示阴影（True/False），默认 True
    """
    pos = POSITIONS.get(position, POSITIONS["bottomright"])
    # 把 main_w-overlay_w-10 转成 main_w-tw-10（drawtext 不认 overlay_w）
    pos_x = pos.split(':')[0].replace('overlay_w', 'tw')
    pos_y = pos.split(':')[1].replace('overlay_h', 'th')

    font_path = "C\\:/Windows/Fonts/msyh.ttc"
    text_escaped = text.replace(":", r"\:").replace("'", r"\'")

    # ffmpeg 7.1: drawtext 不再接受 `shadow=N` 参数，
    # 阴影用 `shadowx=2:shadowy=2:shadowcolor=color@alpha` 控制
    shadow_opts = ""
    if shadow:
        shadow_opts = ":shadowx=2:shadowy=2:shadowcolor=black@0.5"

    drawtext = (
        f"drawtext=text='{text_escaped}':fontfile='{font_path}':"
        f"fontsize={fontsize}:fontcolor={fontcolor}@{opacity}:"
        f"x={pos_x}:y={pos_y}{shadow_opts}"
    )
    run_ffmpeg(["-i", str(video), "-vf", drawtext,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)