#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_live_flag_consistency.py — render_crud_receipt.py 的 live flag 三源一致性守卫(盲区审查 #49)

根因(2026-08-11 盲区审查发现):argparse 定义了 --live-diet-batch-meal,但 main() 的
active 检测循环漏了它 → active=None → 'NoneType'.startswith 崩溃 → CLI 渲染必崩。
单测只调 build_live_* 函数不走 main(),洞逃过全部测试(commit b633c9e 修复)。

本守卫锁死根因:三源必须一致,任何新增 live flag 漏注册立即红灯:
  源1: argparse 的 --live-* 参数定义
  源2: main() 的 active 检测循环(flag_name 元组)
  源3: _LIVE_NAMES 场景映射 dict 的 key
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

TARGET = Path(__file__).resolve().parent.parent / 'scripts' / 'render_crud_receipt.py'


def _src():
    return TARGET.read_text(encoding='utf-8')


def _argparse_live_flags(src):
    """提取 argparse 定义的 --live-* 参数名(连字符→下划线归一)"""
    return {f.replace('-', '_') for f in re.findall(r"add_argument\('--(live-[a-z-]+)'", src)}


def _live_names_keys(src):
    """提取 _LIVE_NAMES dict 的 key 集合(去掉引号冒号)"""
    return {m[1:-2] for m in re.findall(r"'live_[a-z_]+':", src)}


def test_argparse_flags_covered_by_active_loop():
    src = _src()
    defined = _argparse_live_flags(src)
    assert defined, '未匹配到任何 --live-* 参数(正则可能失效,守卫失效)'
    m = re.search(r"for flag_name in \((.*?)\):\s*\n\s*if getattr", src, re.S)
    assert m, '未找到 active 检测循环'
    active = set(re.findall(r"'([a-z_]+)'", m.group(1)))
    missing = defined - active
    assert not missing, (
        f'argparse 定义的 live flag 未进 active 检测循环(CLI 调用会渲染必崩): {sorted(missing)}\n'
        f'修复:render_crud_receipt.py main() 的 active 循环补上对应 flag_name'
    )


def test_argparse_flags_covered_by_live_names():
    src = _src()
    defined = _argparse_live_flags(src)
    names = _live_names_keys(src)
    missing = defined - names
    assert not missing, (
        f'argparse 定义的 live flag 无 _LIVE_NAMES 场景映射(文件名/唤醒词会变 操作回执): {sorted(missing)}'
    )


def test_live_names_keys_covered_by_argparse():
    src = _src()
    defined = _argparse_live_flags(src)
    names = _live_names_keys(src)
    extra = names - defined
    assert not extra, f'_LIVE_NAMES 有 argparse 未定义的 key(死映射): {sorted(extra)}'
