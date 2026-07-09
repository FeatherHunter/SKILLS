# -*- coding: utf-8 -*-
"""
lib/ffmpeg/video/transition.py — 转场

封装 ffmpeg xfade 转场滤镜（SKILL.md 声明 9 种 type）。
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import run_ffmpeg, get_duration  # noqa: E402


# SKILL.md 声明的 9 种转场
XFADE_TYPES = {
    "fade":      {"offset": 0, "description": "淡入淡出（最常用）"},
    "wipeleft":  {"offset": 0, "description": "向左擦除"},
    "wiperight": {"offset": 0, "description": "向右擦除"},
    "wipeup":    {"offset": 0, "description": "向上擦除"},
    "wipedown":  {"offset": 0, "description": "向下擦除"},
    "slideleft": {"offset": 0, "description": "向左滑动"},
    "slideright":{"offset": 0, "description": "向右滑动"},
    "slideup":   {"offset": 0, "description": "向上滑动"},
    "slidedown": {"offset": 0, "description": "向下滑动"},
    "circlecrop":{"offset": 0, "description": "圆形遮罩"},
    "rectcrop":  {"offset": 0, "description": "矩形遮罩"},
    "distance":  {"offset": 0, "description": "距离感"},
    "fadeblack": {"offset": 0, "description": "黑场淡入淡出"},
    "fadewhite": {"offset": 0, "description": "白场淡入淡出"},
    "radial":    {"offset": 0, "description": "径向"},
    "smoothleft":{"offset": 0, "description": "平滑左滑"},
    "smoothright":{"offset": 0, "description": "平滑右滑"},
    "smoothup":  {"offset": 0, "description": "平滑上滑"},
    "smoothdown":{"offset": 0, "description": "平滑下滑"},
    "circleopen":{"offset": 0, "description": "圆形展开"},
    "circleclose":{"offset": 0, "description": "圆形收拢"},
    "vertopen":  {"offset": 0, "description": "垂直展开"},
    "vertclose": {"offset": 0, "description": "垂直收拢"},
    "horzopen":  {"offset": 0, "description": "水平展开"},
    "horzclose": {"offset": 0, "description": "水平收拢"},
    "dissolve":  {"offset": 0, "description": "溶解"},
    "pixelize":  {"offset": 0, "description": "像素化"},
    "diagtl":    {"offset": 0, "description": "对角线（左上）"},
    "diagtr":    {"offset": 0, "description": "对角线（右上）"},
    "diagbl":    {"offset": 0, "description": "对角线（左下）"},
    "diagbr":    {"offset": 0, "description": "对角线（右下）"},
    "hlslice":   {"offset": 0, "description": "水平切片"},
    "hrslice":   {"offset": 0, "description": "垂直切片"},
    "vuslice":   {"offset": 0, "description": "垂直上切片"},
    "vdslice":   {"offset": 0, "description": "垂直下切片"},
    "hblur":     {"offset": 0, "description": "水平模糊"},
    "fadegrays": {"offset": 0, "description": "灰度淡入"},
    "wipetl":    {"offset": 0, "description": "擦除左上"},
    "wipetr":    {"offset": 0, "description": "擦除右上"},
    "wipebl":    {"offset": 0, "description": "擦除左下"},
    "wipebr":    {"offset": 0, "description": "擦除右下"},
}


def xfade_transition(video_a, video_b, output,
                     transition="fade", duration=0.5):
    """两个视频间加转场（xfade）。

    Args:
        video_a: 第一段视频
        video_b: 第二段视频
        output: 输出
        transition: 转场类型（30+ 种，见 XFADE_TYPES）
        duration: 转场时长（秒）
    Returns:
        (True, output_path)
    """
    if transition not in XFADE_TYPES:
        available = ", ".join(list(XFADE_TYPES.keys())[:5]) + "..."
        raise ValueError(f"未知转场类型 '{transition}'。示例: {available}")

    dur_a = get_duration(video_a) or 0
    offset = max(0, dur_a - duration)

    vf = f"xfade=transition={transition}:duration={duration}:offset={offset}"
    run_ffmpeg([
        "-i", str(video_a), "-i", str(video_b),
        "-filter_complex", vf,
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac", "-y", str(output),
    ])
    return True, str(output)


def concat_simple(video_paths, output):
    """简单拼接视频（concat demuxer，无转场）。

    Args:
        video_paths: 视频文件路径列表
        output: 输出
    """
    import tempfile
    list_file = Path(tempfile.gettempdir()) / "concat_list.txt"
    try:
        list_file.write_text(
            "\n".join(f"file '{p}'" for p in video_paths),
            encoding="utf-8",
        )
        run_ffmpeg([
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c", "copy",
            "-y", str(output),
        ])
    finally:
        try:
            list_file.unlink()
        except Exception:
            pass
    return True, str(output)