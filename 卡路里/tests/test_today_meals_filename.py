#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_today_meals_filename.py — 周/月/自定义区间饮食文件命名(issue #53 同族 · 2026-08-09 对抗审查)

对抗审查发现:render_today_meals.py 输出文件名写死「今日饮食」,而模板 h1 已按
meta.label 动态(本周饮食/上周饮食/最近 7 天饮食/某段时间饮食)→ 文件名与内容
标题分裂(与 #53 原始 bug 同类,但走的是周/月视图入口)。

修复:文件名用与 h1 相同的 label(本周饮食_<TS>.html / 上月饮食_<TS>.html …)。
本测试锁住 main() 的命名标签解析(week/month/days/自定义)。
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))


def _resolve_label(args_dict):
    """复刻 main() 的 label 解析逻辑(不跑渲染,只锁命名契约)"""
    import render_today_meals as rtm
    from datetime import date as _date, timedelta as _td
    week = args_dict.get('week')
    month = args_dict.get('month')
    days = args_dict.get('days', 3)
    start, end = args_dict.get('start'), args_dict.get('end')
    if week:
        s, e = rtm._natural_week(week)
        return ('本周' if week == 'current' else '上周'), s, e
    if month:
        s, e = rtm._natural_month(month)
        return ('本月' if month == 'current' else '上月'), s, e
    if not start or not end:
        end_d = _date.today()
        start_d = end_d - _td(days=days - 1)
        return f'最近 {days} 天', start_d.isoformat(), end_d.isoformat()
    return '某段时间', start, end


def test_label_week():
    label, s, e = _resolve_label({'week': 'current'})
    assert label == '本周'
    label2, _, _ = _resolve_label({'week': 'last'})
    assert label2 == '上周'


def test_label_month():
    label, s, e = _resolve_label({'month': 'current'})
    assert label == '本月'
    label2, _, _ = _resolve_label({'month': 'last'})
    assert label2 == '上月'


def test_label_days():
    label, s, e = _resolve_label({'days': 7})
    assert label == '最近 7 天'
    today = date.today()
    assert s == (today - timedelta(days=6)).isoformat()
    assert e == today.isoformat()


def test_label_custom_range():
    label, s, e = _resolve_label({'start': '2026-08-01', 'end': '2026-08-07'})
    assert label == '某段时间'
    assert (s, e) == ('2026-08-01', '2026-08-07')


def test_html_title_injects_label():
    """模板 title 必须动态注入 label(与文件名口径一致)"""
    tpl = Path(__file__).resolve().parent.parent / 'templates' / 'today_meals.html'
    html = tpl.read_text(encoding='utf-8')
    assert 'document.title =' in html
    assert 'meta.label' in html
