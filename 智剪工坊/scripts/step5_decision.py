"""scripts.step5_decision — v1.1 阶段 2 Step 5: 决策报告 + 模板衔接

输入: --workspace /path/to/DAY2
行为:
  1. 汇总 intent.json + 自检报告 + profile + ASR 摘要
  2. 生成 决策.md
  3. 推荐模板加载（基于项目特征）
"""
import argparse
import json
import sys
import time
from pathlib import Path

_SKILL_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_SKILL_ROOT / "lib"))


INTERMEDIATE_DIR = "中间产物"
SINGLE_DIR = "单视频"
CHUNKS_DIR = "组合"
DECISION_MD = "决策.md"


def recommend_template(intent):
    """基于项目特征推荐模板。"""
    project_name = intent.get('project', {}).get('name', '')
    name_lower = project_name.lower()

    # 关键词匹配
    if any(k in name_lower for k in ['减脂', '减肥', '健身', '训练', '挑战', 'day']):
        return '健身vlog.yaml', '检测到减脂/健身/挑战/Day 类关键词'
    if any(k in name_lower for k in ['教程', '教学', '课程', '讲']):
        return '教程vlog.yaml', '检测到教程/教学类关键词'
    return 'VLOG.yaml', '默认通用模板'


def main():
    # v1.1: 用 shared cli_args（卡路里风格：底层 lib 无 argparse）
    from cli_args import make_base_parser
    parser = make_base_parser("v1.1 阶段 2 Step 5: 决策报告 + 模板衔接")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    intermediate_dir = workspace / "00_智剪" / "粗加工" / INTERMEDIATE_DIR
    single_dir = workspace / "00_智剪" / "粗加工" / SINGLE_DIR
    chunks_dir = workspace / "00_智剪" / "粗加工" / CHUNKS_DIR

    print(f"[Step 5] 决策报告 + 模板衔接 — {workspace}")

    intent = json.loads((workspace / "intent.json").read_text(encoding="utf-8"))
    report_path = intermediate_dir / "自检报告.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}

    # 收集 profile
    profiles = []
    if single_dir.exists():
        for prof_path in sorted(single_dir.glob("profile_*.json")):
            try:
                p = json.loads(prof_path.read_text(encoding="utf-8"))
                profiles.append(p)
            except Exception:
                pass

    # 收集 sequence 产物
    chunks = []
    if chunks_dir.exists():
        for mp4 in sorted(chunks_dir.glob("*.mp4")):
            chunks.append({"name": mp4.stem, "path": str(mp4), "size_mb": mp4.stat().st_size // 1024 // 1024})

    # 推荐模板
    template_name, reason = recommend_template(intent)

    # 写决策.md
    decision_path = workspace / "00_智剪" / "粗加工" / DECISION_MD
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    with decision_path.open('w', encoding='utf-8') as f:
        f.write("# 决策报告（Step 5）\n\n")
        f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        f.write("## 1. 项目概览\n\n")
        project = intent.get('project', {})
        f.write(f"- **项目名**: {project.get('name', '?')}\n")
        f.write(f"- **目标时长**: {project.get('target_length', '?')}\n")
        f.write(f"- **整体意图**: {project.get('overall_intent', '?')[:200]}\n")
        f.write(f"- **输出比例**: {intent.get('output', {}).get('aspect_ratio', '?')}\n\n")

        f.write("## 2. 视频处理统计\n\n")
        f.write(f"- 总数: {report.get('videos_total', '?')}\n")
        f.write(f"- 排除: {report.get('videos_excluded', '?')}\n")
        f.write(f"- 处理: {report.get('videos_to_process', '?')}\n")
        f.write(f"- 成功: {sum(1 for p in profiles if not p.get('error'))}\n")
        f.write(f"- 失败: {sum(1 for p in profiles if p.get('error'))}\n")
        f.write(f"- 异常: {len(report.get('anomalies', []))} 条\n\n")

        f.write("## 3. 序列拼接产物\n\n")
        if chunks:
            f.write("| sequence | 大小 |\n|----------|------|\n")
            for c in chunks:
                f.write(f"| {c['name']} | {c['size_mb']}MB |\n")
        else:
            f.write("无（可能未跑 Step 3）\n")
        f.write("\n")

        f.write("## 4. 模板加载建议\n\n")
        f.write(f"**推荐**: `模板/{template_name}`\n\n")
        f.write(f"**理由**: {reason}\n\n")
        f.write("**下一步**：\n")
        f.write(f"1. 确认加载 `模板/{template_name}`\n")
        f.write("2. AI 按模板 stage 一来一回引导（每个 stage AI 提方案 → 用户点头 → 执行）\n\n")

        f.write("## 5. 收尾建议（阶段 4）\n\n")
        cover = intent.get('cover', {})
        if cover.get('type'):
            f.write(f"- **封面**: {cover.get('type')} (prompt: {cover.get('prompt', '?')[:80]}...)\n")
            f.write(f"  - 用 `scripts/cover_ai.py` 生成\n")
        else:
            f.write("- **封面**: 未配置（待用户决定）\n")

        f.write("- **字幕**: Step 4 文字卡候选可烧字幕\n")
        f.write("  - 用 `scripts/auto_subtitle.py` 或 `scripts/overlay.py`\n")
        f.write("- **BGM**: 待用户选择（智剪工坊 `scripts/bgm_loop.py`）\n")
        f.write("- **输出**: `00_智剪/成片/vlog_final.mp4`\n\n")

        f.write("## 6. 已知遗留\n\n")
        f.write("- 待模板工作流（阶段 3）完成后才能进阶段 4 收尾\n")
        f.write("- 自由素材视频（不在 sequence 内）待模板 Stage 顺序阶段决定\n")

    print(f"  ✓ 决策报告: {decision_path}")
    print(f"\n[Step 5 摘要]")
    print(f"  视频处理: {sum(1 for p in profiles if not p.get('error'))}/{len(profiles)}")
    print(f"  sequence 产物: {len(chunks)}")
    print(f"  推荐模板: {template_name}")
    print(f"\n✅ Step 5 完成 — 进模板工作流（阶段 3）")


if __name__ == "__main__":
    main()