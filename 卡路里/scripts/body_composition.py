"""body_composition CLI(V1.0 §02 第 ④ 接口层)

5 子命令: add / list / delete / trend / compare(2026-08-02 · ticket #9 对比体脂)
V1.0 §02 第 ⑧ 反模式消除: source 用 source_constants 常量
V1.0 §02 第 ⑧ 反模式消除: --as-dict 返回 {status, data, message}
"""
import argparse
import json
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DB_PATH = SKILL_DIR / 'calorie_data.db'

sys.path.insert(0, str(SKILL_DIR))
from db import find_db_path, init_db as _init_db
from source_constants import SOURCE_CHOICES, SOURCE_HOME_CALIPER
from validators import validate_composition_input


def _get_conn():
    p = DB_PATH if isinstance(DB_PATH, Path) else Path(DB_PATH)
    if not p.exists():
        _init_db(p)
    return sqlite3.connect(str(p))


def _emit(result, as_dict):
    if as_dict:
        print(json.dumps(result, ensure_ascii=False))
    else:
        if result['status'] == 'ok':
            print(f"✓ {result['message']}")
        else:
            print(f"✗ {result['message']}", file=sys.stderr)
            sys.exit(1)


def cmd_add(args):
    validate_composition_input(args)
    c = _get_conn()
    try:
        cur = c.cursor()
        cur.execute("""
            INSERT INTO body_composition (
                date, source, age, sex,
                caliper_chest_mm, caliper_abdominal_mm, caliper_thigh_mm, caliper_tricep_mm,
                caliper_subscapular_mm, caliper_suprailiac_mm, caliper_midaxillary_mm,
                body_fat_pct, calculated_at, note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            args.date, args.source, args.age, args.sex,
            args.caliper_chest_mm, args.caliper_abdominal_mm, args.caliper_thigh_mm,
            args.caliper_tricep_mm, args.caliper_subscapular_mm, args.caliper_suprailiac_mm,
            args.caliper_midaxillary_mm,
            args.body_fat_pct, args.calculated_at, args.note,
        ))
        c.commit()
        rid = cur.lastrowid
        return {'status': 'ok', 'data': {'id': rid},
                'message': f'已记录 body_composition #{rid}: {args.date} 体脂率 {args.body_fat_pct}%'}
    finally:
        c.close()


def cmd_list(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        params = []
        sql = "SELECT id, date, source, body_fat_pct, note FROM body_composition WHERE is_deprecated = 0"
        date_from = getattr(args, 'date_from', None)
        date_to = getattr(args, 'date_to', None)
        src = getattr(args, 'source', None)
        if src:
            sql += " AND source = ?"
            params.append(src)
        if date_from and date_to:
            sql += " AND date >= ? AND date <= ?"
            params.extend([date_from, date_to])
        elif getattr(args, 'days', None):
            since = (date.today() - timedelta(days=args.days)).isoformat()
            sql += " AND date >= ?"
            params.append(since)
        sql += " ORDER BY date DESC, id DESC"
        limit = getattr(args, 'limit', None)
        if limit:
            sql += " LIMIT ?"
            params.append(limit)
        cur.execute(sql, params)
        rows = [dict(zip(['id', 'date', 'source', 'body_fat_pct', 'note'], r)) for r in cur.fetchall()]
        return {'status': 'ok', 'data': rows,
                'message': f'共 {len(rows)} 条 body_composition' + (f' (source={src})' if src else '')}
    finally:
        c.close()


def cmd_delete(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        cur.execute('UPDATE body_composition SET is_deprecated=1, updated_at=CURRENT_TIMESTAMP WHERE id=?', (args.id,))
        c.commit()
        if cur.rowcount == 0:
            return {'status': 'fail', 'data': None, 'message': f'id={args.id} 不存在'}
        return {'status': 'ok', 'data': {'id': args.id}, 'message': f'已软删除 body_composition #{args.id}'}
    finally:
        c.close()


def _latest_source(c):
    """最近一次测量使用的 source(单来源趋势默认值)"""
    row = c.execute("""
        SELECT source FROM body_composition
        WHERE is_deprecated = 0
        ORDER BY date DESC, id DESC LIMIT 1
    """).fetchone()
    return row[0] if row else None


def cmd_trend(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        src = getattr(args, 'source', None)
        if not src:
            src = _latest_source(c) or SOURCE_HOME_CALIPER
        since = (date.today() - timedelta(days=args.days)).isoformat()
        cur.execute("""
            SELECT date, AVG(body_fat_pct) AS avg_pct, COUNT(*) AS n
            FROM body_composition
            WHERE is_deprecated = 0 AND date >= ? AND source = ?
            GROUP BY date ORDER BY date ASC
        """, (since, src))
        rows = [dict(zip(['date', 'avg_pct', 'n'], r)) for r in cur.fetchall()]
        return {'status': 'ok', 'data': rows,
                'message': f'共 {len(rows)} 天体脂率趋势 (source={src})'}
    finally:
        c.close()


def cmd_compare(args):
    """对比两段时间的体脂:各自均值/最低/记录数 + Δ + 变化率(注明同来源)"""
    c = _get_conn()
    try:
        cur = c.cursor()
        src = getattr(args, 'source', None)
        def _period(start, end):
            params = [start, end]
            sql = """
                SELECT AVG(body_fat_pct) AS avg_pct, MIN(body_fat_pct) AS min_pct,
                       COUNT(*) AS n
                FROM body_composition
                WHERE is_deprecated = 0 AND date >= ? AND date <= ?
            """
            if src:
                sql += " AND source = ?"
                params.append(src)
            r = cur.execute(sql, params).fetchone()
            return {'avg_pct': r[0], 'min_pct': r[1], 'n': r[2]}
        p1 = _period(args.start1, args.end1)
        p2 = _period(args.start2, args.end2)
        delta = None
        pct_change = None
        if p1['avg_pct'] is not None and p2['avg_pct'] is not None:
            delta = round(p2['avg_pct'] - p1['avg_pct'], 2)
            if p1['avg_pct']:
                pct_change = round((p2['avg_pct'] - p1['avg_pct']) / p1['avg_pct'] * 100, 2)
        return {'status': 'ok', 'data': {
            'period1': p1, 'period2': p2,
            'delta': delta, 'pct_change': pct_change,
            'source': src or 'all',
            'same_source_note': '对比需同来源才有意义' if not src else f'同来源 {src} 对比',
        }, 'message': '对比完成'}
    finally:
        c.close()


def build_parser():
    p = argparse.ArgumentParser(description='body_composition CLI')
    p.add_argument('--as-dict', action='store_true', help='输出 JSON (V1.0 第 ⑧ 反模式消除)')
    sub = p.add_subparsers(dest='cmd', required=False)

    pa = sub.add_parser('add', help='记录体脂钳测/外部测量')
    pa.add_argument('--date', required=True)
    pa.add_argument('--source', required=True, choices=SOURCE_CHOICES)
    pa.add_argument('--age', type=int)
    pa.add_argument('--sex', choices=['male', 'female'])
    pa.add_argument('--caliper-chest', '--caliper-chest-mm', dest='caliper_chest_mm', type=float)
    pa.add_argument('--caliper-abdominal', '--caliper-abdominal-mm', dest='caliper_abdominal_mm', type=float)
    pa.add_argument('--caliper-thigh', '--caliper-thigh-mm', dest='caliper_thigh_mm', type=float)
    pa.add_argument('--caliper-tricep', '--caliper-tricep-mm', dest='caliper_tricep_mm', type=float)
    pa.add_argument('--caliper-subscapular', '--caliper-subscapular-mm', dest='caliper_subscapular_mm', type=float)
    pa.add_argument('--caliper-suprailiac', '--caliper-suprailiac-mm', dest='caliper_suprailiac_mm', type=float)
    pa.add_argument('--caliper-midaxillary', '--caliper-midaxillary-mm', dest='caliper_midaxillary_mm', type=float)
    pa.add_argument('--body-fat-pct', dest='body_fat_pct', type=float, required=True)
    pa.add_argument('--calculated-at', dest='calculated_at')
    pa.add_argument('--note', default='')
    pa.set_defaults(func=cmd_add)

    pl = sub.add_parser('list', help='查询体脂记录')
    pl.add_argument('--days', type=int, default=30)
    pl.add_argument('--date-from', dest='date_from')
    pl.add_argument('--date-to', dest='date_to')
    pl.add_argument('--source', choices=SOURCE_CHOICES, help='按来源筛选')
    pl.add_argument('--limit', type=int, help='最多返回条数')
    pl.set_defaults(func=cmd_list)

    pd = sub.add_parser('delete', help='软删除体脂记录')
    pd.add_argument('--id', type=int, required=True)
    pd.set_defaults(func=cmd_delete)

    pt = sub.add_parser('trend', help='体脂趋势')
    pt.add_argument('--source', choices=SOURCE_CHOICES, help='默认=最近使用来源')
    pt.add_argument('--days', type=int, default=30)
    pt.set_defaults(func=cmd_trend)

    pc = sub.add_parser('compare', help='对比两段时间体脂(同来源才有意义)')
    pc.add_argument('--start1', required=True)
    pc.add_argument('--end1', required=True)
    pc.add_argument('--start2', required=True)
    pc.add_argument('--end2', required=True)
    pc.add_argument('--source', choices=SOURCE_CHOICES, help='限定同来源(默认全部)')
    pc.set_defaults(func=cmd_compare)
    return p


_ADD_FLAGS = {'--date', '--source', '--caliper-chest', '--caliper-chest-mm',
              '--caliper-abdominal', '--caliper-abdominal-mm',
              '--caliper-thigh', '--caliper-thigh-mm',
              '--caliper-tricep', '--caliper-tricep-mm',
              '--caliper-subscapular', '--caliper-subscapular-mm',
              '--caliper-suprailiac', '--caliper-suprailiac-mm',
              '--caliper-midaxillary', '--caliper-midaxillary-mm',
              '--body-fat-pct', '--calculated-at', '--age', '--sex'}
_LIST_FLAGS = {'--date-from', '--date-to', '--limit'}
_DELETE_FLAGS = {'--id'}
_TREND_FLAGS = {'--days'}
_COMPARE_FLAGS = {'--start1', '--end1', '--start2', '--end2'}


def _infer_subcommand(argv):
    flags = {a for a in argv if a.startswith('--')}
    if flags & _ADD_FLAGS:
        return 'add'
    if flags & _DELETE_FLAGS:
        return 'delete'
    if flags & _COMPARE_FLAGS:
        return 'compare'
    if flags & _LIST_FLAGS:
        return 'list'
    if flags & _TREND_FLAGS:
        return 'trend'
    return None


def parse_args(argv=None):
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    subcmds = {'add', 'list', 'delete', 'trend', 'compare'}
    as_dict = '--as-dict' in argv
    argv = [a for a in argv if a != '--as-dict']
    if argv and argv[0] not in subcmds:
        inferred = _infer_subcommand(argv)
        if inferred:
            argv = [inferred] + list(argv)
    args = parser.parse_args(argv)
    args.as_dict = as_dict or args.as_dict
    return args


def main():
    parser = build_parser()
    args = parse_args()
    real_db = find_db_path(SKILL_DIR, 'calorie_data.db')
    if not real_db.exists():
        _init_db(real_db)
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    # Override DB_PATH so _get_conn uses the real DB
    global DB_PATH
    DB_PATH = real_db
    result = args.func(args)
    _emit(result, args.as_dict)


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    main()