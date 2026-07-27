"""居家管家 HELP 中心渲染器(总纲 07 §)

输入: references/scenarios.yaml(场景资产唯一事实源)
输出: help_center.html(总纲 04 §4 段式 + 07 §每场景独立复制按钮)

不展示 HELP 自身(07 §核心规则 2)。
"""
import sys
import yaml
from pathlib import Path
from datetime import datetime

SKILL_DIR = Path(__file__).parent.parent
SCENARIOS = SKILL_DIR / "references" / "scenarios.yaml"
TEMPLATE = "help_center.html"


def build_help_payload() -> dict:
    """读 scenarios.yaml → 渲染 payload(总纲 07 §2.1 场景资产 → HELP HTML)"""
    data = yaml.safe_load(SCENARIOS.read_text(encoding="utf-8"))
    scenarios = data.get("scenarios", [])

    # 按 wake_word 分组(保插入序,即 yaml 内出现顺序)
    grouped = {}
    for s in scenarios:
        grouped.setdefault(s["wake_word"], []).append(s)

    # 显式顺序:按 yaml 出现顺序(首个出现的 wake_word 排第一)
    groups = []
    seen = set()
    for s in scenarios:
        ww = s["wake_word"]
        if ww not in seen:
            seen.add(ww)
            groups.append({"wake_word": ww, "scenarios": grouped[ww]})

    # 时间戳: 支持环境变量固定(构建时 / 测试时一致),默认当前时间
    import os
    ts = os.environ.get("HELP_FIXED_TIMESTAMP") or datetime.now().strftime('%Y-%m-%d %H:%M')
    return {
        "status": "ok",
        "data": {
            "summary": {
                "title": "居家管家 · 能力速查",
                "subtitle": f"由 references/scenarios.yaml 渲染(总纲 07 §唯一事实源) · {ts} 更新",
                "metrics": [
                    {"label": "唤醒词", "value": str(len(groups))},
                    {"label": "场景", "value": str(len(scenarios))},
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
