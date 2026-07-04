"""scripts.step4_fallback — v1.1 阶段 2 Step 4: 整体复核 + 模糊项兜底

输入: --workspace /path/to/DAY2
行为:
  1. 读 操作清单.md (v2/v3 已确认) — 看 D 象限已拍板项
  2. 读 ASR 文字稿 — 基于文字稿自动优化 D2(文字卡内容) / D5(水词候选)
  3. 生成 模糊项处理记录.md — 列出待办 + AI 候选 + 用户确认
  4. (可选) 应用原子操作: 水词切除 / 文字卡烧字幕

注意: v1.1 阶段 2 Step 4 是 AI + 用户交互密集型，脚本做"自动候选 + 记录"。
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT / "lib"))

INTERMEDIATE_DIR = "中间产物"
TRANSCRIPTS_DIR = "文字稿"
SINGLE_DIR = "单视频"
FALLBACK_MD = "模糊项处理记录.md"


# 常见水词（中文口语填充词）
FILLER_WORDS = {"嗯", "啊", "呃", "哦", "那个", "这个", "就是说", "然后", "其实", "可能",
                "大概", "差不多", "就是说", "对吧", "你知道", "um", "uh", "like", "you know"}


def detect_fillers_in_md(md_path: Path):
    """从 markdown 文字稿中检测水词候选。
    返回 list[dict]: {word, line, suggestion}
    """
    if not md_path.exists():
        return []
    text = md_path.read_text(encoding="utf-8")
    candidates = []
    for line_no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line.startswith('-'):
            continue
        content = line.lstrip('-').strip()
        for filler in FILLER_WORDS:
            if filler in content:
                candidates.append({
                    "word": filler,
                    "line_no": line_no,
                    "line_text": content,
                    "suggestion": "考虑切除或缩短",
                })
    return candidates


def main():
    # v1.1: 用 shared cli_args（卡路里风格：底层 lib 无 argparse）
    from cli_args import make_base_parser
    parser = make_base_parser("v1.1 阶段 2 Step 4: 模糊项兜底")
    parser.add_argument("--apply", action="store_true",
                        help="应用自动候选（不推荐，AI 应逐条跟用户确认）")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    intermediate_dir = workspace / "00_智剪" / "粗加工" / INTERMEDIATE_DIR
    transcripts_dir = workspace / "00_智剪" / "粗加工" / TRANSCRIPTS_DIR
    single_dir = workspace / "00_智剪" / "粗加工" / SINGLE_DIR

    print(f"[Step 4] 模糊项兜底 — {workspace}")

    # 1. 读 操作清单
    checklist_path = intermediate_dir / "操作清单.md"
    checklist_version = "?"
    if checklist_path.exists():
        content = checklist_path.read_text(encoding="utf-8")
        m = re.search(r'# 操作清单 v(\d+)', content)
        if m:
            checklist_version = m.group(1)
        print(f"  ✓ 操作清单 v{checklist_version}: {checklist_path.name}")
    else:
        print(f"  ⚠️ 操作清单不存在: {checklist_path}")

    intent = json.loads((workspace / "intent.json").read_text(encoding="utf-8"))

    # 2. 处理 ASR 文字稿 — 自动检测水词
    print(f"\n  [D5 自动检测] 扫描 ASR 文字稿中的水词")
    filler_summary = {}  # idx -> list of candidates
    for v in intent.get('videos', []):
        if v.get('exclude'):
            continue
        idx = v.get('index')
        md_path = transcripts_dir / f"视频_{idx:02d}.md"
        candidates = detect_fillers_in_md(md_path)
        if candidates:
            filler_summary[idx] = candidates
            print(f"    #{idx}: 检测到 {len(candidates)} 个水词候选")
            for c in candidates[:3]:
                print(f"      - '{c['word']}' at line {c['line_no']}: {c['line_text'][:40]}...")
            if len(candidates) > 3:
                print(f"      ... 还有 {len(candidates)-3} 个")

    # 3. 文字卡内容候选 (D2) — 基于 ASR 文字稿生成简短的"这段在干嘛"
    print(f"\n  [D2 自动生成] 基于 summary + ASR 文字稿生成文字卡草稿")
    textcard_candidates = {}  # idx -> short description
    for v in intent.get('videos', []):
        if v.get('exclude'):
            continue
        idx = v.get('index')
        summary = (v.get('summary') or v.get('intent') or '').strip()
        if summary:
            # 简化：取 summary 前 12 字
            card = summary[:12].replace(" ", "")
            textcard_candidates[idx] = card
            print(f"    #{idx}: {card!r}")

    # 4. 写 模糊项处理记录.md
    record_path = intermediate_dir / FALLBACK_MD
    with record_path.open('w', encoding='utf-8') as f:
        f.write("# 模糊项处理记录（Step 4）\n\n")
        f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"操作清单版本: v{checklist_version}\n\n")

        f.write("## D5 水词检测结果（自动候选）\n\n")
        if filler_summary:
            f.write("| 视频 # | 水词数 | 候选示例 |\n")
            f.write("|--------|--------|----------|\n")
            for idx, cands in filler_summary.items():
                sample = ", ".join(set(c['word'] for c in cands[:5]))
                f.write(f"| {idx} | {len(cands)} | {sample} |\n")
            f.write("\n**说明**：这是基于关键词的候选，最终水词判定需 AI 看 words.json + SRT 时间戳。\n")
            f.write("**应用方法**：用 `scripts/remove_fillers.py` 走完整流程。\n")
        else:
            f.write("未检测到水词。\n")
        f.write("\n")

        f.write("## D2 文字卡内容候选（自动生成）\n\n")
        if textcard_candidates:
            f.write("| 视频 # | 文字卡建议 |\n")
            f.write("|--------|-----------|\n")
            for idx, card in textcard_candidates.items():
                f.write(f"| {idx} | {card} |\n")
            f.write("\n**说明**：基于 intent.videos[i].summary 自动截取，可由用户调整。\n")
            f.write("**应用方法**：在阶段 4 烧字幕时叠加，或用 `scripts/overlay.py` 加片头文字。\n")
        else:
            f.write("无 summary 可生成。\n")
        f.write("\n")

        # 其他 D 象限项
        f.write("## D 象限其他项\n\n")
        f.write("参考 操作清单.md D 象限。AI 跟用户逐条确认后在此记录。\n\n")

        f.write("## 用户决策记录\n\n")
        f.write("（AI 跟用户逐条讨论后填入）\n\n")
        f.write("### 已确认\n\n")
        f.write("- \n\n")
        f.write("### 待处理\n\n")
        f.write("- \n")
    print(f"\n  ✓ 模糊项处理记录: {record_path}")

    # 5. 汇总
    print(f"\n[Step 4 摘要]")
    print(f"  水词候选视频: {len(filler_summary)} 个")
    print(f"  文字卡候选视频: {len(textcard_candidates)} 个")
    if args.apply:
        print(f"  --apply 参数已设置，但 v1.1 推荐 AI 跟用户逐条确认后再应用")
    print(f"\n✅ Step 4 完成（AI 现在可跟用户逐条确认 D 象限）")


if __name__ == "__main__":
    main()