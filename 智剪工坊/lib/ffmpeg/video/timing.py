# -*- coding: utf-8 -*-
"""
lib/ffmpeg/video/timing.py — 速度 / 时间

封装 ffmpeg 视频时间相关滤镜:
  - setpts     设置 PTS（变速）
  - trim       截取片段
  - reverse    倒放
  - freeze     冻结帧
  - fps        改帧率
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import run_ffmpeg  # noqa: E402


def change_speed(video, output, factor=1.0):
    """变速（setpts，保持音调）。

    Args:
        factor: 速度倍数（>1 加速，<1 减速，范围 0.25-4.0 推荐）
    """
    if not 0.25 <= factor <= 4.0:
        raise ValueError(f"factor 必须在 [0.25, 4.0]，当前: {factor}")
    vf = f"setpts=PTS/{factor}"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-filter:a", f"atempo={factor}",
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "aac", "-y", str(output)])
    return True, str(output)


def trim_clip(video, output, start, duration):
    """截取视频片段（trim）。

    Args:
        video: 输入视频
        output: 输出
        start: 起始秒数
        duration: 时长秒数
    """
    run_ffmpeg(["-ss", str(start), "-i", str(video),
                "-t", str(duration),
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "aac", "-y", str(output)])
    return True, str(output)


def reverse_video(video, output):
    """倒放视频（reverse）。"""
    vf = "reverse"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "aac", "-y", str(output)])
    return True, str(output)


def freeze_frame(video, output, time=0, freeze_duration=2):
    """冻结一帧（freeze）。

    Args:
        time: 冻结哪一帧的时间点（秒）
        freeze_duration: 冻结持续时长（秒）
    """
    vf = f"freeze=frame_rate=25:duration={freeze_duration}:start_time={time}"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "aac", "-y", str(output)])
    return True, str(output)


def set_fps(video, output, fps=30):
    """改帧率（fps 滤镜）。

    Args:
        fps: 目标帧率
    """
    vf = f"fps={fps}"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)