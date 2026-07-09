# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/extract.py — 音频提取与淡入淡出

封装 ffmpeg 音频提取与淡入淡出:
  - extract_audio     从视频提取音频流（mp3/wav/aac）
  - fade_audio        音频淡入淡出

注：这些是从 scripts/audio/extract.py 提升到底层 lib。
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS  # noqa: E402


def extract_audio(input_path, output_path, fmt="wav"):
    """从视频提取音频（最基础操作）。

    Args:
        input_path: 输入视频
        output_path: 输出音频文件
        fmt: 输出格式（mp3 / wav / aac）
    Returns:
        (success: bool, output_path: str)
    """
    codec_map = {
        "mp3": "libmp3lame",
        "wav": "pcm_s16le",
        "aac": "aac",
    }
    codec = codec_map.get(fmt, "copy")

    run_ffmpeg([
        "-i", str(input_path),
        "-vn",
        "-acodec", codec,
        "-y", str(output_path),
    ])
    return True, str(output_path)


def fade_audio(input_path, output_path, fade_in=0, fade_out=0, fps=30):
    """音频淡入淡出（afade）。

    Args:
        input_path: 输入音频/视频
        output_path: 输出
        fade_in: 淡入秒数
        fade_out: 淡出秒数
        fps: 视频帧率（输入是视频时需要）
    Returns:
        (success, output_path)
    """
    duration = get_duration(input_path)
    fade_out_st = max(0, duration - fade_out)
    af_parts = []
    if fade_in > 0:
        af_parts.append(f"afade=t=in:st=0:d={fade_in}")
    if fade_out > 0:
        af_parts.append(f"afade=t=out:st={fade_out_st}:d={fade_out}")
    af = ",".join(af_parts) if af_parts else "anull"
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"fps={fps}",
        "-af", af,
        *DEFAULT_ENCODE_ARGS,
        "-y", str(output_path),
    ])
    return True, str(output_path)