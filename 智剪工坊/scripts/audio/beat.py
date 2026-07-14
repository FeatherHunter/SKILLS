# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/beat 子技能（v1.5 迁移版本）

调用 librosa 做节拍分析。
本文件作为用户入口 CLI + 业务参数封装。

音频链路层级: L2 变换

用法:
  python audio/beat.py --analyze --bgm music.mp3 --output beats.json
  python audio/beat.py --input video.mp4 --bgm music.mp3 --output sync.mp4

依赖: librosa（非 ffmpeg，所以不调 lib/ffmpeg/audio）
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
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


def analyze_beats(bgm_path, output_json, min_tempo=60, max_tempo=180):
    """分析 BGM 节拍，输出 JSON 时间戳。"""
    log_section(f"分析 BGM 节拍: {Path(bgm_path).name}")
    ensure_dir(Path(output_json).parent)

    try:
        import librosa
        import numpy as np
    except ImportError:
        log_warn("librosa 未安装，无法分析节拍")
        log_warn("安装: pip install librosa")
        return None

    y, sr = librosa.load(bgm_path)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

    log_info(f"BPM: {float(tempo):.1f}")
    log_info(f"节拍数: {len(beat_times)}")

    result = {
        "bgm": str(bgm_path),
        "duration": get_duration(bgm_path),
        "tempo": float(tempo),
        "beat_count": len(beat_times),
        "beats": [round(t, 3) for t in beat_times],
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    log_info(f"节拍数据: {output_json}")
    return result


def cut_to_beats(video_path, bgm_path, output_path, mode="cut"):
    """按节拍点自动剪切视频（整体对齐，非逐段）。"""
    log_section(f"按节拍剪辑: {Path(video_path).name} + {Path(bgm_path).name}")
    ensure_dir(Path(output_path).parent)

    beats_file = str(output_path) + ".beats.json"
    beats_data = analyze_beats(bgm_path, beats_file)
    if not beats_data:
        log_warn("无法分析节拍，跳过")
        return

    beats = beats_data["beats"]
    if len(beats) < 2:
        log_warn("节拍数太少")
        return

    log_info(f"按 {len(beats)} 个节拍点剪切视频")

    duration = get_duration(video_path)
    video_dur = duration
    beats_dur = beats[-1]
    factor = video_dur / beats_dur

    log_info(f"视频时长 {video_dur:.1f}s → BGM 时长 {beats_dur:.1f}s，缩放 {factor:.2f}x")

    run_ffmpeg([
        "-i", str(video_path),
        "-i", str(bgm_path),
        "-filter_complex",
        f"[0:v]setpts=PTS*{factor}[v];"
        f"[1:a]aresample=async=1[a]",
        "-map", "[v]", "-map", "[a]",
        *DEFAULT_ENCODE_ARGS,
        str(output_path),
    ])
    log_info(f"输出: {output_path} ({get_duration(output_path):.1f}s)")
    log_info("完整节拍卡点需要逐段 trim + concat，本版本只做整体对齐")


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 节拍卡点（librosa 分析）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  %(prog)s --analyze --bgm music.mp3 --output beats.json\n  %(prog)s --input v.mp4 --bgm music.mp3 --output sync.mp4",
    )
    parser.add_argument("--analyze", action="store_true", help="只分析节拍，输出 JSON")
    parser.add_argument("-i", "--input", help="视频文件")
    parser.add_argument("--bgm", help="BGM 文件")
    parser.add_argument("--output", required=True, help="输出（beat JSON 或视频）")
    args = parser.parse_args()

    if args.analyze:
        if not args.bgm:
            raise Exception("--analyze 需要 --bgm")
        analyze_beats(args.bgm, args.output)
    else:
        if not all([args.input, args.bgm]):
            raise Exception("需要 --input 和 --bgm")
        cut_to_beats(args.input, args.bgm, args.output)


if __name__ == "__main__":
    safe_run(main)()