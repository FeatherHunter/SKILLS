# -*- coding: utf-8 -*-
"""
智剪工坊 · auto_subtitle 子技能
AI 字幕自动生成(Whisper 转录 + 烧录到视频)

用法:
  # 1. 只生成 SRT(不烧录)
  python auto_subtitle.py --input in.mp4 --mode transcribe --out subtitles.srt

  # 2. 直接烧录到视频
  python auto_subtitle.py --input in.mp4 --mode burn --out out.mp4

  # 3. 生成双语字幕(中文 + 英文)
  python auto_subtitle.py --input in.mp4 --mode burn --lang zh --translate en --out out.mp4

依赖:faster-whisper


📖 SKILL.md §14 索引 → REQUIRED: read references/06-text.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS, unified_vf,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


def transcribe_to_srt(audio_or_video, srt_path, model="medium", device="cuda", language=None):
    """用 Whisper 转录音频/视频,生成 SRT"""
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

    log_info(f"开始转录...")
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
            # 格式化时间戳
            start = fmt_ts(seg.start)
            end = fmt_ts(seg.end)
            text = seg.text.strip()
            f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

    log_info(f"SRT 输出: {srt_path} ({idx} 段)")
    return True


def fmt_ts(seconds):
    """格式化 SRT 时间戳"""
    if seconds < 0:
        seconds = 0
    ms = int(round((seconds - int(seconds)) * 1000))
    s = int(seconds)
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def burn_subtitle(video, srt, output, font_size=22):
    """烧录字幕到视频"""
    log_section(f"烧字幕: {Path(srt).name} → {Path(video).name}")
    ensure_dir(Path(output).parent)

    srt_escaped = str(srt).replace("\\", "/").replace(":", r"\:")

    run_ffmpeg([
        "-i", str(video),
        "-vf", f"subtitles='{srt_escaped}':"
               f"force_style='FontName=Microsoft YaHei,FontSize={font_size},"
               "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
               "Outline=2,Shadow=1,MarginV=30,Alignment=2'",
        *DEFAULT_ENCODE_ARGS,
        str(output),
    ])
    log_info(f"输出: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · AI 字幕自动生成(Whisper)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s --input in.mp4 --mode transcribe --out sub.srt\n  %(prog)s --input in.mp4 --mode burn --out out.mp4",
    )
    parser.add_argument("-i", "--input", required=True, help="输入视频")
    parser.add_argument("--mode", choices=["transcribe", "burn"], default="burn",
                       help="transcribe=只生成 SRT, burn=直接烧录")
    parser.add_argument("--output", required=True, help="输出(SRT 或视频)")
    parser.add_argument("--model", default="medium", help="Whisper 模型(tiny/base/small/medium/large-v3)")
    parser.add_argument("--device", default="cuda", help="cuda / cpu")
    parser.add_argument("--lang", help="指定语言(默认自动检测)")
    parser.add_argument("--font-size", type=int, default=22, help="字幕字号")
    args = parser.parse_args()

    if args.mode == "transcribe":
        transcribe_to_srt(args.input, args.output, args.model, args.device, args.lang)
    else:
        # burn:先转录到 SRT,再烧录
        srt_temp = Path(args.output).with_suffix(".srt")
        ok = transcribe_to_srt(args.input, str(srt_temp), args.model, args.device, args.lang)
        if ok:
            burn_subtitle(args.input, srt_temp, args.output, args.font_size)


if __name__ == "__main__":
    safe_run(main)()
