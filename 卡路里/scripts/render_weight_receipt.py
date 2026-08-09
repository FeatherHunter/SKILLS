#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_weight_receipt.py — 记体重回执 HTML 渲染器(G7 · ticket #4 扩展)

对应 SKILL.md 唤醒词:记体重 / 记体重（含备注）/ 补录体重 / 批量补录体重

设计原则(回执型 C,非过程型 B):
- 录入后立即看到大数字 + 趋势图 + 复制按钮
- 无 AI 互动(数据已写入数据库)
- Apple 风 + 趋势图 + 新点高亮

用法:
    python scripts/render_weight_receipt.py --mock tests/fixtures/mock/mock_weight_receipt.json
    python scripts/render_weight_receipt.py --live --kg 70 --note 晨起空腹 --chain "1.解析→2.写库→3.回执"
    python scripts/render_weight_receipt.py --live --kg 70 --date 2026-07-20 --chain "1.解析→2.查冲突→3.写库→4.回执"
    python scripts/render_weight_receipt.py --live-batch --input items.jsonl --chain "1.解析→2.查冲突→3.批量写库→4.回执"
"""
import argparse
import json
from html_paths import html_path, html_scene_path
import sys
from pathlib import Path
from datetime import date, timedelta

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'weight_log_receipt.html'
BATCH_TEMPLATE_PATH = SKILL_DIR / 'templates' / 'weight_batch_receipt.html'

sys.path.insert(0, str(SCRIPT_DIR))
from render_crud_view import _chain_valid, _quote_arg  # noqa: E402


def build_parser():
    p = argparse.ArgumentParser(
        prog='render_weight_receipt',
        description='渲染记体重回执 HTML(G7 · 趋势图 + 大数字回执 · ticket #4 live 扩展)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--mock', help='回执数据 JSON 文件路径(mock 或 weight.py 输出)')
    g.add_argument('--live', action='store_true', help='实读 DB:记体重(写库 + 回执一体 · ticket #4)')
    g.add_argument('--live-batch', action='store_true', help='实读 DB:批量补录体重(写库 + 回执一体)')
    p.add_argument('--kg', type=float, help='体重(kg)')
    p.add_argument('--note', help='备注')
    p.add_argument('--date', help='记录日期 YYYY-MM-DD(默认今天;补录体重用)')
    p.add_argument('--input', help='批量补录 JSONL(每行 {"date": "YYYY-MM-DD", "kg": 70})')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output', help='输出文件路径')
    return p


def load_data(json_path: Path) -> dict:
    if not json_path.exists():
        raise FileNotFoundError(f'输入文件不存在: {json_path}')
    raw = json.loads(json_path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict):
        raise ValueError(f'JSON 顶层必须是 dict,实际是 {type(raw).__name__}')
    if 'data' in raw and isinstance(raw['data'], dict):
        return raw['data']
    return raw


def normalize(data: dict) -> dict:
    if not isinstance(data, dict):
        return {'summary': {}, 'history': []}
    return {
        'summary': data.get('summary', {}) if isinstance(data.get('summary'), dict) else {},
        'history': data.get('history', []) if isinstance(data.get('history'), list) else [],
    }


def render_html(data: dict, template_path: Path) -> str:
    template = template_path.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f'模板占位符数量异常: {template.count(placeholder)}')

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '记体重回执已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


# ============ ticket #4 · live 模式(写库 + 回执一体) ============

def _latest_history(conn, limit=30, days=30):
    """最新在前 + 近 N 天窗口(与模板 weight_log_receipt.html JS 契约一致,newestW = HISTORY[0])

    ticket #43 场景 1 人工终审修复(2026-08-03):此前 reversed(rows) 返回
    oldest→newest,导致趋势方向反/距目标错/最新点标在最旧点。回归测试:
    tests/test_weight_receipt_history.py。

    issue #198 修复(2026-08-09):此前只取最新 30 条无日期窗口过滤,稀疏记录时
    横跨远超 30 天(x 轴出现更早月份 → 与模板「近 30 天趋势」标题不符,用户实测
    最新 30 条跨 44 天)。改为 date >= today-(N-1) 天窗口,与 render_weight_history /
    render_today_meals / render_calorie_trend 等视图的「近 N 天 = 含今天共 N 个日期」
    语义一致(2026-08-09 对抗审查:原 today-N 是 N+1 个日期,off-by-one)。
    """
    cur = conn.cursor()
    # days=30 → 窗口起点 = today-29(含今天共 30 个日期),与仓库其他视图一致
    window_start = (date.today() - timedelta(days=days - 1)).isoformat()
    cur.execute('''
        SELECT date, weight_kg FROM weight_log
        WHERE date >= ?
        ORDER BY date DESC, time DESC LIMIT ?
    ''', (window_start, limit))
    rows = cur.fetchall()
    return [{'date': r[0], 'weight_kg': r[1]} for r in rows]


def build_live_receipt(kg, note='', target_date=None):
    """记体重 / 记体重（含备注）/ 补录体重:写库 + 组装回执

    呈现:体重值/记录时间/BMI/距上次/距目标/备注+分类标签/补录标识+距今天数
    """
    import weight
    from db import find_db_path
    import sqlite3

    is_backfill = bool(target_date)
    receipt = weight.log_weight(kg, note=note, target_date=target_date)
    if receipt is None:
        raise ValueError('写库失败(请先设置档案身高:profile set)')

    db_path = find_db_path(SKILL_DIR)
    conn = sqlite3.connect(str(db_path))
    history = _latest_history(conn)
    cur = conn.cursor()
    cur.execute('SELECT weight_goal FROM daily_goal WHERE id = 1')
    g = cur.fetchone()
    conn.close()

    dl = weight.delta_last(receipt['date'], receipt['time']) if receipt['date'] else None
    dl = round(receipt['kg'] - dl, 1) if dl is not None else None
    goal = g[0] if g and g[0] else None
    goal_diff = round(receipt['kg'] - goal, 1) if goal else None
    days_ago = None
    if is_backfill:
        days_ago = (date.today() - date.fromisoformat(receipt['date'])).days

    summary = {
        'new_record': {
            'id': receipt['id'],
            'date': receipt['date'],
            'time': receipt['time'],
            'weight_kg': receipt['kg'],
            'bmi': receipt['bmi'],
            'note': receipt['note'],
            'tag': weight.note_tag(receipt['note']) if receipt['note'] else None,
        },
        'delta_last': dl,
        'goal_diff': goal_diff,
        'weight_goal': {'target': goal} if goal else None,
        'backfill': {'days_ago': days_ago} if is_backfill else None,
        # 一句话(2026-08-02 · 呈现数据「一句话」)
        'one_line': _one_line(receipt, dl, goal_diff, is_backfill, days_ago),
    }
    return normalize({'summary': summary, 'history': history})


def _one_line(receipt, dl, goal_diff, is_backfill, days_ago):
    """一句话 = 对话式结论,不回声 meta(BMI/补录·距今 已由 meta+tag 展示)

    ticket #43 场景 3 终审(2026-08-03):去重原则 —— meta=事实,趋势卡=序列,
    一句话=本记录结论(记录值 + 记录级解读)。
    """
    parts = [f"{'已补录' if is_backfill else '已记录'} {receipt['kg']}kg"]
    if dl is not None:
        parts.append(f"较上次{'+' if dl > 0 else ''}{dl}kg")
    if goal_diff is not None:
        parts.append(f"距目标{'+' if goal_diff > 0 else ''}{goal_diff}kg")
    return ' · '.join(parts)


def build_live_batch(items):
    """批量补录体重:批量写库 + 组装回执(写入/跳过/失败条数 + 明细)"""
    import weight
    r = weight.batch_log_weight(items)
    return {
        'subtitle': f'共 {len(items)} 条 · 已处理',
        'wrote': r['wrote'],
        'skipped': r['skipped'],
        'failed': r['failed'],
        'items': r['items'],
        'summary': f'批量补录完成:写入 {r["wrote"]} 条,跳过 {r["skipped"]} 条,失败 {r["failed"]} 条',
        'meta': {'generated_at': date.today().isoformat()},
    }


def main():
    args = build_parser().parse_args()
    input_path = Path(args.mock) if args.mock else None

    try:
        if args.live:
            if args.kg is None:
                print('❌ --live 需要 --kg <体重>', file=sys.stderr)
                return 1
            if not _chain_valid(args.chain):
                print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
                return 2
            data = build_live_receipt(args.kg, note=args.note or '', target_date=args.date)
            cmd_name = '补录体重' if args.date else ('记体重（含备注）' if args.note else '记体重')
            template = TEMPLATE_PATH
            data['meta'] = {'chain': args.chain.strip(), 'wake_word': cmd_name, 'generated_at': date.today().isoformat()}
        elif args.live_batch:
            if not args.input:
                print('❌ --live-batch 需要 --input <jsonl>', file=sys.stderr)
                return 1
            if not _chain_valid(args.chain):
                print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
                return 2
            ip = Path(args.input)
            if not ip.exists():
                print(f'❌ 输入文件不存在: {ip}', file=sys.stderr)
                return 1
            items = [json.loads(line) for line in ip.read_text(encoding='utf-8').splitlines() if line.strip()]
            data = build_live_batch(items)
            cmd_name = '批量补录体重'
            template = BATCH_TEMPLATE_PATH
            data['meta'] = {'chain': args.chain.strip(), 'wake_word': cmd_name, 'generated_at': date.today().isoformat()}
        else:
            data = normalize(load_data(input_path))
            cmd_name = None
            template = TEMPLATE_PATH

        # meta 补全必须在 render_html 之前(2026-08-03 · ticket #43 终审:
        # 原写在 render_html 之后,注入 JSON 缺 render_cmd/source → 复制日志显示 (未知))
        if args.live or args.live_batch:
            argv = sys.argv[1:]
            if '--output' in argv:
                i = argv.index('--output')
                argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
            data['meta']['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(_quote_arg(a) for a in argv)
            data['meta']['source'] = 'weight_log (写库回执)'
        html = render_html(data, template)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    if args.live or args.live_batch:
        out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, cmd_name, 'receipt')
    else:
        out_path = Path(args.output) if args.output else html_path(SKILL_DIR, f'体重记录回执_{input_path.stem}')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    if args.live_batch:
        print(f'✅ {out_path}')
        print(f'   批量补录: 写入 {data["wrote"]} · 跳过 {data["skipped"]} · 失败 {data["failed"]}')
        return 0
    r = data.get('summary', {}).get('new_record', {})
    print(f'✅ {out_path}')
    print(f'   已记录: {r.get("date", "?")} {r.get("time", "")} | {r.get("weight_kg", "?")}kg | BMI {r.get("bmi", "?")}')
    print(f'   趋势: {len(data.get("history", []))} 条历史')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
