# -*- coding: utf-8 -*-
"""
智剪工坊 · cut 子技能
剪切 / 拼接视频,统一 1080x1920 竖屏 + 30 fps + libx264 编码

用法:
  # 剪切
  python cut.py trim --input video.mp4 --ss 0 --t 30 --output clip.mp4

  # 拼接(用文件列表)
  python cut.py concat --list clips.txt --output joined.mp4


📖 SKILL.md §14 索引 → REQUIRED: read references/01-cutting.md
"""
import argparse
import sys
from pathlib import Path

# 引入公共库
sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    unified_vf, ensure_dir, require_param, validate_resolution,
    log_info, log_warn, log_error, log_section, safe_run, SKILL_ROOT,
)


def trim(input_path, ss, t, output_path, resolution="1080:1920", fps=30):
    """剪切单段视频"""
    log_section(f"剪切 {Path(input_path).name} (ss={ss}, t={t})")
    ensure_dir(Path(output_path).parent)

    run_ffmpeg([
        "-ss", str(ss),
        "-i", str(input_path),
        "-t", str(t),
        "-vf", unified_vf(resolution, fps),
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


def concat(list_file, output_path, resolution="1080:1920", fps=30):
    """按文件列表拼接(concat demuxer)"""
    log_section(f"拼接 {list_file} → {output_path}")
    ensure_dir(Path(output_path).parent)

    run_ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-vf", unified_vf(resolution, fps),
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 视频剪切/拼接",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s trim --input in.mp4 --ss 0 --t 30 --out clip.mp4
  %(prog)s concat --list clips.txt --out joined.mp4
        """,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # trim
    p_trim = sub.add_parser("trim", help="剪切单段")
    p_trim.add_argument("-i", "--input", required=True, help="输入视频")
    p_trim.add_argument("--start", type=float, default=0, help="起始时间(秒)")
    p_trim.add_argument("--t", type=float, required=True, help="时长(秒)")
    p_trim.add_argument("-o", "--output", required=True, help="输出视频")
    p_trim.add_argument("--resolution", default="1080:1920", help="输出分辨率")
    p_trim.add_argument("--fps", type=int, default=30, help="帧率")

    # concat
    p_concat = sub.add_parser("concat", help="拼接多段(用文件列表)")
    p_concat.add_argument("--list", required=True, help="文件列表 txt(每行 file 'path')")
    p_concat.add_argument("-o", "--output", required=True, help="输出视频")
    p_concat.add_argument("--resolution", default="1080:1920", help="输出分辨率")
    p_concat.add_argument("--fps", type=int, default=30, help="帧率")

    args = parser.parse_args()

    if args.cmd == "trim":
        trim(args.input, args.start, args.t, args.output, args.resolution, args.fps)
    elif args.cmd == "concat":
        concat(args.list, args.output, args.resolution, args.fps)


if __name__ == "__main__":
    safe_run(main)()
