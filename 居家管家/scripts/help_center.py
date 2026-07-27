"""居家管家 HELP 中心渲染器(总纲 07 §)

输入: references/scenarios.yaml(场景资产唯一事实源)
输出: help_center.html(总纲 04 §4 段式 + 07 §每场景独立复制按钮)

分组策略(P1-11b 用户拍板,2026-07-27):
  一级 group = 人类语言任务导向(A 套,11 类)
    找东西 / 存东西 / 改东西 / 盘点 / 出门 / 回家 / 看统计 / 账号 / 检查 / 标签 / 帮助

不展示 HELP 自身(07 §核心规则 2)。
"""
import sys
import yaml
from pathlib import Path
from datetime import datetime
import os

SKILL_DIR = Path(__file__).parent.parent
SCENARIOS = SKILL_DIR / "references" / "scenarios.yaml"
TEMPLATE = "help_center.html"

# 11 类别 — A 套,人类语言任务导向
CATEGORY_ORDER = [
    "找东西", "存东西", "改东西", "盘点",
    "出门", "回家",
    "看统计", "账号", "检查", "标签",
    "帮助",
]


def build_help_payload() -> dict:
    """读 scenarios.yaml → 渲染 payload(总纲 07 §2.1 场景资产 → HELP HTML)

    分组规则:
      一级 group = scenario.category(A 套 11 类,顺序固定)
      每个 group 内:列出该类别下所有场景(按 yaml 出现顺序)
    """
    data = yaml.safe_load(SCENARIOS.read_text(encoding="utf-8"))
    scenarios = data.get("scenarios", [])

    # 时间戳: 支持环境变量固定(构建时 / 测试时一致),默认当前时间
    ts = os.environ.get("HELP_FIXED_TIMESTAMP") or datetime.now().strftime('%Y-%m-%d %H:%M')

    # 按 category 分组(P1-11b)
    by_category = {}
    total_wake_words = set()
    for s in scenarios:
        cat = s.get("category", "其他")
        by_category.setdefault(cat, []).append(s)
        total_wake_words.add(s["wake_word"])

    groups = []
    for cat in CATEGORY_ORDER:
        if cat not in by_category:
            continue
        # 收集该 category 下的 wake_words(去重保插入序)
        wake_words = []
        seen = set()
        for s in by_category[cat]:
            if s["wake_word"] not in seen:
                seen.add(s["wake_word"])
                wake_words.append(s["wake_word"])
        groups.append({
            "category": cat,
            "wake_words": wake_words,
            "scenarios": by_category[cat],
        })

    return {
        "status": "ok",
        "data": {
            "summary": {
                "title": "居家管家 · 能力速查",
                "subtitle": f"由 references/scenarios.yaml 渲染(总纲 07 §唯一事实源) · {ts} 更新",
                "metrics": [
                    {"label": "类别", "value": str(len(groups))},
                    {"label": "场景", "value": str(len(scenarios))},
                    {"label": "唤醒词", "value": str(len(total_wake_words))},
                ],
            },
            "groups": groups,
        },
        "message": "HELP 中心",
    }


if __name__ == "__main__":
    from render import render_page
    payload = build_help_payload()
    out = sys.argv[1] if len(sys.argv) > 1 else None
    print(render_page(TEMPLATE, payload, out))
