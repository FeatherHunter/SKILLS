# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/transform.py — 变换 / 效果

封装 ffmpeg 音频变换:
  - asetrate   改变采样率（实现变调）
  - atempo     改变播放速度（保持音调）
  - asetrate+atempo 组合  变声
  - chorus     合唱效果
  - tremolo    颤音（机器人声基础）
  - aphaser    相位偏移（phaser 效果）
  - aecho      回声
  - flanger    镶边
  - acompressor 压缩器
  - alimiter   限幅器
  - agate      门限（noise gate）
  - aexciter   高频激励
  - acrusher   比特率压缩（低保真效果）
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import run_ffmpeg  # noqa: E402


def change_pitch(input_path, output_path, pitch=1.0):
    """变调（asetrate + atempo 组合）⭐ 核心。

    Args:
        pitch: 音调倍数（>1 升调，<1 降调，1.0=不变）
                注意：范围 [0.5, 2.0]，超出范围需要分段
    """
    if not 0.5 <= pitch <= 2.0:
        raise ValueError(f"pitch 必须在 [0.5, 2.0]，当前: {pitch}")
    af = f"asetrate={int(44100 * pitch)},aresample=44100,atempo={1.0/pitch}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def change_speed(input_path, output_path, speed=1.0):
    """变速（atempo，保持音调）。

    Args:
        speed: 速度倍数（>1 加速，<1 减速）
                范围 [0.5, 2.0]，超出可分段堆叠
    """
    if not 0.5 <= speed <= 2.0:
        raise ValueError(f"speed 必须在 [0.5, 2.0]，当前: {speed}")
    af = f"atempo={speed}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def add_chorus(input_path, output_path, decay=0.5, speed=0.5, depth=0.5):
    """合唱效果（chorus）。"""
    af = f"chorus=0.5:0.5:{50*decay}:0.4:0.25:2"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def add_tremolo(input_path, output_path, frequency=20, depth=0.5):
    """颤音（tremolo，机器人声基础）。"""
    af = f"tremolo=f={frequency}:d={depth}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def add_phaser(input_path, output_path, decay=0.5, speed=0.5):
    """相位偏移（aphaser）。"""
    af = f"aphaser=in_gain=0.4:out_gain=0.74:delay={decay}:decay=0.4:speed={speed}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def add_echo(input_path, output_path, delay=0.5, decay=0.5):
    """回声（aecho）。"""
    af = f"aecho={delay}:{decay}:{delay}:{decay}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def add_flanger(input_path, output_path, delay=0.5):
    """镶边（flanger）。"""
    af = f"flanger=delay={delay}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def compress(input_path, output_path, threshold=0.5, ratio=2, attack=20, release=100):
    """压缩器（acompressor）。"""
    af = f"acompressor=threshold={threshold}:ratio={ratio}:attack={attack}:release={release}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def limit(input_path, output_path, limit_db=-3, attack=5, release=50):
    """限幅器（alimiter）。"""
    af = f"alimiter=limit={limit_db}dB:attack={attack}:release={release}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def gate(input_path, output_path, threshold_db=-30, attack=20, release=100):
    """门限（agate，noise gate）。"""
    af = f"agate=threshold={threshold_db}dB:attack={attack}:release={release}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def excite(input_path, output_path, frequency=3000, amount=1.0):
    """高频激励（aexciter）。

    Args:
        frequency: 中心频率 (Hz, ffmpeg 范围 2000-12000), 默认 3000
        amount: 激励强度 (0-64), 默认 1.0
    """
    # ffmpeg 7.1: aexciter=freq=N (2000-12000, default 7500)，不是 frequency
    af = f"aexciter=freq={frequency}:amount={amount}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


def crusher(input_path, output_path, level=4, bits=8):
    """比特率压缩（acrusher，低保真效果）。"""
    af = f"acrusher=level_in={level}:level_out={1.0/level}:bits={bits}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)