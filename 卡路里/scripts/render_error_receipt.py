#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_error_receipt.py — 失败回执 HTML 渲染器(08 规范 §6.1 三层反馈 · 2026-08-05)

用法(AI 在写库失败/补记冲突/校验不过时调用):
    python scripts/render_error_receipt.py \
        --scene-name "补记体脂" --wake-word 补记体脂 \
        --op "补记体脂 2026-07-20" \
        --reason "该日期已有体脂记录(18.5%),同日重复写入需确认覆盖" \
        --data '{"date":"2026-07-20","body_fat_pct":18.0,"existing":18.5}' \
        --suggestion "确认覆盖为最新值" --suggestion "换个日期补记" \
        --fix-prompt "请帮我覆盖 2026-07-20 的体脂记录为 18.0%" \
        --chain "1.识别→2.查冲突→3.渲染错误回执"
"""

from _base_render import render_template, write_html  # noqa: E402
COMMAND_CN = '操作失败'
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'error_receipt.html'

sys.path.insert(0, str(SKILL_DIR))
from html_paths import html_scene_path  # noqa: E402
from render_goal_common import build_meta  # noqa: E402


def build_error(args) -> dict:
    meta = build_meta(
        wake_word=args.wake_word or args.scene_name or '操作',
        source='错误回执(写库前校验/执行中失败)',
        chain=args.chain,
        extra={'scene_id': args.scene_id or 'error_receipt'},
    )
    try:
        data_text = json.dumps(json.loads(args.data), ensure_ascii=False, indent=2) if args.data else '—'
    except json.JSONDecodeError:
        data_text = args.data or '—'
    return {
        'status': 'ok',
        'data': {
            'scene_name': args.scene_name or '操作失败',
            'op': args.op or '操作未完成',
            'sub': args.sub or '',
            'reason': args.reason or '(未知原因)',
            'data_text': data_text,
            'suggestions': args.suggestion or ['修正后重试', '更换参数/目标', '联系开发者'],
            'fix_prompt': args.fix_prompt or '// 修正 prompt 未生成',
            'meta': meta,
        },
    }


def render_html(data: dict):
    return render_template(TEMPLATE_PATH, data, COMMAND_CN)


def main():
    p = argparse.ArgumentParser(description='渲染失败回执 HTML(08 §6.1)')
    p.add_argument('--scene-name', help='场景名(如:补记体脂)')
    p.add_argument('--wake-word', help='唤醒词')
    p.add_argument('--scene-id', help='scene_id(默认 error_receipt)')
    p.add_argument('--op', help='操作名(用户想干什么)')
    p.add_argument('--sub', help='副标题(可选)')
    p.add_argument('--reason', help='失败原因(人类可读)')
    p.add_argument('--data', help='关键数据(JSON 字符串或文本)')
    p.add_argument('--suggestion', action='append', help='建议下一步(可多个)')
    p.add_argument('--fix-prompt', dest='fix_prompt', help='修正 prompt(复制给 AI)')
    p.add_argument('--chain', help='AI 思考链')
    p.add_argument('--output', help='输出路径(默认 html_scene_path 规则)')
    args = p.parse_args()

    data = build_error(args)
    html = render_html(data)
    scene = args.scene_name or '操作失败'
    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, scene, 'error')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_html(html, out_path)
    print(f'❌ {scene} 失败回执已生成')
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={out_path.absolute()}")
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
