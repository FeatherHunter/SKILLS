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
    "tag": "query",
    "debt": "query",
    "reimburse": "query",
    "installment": "query",
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
    "tag":       {"title": "查标签",          "subtitle": "#tag 命中记录 + 汇总"},
    "debt":      {"title": "查欠款",          "subtitle": "未还借贷聚合(借出/借入)"},
    "reimburse": {"title": "查待报销",        "subtitle": "#待报销 记录 + 总额"},
    "installment": {"title": "查分期",        "subtitle": "#分期 分期卡 + 记录明细"},
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
    "tag":       {"scene_id": "query_tag",       "wake_word": "查标签"},
    "debt":      {"scene_id": "query_debt",      "wake_word": "查欠款"},
    "reimburse": {"scene_id": "query_pending_reimburse", "wake_word": "查待报销"},
    "installment": {"scene_id": "query_installment",     "wake_word": "查分期"},
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


# list 变体 → 场景标识/唤醒词(对齐 scenes/query.yaml 直达式场景;细粒度由调用方覆盖)
LIST_META = {
    "date":      {"scene_id": "query_date",      "wake_word": "查某天", "command_cn": "查某天"},
    "range":     {"scene_id": "query_range",     "wake_word": "查区间", "command_cn": "查区间"},
    "category":  {"scene_id": "query_category",  "wake_word": "查分类", "command_cn": "查分类"},
    "account":   {"scene_id": "query_account",   "wake_word": "查账户", "command_cn": "查账户"},
    "ledger":    {"scene_id": "query_ledger",    "wake_word": "查账本", "command_cn": "查账本"},
    "default":   {"scene_id": "query_list",      "wake_word": "查日期", "command_cn": "查询记录"},
}


def _list_meta(extra_args: list) -> dict:
    """list 参数 → 场景 meta(查某天/查区间/查分类/查账户/查账本)"""
    ex = " ".join(extra_args)
    if "--account" in ex:
        return LIST_META["account"]
    if "--ledger" in ex:
        return LIST_META["ledger"]
    if "--category" in ex:
        return LIST_META["category"]
    if "--from" in ex or "--to" in ex:
        return LIST_META["range"]
    if "--date" in ex:
        return LIST_META["date"]
    return LIST_META["default"]


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
    # list 变体:按参数细分场景(对齐 scenes/query.yaml · 门禁 A 层 1)
    if query_type == "list" and extra_args:
        m = _list_meta(extra_args)
    enriched["meta"] = {
        "scene_id": m["scene_id"],
        "command_cn": m.get("command_cn", meta["title"] + " 结果"),
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


def default_output_path(query_type: str, args=None, extra=None) -> Path:
    """默认输出路径(v2.5 同步卡路里 §4.1):
    $DATA_DIR/biscuit_accountant_html/<command_zh>_<TS>[_N].html
    - 中文 command 名由 html_paths.resolve_command_name() 解析
    - list 命令按参数细分(查日期/查范围/查分类/查账户/查账本)
    """
    from html_paths import html_path, resolve_command_name
    cn = resolve_command_name(query_type, args)
    # 查询域 4 新类型中文文件名(html_paths 公共层不动 · 本域隔离契约内实现)
    NEW_TYPE_CN = {"tag": "查标签", "debt": "查欠款", "reimburse": "查待报销", "installment": "查分期"}
    if query_type in NEW_TYPE_CN:
        cn = NEW_TYPE_CN[query_type]
    # list 变体:解析透传参数(extra)细分中文名(隔离契约内实现,不动 html_paths)
    if query_type == "list" and extra:
        ex = " ".join(extra)
        if "--date" in ex or "--from" in ex:
            if "--from" in ex:
                if "--category" in ex:
                    cn = "查分类区间"
                else:
                    cn = "查区间"
            else:
                cn = "查日期"
        elif "--category" in ex:
            cn = "查分类"
        elif "--account" in ex:
            cn = "查账户"
        elif "--ledger" in ex:
            cn = "查账本"
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
    output_path = Path(args.out) if args.out else default_output_path(args.query_type, args, extra)
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