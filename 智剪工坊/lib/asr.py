# -*- coding: utf-8 -*-
"""
lib.asr — ASR 包装层

设计决策（v0.7）：用 faster-whisper（DAY1 已实测可用）。
DAY1 处理时用过 scripts/auto_subtitle.py 的 transcribe_to_srt，本文件是其薄包装。

对外接口（3 个）：
    transcribe(video_path, srt_path) -> bool
    transcribe_batch(video_dir, output_dir) -> dict[video_name, srt_path]
    merge_to_md(transcript_dir, output_md) -> bool
"""

import sys
from pathlib import Path

# 让 scripts/ 可被 import
_SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

try:
    from auto_subtitle import transcribe_to_srt
except ImportError as e:
    raise ImportError(
        f"lib/asr.py 依赖 scripts/auto_subtitle.py，但导入失败: {e}\n"
        "确认 faster-whisper 已装：pip install faster-whisper"
    )


def transcribe(video_path, srt_path, model="medium", device="cuda", language=None):
    """单视频转录 → SRT。

    Args:
        video_path: 输入视频
        srt_path: 输出 SRT 路径
        model: whisper 模型大小 (tiny/base/small/medium/large-v3)
        device: cuda / cpu
        language: 强制语言代码（None=自动检测）
    Returns:
        bool: 成功
    """
    return transcribe_to_srt(video_path, srt_path, model=model,
                             device=device, language=language)


def transcribe_batch(video_dir, output_dir, model="medium", device="cuda"):
    """批量转录目录下所有 mp4。

    Args:
        video_dir: 视频目录
        output_dir: SRT 输出目录
    Returns:
        dict: {video_filename: srt_path or None(失败)}
    """
    video_dir = Path(video_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for video in sorted(video_dir.glob("*.mp4")):
        srt = output_dir / f"{video.stem}.srt"
        ok = transcribe(video, srt, model=model, device=device)
        results[video.name] = srt if ok else None
    return results


def merge_to_md(transcript_dir, output_md):
    """合并目录下所有 SRT → 一个 markdown。

    SRT 时间戳作为段标记保留，文本部分用 markdown bullet。
    """
    transcript_dir = Path(transcript_dir)
    if not transcript_dir.exists():
        return False

    srt_files = sorted(transcript_dir.glob("*.srt"))
    if not srt_files:
        return False

    output_md = Path(output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)

    sections = []
    for srt in srt_files:
        sections.append(f"## {srt.stem}\n")
        text = _srt_to_md(srt)
        sections.append(text)
        sections.append("")

    output_md.write_text("\n".join(sections), encoding="utf-8")
    return True


def _srt_to_md(srt_path):
    """粗略 SRT → markdown（每段一行）。不追求完美。"""
    lines = srt_path.read_text(encoding="utf-8").splitlines()
    out = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 段编号
        if line.isdigit():
            i += 1
            # 时间码
            if i < len(lines) and "-->" in lines[i]:
                i += 1
            # 文本（可能多行）
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(lines[i].strip())
                i += 1
            if text_lines:
                out.append(f"- {''.join(text_lines)}")
        i += 1
    return "\n".join(out)


# CLI
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="ASR 批量转录")
    p.add_argument("--input-dir", required=True, help="视频目录")
    p.add_argument("--output-dir", required=True, help="SRT 输出目录")
    p.add_argument("--model", default="medium")
    p.add_argument("--device", default="cuda")
    p.add_argument("--merge-to", help="合并到一个 md 文件")
    args = p.parse_args()

    results = transcribe_batch(args.input_dir, args.output_dir,
                                model=args.model, device=args.device)
    for name, srt in results.items():
        status = "✓" if srt else "✗"
        print(f"  {status} {name}")

    if args.merge_to:
        merge_to_md(args.output_dir, args.merge_to)
        print(f"  → merged to {args.merge_to}")
