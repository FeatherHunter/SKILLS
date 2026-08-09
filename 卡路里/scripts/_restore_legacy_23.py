#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""恢复被 6517ac8 误删的 23 个 legacy 词(2026-08-02)

6517ac8(健身计划并发覆盖修复)整文件重写 _triggers.py 时,除误删
基础信息/目标管理/身体细节/身材照片 4 分类外,还删了 23 个 legacy 词
(复盘 9 + 分析榜类 10 + 查健康报告/查卡路里数据 + 看有备注饮食记录),
这些词在 SKILL.md frontmatter 有声明,quick_action 与测试依赖。

本脚本从 git 历史(399eeadf,6517ac8 父提交)用 ast 安全解析 TRIGGERS,
按 wake_word 精确提取目标条目,增量追加到当前 _triggers.py 末尾。

用法: python scripts/_restore_legacy_23.py
"""
import ast
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'scripts' / '_triggers.py'

TARGETS = [
    "今日复盘", "关闭定时复盘", "复盘", "复盘日期范围", "开启定时复盘",
    "本周复盘", "本年复盘", "本月复盘",
    "查低热量榜", "查健康报告", "查卡路里数据", "查定时复盘", "查热量缺口",
    "查热量趋势", "查营养结构", "查运动分布", "查运动贡献", "查频繁吃榜",
    "查食物排行", "查高热量榜", "查高碳水榜", "查高蛋白榜",
    "看「有备注」的饮食记录",
]

PARENT = "399eeadf"  # 6517ac8 的父提交(覆盖前正常状态)


def load_old_triggers():
    raw = subprocess.run(
        ["git", "show", f"{PARENT}:卡路里/scripts/_triggers.py"],
        capture_output=True).stdout.decode("utf-8", errors="replace")
    tree = ast.parse(raw)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == 'TRIGGERS':
                    return ast.literal_eval(node.value)
    raise SystemExit("❌ 旧版 TRIGGERS 未找到")


def render_legacy_entry(t: dict) -> str:
    """按旧格式渲染单条 entry(main_prompt + variants + fill_hints)"""
    mp = t.get('main_prompt') or {}
    # 文本值用 json.dumps 转义(含 \n 换行),避免语法错误
    def js(v):
        return json.dumps(v, ensure_ascii=False)
    parts = [f"    {{",
             f"            'category': {js(t['category'])},     'wake_word': {js(t['wake_word'])},     'desc': {js(t.get('desc', ''))},",
             f"            'main_prompt': {{",
             f"        'cli': {js(mp.get('cli', ''))}, 'text': {js(mp.get('text', ''))}}},",
             f"        'fill_hints': {json.dumps(t.get('fill_hints', []), ensure_ascii=False)},",
             f"            'variants': {json.dumps(t.get('variants', []), ensure_ascii=False)}}},"]
    return "\n".join(parts)


def main():
    old = load_old_triggers()
    by_wake = {t['wake_word']: t for t in old}

    text = DEST.read_text(encoding='utf-8')
    existing = set(re.findall(r"'wake_word': '([^']+)'", text))

    entries = []
    added = 0
    for w in TARGETS:
        if w in existing:
            print(f"  跳过(已存在): {w}")
            continue
        t = by_wake.get(w)
        if not t:
            print(f"❌ 旧版无此词: {w}")
            continue
        entries.append(render_legacy_entry(t))
        added += 1
        print(f"✅ 恢复: {w}")

    if not entries:
        print("✅ 无缺失,无需恢复")
        return

    block = "\n".join(entries) + "\n"
    # 定位 TRIGGERS 数组结束:找到 'TRIGGERS = [' 后匹配的数组闭合 ']'
    # 逐行扫描:从 'TRIGGERS = [' 开始,独立行 ']' 即数组结束
    lines = text.split('\n')
    start_idx = None
    for i, l in enumerate(lines):
        if l.strip().startswith('TRIGGERS = ['):
            start_idx = i
            break
    if start_idx is None:
        raise SystemExit("❌ TRIGGERS = [ 未找到")
    end_idx = None
    for i in range(start_idx, len(lines)):
        if lines[i].strip() == ']':
            end_idx = i
            break
    if end_idx is None:
        raise SystemExit("❌ TRIGGERS 数组闭合 ] 未找到")
    lines.insert(end_idx, block.rstrip('\n'))
    DEST.write_text('\n'.join(lines), encoding='utf-8')
    print(f"✅ 恢复 {added} 条 legacy 词")


if __name__ == '__main__':
    from _io_guard import guard_io; guard_io()
    main()
