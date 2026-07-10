# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/enhance.py — 人声增强

封装 ffmpeg 人声/语音增强滤镜:
  - dialoguenhance   对话增强（增强人声，抑制背景）⭐ 核心
  - deesser         去齿音（s/sh 刺耳）
  - bandpass        带通滤波（保留人声频段 80Hz-8kHz）
  - highpass/lowpass/equalizer
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import run_ffmpeg, log_ffmpeg_call  # noqa: E402


@log_ffmpeg_call
def enhance_dialog(input_path, output_path, level=0.5):
    """对话增强（dialoguenhance）⭐ 核心。

    从混合音中识别对话频段，增强人声，抑制背景音。
    适合：视频有 BGM 或噪音，需要清晰人声。

    Args:
        input_path: 输入音频/视频
        output_path: 输出音频
        level: 增强强度（0=不处理，1=最强），默认 0.5
            内部映射：ffmpeg 7.1 用 `enhance` 参数（0-3），0.5 → 1.5
    """
    # ffmpeg 7.1: dialoguenhance=enhance=N (0-3, default 1)
    # 旧 API 用 level= (0-1)，新版本改名为 enhance=（0-3）
    enhance_val = level * 3
    af = f"dialoguenhance=enhance={enhance_val}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def deess(input_path, output_path, frequency=5000, intensity=0.5):
    """去齿音（deesser）。

    Args:
        frequency: 触发频率 (Hz)，默认 5000
        intensity: 衰减强度 (0-1)，默认 0.5
    """
    af = f"deesser=i={intensity}:f={frequency}:s=e"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def bandpass(input_path, output_path, low=80, high=8000):
    """带通滤波（bandpass）。

    适合提取人声频段（80Hz-8kHz），其他频段衰减。
    默认范围覆盖人声基频 + 共振峰。

    Args:
        low: 下限频率 (Hz)，默认 80
        high: 上限频率 (Hz)，默认 8000
    """
    af = f"bandpass=frequency={int((low+high)/2)}:width_type=h:width={(high-low)//2}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def highpass(input_path, output_path, frequency=80):
    """高通滤波（highpass）。

    去除低频噪音（嗡嗡声、空调声）。
    """
    af = f"highpass=f={frequency}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def lowpass(input_path, output_path, frequency=12000):
    """低通滤波（lowpass）。

    去除高频噪音。
    """
    af = f"lowpass=f={frequency}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def equalize(input_path, output_path, frequencies=None, gains=None):
    """多频段 EQ（equalizer）。

    Args:
        frequencies: 频段中心频率列表（Hz），例如 [60, 250, 1000, 4000, 12000]
        gains: 对应增益（dB），例如 [-3, 0, +2, +1, -2]
    """
    frequencies = frequencies or [60, 250, 1000, 4000, 12000]
    gains = gains or [0] * len(frequencies)

    if len(frequencies) != len(gains):
        raise ValueError("frequencies 和 gains 长度必须一致")

    cbs = "|".join(f"c1 f={f} w={f*0.5} g={g}" for f, g in zip(frequencies, gains))
    af = f"equalizer=cbs='{cbs}'"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def dynamic_equalizer(input_path, output_path,
                      threshold=20, ratio=4, attack=20, release=200):
    """动态 EQ（adynamicequalizer）。

    自适应 EQ，根据输入信号强度动态调整频段增益。
    适合：人声在响的时候突出，安静的时候收回去。

    Args:
        threshold: 触发阈值（ffmpeg 7.1 范围 [0-100]，0=无效果，100=最强压缩门限）
                历史接口是 dB（负数），已废弃。新接口请传正值。
        ratio: 压缩比 (from 0 to 30, default 1)
        attack: 起音时间 (ms, from 0.01 to 2000)
        release: 释放时间 (ms, from 0.01 to 2000)
    """
    # ffmpeg 7.1: threshold 范围 [0-100]，不是 dB
    af = f"adynamicequalizer=threshold={threshold}:ratio={ratio}:attack={attack}:release={release}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)