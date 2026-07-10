# -*- coding: utf-8 -*-
"""
lib/ffmpeg/video/transform.py — 缩放/裁剪/旋转/翻转

封装 ffmpeg 视频变换滤镜:
  - scale       缩放
  - crop        裁剪
  - rotate      旋转
  - hflip/vflip 翻转
  - transpose   转置
  - pad         加黑边
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import run_ffmpeg, log_ffmpeg_call  # noqa: E402


@log_ffmpeg_call
def scale_video(video, output, width, height, keep_aspect=True):
    """缩放（scale）。

    Args:
        video: 输入
        output: 输出
        width, height: 目标尺寸
        keep_aspect: 保持宽高比（加黑边）
    """
    if keep_aspect:
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black"
        )
    else:
        vf = f"scale={width}:{height}"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


@log_ffmpeg_call
def crop_video(video, output, x, y, width, height):
    """裁剪（crop）。

    Args:
        x, y: 起始坐标
        width, height: 裁剪尺寸
    """
    vf = f"crop={width}:{height}:{x}:{y}"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


@log_ffmpeg_call
def rotate_video(video, output, degrees=90):
    """旋转（rotate + transpose）。

    Args:
        degrees: 90 / 180 / 270
    """
    if degrees not in (90, 180, 270):
        raise ValueError(f"degrees 必须是 90/180/270，当前: {degrees}")

    if degrees == 90:
        vf = "transpose=1"
    elif degrees == 180:
        vf = "transpose=1,transpose=1"
    else:  # 270
        vf = "transpose=2"

    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


@log_ffmpeg_call
def flip_video(video, output, mode="h"):
    """翻转（hflip/vflip）。

    Args:
        mode: 'h'（水平） / 'v'（垂直） / 'hv'（都翻）
    """
    if mode == "h":
        vf = "hflip"
    elif mode == "v":
        vf = "vflip"
    elif mode == "hv":
        vf = "hflip,vflip"
    else:
        raise ValueError(f"mode 必须是 h/v/hv，当前: {mode}")

    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


@log_ffmpeg_call
def pad_video(video, output, top, bottom, left, right, color="black"):
    """加黑边（pad）。

    Args:
        top/bottom/left/right: 各方向 padding 像素
        color: 颜色（black/white/red/...）
    """
    # 自动算宽高
    from common import get_duration  # noqa
    vf = f"pad=iw+{left + right}:ih+{top + bottom}:{left}:{top}:{color}"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


@log_ffmpeg_call
def letterbox(video, output, target_width, target_height, color="black"):
    """加黑边到指定尺寸（常用：竖屏视频加到 9:16 标准）。"""
    vf = (
        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:{color}"
    )
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)