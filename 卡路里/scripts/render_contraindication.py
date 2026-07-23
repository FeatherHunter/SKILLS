#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_contraindication.py — 禁忌扫描报告 HTML 渲染器(v2 可改版)

对应 SKILL.md 唤醒词:扫禁忌

设计原则:
- 过程型 HTML(AI 协同模式 · 原则 10)
- 必含 2 复制按钮:复制修改指令 + 完整报告
- 4 部分 prompt:场景 + 数据(已选替代) + 期望 CLI + 来源

2026-07-23 G5 升级:
- 模板升级为 v2 可改版,每个 error 旁附 SAFE_VARIANTS 替代按钮
- 用户在 HTML 直接点选 → 复制时含已选列表
- 完全替代 v1 的"只读"模式

用法:
    python scripts/render_contraindication.py                           # 默认扫描 + 输出
    python scripts/render_contraindication.py --part 腰 --part 膝      # 指定部位
    python scripts/render_contraindication.py --mock mock_contraindication.json  # 用 mock 测试
    python scripts/render_contraindication.py --output /path/out.html
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'contraindication_report.html'


def build_parser():
    p = argparse.ArgumentParser(prog='render_contraindication',
                                  description='渲染禁忌扫描报告 v2 HTML(可改版)')
    p.add_argument('--part', action='append', choices=['腰', '膝', '肩', 'all'],
                   help='扫描部位(可多次传;默认 all)')
    p.add_argument('--db', default='/mnt/d/2Study/StudyNotes/.db/calorie_data.db',
                   help='SQLite DB 路径')
    p.add_argument('--strict', action='store_true', help='严格模式')
    p.add_argument('--mock', help='用 mock JSON 文件代替真实扫描(测试用)')
    p.add_argument('--output', help='输出文件路径')
    return p


def fetch_scan(args) -> dict:
    """从 scan_contraindications.py 拉数据(支持 mock)"""
    if args.mock:
        mock_path = Path(args.mock)
        if not mock_path.exists():
            raise FileNotFoundError(f"mock 文件不存在: {mock_path}")
        raw = json.loads(mock_path.read_text(encoding='utf-8'))
        # 兼容两种格式: ① {summary, hits} ② {data: {summary, hits}}
        if 'data' in raw and isinstance(raw['data'], dict):
            return raw['data']
        return raw

    cmd = ['python3', str(SCRIPT_DIR / 'scan_contraindications.py'),
           '--db', args.db, '--format', 'json']
    if args.part:
        for part in args.part:
            cmd.extend(['--part', part])
    else:
        cmd.append('--part')
        cmd.append('all')
    if args.strict:
        cmd.append('--strict')

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode not in (0, 1):
        raise RuntimeError(f"scan_contraindications.py 失败: {result.stderr}")
    return json.loads(result.stdout)['data']


def enrich_with_safe_variants(data: dict) -> dict:
    """从 contraindications.soft_rules 拉 SAFE_VARIANTS 白名单(BUG #1 修复:仅当缺失时补充)"""
    if 'safe_variants' not in data or not data.get('safe_variants'):
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from contraindications.soft_rules import SAFE_VARIANTS
            data['safe_variants'] = list(SAFE_VARIANTS)
        except Exception:
            # 如果读不到 SAFE_VARIANTS,提供 fallback
            data['safe_variants'] = [
                '支撑式(重力卸力)', '俯卧(趴着重力卸力)',
                '仰卧(贴垫重力零)', '高位(不压腰椎)',
            ]
    return data


def render_html(data: dict) -> str:
    """读模板 + 注入数据"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(f"模板占位符数量异常: {template.count(placeholder)}")

    payload = json.dumps({'status': 'ok', 'data': data, 'message': '禁忌扫描 v2 已生成'},
                         ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    args = build_parser().parse_args()

    try:
        data = fetch_scan(args)
        data = enrich_with_safe_variants(data)
        html = render_html(data)
    except Exception as e:
        print(f'❌ 渲染失败: {e}', file=sys.stderr)
        return 1

    default_name = f'contraindication_report_{args.part[0] if args.part else "all"}.html'
    out_path = Path(args.output) if args.output else Path('/tmp') / default_name
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    s = data.get('summary', {})
    bs = s.get('by_severity', {})
    selected_hint = 'v2:扫描 + 替代选择 + 复制修改指令'
    print(f'✅ {out_path}')
    print(f'   {selected_hint}')
    print(f'   Scan: {s.get("scanned_sessions", 0)} sessions / {s.get("scanned_movements", 0)} movements')
    print(f'   Error {bs.get("error", 0)} · Warn {bs.get("warn", 0)} · Info {bs.get("info", 0)} · Safe {s.get("safe_skipped", 0)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())