#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_body_measurements_wizard.py — 记围度 wizard HTML 渲染器(v2.4.2)

对应 SKILL.md 唤醒词:记围度 / 查围度 / 查围度趋势

数据源:body_measurements 表最近 1 条(注入 wizard 顶部"上次"摘要,
不自动填 input — 避免混淆"新/旧"值,用户主动点"复制上次"按钮)
用法:
    python scripts/render_body_measurements_wizard.py
    python scripts/render_body_measurements_wizard.py --output /path/out.html
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
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'body_measurements_wizard.html'

sys.path.insert(0, str(SKILL_DIR))
from db import find_db_path


def fetch_recent_measurements(limit: int = 1) -> list:
    """查 body_measurements 最近 N 条(不软删除的)"""
    p = find_db_path(SKILL_DIR, 'calorie_data.db')
    if not p.exists():
        return []
    conn = sqlite3.connect(str(p))
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, date, chest_cm, waist_cm, abdomen_cm, hip_cm,
                   left_thigh_cm, right_thigh_cm, left_calf_cm, right_calf_cm,
                   left_arm_cm, right_arm_cm, left_forearm_cm, right_forearm_cm,
                   shoulder_cm, note
            FROM body_measurements
            WHERE is_deprecated = 0
            ORDER BY date DESC, id DESC
            LIMIT ?
        """, (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()


def render(output_path: Path, prefill: dict = None) -> Path:
    """prefill: dict of 13 围度 field → value(用户已告诉 AI 的值)

    AI 调用时,如果有用户提供的围度值,传 prefill 进来,
    wizard input 会自动预填,用户打开即可 verify + 复制 prompt。
    """
    recent = fetch_recent_measurements(1)
    recent_dict = recent[0] if recent else {}
    prefill = prefill or {}

    payload = {
        "status": "ok",
        "data": {
            "fetched_at": datetime.now().isoformat(timespec='seconds'),
            "current_tag": "围度测",
            "recent_date": recent_dict.get("date"),
            "recent_chest_cm": recent_dict.get("chest_cm"),
            "recent_waist_cm": recent_dict.get("waist_cm"),
            "recent_abdomen_cm": recent_dict.get("abdomen_cm"),
            "recent_hip_cm": recent_dict.get("hip_cm"),
            "recent_left_thigh_cm": recent_dict.get("left_thigh_cm"),
            "recent_right_thigh_cm": recent_dict.get("right_thigh_cm"),
            "recent_left_calf_cm": recent_dict.get("left_calf_cm"),
            "recent_right_calf_cm": recent_dict.get("right_calf_cm"),
            "recent_left_arm_cm": recent_dict.get("left_arm_cm"),
            "recent_right_arm_cm": recent_dict.get("right_arm_cm"),
            "recent_left_forearm_cm": recent_dict.get("left_forearm_cm"),
            "recent_right_forearm_cm": recent_dict.get("right_forearm_cm"),
            "recent_shoulder_cm": recent_dict.get("shoulder_cm"),
            "recent_note": recent_dict.get("note"),
            # 用户已告诉 AI 的值(直接渲染为 input value)
            "prefill_date": prefill.get("date"),
            "prefill_chest_cm": prefill.get("chest_cm"),
            "prefill_waist_cm": prefill.get("waist_cm"),
            "prefill_abdomen_cm": prefill.get("abdomen_cm"),
            "prefill_hip_cm": prefill.get("hip_cm"),
            "prefill_shoulder_cm": prefill.get("shoulder_cm"),
            "prefill_left_thigh_cm": prefill.get("left_thigh_cm"),
            "prefill_right_thigh_cm": prefill.get("right_thigh_cm"),
            "prefill_left_calf_cm": prefill.get("left_calf_cm"),
            "prefill_right_calf_cm": prefill.get("right_calf_cm"),
            "prefill_left_arm_cm": prefill.get("left_arm_cm"),
            "prefill_right_arm_cm": prefill.get("right_arm_cm"),
            "prefill_left_forearm_cm": prefill.get("left_forearm_cm"),
            "prefill_right_forearm_cm": prefill.get("right_forearm_cm"),
            "prefill_note": prefill.get("note"),
        },
        "message": "记围度 wizard — 填好参数后复制 prompt 给 AI",
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
    p = argparse.ArgumentParser(description='渲染记围度 wizard HTML')
    p.add_argument('--output', help='输出文件路径')
    # 预填 args(场景 2:用户已给维度数字,AI 帮预填到 input)
    p.add_argument('--date', help='预填日期(YYYY-MM-DD)')
    p.add_argument('--tag', help='预填 tag')
    for f in ['chest_cm','waist_cm','abdomen_cm','hip_cm','shoulder_cm',
              'left_thigh_cm','right_thigh_cm','left_calf_cm','right_calf_cm',
              'left_arm_cm','right_arm_cm','left_forearm_cm','right_forearm_cm']:
        p.add_argument(f'--{f.replace("_","-")}', dest=f, type=float,
                       help=f'预填 {f}(cm)')
    p.add_argument('--note', help='预填 note')
    args = p.parse_args()

    prefill = {}
    for f in ['date','tag','chest_cm','waist_cm','abdomen_cm','hip_cm','shoulder_cm',
              'left_thigh_cm','right_thigh_cm','left_calf_cm','right_calf_cm',
              'left_arm_cm','right_arm_cm','left_forearm_cm','right_forearm_cm','note']:
        v = getattr(args, f, None)
        if v is not None:
            prefill[f] = v

    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '围度向导')
    result = render(out_path, prefill=prefill if prefill else None)
    print(f"✓ 已生成: {result}")
    if prefill:
        print(f"  📋 已预填 {len(prefill)} 个字段(用户已告诉 AI 的值)")
    emit_send_protocol(result)


if __name__ == '__main__':
    main()