#!/usr/bin/env python3
"""
饼干记账 · HTML 注入脚本 v1.0

把 CLI 的 JSON 输出注入到 templates/query_view.html，生成可视化 HTML 页面。

使用方法：
    python3 scripts/bill_inject.py summary
    python3 scripts/bill_inject.py list --date 2026-07-23
    python3 scripts/bill_inject.py recent --limit 20
    python3 scripts/bill_inject.py search "午饭"
    python3 scripts/bill_inject.py monthly --month 2026-07
    python3 scripts/bill_inject.py compare --period week
    python3 scripts/bill_inject.py breakdown
    python3 scripts/bill_inject.py breakdown --from 2026-07-01 --to 2026-07-31
    python3 scripts/bill_inject.py overview --month 2026-07
    python3 scripts/bill_inject.py stats

输出：
    饼干记账_查询_<type>_<YYYYMMDD_HHMMSS>.html（默认写到 D:/Downloads 或当前目录）
    --out <path> 可指定输出路径
"""

import sys
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

SKILL_DIR = _SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "query_view.html"
CLI_PATH = _SCRIPT_DIR / "record_bill.py"

# 支持的查询类型（CLI 子命令 + 对应的 data.title / data.subtitle）
QUERY_TYPES = {
    "summary":   {"title": "今日摘要",        "subtitle": "当天收支概览"},
    "list":      {"title": "查询记录",        "subtitle": "按条件筛选的明细"},
    "recent":    {"title": "最近记录",        "subtitle": "最新 N 条记录"},
    "search":    {"title": "备注搜索",        "subtitle": "关键词匹配的记录"},
    "monthly":   {"title": "月度汇总",        "subtitle": "整月支出/收入/净额 + 分类排行"},
    "compare":   {"title": "周期对比",        "subtitle": "本期 vs 上期支出变化"},
    "breakdown": {"title": "分类明细",        "subtitle": "各类支出占比 + 笔数/均值"},
    "overview":  {"title": "收支总览",        "subtitle": "当月 4 个核心指标"},
    "stats":     {"title": "记账统计",        "subtitle": "总笔数 / 天数 / 首末时间"},
}


def run_cli_json(query_type: str, extra_args: list) -> dict:
    """调用 record_bill.py <query_type> --json <extra_args>...，解析 JSON 输出"""
    cmd = [sys.executable, str(CLI_PATH), query_type, "--json"] + list(extra_args)
    env = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", "PATH": __import__("os").environ.get("PATH", "")}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env, timeout=30)
    except subprocess.TimeoutExpired:
        return {"status": "error", "data": None, "message": f"CLI 调用超时（30s）: {' '.join(cmd)}"}
    except FileNotFoundError as e:
        return {"status": "error", "data": None, "message": f"找不到 CLI: {e}"}

    if result.returncode != 0 and not result.stdout.strip():
        return {
            "status": "error",
            "data": None,
            "message": f"CLI 调用失败 (exit={result.returncode}): {result.stderr.strip() or '(无 stderr)'}"
        }

    out = result.stdout.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        return {
            "status": "error",
            "data": None,
            "message": f"CLI 输出不是合法 JSON：{e} | 原始输出: {out[:200]}"
        }


def build_payload(cli_json: dict, query_type: str, extra_args: list) -> dict:
    """把 CLI JSON 包成模板期望的 payload 结构"""
    meta = QUERY_TYPES.get(query_type, {"title": query_type, "subtitle": ""})
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if cli_json.get("status") == "error":
        return {
            "status": "error",
            "data": None,
            "message": cli_json.get("message", "未知错误")
        }

    data = cli_json.get("data") or {}
    # 注入 type / title / subtitle / generated_at / extra_args
    enriched = dict(data)
    enriched["type"] = query_type
    enriched["title"] = meta["title"]
    enriched["subtitle"] = meta["subtitle"] + (f" · 参数: {' '.join(extra_args)}" if extra_args else "")
    enriched["generated_at"] = now

    return {
        "status": cli_json.get("status", "ok"),
        "data": enriched,
        "message": cli_json.get("message", "")
    }


def inject_to_template(payload: dict, output_path: Path) -> Path:
    """把 payload 注入到模板，生成 HTML 文件"""
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"模板不存在: {TEMPLATE_PATH}")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    old = '<script id="payload" type="application/json">{"status":"empty","data":null,"message":"数据未注入"}</script>'
    new = f'<script id="payload" type="application/json">{payload_json}</script>'
    if old not in template:
        raise RuntimeError("模板中找不到 payload 注入点（<script id=\"payload\" type=\"application/json\">...</script>）")

    html = template.replace(old, new, 1)
    output_path.write_text(html, encoding="utf-8")
    return output_path


def default_output_path(query_type: str) -> Path:
    """默认输出路径：D:/Downloads/饼干记账_查询_<type>_<YYYYMMDD_HHMMSS>.html"""
    fname = f"饼干记账_查询_{query_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    downloads = Path("D:/Downloads")
    if downloads.exists():
        return downloads / fname
    return Path.cwd() / fname


def main():
    parser = argparse.ArgumentParser(
        description="饼干记账 · HTML 注入器",
        usage="python3 scripts/bill_inject.py <query_type> [args...] [--out <path>]"
    )
    parser.add_argument("query_type", choices=list(QUERY_TYPES.keys()), help="查询类型（CLI 子命令）")
    parser.add_argument("--out", default=None, help="输出 HTML 路径（默认写到 D:/Downloads）")

    # 透传参数：收集 --xxx 形式的 CLI 参数
    args, extra = parser.parse_known_args()
    # 处理 --out 已被透传的可能（用户传 --out 给 record_bill.py 的场景）
    cleaned_extra = []
    skip_next = False
    for i, a in enumerate(extra):
        if skip_next:
            skip_next = False
            continue
        if a == "--out":
            skip_next = True
            continue
        cleaned_extra.append(a)
    extra = cleaned_extra

    print(f"📥 注入查询: {args.query_type}")
    print(f"   CLI 参数: {' '.join(extra) if extra else '(无)'}")

    # 1. 调 CLI 拿 JSON
    cli_json = run_cli_json(args.query_type, extra)
    if cli_json.get("status") == "error":
        print(f"✗ {cli_json.get('message')}", file=sys.stderr)
        sys.exit(1)

    # 2. 包 payload
    payload = build_payload(cli_json, args.query_type, extra)

    # 3. 决定输出路径
    output_path = Path(args.out) if args.out else default_output_path(args.query_type)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 4. 注入模板
    try:
        final = inject_to_template(payload, output_path)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"✗ 注入失败：{e}", file=sys.stderr)
        sys.exit(1)

    print(f"✓ 已生成: {final}")
    print(f"  用浏览器打开即可查看。")
    sys.exit(0)


if __name__ == "__main__":
    main()