#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_composition_wizard.py — 记体脂 wizard HTML 渲染器(v2.4.2)

对应 SKILL.md 唤醒词:记体脂 / 查体脂 / 查体脂趋势

数据源:body_composition 表最近 1 条(注入 wizard 顶部"上次"摘要,
不自动填 input — 避免混淆"新/旧"值,用户主动点"复制上次"按钮)
用法:
    python scripts/render_body_composition_wizard.py
    python scripts/render_body_composition_wizard.py --output /path/out.html
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from html_paths import html_path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_composition_wizard.html'
DB_PATH = SKILL_DIR / 'calorie_data.db'

sys.path.insert(0, str(SKILL_DIR))
from db import find_db_path


def fetch_recent_composition(limit: int = 1) -> list:
    """查 body_composition 最近 N 条(不软删除的)"""
    p = find_db_path(SKILL_DIR, 'calorie_data.db')
    if not p.exists():
        return []
    conn = sqlite3.connect(str(p))
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, date, source, body_fat_pct, caliper_chest_mm,
                   caliper_abdominal_mm, caliper_thigh_mm, caliper_tricep_mm,
                   caliper_subscapular_mm, caliper_suprailiac_mm, caliper_midaxillary_mm,
                   age, sex, note
            FROM body_composition
            WHERE is_deprecated = 0
            ORDER BY date DESC, id DESC
            LIMIT ?
        """, (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


def render(output_path: Path, prefill: dict = None) -> Path:
    """prefill: dict of 7 caliper + age + sex + body_fat_pct + source + note(用户已告诉 AI 的值)"""
    recent = fetch_recent_composition(1)
    recent_dict = recent[0] if recent else {}
    prefill = prefill or {}

    payload = {
        "status": "ok",
        "data": {
            "fetched_at": datetime.now().isoformat(timespec='seconds'),
            "current_tag": "体脂钳测",
            "recent_date": recent_dict.get("date"),
            "recent_body_fat_pct": recent_dict.get("body_fat_pct"),
            "recent_source": recent_dict.get("source"),
            "recent_caliper_chest_mm": recent_dict.get("caliper_chest_mm"),
            "recent_caliper_abdominal_mm": recent_dict.get("caliper_abdominal_mm"),
            "recent_caliper_thigh_mm": recent_dict.get("caliper_thigh_mm"),
            "recent_caliper_tricep_mm": recent_dict.get("caliper_tricep_mm"),
            "recent_caliper_subscapular_mm": recent_dict.get("caliper_subscapular_mm"),
            "recent_caliper_suprailiac_mm": recent_dict.get("caliper_suprailiac_mm"),
            "recent_caliper_midaxillary_mm": recent_dict.get("caliper_midaxillary_mm"),
            "recent_age": recent_dict.get("age"),
            "recent_sex": recent_dict.get("sex"),
            "recent_note": recent_dict.get("note"),
            # 用户已告诉 AI 的值(预填)
            "prefill_date": prefill.get("date"),
            "prefill_source": prefill.get("source"),
            "prefill_caliper_chest_mm": prefill.get("caliper_chest_mm"),
            "prefill_caliper_abdominal_mm": prefill.get("caliper_abdominal_mm"),
            "prefill_caliper_thigh_mm": prefill.get("caliper_thigh_mm"),
            "prefill_caliper_tricep_mm": prefill.get("caliper_tricep_mm"),
            "prefill_caliper_subscapular_mm": prefill.get("caliper_subscapular_mm"),
            "prefill_caliper_suprailiac_mm": prefill.get("caliper_suprailiac_mm"),
            "prefill_caliper_midaxillary_mm": prefill.get("caliper_midaxillary_mm"),
            "prefill_body_fat_pct": prefill.get("body_fat_pct"),
            "prefill_age": prefill.get("age"),
            "prefill_sex": prefill.get("sex"),
            "prefill_note": prefill.get("note"),
        },
        "message": "记体脂 wizard — 填好参数后复制 prompt 给 AI",
    }

    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    inject_data = f'<script>window.__DATA__ = {json.dumps(payload, ensure_ascii=False)};</script>'
    html = template.replace('<!--INJECT-DATA-->', inject_data)

    output_path.write_text(html, encoding='utf-8')
    return output_path


def emit_send_protocol(output_path: Path):
    """stdout 末行:V1.3 §HTML 交付协议 - Agent 必须 send 给用户"""
    print(f"⚠️ ACTION=SEND_TO_USER | HTML={output_path.absolute()}")


def main():
    p = argparse.ArgumentParser(description='渲染记体脂 wizard HTML')
    p.add_argument('--output', help='输出文件路径')
    # 预填 args(场景 2:用户已给体脂数字,AI 帮预填)
    p.add_argument('--date', help='预填日期(YYYY-MM-DD)')
    p.add_argument('--source', help='预填 source(家测/医院测)')
    for f in ['caliper_chest_mm','caliper_abdominal_mm','caliper_thigh_mm',
              'caliper_tricep_mm','caliper_subscapular_mm','caliper_suprailiac_mm',
              'caliper_midaxillary_mm']:
        p.add_argument(f'--{f.replace("_","-")}', dest=f, type=float,
                       help=f'预填 {f}(mm)')
    p.add_argument('--body-fat-pct', dest='body_fat_pct', type=float, help='预填体脂率(医院测时直接报)')
    p.add_argument('--age', type=int, help='预填年龄')
    p.add_argument('--sex', choices=['male','female'], help='预填性别')
    p.add_argument('--note', help='预填 note')
    args = p.parse_args()

    prefill = {}
    for f in ['date','source','caliper_chest_mm','caliper_abdominal_mm',
              'caliper_thigh_mm','caliper_tricep_mm','caliper_subscapular_mm',
              'caliper_suprailiac_mm','caliper_midaxillary_mm','body_fat_pct',
              'age','sex','note']:
        v = getattr(args, f, None)
        if v is not None:
            prefill[f] = v

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '体脂向导')
    result = render(out_path, prefill=prefill if prefill else None)
    print(f"✓ 已生成: {result}")
    if prefill:
        print(f"  📋 已预填 {len(prefill)} 个字段(用户已告诉 AI 的值)")
    emit_send_protocol(result)


if __name__ == '__main__':
    main()
