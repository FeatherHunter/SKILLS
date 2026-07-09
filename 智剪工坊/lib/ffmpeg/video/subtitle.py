# -*- coding: utf-8 -*-
"""
lib/ffmpeg/video/subtitle.py — 字幕烧录

封装 ffmpeg 字幕相关滤镜:
  - subtitles   烧录 SRT/ASS 字幕到视频（核心）
  - ass         烧录 ASS 高级字幕（带样式）
  - drawtext    文字叠加（动态文字，非字幕文件）

注：asr/burn_subtitle.py 是用户入口；这是底层 lib。
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))  # lib/ffmpeg
from common import run_ffmpeg  # noqa: E402


def burn_subtitle(video, srt, output, font_size=22, font="Microsoft YaHei"):
    """烧录 SRT 字幕到视频（subtitles 滤镜）。

    Args:
        video: 输入视频
        srt: SRT 字幕文件
        output: 输出视频
        font_size: 字幕字号（默认 22）
        font: 字体（默认 Microsoft YaHei，Windows）
    Returns:
        (True, output_path)
    """
    srt_escaped = str(srt).replace("\\", "/").replace(":", r"\:")
    vf = (
        f"subtitles='{srt_escaped}':"
        f"force_style='FontName={font},FontSize={font_size},"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "Outline=2,Shadow=1,MarginV=30,Alignment=2'"
    )
    run_ffmpeg(["-i", str(video), "-vf", vf, "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


def burn_ass_subtitle(video, ass, output):
    """烧录 ASS 高级字幕（带样式控制）。

    Args:
        video: 输入视频
        ass: ASS 字幕文件
        output: 输出视频
    """
    ass_escaped = str(ass).replace("\\", "/").replace(":", r"\:")
    run_ffmpeg(["-i", str(video), "-vf", f"ass='{ass_escaped}'",
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


def draw_text(video, output, text, x=10, y=10,
              fontsize=24, fontcolor="white", start_time=0, duration=None):
    """视频上叠加文字（drawtext）。

    Args:
        video: 输入视频
        output: 输出
        text: 文字内容
        x, y: 位置（像素）
        fontsize: 字号
        fontcolor: 颜色
        start_time: 起始秒数
        duration: 持续秒数（None=全片）
    """
    enable_expr = f"gte(t,{start_time})"
    if duration is not None:
        enable_expr = f"between(t,{start_time},{start_time + duration})"

    # Windows 字体路径
    font_path = "C\\:/Windows/Fonts/msyh.ttc"
    text_escaped = text.replace(":", r"\:").replace("'", r"\'")

    drawtext = (
        f"drawtext=text='{text_escaped}':fontfile='{font_path}':"
        f"fontsize={fontsize}:fontcolor={fontcolor}:"
        f"x={x}:y={y}:enable='{enable_expr}'"
    )
    run_ffmpeg(["-i", str(video), "-vf", drawtext,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)