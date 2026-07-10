# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/detect.py — 检测 / 分析

封装 ffmpeg 音频检测滤镜:
  - silencedetect    静音检测（自动分段）⭐ 核心
  - astats           音频统计（音量、采样率）
  - volumedetect     音量检测
  - aphasemeter      相位表（立体声分析）

检测类滤镜特点：纯分析，不输出音频，只输出元数据。
返回结构化 dict 而非文件路径。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import log_ffmpeg_call  # noqa: E402


@log_ffmpeg_call
def detect_silence(input_path, threshold=-30, min_duration=0.5):
    """静音检测（silencedetect）⭐ 核心。

    自动找出音频中所有静音段，常用于：
      - 自动分段（找说话人切换点）
      - 切掉开头/结尾静音
      - 检测长视频里"无人说话"的段落

    Args:
        input_path: 输入音频/视频
        threshold: 静音阈值（dB），默认 -30
        min_duration: 最短静音时长（秒），默认 0.5
    Returns:
        dict: {
          'total_silence': 总静音时长(秒),
          'silence_count': 静音段数,
          'segments': [{'start': 0.5, 'end': 3.2, 'duration': 2.7}, ...]
        }
    """
    af = f"silencedetect=noise={threshold}dB:d={min_duration}"
    cmd = ["ffmpeg", "-i", str(input_path), "-af", af, "-f", "null", "-"]

    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=600)

    # 解析 stderr 里的 silencedetect 输出
    # 格式: [silencedetect @ xxx] silence_start: 0.500
    #       [silencedetect @ xxx] silence_end: 3.200 | silence_duration: 2.700
    starts = [float(m.group(1)) for m in re.finditer(r"silence_start:\s*([\d.]+)", result.stderr)]
    ends = [float(m.group(1)) for m in re.finditer(r"silence_end:\s*([\d.]+)", result.stderr)]

    segments = []
    for s, e in zip(starts, ends):
        segments.append({"start": s, "end": e, "duration": round(e - s, 3)})

    return {
        "threshold_db": threshold,
        "min_duration": min_duration,
        "silence_count": len(segments),
        "total_silence": round(sum(seg["duration"] for seg in segments), 3),
        "segments": segments,
    }


@log_ffmpeg_call
def detect_volume(input_path):
    """音量检测（volumedetect）。

    Returns:
        dict: {'max_volume': dB, 'mean_volume': dB}
    """
    cmd = ["ffmpeg", "-i", str(input_path), "-af", "volumedetect", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=600)

    max_v = re.search(r"max_volume:\s*([-\d.]+)\s*dB", result.stderr)
    mean_v = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", result.stderr)

    return {
        "max_volume_db": float(max_v.group(1)) if max_v else None,
        "mean_volume_db": float(mean_v.group(1)) if mean_v else None,
    }


@log_ffmpeg_call
def detect_astats(input_path):
    """音频统计（astats）。

    返回：峰值、最小值、RMS、噪声地板等。
    """
    cmd = ["ffmpeg", "-i", str(input_path), "-af", "astats=metadata=1:reset=1", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=600)

    stats = {}
    # 解析 output（简化版，只取关键指标）
    for line in result.stderr.split("\n"):
        m = re.match(r"\s*(\w+(?:\s+\w+)*):\s+([-\d.]+)\s*(\w+)?", line)
        if m:
            key = m.group(1).strip()
            val = m.group(2)
            try:
                stats[key] = float(val)
            except ValueError:
                stats[key] = val

    return stats


@log_ffmpeg_call
def detect_phase(input_path, duration_limit=30):
    """相位表（aphasemeter）。

    立体声相位分析，返回各帧相位（-1=反相，+1=同相）。
    """
    cmd = ["ffmpeg", "-i", str(input_path), "-af", "aphasemeter",
           "-t", str(duration_limit), "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=120)
    return {"raw_output": result.stderr[-2000:]}  # 简化：返回原始文本