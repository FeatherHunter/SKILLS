# -*- coding: utf-8 -*-
"""
智剪工坊 · asr/transcribe 子技能（v1.5 迁移版本）

调用 lib/whisper 的 ASR 能力。
本文件作为用户入口 CLI + 业务参数封装。

链路位置: L6 ASR

用法:
  python scripts/asr/transcribe.py -i audio.wav --srt subtitles.srt
  python scripts/asr/transcribe.py -i audio.wav --srt subtitles.srt --model small --device cpu
  python scripts/asr/transcribe.py -i audio.wav --srt subtitles.srt --lang zh

依赖: faster-whisper
底层: lib.whisper (v1.5 新增)
"""
import argparse
import sys
from pathlib import Path

# 设置 sys.path：保证 SKILL_ROOT 和 lib 都在 path，但不覆盖标准库
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
from lib.whisper import transcribe_to_srt, check_whisper


def transcribe(input_path, srt_path, model="medium", device="cuda", language=None):
    """ASR 转录（v1.5 迁移版本：调 lib/whisper）。

    Args:
        input_path: 输入音频/视频
        srt_path: 输出 SRT 路径
        model: 模型
        device: cuda / cpu
        language: 强制语言（None=自动检测）

    Returns:
        int 段数（成功）/ None（失败）
    """
    log_section(f"ASR 转录: {Path(input_path).name}")
    ensure_dir(Path(srt_path).parent)

    if not check_whisper():
        log_error("faster-whisper 未安装")
        log_error("安装: pip install faster-whisper")
        return None

    seg_count = transcribe_to_srt(input_path, srt_path,
                                  model=model, device=device, language=language)
    if seg_count is None:
        log_error("ASR 转录失败")
        return None
    return seg_count


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · Whisper ASR 转录",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""用法:
  %(prog)s -i audio.wav --srt subtitles.srt
  %(prog)s -i audio.wav --srt out.srt --model small --device cpu
  %(prog)s -i audio.wav --srt out.srt --lang zh

模型选择:
  tiny     ~75MB  最快，精度低
  base     ~150MB 平衡
  small    ~500MB 推荐（中文 ok）
  medium   ~1.5GB 高精度（默认）
  large-v3 ~3GB   最高精度
        """,
    )
    parser.add_argument("-i", "--input", required=True, help="输入音频/视频")
    parser.add_argument("--srt", required=True, help="输出 SRT 路径")
    parser.add_argument("--model", default="medium",
                       help="Whisper 模型（默认 medium）")
    parser.add_argument("--device", default="cuda", help="cuda / cpu")
    parser.add_argument("--lang", help="强制语言代码（默认自动检测）")

    args = parser.parse_args()
    seg_count = transcribe(args.input, args.srt, args.model, args.device, args.lang)
    if seg_count is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)