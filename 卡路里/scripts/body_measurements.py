"""body_measurements CLI(V1.0 §02 第 ④ 接口层)

4 子命令: add / list / delete / trend
V1.0 §02 第 ⑧ 反模式消除: --as-dict 返回 {status, data, message}
V1.0 §02 第 ① 数据层: 13 围度列(chest/waist/abdomen/hip/thigh×2/calf×2/arm×2/forearm×2/shoulder)
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
from validators import validate_measurement_input, MEASUREMENT_FIELDS, _caliper_cli_name

METRIC_CLI = {_caliper_cli_name(f): f for f in MEASUREMENT_FIELDS}


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
    validate_measurement_input(args)
    c = _get_conn()
    try:
        cur = c.cursor()
        cur.execute(f"""
            INSERT INTO body_measurements (
                date, {', '.join(MEASUREMENT_FIELDS)}, note
            ) VALUES ({', '.join(['?'] * (2 + len(MEASUREMENT_FIELDS)))})
        """, (
            args.date,
            *(getattr(args, f) for f in MEASUREMENT_FIELDS),
            args.note,
        ))
        c.commit()
        rid = cur.lastrowid
        filled = [f for f in MEASUREMENT_FIELDS if getattr(args, f) is not None]
        return {'status': 'ok', 'data': {'id': rid},
                'message': f'已记录 body_measurements #{rid}: {args.date} {len(filled)} 个围度'}
    finally:
        c.close()


def cmd_list(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        params = []
        sql = "SELECT id, date FROM body_measurements WHERE is_deprecated = 0"
        date_from = getattr(args, 'date_from', None)
        date_to = getattr(args, 'date_to', None)
        if date_from and date_to:
            sql += " AND date >= ? AND date <= ?"
            params.extend([date_from, date_to])
        elif getattr(args, 'days', None):
            since = (date.today() - timedelta(days=args.days)).isoformat()
            sql += " AND date >= ?"
            params.append(since)
        sql += " ORDER BY date DESC, id DESC"
        cur.execute(sql, params)
        rows = [dict(zip(['id', 'date'], r)) for r in cur.fetchall()]
        return {'status': 'ok', 'data': rows,
                'message': f'共 {len(rows)} 条 body_measurements'}
    finally:
        c.close()


def cmd_delete(args):
    c = _get_conn()
    try:
        cur = c.cursor()
        cur.execute('UPDATE body_measurements SET is_deprecated=1, updated_at=CURRENT_TIMESTAMP WHERE id=?', (args.id,))
        c.commit()
        if cur.rowcount == 0:
            return {'status': 'fail', 'data': None, 'message': f'id={args.id} 不存在'}
        return {'status': 'ok', 'data': {'id': args.id}, 'message': f'已软删除 body_measurements #{args.id}'}
    finally:
        c.close()


def cmd_trend(args):
    metric_cli = args.metric
    if not metric_cli or metric_cli not in METRIC_CLI:
        return {'status': 'fail', 'data': None,
                'message': f'--metric 必填且为: {", ".join(METRIC_CLI)}'}
    col = METRIC_CLI[metric_cli]
    c = _get_conn()
    try:
        cur = c.cursor()
        since = (date.today() - timedelta(days=args.days)).isoformat()
        cur.execute(f"""
            SELECT date, AVG({col}) AS avg_val, COUNT(*) AS n
            FROM body_measurements
            WHERE is_deprecated = 0 AND date >= ? AND {col} IS NOT NULL
            GROUP BY date ORDER BY date ASC
        """, (since,))
        rows = [dict(zip(['date', 'avg_val', 'n'], r)) for r in cur.fetchall()]
        return {'status': 'ok', 'data': rows,
                'message': f'共 {len(rows)} 天 {col} 趋势'}
    finally:
        c.close()


def build_parser():
    p = argparse.ArgumentParser(description='body_measurements CLI')
    p.add_argument('--as-dict', action='store_true', help='输出 JSON (V1.0 第 ⑧ 反模式消除)')
    sub = p.add_subparsers(dest='cmd', required=False)

    pa = sub.add_parser('add', help='记录围度')
    pa.add_argument('--date', required=True)
    for cli, attr in METRIC_CLI.items():
        pa.add_argument(f'--{cli}', dest=attr, type=float)
    pa.add_argument('--note', default='')
    pa.set_defaults(func=cmd_add)

    pl = sub.add_parser('list', help='查询围度记录')
    pl.add_argument('--days', type=int, default=30)
    pl.add_argument('--date-from', dest='date_from')
    pl.add_argument('--date-to', dest='date_to')
    pl.set_defaults(func=cmd_list)

    pd = sub.add_parser('delete', help='软删除围度记录')
    pd.add_argument('--id', type=int, required=True)
    pd.set_defaults(func=cmd_delete)

    pt = sub.add_parser('trend', help='围度趋势')
    pt.add_argument('--metric', choices=list(METRIC_CLI.keys()))
    pt.add_argument('--days', type=int, default=30)
    pt.set_defaults(func=cmd_trend)
    return p


_ADD_FLAGS = {'--date'} | {f'--{cli}' for cli in METRIC_CLI} | {'--note'}
_LIST_FLAGS = {'--date-from', '--date-to'}
_DELETE_FLAGS = {'--id'}
_TREND_FLAGS = {'--metric', '--days'}


def _infer_subcommand(argv):
    flags = {a for a in argv if a.startswith('--')}
    if flags & _ADD_FLAGS:
        return 'add'
    if flags & _DELETE_FLAGS:
        return 'delete'
    if flags & _LIST_FLAGS:
        return 'list'
    if flags & _TREND_FLAGS:
        return 'trend'
    return None


def parse_args(argv=None):
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    subcmds = {'add', 'list', 'delete', 'trend'}
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
    global DB_PATH
    DB_PATH = real_db
    result = args.func(args)
    _emit(result, args.as_dict)


if __name__ == '__main__':
    main()