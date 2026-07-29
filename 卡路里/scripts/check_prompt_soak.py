#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_prompt_soak.py — 跨页面 prompt 一致性守护

ticket 15 · D7 spec · 2026-07-29
守护同一 wake_word 在多个 presentation surface 上的 prompt 文本字面一致:
  1. _triggers.py 的 main_prompt.text(SoT 源头)
  2. render_home.py quick_actions[i].prompt(主页 dashboard 快捷命令)
  3. render_help_center.py 渲染的 __DATA__.triggers[*].main_prompt.text(HELP HTML)

任一不一致 → exit 1 + 报具体 wake_word + 两端 diff。

用法:
    python scripts/check_prompt_soak.py
"""
from __future__ import annotations

import difflib
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))


def _diff_report(wake: str, surface: str, a: str, b: str) -> list[str]:
    """生成可读 diff"""
    if a == b:
        return []
    a_lines = a.splitlines()
    b_lines = b.splitlines()
    diff = list(difflib.unified_diff(
        a_lines, b_lines,
        fromfile=f'_triggers/{wake}',
        tofile=f'{surface}/{wake}',
        lineterm='',
    ))
    return [
        f'❌ wake_word={wake!r} 在 {surface} 与 _triggers 不一致:',
        *[f'  {ln}' for ln in diff[:10]],
    ]


def check_home_dashboard_prompts() -> list[str]:
    """render_home quick_actions vs _triggers"""
    from _triggers import TRIGGERS
    from render_home import _attach_prompts, QUICK_ACTIONS, _QUICK_ACTION_WAKE_MAP
    wake_to_prompt = {t['wake_word']: t['main_prompt']['text'] for t in TRIGGERS}
    issues = []
    for a in _attach_prompts(QUICK_ACTIONS):
        wake = a.get('wake_word')
        if not wake:
            issues.append(f'quick_action {a["label"]!r} 缺 wake_word 映射')
            continue
        src = wake_to_prompt.get(wake)
        if src is None:
            issues.append(f'quick_action {a["label"]!r} wake_word={wake!r} 不在 TRIGGERS')
            continue
        issues.extend(_diff_report(wake, 'home_dashboard', src, a.get('prompt', '')))
    return issues


def check_help_center_payload() -> list[str]:
    """HELP HTML __DATA__.triggers vs _triggers(若 calorie_html/ 有最新 HELP render)"""
    from _triggers import TRIGGERS
    import json
    import re

    help_htmls = sorted((SKILL_DIR / 'calorie_html').glob('卡路里_HELP_*.html'), reverse=True)
    if not help_htmls:
        return []  # 无 render 产物,skip(由 check_decision_matrix 守护存在性)
    latest = help_htmls[0]
    text = latest.read_text(encoding='utf-8')
    m = re.search(r'<script>\s*window\.__DATA__\s*=\s*(\{.*?\});?\s*</script>', text, re.DOTALL)
    if not m:
        return [f'⚠ {latest.name} 缺 __DATA__ 注入,无法校验']
    try:
        payload = json.loads(m.group(1).replace('<\\/', '</'))
    except json.JSONDecodeError as e:
        return [f'⚠ {latest.name} JSON parse fail: {e}']

    rendered = {t['wake_word']: t['main_prompt']['text']
                for t in payload.get('data', {}).get('triggers', [])}
    wake_to_prompt = {t['wake_word']: t['main_prompt']['text'] for t in TRIGGERS}
    issues = []
    for wake, src in wake_to_prompt.items():
        if wake not in rendered:
            issues.append(f'HELP HTML 缺 wake_word={wake!r}')
            continue
        issues.extend(_diff_report(wake, 'help_center', src, rendered[wake]))
    return issues


def main() -> int:
    issues: list[str] = []
    issues.extend(check_home_dashboard_prompts())
    issues.extend(check_help_center_payload())

    if issues:
        print(f'❌ 跨页面 prompt 一致性:{len(issues)} 处问题')
        for ln in issues:
            print(ln)
        return 1
    print('✅ 跨页面 prompt 一致性 pass(home_dashboard + help_center 与 _triggers SoT 字面一致)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
