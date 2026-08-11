# -*- coding: utf-8 -*-
"""追加: 08 规范硬标准断言 —— 业务模板必须有复制数据/复制日志按钮（#269 遗漏教训）

engine 薄壳模板（day/range/compare/category/anomaly/detail/week）的按钮由
_record_engine.js 运行时生成, 检查外部 JS 文件（教训: 不能只看模板字符串）。
"""
import io
import pathlib

import pytest

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent

# 非薄壳模板（复制数据/日志直接或经 actionBar 在模板内）
DIRECT_TEMPLATES = [
    'plan_result.html', 'record_result.html', 'schedule_list_events.html',
    'schedule_plan_preview.html', 'schedule_plan_receipt.html',
    'schedule_plan_receipt_add.html', 'schedule_plan_receipt_write.html',
    'schedule_plan_review.html', 'schedule_record_receipt.html',
    'schedule_record_receipt_edit.html', 'schedule_replay.html',
]
# engine 薄壳模板（按钮由 _record_engine.js 生成）
ENGINE_TEMPLATES = [
    'schedule_record_anomaly.html', 'schedule_record_category.html',
    'schedule_record_compare.html', 'schedule_record_day.html',
    'schedule_record_detail.html', 'schedule_record_range.html', 'week_view.html',
]


@pytest.mark.parametrize("tpl", DIRECT_TEMPLATES)
def test_direct_template_has_copy_data_log(tpl):
    """08 规范硬标准: 非薄壳模板必须含「复制数据」+「复制日志」字样"""
    c = io.open(SKILL_DIR / 'templates' / tpl, encoding='utf-8').read()
    assert '复制数据' in c, f'{tpl}: 缺「复制数据」（08 规范硬标准）'
    assert '复制日志' in c, f'{tpl}: 缺「复制日志」（08 规范硬标准）'


def test_engine_js_has_copy_data_log():
    """engine 型: _record_engine.js 必须生成复制数据/日志按钮（actionBarBlock）"""
    js = io.open(SKILL_DIR / 'templates' / '_record_engine.js', encoding='utf-8').read()
    assert 'actionBarBlock' in js, '_record_engine.js: 缺 actionBarBlock（复制数据/日志生成）'
    assert '复制数据' in js, '_record_engine.js: 缺复制数据按钮逻辑'
    assert '复制日志' in js, '_record_engine.js: 缺复制日志按钮逻辑'


@pytest.mark.parametrize("tpl", ENGINE_TEMPLATES)
def test_engine_template_references_engine(tpl):
    """engine 薄壳模板必须引用 _record_engine.js（按钮渲染依赖）"""
    c = io.open(SKILL_DIR / 'templates' / tpl, encoding='utf-8').read()
    assert '_record_engine.js' in c, f'{tpl}: 未引用 _record_engine.js（engine 型渲染缺失）'
