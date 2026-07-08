# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/denoise 子技能（音频链路 L4: 降噪）
音频降噪（ffmpeg afftdn / rnnoise 两种模式）

本文件为新增文件（v1.4）。

链路位置（L4）:
  L1 合成 → L2 变换 → L3 提取 → L4 降噪/分离 ← 本文件
  → L5 说话人分离 → L6 ASR

用法:
  # ffmpeg 内置降噪（afftdn，速度快，质量一般）
  python audio/denoise.py --input audio.wav --output audio_clean.wav --mode afftdn

  # RNNoise（质量高，需要编译版 ffmpeg 支持）
  python audio/denoise.py --input audio.wav --output audio_clean.wav --mode rnnoise

  # 降噪后直接提取人声（需要 separate.py）
  python audio/denoise.py --input video.mp4 --output voice.wav --mode afftdn --extract-voice

依赖: ffmpeg（RNNoise 需要 ffmpeg 编译时带 --enable-librnnoise）
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, ensure_dir,
    log_info, log_section, log_warn, safe_run,
)


# 降噪模式
DENOISE_MODES = {
    "afftdn": {
        "description": "ffmpeg 内置（fft 降噪，速度快，质量一般）",
        "params": "afftdn=nr=10:nf=-25:nl=1",
    },
    "rnnoise": {
        "description": "RNNoise（神经网络，质量高，需要 ffmpeg 带 librnnoise）",
        "params": "arnndn=model=denoise.model",
    },
    "light": {
        "description": "轻度降噪（afftdn 轻档，适合有人声的场景）",
        "params": "afftdn=nr=5:nf=-15:nl=0",
    },
    "aggressive": {
        "description": "重度降噪（afftdn 高档，适合纯音乐/录音质量差的场景）",
        "params": "afftdn=nr=20:nf=-40:nl=2",
    },
}


def denoise(input_path, output_path, mode="afftdn"):
    """音频降噪。

    Args:
        input_path: 输入音频/视频
        output_path: 输出音频文件
        mode: 降噪模式（afftdn / rnnoise / light / aggressive）

    Returns:
        output 路径（成功）；None（失败）
    """
    log_section(f"音频降噪 mode={mode}: {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    if mode not in DENOISE_MODES:
        log_warn(f"未知降噪模式 {mode}，可用: {list(DENOISE_MODES.keys())}")
        return None

    params = DENOISE_MODES[mode]["params"]
    log_info(f"降噪参数: {params}")

    run_ffmpeg([
        "-i", str(input_path),
        "-af", params,
        "-c:a", "pcm_s16le",
        "-y", str(output_path),
    ])
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")
    return str(output_path)


def denoise_extract_voice(video_path, output_wav, mode="afftdn"):
    """视频 → 提取音频 → 降噪 → 输出 WAV。

    相当于 extract_audio + denoise 串联。
    """
    log_section(f"降噪提取人声: {Path(video_path).name}")
    ensure_dir(Path(output_wav).parent)

    params = DENOISE_MODES.get(mode, DENOISE_MODES["afftdn"])["params"]
    run_ffmpeg([
        "-i", str(video_path),
        "-vn",
        "-af", params,
        "-c:a", "pcm_s16le",
        "-y", str(output_wav),
    ])
    log_info(f"输出: {output_wav}")
    return str(output_wav)


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 音频降噪（ffmpeg afftdn / RNNoise）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""降噪模式:
  afftdn      ffmpeg 内置 FFT 降噪（速度块，质量一般）
  rnnoise     神经网络降噪（质量高，需 ffmpeg 带 librnnoise）
  light       轻度降噪（afftdn 轻档，适合人声场景）
  aggressive  重度降噪（适合录音质量差或纯音乐）

示例:
  %(prog)s --input audio.wav --output audio_clean.wav --mode afftdn
  %(prog)s --input video.mp4 --output voice.wav --mode light --extract-voice
        """,
    )
    parser.add_argument("-i", "--input", required=True, help="输入音频/视频")
    parser.add_argument("--output", required=True, help="输出音频文件")
    parser.add_argument("--mode", default="afftdn",
                        choices=list(DENOISE_MODES.keys()),
                        help="降噪模式（默认 afftdn）")
    parser.add_argument("--extract-voice", action="store_true",
                        help="从视频提取音频 + 降噪（相当于 extract + denoise）")
    args = parser.parse_args()

    if args.extract_voice:
        result = denoise_extract_voice(args.input, args.output, args.mode)
    else:
        result = denoise(args.input, args.output, args.mode)

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)
