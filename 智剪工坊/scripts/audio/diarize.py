# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/diarize 子技能（v1.5 迁移版本）

调用 lib/pyannote 的说话人分离能力。
本文件作为用户入口 CLI + 业务参数封装。

链路位置: L5 说话人

用法:
  # 基本分离
  python scripts/audio/diarize.py -i vocals.wav -o diar.json

  # 指定说话人数量
  python scripts/audio/diarize.py -i vocals.wav -o diar.json \
      --min-speakers 2 --max-speakers 4

  # 提供 HuggingFace token
  python scripts/audio/diarize.py -i vocals.wav -o diar.json \
      --token hf_xxxxxxxxx

依赖: pyannote.audio + HuggingFace 授权
底层: lib.pyannote (v1.5 新增)
"""
import argparse
import json
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
from lib.asr.pyannote import diarize_speakers, check_pyannote


def diarize(input_path, output_json,
            min_speakers=1, max_speakers=8, use_auth_token=None):
    """说话人分离（v1.5 迁移版本：调 lib/pyannote）。

    Args:
        input_path: 输入音频（建议先用 separate.py 提取人声）
        output_json: 输出 JSON 路径
        min_speakers: 最少说话人数
        max_speakers: 最多说话人数
        use_auth_token: HuggingFace token

    Returns:
        dict (成功) / None (失败)
    """
    log_section(f"说话人分离: {Path(input_path).name}")
    ensure_dir(Path(output_json).parent)

    if not check_pyannote():
        log_error("pyannote.audio 未安装")
        log_error("安装: pip install pyannote.audio")
        log_error("注意: 需要申请 pyannote 授权（https://huggingface.co/pyannote）")
        return None

    result = diarize_speakers(
        input_path, output_json=output_json,
        min_speakers=min_speakers,
        max_speakers=max_speakers,
        use_auth_token=use_auth_token,
    )

    if result is None:
        log_error("说话人分离失败")
        return None

    return result


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 说话人分离（pyannote）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""用法示例:
  %(prog)s -i vocals.wav -o diar.json
  %(prog)s -i vocals.wav -o diar.json --min-speakers 2 --max-speakers 4
  %(prog)s -i vocals.wav -o diar.json --token hf_xxx

完整链路:
  1. separate.py → 提取人声
  2. diarize.py  → 标记说话人
  3. asr/transcribe.py → SRT
  4. asr/speaker_srt.py → 带说话人字幕
  5. asr/burn_subtitle.py → 烧字幕到视频
        """,
    )
    parser.add_argument("-i", "--input", required=True, help="输入音频")
    parser.add_argument("-o", "--output", required=True, help="输出 JSON")
    parser.add_argument("--min-speakers", type=int, default=1, help="最少说话人数")
    parser.add_argument("--max-speakers", type=int, default=8, help="最多说话人数")
    parser.add_argument("--token", help="HuggingFace token")

    args = parser.parse_args()
    result = diarize(args.input, args.output, args.min_speakers, args.max_speakers, args.token)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)()