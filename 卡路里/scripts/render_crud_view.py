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


def build_data(entity_type):
    '''从 DB 真实查询 entity_type 状态(无需 mock)'''
    from db import find_db_path
    import sqlite3
    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if entity_type == 'profile':
        # 真实查 user_profile + weight_log 最新一条
        cur.execute("SELECT * FROM user_profile ORDER BY id DESC LIMIT 1")
        prof = cur.fetchone()
        if not prof:
            return None
        cur.execute("SELECT date, time, weight_kg, bmi FROM weight_log ORDER BY date DESC, time DESC LIMIT 1")
        w = cur.fetchone()
        prof_d = dict(prof)
        weight_d = dict(w) if w else {}
        # BMR + TDEE
        age = prof['age'] or 30
        h = prof['height_cm'] or 175
        w_kg = weight_d.get('weight_kg', 70)
        # Mifflin-St Jeor
        bmr = round(10 * w_kg + 6.25 * h - 5 * age + 5, 0)
        tdee = round(bmr * 1.4, 0)
        bmi = weight_d.get('bmi')
        height_str = f'{h:g} cm' if h else '—'
        bmi_str = f'{bmi} (正常)' if bmi and 18.5 <= bmi <= 24 else f'{bmi} (超重)' if bmi and bmi > 24 else '—' if bmi else '—'
        weight_str = f"{w_kg} kg ({weight_d.get('date')} {weight_d.get('time', '')[:5]})" if w_kg else '—'

        return {
            'status': 'ok',
            'data': {
                'entity': {
                    'type': '用户档案 + 体重',
                    'title': '👤 查档案',
                    'subtitle': 'user_profile 基础信息 + weight_log 最新体重',
                    'section_title': '档案 + 当前体重'
                },
                'kpis': [
                    {'label':'年龄', 'value':str(age), 'extra':prof['gender'] or '—'},
                    {'label':'身高', 'value':height_str, 'extra':'BMR/TDEE 计算'},
                    {'label':'当前体重', 'value':f"{w_kg} kg" if w_kg else '—', 'extra':weight_d.get('date', '—') if w else '无记录'},
                    {'label':'当前 BMI', 'value':f'{bmi}' if bmi else '—', 'extra':bmi_str}
                ],
                'fields': [
                    {'key':'年龄(AGE)', 'value':str(age)},
                    {'key':'性别(GENDER)', 'value':prof['gender'] or '—'},
                    {'key':'身高(HEIGHT_CM)', 'value':height_str},
                    {'key':'最近体重', 'value':weight_str},
                    {'key':'最近 BMI', 'value':bmi_str},
                    {'key':'BMR(Mifflin-St Jeor)', 'value':f'{bmr:,} 卡/天'},
                    {'key':'TDEE(BMR × 1.4)', 'value':f'{tdee:,} 卡/天'},
                    {'key':'档案创建', 'value':prof['created_at'] or '—'},
                    {'key':'档案更新', 'value':prof['updated_at'] or '—'},
                    {'key':'备注', 'value':prof['note'] or '(空)'}
                ],
                'raw': {**prof_d, 'weight': weight_d} if weight_d else prof_d,
                'meta': {
                    'fetched_at': datetime.now().isoformat(timespec='seconds')[:16].replace('T', ' '),
                    'source': 'user_profile + weight_log (latest)'
                }
            },
            'message': '已生成查档案 报告'
        }
    # 后续可加 cron
    return None


def main():
    p = argparse.ArgumentParser(description='渲染状态查看 HTML(查档案/查定时复盘)')
    p.add_argument('--entity', choices=['profile','cron'], help='DB 实体类型(与 --mock 二选一)')
    p.add_argument('--mock', help='mock JSON(与 --entity 二选一)')
    p.add_argument('--output')
    args = p.parse_args()
    try:
        if args.mock:
            data = _load_data(args.mock)
        elif args.entity:
            data = build_data(args.entity)
            if not data:
                print(f'❌ DB 中没有 {args.entity} 记录', file=sys.stderr)
                return 1
        else:
            print('❌ 需要 --mock 或 --entity', file=sys.stderr)
            return 1
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
