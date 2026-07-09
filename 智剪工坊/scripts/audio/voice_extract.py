# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/voice_extract 子技能（v1.5 新增）

用 ffmpeg 内置的 dialoguenhance 滤镜提取人声。
不需要 Demucs / 神经网络模型，纯 ffmpeg 处理，CPU 实时。

链路位置: L4（声源分离的"轻量级"替代方案）

适用场景:
  - 视频里有 BGM 但人声清楚：dialoguenhance 足够
  - 视频里 BGM 很大、人声复杂：要 Demucs（heavyweight）

用法:
  # 基本提取
  python scripts/audio/voice_extract.py -i video.mp4 -o voice.wav

  # 调整强度（level 0=不处理，1=最强，默认 0.5）
  python scripts/audio/voice_extract.py -i video.mp4 -o voice.wav --level 0.7

  # 链式：先降噪再人声提取
  python scripts/audio/extract.py extract -i video.mp4 -o raw.wav
  python scripts/audio/voice_extract.py -i raw.wav -o voice.wav --level 0.5

依赖: lib.ffmpeg.audio.enhance (已内置 dialoguenhance)
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
    ensure_dir, log_info, log_section, log_error, safe_run,
)
from ffmpeg.audio.enhance import enhance_dialog
from ffmpeg.audio.extract import extract_audio


def voice_extract(input_path, output_path, level=0.5, do_extract=True):
    """从视频/音频提取人声。

    Args:
        input_path: 输入视频或音频
        output_path: 输出音频文件
        level: 增强强度（0=不处理，1=最强）
        do_extract: 是否先从视频提取音频（视频输入时必须 True）
    Returns:
        output_path (成功) / None (失败)
    """
    log_section(f"人声提取: {Path(input_path).name} → {Path(output_path).name} (level={level})")
    ensure_dir(Path(output_path).parent)

    # 判断输入是视频还是音频（粗略：扩展名）
    video_exts = {'.mp4', '.mov', '.mkv', '.avi', '.flv', '.webm', '.wmv'}
    is_video = Path(input_path).suffix.lower() in video_exts

    if is_video and do_extract:
        # 步骤 1: 先提取音频
        import tempfile
        tmp_audio = Path(tempfile.gettempdir()) / f"voice_extract_{Path(input_path).stem}.wav"
        try:
            log_info(f"步骤 1/2: 提取音频 → {tmp_audio}")
            success, _ = extract_audio(str(input_path), str(tmp_audio), fmt="wav")
            if not success:
                log_error("音频提取失败")
                return None

            # 步骤 2: 人声增强
            log_info(f"步骤 2/2: 人声增强 (level={level})")
            success, out = enhance_dialog(str(tmp_audio), output_path, level=level)
            return out if success else None
        finally:
            try:
                tmp_audio.unlink()
            except Exception:
                pass
    else:
        # 直接增强
        log_info("直接人声增强")
        success, out = enhance_dialog(input_path, output_path, level=level)
        return out if success else None


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 人声提取（ffmpeg dialoguenhance）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""人声提取（纯 ffmpeg，无需模型）:

  适用: BGM 较小、人声清晰的视频
  局限: BGM 很大或人声复杂时效果有限（改用 audio/separate.py + Demucs）

  level: 0=不处理，0.5=中等，1=最强
        默认 0.5 适合大多数场景

示例:
  %(prog)s -i video.mp4 -o voice.wav
  %(prog)s -i video.mp4 -o voice.wav --level 0.7
  %(prog)s -i audio.wav -o clean_voice.wav --level 0.5
        """,
    )
    parser.add_argument("-i", "--input", required=True, help="输入视频/音频")
    parser.add_argument("-o", "--output", required=True, help="输出音频")
    parser.add_argument("--level", type=float, default=0.5,
                        help="增强强度 0-1（默认 0.5）")
    parser.add_argument("--no-extract", action="store_true",
                        help="不先提取音频（输入已是音频时用）")
    args = parser.parse_args()

    result = voice_extract(args.input, args.output, level=args.level, do_extract=not args.no_extract)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)