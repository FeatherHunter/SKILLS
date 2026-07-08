# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/diarize 子技能（音频链路 L5: 说话人分离）
区分不同说话人，输出「谁在第几秒说了什么」

本文件为新增文件（v1.4）。

链路位置:
  L1 合成 → L2 变换 → L3 提取 → L4 降噪/分离 → L5 说话人分离 ← 本文件
  → L6 ASR（asr/transcribe.py 接 diarize 输出生成带说话人的 SRT）

说话人分离（Speaker Diarization）= 回答「谁在说话」。
常用于：访谈视频、对话录音、会议记录。

典型输出格式:
  SPEAKER 01  (confidence: 0.94)
  00:00:00,000 --> 00:00:03,500
  今天我们聊聊饮食记录

  SPEAKER 02  (confidence: 0.91)
  00:00:03,600 --> 00:00:07,200
  好的，我也想听听你的方法

用法:
  # pyannote（推荐，本地）
  python audio/diarize.py --input audio.wav --output diar.json --backend pyannote

  # 串联: separate（提取人声）→ diarize（说话人分离）→ transcribe（SRT）
  python audio/diarize.py --input audio.wav --output diar.json --backend pyannote
  python asr/transcribe.py --input audio.wav --srt audio.srt
  python asr/speaker_srt.py --diarize diar.json --srt audio.srt --output audio_speaker.srt

依赖:
  - pyannote.audio（pip install pyannote.audio）：开源说话人分离，需要 pyannote 授权
  - azure-speech-sdk（可选，云端，高精度）
  - openai-whisper / faster-whisper（ASR 用，已在 asr/transcribe.py 依赖）
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    get_duration, ensure_dir,
    log_info, log_warn, log_error, log_section, safe_run,
)


def diarize_pyannote(audio_path, output_json, min_speakers=1, max_speakers=8):
    """用 pyannote.audio 做说话人分离。

    Args:
        audio_path: 输入音频（建议先用 separate.py 提取人声）
        output_json: 输出 JSON 文件路径
        min_speakers: 最少说话人数（用于引导模型）
        max_speakers: 最多说话人数

    Returns:
        output_json 路径（成功）；None（失败）

    输出格式:
    {
      "audio": "path/to/audio.wav",
      "segments": [
        {"start": 0.0, "end": 3.5, "speaker": "SPEAKER_00", "confidence": 0.94},
        {"start": 3.6, "end": 7.2, "speaker": "SPEAKER_01", "confidence": 0.91},
        ...
      ]
    }
    """
    log_section(f"pyannote 说话人分离: {Path(audio_path).name}")
    ensure_dir(Path(output_json).parent)

    try:
        import torch
        from pyannote.audio import Pipeline
    except ImportError:
        log_error("pyannote.audio 未安装")
        log_error("安装: pip install pyannote.audio")
        log_error("注意: 需要申请 pyannote 授权（https://huggingface.co/pyannote）")
        return None

    log_info("加载 pyannote 流水线...")
    try:
        # 加载预训练模型（需要 HuggingFace token）
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=None,  # 用户需配置 HF token
        )
    except Exception as e:
        log_error(f"加载 pyannote 模型失败: {e}")
        return None

    if torch.cuda.is_available():
        pipeline = pipeline.to(torch.device("cuda"))
        log_info("使用 GPU 加速")
    else:
        log_warn("无 GPU，使用 CPU（速度较慢）")

    log_info("开始说话人分离...")
    try:
        diarization = pipeline(
            str(audio_path),
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
    except Exception as e:
        log_error(f"分离失败: {e}")
        return None

    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "start": round(turn.start, 3),
            "end": round(turn.end, 3),
            "speaker": speaker,
            "confidence": None,  # pyannote 3.x 支持 confidence
        })

    result = {
        "audio": str(audio_path),
        "duration": get_duration(audio_path),
        "min_speakers": min_speakers,
        "max_speakers": max_speakers,
        "speaker_count": len({s["speaker"] for s in segments}),
        "segments": segments,
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log_info(f"说话人数: {result['speaker_count']}")
    log_info(f"分段数: {len(segments)}")
    log_info(f"输出: {output_json}")
    return str(output_json)


def diarize_azure(audio_path, output_json):
    """用 Azure Speech SDK 做说话人分离（占位，云端方案）。"""
    log_section(f"Azure 说话人分离: {Path(audio_path).name}")
    log_warn("Azure Speech SDK 说话人分离集成待补")
    log_warn("文档: https://learn.microsoft.com/azure/ai-services/speech-service/conversation-transcription")
    # TODO: 实现 Azure SDK 调用
    return None


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 说话人分离（区分不同说话人）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""用法示例:
  # 基本分离（pyannote）
  %(prog)s --input audio.wav --output diar.json

  # 指定说话人数量范围
  %(prog)s --input audio.wav --output diar.json --min-speakers 1 --max-speakers 3

  # Azure 云端方案（待实现）
  %(prog)s --input audio.wav --output diar.json --backend azure

完整链路（推荐）:
  # 1. 提取人声（separate.py）
  python audio/separate.py --input video.mp4 --output vocals.wav --stem vocals

  # 2. 说话人分离（diarize.py）→ 生成 diar.json
  python audio/diarize.py --input vocals.wav --output diar.json

  # 3. ASR 转录（asr/transcribe.py）
  python asr/transcribe.py --input vocals.wav --srt audio.srt

  # 4. 合并说话人 + ASR → 带说话人的 SRT（asr/speaker_srt.py）
  python asr/speaker_srt.py --diarize diar.json --srt audio.srt --output audio_speaker.srt
        """,
    )
    parser.add_argument("-i", "--input", required=True, help="输入音频（建议先 run separate.py 提取人声）")
    parser.add_argument("--output", required=True, help="输出 JSON 文件")
    parser.add_argument("--backend", default="pyannote",
                        choices=["pyannote", "azure"],
                        help="说话人分离后端（默认 pyannote）")
    parser.add_argument("--min-speakers", type=int, default=1,
                        help="最少说话人数（默认 1）")
    parser.add_argument("--max-speakers", type=int, default=8,
                        help="最多说话人数（默认 8）")

    args = parser.parse_args()
    ensure_dir(Path(args.output).parent)

    result = None
    if args.backend == "pyannote":
        result = diarize_pyannote(args.input, args.output,
                                  args.min_speakers, args.max_speakers)
    elif args.backend == "azure":
        result = diarize_azure(args.input, args.output)

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)
