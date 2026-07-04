"""scripts.step1_check_intent — v1.1 阶段 2 Step 1: 解析 + 自检

输入: --workspace /path/to/DAY2
输出: 00_智剪/粗加工/中间产物/自检报告.json + 操作清单.md (草稿)
行为: 解析 intent.json + 检查源文件存在 + 生成 v1.1 操作清单草稿
"""
import argparse
import json
import sys
import time
from pathlib import Path

# 让 lib/ 可被 import
_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT / "lib"))

from stage1_checklist import generate_and_save, INTERMEDIATE_DIR  # noqa: E402


def main():
    # v1.1: 用 shared cli_args（卡路里风格：底层 lib 无 argparse，step 脚本负责解析）
    from cli_args import make_base_parser
    parser = make_base_parser("v1.1 阶段 2 Step 1: 解析 + 自检")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    intent_path = workspace / "intent.json"

    print(f"[Step 1] workspace: {workspace}")

    # 1. 读 intent.json
    if not intent_path.exists():
        print(f"  ❌ intent.json 不存在: {intent_path}")
        sys.exit(1)
    try:
        intent = json.loads(intent_path.read_text(encoding="utf-8"))
        print(f"  ✓ 解析 intent.json (修订号 v{intent.get('_meta', {}).get('revision', '?')})")
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON 解析失败: {e}")
        sys.exit(1)

    # 2. 检查源文件存在
    videos = intent.get('videos', [])
    missing = []
    for v in videos:
        if v.get('exclude'):
            continue
        f = v.get('file', '')
        if not (workspace / f).exists():
            missing.append(f)

    if missing:
        print(f"  ⚠️ 源视频缺失 {len(missing)} 个:")
        for m in missing[:5]:
            print(f"     - {m}")
        if len(missing) > 5:
            print(f"     ... 还有 {len(missing)-5} 个")

    # 3. 写自检报告（v1.1 风格）
    out_dir = workspace / "00_智剪" / "粗加工" / INTERMEDIATE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    total_v = len(videos)
    excluded_v = sum(1 for v in videos if v.get('exclude'))
    sequences = intent.get('sequences', [])
    seq_video_set = set()
    for seq in sequences:
        for vi in seq.get('videos', []):
            seq_video_set.add(vi)
    free_v = [v.get('index') for v in videos
              if not v.get('exclude') and v.get('index') not in seq_video_set]

    report = {
        "version": "v1.1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "intent_path": str(intent_path),
        "intent_revision": intent.get('_meta', {}).get('revision'),
        "videos_total": total_v,
        "videos_excluded": excluded_v,
        "videos_to_process": total_v - excluded_v,
        "sequences_count": len(sequences),
        "sequence_videos": sorted(seq_video_set),
        "free_videos": free_v,
        "missing_sources": missing,
        "anomalies": [f"源视频缺失 {len(missing)} 个"] if missing else [],
    }
    report_path = out_dir / "自检报告.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"  ✓ 自检报告: {report_path.name}")

    # 4. 生成 v1.1 操作清单草稿
    checklist_path = generate_and_save(str(intent_path), str(workspace))
    print(f"  ✓ 操作清单 (草稿): {checklist_path}")

    # 5. 摘要
    print(f"\n[Step 1 摘要]")
    print(f"  共 {total_v} 个视频，{excluded_v} 排除，{total_v - excluded_v} 待处理")
    print(f"  sequence 含 {len(sequences)} 个，{len(seq_video_set)} 个视频")
    print(f"  自由视频: {free_v}")
    print(f"  异常: {len(report['anomalies'])} 条")


if __name__ == "__main__":
    main()