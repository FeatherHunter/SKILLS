# -*- coding: utf-8 -*-
"""
智剪工坊 · asr/burn_subtitle 子技能（音频链路 L6: 合成）
将 SRT 字幕烧录到视频

v1.6 重构（2026-07-09）:
  - 改为薄封装，所有 ffmpeg 调用通过 lib/ffmpeg/video/subtitle.py
  - 上层只做参数解析 + 用户友好的日志

调用示例:
  python scripts/asr/burn_subtitle.py --video in.mp4 --srt sub.srt --output out.mp4
  python scripts/asr/burn_subtitle.py --video in.mp4 --srt sub.srt --output out.mp4 --font-size 26
"""
import argparse
import sys
from pathlib import Path

# lib/ 在 pythonpath（v1.5 _ensure_in_path 模式）
_SKILL_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(_SKILL_ROOT))

from lib.ffmpeg.video.subtitle import burn_subtitle as _lib_burn
from common import ensure_dir, log_info, log_section, safe_run


def burn_subtitle_video(video, srt, output, font_size=22):
    """烧录 SRT 字幕到视频（薄封装，调 lib）。

    Args:
        video: 输入视频
        srt: SRT 字幕文件
        output: 输出视频路径
        font_size: 字幕字号（默认 22）
    """
    log_section(f"烧字幕: {Path(srt).name} → {Path(video).name}")
    ensure_dir(Path(output).parent)

    ok, out_path = _lib_burn(video, srt, output, font_size=font_size)
    if not ok:
        raise RuntimeError(f"烧字幕失败: {out_path}")
    log_info(f"输出: {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · SRT 字幕烧录到视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s --video in.mp4 --srt subtitles.srt --output out_subtitled.mp4\n  %(prog)s --video in.mp4 --srt subtitles.srt --output out.mp4 --font-size 26",
    )
    parser.add_argument("--video", required=True, help="输入视频")
    parser.add_argument("--srt", required=True, help="SRT 字幕文件")
    parser.add_argument("--output", required=True, help="输出视频")
    parser.add_argument("--font-size", type=int, default=22, help="字幕字号（默认 22）")
    args = parser.parse_args()
    burn_subtitle_video(args.video, args.srt, args.output, args.font_size)


if __name__ == "__main__":
    safe_run(main)()