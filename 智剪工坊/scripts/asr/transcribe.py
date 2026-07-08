# -*- coding: utf-8 -*-
"""
智剪工坊 · asr/transcribe 子技能（音频链路 L6: 分析）
用 Whisper 将音频/视频转录为 SRT

来源: scripts/video_subtitle.py（126 行）
本文件为 asr/ 链路主入口，old 路径 video_subtitle.py 保留 backward-compat。

链路位置:
  L1 合成 → L2 变换 → L3 提取 → L4 降噪/分离 → L5 说话人分离
  → L6 ASR ← 本文件（用干净人声做转录，准确率最高）

典型链路用法:
  # 推荐：先 denoise（降噪）再转录，准确率提升
  python audio/denoise.py --input video.mp4 --output clean.wav --mode afftdn
  python asr/transcribe.py --input clean.wav --srt out.srt

  # 完整对话链路（推荐用于多人对话）
  python audio/separate.py --input video.mp4 --output vocals.wav --stem vocals
  python audio/diarize.py --input vocals.wav --output diar.json
  python asr/transcribe.py --input vocals.wav --srt audio.srt
  python asr/speaker_srt.py --diarize diar.json --srt audio.srt --output audio_speaker.srt

依赖: faster-whisper
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS, unified_vf,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


def transcribe_to_srt(audio_or_video, srt_path, model="medium", device="cuda", language=None):
    """用 Whisper 转录音频/视频，生成 SRT。

    Args:
        audio_or_video: 输入音频或视频
        srt_path: 输出 SRT 路径
        model: Whisper 模型（tiny/base/small/medium/large-v3）
        device: cuda / cpu
        language: 强制语言代码（None=自动检测）

    Returns:
        True（成功）；False（失败）
    """
    log_section(f"Whisper 转录: {Path(audio_or_video).name}")
    ensure_dir(Path(srt_path).parent)

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log_warn("faster-whisper 未安装")
        log_warn("安装: pip install faster-whisper")
        return False

    log_info(f"加载模型: {model} ({device})")
    wm = WhisperModel(model, device=device)

    log_info("开始转录...")
    segments, info = wm.transcribe(
        str(audio_or_video),
        language=language,
        word_timestamps=False,
        vad_filter=True,
    )

    # 生成 SRT
    with open(srt_path, "w", encoding="utf-8") as f:
        idx = 0
        for seg in segments:
            idx += 1
            start = fmt_ts(seg.start)
            end = fmt_ts(seg.end)
            text = seg.text.strip()
            f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

    log_info(f"SRT 输出: {srt_path} ({idx} 段)")
    return True


def fmt_ts(seconds):
    """格式化 SRT 时间戳（HH:MM:SS,mmm）。"""
    if seconds < 0:
        seconds = 0
    ms = int(round((seconds - int(seconds)) * 1000))
    s = int(seconds)
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ========== CLI ==========
def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · Whisper ASR 转录（音频 → SRT）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s --input in.mp4 --srt subtitles.srt\n  %(prog)s --input clean.wav --srt audio.srt --model small --device cpu",
    )
    parser.add_argument("-i", "--input", required=True, help="输入视频/音频")
    parser.add_argument("--srt", required=True, help="输出 SRT 路径")
    parser.add_argument("--model", default="medium",
                       help="Whisper 模型（tiny/base/small/medium/large-v3，默认 medium）")
    parser.add_argument("--device", default="cuda", help="cuda / cpu")
    parser.add_argument("--lang", help="强制语言代码（默认自动检测）")
    args = parser.parse_args()

    ok = transcribe_to_srt(args.input, args.srt, args.model, args.device, args.lang)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)
