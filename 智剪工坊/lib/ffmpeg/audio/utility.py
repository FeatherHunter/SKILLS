# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/utility.py — 杂项工具

封装 ffmpeg 音频工具类滤镜:
  - adelay              延迟一个/多个音频通道
  - apad                用静音补齐时长
  - compensationdelay   补偿延迟（多轨音视频同步）
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import run_ffmpeg, log_ffmpeg_call  # noqa: E402


@log_ffmpeg_call
def adelay(input_path, output_path, delays_ms=None):
    """延迟一个/多个音频通道（adelay）⭐ 胶水级。

    混音时让 A 声音在指定毫秒后才开始播。
    默认所有通道延迟 0ms（不延迟）。

    Args:
        input_path: 输入音频
        output_path: 输出音频
        delays_ms: 各通道延迟（毫秒），如 [0, 1000] 表示左声道不延迟，右声道延迟 1 秒
                   默认 [0]（不延迟）
    """
    delays_ms = delays_ms or [0]
    delays_str = "|".join(str(d) for d in delays_ms)
    af = f"adelay={delays_str}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def apad(input_path, output_path, target_duration=None, pad_dur=None):
    """用静音补齐时长（apad）⭐ 胶水级。

    当 BGM 比视频短时，BGM 自然播完后用静音补齐。

    Args:
        input_path: 输入音频
        output_path: 输出音频
        target_duration: 目标总时长（秒），None 表示仅当输入比目标短时补
        pad_dur: 补多少秒静音（默认补到与输入等长）
    """
    if target_duration is not None:
        af = f"apad=whole_dur={target_duration}"
    elif pad_dur is not None:
        af = f"apad=pad_dur={pad_dur}"
    else:
        af = "apad"  # 默认补到原长
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def compensation_delay(input_path, output_path, delay_ms=0, mm=0, cm=0):
    """补偿延迟（compensationdelay）— 多轨音视频同步。

    用于多麦克风录音时的时间对齐。

    Args:
        delay_ms: 延迟毫秒数
        mm: 延迟毫米（基于声速换算）
        cm: 延迟厘米
    """
    if mm > 0:
        delay_val = f"{mm}mm"
    elif cm > 0:
        delay_val = f"{cm}cm"
    else:
        delay_val = str(delay_ms)
    af = f"compensationdelay={delay_val}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)