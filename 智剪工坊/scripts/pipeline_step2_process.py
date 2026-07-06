"""scripts.step2_2_process — v1.1 阶段 2 Step 2.2: 单视频处理

输入: --workspace /path/to/DAY2 [--videos 1,2,3] [--force]
行为: 读 intent.json + 操作清单 (A 象限) → 处理每个视频
      每处理完一个立即 print 路径 + 摘要 + 异常
      支持增量模式（已有产物+profile 跳过）
      集成 ASR 文字稿（如果存在）作为优化输入（v1.1 信息流）
输出: 00_智剪/粗加工/单视频/video_{idx}.mp4 + profile_{idx}.json
      00_智剪/粗加工/中间产物/单视频汇总.md
"""
import argparse
import json
import sys
import time
from pathlib import Path

_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT / "lib"))

from processing import process_video  # noqa: E402


SINGLE_DIR = "单视频"
INTERMEDIATE_DIR = "中间产物"
SUMMARY_MD = "单视频汇总.md"


def main():
    # v1.1: 用 shared cli_args（与卡路里技能对齐风格）
    from cli_args import make_base_parser, resolve_aspect
    parser = make_base_parser("v1.1 阶段 2 Step 2.2: 单视频处理")
    parser.add_argument("--videos", default="", help="逗号分隔的视频 index（默认所有）")
    parser.add_argument("--force", action="store_true", help="强制重跑")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    intent_path = workspace / "intent.json"
    intent = json.loads(intent_path.read_text(encoding="utf-8"))

    single_dir = workspace / "00_智剪" / "粗加工" / SINGLE_DIR
    intermediate_dir = workspace / "00_智剪" / "粗加工" / INTERMEDIATE_DIR
    single_dir.mkdir(parents=True, exist_ok=True)
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    # v1.1: aspect 解析（CLI > intent > 默认 16:9），支持 5 种比例
    # v1.2: aspect_handling（默认 preserve 保留原构图，intent.output.aspect_handling 可覆盖）
    aspect = resolve_aspect(args, intent)
    aspect_handling = intent.get('output', {}).get('aspect_handling', 'aspect-fit')
    if aspect_handling not in ('aspect-fill', 'aspect-fit'):
        aspect_handling = 'aspect-fit'
    transcripts_dir = workspace / "00_智剪" / "粗加工" / "文字稿"

    only_videos = set()
    if args.videos:
        only_videos = {int(x) for x in args.videos.split(",") if x.strip()}

    targets = []
    for v in intent.get('videos', []):
        if v.get('exclude'):
            continue
        idx = v.get('index')
        if only_videos and idx not in only_videos:
            continue
        targets.append(v)

    print(f"[Step 2.2] 单视频处理 — {len(targets)} 个")
    print(f"  workspace: {workspace}")
    print(f"  比例: {aspect}")
    print(f"  输出: {single_dir}")
    print()

    profiles = []
    for i, v in enumerate(targets, 1):
        idx = v.get('index')
        out_path = single_dir / f"video_{idx:02d}.mp4"
        prof_path = single_dir / f"profile_{idx:02d}.json"

        # 增量模式
        if (out_path.exists() and out_path.stat().st_size > 1000
                and prof_path.exists() and not args.force):
            print(f"[{i}/{len(targets)}] #{idx} 跳过 (已有产物)")
            try:
                profiles.append(json.loads(prof_path.read_text(encoding="utf-8")))
            except Exception:
                pass
            continue

        # v1.1：检查 ASR 文字稿（信息流：ASR → 拍板 → 处理）
        transcript_path = transcripts_dir / f"视频_{idx:02d}.md"
        transcript_status = "❌ no ASR"
        if transcript_path.exists():
            size = transcript_path.stat().st_size
            transcript_status = f"✓ ASR ({size}B)"

        t0 = time.time()
        _, profile, ok = process_video(v, workspace, out_path, target_aspect=aspect, aspect_handling=aspect_handling)
        elapsed = time.time() - t0

        if not ok:
            print(f"[{i}/{len(targets)}] #{idx} ❌ 处理失败 ({elapsed:.1f}s)")
            print(f"   错误: {profile.get('error', '?')}")
            print(f"   ASR: {transcript_status}")
            profiles.append({"index": idx, "error": profile.get('error'), "success": False})
            print()
            continue

        # 写 profile
        prof_path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        profiles.append(profile)
        print(f"[{i}/{len(targets)}] #{idx} {v.get('file', '')}")
        print(f"   源: {profile['source_resolution']} "
              f"rotation={profile.get('rotation_applied', 0)}° "
              f"duration={profile.get('output_duration', '?')}s")
        print(f"   输出: {out_path.name} ({out_path.stat().st_size//1024}KB) "
              f"ops={profile['applied_ops']} voice={profile['voice_mode']} "
              f"耗时 {elapsed:.1f}s")
        print(f"   ASR: {transcript_status}")
        print()

    # 写 单视频汇总.md
    summary_path = intermediate_dir / SUMMARY_MD
    with summary_path.open('w', encoding='utf-8') as f:
        f.write("# 单视频处理汇总（Step 2.2）\n\n")
        f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"共 {len([p for p in profiles if p.get('success', True)])} 个视频处理成功\n\n")
        f.write("| # | 源文件 | 源分辨率 | rotation | 应用 op | 输出分辨率 | 输出时长 | voice | ASR |\n")
        f.write("|---|--------|---------|----------|--------|-----------|---------|-------|-----|\n")
        for p in sorted(profiles, key=lambda x: x.get('index', 0)):
            if not p.get('success', True):
                continue
            idx = p.get('index')
            transcript_path = transcripts_dir / f"视频_{idx:02d}.md"
            asr_mark = "✓" if transcript_path.exists() else "✗"
            f.write(f"| {idx} | {p.get('source_file', '?')} | "
                    f"{p.get('source_resolution', '?')} | "
                    f"{p.get('rotation_applied', 0)}° | "
                    f"{','.join(p.get('applied_ops', [])) or '(无)'} | "
                    f"{p.get('output_resolution', '?')} | "
                    f"{p.get('output_duration', '?')}s | "
                    f"{p.get('voice_mode', '?')} | {asr_mark} |\n")
        f.write("\n## profile 文件清单\n\n")
        for p in sorted(profiles, key=lambda x: x.get('index', 0)):
            if not p.get('success', True):
                continue
            f.write(f"- `单视频/profile_{p['index']:02d}.json`\n")
    print(f"✓ 汇总报告: {summary_path}")

    # 统计
    ok_count = sum(1 for p in profiles if p.get('success', True))
    fail_count = sum(1 for p in profiles if not p.get('success', True))
    print(f"\n✅ Step 2.2 完成: {ok_count} 成功 / {fail_count} 失败 / 共 {len(targets)}")


if __name__ == "__main__":
    main()