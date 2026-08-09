#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_today_diet_filename.py — 看昨日饮食文件名与标题一致(issue #53 · 2026-08-09)

现象:用户说"看昨天",生成 HTML 文件名写死「今日饮食总览_<TS>.html」,
内部标题却是昨天日期 → 文件名与内容矛盾,用户无法靠文件名识别。

修复:文件名按查询日期动态(diet_filename_label)+ 模板 <title> 同步日期。
本测试锁住命名契约(今日/昨日/历史日期)+ 模板 title 动态注入。
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))


def test_label_today():
    """今天 → 今日饮食总览"""
    import render_today_diet as rtd
    today = date(2026, 8, 9)
    assert rtd.diet_filename_label('2026-08-09', today) == '今日饮食总览'
    assert rtd.diet_filename_label('20260809', today) == '今日饮食总览'


def test_label_yesterday():
    """昨天 → 昨日饮食总览(issue #53 核心)"""
    import render_today_diet as rtd
    today = date(2026, 8, 9)
    assert rtd.diet_filename_label('2026-08-08', today) == '昨日饮食总览'
    assert rtd.diet_filename_label('20260808', today) == '昨日饮食总览'


def test_label_older_date():
    """N 天前 → 饮食总览_<YYYYMMDD>(按日期归一)"""
    import render_today_diet as rtd
    today = date(2026, 8, 9)
    assert rtd.diet_filename_label('2026-08-05', today) == '饮食总览_20260805'
    assert rtd.diet_filename_label('2026-07-01', today) == '饮食总览_20260701'


def test_label_future_date_also_normalized():
    """未来日期(补看)同样按日期归一"""
    import render_today_diet as rtd
    today = date(2026, 8, 9)
    assert rtd.diet_filename_label('2026-08-10', today) == '饮食总览_20260810'


def test_html_title_injects_date():
    """模板 <title> 必须有 JS 动态注入(issue #53 V5:title 与文件名口径一致)"""
    tpl = Path(__file__).resolve().parent.parent / 'templates' / 'today_diet.html'
    html = tpl.read_text(encoding='utf-8')
    assert 'document.title =' in html, '模板必须动态设置 <title>(随日期变化)'
    assert 'meta.date' in html
