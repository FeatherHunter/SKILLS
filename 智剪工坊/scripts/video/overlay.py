# -*- coding: utf-8 -*-
"""
智剪工坊 · overlay 子技能
画中画(背景视频 + 小视频叠加)

用法:
  # 基础:把 b.mp4 叠到 a.mp4 的右上角
  python overlay.py --bg a.mp4 --pip b.mp4 --out out.mp4

  # 自定义位置(像素)
  python overlay.py --bg a.mp4 --pip b.mp4 --out out.mp4 --x 100 --y 100 --w 480

  # 时间段:只在 5-10s 显示画中画
  python overlay.py --bg a.mp4 --pip b.mp4 --out out.mp4 --start 5 --end 10


📖 SKILL.md §14 索引 → REQUIRED: read references/09-ai-features.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_section, safe_run,
)


# 位置预设
POSITIONS = {
    "top_left": (50, 50),
    "top_right": (W_DEFAULT := 1080 - 50 - 480, 50),
    "bottom_left": (50, 1080 - 50 - 270),  # 16:9 高度约 1920 - 270 - 50
    "bottom_right": (W_DEFAULT, 1080 - 50 - 270),
    "center": (W_DEFAULT // 2, 540),
}


def picture_in_picture(bg, pip, output, x=None, y=None, w=480, h=270,
                     start=None, end=None, opacity=1.0, border=False):
    log_section(f"画中画: {Path(pip).name} → {Path(bg).name}")
    ensure_dir(Path(output).parent)

    # 缩放 pip
    scale_filter = f"[1:v]scale={w}:{h}[pip]"

    # 边框(可选)
    if border:
        scale_filter = f"[1:v]scale={w}:{h},drawbox=x=0:y=0:w={w}:h={h}:color=white@1:t=4[pip]"

    # 时间段(可选)
    time_filter = ""
    if start is not None and end is not None:
        time_filter = f":enable='between(t,{start},{end})'"

    # 不透明度
    opacity_filter = ""
    if opacity < 1.0:
        scale_filter = f"[1:v]scale={w}:{h},format=yuva420p,colorchannelmixer=aa={opacity}[pip]"

    # 位置
    if x is None or y is None:
        x, y = 1080 - w - 50, 50  # 默认右上

    # overlay filter
    overlay_filter = f"[0:v][pip]overlay={x}:{y}{time_filter}[v]"

    # 音频:用背景视频的音频(简单)
    audio_filter = "[0:a]anull[a]"

    filter_complex = f"{scale_filter};{overlay_filter};{audio_filter}"

    run_ffmpeg([
        "-i", str(bg),
        "-i", str(pip),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        *DEFAULT_ENCODE_ARGS,
        str(output),
    ])
    log_info(f"输出: {output} ({get_duration(output):.1f}s)")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 画中画",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s --bg a.mp4 --pip b.mp4 --out out.mp4 --position top_right",
    )
    parser.add_argument("--bg", required=True, help="背景视频")
    parser.add_argument("--pip", required=True, help="画中画小视频")
    parser.add_argument("--output", required=True)
    parser.add_argument("--x", type=int, help="X 坐标(像素)")
    parser.add_argument("--y", type=int, help="Y 坐标(像素)")
    parser.add_argument("--w", type=int, default=480, help="画中画宽度")
    parser.add_argument("--h", type=int, default=270, help="画中画高度(16:9 比例)")
    parser.add_argument("--position", choices=list(POSITIONS.keys()), help="预设位置")
    parser.add_argument("--start", type=float, help="显示开始时间(秒)")
    parser.add_argument("--end", type=float, help="显示结束时间(秒)")
    parser.add_argument("--opacity", type=float, default=1.0, help="不透明度 0-1")
    parser.add_argument("--border", action="store_true", help="加白色边框")
    args = parser.parse_args()

    if args.position and (args.x is None and args.y is None):
        args.x, args.y = POSITIONS[args.position]

    picture_in_picture(
        args.bg, args.pip, args.output,
        args.x, args.y, args.w, args.h,
        args.start, args.end, args.opacity, args.border
    )


if __name__ == "__main__":
    safe_run(main)()
