# -*- coding: utf-8 -*-
"""
智剪工坊 · reverse 子技能
视频倒放(可同时倒放音频)

用法:
  python reverse.py --input in.mp4 --output out.mp4
  python reverse.py --input in.mp4 --output out.mp4 --no-audio  # 不倒放音频(更简单)


📖 SKILL.md §14 索引 → REQUIRED: read references/04-cinematic.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_section, safe_run,
)


def reverse(input_path, output_path, reverse_audio=True):
    log_section(f"倒放 {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    vf = "reverse"
    af = "areverse" if reverse_audio else "anull"

    run_ffmpeg([
        "-i", str(input_path),
        "-vf", vf,
        "-af", af,
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 视频倒放",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s --input in.mp4 --output out.mp4",
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", required=True)
    parser.add_argument("--no-audio", dest="reverse_audio", action="store_false", help="不倒放音频")
    args = parser.parse_args()
    reverse(args.input, args.output, args.reverse_audio)


if __name__ == "__main__":
    safe_run(main)()
