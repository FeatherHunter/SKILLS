# -*- coding: utf-8 -*-
"""
智剪工坊 · asr/speaker_srt 子技能（音频链路 L6: 合成）
将说话人分离结果 + ASR 结果合并，生成带说话人标签的 SRT

本文件为新增文件（v1.4）。

链路位置（L6 合成端）:
  前置步骤：
    1. audio/denoise.py     — 降噪
    2. audio/separate.py   — 声源分离
    3. audio/diarize.py    — 说话人分离 → 输出 diar.json
    4. asr/transcribe.py   — ASR 转录   → 输出 audio.srt
  本文件（L6 合成）:
    5. speaker_srt.py      — 合并       → 输出 audio_speaker.srt

用法:
  python asr/speaker_srt.py --diarize diar.json --srt audio.srt --output audio_speaker.srt

输出格式（SRT + 说话人标签）:
  1
  SPEAKER_00 (00:00:00,000 --> 00:00:03,500)
  今天我们聊聊饮食记录

  2
  SPEAKER_01 (00:00:03,600 --> 00:00:07,200)
  好的，我也想听听你的方法
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "lib"))
from common import (
    ensure_dir,
    log_info, log_section, log_warn, safe_run,
)


def fmt_srt_ts(seconds):
    """格式化 SRT 时间戳（HH:MM:SS,mmm）。"""
    if seconds < 0:
        seconds = 0
    ms = int(round((seconds - int(seconds)) * 1000))
    s = int(seconds)
    h, m, s = s // 3600, (s % 3600) // 60, s % 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def load_srt(srt_path):
    """解析 SRT 文件，返回 [(start, end, text), ...] 列表。"""
    srt_path = Path(srt_path)
    if not srt_path.exists():
        return None

    segments = []
    lines = srt_path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 段编号
        if line.isdigit():
            i += 1
            # 时间码行
            if i < len(lines) and "-->" in lines[i]:
                ts_line = lines[i].strip()
                i += 1
                start_str, end_str = ts_line.split("-->")
                start = _parse_ts(start_str.strip())
                end = _parse_ts(end_str.strip())
                # 文本（可能多行）
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    text_lines.append(lines[i].strip())
                    i += 1
                text = " ".join(text_lines)
                if text:
                    segments.append((start, end, text))
        i += 1
    return segments


def _parse_ts(ts_str):
    """解析 SRT 时间字符串（HH:MM:SS,mmm）→ 秒数。"""
    ts_str = ts_str.replace(",", ".")
    parts = ts_str.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    return 0.0


def assign_speakers_to_segments(srt_segments, diar_json_path):
    """将说话人分配给 ASR 段落（按时间重叠匹配）。"""
    with open(diar_json_path, encoding="utf-8") as f:
        diar = json.load(f)

    diar_segments = diar.get("segments", [])

    # 按时间戳分配说话人
    result = []
    for s_start, s_end, text in srt_segments:
        # 找重叠最大的 diar 段
        best_speaker = "UNKNOWN"
        best_overlap = 0.0

        for d_seg in diar_segments:
            d_start = d_seg["start"]
            d_end = d_seg["end"]
            # 计算重叠
            overlap_start = max(s_start, d_start)
            overlap_end = min(s_end, d_end)
            overlap = max(0, overlap_end - overlap_start)

            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = d_seg["speaker"]

        result.append((best_speaker, s_start, s_end, text))

    return result


def merge_speaker_srt(srt_path, diar_json_path, output_path):
    """生成带说话人标签的 SRT。

    Args:
        srt_path: ASR 输出的 SRT 文件
        diar_json_path: diarize.py 输出的 JSON 文件
        output_path: 合并后的 SRT 路径

    Returns:
        output_path（成功）；None（失败）
    """
    log_section(f"合并说话人 + ASR: {Path(srt_path).name} × {Path(diar_json_path).name}")
    ensure_dir(Path(output_path).parent)

    srt_segments = load_srt(srt_path)
    if srt_segments is None:
        log_warn(f"SRT 文件不存在: {srt_path}")
        return None
    if not srt_segments:
        log_warn("SRT 文件为空")
        return None

    labeled = assign_speakers_to_segments(srt_segments, diar_json_path)

    with open(output_path, "w", encoding="utf-8") as f:
        idx = 0
        for speaker, s_start, s_end, text in labeled:
            idx += 1
            start_ts = fmt_srt_ts(s_start)
            end_ts = fmt_srt_ts(s_end)
            f.write(f"{idx}\n{start_ts} --> {end_ts}\n")
            f.write(f"[{speaker}] {text}\n\n")

    log_info(f"说话人数: {len({s for s, *_ in labeled})}")
    log_info(f"段落数: {len(labeled)}")
    log_info(f"输出: {output_path}")
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 合并说话人分离 + ASR → 带说话人的 SRT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""完整链路:
  # 1. 提取人声
  python audio/separate.py --input video.mp4 --output vocals.wav --stem vocals

  # 2. 说话人分离
  python audio/diarize.py --input vocals.wav --output diar.json

  # 3. ASR 转录
  python asr/transcribe.py --input vocals.wav --srt audio.srt

  # 4. 合并（← 本文件）
  python asr/speaker_srt.py --diarize diar.json --srt audio.srt --output audio_speaker.srt

  # 5. 烧字幕
  python asr/burn_subtitle.py --video video.mp4 --srt audio_speaker.srt --output final.mp4
        """,
    )
    parser.add_argument("--diarize", required=True,
                       help="diarize.py 输出的 JSON 文件")
    parser.add_argument("--srt", required=True,
                       help="asr/transcribe.py 输出的 SRT 文件")
    parser.add_argument("--output", required=True,
                       help="合并后的带说话人 SRT 路径")
    args = parser.parse_args()

    result = merge_speaker_srt(args.srt, args.diarize, args.output)
    if result is None:
        sys.exit(1)


if __name__ == "__main__":
    safe_run(main)
