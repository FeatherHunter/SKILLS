#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_weight_compare.py — 对比体重 18 场景结果 HTML 渲染器(ticket #4)

对应 SKILL.md 唤醒词(18 个):
  a1 对比体重：最近 30 天 vs 之前 30 天      a2 对比体重：自定义两段时间
  a3 对比体重：本周 vs 上周                  a4 对比体重：本月 vs 上月
  a5 对比体重：近 N 天 vs 上一个 N 天        a6 对比体重：今天 vs 一年前今天
  a7 对比体重：今天 vs 半年前今天            a8 对比体重：今天 vs 三月前今天
  b1 对比体重：当前 vs 目标体重              b8 对比体重：当前 vs 平台期首日
  e1 对比体重：当前 vs 历史最低              e2 对比体重：当前 vs 历史最高
  e3 对比体重：减重 5/10kg 那天 vs 今天       e5 对比体重：当前 vs 入夏最低
  e6 对比体重：当前 vs 入冬最低              c5 对比体重：运动多 vs 运动少的两个月
  d4 对比体重：工作日 vs 周末
对应模板: templates/weight_compare.html
用法:
  python scripts/render_weight_compare.py --scenario a1 --chain "1.识别→2.读DB→3.对比→4.渲染"
  python scripts/render_weight_compare.py --scenario a2 --start-a 2026-06-01 --end-a 2026-06-30 --start-b 2026-07-01 --end-b 2026-07-31 --chain "..."
"""
import argparse, json, sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'weight_compare.html'

sys.path.insert(0, str(SCRIPT_DIR))
from html_paths import html_scene_path  # noqa
from render_crud_view import _chain_valid, _quote_arg  # noqa
from analysis.weight_compare import run_scenario, SCENARIO_LABELS  # noqa


def render_html(data):
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    if template.count('<!--INJECT-DATA-->') != 1:
        raise ValueError('模板缺少唯一占位符')
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    return template.replace('<!--INJECT-DATA-->', f'<script>window.__DATA__ = {payload};</script>', 1)


def _summary_line(scenario, data):
    """1 句话总结(呈现数据承诺的对应物)"""
    c = data.get('compare') or {}
    if data.get('sample_warning'):
        return data['sample_warning']
    if c.get('delta_kg') is None:
        return '对比完成'
    # 2026-08-10 #43 审查:精度统一两位(与箭头一致) + 标点「·」分隔
    delta = f"{c['delta_kg']:+.2f}" if isinstance(c['delta_kg'], float) else f"{c['delta_kg']}"
    speed = f" · {c['speed']}" if c.get('speed') and c['speed'] != '—' else ''
    return f"两段对比：Δ{delta} kg · {c['direction']}{speed}"


def main():
    p = argparse.ArgumentParser(description='渲染对比体重结果 HTML(18 场景 · ticket #4)')
    p.add_argument('--scenario', required=True,
                   choices=sorted(SCENARIO_LABELS.keys()),
                   help='对比场景(a1-a8/b1/b8/e1-e6/c5/d4)')
    p.add_argument('--start-a')
    p.add_argument('--end-a')
    p.add_argument('--start-b')
    p.add_argument('--end-b')
    p.add_argument('--n', type=int, default=30, help='a5:近 N 天 vs 上 N 天')
    p.add_argument('--delta', type=float, default=5, help='e3:减重 N kg 里程碑')
    p.add_argument('--chain', help='AI 思考链(必填·强制规则 · 2026-08-02)')
    p.add_argument('--output')
    args = p.parse_args()

    if not _chain_valid(args.chain):
        print('❌ --chain 缺失或无效:AI 思考链是排障日志的必要字段(强制规则)', file=sys.stderr)
        return 2

    label = SCENARIO_LABELS.get(args.scenario, '对比体重')
    if args.scenario == 'e3':
        label = f'对比体重：减重 {args.delta:.0f}kg 那天 vs 今天'
    elif args.scenario == 'a5':
        label = f'对比体重：近 {args.n} 天 vs 上一个 {args.n} 天'

    kw = {'n': args.n, 'delta': args.delta, 'start_a': args.start_a, 'end_a': args.end_a,
          'start_b': args.start_b, 'end_b': args.end_b}
    try:
        data, err = run_scenario(args.scenario, **kw)
        if err:
            # 2026-08-02 ticket #4 对抗审查修复:数据缺失(未设目标/无平台期/样本不足)也要产出 HTML
            # (第 5 层「呈现数据承诺 → HTML 对应物」闭环;AI 拿提示页引导用户下一步)
            data = {
                'scenario': args.scenario,
                'scenario_label': label,
                'title': label,
                'subtitle': f'无法完成对比 · {date.today().isoformat()}',
                'sample_warning': err,
                'kpis': [],
                'seg_a': None,
                'seg_b': None,
                'compare': None,
                'extra_rows': [{'label': '下一步', 'value': '请先按提示补齐数据后重试(如「定体重目标」)'}],
                'summary': err,
                'meta': {'generated_at': date.today().isoformat(),
                         'chain': args.chain.strip(), 'wake_word': label},
            }
        else:
            data['scenario'] = args.scenario
            data['scenario_label'] = label
            data['title'] = label
            data['summary'] = _summary_line(args.scenario, data)
            data['meta'] = {'generated_at': date.today().isoformat(),
                            'chain': args.chain.strip(),
                            'wake_word': label}
        argv = sys.argv[1:]
        if '--output' in argv:
            i = argv.index('--output')
            argv = argv[:i] + argv[i + 2:] if i + 1 < len(argv) else argv[:i]
        data['meta']['render_cmd'] = f"python scripts/{Path(__file__).name} " + ' '.join(_quote_arg(a) for a in argv)
        data['meta']['source'] = 'weight_log (对比分析)'
        payload = {'status': 'ok', 'data': data, 'message': f'已生成 {label}'}
        html = render_html(payload)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    out_path = Path(args.output) if args.output else html_scene_path(SKILL_DIR, label, 'result')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')
    print(f'✅ {out_path}')
    print(f'   场景: {args.scenario} | {label}')
    return 0


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    sys.exit(main())
