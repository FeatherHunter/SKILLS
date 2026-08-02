#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_prompt_quality.py — 验证 prompt 由 _prompt_skeleton 包裹 + body 非空 + 无流程型描述

v2.4.11 · 2026-07-26
依据 SKILL 开发总纲 V1.0 §05 · §⚠️ 强制性规定 第 4 条 HTML-First + §HTML 交付协议。

规则:
  1. 每条 main_prompt.text 必须由 _prompt_skeleton() 包裹生成(head 必须是"加载技能...")
  2. body 必须非空(让 AI 有具体场景说明)
  3. body 内禁止出现"按 SKILL.md §X.Y"等"流程型"措辞(用户话不应指引用 SKILL.md 章节)
  4. body 内禁止出现"步骤 1 / 步骤 2"类步骤序(用户话不该是步骤列表)
  5. body 内禁止出现"告诉用户路径"等指令(违反 SKILL.md §HTML 交付协议,只给路径不算 send)
  6. body 内禁止出现"按流程" / "按命令行" / "解析 stdout"等流程型措辞

退出码:
  0 = pass
  1 = 有违反(打印违规详情)
"""
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _triggers import TRIGGERS  # noqa

BAD_PATTERNS = [
    (r'解析 stdout',          '禁止"解析 stdout"流程型指令'),
    (r'主动 send',            '禁止把 HTML 交付协议细节写在 prompt 里'),
    (r'fallback Chrome',      '禁止 fallback Chrome 细节'),
    (r'步骤\s*[1-9一二三四五]', '禁止"步骤 1/2/3" 序列描述'),
    (r'场景\s*[1-3]',         '禁止"场景 1/2/3"(写 SKILL.md 决策铁则细节)'),
    (r'决策铁则',             '禁止直接引用 SKILL.md 决策铁则让 AI 自己读'),
    (r'send_file_to_feishu', '禁止把飞书指令细节写在 prompt 里'),
    (r'按 SKILL\.md',        '禁止"按 SKILL.md ..."流程型指令'),
    (r'按命令行',             '禁止"按命令行"指令'),
    (r'按流程',               '禁止"按流程"指令'),
    (r'把 .* 路径.*?告诉用户', '禁止让 AI 把路径告诉用户(违反 HTML 交付协议)'),
    (r'user 双击',            '禁止让用户自己双击(违反 send 协议)'),
]


def check_one(label: str, text: str, errors: list, warnings: list, must_contain: list[str] | None = None):
    """校验单条 prompt

    Args:
        must_contain: 若提供,要求 text 包含其中每个关键词(ticket 14 · 记吃了 4-step flow 守护)
    """
    # 规则 1: 必须以"加载技能"开头(head)
    if not text.strip().startswith('请你加载技能'):
        errors.append(f'[{label}] head 错误: 必须以"请你加载技能..."开头')

    # 规则 2: body 非空(head + body 至少 2 段)
    # v1.0 场景格式:结果型无输入引导 = 2 段(head + body);输入型 = 3 段(head + body + 填空引导)
    # 2026-08-02 修订:阈值 3 → 2(结果型场景无输入字段是合法结构)
    parts = text.strip().split('\n\n')
    if len(parts) < 2:
        errors.append(f'[{label}] 结构错误: prompt 应有 head + body 至少 2 段')

    # 规则 3-6: 流程型措辞(关键!)
    for pat, why in BAD_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            errors.append(f'[{label}] 流程型违规 "{pat}":{why} — 匹配:{m.group()!r}')

    # 规则 7 (ticket 14): must_contain 关键词守护(若 trigger 声明了)
    if must_contain:
        for kw in must_contain:
            if kw not in text:
                errors.append(f'[{label}] 缺少必备关键词 "{kw}"(must_contain 守护)')


def main():
    errors = []
    warnings = []

    for t in TRIGGERS:
        wake = t['wake_word']
        must = t.get('must_contain')  # ticket 14 · 可选 must_contain 字段
        check_one(f'main/{wake}', t['main_prompt']['text'], errors, warnings, must_contain=must)

        for v in t.get('variants', []):
            label = v['label']
            check_one(f'v/{wake}/{label}', v['prompt'], errors, warnings, must_contain=must)

    # 输出
    n_main = len(TRIGGERS)
    n_var = sum(len(t.get('variants', [])) for t in TRIGGERS)

    if errors:
        print(f'❌ 发现 {len(errors)} 处违规(main {n_main} + variant {n_var} 检查结果):')
        for e in errors:
            print(f'  - {e}')
        sys.exit(1)
    else:
        print(f'✅ 所有 prompt 通过质量检查(main {n_main} + variant {n_var})')
        sys.exit(0)


if __name__ == '__main__':
    main()
