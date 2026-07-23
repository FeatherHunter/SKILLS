#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_contraindication.py — 渲染禁忌扫描 HTML 报告

对应 SKILL.md 唤醒词:`扫禁忌`(可视化输出)

设计原则(《预置 HTML + 注入数据指导手册》):
- 模板稳定:原 templates/contraindication_report.html 不变
- 数据流动:每次调用通过 scan_contraindications.py 拿最新 JSON
- 占位符唯一:模板含 <!--INJECT-DATA--> 恰好 1 次
- 不污染模板:输出到新文件,原模板不动
- </ 转义防断标签:.replace('</', '<\\/')

用法:
    python scripts/render_contraindication.py                        # 默认扫全部位
    python scripts/render_contraindication.py --part 腰 --part 膝    # 指定部位
    python scripts/render_contraindication.py --output <path>        # 指定输出
    python scripts/render_contraindication.py --strict               # 严格模式
"""
import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / 'templates' / 'contraindication_report.html'

DEFAULT_DB = '/mnt/d/2Study/StudyNotes/.db/calorie_data.db'


def build_parser():
    p = argparse.ArgumentParser(
        prog="render_contraindication",
        description="渲染禁忌扫描 HTML 报告(模板+数据注入)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--part", action="append", choices=["腰", "膝", "肩", "all"])
    p.add_argument("--db", default=DEFAULT_DB, help="SQLite DB 路径")
    p.add_argument("--strict", action="store_true", help="严格模式")
    p.add_argument("--output", help="输出文件路径(默认 /tmp/contraindication_<date>.html)")
    return p


def fetch_json(args) -> dict:
    """调 scan_contraindications.py 拿结构化 JSON"""
    cmd = ['python3', str(SCRIPT_DIR / 'scan_contraindications.py'),
           '--db', args.db, '--format', 'json']
    if args.part:
        for p in args.part:
            cmd.extend(['--part', p])
    if args.strict:
        cmd.append('--strict')

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    if result.returncode not in (0, 1):  # 0=ok, 1=warn(允许)
        raise RuntimeError(
            f"scan_contraindications.py 失败 (exit={result.returncode})\n"
            f"stderr: {result.stderr}"
        )
    return json.loads(result.stdout)


def render_html(data: dict) -> str:
    """读模板 + 注入数据"""
    template = TEMPLATE_PATH.read_text(encoding='utf-8')

    # 检查占位符唯一性
    placeholder = '<!--INJECT-DATA-->'
    if template.count(placeholder) != 1:
        raise ValueError(
            f"模板占位符数量异常: 期望 1 个,实际 {template.count(placeholder)} 个\n"
            f"路径: {TEMPLATE_PATH}"
        )

    # 转义 </ 防止提前闭合 script 标签
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    inject = f'<script>window.__DATA__ = {payload};</script>'
    return template.replace(placeholder, inject, 1)


def main():
    args = build_parser().parse_args()

    try:
        data = fetch_json(args)
        html = render_html(data)
    except Exception as e:
        print(f"❌ 渲染失败: {e}", file=sys.stderr)
        return 1

    # 输出
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = Path(f'/tmp/contraindication_{date.today().isoformat()}.html')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding='utf-8')

    # 摘要
    d = data.get('data', {})
    status = data.get('status', '?')
    summary_status = d.get('summary_status', '?')
    by_sev = d.get('by_severity', {})
    print(f"✅ {out_path}")
    print(f"   status={status} | summary={summary_status}")
    print(f"   error={by_sev.get('error', 0)} warn={by_sev.get('warn', 0)} info={by_sev.get('info', 0)}")
    print(f"   safe_skipped={d.get('safe_skipped', 0)} | hits={len(d.get('hits', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())