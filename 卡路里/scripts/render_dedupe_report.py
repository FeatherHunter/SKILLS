#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_dedupe_report.py — 看食品库(去重) HTML 渲染器(结果型)

对应 SKILL.md 唤醒词: 看食品库（去重）
对应模板: templates/dedupe_report.html

呈现数据: 重复组列表/重复条数/处理建议
"""
import argparse, json, sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'dedupe_report.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_path  # noqa


def build_data(chain=None):
    from batch_import import get_db_path, connect_db
    db_path = get_db_path()
    conn = connect_db(db_path)
    cur = conn.cursor()
    cur.execute('''
        SELECT product_name, brand, COUNT(*) as cnt, GROUP_CONCAT(id) as ids
        FROM nutrition_products
        WHERE is_deprecated = 0
        GROUP BY product_name, brand
        HAVING cnt > 1
        ORDER BY cnt DESC
    ''')
    dups = cur.fetchall()
    total_products = cur.execute('SELECT COUNT(*) FROM nutrition_products WHERE is_deprecated = 0').fetchone()[0]
    conn.close()

    groups = []
    extra_rows = 0
    for row in dups:
        ids = [int(x) for x in row['ids'].split(',')]
        groups.append({'name': row['product_name'], 'brand': row['brand'] or '',
                       'count': row['cnt'], 'ids': ids})
        extra_rows += row['cnt'] - 1

    return {
        'status': 'ok',
        'data': {
            'summary': {'groups': len(groups), 'duplicate_rows': extra_rows,
                        'total_products': total_products, 'clean': len(groups) == 0},
            'items': groups,
            'meta': {'today': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'chain': chain},
        },
        'message': f'去重检查: {len(groups)} 组重复',
    }


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def main():
    p = argparse.ArgumentParser(description='渲染食品库去重报告 HTML(结果型)')
    p.add_argument('--output')
    p.add_argument('--chain', help='AI 思考链注入(meta.chain,不进 UI;复制日志可带出 · R3)')
    args = p.parse_args()
    try:
        data = build_data(getattr(args, 'chain', None))
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else html_path(SKILL_DIR, '食品库去重')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    sm = data['data']['summary']
    print(f'✅ {out_path}')
    print(f'   重复组 {sm["groups"]} | 冗余行 {sm["duplicate_rows"]} | 库总 {sm["total_products"]}')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
