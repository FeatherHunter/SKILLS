#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_cron_setup.py — 开启/关闭定时复盘 HTML 渲染器(配置型)

对应 SKILL.md 唤醒词(2 个):
  - 开启定时复盘 → 模式:create
  - 关闭定时复盘 → 模式:delete
对应模板: templates/cron_setup.html
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '定时复盘设置'
import argparse, json, sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'cron_setup.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError('数据状态非 ok')
    return raw


def render_html(data):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def main():
    p = argparse.ArgumentParser(description='渲染定时复盘 HTML(开启/关闭)')
    p.add_argument('--mock', required=True)
    p.add_argument('--output')
    args = p.parse_args()
    try:
        data = _load_data(args.mock)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '定时任务设置')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    print(f'✅ {out_path}')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
