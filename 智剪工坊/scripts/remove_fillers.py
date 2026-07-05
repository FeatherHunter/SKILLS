# -*- coding: utf-8 -*-
"""
智剪工坊 · remove_fillers 子技能
两段式架构(无 LLM token 依赖):转录 → 智能判断 → 切割

支持 sentence-level 和 word-level 两种粒度。

用法:
  # 1. 转录(自动输出 SRT + words.json)
  python remove_fillers.py transcribe --input v.mp4 --srt v.srt

  # 2. agent(我)读 SRT + JSON,逐句/逐词判断,告诉你删什么

  # 3a. 句级切割(粗)
  python remove_fillers.py cut --input v.mp4 --srt v.srt --output v_clean.mp4 --remove 1,3,5

  # 3b. 词级切割(精准,推荐)
  python remove_fillers.py cut --input v.mp4 --srt v.srt --output v_clean.mp4 --remove-words 2,5,12

依赖:faster-whisper(转录)+ ffmpeg(切割)


📖 SKILL.md §14 索引 → REQUIRED: read references/09-ai-features.md
"""
import argparse
import json
import re
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    get_duration, ensure_dir, log_info, log_warn, log_error,
    log_section, safe_run,
)

try:
    from faster_whisper import WhisperModel
    WHISPER_OK = True
except ImportError as e:
    WHISPER_OK = False
    _WHISPER_ERR = str(e)


# ============================================================
# SRT 解析 / 生成
# ============================================================

def parse_srt(srt_text: str) -> list:
    """解析 SRT 文本,返回 [{idx, start, end, text}, ...]"""
    blocks = re.split(r"\n\s*\n", srt_text.strip())
    result = []
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 2:
            continue
        try:
            idx = int(lines[0].strip())
        except ValueError:
            continue
        time_line = None
        text_start = 1
        for i, line in enumerate(lines[1:], 1):
            if "-->" in line:
                time_line = line
                text_start = i + 1
                break
        if not time_line:
            continue
        m = re.match(
            r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)",
            time_line,
        )
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
        text = " ".join(lines[text_start:]).strip()
        if not text:
            continue
        result.append({"idx": idx, "start": start, "end": end, "text": text})
    return result


def format_srt(subs: list) -> str:
    """生成 SRT 文本"""
    lines = []
    for sub in subs:
        start_str = _sec_to_srt_time(sub["start"])
        end_str = _sec_to_srt_time(sub["end"])
        lines.append(f"{sub['idx']}\n{start_str} --> {end_str}\n{sub['text']}\n")
    return "\n".join(lines)


def _sec_to_srt_time(s: float) -> str:
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = int(s % 60)
    ms = int(round((s - int(s)) * 1000))
    if ms == 1000:
        sec += 1
        ms = 0
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


# ============================================================
# 索引解析(支持 1,3,5-8 语法)
# ============================================================

def parse_indices(spec: str, max_val: int) -> set:
    """解析 "1,3,5-8" → {1,3,5,6,7,8},剔除超出 max_val 的"""
    result = set()
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            a, b = token.split("-", 1)
            result.update(range(int(a), int(b) + 1))
        else:
            result.add(int(token))
    invalid = result - set(range(1, max_val + 1))
    if invalid:
        log_warn(f"忽略无效索引(超出 1-{max_val}): {sorted(invalid)[:20]}")
    return result & set(range(1, max_val + 1))


# ============================================================
# Whisper 转录
# ============================================================

def transcribe(input_path: Path, model_size: str = "small", device: str = "cpu",
               language: str = "zh") -> tuple:
    """
    用 faster-whisper 转录,返回 (sentences, words):
      sentences: [{idx, start, end, text}, ...]
      words: [{idx, start, end, word, sentence}, ...]
    """
    if not WHISPER_OK:
        log_error(f"缺 faster-whisper:{_WHISPER_ERR}\n  修复: pip install faster-whisper")
        sys.exit(3)

    log_info(f"加载 Whisper 模型({model_size}, {device})...")
    compute = "int8" if device == "cpu" else "float16"
    model = WhisperModel(model_size, device=device, compute_type=compute)
    log_info("开始转录(可能需要几分钟)...")

    segments, info = model.transcribe(
        str(input_path),
        language=language,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=500),
        word_timestamps=True,  # 关键:词级时间戳
    )

    sentences = []
    words = []
    word_idx = 0
    for seg_idx, seg in enumerate(segments, 1):
        text = seg.text.strip()
        if not text:
            continue
        sentences.append({
            "idx": seg_idx,
            "start": seg.start,
            "end": seg.end,
            "text": text,
        })
        # 词级时间戳
        if seg.words:
            for w in seg.words:
                word_idx += 1
                words.append({
                    "idx": word_idx,
                    "start": w.start,
                    "end": w.end,
                    "word": w.word.strip(),
                    "sentence": seg_idx,
                })
    log_info(f"转录完成: {len(sentences)} 句,{len(words)} 词,共 {info.duration:.1f}s")
    return sentences, words


# ============================================================
# 切割:句级
# ============================================================

def compute_keep_segments_from_sentences(subs, remove_indices, padding=0.05):
    """句级:删除整句,返回保留段"""
    keep = []
    last_kept_end = 0.0
    for sub in subs:
        if sub["idx"] in remove_indices:
            continue
        start = max(sub["start"] - padding, last_kept_end)
        end = sub["end"] + padding
        if end > start:
            keep.append((start, end))
            last_kept_end = end
    return keep


# ============================================================
# 切割:词级(把要删的词合并成连续段)
# ============================================================

def compute_word_remove_segments(words, remove_indices, padding=0.05, merge_gap=0.2):
    """
    根据要删的词索引,合并成连续时间段。
    词之间间隔 < merge_gap 秒(0.2s)就合并成一段切(避免硬切)。
    返回 [(start, end), ...]
    """
    removed = sorted(
        [w for w in words if w["idx"] in remove_indices],
        key=lambda w: w["start"],
    )
    if not removed:
        return []
    segments = []
    cur_s, cur_e = removed[0]["start"], removed[0]["end"]
    for w in removed[1:]:
        if w["start"] - cur_e <= merge_gap:
            cur_e = max(cur_e, w["end"])  # 合并
        else:
            segments.append((cur_s, cur_e))
            cur_s, cur_e = w["start"], w["end"]
    segments.append((cur_s, cur_e))
    # 加 padding
    return [(max(0.0, s - padding), e + padding) for s, e in segments]


def invert_segments(remove_segments, total_duration):
    """从总时长减去删除段,得到保留段"""
    keep = []
    last_end = 0.0
    for s, e in sorted(remove_segments):
        if s > last_end:
            keep.append((last_end, s))
        last_end = max(last_end, e)
    if last_end < total_duration:
        keep.append((last_end, total_duration))
    return keep


# ============================================================
# 视频切割(ffmpeg)
# ============================================================

def cut_video(input_path: Path, output_path: Path, keep_segments: list) -> None:
    if not keep_segments:
        log_warn("无可保留段,跳过切割")
        return
    log_info(f"切割 {len(keep_segments)} 段 → {output_path}")
    ensure_dir(output_path.parent)

    parts = []
    concat_inputs = []
    for i, (start, end) in enumerate(keep_segments):
        parts.append(f"[0:v]trim=start={start}:end={end},setpts=PTS-STARTPTS[v{i}];")
        parts.append(f"[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}];")
        concat_inputs.append(f"[v{i}][a{i}]")
    parts.append(f"{''.join(concat_inputs)}concat=n={len(keep_segments)}:v=1:a=1[outv][outa]")
    filter_complex = "".join(parts)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True,
                            encoding="utf-8", errors="ignore", timeout=3600)
    if result.returncode != 0:
        log_error(f"ffmpeg 失败: {result.stderr[-500:]}")
        sys.exit(1)


# ============================================================
# 子命令
# ============================================================

def cmd_transcribe(args):
    """Step 1: 转录 → SRT + words.json"""
    log_section(f"Step 1 · 转录: {args.input}")
    input_path = Path(args.input)
    if not input_path.exists():
        log_error(f"输入不存在: {input_path}")
        sys.exit(1)

    srt_path = Path(args.srt)
    sentences, words = transcribe(input_path, args.whisper_model, args.device, args.language)
    ensure_dir(srt_path.parent)
    srt_path.write_text(format_srt(sentences), encoding="utf-8")
    log_info(f"SRT 写好: {srt_path} ({len(sentences)} 句)")

    # 写词级 JSON
    json_path = srt_path.with_suffix(".words.json")
    json_path.write_text(
        json.dumps({"sentences": sentences, "words": words},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log_info(f"词级 JSON 写好: {json_path} ({len(words)} 词)")

    # 打印 SRT(给 Mavis 看)
    print()
    print("=" * 60)
    print(f"  SRT({len(sentences)} 句)")
    print("=" * 60)
    print(format_srt(sentences))
    print("=" * 60)
    print(f"  词级时间戳({len(words)} 词,每行一个)")
    print("=" * 60)
    for w in words:
        print(f"  [{w['idx']:3d}] {w['start']:6.2f}-{w['end']:6.2f}s 句{w['sentence']:2d}: {w['word']}")
    print("=" * 60)


def cmd_cut(args):
    """Step 3: 根据句/词索引切视频"""
    log_section(f"Step 3 · 切割: {args.input}")
    input_path = Path(args.input)
    if not input_path.exists():
        log_error(f"输入不存在: {input_path}")
        sys.exit(1)
    srt_path = Path(args.srt)
    if not srt_path.exists():
        log_error(f"SRT 不存在: {srt_path}(先跑 transcribe)")
        sys.exit(1)
    if not args.output:
        log_error("需要 --output 路径")
        sys.exit(1)
    if not args.remove and not args.remove_words:
        log_error("需要 --remove(句索引)或 --remove-words(词索引)")
        sys.exit(1)

    output_path = Path(args.output)
    sentences = parse_srt(srt_path.read_text(encoding="utf-8"))
    if not sentences:
        log_error("SRT 解析失败或为空")
        sys.exit(1)

    total_duration = get_duration(input_path)
    log_info(f"视频时长: {total_duration:.1f}s,{len(sentences)} 句")

    # 决定模式
    if args.remove_words:
        # 词级模式
        json_path = srt_path.with_suffix(".words.json")
        if not json_path.exists():
            log_error(f"词级 JSON 不存在: {json_path}(transcribe 时要输出过)")
            sys.exit(1)
        data = json.loads(json_path.read_text(encoding="utf-8"))
        words = data["words"]
        remove_indices = parse_indices(args.remove_words, max_val=len(words))
        if not remove_indices:
            log_warn("没有要删的词,跳过")
            return
        log_info(f"词级删除 {len(remove_indices)} 词:")
        for w in words:
            if w["idx"] in remove_indices:
                log_info(f"  [{w['idx']:3d}] {w['start']:6.2f}-{w['end']:6.2f}s 句{w['sentence']}: {w['word']}")
        # 合并成时间段
        remove_segs = compute_word_remove_segments(words, remove_indices, args.padding)
        log_info(f"合并成 {len(remove_segs)} 个连续删除段")
        # 保留 = 总时长 - 删除
        keep = invert_segments(remove_segs, total_duration)
    else:
        # 句级模式
        remove_indices = parse_indices(args.remove, max_val=len(sentences))
        if not remove_indices:
            log_warn("没有要删的句,跳过")
            return
        log_info(f"句级删除 {len(remove_indices)} 句:")
        for s in sentences:
            if s["idx"] in remove_indices:
                log_info(f"  [{s['idx']:3d}] {_sec_to_srt_time(s['start'])} {s['text'][:50]}")
        keep = compute_keep_segments_from_sentences(sentences, remove_indices, args.padding)

    if not keep:
        log_warn("无可保留段,不输出")
        return

    cut_video(input_path, output_path, keep)

    # 写新 SRT(基于句模式,词模式不重写 SRT——会让句时间戳错乱)
    if args.new_srt and not args.remove_words:
        kept_subs = [s for s in sentences if s["idx"] not in remove_indices]
        # 重新映射时间戳(用 keep 段)
        new_subs = []
        for sub, (s, e) in zip(kept_subs, keep):
            new_subs.append({"idx": sub["idx"], "start": s, "end": e, "text": sub["text"]})
        Path(args.new_srt).write_text(format_srt(new_subs), encoding="utf-8")
        log_info(f"新 SRT: {args.new_srt}")

    new_dur = get_duration(output_path)
    log_info(f"完成:{input_path} ({total_duration:.1f}s) → {output_path} ({new_dur:.1f}s)")
    log_info(f"省了 {total_duration - new_dur:.1f}s")


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · AI 去水词(两段式,无 LLM token 依赖)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "工作流:\n"
            "  1. transcribe: 视频 → SRT + words.json\n"
            "  2. agent 读 SRT + JSON,逐句/词判断,告诉你删什么\n"
            "  3. cut --remove(句)或 --remove-words(词,推荐)切视频"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # transcribe
    p_trans = subparsers.add_parser("transcribe", help="视频 → SRT + words.json")
    p_trans.add_argument("-i", "--input", required=True)
    p_trans.add_argument("--srt", required=True)
    p_trans.add_argument("--whisper-model", default="small",
                         choices=["tiny", "base", "small", "medium", "large-v3"])
    p_trans.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    p_trans.add_argument("--language", default="zh")
    p_trans.set_defaults(func=cmd_transcribe)

    # cut
    p_cut = subparsers.add_parser("cut", help="按索引切视频")
    p_cut.add_argument("-i", "--input", required=True)
    p_cut.add_argument("--srt", required=True)
    p_cut.add_argument("-o", "--output", required=True)
    p_cut.add_argument("--remove", help="句索引(eg 1,3,5-8)")
    p_cut.add_argument("--remove-words", help="词索引(eg 2,5,12,推荐)")
    p_cut.add_argument("--padding", type=float, default=0.05, help="切割边缘 padding(秒)")
    p_cut.add_argument("--new-srt", help="可选:新 SRT 路径(只用于句模式)")
    p_cut.set_defaults(func=cmd_cut)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    safe_run(main)()
