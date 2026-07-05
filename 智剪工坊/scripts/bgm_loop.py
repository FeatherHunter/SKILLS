# -*- coding: utf-8 -*-
"""
智剪工坊 · bgm_loop 子技能
给视频循环添加 BGM(混音,人声不被覆盖)

用法:
  python bgm_loop.py --video in.mp4 --bgm bgm.mp3 --volume 0.18 --output out.mp4


📖 SKILL.md §14 索引 → REQUIRED: read references/07-audio.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


def add_bgm_loop(video, bgm, output, video_volume=1.0, bgm_volume=0.18, fade_out=0):
    """给视频加循环 BGM"""
    log_section(f"加 BGM: {Path(bgm).name} → {Path(video).name}")

    video_dur = get_duration(video)
    bgm_dur = get_duration(bgm)
    log_info(f"视频时长: {video_dur:.1f}s, BGM 时长: {bgm_dur:.1f}s(将循环)")

    ensure_dir(Path(output).parent)

    # 构造 filter
    bgm_filter = f"volume={bgm_volume},aloop=loop=-1:size=2e9"
    if fade_out > 0:
        bgm_filter += f",afade=t=out:st={video_dur - fade_out}:d={fade_out}"

    filter_complex = (
        f"[0:a]volume={video_volume}[a0];"
        f"[1:a]{bgm_filter}[a1];"
        f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[a]"
    )

    run_ffmpeg([
        "-i", str(video),
        "-stream_loop", "-1",
        "-i", str(bgm),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[a]",
        *DEFAULT_ENCODE_ARGS,
        str(output),
    ])
    log_info(f"输出: {output} ({get_duration(output):.1f}s)")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 给视频加 BGM(自动循环)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --video vlog.mp4 --bgm bgm.mp3 --volume 0.18 --out vlog_with_bgm.mp4
  %(prog)s --video vlog.mp4 --bgm bgm.mp3 --volume 0.2 --fade-out 3 --out out.mp4
        """,
    )
    parser.add_argument("--input", dest="video", required=True, help="输入视频")
    parser.add_argument("--bgm", required=True, help="BGM 文件(短 BGM 会自动循环)")
    parser.add_argument("--volume", type=float, default=0.18, help="BGM 音量(0-1,默认 0.18 不盖人声)")
    parser.add_argument("--video-volume", type=float, default=1.0, help="原声音量")
    parser.add_argument("--fade-out", type=float, default=0, help="BGM 结尾淡出秒数(默认 0)")
    parser.add_argument("--output", required=True, help="输出视频")
    args = parser.parse_args()
    add_bgm_loop(args.video, args.bgm, args.output, args.video_volume, args.volume, args.fade_out)


if __name__ == "__main__":
    safe_run(main)()
