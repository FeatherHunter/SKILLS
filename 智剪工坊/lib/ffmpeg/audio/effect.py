# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/effect.py — 其他效果

封装 ffmpeg 其他音频效果:
  - aecho             回声（已在 transform.py 暴露，此处额外参数）
  - flanger           镶边（同上）
  - compand           多段压缩/扩展
  - dcshift           直流偏移
  - adeclick/adeclip  去爆音/削波（denoise.py 也有）
  - crystalizer       噪声锐化
  - apulsator         脉冲效果
  - atilt             频谱倾斜
  - sidechaingate     侧链门限
  - virtualbass       虚拟低音
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import run_ffmpeg, log_ffmpeg_call  # noqa: E402


@log_ffmpeg_call
def echo_advanced(input_path, output_path,
                  in_gain=0.6, out_gain=0.3,
                  delays="1000|1800|2500", decays="0.3|0.25|0.2"):
    """回声（aecho，完整参数）。"""
    af = f"aecho={in_gain}:{out_gain}:{delays}:{decays}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def compand_multi(input_path, output_path, compand_expr):
    """多段压缩/扩展（compand）。

    Args:
        compand_expr: compand 表达式
        示例: "0.05,0.1 6:-70/-60,-20/-20,0/-10"（双段）
    """
    af = f"compand={compand_expr}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def dc_shift(input_path, output_path, shift=0):
    """直流偏移（dcshift）。"""
    af = f"dcshift={shift}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def crystalizer(input_path, output_path, intensity=1.0):
    """噪声锐化（crystalizer）。"""
    af = f"crystalizer=i={intensity}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def pulsator(input_path, output_path, hz=2, amount=0.5):
    """脉冲效果（apulsator）。"""
    af = f"apulsator=hz={hz}:amount={amount}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def spectral_tilt(input_path, output_path, slope=0):
    """频谱倾斜（atilt）。

    Args:
        slope: 倾斜量（-1 到 1），正值增强高频，负值增强低频
                历史接口名是 `tilt`。已重命名为 `slope` 以匹配 ffmpeg 7.1 参数名。
    """
    # ffmpeg 7.1: atilt=slope=N (-1 到 1)，不是 tilt
    af = f"atilt=slope={slope}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def sidechain_gate(input_path, output_path, sidechain_path, threshold=-30):
    """侧链门限（sidechaingate）。

    Args:
        sidechain_path: 侧链信号（控制信号源）
        threshold: 门限阈值 (dB)
    """
    af = f"sidechaingate=threshold={threshold}dB"
    run_ffmpeg([
        "-i", str(input_path), "-i", str(sidechain_path),
        "-af", f"{af}:sc", "-c:a", "pcm_s16le", "-y", str(output_path),
    ])
    return True, str(output_path)


@log_ffmpeg_call
def virtual_bass(input_path, output_path, cutoff=200, strength=1.0):
    """虚拟低音（virtualbass）。"""
    af = f"virtualbass=cutoff={cutoff}:strength={strength}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def drmeter(input_path, output_path):
    """DR 测量（drmeter）— 动态范围标准（CD 制作标准）。

    注意：这个滤镜是测量，不输出文件。
    实际返回 stdout 信息。
    """
    import subprocess
    cmd = ["ffmpeg", "-i", str(input_path), "-af", "drmeter", "-f", "null", "-"]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=120)
    return True, {"raw_output": result.stderr[-2000:]}