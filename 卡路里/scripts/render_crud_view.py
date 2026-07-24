#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_crud_view.py — 通用状态查看 HTML 渲染器(报告型)

对应 SKILL.md 唤醒词(2 个):
  - 查档案   → 显示 user_profile 字段
  - 查定时复盘 → 显示 mavis cron 任务配置
对应模板: templates/crud_view.html
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'crud_view.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


def _load_data(input_path):
    raw = json.loads(Path(input_path).read_text(encoding='utf-8'))
    if raw.get('status') != 'ok':
        raise ValueError('数据状态非 ok')
    return raw


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染状态查看 HTML(查档案/查定时复盘)')
    p.add_argument('--mock', required=True, help='mock JSON')
    p.add_argument('--output')
    args = p.parse_args()
    try:
        data = _load_data(args.mock)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, 'crud_view')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    d = data['data']
    print(f'✅ {out_path}')
    print(f'   实体: {d["entity"]["type"]} | {d["entity"]["title"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
