#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_diet_add_filename_suffix.py — 记一餐回执文件名带食物名(issue #49 · 2026-08-11 grilling 定稿)

拍板方案:
  - 方案 A:html_paths.py 的 html_name/html_path/html_scene_path 加可选 suffix 参数
  - 文件名格式:<场景>_<类型中文>_<内容>_<TS>.html,例 记一餐_回执_香蕉_20260803_000422.html
  - sanitize:替换 \\/:*?"<>|[] → _;去前后空格;截断 32 字符(按字符数)
  - 仅 live_diet_add 传 suffix;其余命令(记喝水/改食品等)文件名不变
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = SKILL_DIR / 'scripts'


# ---------- 纯函数:_sanitize_filename_part ----------

def test_sanitize_basic():
    from html_paths import _sanitize_filename_part
    assert _sanitize_filename_part('香蕉') == '香蕉'
    assert _sanitize_filename_part('咖啡拿铁') == '咖啡拿铁'


def test_sanitize_illegal_chars():
    from html_paths import _sanitize_filename_part
    # Windows 非法字符全部替换为 _
    assert _sanitize_filename_part('a/b\\c:d*e?f"g<h>i|j') == 'a_b_c_d_e_f_g_h_i_j'
    # [] 是 glob 元字符:Windows 文件名合法但会破坏冲突检测 glob,必须替换
    assert _sanitize_filename_part('苹果[大]') == '苹果_大_'


def test_sanitize_trim_and_len():
    from html_paths import _sanitize_filename_part
    assert _sanitize_filename_part('  香蕉  ') == '香蕉'
    long_name = '超' * 40
    assert _sanitize_filename_part(long_name) == '超' * 32
    assert len(_sanitize_filename_part(long_name)) == 32


def test_sanitize_empty():
    from html_paths import _sanitize_filename_part
    assert _sanitize_filename_part(None) == ''
    assert _sanitize_filename_part('') == ''


# ---------- html_name / html_path / html_scene_path 的 suffix ----------

def test_html_name_with_suffix(tmp_path):
    from html_paths import html_name
    nm = html_name('记一餐_回执', html_dir=str(tmp_path), suffix='香蕉')
    assert nm.name.startswith('记一餐_回执_香蕉_')
    assert nm.name.endswith('.html')
    # 不传 suffix = 原行为
    nm2 = html_name('记一餐_回执', html_dir=str(tmp_path))
    assert nm2.name.startswith('记一餐_回执_')
    assert '_香蕉_' not in nm2.name


def test_html_scene_path_with_suffix(tmp_path):
    from html_paths import html_scene_path
    p = html_scene_path(SKILL_DIR, '记一餐', 'receipt', suffix='咖啡拿铁')
    assert p.name.startswith('记一餐_回执_咖啡拿铁_')
    assert p.name.endswith('.html')
    # 不传 suffix = 原行为
    p2 = html_scene_path(SKILL_DIR, '记一餐', 'receipt')
    assert p2.name.startswith('记一餐_回执_')
    assert '_咖啡拿铁_' not in p2.name


def test_suffix_illegal_chars_sanitized(tmp_path):
    from html_paths import html_scene_path
    p = html_scene_path(SKILL_DIR, '记一餐', 'receipt', suffix='香蕉/大份')
    assert '_香蕉_大份_' in p.name
    assert '/' not in p.name


def test_conflict_same_food_same_second(tmp_path):
    """同秒同食物 → 追加 _2(冲突保护保留)"""
    from html_paths import html_name
    a = html_name('记一餐_回执', html_dir=str(tmp_path), suffix='香蕉')
    (tmp_path / a).write_text('x', encoding='utf-8')  # 模拟第一次已写盘
    b = html_name('记一餐_回执', html_dir=str(tmp_path), suffix='香蕉')
    assert b.name == a.name.replace('.html', '_2.html')


def test_conflict_different_food_same_second(tmp_path):
    """同秒不同食物 → 互不冲突(前缀不同)"""
    from html_paths import html_name
    a = html_name('记一餐_回执', html_dir=str(tmp_path), suffix='香蕉')
    (tmp_path / a).write_text('x', encoding='utf-8')
    b = html_name('记一餐_回执', html_dir=str(tmp_path), suffix='苹果')
    assert b.name != a.name
    assert '_苹果_' in b.name
    assert b.name.endswith('.html')  # 无 _2 后缀


# ---------- 端到端:render_crud_receipt.py CLI(隔离 DB) ----------

_CHAIN = '1.测试_49_记一餐文件名'

def _run_render(env_dir, *args):
    env = {**os.environ, 'SKILLS_DB_PATH': str(env_dir)}
    return subprocess.run(
        [sys.executable, 'render_crud_receipt.py', *args, '--chain', _CHAIN],
        cwd=str(SCRIPTS_DIR), env=env, capture_output=True, text=True,
        encoding='utf-8', timeout=120)


def test_e2e_diet_add_filename_has_food(temp_db):
    """记一餐 → 文件名带食物名:记一餐_回执_香蕉_<TS>.html"""
    html_dir = temp_db.parent / 'calorie_html'
    res = _run_render(temp_db.parent, '--live-diet-add', '香蕉', '200', '2')
    assert res.returncode == 0, res.stderr
    files = list(html_dir.glob('记一餐_回执_香蕉_*.html'))
    assert files, f'未生成带食物名的回执,实际文件:{[p.name for p in html_dir.iterdir()]}'
    assert files[0].read_text(encoding='utf-8').strip()  # 内容非空


def test_e2e_diet_add_same_food_twice(temp_db):
    """同秒两次记同一食物 → 第二个文件名 _2 后缀仍工作"""
    html_dir = temp_db.parent / 'calorie_html'
    res1 = _run_render(temp_db.parent, '--live-diet-add', '香蕉', '200', '2')
    assert res1.returncode == 0, res1.stderr
    res2 = _run_render(temp_db.parent, '--live-diet-add', '香蕉', '200', '2')
    assert res2.returncode == 0, res2.stderr
    files = sorted(html_dir.glob('记一餐_回执_香蕉_*.html'))
    assert len(files) >= 2
    assert any('_2.' in p.name for p in files), [p.name for p in files]


def test_e2e_diet_add_english_and_special(tmp_path):
    """英文 / 数字 / 特殊字符食物名安全(隔离 DB:手动设 env,不依赖 temp_db)"""
    from html_paths import html_dir as _hd  # noqa: F401  (仅为触发同路径逻辑)
    env_dir = tmp_path / 'db'
    env_dir.mkdir()
    html_dir = env_dir / 'calorie_html'
    res = _run_render(env_dir, '--live-diet-add', 'Coffee Latte/大杯', '150', '3')
    assert res.returncode == 0, res.stderr
    files = list(html_dir.glob('记一餐_回执_Coffee Latte_大杯_*.html'))
    assert files, f'英文/空格/斜杠食物名未正确 sanitize,实际:{[p.name for p in html_dir.iterdir()]}'
    assert '/' not in files[0].name


def test_e2e_other_commands_filename_unchanged(temp_db):
    """非记一餐命令文件名不变:记喝水_回执_<TS>.html"""
    html_dir = temp_db.parent / 'calorie_html'
    res = _run_render(temp_db.parent, '--live-water-add', '500')
    assert res.returncode == 0, res.stderr
    files = list(html_dir.glob('记喝水_回执_*.html'))
    assert files, f'记喝水回执未生成,实际:{[p.name for p in html_dir.iterdir()]}'
    for p in files:
        stem = p.stem[len('记喝水_回执'):]  # _<TS> 或 _<TS>_2
        assert stem.startswith('_') and stem[1].isdigit(), p.name
