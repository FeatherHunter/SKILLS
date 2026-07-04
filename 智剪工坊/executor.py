#!/usr/bin/env python3
"""智剪工坊 Executor v1.1
========================

**默认 AI 不使用本工具**。AI 按 SKILL.md 流程**逐个调用 step 脚本**：
    python scripts/step1_check_intent.py --workspace <path>
    python scripts/step2_1_asr.py --workspace <path>
    python scripts/step2_2_process.py --workspace <path>
    python scripts/step3_assemble.py --workspace <path>
    python scripts/step4_fallback.py --workspace <path>
    python scripts/step5_decision.py --workspace <path>

本工具的用途：
- **批处理 / CI / 无 AI 交互场景**：一键跑完 6 个 step
- **AI 一键跑（不推荐）**：仅在用户明确说"全自动跑"时使用

为什么默认不用：v1.1 流程要求「每完成一个 video 立即汇报 + 模糊项逐条问」，
一键跑会绕过这些交互契约。
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

_SKILL_ROOT = Path(__file__).parent
SCRIPTS_DIR = _SKILL_ROOT / "scripts"


STEPS = [
    ("1", "step1_check_intent", "解析 + 自检 + 操作清单"),
    ("2.1", "step2_1_asr", "ASR 优先（批量转录）"),
    ("2.2", "step2_2_process", "单视频处理（基于 ASR 优化）"),
    ("3", "step3_assemble", "sequence 拼接（仅 sequence 内）"),
    ("4", "step4_fallback", "模糊项兜底"),
    ("5", "step5_decision", "决策报告 + 模板衔接"),
]


def run_step(step_id, step_script, workspace, skip_existing=True):
    """调用单个 step 脚本。"""
    script_path = SCRIPTS_DIR / f"{step_script}.py"
    if not script_path.exists():
        print(f"  ❌ 脚本不存在: {script_path}")
        return False, time.time()

    cmd = [sys.executable, str(script_path), "--workspace", str(workspace)]
    print(f"\n{'='*60}")
    print(f"[Step {step_id}] {step_script}")
    print(f"{'='*60}")

    t0 = time.time()
    try:
        result = subprocess.run(cmd, timeout=3600)
        elapsed = time.time() - t0
        return result.returncode == 0, elapsed
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        print(f"  ❌ Step {step_id} 超时 ({elapsed:.0f}s)")
        return False, elapsed
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  ❌ Step {step_id} 异常: {e}")
        return False, elapsed


def main():
    parser = argparse.ArgumentParser(
        description="智剪工坊 Executor v1.1 — 一键跑（默认 AI 不用）",
        epilog="默认 AI 不使用本工具，按 step 逐个调用 scripts/step*.py",
    )
    parser.add_argument("--workspace", required=True, help="工作区根目录")
    parser.add_argument("--steps", default="1,2.1,2.2,3,4,5",
                        help="逗号分隔的 step 列表（默认全部）")
    parser.add_argument("--yes", action="store_true",
                        help="跳过所有 AI 交互确认（一键跑到底）")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    if not workspace.exists():
        print(f"❌ workspace 不存在: {workspace}")
        sys.exit(1)

    selected = set(args.steps.split(","))
    print(f"=== 智剪工坊 Executor v1.1 ===")
    print(f"workspace: {workspace}")
    print(f"selected steps: {selected}")
    if not args.yes:
        print()
        print("⚠️ 警告：默认推荐 AI 按 step 逐个调用，本工具适合批处理/CI 场景。")
        print("⚠️ 一键跑会绕过 '每完成一个 video 立即汇报' + '模糊项逐条问' 契约。")
        print("⚠️ 如确认要全自动跑，加 --yes 参数。")
        sys.exit(0)

    results = []
    for step_id, step_script, desc in STEPS:
        if step_id not in selected:
            continue
        ok, elapsed = run_step(step_id, step_script, workspace)
        results.append((step_id, step_script, ok, elapsed))

    print(f"\n{'='*60}")
    print(f"=== 全部完成 ===")
    print(f"{'='*60}")
    for step_id, step_script, ok, elapsed in results:
        mark = "✓" if ok else "❌"
        print(f"  {mark} Step {step_id}: {step_script} ({elapsed:.1f}s)")
    fail_count = sum(1 for _, _, ok, _ in results if not ok)
    if fail_count:
        print(f"\n⚠️ {fail_count} 个 step 失败")
        sys.exit(1)
    print(f"\n✅ 全部成功")


if __name__ == "__main__":
    main()