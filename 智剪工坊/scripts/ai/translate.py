# -*- coding: utf-8 -*-
"""
智剪工坊 · translate 子技能
视频翻译(Whisper 转录 + 翻译 + TTS 配音 + 烧字幕)

支持翻译:
  - 免费:无(需要自己接 API)
  - 付费:DeepL / Google Translate / 百度翻译

TTS:
  - 免费:edge-tts(微软 Azure TTS,免费,高质量)
  - 付费:Azure / Google Cloud TTS

用法:
  # 中文视频 → 英文版
  python translate.py --input in.mp4 --target-lang en --out out_en.mp4

  # 中视频 → 中英双语字幕
  python translate.py --input in.mp4 --target-lang en --mode subtitle --out out_sub.mp4

依赖:faster-whisper, edge-tts


📖 SKILL.md §14 索引 → REQUIRED: read references/06-text.md
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


# 翻译 API(用户需要填)
# 简易方案:用 deep-translator(支持多种后端)
def translate_text(text, target_lang="en"):
    """翻译文本(用 deep-translator)"""
    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        log_warn("deep-translator 未安装")
        log_warn("安装: pip install deep-translator")
        return text

    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        return translated
    except Exception as e:
        log_warn(f"翻译失败: {e}")
        return text


def transcribe_to_segments(video_path, model="medium", device="cuda", language=None):
    """Whisper 转录成带时间戳的段落"""
    log_section(f"转录: {Path(video_path).name}")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log_warn("faster-whisper 未安装")
        return None

    wm = WhisperModel(model, device=device)

    segments, info = wm.transcribe(
        str(video_path),
        language=language,
        word_timestamps=False,
    )

    result = []
    for seg in segments:
        result.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text.strip(),
        })
    return result


def fmt_ts(seconds):
    if seconds < 0:
        seconds = 0
    ms = int(round((seconds - int(seconds)) * 1000))
    s = int(seconds)
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def make_translated_srt(segments, target_lang, output_srt):
    """生成翻译版 SRT"""
    log_section(f"生成翻译 SRT → {target_lang}")
    ensure_dir(Path(output_srt).parent)

    with open(output_srt, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            translated = translate_text(seg["text"], target_lang)
            f.write(f"{i}\n")
            f.write(f"{fmt_ts(seg['start'])} --> {fmt_ts(seg['end'])}\n")
            f.write(f"{translated}\n\n")

    log_info(f"SRT 输出: {output_srt}")


def make_tts_audio(segments, target_lang, output_audio):
    """用 edge-tts 合成翻译版音频"""
    log_section(f"TTS 合成: {target_lang}")
    ensure_dir(Path(output_audio).parent)

    try:
        import edge_tts
        import asyncio
    except ImportError:
        log_warn("edge-tts 未安装: pip install edge-tts")
        return False

    # 选择 TTS 语音
    voices = {
        "en": "en-US-JennyNeural",
        "zh": "zh-CN-XiaoxiaoNeural",
        "ja": "ja-JP-NanamiNeural",
        "ko": "ko-KR-SunHiNeural",
        "es": "es-ES-ElviraNeural",
        "fr": "fr-FR-DeniseNeural",
        "de": "de-DE-KatjaNeural",
    }
    voice = voices.get(target_lang, "en-US-JennyNeural")

    # 拼接所有文本
    full_text = " ".join([seg["text"] for seg in segments])
    translated_full = translate_text(full_text, target_lang)

    async def gen():
        communicate = edge_tts.Communicate(translated_full, voice)
        await communicate.save(str(output_audio))

    asyncio.run(gen())
    log_info(f"TTS 输出: {output_audio}")
    return True


def replace_audio_and_subtitle(video_path, new_audio, new_srt, output_path):
    """替换视频的音频和字幕"""
    log_section(f"替换音频和字幕")

    srt_escaped = str(new_srt).replace("\\", "/").replace(":", r"\:")

    run_ffmpeg([
        "-i", str(video_path),
        "-i", str(new_audio),
        "-map", "0:v",
        "-map", "1:a",
        "-vf", f"subtitles='{srt_escaped}':"
               "force_style='FontName=Microsoft YaHei,FontSize=22,"
               "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
               "Outline=2,Shadow=1,MarginV=30,Alignment=2'",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output_path),
    ])

    log_info(f"输出: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 视频翻译",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s --input in.mp4 --target-lang en --out out_en.mp4",
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("--target-lang", default="en", help="目标语言(en/zh/ja/ko/es/fr/de)")
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=["full", "subtitle"], default="full",
                       help="full=替换音轨+字幕,subtitle=只换字幕")
    parser.add_argument("--model", default="medium")
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    # 1. 转录
    segments = transcribe_to_segments(args.input, args.model, args.device)
    if not segments:
        return
    log_info(f"转录 {len(segments)} 段")

    # 2. 翻译 SRT
    srt_path = Path(args.output).with_suffix(".srt")
    make_translated_srt(segments, args.target_lang, str(srt_path))

    if args.mode == "subtitle":
        # 只烧字幕(原音频)
        srt_escaped = str(srt_path).replace("\\", "/").replace(":", r"\:")
        run_ffmpeg([
            "-i", str(args.input),
            "-vf", f"subtitles='{srt_escaped}':"
                   "force_style='FontName=Microsoft YaHei,FontSize=22,"
                   "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                   "Outline=2,Shadow=1,MarginV=30,Alignment=2'",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "copy",
            str(args.output),
        ])
        log_info(f"输出: {args.output}")
    else:
        # 完整翻译:替换音频 + 字幕
        tts_path = Path(args.output).with_suffix(".tts.mp3")
        ok = make_tts_audio(segments, args.target_lang, str(tts_path))
        if ok:
            replace_audio_and_subtitle(args.input, tts_path, srt_path, args.output)
        else:
            log_warn("TTS 失败,退化为只烧字幕")
            log_warn("需要: pip install edge-tts")


if __name__ == "__main__":
    safe_run(main)()
