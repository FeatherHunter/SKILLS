# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/extract 子技能（音频链路 L3: 提取）
从视频提取音频 + 音频淡入淡出

来源: 从 scripts/edit.py（extract-audio + fade-audio 子命令）
edit.py 保留 backward-compat，本文件为 audio/ 链路主入口。

依赖: ffmpeg
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_section, safe_run,
)


def extract_audio(input_path, output_path, fmt="mp3"):
    """从视频提取音频流。

    Args:
        input_path: 输入视频
        output_path: 输出音频文件
        fmt: 输出格式（mp3 / wav / aac）
    """
    log_section(f"extract-audio {Path(input_path).name} → .{fmt}")
    ensure_dir(Path(output_path).parent)
    codec_map = {
        "mp3": "libmp3lame",
        "wav": "pcm_s16le",
        "aac": "aac",
    }
    codec = codec_map.get(fmt, "copy")
    run_ffmpeg([
        "-i", str(input_path),
        "-vn",
        "-acodec", codec,
        "-y", str(output_path),
    ])
    log_info(f"输出: {output_path}")


def fade_audio(input_path, output_path, fade_in=0, fade_out=0, fps=30):
    """音频淡入淡出（秒）。

    Args:
        input_path: 输入音频/视频
        output_path: 输出文件
        fade_in: 淡入秒数
        fade_out: 淡出秒数
        fps: 帧率（用于视频输出）
    """
    log_section(f"fade-audio in={fade_in}s out={fade_out}s {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)
    duration = get_duration(input_path)
    fade_out_st = max(0, duration - fade_out)
    af_parts = []
    if fade_in > 0:
        af_parts.append(f"afade=t=in:st=0:d={fade_in}")
    if fade_out > 0:
        af_parts.append(f"afade=t=out:st={fade_out_st}:d={fade_out}")
    af = ",".join(af_parts) if af_parts else "anull"
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"fps={fps}",
        "-af", af,
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


# ========== CLI ==========
def main():
    parser = argparse.ArgumentParser(description="智剪工坊 · 音频提取与淡入淡出")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # extract-audio
    p = subparsers.add_parser("extract", help="从视频提取音频")
    p.add_argument("-i", "--input", required=True, help="输入视频")
    p.add_argument("--output", required=True, help="输出音频")
    p.add_argument("--format", default="mp3", choices=["mp3", "wav", "aac"],
                   help="输出格式（默认 mp3）")

    # fade-audio
    p2 = subparsers.add_parser("fade", help="音频淡入淡出")
    p2.add_argument("-i", "--input", required=True, help="输入音频/视频")
    p2.add_argument("--output", required=True, help="输出文件")
    p2.add_argument("--fade-in", type=float, default=0, help="淡入秒数")
    p2.add_argument("--fade-out", type=float, default=0, help="淡出秒数")

    args = parser.parse_args()

    if args.cmd == "extract":
        extract_audio(args.input, args.output, args.format)
    elif args.cmd == "fade":
        fade_audio(args.input, args.output, args.fade_in, args.fade_out)


if __name__ == "__main__":
    safe_run(main)
