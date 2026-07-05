# -*- coding: utf-8 -*-
"""
智剪工坊 · color_style 子技能
风格化滤镜(灰度/老电影/暖色/冷色/漫画/黑白/复古)

用法:
  python color_style.py --input in.mp4 --style vintage --out out.mp4
  python color_style.py --input in.mp4 --style comic --out out.mp4


📖 SKILL.md §14 索引 → REQUIRED: read references/05-color.md
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_section, safe_run,
)


# 风格预设(每个预设 = 一组 ffmpeg filters)
STYLES = {
    "bw": {
        "desc": "黑白",
        "vf": "hue=s=0",
    },
    "vintage": {
        "desc": "复古(70 年代胶片色)",
        "vf": ",vignette=PI/4",
    },
    "warm": {
        "desc": "暖色调",
        "vf": "colorbalance=rs=0.1:bs=-0.1:gs=0.05",
    },
    "cool": {
        "desc": "冷色调",
        "vf": "colorbalance=rs=-0.1:bs=0.1:gs=-0.05",
    },
    "cinematic": {
        "desc": "电影感(teal & orange)",
        "vf": "colorbalance=rs=0.05:bs=0.1:gs=-0.05",
    },
    "noir": {
        "desc": "黑色电影(强对比黑白)",
        "vf": "hue=s=0,eq=contrast=1.3:brightness=-0.05",
    },
    "comic": {
        "desc": "漫画风(边缘检测)",
        "vf": "edgedetect=low=0.1:high=0.4,eq=saturation=1.5",
    },
    "sketch": {
        "desc": "素描风",
        "vf": "edgedetect=low=0.05:high=0.3,negate,eq=brightness=0.1",
    },
    "faded": {
        "desc": "褪色 / 旧照片",
        "vf": ",eq=saturation=0.7",
    },
    "punchy": {
        "desc": "活力(高饱和高对比)",
        "vf": "eq=saturation=1.4:contrast=1.2",
    },
    "vhs": {
        "desc": "VHS 复古录像带",
        "vf": ",noise=alls=20:allf=t+u,vignette=PI/3",
    },
    "dream": {
        "desc": "梦幻柔光",
        "vf": "gblur=sigma=1,eq=brightness=0.05:saturation=1.2",
    },
    "sharpen": {
        "desc": "锐化",
        "vf": "unsharp=5:5:1.5:5:5:0",
    },
}


def apply_style(input_path, output_path, style, intensity=1.0):
    """应用风格化滤镜"""
    if style not in STYLES:
        raise ValueError(f"未知风格: {style},可用: {', '.join(STYLES.keys())}")

    cfg = STYLES[style]
    log_section(f"风格化 {style}({cfg['desc']}): {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    vf = cfg["vf"]
    if intensity != 1.0:
        # 简单实现:用 blend 模式混合原图和风格化结果
        vf += f",split[orig][styled];[orig][styled]blend=all_mode='overlay':all_opacity={intensity}"

    run_ffmpeg([
        "-i", str(input_path),
        "-vf", vf,
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 风格化滤镜",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="风格:\n  " + "\n  ".join([f"{k} - {v['desc']}" for k, v in STYLES.items()]) + "\n\n示例:\n  %(prog)s --input in.mp4 --style vintage --out out.mp4",
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--style", required=True, choices=list(STYLES.keys()))
    parser.add_argument("--intensity", type=float, default=1.0, help="强度 0-1")
    args = parser.parse_args()
    apply_style(args.input, args.output, args.style, args.intensity)


if __name__ == "__main__":
    safe_run(main)()
