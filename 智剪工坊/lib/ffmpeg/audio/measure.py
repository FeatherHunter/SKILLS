# -*- coding: utf-8 -*-
"""
lib/ffmpeg/audio/measure.py — 测量 / 评估

封装 ffmpeg 音频测量类滤镜（用于质量评估、A/B 对比）:
  - apsnr        PSNR 测量（峰值信噪比）
  - asdr         SDR 测量（信噪失真比）
  - asisdr       SI-SDR（尺度不变信噪失真比）
  - axcorrelate  两流互相关（相似度检测）

测量类函数返回元数据 dict，不输出文件。
"""
import re
import subprocess
import sys
from pathlib import Path

_LIB_DIR = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(_LIB_DIR))


def measure_psnr(input_path, reference_path):
    """PSNR 测量（apsnr）— 比较两个音频的峰值信噪比。

    Args:
        input_path: 待评估音频
        reference_path: 参考音频
    Returns:
        dict: {'psnr_avg': dB, 'psnr_max': dB, ...}
    """
    af = "apsnr"
    cmd = [
        "ffmpeg", "-i", str(input_path), "-i", str(reference_path),
        "-lavfi", af, "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=300)

    # 解析 PSNR: 格式 "PSNR avg:65.43 max:78.21"
    psnr_avg = re.search(r"PSNR\s+avg:([\d.]+)", result.stderr)
    psnr_max = re.search(r"PSNR\s+max:([\d.]+)", result.stderr)
    psnr_min = re.search(r"PSNR\s+min:([\d.]+)", result.stderr)

    return {
        "psnr_avg_db": float(psnr_avg.group(1)) if psnr_avg else None,
        "psnr_max_db": float(psnr_max.group(1)) if psnr_max else None,
        "psnr_min_db": float(psnr_min.group(1)) if psnr_min else None,
        "raw_output": result.stderr[-500:],
    }


def measure_sdr(input_path, reference_path):
    """SDR 测量（asdr）— 信噪失真比。

    Args:
        input_path: 待评估音频
        reference_path: 参考音频
    Returns:
        dict: {'sdr': dB}
    """
    af = "asdr"
    cmd = [
        "ffmpeg", "-i", str(input_path), "-i", str(reference_path),
        "-lavfi", af, "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=300)

    # 解析 SDR: 格式 "SDR:18.45"
    sdr = re.search(r"SDR:\s*([-\d.]+)", result.stderr)
    return {
        "sdr_db": float(sdr.group(1)) if sdr else None,
        "raw_output": result.stderr[-500:],
    }


def measure_si_sdr(input_path, reference_path):
    """SI-SDR 测量（asisdr）— 尺度不变信噪失真比。

    Args:
        input_path: 待评估音频
        reference_path: 参考音频
    Returns:
        dict: {'si_sdr': dB}
    """
    af = "asisdr"
    cmd = [
        "ffmpeg", "-i", str(input_path), "-i", str(reference_path),
        "-lavfi", af, "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=300)

    si_sdr = re.search(r"SI-SDR:\s*([-\d.]+)", result.stderr)
    return {
        "si_sdr_db": float(si_sdr.group(1)) if si_sdr else None,
        "raw_output": result.stderr[-500:],
    }


def measure_correlation(input_path_1, input_path_2):
    """两流互相关（axcorrelate）— 相似度检测。

    Args:
        input_path_1, input_path_2: 待比较的两个音频
    Returns:
        dict: {'max_correlation': float, 'lag_seconds': float}
        接近 1.0 表示高度相似，接近 0 表示不相关
    """
    af = "axcorrelate"
    cmd = [
        "ffmpeg", "-i", str(input_path_1), "-i", str(input_path_2),
        "-lavfi", af, "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=300)

    max_corr = re.search(r"max correlation:\s*([-\d.]+)", result.stderr)
    lag = re.search(r"lag_seconds:\s*([-\d.]+)", result.stderr)

    return {
        "max_correlation": float(max_corr.group(1)) if max_corr else None,
        "lag_seconds": float(lag.group(1)) if lag else None,
        "raw_output": result.stderr[-500:],
    }