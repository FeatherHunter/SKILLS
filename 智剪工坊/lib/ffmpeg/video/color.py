# -*- coding: utf-8 -*-
"""
lib/ffmpeg/video/color.py — 调色

封装 ffmpeg 视频调色滤镜:
  - eq           基础亮度/对比度/饱和度
  - colorbalance  颜色平衡（阴影/中调/高光）
  - curves        曲线调节（高级）
  - hue           色相
  - lut3d         3D LUT 应用
  - vibrance      自然饱和度
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common import run_ffmpeg  # noqa: E402


def adjust_brightness_contrast(video, output,
                               brightness=0, contrast=1.0, saturation=1.0,
                               gamma=1.0):
    """亮度/对比度/饱和度/伽马（eq）。

    Args:
        brightness: 亮度（-1 到 1，默认 0）
        contrast: 对比度（默认 1.0 = 不变）
        saturation: 饱和度（默认 1.0 = 不变）
        gamma: 伽马（默认 1.0 = 不变）
    """
    vf = f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}:gamma={gamma}"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


def color_balance(video, output,
                  rs=0, gs=0, bs=0,    # 阴影（暗部）RGB 调整
                  rm=0, gm=0, bm=0,    # 中调 RGB
                  rh=0, gh=0, bh=0):   # 高光 RGB
    """颜色平衡（colorbalance）。

    Args:
        rs/gs/bs: 阴影区 R/G/B 调整（-1 到 1）
        rm/gm/bm: 中调 R/G/B 调整
        rh/gh/bh: 高光 R/G/B 调整
    """
    vf = (
        f"colorbalance="
        f"rs={rs}:gs={gs}:bs={bs}:"
        f"rm={rm}:gm={gm}:bm={bm}:"
        f"rh={rh}:gh={gh}:bh={bh}"
    )
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


def hue_shift(video, output, hue=0, saturation=1.0):
    """色相/饱和度（hue）。

    Args:
        hue: 色相偏移（-180 到 180 度）
        saturation: 饱和度（0=灰度，1=原色）
    """
    vf = f"hue=h={hue}:s={saturation}"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


def apply_lut(video, lut_file, output):
    """应用 3D LUT 文件（lut3d）。

    Args:
        video: 输入视频
        lut_file: .cube 或 .3dl 文件路径
        output: 输出
    """
    run_ffmpeg(["-i", str(video), "-vf", f"lut3d='{lut_file}'",
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


def vibrance(video, output, intensity=0.5):
    """自然饱和度（vibrance）。

    Args:
        intensity: 强度（-1 到 1）
    """
    vf = f"vibrance=intensity={intensity}"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)


def curves_adjust(video, output, preset="increase_contrast"):
    """预设曲线（curves）。

    Args:
        preset: 预设名（increase_contrast / darker / increase_saturation / ...）
        完整列表见: ffmpeg -h filter=curves
    """
    vf = f"curves=preset={preset}"
    run_ffmpeg(["-i", str(video), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium",
                "-c:a", "copy", "-y", str(output)])
    return True, str(output)