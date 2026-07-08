# -*- coding: utf-8 -*-
"""
智剪工坊 · asr/burn_subtitle 子技能（音频链路 L6: 合成）
将 SRT 字幕烧录到视频

来源: 从 scripts/video_subtitle.py 的 burn_subtitle() 函数独立出来
本文件为 asr/ 链路合成端入口。

依赖: ffmpeg（subtitles filter）
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_section, safe_run,
)


def burn_subtitle(video, srt, output, font_size=22):
    """烧录 SRT 字幕到视频。

    Args:
        video: 输入视频
        srt: SRT 字幕文件
        output: 输出视频路径
        font_size: 字幕字号（默认 22）
    """
    log_section(f"烧字幕: {Path(srt).name} → {Path(video).name}")
    ensure_dir(Path(output).parent)

    # SRT 路径中的特殊字符要转义（Windows path + colon）
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
        description="智剪工坊 · SRT 字幕烧录到视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s --video in.mp4 --srt subtitles.srt --output out_subtitled.mp4\n  %(prog)s --video in.mp4 --srt subtitles.srt --output out.mp4 --font-size 26",
    )
    parser.add_argument("--video", required=True, help="输入视频")
    parser.add_argument("--srt", required=True, help="SRT 字幕文件")
    parser.add_argument("--output", required=True, help="输出视频")
    parser.add_argument("--font-size", type=int, default=22, help="字幕字号（默认 22）")
    args = parser.parse_args()
    burn_subtitle(args.video, args.srt, args.output, args.font_size)


if __name__ == "__main__":
    safe_run(main)
