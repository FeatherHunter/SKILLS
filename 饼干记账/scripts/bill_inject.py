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

# #300 Base 管线共享层:统一信封 + Base 注入器 + utf-8-sig BOM
from _base_render import (SKILL_NAME, SKILL_VERSION, envelope, error_envelope,
                          inject_base, write_html, bill_summary, bill_rows)

SKILL_DIR = _SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "templates" / "query_view.html"
ANALYSIS_TEMPLATE_PATH = SKILL_DIR / "templates" / "分析" / "analysis_view.html"

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
    # 分析域 25 场景(2026-08-09 实施 · 分析域最大域)
    "yearly": "analysis",
    "week": "analysis",
    "category": "analysis",
    "account": "analysis",
    "ledger": "analysis",
    "structure": "analysis",
    "range_compare": "analysis",
    "yoy": "analysis",
    "cat_compare": "analysis",
    "trend": "analysis",
    "cat_trend": "analysis",
    "top": "analysis",
    "top_freq": "analysis",
    "distribution": "analysis",
    "activity": "analysis",
    "insight": "analysis",
    "anomaly": "analysis",
    "debt_summary": "analysis",
    "reimburse_summary": "analysis",
    "installment_summary": "analysis",
    "refund_summary": "analysis",
}


def cli_path(query_type: str) -> Path:
    return _SCRIPT_DIR / QUERY_DOMAIN.get(query_type, "query") / "cli.py"

# 分析域 25 场景 → 模板(单模板多渲染器 · 隔离契约 templates/分析/)
# breakdown 属查询域(query_view 有完整 renderBreakdown 渲染器;2026-08-13 #300 验收修复:移出分析域回落 query_view)
ANALYSIS_TYPES = {
    "monthly", "yearly", "overview", "week",
    "category", "account", "ledger", "structure",
    "compare", "range_compare", "yoy", "cat_compare",
    "trend", "cat_trend",
    "top", "top_freq", "distribution",
    "stats", "activity", "insight", "anomaly",
    "debt_summary", "reimburse_summary", "installment_summary", "refund_summary",
}


def template_path_for(query_type: str) -> Path:
    """按类型选模板:分析域 → templates/分析/analysis_view.html;其余 → query_view.html"""
    return ANALYSIS_TEMPLATE_PATH if query_type in ANALYSIS_TYPES else TEMPLATE_PATH

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
    # ── 分析域 25 场景(2026-08-09 实施) ──
    "yearly":    {"title": "年度汇总",        "subtitle": "全年 KPI + 逐月趋势 + 大额分类"},
    "week":      {"title": "本周简报",        "subtitle": "本周 KPI + 对比上周 + 大额支出"},
    "category":  {"title": "分类占比",        "subtitle": "SVG 环形图 + 排行(总额/占比/笔数/均值)"},
    "account":   {"title": "账户占比",        "subtitle": "各账户支出/收入/净额"},
    "ledger":    {"title": "账本汇总",        "subtitle": "各账本收支汇总卡 + 占比"},
    "structure": {"title": "收支结构",        "subtitle": "收入来源 + 支出去向双环形"},
    "range_compare": {"title": "双区间对比",  "subtitle": "两段时间双卡 + 变化率 + 分类差异"},
    "yoy":       {"title": "同比对比",        "subtitle": "今年 vs 去年同月"},
    "cat_compare":  {"title": "分类对比",     "subtitle": "两段时间分类差异 TOP"},
    "trend":     {"title": "收支趋势",        "subtitle": "SVG 双线折线 + 峰值 + 月均"},
    "cat_trend": {"title": "分类趋势",        "subtitle": "某分类逐月变化折线/柱状"},
    "top":       {"title": "大额排行",        "subtitle": "支出 TOP N"},
    "top_freq":  {"title": "高频排行",        "subtitle": "分类笔数 TOP"},
    "distribution": {"title": "金额分布",     "subtitle": "SVG 直方图(5 区间)"},
    "activity":  {"title": "记账活跃度",      "subtitle": "周几分布 + 时段分布"},
    "insight":   {"title": "AI 消费洞察",     "subtitle": "洞察生成器事实 + AI 解读"},
    "anomaly":   {"title": "异常波动检测",    "subtitle": "突增月/暴涨分类事实"},
    "debt_summary": {"title": "借贷总览",     "subtitle": "借出/借入未还 + 对象列表"},
    "reimburse_summary": {"title": "报销汇总", "subtitle": "待报销 + 已到账 + 历史"},
    "installment_summary": {"title": "分期总览", "subtitle": "进行中分期卡 + 历史"},
    "refund_summary": {"title": "退款统计",   "subtitle": "退款总额/次数 + 月份分布"},
}

# 模板能力接口(08 §4 硬标准 · 复制数据/复制日志数据源):query_type → 场景标识/唤醒词
# scene_id 对齐 scenes/query.yaml 的场景(基础映射;细粒度由调用方覆盖)
# command_cn 对齐 scenes/{域}.yaml html.command_cn(复制数据 5 段 · 2026-08-09 对抗式审查补齐)
QUERY_META = {
    "summary":   {"scene_id": "query_today",     "wake_word": "查今天", "command_cn": "今日摘要"},
    "list":      {"scene_id": "query_list",      "wake_word": "查日期", "command_cn": "查询记录"},
    "recent":    {"scene_id": "query_recent",    "wake_word": "查最近", "command_cn": "最近记录"},
    "search":    {"scene_id": "query_search",    "wake_word": "搜备注", "command_cn": "备注搜索"},
    "tag":       {"scene_id": "query_tag",       "wake_word": "查标签", "command_cn": "查标签"},
    "debt":      {"scene_id": "query_debt",      "wake_word": "查欠款", "command_cn": "查欠款"},
    "reimburse": {"scene_id": "query_pending_reimburse", "wake_word": "查待报销", "command_cn": "查待报销"},
    "installment": {"scene_id": "query_installment",     "wake_word": "查分期", "command_cn": "查分期"},
    "monthly":   {"scene_id": "monthly_summary", "wake_word": "看月度", "command_cn": "月度汇总"},
    "compare":   {"scene_id": "period_compare",   "wake_word": "看对比", "command_cn": "周期对比"},
    "breakdown": {"scene_id": "category_breakdown", "wake_word": "看分类", "command_cn": "分类明细"},
    "overview":  {"scene_id": "range_overview",   "wake_word": "看总览", "command_cn": "收支总览"},
    "stats":     {"scene_id": "stats",            "wake_word": "做统计", "command_cn": "记账统计"},
    # ── 分析域 25 场景(2026-08-09 实施 · 对齐 scenes/analysis.yaml) ──
    "yearly":    {"scene_id": "yearly_summary",      "wake_word": "看年度", "command_cn": "年度汇总"},
    "week":      {"scene_id": "week_brief",          "wake_word": "看周报", "command_cn": "周报"},
    "category":  {"scene_id": "category_breakdown",  "wake_word": "看分类", "command_cn": "分类占比"},
    "account":   {"scene_id": "account_breakdown",   "wake_word": "看账户", "command_cn": "账户占比"},
    "ledger":    {"scene_id": "ledger_summary",      "wake_word": "看账本", "command_cn": "账本汇总"},
    "structure": {"scene_id": "income_expense_structure", "wake_word": "看结构", "command_cn": "收支结构"},
    "range_compare": {"scene_id": "range_compare",   "wake_word": "看双区间", "command_cn": "双区间对比"},
    "yoy":       {"scene_id": "year_over_year",      "wake_word": "看同比", "command_cn": "同比"},
    "cat_compare":  {"scene_id": "category_compare", "wake_word": "看分类对比", "command_cn": "分类对比"},
    "trend":     {"scene_id": "monthly_trend",       "wake_word": "看趋势", "command_cn": "收支趋势"},
    "cat_trend": {"scene_id": "category_trend",      "wake_word": "看分类趋势", "command_cn": "分类趋势"},
    "top":       {"scene_id": "top_expense",         "wake_word": "看大额", "command_cn": "大额排行"},
    "top_freq":  {"scene_id": "top_frequency",       "wake_word": "看高频", "command_cn": "高频排行"},
    "distribution": {"scene_id": "amount_distribution", "wake_word": "看分布", "command_cn": "金额分布"},
    "activity":  {"scene_id": "activity",            "wake_word": "看活跃", "command_cn": "活跃度"},
    "insight":   {"scene_id": "insight",             "wake_word": "看洞察", "command_cn": "消费洞察"},
    "anomaly":   {"scene_id": "anomaly",             "wake_word": "看异常", "command_cn": "异常检测"},
    "debt_summary":  {"scene_id": "debt_summary",    "wake_word": "看借贷", "command_cn": "借贷总览"},
    "reimburse_summary": {"scene_id": "reimburse_summary", "wake_word": "看报销", "command_cn": "报销汇总"},
    "installment_summary": {"scene_id": "installment_summary", "wake_word": "看分期", "command_cn": "分期总览"},
    "refund_summary": {"scene_id": "refund_summary", "wake_word": "看退款", "command_cn": "退款统计"},
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


def _human_args(query_type: str, extra_args: list) -> str:
    """把 CLI 参数翻译成人话(副标题用,不显示 --xxx 原始参数)

    规则:每个 --flag value 转成中文片段;值本身是人话时直接透传。
    """
    if not extra_args:
        return ""
    labels = {
        "--date": "", "--from": "~", "--to": "",
        "--category": "分类", "--account": "账户", "--ledger": "账本",
        "--tag": "标签", "--target": "对象", "--name": "名目",
        "--limit": "最近", "--days": "近", "--month": "月份",
        "--year": "年份", "--months": "近", "--offset": "偏移",
        "--from1": "区间一", "--to1": "", "--from2": "区间二", "--to2": "",
    }
    values = {"--sort": {"amount_desc": "金额从大到小", "amount_asc": "金额从小到大"},
              "--type": {"expense": "支出", "income": "收入"}}
    out = []
    i = 0
    while i < len(extra_args):
        a = extra_args[i]
        if not a.startswith("--"):
            i += 1
            continue
        val = extra_args[i + 1] if i + 1 < len(extra_args) else ""
        label = labels.get(a, "")
        v = values.get(a, {}).get(val, val)
        if a == "--date":
            out.append(v)
        elif a in ("--from", "--to"):
            out.append(v)
        elif a == "--days":
            out.append(f"近 {v} 天")
        elif a == "--limit":
            out.append(f"最近 {v} 条")
        elif label:
            out.append(f"{label} {v}")
        else:
            out.append(v)
        i += 2
    # 区间:from/to 相邻时拼成 "X ~ Y"
    if "--from" in extra_args and "--to" in extra_args:
        idx_from = extra_args.index("--from")
        idx_to = extra_args.index("--to")
        joined = f"{extra_args[idx_from + 1]} ~ {extra_args[idx_to + 1]}"
        # 从 out 中移除两个孤立日期,替换为拼接
        out = [x for x in out if x not in (extra_args[idx_from + 1], extra_args[idx_to + 1])]
        out.append(joined)
    return " · ".join(x for x in out if x)


def build_payload(cli_json: dict, query_type: str, extra_args: list, ai_note: str = None, chain: str = None) -> dict:
    """把 CLI JSON 包成模板期望的 payload 结构（#300 统一信封 + Base scene.snapshot）

    ai_note: AI 解读文本(看洞察/看异常 · 注入 data.ai_note 供洞察卡渲染,08 §5 双通道)
    chain:   AI 思考链(注入 meta.chain · 复制日志②段数据源)
    """
    meta = QUERY_TYPES.get(query_type, {"title": query_type, "subtitle": ""})
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if cli_json.get("status") == "error":
        return error_envelope(cli_json.get("message", "未知错误"), command_cn=meta["title"])

    data = cli_json.get("data") or {}
    # 注入 type / title / subtitle / generated_at / extra_args / meta(复制数据日志数据源)
    enriched = dict(data)
    enriched["type"] = query_type
    enriched["title"] = meta["title"]
    human = _human_args(query_type, extra_args)
    enriched["subtitle"] = meta["subtitle"] + (f" · {human}" if human else "")
    enriched["generated_at"] = now
    # AI 解读注入(看洞察/看异常:洞察卡数据源 · 08 §5 输出双通道落地)
    if ai_note:
        enriched["ai_note"] = ai_note
    m = QUERY_META.get(query_type, {"scene_id": query_type, "wake_word": query_type})
    # list 变体:按参数细分场景(对齐 scenes/query.yaml · 门禁 A 层 1)
    if query_type == "list" and extra_args:
        m = _list_meta(extra_args)
    enriched["meta"] = {
        "scene_id": m["scene_id"],
        "command_cn": m.get("command_cn", meta["title"] + " 结果"),
        "wake_word": m["wake_word"],
        "occurred_at": now,
        "chain": chain or "(未注入 · AI 可在日志覆盖)",
        "render_cmd": f"bill_inject.py {query_type} {' '.join(extra_args)}".strip(),
        "version": SKILL_VERSION,
    }

    # #300 统一信封:领域数据组织进 scene.snapshot(复制数据【场景名 · 数据快照】)
    sections = []
    records = enriched.get("records") or []
    if records:
        sections.append({"heading": "记录明细", "rows": bill_rows(records)})
    cats = enriched.get("categories") or []
    if cats:
        sections.append({"heading": "分类聚合", "rows": [
            f"{c.get('category', '')} {c.get('total', '')} {c.get('count', '')}笔".strip()
            for c in cats[:15]
        ]})
    envelope(enriched, m["command_cn"], m["wake_word"], m["scene_id"],
             enriched["meta"]["render_cmd"],
             bill_summary(enriched), sections,
             thinking=(chain or None),
             data_structure="biscuit_accountant.db bills 表（只读查询）")

    return {
        "status": cli_json.get("status", "ok"),
        "data": enriched,
        "message": cli_json.get("message", "")
    }


def inject_to_template(payload: dict, output_path: Path, query_type: str = None) -> Path:
    """payload → Base 注入器 → 生成 HTML(分析域 → templates/分析/analysis_view.html · utf-8-sig BOM)"""
    template_path = template_path_for(query_type) if query_type else TEMPLATE_PATH
    if not template_path.exists():
        raise FileNotFoundError(f"模板不存在: {template_path}")

    template = template_path.read_text(encoding="utf-8")
    # Base 注入(3 占位符硬拦截:缺/重复 → 报错;#300 契约)
    html = inject_base(template, payload)
    return write_html(html, output_path)


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
    # 分析域 21 新类型中文文件名(html_paths 公共层不动 · 本域隔离契约内实现)
    ANALYSIS_TYPE_CN = {
        "yearly": "年度汇总", "week": "周报", "category": "分类占比",
        "account": "账户占比", "ledger": "账本汇总", "structure": "收支结构",
        "range_compare": "双区间对比", "yoy": "同比", "cat_compare": "分类对比",
        "trend": "收支趋势", "cat_trend": "分类趋势",
        "top": "大额排行", "top_freq": "高频排行", "distribution": "金额分布",
        "activity": "活跃度", "insight": "消费洞察", "anomaly": "异常检测",
        "debt_summary": "借贷总览", "reimburse_summary": "报销汇总",
        "installment_summary": "分期总览", "refund_summary": "退款统计",
    }
    if query_type in ANALYSIS_TYPE_CN:
        cn = ANALYSIS_TYPE_CN[query_type]
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
        usage="python3 scripts/bill_inject.py <query_type> [args...] [--out <path>] [--ai-note <文本>] [--chain <思考链>]"
    )
    parser.add_argument("query_type", choices=list(QUERY_TYPES.keys()), help="查询类型（CLI 子命令）")
    parser.add_argument("--out", default=None, help="输出 HTML 路径(默认 $DATA_DIR/biscuit_accountant_html/)")
    # AI 解读/思考链注入(08 §5 双通道 · 看洞察/看异常洞察卡 + 复制日志②段)
    parser.add_argument("--ai-note", dest="ai_note", default=None, help="AI 解读文本(洞察卡渲染,如看洞察/看异常)")
    parser.add_argument("--chain", default=None, help="AI 思考链(复制日志②段数据源)")

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
    if args.ai_note:
        print(f"   AI 解读: {args.ai_note[:60]}{'…' if len(args.ai_note) > 60 else ''}")

    # 1. 调 CLI 拿 JSON
    cli_json = run_cli_json(args.query_type, extra)

    # 2. 包 payload(带 AI 解读/思考链)
    payload = build_payload(cli_json, args.query_type, extra,
                            ai_note=args.ai_note, chain=args.chain)

    # 3. 决定输出路径
    output_path = Path(args.out) if args.out else default_output_path(args.query_type, args, extra)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 4. 注入模板（即使 CLI 返回 error 也注入，模板会显示错误卡片）
    try:
        final = inject_to_template(payload, output_path, args.query_type)
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