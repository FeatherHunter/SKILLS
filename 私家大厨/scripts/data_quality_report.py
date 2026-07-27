#!/usr/bin/env python3
"""
私家大厨 · 数据质量报告(场景 1 · 让 13 manager 立刻有产出)

调用 9 个 manager CLI 收集数据 → 计算每道菜的"完整度评分" → 输出 JSON 或 HTML

设计:
    - 调 recipe_manager.list 拿到所有菜
    - 每道菜:ingredients(≥3) + steps(≥3) + tips(≥1) + techniques(≥1) + background(有)
    - 评分公式:每项 20 分,满分 100
    - 输出按评分倒序(最差的排前面,引导用户先补)

启发式解析 fallback:
    大多数 manager 没加 print_or_emit,返裸文本。本脚本用正则提取关键数据。
    真实数据 vs 启发式解析可能略有偏差,但报告可用。
    治本:manager 加 print_or_emit + --json(Q3 argparse 重写时统一治)
"""
import sys
import os
import re
import json
import subprocess
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).resolve().parent


def call_cli_raw(*args) -> tuple:
    """调 scripts/<args> --json,返回 (status, data, raw_stdout, raw_stderr)"""
    cmd = ["python3", str(SCRIPT_DIR / args[0])] + list(args[1:]) + ["--json"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout.strip()
    err = r.stderr.strip()
    if out.startswith("{"):
        try:
            data = json.loads(out)
            return data.get("status"), data.get("data", {}), out, err
        except json.JSONDecodeError:
            return None, None, out, err
    return None, None, out, err


def call_cli_fallback(*args) -> str:
    """fallback:无 --json 跑,返 stdout 文本"""
    cmd = ["python3", str(SCRIPT_DIR / args[0])] + list(args[1:])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout.strip()


def collect_recipe_complete(recipe_id: str, recipe_name: str) -> dict:
    """收集 1 道菜的全部质量维度(启发式 + JSON 混合)"""
    result = {
        "recipe_id": recipe_id,
        "recipe_name": recipe_name,
        "ingredients_count": 0,
        "steps_count": 0,
        "tips_count": 0,
        "techniques_count": 0,
        "has_background": False,
        "has_nutrition": False,
        "difficulty": None,
        "total_time_minutes": None,
        "history_count": 0,
    }

    # 1. 食材(启发式:解析"共 N 种")
    raw = call_cli_fallback("ingredient_manager.py", "list", recipe_id)
    m = re.search(r'共\s*(\d+)\s*种', raw)
    if m:
        result["ingredients_count"] = int(m.group(1))
    else:
        # fallback:行数(每行 1 食材)
        result["ingredients_count"] = len([l for l in raw.split("\n") if l.strip() and l[0:1].isdigit()])

    # 2. 步骤(启发式:解析"第N步"出现次数)
    raw = call_cli_fallback("step_manager.py", "list", recipe_id)
    steps = re.findall(r'第(\d+)步', raw)
    result["steps_count"] = len(set(steps)) if steps else 0

    # 3. tips(启发式:看"没有小贴士"或统计行数)
    raw = call_cli_fallback("tip_manager.py", "list", recipe_id)
    if "没有小贴士" in raw or "没有" in raw:
        result["tips_count"] = 0
    else:
        # 数 "category" 出现次数(每条 tip 至少 1 个 category)
        result["tips_count"] = raw.count("category=") + raw.count("类别:") + raw.count("分类:")

    # 4. techniques(启发式:看"没有技法"或统计行数)
    raw = call_cli_fallback("technique_manager.py", "list-by-recipe", recipe_id)
    if "没有技法" in raw:
        result["techniques_count"] = 0
    else:
        result["techniques_count"] = raw.count("\n") - raw.count("---")  # 粗略:行数

    # 5. background(检查"起源故事"关键字)
    raw = call_cli_fallback("background_manager.py", "get", recipe_id)
    result["has_background"] = ("起源" in raw) or ("历史" in raw) or ("文化" in raw)

    # 6. nutrition(有 --json 支持)
    status, data, _, _ = call_cli_raw("nutrition_manager.py", "get", recipe_id)
    if status == "success" and data:
        result["has_nutrition"] = bool(data.get("calories") is not None)

    # 7. history(有 --json 支持)
    status, data, _, _ = call_cli_raw("history_manager.py", "list", recipe_id)
    if status == "success":
        history_list = data.get("history", []) if isinstance(data, dict) else []
        result["history_count"] = len(history_list)

    return result


def compute_score(data: dict) -> int:
    """完整度评分:每项 20 分,满分 100"""
    score = 0
    if data["ingredients_count"] >= 3: score += 20
    elif data["ingredients_count"] >= 1: score += 10
    if data["steps_count"] >= 3: score += 20
    elif data["steps_count"] >= 1: score += 10
    if data["tips_count"] >= 1: score += 20
    if data["techniques_count"] >= 1: score += 20
    if data["has_background"]: score += 20
    return score


def missing_items(data: dict) -> list:
    """缺失项清单(给用户看需要补什么)"""
    missing = []
    if data["ingredients_count"] < 3:
        missing.append(f"食材不足 3 种(当前 {data['ingredients_count']})")
    if data["steps_count"] < 3:
        missing.append(f"步骤不足 3 步(当前 {data['steps_count']})")
    if data["tips_count"] < 1:
        missing.append("没有小贴士(Q1 设计意图:每道菜 ≥ 1 tip)")
    if data["techniques_count"] < 1:
        missing.append("没有技法(Q2 设计意图:每步都该有技法)")
    if not data["has_background"]:
        missing.append("没有背景故事")
    return missing


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        print("""\n用法:
    python scripts/data_quality_report.py             # 输出 JSON
    python scripts/data_quality_report.py --html    # 输出 HTML 报告路径

调用的 9 个 manager(场景 1 核心:让 13 manager 第一次真正"被使用"):
    - recipe_manager.py list           (有 --json)
    - ingredient_manager.py list       (启发式解析)
    - step_manager.py list             (启发式解析)
    - tip_manager.py list              (启发式解析)
    - technique_manager.py list-by-recipe  (启发式解析)
    - background_manager.py get        (启发式解析)
    - nutrition_manager.py get         (有 --json)
    - history_manager.py list           (有 --json)
""")
        return

    # 1. 取所有菜(用 recipe_manager --json 模式)
    cmd = ["python3", str(SCRIPT_DIR / "recipe_manager.py"), "list", "--json"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    data = json.loads(r.stdout)
    if data.get("status") != "success":
        print(f"❌ recipe_manager.list 失败:{data.get('message', '未知错误')}")
        return
    recipes = data.get("data", {}).get("recipes", [])

    if not recipes:
        print("未找到任何菜谱")
        return

    # 2. 收集每道菜的完整度
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_recipes": len(recipes),
        "recipes": [],
        "summary": {"full_complete": 0, "partial": 0, "minimal": 0},
    }
    for r in recipes:
        data = collect_recipe_complete(r["id"], r["name"])
        data["score"] = compute_score(data)
        data["missing"] = missing_items(data)
        data["difficulty"] = r.get("difficulty")
        data["total_time_minutes"] = r.get("total_time_minutes")
        if data["score"] >= 80:
            report["summary"]["full_complete"] += 1
        elif data["score"] >= 40:
            report["summary"]["partial"] += 1
        else:
            report["summary"]["minimal"] += 1
        report["recipes"].append(data)

    # 按评分倒序(最差排前面,引导用户先补)
    report["recipes"].sort(key=lambda x: x["score"])

    if "--html" in sys.argv:
        from render_quality_report import render_html_report
        out_path = render_html_report(report)
        print(f"✅ 报告已生成: {out_path}")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()