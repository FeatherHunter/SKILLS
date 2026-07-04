"""scripts.step2_1_asr — v1.1 阶段 2 Step 2.1: ASR 优先（批量）

输入: --workspace /path/to/DAY2 [--model small|medium|large-v3]
                     [--device cuda|cpu] [--language zh]
                     [--videos 1,2,3] (默认所有 voice!=mute 的视频)
行为: 批量转录所有需要 ASR 的视频，每完成一个立即 print
输出: 00_智剪/粗加工/文字稿/视频_{idx}.{srt,md} + 全部.md
"""
import argparse
import json
import sys
import time
from pathlib import Path

_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT / "lib"))
sys.path.insert(0, str(_SKILL_ROOT / "scripts"))

from asr import transcribe, _srt_to_md, merge_to_md  # noqa: E402


TRANSCRIPTS_DIR = "文字稿"


def probe_duration(video_path: Path, ffmpeg: str = None) -> float:
    """快速探测视频时长（秒）。"""
    import subprocess, re
    if ffmpeg is None:
        # 优先 imageio_ffmpeg，其次 PATH
        candidate = Path(r'D:\0Tools\Python313\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg.exe')
        ffmpeg = str(candidate) if candidate.exists() else 'ffmpeg'
    try:
        r = subprocess.run(
            [ffmpeg, '-hide_banner', '-i', str(video_path)],
            capture_output=True, text=True, timeout=30
        )
        m = re.search(r'Duration:\s*(\d+):(\d+):(\d+\.?\d*)', r.stderr)
        if m:
            return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="v1.1 阶段 2 Step 2.1: ASR 优先")
    parser.add_argument("--workspace", required=True, help="工作区根目录")
    parser.add_argument("--model", default="small", help="whisper 模型")
    parser.add_argument("--device", default="cuda", help="cuda 或 cpu")
    parser.add_argument("--language", default="zh", help="语言代码")
    parser.add_argument("--videos", default="", help="逗号分隔的视频 index 列表（默认所有）")
    parser.add_argument("--force", action="store_true", help="强制重跑已有 SRT")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    intent_path = workspace / "intent.json"
    intent = json.loads(intent_path.read_text(encoding="utf-8"))

    out_dir = workspace / "00_智剪" / "粗加工" / TRANSCRIPTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # 找出需要 ASR 的视频
    only_videos = set()
    if args.videos:
        only_videos = {int(x) for x in args.videos.split(",") if x.strip()}

    targets = []
    for v in intent.get('videos', []):
        if v.get('exclude'):
            continue
        voice = v.get('voice', 'keep')
        if voice in ('mute', 'bgm-only'):
            continue
        idx = v.get('index')
        if only_videos and idx not in only_videos:
            continue
        targets.append(v)

    print(f"[Step 2.1] ASR 优先 — {len(targets)} 个视频")
    print(f"  workspace: {workspace}")
    print(f"  model={args.model} device={args.device} language={args.language}")
    print(f"  输出: {out_dir}")
    print()

    results = []
    for i, v in enumerate(targets, 1):
        idx = v['index']
        file = v['file']
        src = workspace / file
        if not src.exists():
            print(f"[{i}/{len(targets)}] #{idx} ❌ 源不存在: {file}")
            results.append((idx, file, 'missing'))
            continue

        srt_path = out_dir / f"视频_{idx:02d}.srt"
        md_path = out_dir / f"视频_{idx:02d}.md"

        if srt_path.exists() and srt_path.stat().st_size > 0 and not args.force:
            print(f"[{i}/{len(targets)}] #{idx} 跳过 (已有 SRT)")
            results.append((idx, file, 'skip'))
            continue

        duration = probe_duration(src)
        print(f"[{i}/{len(targets)}] #{idx} {file}")
        print(f"   时长: {duration:.2f}s" if duration else "   时长: ?")

        t0 = time.time()
        try:
            ok = transcribe(src, srt_path,
                            model=args.model, device=args.device,
                            language=args.language)
        except Exception as e:
            print(f"   ❌ ASR 异常: {e}")
            results.append((idx, file, 'fail'))
            continue
        elapsed = time.time() - t0

        if not ok or not srt_path.exists() or srt_path.stat().st_size == 0:
            print(f"   ❌ ASR 失败 ({elapsed:.1f}s)")
            results.append((idx, file, 'fail'))
            continue

        size = srt_path.stat().st_size
        print(f"   ✓ {srt_path.name} ({size}B) 耗时 {elapsed:.1f}s")

        # 转 .md
        try:
            md_text = _srt_to_md(srt_path)
            md_path.write_text(
                f"# 视频 {idx:02d} 文字稿\n\n"
                f"源文件: {file}\n"
                f"时长: {duration:.2f}s\n"
                f"ASR 耗时: {elapsed:.1f}s\n\n"
                f"---\n\n{md_text}\n",
                encoding="utf-8"
            )
            print(f"   ✓ {md_path.name} ({md_path.stat().st_size}B)")
        except Exception as e:
            print(f"   ⚠️ 转 md 失败: {e}")

        results.append((idx, file, 'ok'))
        print()

    # 合并 全部.md
    print("--- 合并 全部.md ---")
    all_md = out_dir / "全部.md"
    if merge_to_md(out_dir, all_md):
        print(f"  ✓ {all_md.name} ({all_md.stat().st_size}B)")
    else:
        print(f"  ⚠️ 合并失败")

    # 统计
    ok_count = sum(1 for r in results if r[2] in ('ok', 'skip'))
    fail_count = sum(1 for r in results if r[2] in ('fail', 'missing'))
    print(f"\n✅ Step 2.1 完成: {ok_count} 成功 / {fail_count} 失败 / 共 {len(targets)}")
    print(f"   文字稿目录: {out_dir}")


if __name__ == "__main__":
    main()