# -*- coding: utf-8 -*-
"""
智剪工坊 · xfade 子技能
两段视频之间加转场(xfade filter,支持 60+ 种转场)

用法:
  python xfade.py --a clip1.mp4 --b clip2.mp4 --type fade --duration 1 --output joined.mp4
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_error, log_section, safe_run, ParamError,
)


# 常用转场类型(完整列表见 SKILL.md / references/02-transitions.md)
TRANSITIONS = [
    "fade", "dissolve", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "circleopen", "circleclose", "fadeblack", "fadewhite",
    "radial", "squeeze", "pixelize", "hlslice", "hrslice",
    "vuslice", "vdslice", "diagtl", "diagtr",
]


def xfade(a, b, transition, duration, output, offset=None, custom_offset=None):
    """两段视频加转场拼接"""
    log_section(f"xfade: {Path(a).name} + {transition} + {Path(b).name}")

    if transition not in TRANSITIONS:
        log_warn(f"转场类型 {transition} 不在常用列表,试试 ffmpeg -h filter=xfade 查更多")
        log_warn(f"常用: {', '.join(TRANSITIONS)}")

    duration_a = get_duration(a)
    duration_b = get_duration(b)

    if offset is None:
        # 默认:转场发生在 A 末尾(让 A 和 B 看起来无缝)
        offset = duration_a - duration
        log_info(f"自动计算 offset: {offset:.2f}s (A 末尾)")

    if custom_offset is not None:
        offset = custom_offset

    ensure_dir(Path(output).parent)

    # xfade filter(只处理视频,音频用 acrossfade)
    run_ffmpeg([
        "-i", str(a),
        "-i", str(b),
        "-filter_complex",
        f"[0:v][1:v]xfade=transition={transition}:duration={duration}:offset={offset}[v];"
        f"[0:a][1:a]acrossfade=d={duration}[a]",
        "-map", "[v]",
        "-map", "[a]",
        *DEFAULT_ENCODE_ARGS,
        str(output),
    ])
    log_info(f"输出: {output} ({get_duration(output):.1f}s)")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 视频转场(xfade)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
常用转场: fade / dissolve / wipeleft / circleopen / fadeblack / radial / pixelize
完整列表: 60+ 种,见 references/02-transitions.md

示例:
  %(prog)s --a clip1.mp4 --b clip2.mp4 --type fade --duration 1 --out joined.mp4
  %(prog)s --a a.mp4 --b b.mp4 --type dissolve --duration 0.5 --offset 5 --out out.mp4
        """,
    )
    parser.add_argument("--a", required=True, help="视频 A(先)")
    parser.add_argument("--b", required=True, help="视频 B(后)")
    parser.add_argument("--type", default="fade", help=f"转场类型(默认 fade,可选: {', '.join(TRANSITIONS[:5])}...)")
    parser.add_argument("--duration", type=float, default=1.0, help="转场时长(秒,默认 1)")
    parser.add_argument("--offset", type=float, default=None, help="转场起始时间(相对 A,默认 A 末尾)")
    parser.add_argument("--output", dest="output", required=True, help="输出视频")
    args = parser.parse_args()
    xfade(args.a, args.b, args.type, args.duration, args.output, args.offset)


if __name__ == "__main__":
    safe_run(main)()
