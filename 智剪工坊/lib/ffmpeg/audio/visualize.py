# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/visualize.py — 可视化

封装 ffmpeg 音频可视化（生成视频或图片）:
  - showwaves / showwavespic    波形图（动态 / 静态）
  - showspectrum / showspectrumpic  频谱图（动态 / 静态）
  - showcqt                    高分辨率频谱
  - showfreqs                  频率图
  - showvolume                 音量条
  - ahistogram                 直方图

输出是视频文件（含音频可视化）或单张图片。
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import run_ffmpeg  # noqa: E402


def waveform_video(input_path, output_path, width=1280, height=240,
                   mode="cline", colors="white", rate=25):
    """动态波形视频（showwaves）。

    Args:
        input_path: 输入音频
        output_path: 输出视频
        width: 视频宽度
        height: 视频高度
        mode: 'point' / 'line' / 'cline' / 'p2p'
        colors: 颜色（'white' / 'red|green|blue' 等）
        rate: 视频帧率
    """
    vf = f"showwaves=s={width}x{height}:mode={mode}:colors={colors}:rate={rate}"
    run_ffmpeg([
        "-i", str(input_path), "-vf", vf,
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac", "-y", str(output_path),
    ])
    return True, str(output_path)


def waveform_image(input_path, output_path, width=1280, height=240, colors="white"):
    """静态波形图（showwavespic）。

    输出单张 PNG 图片。

    实现方式：audio → video filter chain（filter_complex），而非 -vf。
    原因：-vf 在纯 audio 输入上无法产生 video output stream；filter_complex 强制链式转换。
    """
    fc = f"[0:a]showwavespic=s={width}x{height}:colors={colors}[v]"
    run_ffmpeg([
        "-i", str(input_path),
        "-filter_complex", fc,
        "-map", "[v]",
        "-frames:v", "1",
        "-update", "1",   # image2 muxer 持续模式
        "-c:v", "png",    # 强制 png 编码
        "-y", str(output_path),
    ])
    return True, str(output_path)


def spectrum_video(input_path, output_path, width=1280, height=480,
                   mode="combined", color="rainbow", rate=25):
    """动态频谱视频（showspectrum）。

    Args:
        mode: 'combined' / 'separate'
        color: 'rainbow' / 'channel' / 'intensity'
    """
    vf = f"showspectrum=s={width}x{height}:mode={mode}:color={color}:rate={rate}"
    run_ffmpeg([
        "-i", str(input_path), "-vf", vf,
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac", "-y", str(output_path),
    ])
    return True, str(output_path)


def spectrum_image(input_path, output_path, width=1280, height=480,
                  mode="combined", color="rainbow"):
    """静态频谱图（showspectrumpic）。

    用 filter_complex 强制 audio→video 转换（ffmpeg 7.1 + -vf 不可用）。
    """
    fc = f"[0:a]showspectrumpic=s={width}x{height}:mode={mode}:color={color}[v]"
    run_ffmpeg([
        "-i", str(input_path),
        "-filter_complex", fc,
        "-map", "[v]",
        "-frames:v", "1",
        "-update", "1",
        "-c:v", "png",
        "-y", str(output_path),
    ])
    return True, str(output_path)


def cqt_video(input_path, output_path, width=1280, height=480,
              rate=25):
    """CQT 频谱视频（showcqt）。"""
    vf = f"showcqt=s={width}x{height}:rate={rate}"
    run_ffmpeg([
        "-i", str(input_path), "-vf", vf,
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac", "-y", str(output_path),
    ])
    return True, str(output_path)


def freqs_video(input_path, output_path, width=1280, height=480, rate=25):
    """频率图视频（showfreqs）。"""
    vf = f"showfreqs=s={width}x{height}:rate={rate}"
    run_ffmpeg([
        "-i", str(input_path), "-vf", vf,
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac", "-y", str(output_path),
    ])
    return True, str(output_path)


def volume_meter_video(input_path, output_path, width=400, height=20, rate=25):
    """音量条视频（showvolume）。

    Args:
        width: 视频宽度（默认 400 像素）
        height: 视频高度（默认 20 像素）
    """
    vf = f"showvolume=w={width}:h={height}:rate={rate}"
    run_ffmpeg([
        "-i", str(input_path), "-vf", vf,
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac", "-y", str(output_path),
    ])
    return True, str(output_path)


def histogram_image(input_path, output_path, width=1024, height=400):
    """直方图（ahistogram）。

    用 filter_complex 强制 audio→video 转换（ffmpeg 7.1 + -vf 不可用）。
    """
    fc = f"[0:a]ahistogram=s={width}x{height}[v]"
    run_ffmpeg([
        "-i", str(input_path),
        "-filter_complex", fc,
        "-map", "[v]",
        "-frames:v", "1",
        "-update", "1",
        "-c:v", "png",
        "-y", str(output_path),
    ])
    return True, str(output_path)