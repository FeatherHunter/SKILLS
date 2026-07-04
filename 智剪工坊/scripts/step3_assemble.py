"""scripts.step3_assemble — v1.1 阶段 2 Step 3: sequence 拼接（仅 sequence 内视频）

输入: --workspace /path/to/DAY2 [--sequence 开场]
行为: 读 intent.json.sequences + 单视频产物 → xfade 链拼接
      输出 组合/seq_<name>.mp4 + 自由素材清单.md
"""
import argparse
import json
import sys
import time
from pathlib import Path

_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT / "lib"))

from processing import xfade_concat, concatenate_simple  # noqa: E402


SINGLE_DIR = "单视频"
CHUNKS_DIR = "组合"
INTERMEDIATE_DIR = "中间产物"
FREE_LIST_MD = "自由素材清单.md"
LOG_FILE = "拼接日志.log"


def main():
    parser = argparse.ArgumentParser(description="v1.1 阶段 2 Step 3: sequence 拼接")
    # v1.1: 用 shared cli_args（卡路里风格：底层 lib 无 argparse）
    from cli_args import make_base_parser
    parser = make_base_parser("v1.1 阶段 2 Step 3: sequence 拼接")
    parser.add_argument("--sequence", default="", help="只拼接指定 sequence 名（默认全部）")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    intent = json.loads((workspace / "intent.json").read_text(encoding="utf-8"))

    single_dir = workspace / "00_智剪" / "粗加工" / SINGLE_DIR
    chunks_dir = workspace / "00_智剪" / "粗加工" / CHUNKS_DIR
    intermediate_dir = workspace / "00_智剪" / "粗加工" / INTERMEDIATE_DIR
    chunks_dir.mkdir(parents=True, exist_ok=True)
    intermediate_dir.mkdir(parents=True, exist_ok=True)

    sequences = intent.get('sequences', [])
    only_seq = args.sequence

    print(f"[Step 3] sequence 拼接 — {len(sequences)} 个 sequence")

    # 自由素材（v1.1 新增：未在 sequence 内的视频）
    seq_video_set = set()
    for seq in sequences:
        for vi in seq.get('videos', []):
            seq_video_set.add(vi)
    all_processed = [
        v.get('index') for v in intent.get('videos', [])
        if not v.get('exclude')
    ]
    free_videos = [i for i in all_processed if i not in seq_video_set]

    # 写自由素材清单
    free_path = intermediate_dir / FREE_LIST_MD
    with free_path.open('w', encoding='utf-8') as f:
        f.write("# 自由素材清单（v1.1 新增）\n\n")
        f.write("> 这些视频**不在任何 sequence 内**，Step 3 不处理。\n")
        f.write("> 留给模板工作流 Stage 顺序阶段讨论怎么安排。\n\n")
        f.write(f"## 共 {len(free_videos)} 段\n\n")
        for idx in free_videos:
            v = next((vv for vv in intent['videos'] if vv.get('index') == idx), None)
            if v:
                f.write(f"- **#{idx}** `{v.get('file')}` — {v.get('summary', v.get('intent', ''))}\n")
        f.write(f"\n## 排除的视频（exclude=true）\n\n")
        excluded = [v.get('index') for v in intent.get('videos', []) if v.get('exclude')]
        for idx in excluded:
            f.write(f"- #{idx}\n")
    print(f"  ✓ 自由素材清单: {free_path}")

    log_lines = [f"=== Step 3 sequence 拼接 {time.strftime('%Y-%m-%d %H:%M:%S')} ==="]
    log_lines.append(f"workspace: {workspace}")
    log_lines.append(f"自由素材: {free_videos}")
    log_lines.append("")

    chunk_paths = {}
    for seq in sequences:
        name = seq.get('name', 'seq_default')
        if only_seq and name != only_seq:
            continue
        videos = seq.get('videos', [])
        transitions = seq.get('transitions', [])

        print(f"\n  [Sequence: {name}] videos={videos}")
        log_lines.append(f"[{name}] videos={videos}")

        # 收集单视频路径
        single_paths = []
        for idx in videos:
            sp = single_dir / f"video_{idx:02d}.mp4"
            if not sp.exists():
                print(f"    ⚠️ #{idx} 单视频不存在: {sp}")
                log_lines.append(f"  ⚠️ #{idx} 单视频不存在")
                continue
            single_paths.append(sp)

        if not single_paths:
            print(f"    ❌ 没有可用视频")
            log_lines.append(f"  ❌ 没有可用视频")
            continue

        # 拼接（xfade 链）
        out_path = chunks_dir / f"{name}.mp4"
        if len(single_paths) == 1:
            import shutil
            shutil.copy2(single_paths[0], out_path)
            print(f"    ✓ {out_path.name} (单视频复制)")
        else:
            current = single_paths[0]
            for i in range(1, len(single_paths)):
                # 找当前 transition
                trans = next((t for t in transitions
                              if t.get('after') == videos[i-1]),
                             {'type': 'fade', 'duration': 0.5})
                tmp = chunks_dir / f"_tmp_{name}_{i}.mp4"
                result = xfade_concat(current, single_paths[i], trans, tmp)
                if result is None:
                    print(f"    ❌ xfade #{i} 失败")
                    log_lines.append(f"  ❌ xfade #{i} 失败")
                    break
                current = result
            else:
                import shutil
                shutil.move(str(current), str(out_path))
                print(f"    ✓ {out_path.name} ({out_path.stat().st_size//1024//1024}MB)")

        chunk_paths[name] = out_path
        log_lines.append(f"  ✓ {out_path}")

    # 写日志
    log_path = intermediate_dir / LOG_FILE
    log_path.write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\n  ✓ 拼接日志: {log_path}")
    print(f"\n✅ Step 3 完成: {len(chunk_paths)} 个 sequence 拼好")


if __name__ == "__main__":
    main()