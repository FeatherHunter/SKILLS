#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_photo_log_wizard.py — 记身材照 wizard HTML 渲染器(v1.0)

对应 SKILL.md 唤醒词:记身材照

数据源:无(纯配置型,wizard 不需要查 DB,用户填好后生成 prompt)
用法:
    python scripts/render_body_photo_log_wizard.py
"""

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

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    inject_data = f'<script>window.__DATA__ = {json.dumps(payload, ensure_ascii=False)};</script>'
    html = template.replace('<!--INJECT-DATA-->', inject_data)

    output_path.write_text(html, encoding='utf-8')
    return output_path


def main():
    p = argparse.ArgumentParser(description='渲染记身材照 wizard HTML')
    p.add_argument('--output', help='输出文件路径')
    args = p.parse_args()

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, 'body_photo_log_wizard')
    result = render(out_path)
    print(f"✓ 已生成: {result}")


if __name__ == '__main__':
    main()