# -*- coding: utf-8 -*-
"""
智剪工坊 · quotes 子技能
金句检测(从视频字幕/音频中找"最有冲击力"的几句话)

用法:
  python quotes.py --input in.mp4 --top 5 --out quotes.json

依赖:faster-whisper
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "lib"))
from common import (
    run_ffmpeg, get_duration, DEFAULT_ENCODE_ARGS,
    ensure_dir, log_info, log_warn, log_section, safe_run,
)


# 关键词权重(用于打分)
KEYWORDS_HIGH = {
    "坚持": 3, "放弃": 3, "3650": 3, "一定": 2, "相信": 2,
    "为什么": 2, "因为": 2, "梦想": 2, "改变": 2, "自律": 3,
    "减肥": 2, "目标": 1, "成功": 2, "失败": 1, "努力": 2,
    "不": 1, "没": 1, "别": 1,
}


def score_segment(text, start, end):
    """给转录段落打分"""
    score = 0
    text_lower = text.lower()

    # 短句更有冲击力
    if len(text) < 30:
        score += 2
    elif len(text) > 100:
        score -= 2

    # 关键词
    for kw, weight in KEYWORDS_HIGH.items():
        if kw in text:
            score += weight

    # 含数字
    if any(c.isdigit() for c in text):
        score += 1

    # 修辞(疑问句、感叹句)
    if "?" in text or "?" in text or "!" in text or "!" in text:
        score += 1

    # 第一人称(更真实)
    if "我" in text:
        score += 1

    return score


def find_quotes(video_path, top_n=5, model="medium", device="cuda", language=None):
    """从视频找 Top N 金句"""
    log_section(f"金句检测: {Path(video_path).name}")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log_warn("faster-whisper 未安装")
        log_warn("安装: pip install faster-whisper")
        return None

    log_info(f"加载模型: {model} ({device})")
    wm = WhisperModel(model, device=device)

    log_info("开始转录...")
    segments, info = wm.transcribe(
        str(video_path),
        language=language,
        word_timestamps=False,
    )

    # 评分
    scored = []
    for seg in segments:
        text = seg.text.strip()
        if not text or len(text) < 3:
            continue
        s = score_segment(text, seg.start, seg.end)
        scored.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": text,
            "score": s,
            "duration": round(seg.end - seg.start, 2),
        })

    # 排序取 Top N
    scored.sort(key=lambda x: x["score"], reverse=True)
    top_quotes = scored[:top_n]

    log_info(f"Top {top_n} 金句:")
    for i, q in enumerate(top_quotes, 1):
        log_info(f"  {i}. [{q['score']}分] {q['text']}")

    return {
        "video": str(video_path),
        "duration": get_duration(video_path),
        "total_segments": len(scored),
        "top_quotes": top_quotes,
    }


def save_quotes(quotes, output_path):
    """保存金句数据"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(quotes, f, ensure_ascii=False, indent=2)
    log_info(f"金句数据: {output_path}")


def cut_quotes(video_path, quotes, output_path, padding=1.0):
    """根据金句时间戳剪切金句片段"""
    log_section(f"剪切金句片段: {len(quotes['top_quotes'])} 段")
    ensure_dir(Path(output_path).parent)

    segments = []
    for i, q in enumerate(quotes["top_quotes"]):
        start = max(0, q["start"] - padding)
        end = min(quotes["duration"], q["end"] + padding)
        seg_path = Path(output_path).with_suffix(f".quote{i:02d}.mp4")

        run_ffmpeg([
            "-ss", str(start),
            "-i", str(video_path),
            "-t", str(end - start),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            str(seg_path),
        ])
        segments.append(seg_path)
        log_info(f"  [{i+1}] {start:.1f}s - {end:.1f}s: {q['text']}")

    # 合并
    if segments:
        list_file = Path(output_path).with_suffix(".list.txt")
        with open(list_file, "w") as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")

        run_ffmpeg([
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k",
            str(output_path),
        ])


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 · 金句检测",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", required=True, help="视频文件")
    parser.add_argument("--top", type=int, default=5, help="Top N 金句")
    parser.add_argument("--out", required=True, help="输出 JSON 或金句视频")
    parser.add_argument("--mode", choices=["detect", "cut"], default="detect",
                       help="detect=只检测,cut=检测+剪切")
    parser.add_argument("--model", default="medium")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--lang", help="指定语言")
    args = parser.parse_args()

    quotes = find_quotes(args.input, args.top, args.model, args.device, args.lang)
    if not quotes:
        return

    if args.mode == "cut":
        json_out = Path(args.out).with_suffix(".quotes.json")
        save_quotes(quotes, str(json_out))
        cut_quotes(args.input, quotes, args.out)
    else:
        save_quotes(quotes, args.out)


if __name__ == "__main__":
    safe_run(main)()
