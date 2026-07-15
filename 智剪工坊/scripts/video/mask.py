# -*- coding: utf-8 -*-
"""
智剪工坊 · mask 子技能
基础蒙版(矩形 / 圆形 / 线性渐变)

用法:
  # 矩形蒙版(只显示中心区域)
  python mask.py --input in.mp4 --type rect --x 100 --y 100 --w 500 --h 300 --out out.mp4

  # 圆形蒙版(只显示中心圆形)
  python mask.py --input in.mp4 --type circle --cx 540 --cy 960 --r 300 --out out.mp4


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


def mask_rect(input_path, output_path, x, y, w, h, feather=0, invert=False):
    """矩形蒙版"""
    log_section(f"矩形蒙版 ({x},{y},{w}x{h}): {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    # 视频尺寸假设 1080x1920
    vw, vh = 1080, 1920

    if invert:
        # 反向蒙版:挖空中心,显示边缘
        # 用 2 个黑条遮住
        # 上条:y=0 到 y=h
        # 下条:y=y+w 到 vh
        # 完整实现略复杂,简化
        log_info("反向矩形蒙版需要 split + blend,暂简化")

    # mask 表达式:中心 1,边缘 0(羽化)
    if feather > 0:
        # 羽化边
        # 用 geq 实现柔边矩形
        expr = (
            f"if(between(X,{x+feather},{x+w-feather})*between(Y,{y+feather},{y+h-feather}),"
            f"if(between(X,{x},{x+feather})*between(Y,{y},{y+h}),"
            f"(X-{x})/{feather},"
            f"if(between(X,{x+w-feather},{x+w})*between(Y,{y},{y+h}),"
            f"({x+w}-X)/{feather},1)),"
            "0)"
        )
    else:
        # 硬边
        expr = (
            f"if(between(X,{x},{x+w})*between(Y,{y},{y+h}),1,0)"
        )

    # 用 geq 创建蒙版,然后用 mask filter 应用
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"geq=lum='{expr}*255':cb='128':cr='128'[mask];[0:v][mask]alphamerge[out]",
        "-map", "[out]",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def mask_circle(input_path, output_path, cx, cy, r, feather=0):
    """圆形蒙版"""
    log_section(f"圆形蒙版 (cx={cx},cy={cy},r={r}): {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    # 圆形 mask
    if feather > 0:
        # 羽化边
        expr = (
            f"if(lte(sqrt((X-{cx})*(X-{cx})+(Y-{cy})*(Y-{cy})),{r-feather}),1,"
            f"if(lte(sqrt((X-{cx})*(X-{cx})+(Y-{cy})*(Y-{cy})),{r}),"
            f"({r}-sqrt((X-{cx})*(X-{cx})+(Y-{cy})*(Y-{cy})))/{feather},0))"
        )
    else:
        expr = f"if(lte(sqrt((X-{cx})*(X-{cx})+(Y-{cy})*(Y-{cy})),{r}),1,0)"

    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"geq=lum='{expr}*255':cb='128':cr='128'[mask];[0:v][mask]alphamerge[out]",
        "-map", "[out]",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 基础蒙版(矩形/圆形)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--type", choices=["rect", "circle"], required=True)

    # 矩形参数
    parser.add_argument("--x", type=int, help="矩形 X")
    parser.add_argument("--y", type=int, help="矩形 Y")
    parser.add_argument("--w", type=int, help="矩形宽")
    parser.add_argument("--h", type=int, help="矩形高")

    # 圆形参数
    parser.add_argument("--cx", type=int, help="圆心 X")
    parser.add_argument("--cy", type=int, help="圆心 Y")
    parser.add_argument("--r", type=int, help="半径")

    parser.add_argument("--feather", type=int, default=0, help="羽化像素")
    args = parser.parse_args()

    if args.type == "rect":
        if not all([args.x, args.y, args.w, args.h]):
            raise Exception("矩形蒙版需要 --x --y --w --h")
        mask_rect(args.input, args.output, args.x, args.y, args.w, args.h, args.feather)
    elif args.type == "circle":
        if not all([args.cx, args.cy, args.r]):
            raise Exception("圆形蒙版需要 --cx --cy --r")
        mask_circle(args.input, args.output, args.cx, args.cy, args.r, args.feather)


if __name__ == "__main__":
    safe_run(main)()
