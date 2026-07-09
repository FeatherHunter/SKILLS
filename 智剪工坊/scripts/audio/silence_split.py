# -*- coding: utf-8 -*-
"""
智剪工坊 · audio/silence_split 子技能（v1.5 新增）

用 ffmpeg silencedetect 自动检测静音段，输出分段方案。

链路位置: L6 之前的「分段预处理」

适用场景:
  - 长视频自动分段（找"说话人切换点"）
  - 检测长视频里"无人说话"的段落（剪掉）
  - 给 ASR 提供段落边界（减少幻觉）

输出:
  - segments.json（每个段的时间戳）
  - 也可选：自动按静音段切分原音频

用法:
  # 只检测（输出 segments.json）
  python scripts/audio/silence_split.py detect -i audio.wav -o segments.json

  # 检测 + 自动切分（输出 segments/ 目录）
  python scripts/audio/silence_split.py split -i audio.wav -o segments/

  # 调整参数
  python scripts/audio/silence_split.py detect -i audio.wav -o seg.json \
      --threshold -40 --min-duration 1.0
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
    run_ffmpeg, get_duration, ensure_dir,
    log_info, log_section, log_error, safe_run,
)
from ffmpeg.audio.detect import detect_silence


def detect(input_path, output_json, threshold=-30, min_duration=0.5):
    """检测静音段，输出 JSON。

    Args:
        input_path: 输入音频/视频
        output_json: 输出 JSON 路径
        threshold: 静音阈值 (dB)，默认 -30
        min_duration: 最短静音时长 (秒)，默认 0.5
    Returns:
        output_path (成功) / None (失败)
    """
    log_section(f"静音检测: {Path(input_path).name}")
    ensure_dir(Path(output_json).parent)

    # 调 lib 检测
    result = detect_silence(input_path, threshold=threshold, min_duration=min_duration)
    if result is None:
        log_error("静音检测失败（lib 返回 None）")
        return None

    # 调 lib 检测只有静音段，还需计算"非静音段"（即有人说话段）
    duration = get_duration(input_path)
    if duration is None:
        log_error("无法获取音频时长")
        return None

    # 计算说话段（静音段的反向）
    silence_segments = result["segments"]
    speech_segments = []
    prev_end = 0.0
    for seg in silence_segments:
        if seg["start"] > prev_end:
            speech_segments.append({
                "start": prev_end,
                "end": seg["start"],
                "duration": round(seg["start"] - prev_end, 3),
            })
        prev_end = seg["end"]
    # 最后一段
    if prev_end < duration:
        speech_segments.append({
            "start": prev_end,
            "end": duration,
            "duration": round(duration - prev_end, 3),
        })

    output = {
        "audio": input_path,
        "duration": duration,
        "threshold_db": threshold,
        "min_duration": min_duration,
        "silence_count": len(silence_segments),
        "speech_count": len(speech_segments),
        "total_silence": round(sum(s["duration"] for s in silence_segments), 3),
        "total_speech": round(sum(s["duration"] for s in speech_segments), 3),
        "silence_segments": silence_segments,
        "speech_segments": speech_segments,
    }

    Path(output_json).write_text(
        json.dumps(output, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    log_info(f"检测完成: 静音 {result['silence_count']} 段, "
             f"说话 {len(speech_segments)} 段")
    log_info(f"输出: {output_json}")
    return str(output_json)


def split(input_path, output_dir, threshold=-30, min_duration=0.5, keep_silence=0.2):
    """检测 + 自动切分音频。

    Args:
        input_path: 输入音频
        output_dir: 输出目录（每个段一个 wav）
        threshold: 静音阈值
        min_duration: 最短静音时长
        keep_silence: 段间保留的静音秒数（避免突然切断）
    Returns:
        output_dir (成功) / None (失败)
    """
    log_section(f"静音分段 + 切分: {Path(input_path).name}")
    output_dir = Path(output_dir)
    ensure_dir(output_dir)

    # 直接调 lib 检测（不写 JSON 中间文件）
    silence_result = detect_silence(input_path, threshold=threshold, min_duration=min_duration)
    if silence_result is None:
        log_error("静音检测失败（lib 返回 None）")
        return None

    duration = get_duration(input_path)
    if duration is None:
        log_error("无法获取音频时长")
        return None

    # 计算说话段
    silence_segments = silence_result["segments"]
    speech_segs = []
    prev_end = 0.0
    for seg in silence_segments:
        if seg["start"] > prev_end:
            speech_segs.append({
                "start": prev_end,
                "end": seg["start"],
                "duration": round(seg["start"] - prev_end, 3),
            })
        prev_end = seg["end"]
    if prev_end < duration:
        speech_segs.append({
            "start": prev_end,
            "end": duration,
            "duration": round(duration - prev_end, 3),
        })

    log_info(f"开始切分 {len(speech_segs)} 段 → {output_dir}/")

    try:
        # 切分（用 ffmpeg -ss + -t）
        for i, seg in enumerate(speech_segs, 1):
            start = seg["start"]
            end = seg["end"]
            # 段间保留静音
            seg_start = max(0, start - keep_silence)
            seg_end = min(duration, end + keep_silence)
            seg_duration = seg_end - seg_start

            out_file = output_dir / f"segment_{i:04d}.wav"
            run_ffmpeg([
                "-i", str(input_path),
                "-ss", str(seg_start),
                "-t", str(seg_duration),
                "-c:a", "pcm_s16le",
                "-y", str(out_file),
            ])
            log_info(f"  [{i}/{len(speech_segs)}] {seg_start:.1f}s-{seg_end:.1f}s → {out_file.name}")

        log_info(f"切分完成: {output_dir}")
        return str(output_dir)
    except Exception:
        # 异常时清理已生成的段文件
        for f in output_dir.glob("segment_*.wav"):
            try:
                f.unlink()
            except Exception:
                pass
        raise


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 静音检测与自动分段",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""用法:
  检测: %(prog)s detect -i audio.wav -o segments.json
  切分: %(prog)s split -i audio.wav -o segments_dir/

参数说明:
  --threshold    静音阈值 (dB)，越小越严格（默认 -30）
  --min-duration 最短静音时长 (秒)，低于这个不算静音段（默认 0.5）
  --keep-silence 切分时保留的段间静音 (秒)，避免突然切断（默认 0.2）
        """,
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # detect
    p = subparsers.add_parser("detect", help="只检测，输出 JSON")
    p.add_argument("-i", "--input", required=True, help="输入音频/视频")
    p.add_argument("-o", "--output", required=True, help="输出 JSON 路径")
    p.add_argument("--threshold", type=float, default=-30, help="静音阈值 (dB)")
    p.add_argument("--min-duration", type=float, default=0.5, help="最短静音时长 (秒)")

    # split
    p2 = subparsers.add_parser("split", help="检测 + 自动切分")
    p2.add_argument("-i", "--input", required=True, help="输入音频")
    p2.add_argument("-o", "--output", required=True, help="输出目录")
    p2.add_argument("--threshold", type=float, default=-30, help="静音阈值 (dB)")
    p2.add_argument("--min-duration", type=float, default=0.5, help="最短静音时长 (秒)")
    p2.add_argument("--keep-silence", type=float, default=0.2, help="段间保留静音 (秒)")

    args = parser.parse_args()

    if args.cmd == "detect":
        result = detect(args.input, args.output, args.threshold, args.min_duration)
    elif args.cmd == "split":
        result = split(args.input, args.output, args.threshold, args.min_duration, args.keep_silence)

    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)