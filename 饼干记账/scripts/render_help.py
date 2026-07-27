#!/usr/bin/env python3
"""
饼干记账 · HELP HTML 渲染器 v1.0

按 SKILL开发总纲V1.0 §07 契约:
- 读 references/scenarios.json (唯一事实源)
- 注入 templates/help.html (含占位符 <!--INJECT-DATA-->)
- 输出 HTML 文件,默认到 D:/Downloads/

用法:
    python3 scripts/render_help.py              # 默认输出
    python3 scripts/render_help.py --out X.html  # 指定输出
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

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
    """把场景资产包成模板期望的 payload"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    wake_words = []
    total = 0
    pending = 0
    for ww, scs in scenarios.items():
        if ww.startswith("_"):
            continue
        wake_words.append({
            "name": ww,
            "scenarios": scs,
            "count": len(scs),
            "pending_count": sum(1 for s in scs if s.get("status") == "【待开发】")
        })
        total += len(scs)
        pending += sum(1 for s in scs if s.get("status") == "【待开发】")

    return {
        "status": "ok",
        "data": {
            "skill": "饼干记账",
            "version": "v2.3",
            "generated_at": now,
            "wake_words": wake_words,
            "scenarios_total": total,
            "wake_words_total": len(wake_words),
            "pending_total": pending,
            "type": "help",
            "title": "饼干记账 · 能力速查",
            "subtitle": "所有唤醒词 × 全部合法场景,一键复制 prompt 给 AI"
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
    """默认输出路径:跨平台 fallback 链
    1. D:/Downloads (Windows 原生)
    2. ~/Downloads (Linux/macOS 标准)
    3. cwd (最后兜底)
    """
    fname = f"饼干记账_HELP_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    for candidate in (Path("D:/Downloads"), Path.home() / "Downloads"):
        if candidate.exists():
            return candidate / fname
    return Path.cwd() / fname


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
    output_path.write_text(html, encoding="utf-8")

    print(f"\n✓ 已生成: {output_path}")
    print(f"  用浏览器打开即可查看。")
    return 0


if __name__ == "__main__":
    sys.exit(main())