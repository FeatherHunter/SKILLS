# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/denoise 子技能（v1.5 迁移版本）

调用 lib/ffmpeg/audio/denoise.py 的降噪能力。
本文件作为用户入口 CLI + 业务参数封装。

音频链路层级:
  L1 合成 → mix
  L2 变换 → voice, beat, normalize
  L3 提取 → extract
  L4 降噪/分离 → 本文件
  L5 说话人 → diarize
  L6 ASR → asr/transcribe

用法:
  python audio/denoise.py --input audio.wav --output audio_clean.wav --mode afftdn
  python audio/denoise.py --input video.mp4 --output voice.wav --mode afftdn --extract-voice

依赖:
  - lib.ffmpeg.audio.denoise（必须可用）
  - faster-whisper / ffmpeg 不直接依赖（由 lib 包处理）
"""
import argparse
import sys
from pathlib import Path

# 让 lib/ffmpeg/audio 可被 import
# 设置 sys.path：保证 SKILL_ROOT 和 lib 都在 path（但 append，不覆盖）
_SKILL_ROOT = Path(__file__).parent.parent.parent  # SKILL_ROOT/
_LIB_DIR = _SKILL_ROOT / "lib"

# 用 append（不会覆盖），并且只在路径里不存在时才加入
def _ensure_in_path(p):
    p = str(p)
    if p not in sys.path:
        sys.path.append(p)

_ensure_in_path(str(_SKILL_ROOT))
_ensure_in_path(str(_LIB_DIR))

from common import (
    ensure_dir, log_info, log_section, log_warn, log_error, safe_run,
)
from ffmpeg.audio.denoise import (
    denoise_fft, denoise_wavelet, denoise_rnn,
    remove_click, remove_clip, aap_denoise,
)


# ========== 业务模式 → lib 函数映射 ==========
DENOISE_MODES = {
    "afftdn": {
        "description": "ffmpeg FFT 降噪（默认，中等强度）",
        "params": {"nr": 10, "nf": -25, "nl": 1},
    },
    "rnnoise": {
        "description": "RNNoise 神经网络降噪（需模型文件）",
        "params": {"model_path": "denoise.model"},  # 占位
    },
    "light": {
        "description": "轻度降噪（afftdn 轻档）",
        "params": {"nr": 5, "nf": -15, "nl": 0},
    },
    "aggressive": {
        "description": "重度降噪（afftdn 高档）",
        "params": {"nr": 20, "nf": -40, "nl": 2},
    },
    "wavelet": {
        "description": "小波降噪（afwtdn）",
        "params": {"sigma": 2},
    },
    "aap": {
        "description": "仿射投影算法降噪（高阶自适应）",
        "params": {"projection": 2, "order": 64, "mu": 1.0},
    },
}


def denoise(input_path, output_path, mode="afftdn"):
    """音频降噪（v1.5 迁移版本：调 lib/ffmpeg/audio/denoise）。

    Args:
        input_path: 输入音频/视频
        output_path: 输出音频文件
        mode: 降噪模式（afftdn / rnnoise / light / aggressive / wavelet / aap）

    Returns:
        output 路径（成功）；None（失败）
    """
    log_section(f"音频降噪 mode={mode}: {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    if mode not in DENOISE_MODES:
        log_error(f"未知降噪模式 {mode}，可用: {list(DENOISE_MODES.keys())}")
        return None

    params = DENOISE_MODES[mode]["params"]
    log_info(f"降噪参数: {params}")

    # 调用 lib
    success = False
    try:
        if mode == "afftdn":
            success, _ = denoise_fft(input_path, output_path,
                                     nr=params["nr"], nf=params["nf"], nl=params["nl"])
        elif mode == "light":
            success, _ = denoise_fft(input_path, output_path,
                                     nr=params["nr"], nf=params["nf"], nl=params["nl"])
        elif mode == "aggressive":
            success, _ = denoise_fft(input_path, output_path,
                                     nr=params["nr"], nf=params["nf"], nl=params["nl"])
        elif mode == "rnnoise":
            success, _ = denoise_rnn(input_path, output_path, params["model_path"])
        elif mode == "wavelet":
            success, _ = denoise_wavelet(input_path, output_path, sigma=params["sigma"])
        elif mode == "aap":
            success, _ = aap_denoise(input_path, output_path,
                                     projection=params["projection"],
                                     order=params["order"], mu=params["mu"])
    except Exception as e:
        log_error(f"降噪失败: {e}")
        return None

    if not success:
        log_error("降噪失败（lib 返回失败）")
        return None

    log_info(f"输出: {output_path}")
    return str(output_path)


def denoise_extract_voice(video_path, output_wav, mode="afftdn"):
    """视频 → 提取音频 → 降噪 → 输出 WAV（链式调用）。

    流程：
      1. lib.extract_audio 提取音频流
      2. denoise 降噪
    """
    log_section(f"降噪提取人声: {Path(video_path).name}")
    ensure_dir(Path(output_wav).parent)

    # 临时文件路径
    import tempfile
    tmp_audio = Path(tempfile.gettempdir()) / f"{Path(video_path).stem}_extracted.wav"

    try:
        # 步骤 1: 提取音频（调 lib）
        from ffmpeg.audio.extract import extract_audio
        success, _ = extract_audio(str(video_path), str(tmp_audio), fmt="wav")
        if not success:
            log_error(f"提取音频失败: {video_path}")
            return None

        # 步骤 2: 降噪
        result = denoise(str(tmp_audio), output_wav, mode)
        return result
    finally:
        # 确保清理临时文件
        try:
            tmp_audio.unlink()
        except Exception:
            pass


# ========== CLI ==========
def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 音频降噪（调 lib/ffmpeg/audio/denoise）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""降噪模式:
  afftdn      FFT 降噪（默认，中等强度）
  rnnoise     RNNoise 神经网络（需模型文件）
  light       轻度降噪
  aggressive  重度降噪
  wavelet     小波降噪
  aap         仿射投影算法（高阶）

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
    safe_run(main)()