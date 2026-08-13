#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_source_stats.py — 看食品来源统计 HTML 渲染器(结果型)

对应 SKILL.md 唤醒词: 看食品来源统计
对应模板: templates/source_stats.html

呈现数据: 按来源分组计数 + 总数
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '看食品来源统计'
import argparse, json, sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'source_stats.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


def build_data(chain=None):
    import product_library
    rows, total = product_library.source_stats()
    items = [{'source': src or '未知', 'count': cnt} for src, cnt in rows]
    pcts = [round(cnt / total * 100, 1) if total else 0 for _, cnt in rows]
    for it, pct in zip(items, pcts):
        it['pct'] = pct
    return {
        'status': 'ok',
        'data': {
            'summary': {'total': total, 'sources': len(items)},
            'items': items,
            'meta': {'today': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'chain': chain},
        },
        'message': f'食品来源统计 {len(items)} 个来源 / {total} 条',
    }


def render_html(data):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def main():
    p = argparse.ArgumentParser(description='渲染食品来源统计 HTML(结果型)')
    p.add_argument('--output')
    p.add_argument('--chain', help='AI 思考链注入(meta.chain,不进 UI;复制日志可带出 · R3)')
    args = p.parse_args()
    try:
        data = build_data(getattr(args, 'chain', None))
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '食品来源统计')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   来源 {sm["sources"]} 个 | 总数 {sm["total"]} 条')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
