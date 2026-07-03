# -*- coding: utf-8 -*-
"""
智剪工坊 · keyframe 子技能
关键帧动画(位置/缩放/透明度/旋转)

用法:
  # 简单:从中心放大到 1.5 倍
  python keyframe.py --input in.mp4 --action zoom --start 1.0 --end 1.5 --out out.mp4

  # 位置:从左到右平移
  python keyframe.py --input in.mp4 --action pan --from "0,0" --to "200,0" --out out.mp4

  # 透明度淡入
  python keyframe.py --input in.mp4 --action fade_in --duration 2 --out out.mp4
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


def keyframe_zoom(input_path, output_path, start, end, x=None, y=None, duration=None):
    """关键帧缩放"""
    if duration is None:
        duration = get_duration(input_path)

    log_section(f"关键帧缩放 {start}→{end}: {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    # 简化:用 zoompan 实现
    if x is None or y is None:
        # 中心缩放
        run_ffmpeg([
            "-i", str(input_path),
            "-vf", f"zoompan=z='if(lte(on,0),{start},min({end},{start}+({end}-{start})*on/{int(duration*30)}))':d={int(duration*30)}:s=1080x1920",
            *DEFAULT_ENCODE_ARGS,
            str(output_path),
        ])
    else:
        # 缩放到指定坐标
        run_ffmpeg([
            "-i", str(input_path),
            "-vf", f"zoompan=z='if(lte(on,0),{start},min({end},{start}+({end}-{start})*on/{int(duration*30)}))':x='{x}':y='{y}':d={int(duration*30)}:s=1080x1920",
            *DEFAULT_ENCODE_ARGS,
            str(output_path),
        ])

    log_info(f"输出: {output_path}")


def keyframe_pan(input_path, output_path, from_xy, to_xy, duration=None):
    """关键帧平移"""
    if duration is None:
        duration = get_duration(input_path)

    fx, fy = map(int, from_xy.split(","))
    tx, ty = map(int, to_xy.split(","))

    log_section(f"关键帧平移 ({fx},{fy})→({tx},{ty}): {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    total_frames = int(duration * 30)
    # 用 zoompan 实现平移(z=1.0,x/y 动态)
    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"zoompan=z='1.0':x='{fx}+({tx}-{fx})*on/{total_frames}':y='{fy}+({ty}-{fy})*on/{total_frames}':d={total_frames}:s=1080x1920",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])

    log_info(f"输出: {output_path}")


def keyframe_fade_in(input_path, output_path, fade_duration):
    """淡入"""
    log_section(f"淡入 {fade_duration}s: {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"fade=t=in:st=0:d={fade_duration}",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def keyframe_fade_out(input_path, output_path, fade_duration):
    """淡出"""
    duration = get_duration(input_path)
    log_section(f"淡出 {fade_duration}s: {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    run_ffmpeg([
        "-i", str(input_path),
        "-vf", f"fade=t=out:st={duration - fade_duration}:d={fade_duration}",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 关键帧动画",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--action", required=True, choices=["zoom", "pan", "fade_in", "fade_out"])

    parser.add_argument("--start", type=float, help="zoom 起始倍数")
    parser.add_argument("--end", type=float, help="zoom 结束倍数")
    parser.add_argument("--x", type=int, help="zoom 中心 X")
    parser.add_argument("--y", type=int, help="zoom 中心 Y")
    parser.add_argument("--from", dest="from_xy", help="pan 起始坐标 'x,y'")
    parser.add_argument("--to", dest="to_xy", help="pan 结束坐标 'x,y'")
    parser.add_argument("--duration", type=float, help="时长(秒)")
    args = parser.parse_args()

    if args.action == "zoom":
        if args.start is None or args.end is None:
            raise Exception("zoom 需要 --start 和 --end")
        keyframe_zoom(args.input, args.out, args.start, args.end, args.x, args.y, args.duration)
    elif args.action == "pan":
        if not args.from_xy or not args.to_xy:
            raise Exception("pan 需要 --from 和 --to")
        keyframe_pan(args.input, args.out, args.from_xy, args.to_xy, args.duration)
    elif args.action == "fade_in":
        keyframe_fade_in(args.input, args.out, args.duration or 2.0)
    elif args.action == "fade_out":
        keyframe_fade_out(args.input, args.out, args.duration or 2.0)


if __name__ == "__main__":
    safe_run(main)()
