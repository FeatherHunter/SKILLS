#!/usr/bin/env python3
"""
饼干记账 · HELP HTML 渲染器 v2.4

按 SKILL开发总纲V1.0 §07 契约:
- 读 references/scenarios.json (唯一事实源)
- 注入 templates/help.html (含占位符 <!--INJECT-DATA-->)
- 输出 HTML 文件,默认 $DATA_DIR/biscuit_accountant_html/ (v2.5 同步卡路里 §4.1)

用法:
    python3 scripts/render_help.py              # 默认输出
    python3 scripts/render_help.py --out X.html  # 指定输出
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = _SCRIPT_DIR.parent
SCENARIOS_PATH = SKILL_DIR / "references" / "scenarios.json"
TEMPLATE_PATH = SKILL_DIR / "templates" / "help.html"


def load_scenarios() -> dict:
    """读场景资产(唯一事实源)"""
    if not SCENARIOS_PATH.exists():
        raise FileNotFoundError(f"场景资产不存在: {SCENARIOS_PATH}")
    return json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))


def enrich_scenarios(scenarios: dict) -> dict:
    """把场景资产包成模板期望的 payload (v2.4: 分 5 类组织)

    payload.data 结构:
      - categories:    5 类组织(含 ww 列表 + 每个 ww 的场景)
      - wake_words:    扁平列表(向后兼容 / 总数统计用)
      - scenarios_total / wake_words_total / pending_total
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta = scenarios.get("_meta", {})
    categories_def = scenarios.get("_categories", [])

    # 按 ww 名构建索引 (ww → scenarios)
    ww_to_scenarios = {
        ww: scs for ww, scs in scenarios.items()
        if not ww.startswith("_")
    }

    # 扁平 wake_words (保持向后兼容 + 总数统计)
    wake_words = []
    total = 0
    pending = 0
    for ww, scs in ww_to_scenarios.items():
        wake_words.append({
            "name": ww,
            "scenarios": scs,
            "count": len(scs),
            "pending_count": sum(1 for s in scs if s.get("status") == "【待开发】")
        })
        total += len(scs)
        pending += sum(1 for s in scs if s.get("status") == "【待开发】")

    # 按 _categories 组织 (v2.4)
    categories = []
    for cat in categories_def:
        cat_wws = []
        cat_total = 0
        cat_pending = 0
        for ww in cat.get("wake_words", []):
            scs = ww_to_scenarios.get(ww, [])
            cat_wws.append({
                "name": ww,
                "scenarios": scs,
                "count": len(scs),
                "pending_count": sum(1 for s in scs if s.get("status") == "【待开发】")
            })
            cat_total += len(scs)
            cat_pending += sum(1 for s in scs if s.get("status") == "【待开发】")
        categories.append({
            "key": cat["key"],
            "name": cat["name"],
            "icon": cat.get("icon", ""),
            "desc": cat.get("desc", ""),
            "wake_words": cat_wws,
            "ww_count": len(cat_wws),
            "scenario_count": cat_total,
            "pending_count": cat_pending
        })

    return {
        "status": "ok",
        "data": {
            "skill": "饼干记账",
            "version": meta.get("version", "v2.4"),
            "generated_at": now,
            "categories": categories,
            "wake_words": wake_words,
            "wake_words_total": len(wake_words),
            "scenarios_total": total,
            "pending_total": pending,
            # §12.B：4 条 HELP 唤醒词（与 SKILL.md §唤醒词总表 HELP 行同步）
            # 单列展示在 HELP 类别下（5 类别中第 5 类 wake_words=[]，避免重复计数）
            "help_wake_words": meta.get("help_wake_words", ["饼干记账 HELP"]),
            "type": "help",
            "title": "饼干记账 · 唤醒词速查台",
            "subtitle": "▸ 类别 → 选唤醒词 → 复制 prompt → 贴给 AI"
        },
        "message": "HELP 场景清单"
    }


def inject_payload(template: str, payload: dict) -> str:
    """注入 payload 到模板占位符(继承 §04 原则 4 安全规则)"""
    placeholder = "<!--INJECT-DATA-->"
    if template.count(placeholder) != 1:
        raise ValueError(
            f"模板占位符 {placeholder} 数量异常: 期望 1, 实际 {template.count(placeholder)}"
        )
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    inject_str = (
        f'<script id="payload" type="application/json">{payload_json}</script>'
    )
    return template.replace(placeholder, inject_str, 1)


def default_output_path() -> Path:
    """默认输出路径（§12.B 标准）:
    $DATA_DIR/biscuit_accountant_html/饼干记账_HELP_<YYYYMMDD>_<HHMMSS>[_N].html

    复用 scripts/html_paths.html_path()，传 §12.B 保留字「饼干记账_HELP」
    （html_paths.COMMAND_NAMES["help"] 也是这个值，保持一致）。
    """
    from html_paths import html_path
    return html_path("饼干记账_HELP")


def main():
    parser = argparse.ArgumentParser(description="饼干记账 · HELP 渲染器")
    parser.add_argument("--out", default=None, help="输出 HTML 路径")
    parser.add_argument("--check", action="store_true", help="仅校验不写文件")
    args = parser.parse_args()

    print(f"📥 HELP 渲染")
    print(f"   场景资产: {SCENARIOS_PATH}")

    scenarios = load_scenarios()
    payload = enrich_scenarios(scenarios)
    print(f"   唤醒词: {payload['data']['wake_words_total']} 个")
    print(f"   场景: {payload['data']['scenarios_total']} 个")
    print(f"   待开发: {payload['data']['pending_total']} 个")

    if args.check:
        print(f"\n✓ 校验通过(未写文件)")
        return 0

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = inject_payload(template, payload)

    output_path = Path(args.out) if args.out else default_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8-sig")

    print(f"\n✓ 已生成: {output_path}")
    print(f"  用浏览器打开即可查看。")
    return 0


if __name__ == "__main__":
    sys.exit(main())