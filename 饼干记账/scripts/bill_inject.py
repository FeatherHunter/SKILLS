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
import os
import json
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

SKILL_DIR = _SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "query_view.html"

# 查询类型 → 域 CLI(拆分后按域路由,v2.0 隔离契约)
QUERY_DOMAIN = {
    "summary": "query",
    "list": "query",
    "search": "query",
    "recent": "query",
    "monthly": "analysis",
    "compare": "analysis",
    "breakdown": "analysis",
    "overview": "analysis",
    "stats": "analysis",
}


def cli_path(query_type: str) -> Path:
    return _SCRIPT_DIR / QUERY_DOMAIN.get(query_type, "query") / "cli.py"

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

# 模板能力接口(08 §4 硬标准 · 复制数据/复制日志数据源):query_type → 场景标识/唤醒词
# scene_id 对齐 scenes/query.yaml 的场景(基础映射;细粒度由调用方覆盖)
QUERY_META = {
    "summary":   {"scene_id": "query_today",     "wake_word": "查今天"},
    "list":      {"scene_id": "query_list",      "wake_word": "查日期"},
    "recent":    {"scene_id": "query_recent",    "wake_word": "查最近"},
    "search":    {"scene_id": "query_search",    "wake_word": "搜备注"},
    "monthly":   {"scene_id": "monthly_current", "wake_word": "看月度"},
    "compare":   {"scene_id": "compare_month",   "wake_word": "看对比"},
    "breakdown": {"scene_id": "breakdown_current_month", "wake_word": "看分类"},
    "overview":  {"scene_id": "overview_current", "wake_word": "看总览"},
    "stats":     {"scene_id": "stats_long_term", "wake_word": "做统计"},
}

SKILL_VERSION = "2.0"


def run_cli_json(query_type: str, extra_args: list) -> dict:
    """调用 <域>/cli.py <query_type> --json <extra_args>...，解析 JSON 输出"""
    cmd = [sys.executable, str(cli_path(query_type)), query_type, "--json"] + list(extra_args)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
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
    # 注入 type / title / subtitle / generated_at / extra_args / meta(复制数据日志数据源)
    enriched = dict(data)
    enriched["type"] = query_type
    enriched["title"] = meta["title"]
    enriched["subtitle"] = meta["subtitle"] + (f" · 参数: {' '.join(extra_args)}" if extra_args else "")
    enriched["generated_at"] = now
    m = QUERY_META.get(query_type, {"scene_id": query_type, "wake_word": query_type})
    enriched["meta"] = {
        "scene_id": m["scene_id"],
        "command_cn": meta["title"] + " 结果",
        "wake_word": m["wake_word"],
        "occurred_at": now,
        "chain": "(未注入 · AI 可在日志覆盖)",
        "render_cmd": f"bill_inject.py {query_type} {' '.join(extra_args)}".strip(),
        "version": SKILL_VERSION,
    }

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
    # 使用 utf-8-sig 写入 BOM,兼容 Windows 记事本/PowerShell ISE 按 GBK 误判
    output_path.write_text(html, encoding="utf-8-sig")
    return output_path


def default_output_path(query_type: str, args=None) -> Path:
    """默认输出路径(v2.5 同步卡路里 §4.1):
    $DATA_DIR/biscuit_accountant_html/<command_zh>_<TS>[_N].html
    - 中文 command 名由 html_paths.resolve_command_name() 解析
    - list 命令按参数细分(查日期/查范围/查分类)
    """
    from html_paths import html_path, resolve_command_name
    cn = resolve_command_name(query_type, args)
    return html_path(cn)




def main():
    parser = argparse.ArgumentParser(
        description="饼干记账 · HTML 注入器",
        usage="python3 scripts/bill_inject.py <query_type> [args...] [--out <path>]"
    )
    parser.add_argument("query_type", choices=list(QUERY_TYPES.keys()), help="查询类型（CLI 子命令）")
    parser.add_argument("--out", default=None, help="输出 HTML 路径(默认 $DATA_DIR/biscuit_accountant_html/)")

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

    # 2. 包 payload
    payload = build_payload(cli_json, args.query_type, extra)

    # 3. 决定输出路径
    output_path = Path(args.out) if args.out else default_output_path(args.query_type, args)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 4. 注入模板（即使 CLI 返回 error 也注入，模板会显示错误卡片）
    try:
        final = inject_to_template(payload, output_path)
    except (FileNotFoundError, RuntimeError) as e:
        print(f"✗ 注入失败：{e}", file=sys.stderr)
        sys.exit(1)

    if cli_json.get("status") == "error":
        print(f"⚠ 已生成错误页: {final}")
        print(f"  原因: {cli_json.get('message', '未知错误')}")
        sys.exit(0)

    print(f"✓ 已生成: {final}")
    print(f"  用浏览器打开即可查看。")
    sys.exit(0)


if __name__ == "__main__":
    main()