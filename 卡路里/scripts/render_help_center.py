#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_help_center.py — 卡路里唤醒词速查台 HTML 渲染器

对应 SKILL.md 唤醒词: 卡路里HELP

设计(v2.4.10 · 2026-07-26):
- 数据源:scripts/_triggers.py(80 唤醒词 × ~2 用法 = 109 prompt)
- 3 层折叠 + sticky 类别导航 + 搜索 + 一键复制全部
- 占位符唯一:<!--INJECT-DATA--> 恰好 1 次
- 结果型 · 原则 10 出口设计:每条 prompt 1 个 [📋 复制 prompt] 按钮

用法:
    python scripts/render_help_center.py                  # 默认 → calorie_html/
    python scripts/render_help_center.py --output <path> # 显式覆盖
"""
import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'help_center.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa: E402
from _triggers import CATEGORIES, TRIGGERS, get_summary  # noqa: E402


def build_data():
    """组装速查台数据契约

    returns:
        {
            status: 'ok',
            data: {
                summary: { total_wake_words, total_prompts, total_categories, by_category },
                categories: [ {icon, name, key}, ... ],
                triggers: [ {category, wake_word, aliases, desc, main_prompt, variants}, ... ]
            },
            message: '...'
        }
    """
    return {
        'status':  'ok',
        'data': {
            'summary':    get_summary(),
            'categories': [{'icon': ic, 'name': nm, 'key': ky} for ic, nm, ky in CATEGORIES],
            'triggers':   TRIGGERS,
        },
        'message': f'已加载 {len(TRIGGERS)} 唤醒词 / {sum(len(t.get("variants", [])) for t in TRIGGERS) + len(TRIGGERS)} prompt',
    }


def render_html(data):
    """注入数据到模板 · 4 步(手册第 7 节)"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符 <!--INJECT-DATA-->')

    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    inject  = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace('<!--INJECT-DATA-->', inject, 1)


def main():
    p = argparse.ArgumentParser(description='渲染卡路里唤醒词速查台 HTML')
    p.add_argument('--output', help='输出文件路径(默认走 html_path 新规范)')
    args = p.parse_args()

    try:
        data  = build_data()
        html  = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '卡路里_HELP')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   类别: {sm["total_categories"]} · 唤醒词: {sm["total_wake_words"]} · prompt: {sm["total_prompts"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
