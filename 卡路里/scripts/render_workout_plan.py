#!/usr/bin/env python3
"""健身计划 HTML 渲染器（2026-07-23 重构：模板+数据注入）

职责定位：
- 本 HTML = 训练前看今天练什么（"今天该做哪些动作、几组、几kg"）
- 训练复盘 = 走独立 CLI：`/卡路里 复盘今日`，由 exercise_review 动态算
- 本 HTML 不嵌入任何复盘数据（避免写死假数据，如完成率 0%）
- include_review 默认 False；要开复盘 section 必须显式传 --review

Phase C 重构要点：
- 原 340 行单文件 → 拆为 模板（templates/workout_plan_view.html）+ 渲染器（本文件）
- 渲染器只做：读数据 → 序列化 → 注入 → 输出
- DOM 渲染交给 JS（CSS / JS / HTML 骨架都在稳定模板里）
- 占位符唯一：<!--INJECT-DATA--> 恰好 1 次（注入器校验）
"""
import argparse
import json
import sys
from datetime import date
from itertools import groupby
from pathlib import Path

from db import find_db_path, get_db, init_db

SKILL_DIR = Path(__file__).resolve().parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'workout_plan_view.html'


def _get_db():
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


def _query_plan(conn):
    """读 plan_config + plans 原始行，返回结构化 data dict"""
    c = conn.cursor()

    # config
    c.execute('SELECT title, version, description, total_weeks, start_date FROM workout_plan_config')
    cfg_row = c.fetchone()
    if not cfg_row:
        return None

    config = {
        'title': cfg_row[0] or '健身计划',
        'version': cfg_row[1] or '',
        'description': cfg_row[2] or '',
        'total_weeks': cfg_row[3],
        'start_date': cfg_row[4] or '',
    }

    # plans 行
    c.execute('''
        SELECT week_number, day_of_week, session_index, session_label,
               time_start, time_end, is_rest_day, total_sets, movements
        FROM workout_plans ORDER BY week_number, day_of_week, session_index
    ''')
    rows = c.fetchall()

    # 按 week_number → day_of_week → sessions 三层结构
    weeks_map = {}
    for r in rows:
        wn, dow, si, label, ts, te, rest, total_sets, movements = r
        weeks_map.setdefault(wn, {}).setdefault(dow, []).append({
            'session_index': si,
            'session_label': label,
            'time_start': ts or '',
            'time_end': te or '',
            'is_rest_day': bool(rest),
            'total_sets': total_sets or 0,
            'movements': json.loads(movements) if movements else [],
        })

    weeks = []
    for wn in sorted(weeks_map.keys()):
        days = []
        for dow in sorted(weeks_map[wn].keys()):
            days.append({
                'day_of_week': dow,
                'day_label': ['', '周一','周二','周三','周四','周五','周六','周日'][dow],
                'sessions': weeks_map[wn][dow],
            })
        weeks.append({
            'week_number': wn,
            'days': days,
        })

    return {
        'config': config,
        'weeks': weeks,
        'review': None,  # 占位，render() 会填充
    }


def _build_review_data(conn) -> dict:
    """可选：拉今日复盘数据填充 review section"""
    try:
        from analysis.exercise import exercise_review
        today_str = date.today().strftime('%Y-%m-%d')
        raw = exercise_review(today_str, today_str, silent=True)
        if not raw:
            return {'today': None}
        today_review = raw.get(today_str) or next(iter(raw.values()), None)
        if not today_review:
            return {'today': None}
        return {
            'today': {
                'date': today_review.get('date') or today_str,
                'completion_rate': today_review.get('completion_rate'),
                'sessions': today_review.get('sessions') or [],
                'plan_total_sets': today_review.get('plan_total_sets', 0),
                'actual_total_sets': today_review.get('actual_total_sets', 0),
                'anomalies': today_review.get('anomalies') or [],
                'note': today_review.get('note'),
            }
        }
    except Exception as e:
        print(f"⚠️ 复盘 section 渲染失败: {e}", file=sys.stderr)
        return {'today': None}


def _render_html(data: dict) -> str:
    """读模板 + 注入数据"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')

    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(
            f"模板占位符数量异常: 期望 1 个,实际 {template.count(placeholder)} 个\n"
            f"路径: {TEMPLATE_PATH}"
        )

    payload_obj = {
        'status': 'ok',
        'data': data,
        'message': '健身计划 HTML 已生成',
    }

    # 转义 </ 防止提前闭合 script 标签
    payload = json.dumps(payload_obj, ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def render(output_path=None, target_week=None, include_review=False):
    """主渲染函数"""
    conn = _get_db()

    try:
        data = _query_plan(conn)
    finally:
        conn.close()

    if not data:
        return "尚未制定健身计划。"

    # 可选：填充复盘数据
    if include_review:
        conn2 = _get_db()
        try:
            data['review'] = _build_review_data(conn2)
        finally:
            conn2.close()
    else:
        data['review'] = {'today': None}

    # 渲染（如果指定 target_week，可以裁剪 weeks，但暂保持原行为：渲染全部）
    html = _render_html(data)

    # 输出
    if output_path:
        Path(output_path).write_text(html, encoding='utf-8')
        return output_path

    # 默认输出到技能目录
    default_path = SKILL_DIR / '健身计划.html'
    default_path.write_text(html, encoding='utf-8')
    return str(default_path)


def main():
    p = argparse.ArgumentParser(
        description='渲染健身计划 HTML（模板+数据注入 · Phase C 重构）'
    )
    p.add_argument('-o', '--output', help='输出文件路径')
    p.add_argument('-w', '--week', type=int, help='聚焦第几周')
    p.add_argument('--review', action='store_true',
                   help='打开复盘 section（默认关闭。复盘请用 `/卡路里 复盘今日` CLI）')
    args = p.parse_args()

    result = render(args.output, args.week, include_review=args.review)
    if isinstance(result, str) and not args.output:
        print(result)
    elif args.output:
        print(f'→ {result}')


if __name__ == '__main__':
    main()