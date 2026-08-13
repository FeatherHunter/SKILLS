#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_photo_log_wizard.py — 记身材照 wizard HTML 渲染器(v1.0)

对应 SKILL.md 唤醒词:记身材照

数据源:无(纯配置型,wizard 不需要查 DB,用户填好后生成 prompt)
用法:
    python scripts/render_body_photo_log_wizard.py
"""

from _base_render import render_template, write_html  # noqa: E402

import argparse
import json
from datetime import datetime
from pathlib import Path

from html_paths import html_path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_photo_log_wizard.html'


def render(output_path: Path) -> Path:
    payload = {
        "status": "ok",
        "data": {
            "fetched_at": datetime.now().isoformat(timespec='seconds'),
        },
        "message": "记身材照 wizard",
    }

    html = render_template(TEMPLATE_PATH, payload, "记身材照")

    write_html(html, output_path)
    return output_path


def emit_send_protocol(output_path: Path):
    """stdout 末行:V1.3 §HTML 交付协议 - Agent 必须 send 给用户"""
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={output_path.absolute()}")


def main():
    p = argparse.ArgumentParser(description='渲染记身材照 wizard HTML')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '身材照记录向导')
    result = render(out_path)
    print(f"✓ 已生成: {result}")
    emit_send_protocol(result)


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    main()