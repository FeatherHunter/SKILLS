# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/denoise.py — 降噪 / 去噪

封装 ffmpeg 音频降噪滤镜:
  - afftdn    FFT 降噪（默认，速度快）
  - afwtdn    小波降噪（对脉冲噪声好）
  - arnndn    RNNoise 神经网络降噪（质量高，需 ffmpeg 编译支持）
  - adeclick  去爆音（click）
  - adeclip   去削波失真（clipping）
"""
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))
from common import run_ffmpeg, get_duration, log_ffmpeg_call  # noqa: E402


@log_ffmpeg_call
def denoise_fft(input_path, output_path, nr=10, nf=-25, nl=1, format="wav"):
    """FFT 降噪（afftdn）。

    Args:
        input_path: 输入音频/视频
        output_path: 输出音频
        nr: 噪声衰减量 (dB)，默认 10
        nf: 噪声地板 (dB)，默认 -25
        nl: 非线性模式（0=线性，1=非线性保瞬态），默认 1
        format: 输出格式，默认 wav
    Returns:
        (success, output_path)
    """
    af = f"afftdn=nr={nr}:nf={nf}:nl={nl}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def denoise_wavelet(input_path, output_path, sigma=2):
    """小波降噪（afwtdn）。

    Args:
        sigma: 噪声标准差估计
    """
    af = f"afwtdn=sigma={sigma}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def denoise_rnn(input_path, output_path, model_path):
    """RNNoise 神经网络降噪（arnndn）。

    Args:
        model_path: RNN 模型文件路径（需 ffmpeg 编译时带 --enable-librnnoise）
    """
    af = f"arnndn=m='{model_path}'"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def remove_click(input_path, output_path, w=2):
    """去爆音（adeclick）。

    Args:
        w: 窗口大小
    """
    af = f"adeclick=w={w}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def remove_clip(input_path, output_path, w=5):
    """去削波失真（adeclip）。

    Args:
        w: 窗口大小
    """
    af = f"adeclip=w={w}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)


@log_ffmpeg_call
def aap_denoise(input_path, output_path, projection=2, order=64, mu=1.0):
    """仿射投影算法降噪（aap）。

    自适应降噪算法，比 afftdn 更激进，适合复杂噪声场景。

    Args:
        projection: 投影阶数（默认 2，范围 1-10）
        order: 滤波器阶数（默认 64，范围 8-512）
        mu: 步长（默认 1.0，范围 0.1-2.0）
    """
    af = f"aap=projection={projection}:order={order}:mu={mu}"
    run_ffmpeg(["-i", str(input_path), "-af", af, "-c:a", "pcm_s16le", "-y", str(output_path)])
    return True, str(output_path)