# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/voice 子技能（音频链路 L2: 变换）
音频变声（老人 / 小孩 / 机器人 / 女声 / 男声）

来源: scripts/audio_voice.py（97 行）
本文件为 audio/ 链路主入口，old 路径 audio_voice.py 保留 backward-compat。

依赖: ffmpeg（asetrate + atempo 链）
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_section, safe_run,
)

# 变声预设
PRESETS = {
    "old_man": {"pitch": 0.7, "description": "老人（低沉）"},
    "child": {"pitch": 1.5, "description": "小孩（高音）"},
    "robot": {"pitch": 1.0, "robot": True, "description": "机器人"},
    "female": {"pitch": 1.2, "description": "女声"},
    "male": {"pitch": 0.85, "description": "男声（低沉）"},
    "whisper": {"pitch": 0.95, "whisper": True, "description": "耳语"},
    "chipmunk": {"pitch": 2.0, "description": "花栗鼠（超高音）"},
    "deep": {"pitch": 0.5, "description": "极低沉"},
}


def change_voice(input_path, output_path, pitch=1.0, robot=False, whisper=False):
    """变声核心逻辑。

    - pitch < 1: 变低沉（老人）
    - pitch > 1: 变高（小孩、女声）
    - robot: 用 tremolo + 调制
    - whisper: 加呼吸声 + 降音量
    """
    log_section(f"变声 pitch={pitch} robot={robot} whisper={whisper}: {Path(input_path).name}")
    ensure_dir(Path(output_path).parent)

    # 音调调整: asetrate + atempo 补偿
    if 0.5 <= pitch <= 2.0:
        af_chain = f"asetrate={int(44100 * pitch)},aresample=44100,atempo={1.0/pitch}"
    else:
        af_chain = f"asetrate={int(44100 * pitch)},aresample=44100"

    if robot:
        af_chain = f"{af_chain},tremolo=f=20:d=0.5,chorus=0.5:0.5:50:0.4:0.25:2"
    elif whisper:
        af_chain = f"{af_chain},volume=0.4,highpass=f=300,lowpass=f=3000"

    run_ffmpeg([
        "-i", str(input_path),
        "-af", af_chain,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "128k",
        str(output_path),
    ])
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 音频变声",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="预设: " + ", ".join(PRESETS.keys()) + "\n\n示例:\n  %(prog)s --input in.mp4 --type old_man --output out.mp4\n  %(prog)s --input in.mp4 --pitch 1.5 --output out.mp4",
    )
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--type", choices=list(PRESETS.keys()), help="预设变声")
    parser.add_argument("--pitch", type=float, help="自定义音调倍数（0.5-2.0）")
    args = parser.parse_args()

    if args.type:
        preset = PRESETS[args.type]
        change_voice(
            args.input, args.output,
            pitch=preset.get("pitch", 1.0),
            robot=preset.get("robot", False),
            whisper=preset.get("whisper", False),
        )
    else:
        change_voice(args.input, args.output, pitch=args.pitch or 1.0)


if __name__ == "__main__":
    safe_run(main)
