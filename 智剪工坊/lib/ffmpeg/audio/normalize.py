# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/normalize.py — 归一化 / 动态

封装 ffmpeg 音频归一化:
  - loudnorm    EBU R128 响度归一化（广播/流媒体标准）⭐ 核心
  - dynaudnorm  动态归一化（自适应）
  - volume      音量调整（线性）
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import run_ffmpeg, log_ffmpeg_call  # noqa: E402


@log_ffmpeg_call
def normalize_loudnorm(input_path, output_path,
                       target_lufs=-23, true_peak=-2, lra=7):
    """EBU R128 响度归一化（loudnorm）⭐ 核心。

    把音频统一到目标响度（默认 -23 LUFS，广播标准）。
    适合：podcast、流媒体、跨平台播放。

    Args:
        input_path: 输入音频/视频
        output_path: 输出音频
        target_lufs: 目标响度（LUFS），默认 -23（EBU R128 标准）
        true_peak: 真峰值上限（dBTP），默认 -2
        lra: 响度范围（LRA），默认 7
    """
    af = f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def normalize_dynamic(input_path, output_path, target_rms_db=-23, compress=0.5):
    """动态归一化（dynaudnorm）。

    自适应音量归一化，保持动态范围。

    Args:
        target_rms_db: 目标 RMS（dBFS），内部转换为线性值
                历史接口是 `target_rms`（直接传 dB 值）。已重命名为 `target_rms_db` 以区分。
        compress: 压缩比 (ffmpeg 范围 0-30)
    """
    # ffmpeg 7.1: dynaudnorm 用 targetrms (0-1 线性) 或 peak (0-1)
    # 用户传 dB，内部转换为线性值
    target_rms = 10 ** (target_rms_db / 20)
    af = f"dynaudnorm=targetrms={target_rms}:compress={compress}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def adjust_volume(input_path, output_path, factor=1.0):
    """调整音量（volume）。

    Args:
        factor: 音量倍数（1.0=不变，0.5=半音量，2.0=2倍音量）
    """
    af = f"volume={factor}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def adjust_volume_db(input_path, output_path, db=0):
    """调整音量（dB 单位，volume）。

    Args:
        db: 音量调整量（dB），默认 0 不变
    """
    af = f"volume={db}dB"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def fade_in_out(input_path, output_path, fade_in=0, fade_out=0):
    """淡入淡出（afade）。

    Args:
        fade_in: 淡入秒数
        fade_out: 淡出秒数
    """
    duration = 0  # 占位
    af_parts = []
    if fade_in > 0:
        af_parts.append(f"afade=t=in:st=0:d={fade_in}")
    if fade_out > 0:
        af_parts.append(f"afade=t=out:st=0:d={fade_out}")
    af = ",".join(af_parts) if af_parts else "anull"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)