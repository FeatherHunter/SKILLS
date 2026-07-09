# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/extract 子技能（v1.5 迁移版本）

调用 lib/ffmpeg/audio/extract.py 的能力。
本文件作为用户入口 CLI。

音频链路层级: L3 提取

用法:
  python audio/extract.py extract -i v.mp4 -o audio.wav
  python audio/extract.py fade -i v.mp4 -o out.mp4 --fade-in 2 --fade-out 3
"""
import argparse
import sys
from pathlib import Path

# 设置 sys.path：保证 SKILL_ROOT 和 lib 都在 path（但 append，不覆盖）
_SKILL_ROOT = Path(__file__).parent.parent.parent  # SKILL_ROOT/
_LIB_DIR = _SKILL_ROOT / "lib"

# 用 append（不会覆盖），并且只在路径里不存在时才加入
def _ensure_in_path(p):
    p = str(p)
    if p not in sys.path:
        sys.path.append(p)

_ensure_in_path(str(_SKILL_ROOT))
_ensure_in_path(str(_LIB_DIR))

from common import (
    log_info, log_section, log_error, ensure_dir, safe_run,
)
from ffmpeg.audio.extract import extract_audio, fade_audio


# ========== 业务封装 ==========
def extract(input_path, output_path, fmt="wav"):
    """从视频提取音频。"""
    log_section(f"提取音频: {Path(input_path).name} → .{fmt}")
    ensure_dir(Path(output_path).parent)
    try:
        success, out = extract_audio(input_path, output_path, fmt=fmt)
        if success:
            log_info(f"输出: {out}")
            return out
        log_error("提取音频失败")
        return None
    except Exception as e:
        log_error(f"提取音频失败: {e}")
        return None


def fade(input_path, output_path, fade_in=0, fade_out=0):
    """音频淡入淡出。"""
    log_section(f"音频淡入淡出 in={fade_in}s out={fade_out}s")
    ensure_dir(Path(output_path).parent)
    try:
        success, out = fade_audio(input_path, output_path, fade_in, fade_out)
        if success:
            log_info(f"输出: {out}")
            return out
        log_error("淡入淡出失败")
        return None
    except Exception as e:
        log_error(f"淡入淡出失败: {e}")
        return None


# ========== CLI ==========
def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 音频提取与淡入淡出（调 lib/ffmpeg/audio/extract）",
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # extract
    p = subparsers.add_parser("extract", help="从视频提取音频")
    p.add_argument("-i", "--input", required=True, help="输入视频")
    p.add_argument("--output", required=True, help="输出音频")
    p.add_argument("--format", default="wav", choices=["wav", "mp3", "aac"],
                   help="输出格式（默认 wav）")

    # fade
    p2 = subparsers.add_parser("fade", help="音频淡入淡出")
    p2.add_argument("-i", "--input", required=True, help="输入音频/视频")
    p2.add_argument("--output", required=True, help="输出文件")
    p2.add_argument("--fade-in", type=float, default=0, help="淡入秒数")
    p2.add_argument("--fade-out", type=float, default=0, help="淡出秒数")

    args = parser.parse_args()

    if args.cmd == "extract":
        result = extract(args.input, args.output, args.format)
    elif args.cmd == "fade":
        result = fade(args.input, args.output, args.fade_in, args.fade_out)

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)