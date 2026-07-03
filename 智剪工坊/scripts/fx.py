# -*- coding: utf-8 -*-
"""
智剪工坊 · fx 子技能
动态特效(光晕 / 模糊 / 扭曲 / 镜头光斑 / 抖动 / 翻转)

用法:
  python fx.py --input in.mp4 --effect glow --out out.mp4
  python fx.py --input in.mp4 --effect lens_flare --out out.mp4
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_section, safe_run,
)


# 特效预设
EFFECTS = {
    "glow": {
        "desc": "柔光 / 辉光",
        "vf": "gblur=sigma=2,eq=brightness=0.1:saturation=1.3,curves=preset=punchy",
    },
    "lens_flare": {
        "desc": "镜头光晕",
        "vf": "curves=preset=cross_process,eq=brightness=0.15:saturation=1.4,colorbalance=rs=0.1",
    },
    "motion_blur": {
        "desc": "动态模糊",
        "vf": "gblur=sigma=5,boxblur=10:1",
    },
    "zoom_blur": {
        "desc": "径向模糊(快速 zoom)",
        "vf": "zoompan=z='1.0+0.001*on':d=1:s=1080x1920,boxblur=1:5",
    },
    "distort": {
        "desc": "画面扭曲",
        "vf": "eq=contrast=1.3,curves=preset=cross_process,negate",
    },
    "shake": {
        "desc": "画面震动(地震感)",
        "vf": "crop=in_w-20:in_h-20:10+random(0)*30:10+random(0)*30",
    },
    "mirror_h": {
        "desc": "水平镜像",
        "vf": "hflip",
    },
    "mirror_v": {
        "desc": "垂直镜像",
        "vf": "vflip",
    },
    "rotate_90": {
        "desc": "旋转 90 度",
        "vf": "transpose=1",
    },
    "rotate_270": {
        "desc": "旋转 270 度",
        "vf": "transpose=2",
    },
    "fisheye": {
        "desc": "鱼眼效果",
        "vf": "v360=e:in_stereo=0:out_stereo=0:interp=linear",
    },
    "lens_distort": {
        "desc": "镜头畸变",
        "vf": "lenscorrection=k1=0.2:k2=0.1",
    },
    "pixelate": {
        "desc": "像素化",
        "vf": "scale=180:320,scale=1080:1920:flags=neighbor",
    },
    "vhs_distort": {
        "desc": "VHS 扭曲",
        "vf": "split[orig];[orig]curves=preset=cross_process,noise=alls=30:allf=t+u[bad];[bad]vignette=PI/2",
    },
    "frosted_glass": {
        "desc": "磨砂玻璃",
        "vf": "gblur=sigma=8,eq=saturation=0.8",
    },
    "high_contrast": {
        "desc": "高对比",
        "vf": "eq=contrast=1.5,curves=preset=strong_contrast",
    },
    "tilt_shift": {
        "desc": "移轴(微缩)",
        "vf": "v360=e:yaw=0:pitch=0:roll=0",
    },
    "glitch": {
        "desc": "故障感",
        "vf": "rgbcheckr=contrast=0.3:transform=0.2,eq=saturation=1.5",
    },
    "vintage_footage": {
        "desc": "老电影",
        "vf": "curves=preset=vintage,noise=alls=10:allf=t,vignette=PI/3",
    },
}


def apply_effect(input_path, output_path, effect, intensity=1.0):
    """应用动态特效"""
    if effect not in EFFECTS:
        raise ValueError(f"未知特效: {effect},可用: {', '.join(EFFECTS.keys())}")

    cfg = EFFECTS[effect]
    log_section(f"特效 {effect}({cfg['desc']}): {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    vf = cfg["vf"]
    # 注:原版用 blend 混合 intensity,语法有 bug;现在用静态效果,
    # 要调强度直接换 effect 或加更多 filter chain
    if intensity != 1.0:
        log_info(f"提示:--intensity {intensity} 当前未动态应用,效果是预设强度")

    run_ffmpeg([
        "-i", str(input_path),
        "-vf", vf,
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 动态特效",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="特效:\n  " + "\n  ".join([f"{k} - {v['desc']}" for k, v in EFFECTS.items()]),
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--effect", required=True, choices=list(EFFECTS.keys()))
    parser.add_argument("--intensity", type=float, default=1.0, help="强度 0-1")
    args = parser.parse_args()
    apply_effect(args.input, args.out, args.effect, args.intensity)


if __name__ == "__main__":
    safe_run(main)()
