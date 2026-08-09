#!/usr/bin/env python3
"""
schedule_html_render.py — 日程计划查询的 HTML 渲染器（2026-07-23 新增）

设计原则(来自《预置 HTML+注入数据指导手册》§4 通用架构):
- HTML 不直连数据库 — 数据全由 CLI/调度器注入
- 模板只放在 templates/, 输出副本到指定路径
- JSON 三段式 {status, data, message}
- 所有注入值走 json.dumps,防 XSS(手册 §11)

职责:
  1. 从 schedule_db 拉数据(list_plan_events / get_plans)
  2. 计算派生字段(summary / gap / feishu 状态)
  3. 读 templates/schedule_list_events.html
  4. JSON 注入 + 写副本

被 schedule_cli.py 的两个新子命令调用:
  - render-list-events <日期>
  - render-query-plans <日期1,日期2,...>
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_DIR = SKILL_DIR / "templates"

# 复用 schedule_db 的 DB 配置(不重复定义)
sys.path.insert(0, str(SCRIPT_DIR))


def _normalize_date(d) -> str:
    """复用 schedule_db 的归一化(避免重复维护)"""
    from schedule_db import _normalize_date as _n
    return _n(d)


def _build_summary(events: list[dict], inactive_ids: set) -> dict:
    """派生首屏摘要卡字段"""
    active = [e for e in events if e["id"] not in inactive_ids]
    completed = sum(1 for e in active if e.get("completion") == "已完成")
    completed_late = sum(1 for e in active if e.get("completion") == "已完成(超时)")
    partial = sum(1 for e in active if e.get("completion") == "部分完成")
    unfin = sum(1 for e in active if e.get("completion") == "未完成")
    unfin_force = sum(1 for e in active if e.get("completion") == "未完成(不可抗力)")
    done_count = completed + completed_late + partial  # "算完成了的"广义口径
    unreviewed = sum(1 for e in active if not e.get("completion"))
    unsynced = sum(1 for e in active if not e.get("feishu_event_id"))
    return {
        "total_active": len(active),
        "total_inactive": len(inactive_ids),
        "completed_count": done_count,
        "completed_strict": completed,
        "completed_late": completed_late,
        "partial": partial,
        "unfinished": unfin,
        "unfinished_force": unfin_force,
        "unreviewed_count": unreviewed,
        "unsynced_count": unsynced,
    }


def _hhmm_to_minutes(t: str) -> int:
    """HH:MM → 分钟数(24:00 → 24*60, 跨日边界;其余正常)"""
    if not t:
        return 0
    if t == "24:00":
        return 24 * 60
    h, m = t.split(":")[:2]
    try:
        return int(h) * 60 + int(m)
    except ValueError:
        return 0


def _build_gap(events: list[dict]) -> dict:
    """检测 24h 联合覆盖;只对 active 事件"""
    active = sorted(
        [e for e in events if e.get("is_active") != 0],
        key=lambda e: _hhmm_to_minutes(e.get("time_start") or "00:00"),
    )
    if not active:
        return {"has_gap": False, "gap_count": 0, "first_gap": None}

    gaps = []
    first_start = _hhmm_to_minutes(active[0].get("time_start") or "00:00")
    if first_start > 0:
        gaps.append(("00:00", active[0].get("time_start")))
    for i in range(len(active) - 1):
        prev_end = _hhmm_to_minutes(active[i].get("time_end") or "00:00")
        next_start = _hhmm_to_minutes(active[i + 1].get("time_start") or "00:00")
        if next_start > prev_end:
            gaps.append((active[i].get("time_end"), active[i + 1].get("time_start")))

    last_end = _hhmm_to_minutes(active[-1].get("time_end") or "00:00")
    if last_end < 24 * 60:
        gaps.append((active[-1].get("time_end"), "24:00"))

    return {
        "has_gap": len(gaps) > 0,
        "gap_count": len(gaps),
        "first_gap": f"{gaps[0][0]} → {gaps[0][1]}" if gaps else None,
        "all_gaps": [f"{a} → {b}" for a, b in gaps],
    }


def _safe_iso_or_empty(dt) -> str:
    try:
        if dt:
            return str(dt)
    except Exception:
        pass
    return ""


def render_list_events(date: str, *, include_inactive: bool = True) -> dict:
    """
    为指定日期生成 HTML 渲染数据(对应 list-events 模式)。
    返回 {status, data, message} 三段式 dict,data 可直接 JSON 注入。
    """
    from schedule_db import list_plan_events

    date = _normalize_date(date)
    active = list_plan_events(date, include_inactive=False)
    all_events = list_plan_events(date, include_inactive=True) if include_inactive else active

    inactive_ids = {e["id"] for e in all_events if e.get("is_active") == 0}
    # 默认按 time_start 排序,等同 list-events 的原行为
    all_events.sort(key=lambda e: (e.get("time_start") or ""))

    summary = _build_summary(all_events, inactive_ids)
    gap = _build_gap(all_events)

    feishu = _get_feishu_summary()

    data = {
        "meta": {
            "mode": "list-events",
            "date": date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "include_inactive": include_inactive,
        },
        "summary": summary,
        "events": all_events,
        "gap": gap,
        "feishu": feishu,
        "inactive": [e for e in all_events if e.get("is_active") == 0],
        "copy_prompt": _build_list_events_copy_prompt(date, all_events),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": data,
        "message": f"✓ {date} 日程 HTML 渲染数据已生成({summary['total_active']} 活跃 + {summary['total_inactive']} 停用)",
    }


def render_query_plans(dates_raw: str) -> dict:
    """
    为 1 个或多个日期生成 24h 聚合视图的 HTML 渲染数据(对应 query-plans 模式)。
    dates_raw: 逗号分隔日期字符串
    """
    from schedule_db import list_plan_events

    dates = [_normalize_date(d) for d in dates_raw.split(",") if d.strip()]
    if not dates:
        return {
            "status": "error",
            "data": None,
            "message": "至少需要一个日期(逗号分隔)",
        }

    days = []
    all_events_flat = []  # 平铺,让模板可用统一 events 数组渲染
    total_active = 0
    total_inactive = 0
    total_unsynced = 0
    total_unreviewed = 0
    total_completed = 0

    for d in dates:
        all_e = list_plan_events(d, include_inactive=True)
        all_e.sort(key=lambda e: (e.get("time_start") or ""))
        inactive_ids = {e["id"] for e in all_e if e.get("is_active") == 0}
        active = [e for e in all_e if e.get("is_active") != 0]
        s = _build_summary(all_e, inactive_ids)
        g = _build_gap(all_e)
        days.append({
            "date": d,
            "summary": s,
            "gap": g,
            "events": all_e,
            "inactive": [e for e in all_e if e.get("is_active") == 0],
        })
        all_events_flat.extend(all_e)
        total_active += s["total_active"]
        total_inactive += s["total_inactive"]
        total_unsynced += s["unsynced_count"]
        total_unreviewed += s["unreviewed_count"]
        total_completed += s["completed_count"]

    feishu = _get_feishu_summary()

    data = {
        "meta": {
            "mode": "query-plans",
            "dates": dates,
            "date_count": len(dates),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "summary": {
            "total_active": total_active,
            "total_inactive": total_inactive,
            "completed_count": total_completed,
            "unreviewed_count": total_unreviewed,
            "unsynced_count": total_unsynced,
        },
        "days": days,
        "events": all_events_flat,  # 平铺,模板 events.length 可用
        "feishu": feishu,
        "errors": [],
    }
    return {
        "status": "ok",
        "data": data,
        "message": f"✓ {len(dates)} 日查询 HTML 渲染数据已生成(共 {total_active} 活跃)",
    }


def _get_feishu_summary() -> dict:
    """探测飞书可用度(三档),失败降级,不抛异常"""
    try:
        from feishu_sync import is_feishu_available
        st = is_feishu_available()
        return {
            "tier": st.tier,
            "cli_installed": st.cli_installed,
            "authenticated": st.authenticated,
            "calendar_writable": st.calendar_writable,
            "last_error": st.last_error,
        }
    except Exception as e:
        return {"tier": "unknown", "last_error": str(e)}


def inject_into_template(template_name: str, payload: dict, output_path: Path) -> Path:
    """
    读模板 → JSON 注入 → CSS/JS inline → 写单文件副本。

    第一性:HTML 自称"单文件自包含,无外部依赖"(offline banner 文案)。
    旧实现把 _record_styles.css / _record_engine.js 复制到输出目录 —
    在 Chrome 本地 file:// 协议下能用,但飞书/邮件消息预览/移动浏览器拿到
    的 HTML 没有伴随 CSS/JS 文件 → JS 失败 → "加载中..." + 空白页面。

    新实现:inline CSS/JS 进 HTML,真正做到单文件可分享。

    严格遵循手册 §8:生成副本,不污染原模板。
    """
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"模板不存在: {template_path}")

    template_text = template_path.read_text(encoding="utf-8")
    payload_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_str = payload_str.replace("</", "<\\/")

    anchor = '<script id="payload" type="application/json">'
    if anchor not in template_text:
        raise RuntimeError(
            f"模板 {template_name} 缺少 {anchor} 锚点"
        )

    # 找到锚点位置,把锚点开始到 </script> 结束 整段替换为「锚点 + payload + </script>」
    close_tag = "</script>"
    start_idx = template_text.find(anchor)
    end_idx = template_text.find(close_tag, start_idx)
    if end_idx < 0:
        raise RuntimeError(f"模板 {template_name} 缺少 {close_tag} 闭合")
    end_idx += len(close_tag)  # 包含 </script>

    head = template_text[:start_idx]
    tail = template_text[end_idx:]
    injected = head + anchor + payload_str + close_tag + tail

    # {{ 占位符替换
    title = title_for_mode(payload.get("data", {}).get("meta", {}))
    injected = injected.replace("{{ title }}", title).replace("{{ TITLE }}", title)
    injected = injected.replace("{{ template_name }}", template_name)

    # === v1.2.0 第一性 inline CSS/JS ===
    # 模板里 <link rel="stylesheet" href="_record_styles.css"> →
    # 内联 CSS 进 <style> 块
    css_link = '<link rel="stylesheet" href="_record_styles.css">'
    if css_link in injected:
        css_text = (TEMPLATE_DIR / "_record_styles.css").read_text(encoding="utf-8")
        injected = injected.replace(
            css_link,
            "<style>\n" + css_text + "\n</style>"
        )

    # 模板里 <script src="_record_engine.js"></script> →
    # 内联 JS 进 <script> 块
    js_src = '<script src="_record_engine.js"></script>'
    if js_src in injected:
        js_text = (TEMPLATE_DIR / "_record_engine.js").read_text(encoding="utf-8")
        # 与 payload 同款转义(2026-08-09 对抗式复查):内联 JS 若含 </script>
        # 字面量(注释/字符串)会被 HTML 解析器提前截断 script 块。
        # JS 字符串里 \/ === /,零语义影响。
        js_text = js_text.replace("</", "<\\/")
        injected = injected.replace(
            js_src,
            "<script>\n" + js_text + "\n</script>"
        )

    # 模板里 <script src="_copy_prompt_helper.js"></script> →
    # 内联共享复制 prompt helper(ADR-0002 Q6 · _record_engine.js + schedule_list_events.html 共用)
    helper_src = '<script src="_copy_prompt_helper.js"></script>'
    if helper_src in injected:
        helper_text = (TEMPLATE_DIR / "_copy_prompt_helper.js").read_text(encoding="utf-8")
        helper_text = helper_text.replace("</", "<\\/")  # 同款转义,防 </script> 字面量截断
        injected = injected.replace(
            helper_src,
            "<script>\n" + helper_text + "\n</script>"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(injected, encoding="utf-8")

    return output_path


# ===== 路径常量:统一 DB 基目录(get_db_base_dir · Q6 链,plan/list + plan/query 也走这里)=====


# === 中文 command 名映射(ADR-0002 Q5 · 总纲 §04 原则 12.A)===
# 15 模板英文 command → 中文 command 名(help 域已对齐,不在此映射)
# 用于 `_naming_path` 输出文件名:`<中文 command>_<YYYYMMDD>_<HHMMSS>[_<N>].html`
# Issue 02(expand):映射表建立,英文调用方仍可工作(fallback)
# Issue 07(contract):英文 fallback 移除,只接受中文 command 名
#
# 4 域分组(ADR-0003 Q7 · 为将来拆模块 record_cli/plan_cli/receipt_cli/help_render 打基础):
# === record 域(6) === 报告型 HTML,回顾性输入(schedule_records) — day/range/compare/category/anomaly/detail
# === plan 域(3) === 过程型 HTML,预测性输入(schedule_plans) — list/preview/review
# === receipt 域(5) === 回执型 HTML,CRUD 后视觉反馈(record+plan 域共享) — record-receipt×2 + plan-receipt×3
# === 跨域 域(1) === Phase E · 复盘 start-end · dual-domain 分析(record + plan 跨域 review + AI 洞察)
# === help 域(N/A) === HELP 中心(help_render.py 独立映射,不在此处)
CN_COMMAND_MAP = {
    # === record 域(6) === 报告型:day/range/compare/category/anomaly/detail ===
    "record_day":          "查作息记录",
    "record_range":        "查作息区间",
    "record_compare":      "查作息对比",
    "record_category":     "查作息类别",
    "record_anomaly":      "查作息异常",
    "record_detail":       "作息详情",
    # === plan 域(3) === 过程型:list/preview/review ===
    "plan_list":           "查日程",
    "plan_preview":        "商量计划预览",
    "plan_review":         "复盘",
    # === receipt 域(5) === 回执型:record-receipt×2 + plan-receipt×3 ===
    "record_receipt":      "记作息回执",
    "record_receipt_edit": "修正作息回执",
    # === 结果域(1) === 记录三件套结果 HTML(T2 · 2026-08-09 升级 add 回执链路 · G1-A1)
    "record_result":       "记作息结果",
    "plan_receipt":        "改日程回执",
    "plan_receipt_add":    "补日程回执",
    "plan_receipt_write":  "写日程回执",
    # === 跨域 域(1) === Phase E · 复盘 start-end · 跨 record+plan 双域分析报告 ===
    # 注意:与 plan_review("复盘") 在"复盘"语义同源,但产品边界严格区分:
    #   plan_review = 单日 plan 域 completion 写库
    #   replay      = 任意区间 dual-domain 分析报告(record + plan + 跨域 + AI)
    # 中文 command 名 = "区间复盘"(避免 _naming_path 重复映射),详见 .scratch/replay-start-end/spec.md
    "replay":              "区间复盘",
}


def _html_base_dir() -> Path:
    """延迟求值,避免模块加载时 DB 基目录还不存在导致 RECORD_DIR 永久冻结为空"""
    from schedule_db import get_db_base_dir
    return get_db_base_dir() / 'schedule_html'


def _naming_path(command: str, subdir: str = "") -> Path:
    """按《预置 HTML+注入数据指导手册》§4.1 生成命名合规路径。

    格式: <command>_<YYYYMMDD>_<HHMMSS>[_<N>].html(ADR-0002 Q5 · 总纲 §04 原则 12.A)
    子目录(如 "record/day", "plan/receipt")会自动 mkdir -p。
    冲突保护:文件已存在时自动追加 _2/_3/...(同秒多次生成不覆盖)。

    命名合规动机:避免同一天 receipt 多次生成覆盖前一份(数据丢失风险);
    跨 SKILL 一致(手册里 memo_query_20260724_103045.html 也是这个格式)。

    Q5 Contract(Issue 07):若传入的 command 是 CN_COMMAND_MAP 的英文 key,
    抛 ValueError 提示改用中文。防止 caller 忘记映射、产生旧英文命名残留。
    不在 CN_COMMAND_MAP 里的 command(如 "unknown" / 自定义测试用)仍接受。

    Args:
        command: 中文 command 名(查作息记录 / 查日程 / 复盘 等);传 CN_COMMAND_MAP
                 的英文 key(record_day 等)会抛 ValueError。
        subdir: 在 _html_base_dir() 下的子目录,可空(用 "/" 分隔多级)。
                pid/rid/action/date 等语义信息不再放 filename 里(避免暴露隐私);
                这些信息保留在 payload data.meta 里。

    Returns:
        完整的绝对路径,且保证父目录存在。
    """
    # Q5 Contract(Issue 07):英文 command 名(在 CN_COMMAND_MAP 里)→ 报错
    if command in CN_COMMAND_MAP:
        raise ValueError(
            f"字段 _naming_path(command=...):当前值 '{command}' 是英文 command 名,"
            f"ADR-0002 Q5 已迁移到中文命名,期望值 '{CN_COMMAND_MAP[command]}',"
            f"修复建议: 改用 _naming_path(CN_COMMAND_MAP['{command}'], ...) 或直接传中文字面量"
        )

    base = _html_base_dir()
    if subdir:
        base = base.joinpath(*subdir.split("/"))
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = base / f"{command}_{stamp}.html"
    if not target.exists():
        return target
    # 冲突保护:追加 _2/_3/...
    n = 2
    while n < 1000:
        candidate = base / f"{command}_{stamp}_{n}.html"
        if not candidate.exists():
            return candidate
        n += 1
    raise RuntimeError(f"冲突保护超过 1000 次:{command}_{stamp}")

def _record_dir() -> Path:
    return _html_base_dir() / 'record'


def default_output_path(meta: dict) -> Path:
    """
    按手册 §4.1 命名合规生成默认输出路径。
    命名格式:<中文 command>_<YYYYMMDD>_<HHMMSS>[_<N>].html(ADR-0002 Q5)

    ADR-0003 Q7 · 4 域分组(为将来拆模块打基础):
      === record 域(6 mode)=== 报告型:day/range/compare/category/anomaly/detail → 委托 record_output_path()
      === plan 域(3 mode)=== 过程型:list/preview/review → plan/list | plan/query
      === receipt 域(5 mode)=== 回执型:record-receipt×2 + plan-receipt×3 → 由 record_output_path 处理
      === 跨域 域(1 mode)=== Phase E · 复盘 start-end · dual-domain 分析 · replay/
      === help 域 === → 由 help_render.py 独立处理,不在此处

    pid/rid/action/date 等语义信息保留在 payload data.meta 里,
    filename 的唯一职责是跨 SKILL 一致 + 同秒冲突保护。
    """
    mode = meta.get("mode", "list-events")

    if mode.startswith("record-"):
        return record_output_path(mode, meta)

    # === 跨域 域(1 mode · Phase E · 复盘 start-end · dual-domain 分析 · 独立 subdir)===
    if mode == "replay":
        return _naming_path(CN_COMMAND_MAP["replay"], "replay")

    # === plan 域(3 mode · ADR-0002 Q5 中文 command 名 · ADR-0003 Q7 分组)===
    if mode == "list-events":
        return _naming_path(CN_COMMAND_MAP["plan_list"], "plan/list")
    if mode == "query-plans":
        # query-plans 与 list-events 共享 查日程 命名(同模板,同唤醒词族)
        return _naming_path(CN_COMMAND_MAP["plan_list"], "plan/query")
    if mode == "plan-preview":
        return _naming_path(CN_COMMAND_MAP["plan_preview"], "plan/list")
    if mode == "plan-review":
        return _naming_path(CN_COMMAND_MAP["plan_review"], "plan/list")
    # === receipt 域(plan-receipt 3 款 · 回执型,与 plan 域共享子目录)===
    if mode == "plan-receipt":
        return _naming_path(CN_COMMAND_MAP["plan_receipt"], "plan/receipt")
    if mode == "plan-receipt-add":
        return _naming_path(CN_COMMAND_MAP["plan_receipt_add"], "plan/receipt")
    if mode == "plan-receipt-write":
        return _naming_path(CN_COMMAND_MAP["plan_receipt_write"], "plan/receipt")
    return _naming_path("unknown")


# 5 模板目录映射 — M10 改用 record_output_path(meta) 自动派生,不再需要独立字典
# (旧 _RECORD_TEMPLATE_DIRS 已删除)


def record_output_path(mode: str, meta: dict = None) -> Path:
    """按手册 §4.1 命名合规(<中文 command>_<YYYYMMDD>_<HHMMSS>[_<N>].html)生成路径。

    ADR-0002 Q5:全部 record/receipt 域 mode 输出中文 command 名。
    ADR-0003 Q7 · 4 域分组(为将来拆模块打基础):
      === record 域(6 mode)=== 报告型:day/range/compare/category/anomaly/detail(record-report 等价 record-day)
      === receipt 域(5 mode)=== 回执型:record-receipt×2 + plan-receipt×3(与 plan 域共享子目录约定)

    pid/rid/action/date 等语义信息不再放 filename(避免暴露隐私 +
    避免信息冗余),这些信息保留在 payload data.meta 里。
    filename 的唯一职责是跨 SKILL 一致的命名 + 同秒冲突保护。
    """
    meta = meta or {}  # noqa  # 保留参数以便未来 meta 路径命名复用

    # === record 域(6 mode · 报告型 · ADR-0002 Q5 中文 command 名)===
    if mode == "record-day":
        return _naming_path(CN_COMMAND_MAP["record_day"], "record/day")
    if mode == "record-range":
        return _naming_path(CN_COMMAND_MAP["record_range"], "record/range")
    if mode == "record-compare":
        return _naming_path(CN_COMMAND_MAP["record_compare"], "record/compare")
    if mode == "record-category":
        return _naming_path(CN_COMMAND_MAP["record_category"], "record/category")
    if mode == "record-anomaly":
        return _naming_path(CN_COMMAND_MAP["record_anomaly"], "record/anomaly")
    if mode == "record-report":
        # 兼容旧 CLI,等价 record-day(中文 command 同)
        return _naming_path(CN_COMMAND_MAP["record_day"], "record/day")
    if mode == "record-detail":
        return _naming_path(CN_COMMAND_MAP["record_detail"], "record/detail")
    # === 跨域 域(1 mode · Phase E · 复盘 start-end · dual-domain 分析)===
    if mode == "replay":
        return _naming_path(CN_COMMAND_MAP["replay"], "replay")
    # === receipt 域(5 mode · 回执型 · record+plan 共享)===
    if mode == "record-receipt":
        return _naming_path(CN_COMMAND_MAP["record_receipt"], "record/receipt")
    if mode == "record-receipt-edit":
        return _naming_path(CN_COMMAND_MAP["record_receipt_edit"], "record/receipt")
    # === 结果域(1 mode · T2 · 记录三件套结果 HTML · 独立 subdir record/result)===
    if mode == "record-result":
        return _naming_path(CN_COMMAND_MAP["record_result"], "record/result")
    if mode == "plan-receipt":
        # plan-receipt 也走此函数(向后兼容),实际由 plan_receipt 中文映射处理
        return _naming_path(CN_COMMAND_MAP["plan_receipt"], "plan/receipt")
    return _naming_path("unknown")


def title_for_mode(meta: dict) -> str:
    """为模板 title 生成对应文案(替换 {{title}} 占位符)"""
    mode = meta.get("mode", "list-events")
    if mode == "list-events":
        d = meta.get("date", "")
        return f"日程计划 · {d}"
    if mode == "query-plans":
        dates = meta.get("dates", [])
        if len(dates) == 1:
            return f"日程计划 · {dates[0]}"
        if len(dates) >= 2:
            return f"日程计划 · {dates[0]} ~ {dates[-1]} ({len(dates)} 日)"
        return "日程计划"
    if mode == "record-report":
        d = meta.get("date", "")
        from datetime import date as _dt
        try:
            dt = _dt.fromisoformat(d)
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            return f"作息报告 · {dt.year}年{dt.month}月{dt.day}日（{weekdays[dt.weekday()]}）"
        except Exception:
            return f"作息报告 · {d}"
    # record 域 5 mode(2026-07-24 补:之前全部 fallback 到"作息管家",用户看不到 mode 标识)
    if mode == "record-day":
        d = meta.get("date", "")
        return f"作息记录 · 单日报告 · {d}" if d else "作息记录 · 单日报告"
    if mode == "record-range":
        s, e = meta.get("start", ""), meta.get("end", "")
        return f"作息记录 · 区间报告 · {s}~{e}" if s and e else "作息记录 · 区间报告"
    if mode == "record-compare":
        la = meta.get("label_a", "A")
        lb = meta.get("label_b", "B")
        return f"作息对比 · {la} vs {lb}"
    if mode == "record-category":
        cat = meta.get("category", "")
        s, e = meta.get("start", ""), meta.get("end", "")
        return f"作息深挖 · {cat} · {s}~{e}" if s and e else f"作息深挖 · {cat}"
    if mode == "record-anomaly":
        return f"作息异常检测 · 最近 {meta.get('window', 7)} 天"
    if mode == "record-result":
        d = meta.get("date", "")
        return f"记录结果 · {d}" if d else "记录结果"
    return "作息管家"


# ===== 历史 4 段视觉复刻(沿用 _render_report_2026-07-02.py:38-43)=====
EMOJI_MAP = {
    "睡眠": "😴", "工作": "💼", "学习": "📚", "运动": "🏋️",
    "通勤": "🚴", "餐饮": "🍽️", "娱乐": "🎮", "社交": "💕",
    "休闲": "🛋️", "健康": "🏥", "洗漱": "🚿", "兴趣爱好": "🎨",
    "家务": "🧹", "未知": "❓", "休息": "📌", "起居": "🪥", "计划": "📋",
    "维持": "🌱", "维持.睡眠": "🌱",
    "饮食记录": "🍽️", "做饭": "🍳", "饮食": "🍽️", "采购": "🛒",
    "就医": "💊", "护肤": "💆",
    "修行": "🧘", "冥想": "🧠", "看病": "🩺", "康复": "🩹", "保健": "🛡️", "八段锦": "☯️",
    "AI调优": "🤖", "开发": "💻", "剪辑": "🎬", "文案": "📝",
    "运营": "📊", "会议": "🤝", "财务": "💰", "调研": "🔍",
    "技术": "💻", "语言": "🗣️", "考试": "✏️", "读书": "📕",
    "研究": "🔬", "AI": "🤖", "阅读": "📰",
    "文字": "✍️", "视频": "🎥", "音频": "🎵", "设计": "🖌️",
    "编程": "💻", "菜谱": "🍴", "SOP": "📋", "教学": "👨‍🏫",
    "家人": "👨‍👩‍👧", "朋友": "🧑‍🤝‍🧑", "同事": "👔", "伴侣": "❤️",
    "宠物": "🐾", "社交/服务": "👋",
    "游戏": "🎮", "视频/追剧": "📺", "音乐": "🎧", "手机": "📱",
    "玩耍": "🎈", "发呆": "💭", "散步": "🚶", "午睡": "😴",
    "过渡": "⏳", "休息/娱乐": "📰",
    "代办": "☑️", "决策": "🤔", "杂事": "🔧", "收拾": "🧹",
    "行政": "📑", "等候": "⏳", "园艺": "🌿",
    "健身": "🏋️", "通勤/回家": "🚴",
    "维持/通勤": "🚴", "学习/研究": "🔬",
}

COLOR_MAP = {
    "睡眠": "#5E5CE6", "工作": "#007AFF", "学习": "#34C759", "运动": "#FF9500",
    "通勤": "#64D2FF", "餐饮": "#FF9F0A", "娱乐": "#AF52DE", "社交": "#FF2D55",
    "休闲": "#30D158", "健康": "#FF3B30", "洗漱": "#5AC8FA", "兴趣爱好": "#BF8F5F",
    "家务": "#A2845E", "未知": "#8E8E93", "休息": "#8E8E93", "起居": "#8E8E93", "计划": "#FF6B9D",
    "维持": "#5E5CE6",
    "做饭": "#FF9F0A", "饮食": "#FF9F0A", "采购": "#FF9F0A",
    "就医": "#FF3B30", "护肤": "#FF3B30",
    "出行": "#64D2FF",
    "健身": "#FF9500", "修行": "#FF9500", "冥想": "#FF9500",
    "AI调优": "#007AFF", "开发": "#007AFF", "技术": "#007AFF",
    "散步": "#34C759", "午睡": "#5E5CE6",
    "游戏": "#AF52DE", "手机": "#AF52DE",
    "代办": "#A2845E", "杂事": "#A2845E", "收拾": "#A2845E", "行政": "#A2845E",
}


def _cat_emoji(cat: str) -> str:
    """返回分类 emoji — 委托 calculations.cat_emoji(共享 validators LEVEL2 全 69 二级,2026-07-25 重构)。"""
    from calculations import cat_emoji as _ce
    return _ce(cat)


def _cat_color(cat: str) -> str:
    return COLOR_MAP.get(cat, "#8E8E93")


def _to_min(hhmm: str) -> int:
    """HH:MM → 分钟数(24:00 → 24*60,跨日边界;其余正常)"""
    if not hhmm:
        return 0
    if hhmm == "24:00":
        return 24 * 60
    h, m = hhmm.split(":")[:2]
    try:
        return int(h) * 60 + int(m)
    except ValueError:
        return 0


def _fmt_dur(mins: int) -> str:
    if mins <= 0:
        return "0分钟"
    h = mins // 60
    m = mins % 60
    if h and m:
        return f"{h}小时{m}分钟"
    if h:
        return f"{h}小时"
    return f"{m}分钟"


def _fmt_dur_short(mins: int) -> str:
    """时间轴 tooltip 用:6h40m 这种短格式"""
    h = mins // 60
    m = mins % 60
    if h and m:
        return f"{h}h{m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def _build_full_records(records: list) -> list:
    """
    100% 字段暴露原则:把 schedule_records 原始行映射为 11 字段 dict 列表。
    11 字段:id / date / time_start / time_end / duration_minutes / activity /
    category / source_contents / source_timestamps / analysis_reasoning / created_at。
    上层(HTML 模板) 自行决定消费哪些、是否折叠、什么样式。
    """
    return [
        {
            "id": r["id"],
            "date": r["date"],
            "time_start": r["time_start"],
            "time_end": r["time_end"],
            "duration_minutes": int(r.get("duration_minutes") or 0),
            "activity": r["activity"],
            "category": r["category"],
            "source_contents": r.get("source_contents") or "",
            "source_timestamps": r.get("source_timestamps") or "",
            "analysis_reasoning": r.get("analysis_reasoning") or "",
            "created_at": r.get("created_at") or "",
        }
        for r in records
    ]


# === ADR-0002 Q6 · copy_prompt 单 map + CopyPromptContext dataclass ===
# 替代原 SCENE/EXPECT/SOURCE 三平行 dict(B3 Repeated Switches smell)
# + 替代原 (mode, meta, records, summary_items, extra_data) 多参签名(B4 Data Clumps smell)
#
# 第一性:加新 mode 只需在 _COPY_PROMPT_PARTS 加一个 entry,不用动函数体
# 调用方不再需要往 meta 塞 date/total_minutes(原 B4 meta 污染问题)
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class CopyPromptContext:
    """copy_prompt 渲染上下文(ADR-0002 Q6 · B4 修复)

    把原 (mode, meta, records, summary_items, extra_data) 多参打包成一个 dataclass,
    调用方语义清晰(「喂 copy_prompt 用」),不再污染 meta。

    字段说明:
      mode: record-day / record-range / record-compare / record-category / record-anomaly / record-detail
      date: 主日期(单日/区间起始/详情当天)
      total_minutes: 主时长分钟数
      records: 该 HTML 包含的 schedule_records 行(用于摘要 + 详情溯源)
      summary_items: 分类摘要(可选,day/range/compare/category 有)
      extra_data: 模式特有数据(可选,anomaly: anomalies / 其他: health 等)
      range_start / range_end: 区间 mode(start/end 替代 date)
      label_a / label_b: compare mode 的对比双方标签
      category_name: category mode 的类别名
      window_days: anomaly mode 的窗口天数
    """
    mode: str
    date: str = ""
    total_minutes: int = 0
    records: List[Dict[str, Any]] = field(default_factory=list)
    summary_items: List[Dict[str, Any]] = field(default_factory=list)
    extra_data: Dict[str, Any] = field(default_factory=dict)
    range_start: str = ""
    range_end: str = ""
    label_a: str = ""
    label_b: str = ""
    category_name: str = ""
    window_days: int = 7


# 6 个 record mode × {scene, expect, source} 三个字符串模板(B3 单 map 替代三平行 dict)
# 加新 mode:只需在此加一个 entry,函数体不动
_COPY_PROMPT_PARTS = {
    "record-day": {
        "scene":  "查看了 {date} 单日作息报告(共 {n_records} 条记录,总时长 {total_dur})",
        "expect": "基于今日数据,可调 schedule_cli.py render-record-day {date} 重渲,"
                  "或调 render-plans-review 复盘今日 plan 执行情况",
        "source": "record_day.html 生成于 {generated_at},数据来自 schedule_records WHERE date={date}",
    },
    "record-range": {
        "scene":  "查看了 {range_start} 至 {range_end} 区间作息报告"
                  "(共 {n_records} 条记录,总时长 {total_dur})",
        "expect": "可对区间内某天做单日深挖(render-record-day),"
                  "或对比另一段时段(render-record-compare)",
        "source": "record_range.html 生成于 {generated_at},数据来自 schedule_records "
                  "WHERE date BETWEEN {range_start} AND {range_end}",
    },
    "record-compare": {
        "scene":  "对比查看了 {label_a}({range_start}) vs {label_b}({range_end}) 两段作息",
        "expect": "可深挖差异最大的类别(render-record-category-range),"
                  "或对其中一段做异常检测(render-record-anomaly)",
        "source": "record_compare.html 生成于 {generated_at},数据来自两段 schedule_records 区间",
    },
    "record-category": {
        "scene":  "深挖了类别「{category_name}」在 {range_start} 至 {range_end} 的分布",
        "expect": "可深挖另一类别做对比,或对该类别做单日时间块分析",
        "source": "record_category.html 生成于 {generated_at},"
                  "数据来自 schedule_records WHERE category LIKE '{category_name}%'",
    },
    "record-anomaly": {
        "scene":  "查看了最近 {window_days} 天作息异常检测"
                  "({n_anomalies} 项异常)",
        "expect": "针对红色异常,可调 amend-record 修正历史记录,"
                  "或调 render-plans-preview 规划调整方案",
        "source": "record_anomaly.html 生成于 {generated_at},"
                  "数据来自最近 {window_days} 天 schedule_records",
    },
    "record-detail": {
        "scene":  "查看了 {date} 作息详情(全 11 字段溯源,{n_records} 条记录)",
        "expect": "可调 amend-record <id> 修正某条记录,"
                  "或调 render-record-day 生成单日报告",
        "source": "record_detail.html 生成于 {generated_at},数据来自 schedule_records WHERE date={date}",
    },
}


def _build_record_copy_prompt(ctx_or_mode, meta=None, records=None,
                              summary_items=None, extra_data=None) -> str:
    """构造 4 部分 copy prompt(record 域 6 模板共享 · ADR-0002 Q6 · 总纲 §04 原则 10)

    支持两种签名(向后兼容):
      1. 新签名: _build_record_copy_prompt(CopyPromptContext(...))
      2. 旧签名: _build_record_copy_prompt(mode, meta, records, summary_items, extra_data)
         (deprecated · 由 render_record_* 调用方迁移到 CopyPromptContext)

    4 部分结构(原则 10):
      ① 场景: 用户在 HTML 中做了什么
      ② 数据: 用户看到的最终数据(分类摘要 / 时长 / 健康分 / 关键事件)
      ③ 期望: AI 应执行什么 CLI 操作
      ④ 来源: HTML 数据来自哪个 CLI + 时间
    """
    # === 签名分发(向后兼容) ===
    # 新签名:CopyPromptContext dataclass
    if isinstance(ctx_or_mode, CopyPromptContext):
        ctx = ctx_or_mode
    else:
        # 旧签名:拆 (mode, meta, records, summary_items, extra_data)
        # 提取 _COPY_PROMPT_PARTS 需要的字段(不污染 meta)
        mode = ctx_or_mode
        records = records or []
        summary_items = summary_items or []
        extra_data = extra_data or {}
        ctx = CopyPromptContext(
            mode=mode,
            date=(meta or {}).get("date", ""),
            total_minutes=int((meta or {}).get("total_minutes") or 0),
            records=records,
            summary_items=summary_items,
            extra_data=extra_data,
            range_start=(meta or {}).get("start", (meta or {}).get("date", "")),
            range_end=(meta or {}).get("end", ""),
            label_a=(meta or {}).get("label_a", "A"),
            label_b=(meta or {}).get("label_b", "B"),
            category_name=(meta or {}).get("category", ""),
            window_days=int((meta or {}).get("window", 7)),
        )

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = _COPY_PROMPT_PARTS.get(ctx.mode, {
        "scene": "查看了作息报告({mode})".format(mode=ctx.mode),
        "expect": "根据报告内容决定后续 CLI 操作",
        "source": f"生成于 {generated_at}",
    })

    # === 字段填充 ===
    fill = {
        "date":         ctx.date,
        "range_start":  ctx.range_start or ctx.date,
        "range_end":    ctx.range_end or ctx.date,
        "label_a":      ctx.label_a or "A",
        "label_b":      ctx.label_b or "B",
        "category_name":ctx.category_name,
        "window_days":  ctx.window_days,
        "n_records":    len(ctx.records),
        "n_anomalies":  len(ctx.extra_data.get("anomalies", [])),
        "total_dur":    _fmt_dur(ctx.total_minutes),
        "generated_at": generated_at,
    }
    scene  = parts["scene"].format(**fill)
    expect = parts["expect"]
    source = parts["source"].format(**fill)

    # === ② 数据:分类摘要 top 3 + 健康分(如有) + 异常计数 ===
    cat_lines = ""
    if ctx.summary_items:
        top3 = ctx.summary_items[:3]
        cat_lines = "\n".join(
            f"  - {s.get('emoji', '')} {s['category']}:{_fmt_dur(s['total_minutes'])}({s.get('pct', 0)}%)"
            for s in top3
        )
    health = ctx.extra_data.get("health") or {}
    health_line = f"\n健康分: {health.get('score', '—')} ({health.get('label', '—')})" if health else ""

    anomalies = ctx.extra_data.get("anomalies") or []
    anomaly_line = ""
    if anomalies:
        red = sum(1 for a in anomalies if a.get("severity") == "red")
        yellow = sum(1 for a in anomalies if a.get("severity") == "yellow")
        anomaly_line = f"\n异常: 🔴 {red} 严重 · 🟡 {yellow} 警告"

    return (
        f"① 场景: {scene}\n\n"
        f"② 数据:{health_line}{anomaly_line}\n{cat_lines}\n\n"
        f"③ 期望: {expect}\n\n"
        f"④ 来源: {source}"
    )


def _build_list_events_copy_prompt(date: str, plan_events: list) -> str:
    """构造 list_events(查日程)的 4 部分 copy prompt(ADR-0002 Q6)"""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    active_count = sum(1 for e in plan_events if e.get("is_active", 1))
    coverage_minutes = sum(int(e.get("duration_minutes", 0) or 0) for e in plan_events)
    coverage_hours = coverage_minutes / 60
    events_preview = "\n".join(
        f"  - {e.get('time_start', '')}–{e.get('time_end', '')} {e.get('title', '')}"
        f"({e.get('category', '—')})"
        for e in plan_events[:8]
    )
    more = f"\n  ...(共 {len(plan_events)} 段,只显示前 8 段)" if len(plan_events) > 8 else ""
    return (
        f"① 场景: 查看了 {date} 的日程计划({len(plan_events)} 段事件,"
        f"{active_count} 段活跃,覆盖 {coverage_hours:.1f}h)\n\n"
        f"② 数据:\n{events_preview}{more}\n\n"
        f"③ 期望: 可调 render-plans-review {date} 复盘,或调 update-event <id> --completion 标记完成,"
        f"或调 render-plans-preview {date} 重新规划\n\n"
        f"④ 来源: list_events.html 生成于 {generated_at},"
        f"数据来自 schedule_plans WHERE date={date} AND is_active=1"
    )


def render_record_report(date: str) -> dict:
    """兼容旧 CLI render-record-report — 等价于 render_record_day"""
    return render_record_day(date)


def render_records_detail(date: str, record_id: int = None) -> dict:
    """
    作息详情网页数据派生（人工智能推理溯源, 四步契约 §8 落地）.

    100% 字段暴露原则:每条作息记录的全部 11 字段都注入 payload,
      上层(HTML 模板) 自行决定渲染哪些字段、用什么样式、是否折叠。
      全部字段:id / date / time_start / time_end / duration_minutes / activity /
      category / source_contents / source_timestamps / analysis_reasoning / created_at。

    返回: {status, data: {meta, records, selected_record, ai_questions, errors, ...},
           message}
    """
    from schedule_db import _normalize_date, get_records_by_date
    from calculations import ai_questions_for_day, aggregate_by_category

    date = _normalize_date(date)
    records = get_records_by_date(date)

    full_records = [
        {
            "id": r["id"],
            "date": r["date"],
            "time_start": r["time_start"],
            "time_end": r["time_end"],
            "duration_minutes": int(r.get("duration_minutes") or 0),
            "activity": r["activity"],
            "category": r["category"],
            "source_contents": r.get("source_contents") or "",
            "source_timestamps": r.get("source_timestamps") or "",
            "analysis_reasoning": r.get("analysis_reasoning") or "",
            "created_at": r.get("created_at") or "",
        }
        for r in records
    ]

    selected = None
    if record_id is not None:
        for fr in full_records:
            if fr["id"] == record_id:
                selected = fr
                break

    cat_minutes = aggregate_by_category(records)
    total_minutes = sum(cat_minutes.values())
    sleep_records = [r for r in records if "睡眠" in r.get("category", "") or "午睡" in r.get("category", "")]
    sleep_min = max((r.get("duration_minutes") or 0 for r in sleep_records), default=0)

    dt = datetime.fromisoformat(date)
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    payload = {
        "meta": {
            "mode": "record-detail",
            "date": date,
            "record_id": record_id,
            "weekday": weekdays[dt.weekday()],
            "title": f"作息详情 · {dt.year}年{dt.month}月{dt.day}日({weekdays[dt.weekday()]})",
            "subtitle": f"共 {len(records)} 条记录 · 详情溯源 · 每条全 11 字段",
            "record_count": len(records),
            "total_minutes": int(total_minutes),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-23",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "records": full_records,
        "selected_record": selected,
        "summary_categories_count": len(cat_minutes),
        "ai_questions": ai_questions_for_day(date, [], sleep_min, total_minutes, 0),
        "copy_prompt": _build_record_copy_prompt(
            "record-detail",
            {"date": date, "total_minutes": total_minutes},
            records,
        ),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {date} 作息详情数据已生成({len(records)} 条记录,每条含 11 字段)",
    }


def render_plans_preview(date: str, plan_events: list, locked_events: list = None) -> dict:
    """
    商量计划预览(过程型首批落地,四步契约§3.6 + 手册§原则10 过程型 AI 协同模式).

    数据契约:
      - plan_events: 候选 24h 事件 list[{time_start, time_end, title, notes, category}, ...]
      - locked_events: 已有 schedule_plans WHERE date=date AND is_active=1 list[...]

    输出:
      - status: 'ok' | 'conflict' | 'incomplete'
      - 4 部分 prompt 字符串(场景/数据/期望/来源) → 用户复制给 AI
      - 24h 覆盖率 coverage_pct
      - conflicts: 候选与 locked 时间重叠
      - copy_prompt: 完整指令文本
    """
    from schedule_db import _normalize_date, list_plan_events, validate_24h_coverage

    date = _normalize_date(date)
    locked_events = locked_events or []
    if not plan_events:
        return {
            "status": "error",
            "data": None,
            "message": f"plan_events 为空,至少需要 1 条候选事件",
        }

    # 计算 24h 覆盖率
    coverage_err = validate_24h_coverage(plan_events)
    if coverage_err is None:
        coverage_pct = 100
        coverage_status = "ok"
    else:
        # 24h 不完整,粗略计算已覆盖分钟数
        covered_minutes = 0
        for ev in plan_events:
            try:
                sh, sm = map(int, ev["time_start"].split(":"))
                eh, em = map(int, ev["time_end"].split(":"))
                ev_min = (eh * 60 + em) - (sh * 60 + sm)
                if ev_min > 0:
                    covered_minutes += ev_min
            except (KeyError, ValueError):
                pass
        coverage_pct = round(covered_minutes / 1440 * 100, 1)
        coverage_status = "incomplete"

    # 计算冲突(候选与 locked 时间重叠)
    def to_min(hhmm):
        h, m = map(int, hhmm.split(":"))
        return h * 60 + m
    conflicts = []
    for i, cand in enumerate(plan_events):
        try:
            cs, ce = to_min(cand["time_start"]), to_min(cand["time_end"])
        except (KeyError, ValueError):
            continue
        for lk in locked_events:
            try:
                ls, le = to_min(lk["time_start"]), to_min(lk["time_end"])
            except (KeyError, ValueError):
                continue
            if cs < le and ls < ce:  # 时间区间相交
                conflicts.append({
                    "time_range": cand["time_start"] + "–" + cand["time_end"],
                    "candidate": cand.get("title", "—"),
                    "locked": lk.get("title", "—"),
                    "candidate_idx": i,
                })

    # 整体状态
    if conflicts:
        status = "conflict"
    elif coverage_status == "incomplete":
        status = "incomplete"
    else:
        status = "ok"

    # 4 部分 prompt(手册§原则10)
    plan_json_str = json.dumps(plan_events, ensure_ascii=False, indent=2)
    locked_summary = ""
    if locked_events:
        locked_summary = "\n⑤ 已锁定事件(写库时锁定时段,会被保护):\n" + \
            "\n".join([f"  - {e['time_start']}–{e['time_end']} {e.get('title','—')}" for e in locked_events]) + "\n"

    conflicts_summary = ""
    if conflicts:
        conflicts_summary = "\n⚠ 检测到 " + str(len(conflicts)) + " 处候选与已锁定事件时间冲突:\n" + \
            "\n".join([f"  - {c['time_range']}: 候选「{c['candidate']}」与已锁定「{c['locked']}」重叠" for c in conflicts]) + \
            "\n请调整候选事件时段或更新已锁定事件后重新预览。\n"

    copy_prompt = f"""① 场景: 我和 AI 多轮对话生成了 {date} 的候选计划({len(plan_events)} 段事件覆盖 24h {coverage_pct}%)。{('有 ' + str(len(conflicts)) + ' 处冲突需调整') if conflicts else '无冲突'}

② 数据(候选 24h 时间块):
{plan_json_str}{locked_summary}{conflicts_summary}
③ 期望: 请执行 schedule_cli.py upsert-plan-events {date} --json @plan.json 写库;询问飞书同步(Y/n)
  - 无冲突时直接采纳
  - 有冲突时先与用户讨论调整再写

④ 来源: plan_preview.html 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")},数据来自多轮对话
"""

    payload = {
        "meta": {
            "mode": "plan-preview",
            "date": date,
            "title": f"商量计划预览 · {date}",
            "subtitle": f"候选 {len(plan_events)} 段事件 · 24h 覆盖率 {coverage_pct}% · {len(conflicts)} 处冲突" + (" · 需调整" if conflicts else ""),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "plan_events": plan_events,
        "locked_events": locked_events,
        "conflicts": conflicts,
        "coverage_pct": coverage_pct,
        "status": status,
        "copy_prompt": copy_prompt,
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {date} 商量计划预览数据已生成(候选 {len(plan_events)} 段,冲突 {len(conflicts)} 处,24h 覆盖率 {coverage_pct}%)",
    }


def render_plans_review(date: str) -> dict:
    """
    复盘报告(process-html 阶段第 2 款,手册§原则10 过程型 AI 协同模式).

    数据契约:拉取 schedule_plans WHERE date=date AND is_active=1
    输出:每条事件含 id / time_start / time_end / title / category / completion / completion_note
          + meta(已标记的 completion 预填到 userMarks)
          + 4 部分 prompt 模板骨架(前端 JS 根据用户标记动态生成)

    与 render_plans_preview 区别:
      - preview 是"写库前预览"(AI 写库前确认)
      - review 是"写库后复盘"(AI 写库后用户标 status + note)
    """
    from schedule_db import _normalize_date, list_plan_events
    from calculations import ai_questions_for_day

    date = _normalize_date(date)
    events = list_plan_events(date, include_inactive=False)  # 仅活跃

    # 标准化为模板消费的字段
    plan_events = []
    for ev in events:
        plan_events.append({
            "id": ev.get("id"),
            "date": ev.get("date"),
            "time_start": ev.get("time_start"),
            "time_end": ev.get("time_end"),
            "title": ev.get("title"),
            "category": ev.get("category"),
            "notes": ev.get("notes") or "",
            "completion": ev.get("completion"),  # 已有 completion 预填
            "completion_note": ev.get("completion_note") or "",
        })

    # 计算复盘进度
    reviewed_count = sum(1 for ev in plan_events if ev["completion"])
    total = len(plan_events)
    progress_pct = round(reviewed_count / total * 100, 1) if total > 0 else 0

    payload = {
        "meta": {
            "mode": "plan-review",
            "date": date,
            "title": f"复盘报告 · {date}",
            "subtitle": f"逐条标记状态 · 复制 4 部分 prompt 给 AI · {reviewed_count}/{total} 已标记",
            "reviewed_count": reviewed_count,
            "total_count": total,
            "progress_pct": progress_pct,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "plan_events": plan_events,
        "ai_questions": ai_questions_for_day(date, [], 0, 0, 0),  # 占位
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {date} 复盘报告数据已生成({total} 段事件,{reviewed_count} 已标记)",
    }


def render_receipt(record_id: int) -> dict:
    """
    单条 CRUD 后漂亮回执(回执型首款,用户 2026-07-23 提出 3 类型分类中的"回执型"首批落地).

    ③ 期望: AI 自主决定,不让用户选 A/B/C(2026-07-24 改进)
      - 用户复制粘贴 = 一次性动作
      - AI 收到上下文 → 自主回复(继续记/看全貌/复盘/补漏)
      - 不让用户做"选方案"决定
    """
    from schedule_db import get_record_by_id, get_records_by_date, get_records_range
    from datetime import timedelta

    record = get_record_by_id(record_id)
    if not record:
        return {
            "status": "error",
            "data": None,
            "message": f"未找到 id={record_id} 的作息记录",
        }

    date = record.get("date")
    duration = int(record.get("duration_minutes") or 0)
    category = record.get("category") or ""

    today_records = get_records_by_date(date) if date else []
    today_count = len(today_records)
    today_mins = sum(int(r.get("duration_minutes") or 0) for r in today_records)

    try:
        end_dt = datetime.fromisoformat(date)
        start_dt = end_dt - timedelta(days=6)
        week_records = get_records_range(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
        week_count = len(week_records)
    except Exception:
        week_count = today_count

    category_records = [r for r in today_records if r.get("category") == category]
    category_total = len(category_records)
    try:
        sorted_cats = sorted(category_records, key=lambda r: r.get("time_start", ""))
        category_rank = next((i + 1 for i, r in enumerate(sorted_cats) if r.get("id") == record_id), category_total)
    except Exception:
        category_rank = category_total

    record_json = json.dumps({
        "id": record.get("id"),
        "date": record.get("date"),
        "time_start": record.get("time_start"),
        "time_end": record.get("time_end"),
        "duration_minutes": duration,
        "activity": record.get("activity"),
        "category": category,
        "source_contents": record.get("source_contents") or "",
        "source_timestamps": record.get("source_timestamps") or "",
        "analysis_reasoning": record.get("analysis_reasoning") or "",
        "created_at": record.get("created_at"),
    }, ensure_ascii=False, indent=2)

    # 3 种"复制动作"prompt(2026-07-24 设计改进:取消独立"复制今日进度"按钮,
    # §1 三个操作按钮 = 3 种具体 prompt。每个按钮 = 用户决策 + AI 指令合一。)
    base_prompt = f"""① 场景: 我刚记录了一条作息(id={record_id} · {record.get('date')} {record.get('time_start')}–{record.get('time_end')} {category})

② 数据(今日进度):
  - 今日已记录 {today_count} 条,总时长 {today_mins} 分钟({today_mins // 60}h{today_mins % 60}m)
  - 本周累计 {week_count} 条(最近 7 天)
  - 在「{category}」分类中,本条排第 {category_rank} / 共 {category_total} 条
  - 刚记录:
{record_json}

④ 来源: receipt_id{record_id}_{date}.html 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")},新记录 id={record_id}
"""

    prompt_continue = base_prompt + """
③ 期望: 用户即将告诉你"我刚才在做 X"。
请调 schedule_cli.py add 写库 + 调 render-receipt <新 id> 生成下一份回执。
不要做其他事,等用户输入。"""

    prompt_overview = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-record-day {record.get('date')} 生成今日报告 HTML,
让我扫读全部记录(包含今日所有作息 + 24h 时间轴 + 分类进度)。
不要做复盘,纯展示。"""

    prompt_review = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-plans-review {record.get('date')} 生成复盘报告 HTML,
让我逐条标"已完成 / 已完成(超时) / 部分完成 / 未完成 / 未完成(不可抗力)" + 写完成原因。
完成后给我返回复盘小结(完成率 + 各类占比 + 1-2 句今日总结)。"""

    payload = {
        "meta": {
            "mode": "record-receipt",
            "title": "已记录",
            "record_id": record_id,
            "date": date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "record": record,
        "stats": {
            "today_count": today_count,
            "today_mins": today_mins,
            "week_count": week_count,
            "category": category,
            "category_rank": category_rank,
            "category_total": category_total,
        },
        "prompts": {
            "continue": prompt_continue,  # §1 按钮 1:继续记
            "overview": prompt_overview,  # §1 按钮 2:看今日全貌
            "review":   prompt_review,     # §1 按钮 3:晚点复盘
        },        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ id={record_id} 漂亮回执已生成(今日 {today_count} 条,本周 {week_count} 条)",
    }


# ============================================================
# T2 · 记录三件套结果 HTML(G1-A1 · 2026-08-09 升级 add 回执链路,非纯新增)
# ============================================================
# 顶层体验 §5:记录每一笔之后,返回一个结果型 HTML,设计好看、信息全面。
# 三件套 = ① 全天作息时间轴 + ② 过去几小时推断高亮 + ③ 当前状态总览(笔数/覆盖时长/缺口)。
# 分类统计 / 计划对照不叠入(归复盘场景 · G1 Q1 定标)。

RECENT_HOURS = 3  # 「过去几小时」= 新记录时段结束前推 3 小时(推断回溯窗口)


def _snip(text, max_len):
    """摘要截断:超过 max_len 用省略号"""
    text = str(text or "").strip()
    return text if len(text) <= max_len else text[:max_len] + "…"


def _fmt_hhmm(mins: int) -> str:
    """分钟数 → HH:MM(1440 → 24:00,跨日边界)"""
    if mins >= 24 * 60:
        return "24:00"
    return f"{mins // 60:02d}:{mins % 60:02d}"


def _day_gap_slots(records):
    """计算单日记录间的缺口时段列表(三件套 ③ 状态总览)。

    按 time_start 排序,区间合并(cursor 前滚)后取:
    首条前(00:00→) + 相邻记录间隔 + 末条后(→24:00)。
    返回 [{"start","end","text","minutes"}, ...],按时间顺序。
    """
    sorted_recs = sorted(
        [r for r in records if r.get("time_start") and r.get("time_end")],
        key=lambda r: (r.get("time_start", ""), r.get("id") or 0),
    )
    slots = []
    cursor = 0
    for r in sorted_recs:
        ts = _to_min(r.get("time_start"))
        te = max(_to_min(r.get("time_end")), ts)
        if ts > cursor:
            slots.append({
                "start": _fmt_hhmm(cursor),
                "end": _fmt_hhmm(ts),
                "text": f"{_fmt_hhmm(cursor)} → {_fmt_hhmm(ts)}",
                "minutes": ts - cursor,
            })
        if te > cursor:
            cursor = te
    if cursor < 24 * 60:
        slots.append({
            "start": _fmt_hhmm(cursor),
            "end": "24:00",
            "text": f"{_fmt_hhmm(cursor)} → 24:00",
            "minutes": 24 * 60 - cursor,
        })
    return slots


def _build_record_result_prompts(record, record_id, today_count, today_mins,
                                 week_count, category, category_rank,
                                 category_total, record_json):
    """三件套 3 个操作按钮 prompt(T2 · 2026-08-09)

    §1 三个操作按钮 = 3 种具体 prompt(用户决策 + AI 指令合一)。
    指令指向三件套新链路:add 自动渲染 / render-record-result <新 id>。
    """
    date = record.get("date")
    base_prompt = f"""① 场景: 我刚记录了一条作息(id={record_id} · {date} {record.get('time_start')}–{record.get('time_end')} {category})

② 数据(今日进度):
  - 今日已记录 {today_count} 条,总时长 {today_mins} 分钟({today_mins // 60}h{today_mins % 60}m)
  - 本周累计 {week_count} 条(最近 7 天)
  - 在「{category}」分类中,本条排第 {category_rank} / 共 {category_total} 条
  - 刚记录:
{record_json}

④ 来源: 记作息结果 id={record_id} 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    prompt_continue = base_prompt + """
③ 期望: 用户即将告诉你"我刚才在做 X"。
请调 schedule_cli.py add 写库(add 会自动生成三件套结果 HTML,无需再调 render 命令)。
不要做其他事,等用户输入。"""

    prompt_overview = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-record-day {date} 生成今日报告 HTML,
让我扫读全部记录(包含今日所有作息 + 24h 时间轴 + 分类进度)。
不要做复盘,纯展示。"""

    prompt_review = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-plans-review {date} 生成复盘报告 HTML,
让我逐条标"已完成 / 已完成(超时) / 部分完成 / 未完成 / 未完成(不可抗力)" + 写完成原因。
完成后给我返回复盘小结(完成率 + 各类占比 + 1-2 句今日总结)。"""

    return {
        "continue": prompt_continue,  # §1 按钮 1:继续记
        "overview": prompt_overview,  # §1 按钮 2:看今日全貌
        "review":   prompt_review,    # §1 按钮 3:晚点复盘
    }


def render_record_result(record_id: int, warning: str = None) -> dict:
    """T2 · 记录三件套结果 HTML(G1-A1 · 2026-08-09)

    记录一笔 → 三件套结果 HTML:
      ① 全天作息时间轴(24h 主导分类色带 · 高中作息表升级版)
      ② 过去几小时推断高亮(回溯窗口 = 新记录 time_end 前推 3 小时,
         每条回溯来源消息 + 推理链;补记日不会把"未来"记录误标已推断)
      ③ 当前状态总览(今日笔数 / 覆盖时长 / 缺口时段 / 本周累计)

    Args:
        record_id: 刚写入的作息记录 id
        warning: add 链路的附加提示(如一级 category 建议细化),注入模板警示条

    Returns:
        {status, data: {meta, record, stats, timeline, past_hours, prompts, warning}, message}
    """
    from schedule_db import get_record_by_id, get_records_by_date, get_records_range
    from calculations import build_hourly_dominant
    from datetime import timedelta

    record = get_record_by_id(record_id)
    if not record:
        return {
            "status": "error",
            "data": None,
            "message": f"未找到 id={record_id} 的作息记录",
        }

    date = record.get("date")
    category = record.get("category") or ""
    today_records = get_records_by_date(date) if date else []
    today_records_sorted = sorted(
        today_records,
        key=lambda r: (r.get("time_start") or "", r.get("id") or 0),
    )
    today_count = len(today_records)
    today_mins = sum(int(r.get("duration_minutes") or 0) for r in today_records)

    # === ③ 状态总览:缺口 / 覆盖 / 周累计 ===
    gap_slots = _day_gap_slots(today_records_sorted)
    try:
        end_dt = datetime.fromisoformat(date)
        start_dt = end_dt - timedelta(days=6)
        week_count = len(get_records_range(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")))
    except Exception:
        week_count = today_count

    category_records = [r for r in today_records if r.get("category") == category]
    category_total = len(category_records)
    sorted_cats = sorted(category_records, key=lambda r: r.get("time_start", ""))
    category_rank = next(
        (i + 1 for i, r in enumerate(sorted_cats) if r.get("id") == record_id),
        category_total,
    )

    is_today = (date == datetime.now().strftime("%Y-%m-%d"))
    now_min = datetime.now().hour * 60 + datetime.now().minute
    passed_min = now_min if is_today else 24 * 60
    coverage_pct = round(min(today_mins / passed_min * 100, 100), 1) if passed_min else 0.0

    # === ② 过去几小时推断高亮:窗口 = [新记录 time_end − 3h, 新记录 time_end] ===
    anchor_min = _to_min(record.get("time_end") or "00:00")
    window_start_min = max(0, anchor_min - RECENT_HOURS * 60)
    past_hours = [
        {
            "id": r.get("id"),
            "time": f"{r.get('time_start')} → {r.get('time_end')}",
            "activity": r.get("activity"),
            "category": r.get("category"),
            "color": _cat_color(r.get("category", "")),
            "duration_minutes": int(r.get("duration_minutes") or 0),
            "source_summary": _snip(r.get("source_contents") or "", 40),
            "reasoning_summary": _snip(r.get("analysis_reasoning") or "", 60),
            "is_new": r.get("id") == record_id,
        }
        for r in today_records_sorted
        if _to_min(r.get("time_end") or "00:00") > window_start_min
        and _to_min(r.get("time_start") or "00:00") < anchor_min
    ]

    # === ① 全天作息时间轴(24h 主导分类,每小时一条) ===
    timeline = [
        {
            "hour": h["hour"],
            "category": h["dominant_cat"],
            "color": _cat_color(h["dominant_cat"]),
            "tip": f"{h['hour']:02d}:00 {h['dominant_cat']}",
            "records_count": h["records_count"],
        }
        for h in build_hourly_dominant(today_records)
    ]

    record_json = json.dumps({
        "id": record.get("id"),
        "date": record.get("date"),
        "time_start": record.get("time_start"),
        "time_end": record.get("time_end"),
        "duration_minutes": int(record.get("duration_minutes") or 0),
        "activity": record.get("activity"),
        "category": category,
        "source_contents": record.get("source_contents") or "",
        "source_timestamps": record.get("source_timestamps") or "",
        "analysis_reasoning": record.get("analysis_reasoning") or "",
        "created_at": record.get("created_at"),
    }, ensure_ascii=False, indent=2)

    prompts = _build_record_result_prompts(
        record, record_id, today_count, today_mins, week_count,
        category, category_rank, category_total, record_json,
    )

    payload = {
        "meta": {
            "mode": "record-result",
            "title": "已记录",
            "record_id": record_id,
            "date": date,
            "is_today": is_today,
            "inference_window": {
                "start": _fmt_hhmm(window_start_min),
                "end": record.get("time_end") or "00:00",
                "hours": RECENT_HOURS,
            },
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-08-09-T2",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "record": record,
        "stats": {
            "today_count": today_count,
            "today_mins": today_mins,
            "coverage_pct": coverage_pct,
            "passed_min": passed_min,
            "week_count": week_count,
            "category": category,
            "category_rank": category_rank,
            "category_total": category_total,
            "gap_slots": gap_slots,
        },
        "timeline": timeline,
        "past_hours": past_hours,
        "prompts": prompts,
        "warning": warning,
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ id={record_id} 三件套结果已生成(今日 {today_count} 条,缺口 {len(gap_slots)} 段)",
    }


def render_record_receipt_edit(record_id: int, diff: dict = None) -> dict:
    """
    纠正记录后漂亮回执(回执型第 2 款,蓝调,"已纠正"标识,2026-07-24)。

    第一性:用户说"amend-record" 纠正了记录后,需要一份能审计改了什么 +
    改对没对的回执。核心是 **diff 视图**(before/after 三列)。

    Args:
        record_id: 记录 ID
        diff: 修正内容 dict 格式 {field: {"old": X, "new": Y}, ...}
              从 schedule_db.update_record() 返回值传入。
              不传则 diff={}(只展示当前记录,无 diff 区块)。

    Returns:
        完整 payload 注入 record-receipt-edit 模板,含:
          - meta: mode + title + record_id + date + edit_count + updated_at
          - record: 完整 13 字段
          - diff: {field: {old, new}} (空 dict if 无 diff)
          - stats: 4 张摘要卡
          - prompts: 3 操作按钮
    """
    from schedule_db import get_record_by_id, get_records_by_date, get_records_range

    record = get_record_by_id(record_id)
    if not record:
        return {
            "status": "error",
            "data": None,
            "message": f"未找到 id={record_id} 的作息记录",
        }

    date = record.get("date")
    duration = int(record.get("duration_minutes") or 0)
    category = record.get("category") or ""
    edit_count = int(record.get("edit_count") or 0)
    updated_at = record.get("updated_at") or ""

    # 4 张 stat 卡所需数据
    today_records = get_records_by_date(date) if date else []
    today_count = len(today_records)
    today_mins = sum(int(r.get("duration_minutes") or 0) for r in today_records)

    try:
        end_dt = datetime.fromisoformat(date)
        start_dt = end_dt - timedelta(days=6)
        week_records = get_records_range(start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
        week_count = len(week_records)
    except Exception:
        week_count = today_count

    diff = diff or {}  # 缺省空 dict(防止 None)

    diff_count = len(diff)
    diff_lines = []
    for k, v in diff.items():
        old = v.get("old") if isinstance(v, dict) else None
        new = v.get("new") if isinstance(v, dict) else None
        diff_lines.append({
            "field": k,
            "old": old if old is not None else "(空)",
            "new": new if new is not None else "(空)",
        })

    record_json = json.dumps({
        "id": record.get("id"),
        "date": record.get("date"),
        "time_start": record.get("time_start"),
        "time_end": record.get("time_end"),
        "duration_minutes": duration,
        "activity": record.get("activity"),
        "category": category,
        "source_contents": record.get("source_contents") or "",
        "source_timestamps": record.get("source_timestamps") or "",
        "analysis_reasoning": record.get("analysis_reasoning") or "",
        "created_at": record.get("created_at"),
        "updated_at": updated_at,
        "edit_count": edit_count,
    }, ensure_ascii=False, indent=2)

    # 3 操作按钮 prompt(蓝调回执版,2026-07-24 设计:强调"已纠正"+ diff 让用户审计)
    base_prompt = f"""① 场景: 我刚纠正了一条作息(id={record_id} · {record.get('date')} {record.get('time_start')}–{record.get('time_end')} {category})
本次纠正了 {diff_count} 个字段(edit_count={edit_count})。

② 数据(纠正后状态):
  - 今日已记录 {today_count} 条,总时长 {today_mins} 分钟({today_mins // 60}h{today_mins % 60}m)
  - 本周累计 {week_count} 条(最近 7 天)
  - 纠正后记录(已含 updated_at + edit_count):
{record_json}
"""

    if diff_count > 0:
        base_prompt += f"""
②.5 纠正 diff({diff_count} 个字段):
"""
        for d in diff_lines:
            base_prompt += f"  - {d['field']}: {d['old']!r} → {d['new']!r}\n"

    base_prompt += f"""
④ 来源: record_receipt_edit_id{record_id}_{date}.html 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")},record_id={record_id},edit_count={edit_count}
"""

    prompt_continue = base_prompt + """
③ 期望: 用户即将告诉你"我接下来在做 X"(可能是继续记下一条,或接着纠正另一条)。
请调 schedule_cli.py add 写库 + 调 render-record-receipt <新 id> 生成回执;或调 amend-record <其他 id> 继续修正。
不要做其他事,等用户输入。"""

    prompt_overview = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-record-day {record.get('date')} 生成今日报告 HTML,
让我扫读全部记录(包含今日所有作息 + 24h 时间轴 + 分类进度)。
纯展示,不做复盘。"""

    prompt_review = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-plans-review {record.get('date')} 生成复盘报告 HTML,
让我逐条标"已完成 / 已完成(超时) / 部分完成 / 未完成 / 未完成(不可抗力)" + 写完成原因。
完成后给我返回复盘小结(完成率 + 各类占比 + 1-2 句今日总结)。"""

    payload = {
        "meta": {
            "mode": "record-receipt-edit",
            "title": "已纠正",
            "subtitle": f"id={record_id} · 纠正 {diff_count} 个字段",
            "record_id": record_id,
            "date": date,
            "edit_count": edit_count,
            "updated_at": updated_at,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "record": record,
        "diff": diff,        # 原始 diff dict {field: {old, new}}
        "diff_list": diff_lines,  # 列表形式方便模板渲染
        "stats": {
            "today_count": today_count,
            "today_mins": today_mins,
            "week_count": week_count,
            "category": category,
            "diff_count": diff_count,
            "edit_count": edit_count,
        },
        "prompts": {
            "continue": prompt_continue,  # 继续记 / 继续纠正
            "overview": prompt_overview,  # 看今日全貌
            "review":   prompt_review,     # 复盘今日
        },
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ id={record_id} 已纠正回执已生成(纠正 {diff_count} 个字段,edit_count={edit_count})",
    }


def _calc_plan_minutes(p):
    """计算 plan_event 的时段分钟数(无效返回 0)"""
    try:
        ts = p.get("time_start") or "0:0"
        te = p.get("time_end") or "0:0"
        sh, sm = map(int, ts.split(":"))
        eh, em = map(int, te.split(":"))
        m = (eh * 60 + em) - (sh * 60 + sm)
        if m > 0:
            return m
    except Exception:
        pass
    return 0


def _calc_plan_receipt_stats(plan, today_plans):
    """render_plan_receipt 4 款公共 stats 派生(2026-07-24 提取)"""
    today_count = len(today_plans)
    completed_count = sum(1 for p in today_plans if p.get("completion") and p["completion"] != "未完成")
    note_count = sum(1 for p in today_plans if p.get("completion_note"))
    completion_rate = round(completed_count / today_count * 100) if today_count > 0 else 0
    feishu_synced = sum(1 for p in today_plans if p.get("feishu_event_id"))
    coverage_minutes = sum(_calc_plan_minutes(p) for p in today_plans if p.get("is_active", 1) == 1)
    coverage_hours = round(coverage_minutes / 60, 1)
    return {
        "today_count": today_count,
        "completed_count": completed_count,
        "note_count": note_count,
        "completion_rate": completion_rate,
        "feishu_synced": feishu_synced,
        "coverage_hours": coverage_hours,
    }


def _build_plan_json(plan):
    """render_plan_receipt 4 款公共 plan_json 拼装(13 字段)"""
    return json.dumps({
        "id": plan.get("id"),
        "date": plan.get("date"),
        "time_start": plan.get("time_start"),
        "time_end": plan.get("time_end"),
        "title": plan.get("title"),
        "notes": plan.get("notes") or "",
        "category": plan.get("category") or "",
        "feishu_event_id": plan.get("feishu_event_id"),
        "last_synced_at": plan.get("last_synced_at"),
        "is_active": plan.get("is_active", 1),
        "completion": plan.get("completion"),
        "completion_note": plan.get("completion_note") or "",
    }, ensure_ascii=False, indent=2)


def _build_plan_receipt_base_prompt(plan_id, plan, stats, plan_json, action_verb_zh, action_label_zh, file_action):
    """render_plan_receipt 4 款公共 base_prompt 构造"""
    date = plan.get("date", "")
    return f"""① 场景: 我刚"{action_verb_zh}"了一条计划(id={plan_id} · {date} {plan.get("time_start")}–{plan.get("time_end")} {plan.get("title")})

② 数据(今日计划概况):
  - 今日共 {stats["today_count"]} 条计划(完成 {stats["completed_count"]} 条,完成率 {stats["completion_rate"]}%)
  - 飞书已同步 {stats["feishu_synced"]} 条
  - 24h 覆盖率 {stats["coverage_hours"]} 小时
  - 刚"{action_label_zh}":
{plan_json}

④ 来源: plan_receipt_{file_action}_id{plan_id}_{date}.html 生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")},操作 action={file_action}
"""





def render_plan_receipt(plan_id: int, action: str = "update") -> dict:
    """改/删计划回执(回执型第2款,2026-07-24,复用 #0 漂亮回执模式)."""
    from schedule_db import get_plan_event, list_plan_events

    plan = get_plan_event(plan_id)
    if not plan:
        return {"status": "error", "data": None, "message": f"未找到 id={plan_id} 的计划事件"}

    date = plan.get("date")
    today_plans = list_plan_events(date, include_inactive=(action == "deactivate"))
    stats = _calc_plan_receipt_stats(plan, today_plans)
    plan_json = _build_plan_json(plan)

    action_verb_zh = "修改" if action == "update" else "软删"
    base_prompt = _build_plan_receipt_base_prompt(plan_id, plan, stats, plan_json, action_verb_zh, action_verb_zh, action)

    prompt_adjust = base_prompt + f"""
③ 期望: 用户即将告诉你修改内容(改时间/改标题/补备注/改分类)。
请调 schedule_cli.py update-event {plan_id} <字段> <值> 写库。
不要做其他事,等用户输入。"""

    prompt_overview = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-list-events {date} 生成今日所有计划 HTML,
让我扫读今日全部计划(包含所有状态 + 飞书同步状态)。
不要做复盘,纯展示。"""

    prompt_review = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-plans-review {date} 生成复盘报告 HTML,
让我逐条标"已完成 / 已完成(超时) / 部分完成 / 未完成 / 未完成(不可抗力)" + 写完成原因。
完成后给我返回复盘小结(完成率 + 各类占比 + 1-2 句今日总结)。"""

    payload = {
        "meta": {
            "mode": "plan-receipt",
            "title": "已" + ("修改" if action == "update" else "删除"),
            "action": action,
            "plan_id": plan_id, "date": date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "plan": plan, "stats": stats,
        "prompts": {"adjust": prompt_adjust, "overview": prompt_overview, "review": prompt_review},
        "errors": [],
    }
    return {
        "status": "ok", "data": payload,
        "message": f"✓ id={plan_id} 计划 {action_verb_zh}回执已生成(今日 {stats['today_count']} 条计划,完成率 {stats['completion_rate']}%)",
    }


def render_plan_receipt_add(plan_id: int) -> dict:
    """补计划回执(回执型第 3 款,2026-07-24,绿色调)."""
    from schedule_db import get_plan_event, list_plan_events

    plan = get_plan_event(plan_id)
    if not plan:
        return {"status": "error", "data": None, "message": f"未找到 id={plan_id} 的计划事件"}

    date = plan.get("date")
    today_plans = list_plan_events(date, include_inactive=True) if date else []
    stats = _calc_plan_receipt_stats(plan, today_plans)
    plan_json = _build_plan_json(plan)
    base_prompt = _build_plan_receipt_base_prompt(plan_id, plan, stats, plan_json, "补", "补", "add")

    prompt_continue = base_prompt + """
③ 期望: 用户即将告诉你"继续补下一条"。
请调 schedule_cli.py ensure-plan-event <新日期> <新时段> --title "..." --category "..." 写库。
不要做其他事,等用户输入。"""

    prompt_overview = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-list-events {date} 生成今日所有计划 HTML,
让我扫读今日全部计划(包含所有状态 + 飞书同步状态)。
不要做复盘,纯展示。"""

    prompt_review = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-plans-review {date} 生成复盘报告 HTML,
让我逐条标"已完成 / 已完成(超时) / 部分完成 / 未完成 / 未完成(不可抗力)" + 写完成原因。
完成后给我返回复盘小结(完成率 + 各类占比 + 1-2 句今日总结)。"""

    payload = {
        "meta": {
            "mode": "plan-receipt-add", "title": "已补计划",
            "plan_id": plan_id, "date": date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "plan": plan, "stats": stats,
        "prompts": {"continue": prompt_continue, "overview": prompt_overview, "review": prompt_review},
        "errors": [],
    }
    return {
        "status": "ok", "data": payload,
        "message": f"✓ id={plan_id} 计划 已补回执已生成(今日 {stats['today_count']} 条计划,完成率 {stats['completion_rate']}%)",
    }


def render_plan_receipt_write(plan_id: int) -> dict:
    """写摘要回执(回执型第 4 款,2026-07-24,紫色调,与 update 同源)."""
    from schedule_db import get_plan_event, list_plan_events

    plan = get_plan_event(plan_id)
    if not plan:
        return {"status": "error", "data": None, "message": f"未找到 id={plan_id} 的计划事件"}

    date = plan.get("date")
    today_plans = list_plan_events(date, include_inactive=True) if date else []
    stats = _calc_plan_receipt_stats(plan, today_plans)
    plan_json = _build_plan_json(plan)
    base_prompt = _build_plan_receipt_base_prompt(plan_id, plan, stats, plan_json, "写摘要", "写摘要", "write")

    prompt_continue = base_prompt + """
③ 期望: 用户即将告诉你"继续写另一条摘要"。
请调 schedule_cli.py update-event <新 id> --completion X --completion-note "Y"。
不要做其他事,等用户输入。"""

    prompt_overview = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-plans-review {date} 生成复盘报告 HTML,
让我扫读所有事件(已标完成 + 未完成),继续标剩余事件。
不要做其他事,纯展示 + 让我标。"""

    prompt_look_all = base_prompt + f"""
③ 期望: 请调 schedule_cli.py render-list-events {date} 生成今日所有计划 HTML,
让我扫读今日全部计划(包含所有状态 + 飞书同步状态)。
不要做复盘,纯展示。"""

    payload = {
        "meta": {
            "mode": "plan-receipt-write", "title": "已写摘要",
            "plan_id": plan_id, "date": date,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "_template_version": "v2026-07-24",
            "_snapshot_at": datetime.now().isoformat(),
        },
        "plan": plan, "stats": stats,
        "prompts": {"continue": prompt_continue, "overview": prompt_overview, "look_all": prompt_look_all},
        "errors": [],
    }
    return {
        "status": "ok", "data": payload,
        "message": f"✓ id={plan_id} 计划 已写摘要回执已生成(今日 {stats['today_count']} 条计划,完成率 {stats['completion_rate']}%,已写反思 {stats['note_count']} 条)",
    }


# ===== 5 模板数据派生函数(T1~T5,2026-07-23 升级)=====

def render_record_day(date: str) -> dict:
    """T1 单日:4 卡摘要 + 24h 时间轴 + 分类进度 + 睡眠分析 + 健康分 + AI 钩子"""
    from schedule_db import _normalize_date, get_records_by_date
    from calculations import (
        aggregate_by_category, build_hourly_dominant, compute_health_score,
        ai_questions_for_day,
    )

    date = _normalize_date(date)
    records = get_records_by_date(date)
    cat_minutes = aggregate_by_category(records)
    total_minutes = sum(cat_minutes.values())

    sorted_cats = sorted(cat_minutes.items(), key=lambda x: -x[1])
    summary_items = [
        {
            "category": cat, "emoji": _cat_emoji(cat), "color": _cat_color(cat),
            "total_minutes": int(mins), "duration_text": _fmt_dur(int(mins)),
            "pct": round((mins / total_minutes * 100) if total_minutes else 0.0, 1),
        }
        for cat, mins in sorted_cats
    ]

    hour_dominant = build_hourly_dominant(records)
    timeline = [
        {"hour": h["hour"], "category": h["dominant_cat"],
         "color": _cat_color(h["dominant_cat"]),
         "tip": f"{h['hour']:02d}:00 {h['dominant_cat']}"}
        for h in hour_dominant
    ]

    sleep_records = [r for r in records
                    if "睡眠" in r.get("category", "") or "午睡" in r.get("category", "")]
    main_sleep = max(sleep_records, key=lambda r: r.get("duration_minutes") or 0) if sleep_records else None
    sleep_data = {
        "total_records": len(sleep_records),
        "main_sleep": (
            {
                "time_start": main_sleep["time_start"],
                "time_end": main_sleep["time_end"],
                "duration_minutes": int(main_sleep.get("duration_minutes") or 0),
                "duration_text": _fmt_dur(int(main_sleep.get("duration_minutes") or 0)),
                "category": main_sleep.get("category"),
                "color": _cat_color(main_sleep.get("category", "睡眠")),
            } if main_sleep else None
        ),
        "is_sufficient": (main_sleep.get("duration_minutes") or 0) >= 7 * 60 if main_sleep else False,
    }
    sleep_min = main_sleep.get("duration_minutes") or 0 if main_sleep else 0

    dt = datetime.fromisoformat(date)
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    payload = {
        "meta": {
            "mode": "record-day",
            "date": date,
            "weekday": weekdays[dt.weekday()],
            "title": f"作息报告 · {dt.year}年{dt.month}月{dt.day}日({weekdays[dt.weekday()]})",
            "subtitle": f"共 {len(records)} 条记录,总时长 {_fmt_dur(total_minutes)}",
            "record_count": len(records),
            "total_minutes": int(total_minutes),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "summary_items": summary_items,
        "timeline": timeline,
        "sleep_data": sleep_data,
        "records": _build_full_records(records),
        "health": {
            "score": compute_health_score(records),
            "label": "充足" if sleep_min >= 7*60 else ("偏短" if sleep_min >= 5*60 else "严重不足"),
        },
        "ai_questions": ai_questions_for_day(date, summary_items, sleep_min, total_minutes, compute_health_score(records)),
        "copy_prompt": _build_record_copy_prompt(
            "record-day", {"date": date, "total_minutes": total_minutes},
            records, summary_items,
            {"health": {"score": compute_health_score(records),
                       "label": "充足" if sleep_min >= 7*60 else ("偏短" if sleep_min >= 5*60 else "严重不足")}},
        ),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {date} 单日报告数据已生成",
    }


def render_record_range(start: str, end: str) -> dict:
    """T2 区间:4 卡摘要 + 7 维趋势 SVG + 分类进度 + 健康分 + AI 钩子"""
    from schedule_db import _normalize_date, get_records_range
    from calculations import (
        aggregate_by_category, build_dimension_aggregates, build_trend_series,
        compute_health_score, ai_questions_for_range,
    )
    import math

    start = _normalize_date(start)
    end = _normalize_date(end)
    records = get_records_range(start, end)
    days = sorted({r.get("date", "") for r in records})
    days_count = len(days)

    dim_totals = build_dimension_aggregates(records)
    cat_minutes = aggregate_by_category(records)
    total = sum(dim_totals.values())

    sorted_cats = sorted(cat_minutes.items(), key=lambda x: -x[1])
    summary_items = [
        {
            "category": cat, "emoji": _cat_emoji(cat), "color": _cat_color(cat),
            "total_minutes": int(mins), "duration_text": _fmt_dur(int(mins)),
            "pct": round((mins / total * 100) if total else 0.0, 1),
        }
        for cat, mins in sorted_cats
    ]

    # 7 维趋势 SVG
    HEALTH_DIMS = ["维持", "健康", "工作", "学习", "调整", "日常", "投入"]
    colors = {"维持":"#5E5CE6","健康":"#FF9500","工作":"#007AFF","学习":"#34C759","调整":"#30D158","日常":"#8E8E93","投入":"#FF2D55"}
    series = {d: build_trend_series(records, d) for d in HEALTH_DIMS}
    max_y = max((s["mins"] for arr in series.values() for s in arr), default=1) or 1
    width, height = 640, 130
    n = max(1, days_count)
    step_x = (width - 40) / max(1, n - 1) if n > 1 else 0
    svg_lines = [f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none">']
    for d in HEALTH_DIMS:
        arr = series[d]
        if not arr:
            continue
        pts = []
        for i, pt in enumerate(arr):
            x = 20 + i * step_x
            y = height - 10 - (pt["mins"] / max_y * (height - 30))
            pts.append(f"{x:.1f},{y:.1f}")
        svg_lines.append(f'<polyline class="line" stroke="{colors[d]}" points="{" ".join(pts)}"/>')
    if days:
        for i in [0, len(days) - 1]:
            if 0 <= i < len(days):
                x = 20 + i * step_x
                svg_lines.append(f'<text class="axis" x="{x:.1f}" y="{height-2}" text-anchor="{"start" if i==0 else "end"}">{days[i][5:]}</text>')
    svg_lines.append('</svg>')
    trend_chart = "".join(svg_lines)

    health = {"score": compute_health_score(records), "label": ""}
    payload = {
        "meta": {
            "mode": "record-range",
            "start": start, "end": end, "days": days_count,
            "total_minutes": total,
            "title": f"作息区间报告 · {start} ~ {end}",
            "subtitle": f"{days_count} 天,{len(records)} 条记录,总时长 {_fmt_dur(total)}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "days": days,
        "summary_items": summary_items,
        "dim_totals": dim_totals,
        "total_records": len(records),
        "records": _build_full_records(records),
        "trend_chart": trend_chart,
        "health": health,
        "ai_questions": ai_questions_for_range(start, end, dim_totals, health["score"], 0),
        "copy_prompt": _build_record_copy_prompt(
            "record-range",
            {"date": start, "start": start, "end": end, "total_minutes": total},
            records, summary_items, {"health": health},
        ),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {start} ~ {end} 区间报告数据已生成",
    }


def render_record_compare(label_a: str, start_a: str, end_a: str, label_b: str, start_b: str, end_b: str) -> dict:
    """T3 对比:2 段 A/B 7 维差异柱"""
    from schedule_db import _normalize_date, get_records_range
    from calculations import build_compare_aggregates, build_diff_table, ai_questions_for_compare
    from datetime import date as _d

    start_a = _normalize_date(start_a)
    end_a = _normalize_date(end_a)
    start_b = _normalize_date(start_b)
    end_b = _normalize_date(end_b)
    recs_a = get_records_range(start_a, end_a)
    recs_b = get_records_range(start_b, end_b)
    days_a = (_d.fromisoformat(end_a) - _d.fromisoformat(start_a)).days + 1
    days_b = (_d.fromisoformat(end_b) - _d.fromisoformat(start_b)).days + 1
    ranges = build_compare_aggregates([
        {"label": label_a, "start": start_a, "end": end_a, "days": days_a, "records": recs_a},
        {"label": label_b, "start": start_b, "end": end_b, "days": days_b, "records": recs_b},
    ])
    diffs = build_diff_table(ranges[0], ranges[1])
    payload = {
        "meta": {
            "mode": "record-compare",
            "title": f"作息对比 · {label_a} vs {label_b}",
            "subtitle": f"{label_a}:{start_a}~{end_a} · {label_b}:{start_b}~{end_b}",
            "label_a": label_a,   # 2026-07-24 补:title_for_mode 用此生成 title
            "label_b": label_b,   # 2026-07-24 补:title_for_mode 用此生成 title
            "start_a": start_a,
            "end_a": end_a,
            "start_b": start_b,
            "end_b": end_b,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "ranges": ranges,
        "diffs": diffs,
        "ai_questions": ai_questions_for_compare(ranges, diffs),
        "copy_prompt": _build_record_copy_prompt(
            "record-compare",
            {"date": start_a, "label_a": label_a, "start_a": start_a,
             "label_b": label_b, "start_b": start_b},
            recs_a + recs_b, [],
        ),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ 对比 {label_a} vs {label_b} 数据已生成",
    }


def render_record_category(category: str, start: str, end: str) -> dict:
    """T4 类别深挖:24h × N 天 热力图"""
    from schedule_db import _normalize_date, get_records_range
    from calculations import l1_of, ai_questions_for_category

    start = _normalize_date(start)
    end = _normalize_date(end)
    records = get_records_range(start, end)
    l1_target = l1_of(category)
    cat_records = [r for r in records if l1_of(r.get("category", "")) == l1_target]
    total = sum(r.get("duration_minutes") or 0 for r in cat_records)
    days = sorted({r.get("date", "") for r in cat_records})
    days_count = len(days)
    daily_avg = round(total / days_count, 1) if days_count else 0  # L8 修复:整数除法丢精度

    by_date: dict[str, list[dict]] = {}
    for r in cat_records:
        by_date.setdefault(r.get("date", ""), []).append(r)
    sorted_dates = sorted(by_date.keys())
    matrix = []
    for d in sorted_dates:
        hour_mins = [0] * 24
        for r in by_date[d]:
            s_min = _to_min(r.get("time_start", ""))
            e_min = _to_min(r.get("time_end", ""))
            if e_min <= s_min:
                continue
            cur = s_min
            while cur < e_min:
                h = cur // 60
                if 0 <= h < 24:
                    nh = (h + 1) * 60
                    covered = min(nh, e_min) - cur
                    if covered > 0:
                        hour_mins[h] += covered
                cur += 60
        row = []
        for h in range(24):
            if hour_mins[h] > 0:
                row.append({"cat": l1_target, "mins": hour_mins[h], "color": _cat_color(l1_target)})
            else:
                row.append({"cat": None, "mins": 0, "color": "#f5f5f7"})
        matrix.append(row)

    payload = {
        "meta": {
            "mode": "record-category",
            # M5:用户原值 (category) + 映射后值 (l1_target) 都写 meta,文件名前缀用原值
            "category": category,         # 用户原值 "运动" → 文件名 "运动_..."
            "l1_category": l1_target,    # 映射后值 "健康" → 内部过滤用
            "start": start, "end": end,
            "total_minutes": total,
            "title": f"类别深挖 · {l1_target} · {start} ~ {end}",
            "subtitle": f"{days_count} 天活跃,日均 {_fmt_dur(daily_avg)}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "days": sorted_dates,
        "total_minutes": total,
        "daily_avg": daily_avg,
        "heatmap": matrix,
        "records": _build_full_records(cat_records),
        "ai_questions": ai_questions_for_category(l1_target, days_count, total, daily_avg),
        "copy_prompt": _build_record_copy_prompt(
            "record-category",
            {"date": start, "start": start, "end": end,
             "category": l1_target, "total_minutes": total},
            cat_records, [],
        ),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ {l1_target} 类别深挖数据已生成",
    }


def render_record_anomaly(window_days: int = 7) -> dict:
    """T5 异常:默认 7 天 vs 近 30 天基线 + 7 维雷达 SVG"""
    from schedule_db import get_records_range
    from calculations import detect_anomalies, build_dimension_aggregates, ai_questions_for_anomaly
    from datetime import date as _d, timedelta as _td
    import math

    today = _d.today()
    window_start = (today - _td(days=window_days - 1)).isoformat()
    today_iso = today.isoformat()
    baseline_start = (today - _td(days=30)).isoformat()

    cur_records = get_records_range(window_start, today_iso)
    baseline_records = get_records_range(baseline_start, today_iso)

    anomalies = detect_anomalies(cur_records, baseline_records, threshold=0.2)

    HEALTH_DIMS = ["维持", "健康", "工作", "学习", "调整", "日常", "投入"]
    cur = build_dimension_aggregates(cur_records)
    base = build_dimension_aggregates(baseline_records)
    cx, cy, r = 200, 200, 130
    n = len(HEALTH_DIMS)
    svg = [f'<svg class="radar-svg" viewBox="0 0 400 420">']
    for r2 in [0.2, 0.4, 0.6, 0.8, 1.0]:
        pts = []
        for i in range(n):
            a = -math.pi/2 + i * 2*math.pi/n
            pts.append(f"{cx + r*r2*math.cos(a):.1f},{cy + r*r2*math.sin(a):.1f}")
        svg.append(f'<polygon points="{" ".join(pts)}" fill="none" stroke="#d2d2d7" stroke-width="0.5"/>')
    for i, d in enumerate(HEALTH_DIMS):
        a = -math.pi/2 + i * 2*math.pi/n
        x2, y2 = cx + r*math.cos(a), cy + r*math.sin(a)
        svg.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#d2d2d7" stroke-width="0.5"/>')
        svg.append(f'<text class="radar-axis" x="{x2:.1f}" y="{y2:.1f}" text-anchor="middle" dy="4">{d}</text>')
    pts_curr, pts_base = [], []
    max_v = max(max(cur.values(), default=1), max(base.values(), default=1), 1)
    for i, d in enumerate(HEALTH_DIMS):
        a = -math.pi/2 + i * 2*math.pi/n
        vc = cur.get(d, 0) / max_v
        vb = base.get(d, 0) / max_v
        pts_curr.append(f"{cx + r*vc*math.cos(a):.1f},{cy + r*vc*math.sin(a):.1f}")
        pts_base.append(f"{cx + r*vb*math.cos(a):.1f},{cy + r*vb*math.sin(a):.1f}")
    svg.append(f'<polygon points="{" ".join(pts_base)}" fill="#8E8E93" fill-opacity="0.2" stroke="#8E8E93" stroke-width="1"/>')
    svg.append(f'<polygon points="{" ".join(pts_curr)}" fill="#007AFF" fill-opacity="0.3" stroke="#007AFF" stroke-width="2"/>')
    svg.append('<text x="200" y="395" text-anchor="middle" font-size="11" fill="#6e6e73">蓝=当前 | 灰=基线(30天)</text>')
    svg.append('</svg>')
    radar_svg = "".join(svg)

    payload = {
        "meta": {
            "mode": "record-anomaly",
            "window": window_days,
            "title": f"异常检测 · 最近 {window_days} 天",
            "subtitle": f"对比基线:近 30 天均值,阈值 ±20%",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "anomalies": anomalies,
        "radar_svg": radar_svg,
        "ai_questions": ai_questions_for_anomaly(anomalies, window_days),
        "copy_prompt": _build_record_copy_prompt(
            "record-anomaly",
            {"date": datetime.now().strftime("%Y-%m-%d"), "window": window_days},
            cur_records, [],
            {"anomalies": anomalies},
        ),
        "errors": [],
    }
    return {
        "status": "ok",
        "data": payload,
        "message": f"✓ 异常检测完成,检出 {len(anomalies)} 项",
    }


def check_offline() -> bool:
    """T07 · 网络连通性探测(offline 状态判定)

    当前实现:简单的 timeout 1s 检测(避免阻塞)。
    返回 True = 在线,False = 离线。
    后续可替换为 feishu_probe() 调用。
    """
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=1).close()
        return True
    except OSError:
        return False


def render_replay(start: str, end: str, ai_engine: str = "mock") -> dict:
    """Phase E · 复盘 start-end · 跨域 dual-domain 分析(任意 start-end 区间)

    4 段叙事骨架(T03-T06 各自填充实数据):
      - record_aggregate: 分类时长 / 7 维趋势 / 24h 热力图 (T03 填充)
      - plan_aggregate:   completion 6 类分布 + 分类拆解 (T04 填充)
      - cross_domain:     planned_actual_pairs / unexecuted / unexpected / overrun (T05 填充)
      - ai_insights:      mock 异常检测 + 周期对比 + 建议 (T06 填充)
      - copy_prompt:      4 部分结构(单工铁律,总纲 §04 原则 10)

    5 状态 fallback(T01 + T07):
      - empty: 两域都空(刚装完数据库)
      - incomplete: 单域有数据(缺失域标 incomplete=True + 友好提示)
      - ok: 两域数据完整
      - error: DB 错误(ConnectionError 等)
      - offline: 网络不通(单文件 HTML 仍可查看,主流程不依赖网络)

    Args:
        start: 起始日期 YYYY-MM-DD
        end:   结束日期 YYYY-MM-DD (含)
        ai_engine: AI 洞察引擎,默认 "mock"(规则生成,无需外部 LLM)。

    Returns:
        {"status": "ok"|"empty"|"incomplete"|"error"|"offline", "data": payload|None, "message": str}
    """
    from schedule_db import _normalize_date, get_records_range, get_plan_events_range

    start = _normalize_date(start)
    end = _normalize_date(end)

    # === T07 error 状态:DB 异常 catch ===
    try:
        records = get_records_range(start, end)
        plans = get_plan_events_range(start, end, include_inactive=False)
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"数据库查询失败: {type(e).__name__}: {e}",
        }

    total_records = len(records)
    total_minutes = sum((r.get("duration_minutes") or 0) for r in records)
    days = sorted({r.get("date", "") for r in records} | {p.get("date", "") for p in plans})
    # days_count: 有数据用实际天数,空数据按 start-end 区间长度计算(总纲 §04 原则 11)
    if days:
        days_count = len(days)
    else:
        from datetime import date as _date, timedelta as _td
        try:
            s = _date.fromisoformat(start)
            e = _date.fromisoformat(end)
            days_count = max(1, (e - s).days + 1)
        except ValueError:
            days_count = 1

    # === T03 · record 聚合段 ===
    # 复用 calculations 模块算法:summary_items / trend / heatmap
    from calculations import (
        aggregate_by_category, build_dimension_aggregates, build_trend_series,
        build_24h_heatmap, cat_emoji, cat_color, fmt_dur,
    )
    HEALTH_DIMS = ["维持", "健康", "工作", "学习", "调整", "日常", "投入"]

    has_records = total_records > 0
    has_plans = len(plans) > 0

    cat_minutes = aggregate_by_category(records)
    sorted_cats = sorted(cat_minutes.items(), key=lambda x: -x[1])
    TOP_N_VISIBLE = 10  # 默认 Top 10 + "展开全部" 按钮(T08 视觉打磨会实现按钮交互)
    summary_items = [
        {
            "category": cat, "emoji": cat_emoji(cat), "color": cat_color(cat),
            "total_minutes": int(mins), "duration_text": fmt_dur(int(mins)),
            "pct": round((mins / total_minutes * 100) if total_minutes else 0.0, 1),
        }
        for cat, mins in sorted_cats
    ]

    trend_series = [
        {"dim": d, "series": build_trend_series(records, d)}
        for d in HEALTH_DIMS
    ]
    # T03 7 维趋势仅取非空 dim(T08 视觉打磨会扩展为 SVG 多色折线)
    trend_filtered = [t for t in trend_series if t["series"]]

    heatmap_matrix, heatmap_dates = (build_24h_heatmap(records) if records else ([], []))
    # heatmap_matrix: [[{cat, mins, color} for h in 24] for d in N]
    # heatmap_dates: [date_str for d in N](build_24h_heatmap 返回 tuple)
    # 转为 [{date, hours: [{cat, mins, color}]}] 结构供前端使用
    heatmap = []
    for i, day_24h in enumerate(heatmap_matrix):
        day_date = heatmap_dates[i] if i < len(heatmap_dates) else ""
        heatmap.append({"date": day_date, "hours": day_24h})

    record_aggregate = {
        "summary_items": summary_items,
        "top_n_visible": min(TOP_N_VISIBLE, len(summary_items)),
        "top_n_total": len(summary_items),
        "trend": trend_filtered,
        "heatmap": heatmap,
        "dim_totals": build_dimension_aggregates(records),
    }

    # === T04 · plan 聚合段 ===
    # 6 类 completion 分布 + 按分类拆解 + 整体完成率
    COMPLETION_KEYS = ["已完成", "已完成(超时)", "部分完成",
                       "未完成", "未完成(不可抗力)", "未复盘"]
    completion_distribution = {k: 0 for k in COMPLETION_KEYS}
    by_category: dict[str, dict[str, int]] = {}  # cat -> {completion_key: count}
    for p in plans:
        comp = p.get("completion")
        key = comp if comp in COMPLETION_KEYS[:5] else "未复盘"
        completion_distribution[key] += 1
        cat = p.get("category") or "(未分类)"
        if cat not in by_category:
            by_category[cat] = {k: 0 for k in COMPLETION_KEYS}
        by_category[cat][key] += 1

    # 按分类拆解:[{category, total, completed, completion_rate}]
    completion_by_category = []
    for cat, dist in by_category.items():
        total = sum(dist.values())
        # 已完成 = "已完成" 类(按时完成,不包含超时/部分完成)
        completed = dist["已完成"]
        rate = (completed / total) if total > 0 else 0.0
        completion_by_category.append({
            "category": cat, "total": total, "completed": completed,
            "completion_rate": round(rate, 3),
        })
    # 按 total 降序
    completion_by_category.sort(key=lambda c: -c["total"])

    # 整体完成率:已完成 / (已完成 + 未完成) 二分
    total_events = len(plans)
    completed_count = sum(1 for p in plans if p.get("completion") == "已完成")
    not_completed = sum(1 for p in plans if p.get("completion") in ("未完成", "未完成(不可抗力)"))
    overall_rate = (completed_count / (completed_count + not_completed)) if (completed_count + not_completed) > 0 else 0.0

    plan_aggregate = {
        "completion_distribution": completion_distribution,
        "completion_by_category": completion_by_category,
        "completion_rate": round(overall_rate, 3),
    }

    # === T05 · 跨域对比段 ===
    # 4 类清单:planned_actual_pairs + unexecuted_plans + unexpected_records + overrun_plans
    # 算法核心:按 (date, plan_id) 做 record 聚合 → plan vs 实际时长对比
    from datetime import datetime as _dt, time as _time
    def _hhmm_to_min(s: str) -> int:
        """'HH:MM' → 从 00:00 起的分钟数(字符串解析避免 datetime 慢路径)"""
        try:
            h, m = s.strip().split(":")
            return int(h) * 60 + int(m)
        except Exception:
            return 0

    def _plan_duration_min(p: dict) -> int:
        return max(0, _hhmm_to_min(p.get("time_end", "00:00")) - _hhmm_to_min(p.get("time_start", "00:00")))

    # 按 date 分组 records(便于同日期 plan 配对)
    records_by_date: dict[str, list[dict]] = {}
    for r in records:
        records_by_date.setdefault(r.get("date", ""), []).append(r)

    planned_actual_pairs: list[dict] = []
    unexecuted_plans: list[dict] = []
    unexpected_records: list[dict] = []
    overrun_plans: list[dict] = []

    UNEXECUTED_COMPLETIONS = {"未完成", "未完成(不可抗力)", "部分完成"}
    OVERRUN_RATIO = 1.2  # 实际超出计划 20% 触发 overrun 标注

    for p in plans:
        pid = p["id"]
        p_date = p.get("date", "")
        p_start = _hhmm_to_min(p.get("time_start", "00:00"))
        p_end = _hhmm_to_min(p.get("time_end", "00:00"))
        plan_dur = max(0, p_end - p_start)

        # 同日期 record 时间重叠 → 计算实际时长(取交集)
        same_date_records = records_by_date.get(p_date, [])
        actual_dur = 0
        for r in same_date_records:
            r_start = _hhmm_to_min(r.get("time_start", "00:00"))
            r_end = _hhmm_to_min(r.get("time_end", "00:00"))
            overlap_start = max(p_start, r_start)
            overlap_end = min(p_end, r_end)
            if overlap_end > overlap_start:
                actual_dur += (overlap_end - overlap_start)

        comp = p.get("completion")
        # 1. planned_actual_pairs:plan 完成状态任意 + 同日有时间重叠的 record
        if actual_dur > 0:
            planned_actual_pairs.append({
                "plan_id": pid, "title": p.get("title", ""),
                "plan_duration_minutes": plan_dur,
                "actual_duration_minutes": actual_dur,
                "delta_minutes": actual_dur - plan_dur,
                "completion": comp,
            })

        # 2. unexecuted_plans:plan 存在但完成状态 ∈ {未完成 / 未完成(不可抗力) / 部分完成}
        if comp in UNEXECUTED_COMPLETIONS:
            unexecuted_plans.append({
                "plan_id": pid, "title": p.get("title", ""),
                "time_start": p.get("time_start", ""),
                "time_end": p.get("time_end", ""),
                "category": p.get("category", ""),
                "completion": comp,
                "completion_note": p.get("completion_note", "") or "",
            })

        # 3 & 4. overrun_plans:record 总时长超出 plan 20%(无论 plan 完成状态)
        if plan_dur > 0:
            # 取所有跟 plan 时间重叠的 record 的总 duration
            record_total_dur = 0
            for r in same_date_records:
                r_start = _hhmm_to_min(r.get("time_start", "00:00"))
                r_end = _hhmm_to_min(r.get("time_end", "00:00"))
                if max(p_start, r_start) < min(p_end, r_end):
                    # 用 record 的 duration_minutes 字段(优先) 或 从时间区间算
                    dur = r.get("duration_minutes")
                    if dur is None:
                        dur = max(0, r_end - r_start)
                    record_total_dur += dur
            if record_total_dur > 0:
                ratio = record_total_dur / plan_dur
                if ratio >= OVERRUN_RATIO:
                    overrun_plans.append({
                        "plan_id": pid, "title": p.get("title", ""),
                        "plan_duration_minutes": plan_dur,
                        "actual_duration_minutes": record_total_dur,
                        "ratio": round(ratio, 2),
                        "severity": "high" if ratio >= 1.5 else "medium",
                    })

    # 5. unexpected_records:record 无对应 plan
    for r in records:
        r_date = r.get("date", "")
        r_start = _hhmm_to_min(r.get("time_start", "00:00"))
        r_end = _hhmm_to_min(r.get("time_end", "00:00"))
        matched = False
        for p in plans:
            if p.get("date", "") != r_date:
                continue
            p_start = _hhmm_to_min(p.get("time_start", "00:00"))
            p_end = _hhmm_to_min(p.get("time_end", "00:00"))
            if max(p_start, r_start) < min(p_end, r_end):
                matched = True
                break
        if not matched:
            unexpected_records.append({
                "record_id": r.get("id"),
                "time_start": r.get("time_start", ""),
                "time_end": r.get("time_end", ""),
                "category": r.get("category", ""),
                "activity": r.get("activity", ""),
                "duration_minutes": r.get("duration_minutes") or 0,
            })

    cross_domain = {
        "planned_actual_pairs": planned_actual_pairs,
        "unexecuted_plans": unexecuted_plans,
        "unexpected_records": unexpected_records,
        "overrun_plans": overrun_plans,
    }

    # === T06 · AI 洞察段(mock 算法,接口预留 ai_engine="mock"|"llm")===
    # pragmatic:当前 fixtures 没有过去数据,baseline = 区间前半段均值,current = 后半段
    # spec aspirational:上周/上月/上年同期对比 → 后续 LLM 接入时拉历史 DB
    anomalies: list[dict] = []
    periodic_compare: list[dict] = []
    suggestions: list[dict] = []

    if records:
        # 按分类统计总时长
        cat_total_min: dict[str, int] = {}
        cat_date_min: dict[str, dict[str, int]] = {}  # cat -> {date -> mins}
        for r in records:
            cat = r.get("category", "")
            mins = r.get("duration_minutes") or 0
            d_str = r.get("date", "")
            cat_total_min[cat] = cat_total_min.get(cat, 0) + mins
            cat_date_min.setdefault(cat, {})
            cat_date_min[cat][d_str] = cat_date_min[cat].get(d_str, 0) + mins

        # 区间按日期拆分前后半
        sorted_dates = sorted({r.get("date", "") for r in records if r.get("date")})
        n_days = len(sorted_dates)
        if n_days >= 2:
            half = n_days // 2
            baseline_dates = set(sorted_dates[:half])
            current_dates = set(sorted_dates[half:])

            # === anomalies:每分类 baseline vs current ratio ===
            for cat, total_min in cat_total_min.items():
                date_min = cat_date_min[cat]
                baseline_mins = sum(m for d, m in date_min.items() if d in baseline_dates)
                current_mins = sum(m for d, m in date_min.items() if d in current_dates)
                if baseline_mins == 0 and current_mins == 0:
                    continue
                # ratio = current / baseline(baseline=0 用 total/2 兜底)
                base_val = baseline_mins if baseline_mins > 0 else max(1, total_min // 2)
                ratio = current_mins / base_val
                # 高阈值:ratio >= 2.0 或 ratio <= 0.5(异常下降)
                # 中阈值:1.5 <= ratio < 2.0 或 0.67 <= ratio < 0.5 的镜像
                severity = None
                if ratio >= 2.0 or ratio <= 0.5:
                    severity = "high"
                elif ratio >= 1.5 or (0.4 < ratio <= 0.67):
                    severity = "medium"
                if severity:
                    anomalies.append({
                        "category": cat,
                        "current_value": current_mins,
                        "baseline_value": baseline_mins,
                        "ratio": round(ratio, 2),
                        "severity": severity,
                        "direction": "up" if ratio >= 1.0 else "down",
                    })

            # === periodic_compare:每分类 本区间 vs 前半段 baseline ===
            for cat, total_min in cat_total_min.items():
                date_min = cat_date_min[cat]
                baseline_mins = sum(m for d, m in date_min.items() if d in baseline_dates)
                current_mins = sum(m for d, m in date_min.items() if d in current_dates)
                if baseline_mins == 0:
                    delta_pct = 100.0 if current_mins > 0 else 0.0
                else:
                    delta_pct = round((current_mins - baseline_mins) / baseline_mins * 100, 1)
                periodic_compare.append({
                    "category": cat,
                    "period": "current_vs_first_half",
                    "current_period": current_mins,
                    "previous_period": baseline_mins,
                    "delta_pct": delta_pct,
                })

            # === suggestions:基于 anomalies 触发规则生成器(5-8 条)===
            for a in anomalies:
                cat = a["category"]
                ratio = a["ratio"]
                direction = a["direction"]
                severity = a["severity"]
                # 规则 1:工作骤增
                if cat.startswith("工作") and direction == "up" and ratio >= 1.5:
                    suggestions.append({
                        "trigger": f"工作时长骤增 +{int((ratio-1)*100)}%",
                        "text": f"⚠️ {cat} 时长比上半期增加 {int((ratio-1)*100)}%,建议调整时间块或减少会议。",
                        "severity": severity,
                    })
                # 规则 2:维持(睡眠)骤降
                elif cat.startswith("维持") and direction == "down" and ratio <= 0.67:
                    pct = int((1 - ratio) * 100)
                    suggestions.append({
                        "trigger": f"维持(睡眠)骤降 -{pct}%",
                        "text": f"😴 {cat} 时长比上半期下降 {pct}%,建议关注作息规律。",
                        "severity": severity,
                    })
                # 规则 3:健康骤降
                elif cat.startswith("健康") and direction == "down" and ratio <= 0.67:
                    pct = int((1 - ratio) * 100)
                    suggestions.append({
                        "trigger": f"健康投入骤降 -{pct}%",
                        "text": f"🏃 {cat} 时长比上半期下降 {pct}%,建议恢复运动习惯。",
                        "severity": severity,
                    })
                # 规则 4:学习骤降
                elif cat.startswith("学习") and direction == "down" and ratio <= 0.67:
                    pct = int((1 - ratio) * 100)
                    suggestions.append({
                        "trigger": f"学习投入骤降 -{pct}%",
                        "text": f"📖 {cat} 时长比上半期下降 {pct}%,建议重启学习节奏。",
                        "severity": severity,
                    })
                # 规则 5:调整(娱乐)骤增
                elif cat.startswith("调整") and direction == "up" and ratio >= 1.5:
                    suggestions.append({
                        "trigger": f"调整(娱乐)骤增 +{int((ratio-1)*100)}%",
                        "text": f"🎮 {cat} 时长比上半期增加 {int((ratio-1)*100)}%,建议控制娱乐时长。",
                        "severity": severity,
                    })
                # 规则 6:通用 — 任意方向显著变化
                else:
                    arrow = "↑" if direction == "up" else "↓"
                    pct = abs(int((ratio - 1) * 100)) if direction == "up" else abs(int((1 - ratio) * 100))
                    suggestions.append({
                        "trigger": f"{cat} {arrow}{pct}%",
                        "text": f"📊 {cat} 时长较上半期变化 {arrow}{pct}%,建议关注持续性。",
                        "severity": severity,
                    })

    ai_insights = {
        "anomalies": anomalies,
        "periodic_compare": periodic_compare,
        "suggestions": suggestions,
    }

    # === T07 · 5 状态 fallback 完整 ===
    # offline 探测(主流程不依赖网络,但标记状态)
    online = check_offline()
    status_badge = "📡 offline" if not online else None  # None = 不强制标 offline,留给下游判定

    # 空骨架 payload(各状态共用基础)
    def _make_meta(extra: dict) -> dict:
        base = {
            "mode": "replay",
            "start": start, "end": end, "days": days_count,
            "total_records": total_records, "total_minutes": total_minutes,
            "title": f"区间复盘 · {start} ~ {end}",
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status_badge": status_badge,
        }
        base.update(extra)
        return base

    def _make_record_aggregate(incomplete: bool = False) -> dict:
        base_ra = {
            "summary_items": summary_items, "trend": trend_filtered,
            "heatmap": heatmap, "dim_totals": build_dimension_aggregates(records),
            "top_n_visible": min(TOP_N_VISIBLE, len(summary_items)),
            "top_n_total": len(summary_items),
            "incomplete": incomplete,
        }
        return base_ra

    def _make_plan_aggregate(incomplete: bool = False) -> dict:
        base_pa = {
            "completion_distribution": completion_distribution,
            "completion_by_category": completion_by_category,
            "completion_rate": round(overall_rate, 3),
            "incomplete": incomplete,
        }
        return base_pa

    def _make_cross_domain() -> dict:
        return {
            "planned_actual_pairs": planned_actual_pairs,
            "unexecuted_plans": unexecuted_plans,
            "unexpected_records": unexpected_records,
            "overrun_plans": overrun_plans,
        }

    # empty: 两域都空
    if not has_records and not has_plans:
        return {
            "status": "empty",
            "data": {
                "meta": _make_meta({
                    "total_records": 0, "total_minutes": 0,
                    "subtitle": f"{days_count} 天 · 无数据",
                    "status_badge": status_badge or "📭 empty",
                }),
                "record_aggregate": {
                    "summary_items": [], "trend": [], "heatmap": [],
                    "top_n_visible": 0, "top_n_total": 0,
                    "dim_totals": {d: 0 for d in HEALTH_DIMS},
                    "incomplete": False,
                },
                "plan_aggregate": {
                    "completion_distribution": {
                        "已完成": 0, "已完成(超时)": 0, "部分完成": 0,
                        "未完成": 0, "未完成(不可抗力)": 0, "未复盘": 0,
                    },
                    "completion_by_category": [],
                    "completion_rate": 0.0,
                    "incomplete": False,
                },
                "cross_domain": {
                    "planned_actual_pairs": [], "unexecuted_plans": [],
                    "unexpected_records": [], "overrun_plans": [],
                },
                "ai_insights": {"anomalies": [], "periodic_compare": [], "suggestions": []},
                "copy_prompt": _build_replay_copy_prompt(start, end, 0, 0, 0, 0),
                "errors": [],
            },
            "message": f"📭 {start} ~ {end} 区间无数据(空态)",
        }

    # incomplete: 单域有数据 → 缺失域标 incomplete=True
    if has_records and not has_plans:
        subtitle = f"{days_count} 天 · {total_records} 条记录 · 0 条计划(计划域缺失)"
        msg = f"⚠️ {start} ~ {end} 区间只有作息记录,无日程计划(计划域 incomplete)"
    elif has_plans and not has_records:
        subtitle = f"{days_count} 天 · 0 条记录 · {len(plans)} 条计划(记录域缺失)"
        msg = f"⚠️ {start} ~ {end} 区间只有日程计划,无作息记录(记录域 incomplete)"
    else:
        subtitle = f"{days_count} 天 · {total_records} 条记录 · {total_minutes} 分钟"
        msg = f"✓ {start} ~ {end} 区间复盘数据已生成"

    payload = {
        "meta": _make_meta({
            "total_records": total_records, "total_minutes": total_minutes,
            "subtitle": subtitle,
            "status_badge": status_badge or (
                "⚠️ incomplete" if (has_records != has_plans) else "✅ ok"
            ),
        }),
        "record_aggregate": _make_record_aggregate(incomplete=not has_records),
        "plan_aggregate": _make_plan_aggregate(incomplete=not has_plans),
        "cross_domain": _make_cross_domain(),
        "ai_insights": ai_insights,
        "copy_prompt": _build_replay_copy_prompt(
            start, end, total_records, total_minutes,
            sum(1 for p in plans if p.get("completion") == "已完成"),
            len(plans),
        ),
        "errors": [],
    }

    # 5 状态判定优先级:incomplete > offline > ok
    if has_records != has_plans:
        status = "incomplete"
    elif not online:
        status = "offline"
    else:
        status = "ok"

    return {
        "status": status,
        "data": payload,
        "message": msg,
    }


def _build_replay_copy_prompt(start: str, end: str, total_records: int,
                              total_minutes: int, completed_events: int,
                              total_events: int) -> str:
    """T01 · copy_prompt 4 部分结构(单工铁律,总纲 §04 原则 10)骨架。

    T08 视觉打磨阶段会完善 prompt 内容(参考 record-range 的 _build_record_copy_prompt)。
    T01 仅给骨架,让契约不空。
    """
    completion_rate = (completed_events / total_events * 100) if total_events else 0.0
    return (
        f"① 场景: 复盘 {start} ~ {end} 区间的作息与计划执行情况\n"
        f"② 数据: {total_records} 条记录,总时长 {total_minutes} 分钟,"
        f"计划完成 {completed_events}/{total_events} ({completion_rate:.1f}%)\n"
        f"③ 用户原话: 请帮我复盘这一段\n"
        f"④ 来源: schedule_replay.html 生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')},"
        f"数据源 schedule_records + schedule_plans"
    )


def render_and_write(payload: dict, output_path: Path = None) -> dict:
    """渲染 + 写入文件,返回 {status, data:{file_path, bytes}, message}"""
    template_map = {
        "list-events":     "schedule_list_events.html",
        "query-plans":     "schedule_list_events.html",
        "plan-preview":    "schedule_plan_preview.html",  # 商量计划预览(过程型首批落地,2026-07-24)
        "plan-review":     "schedule_plan_review.html",   # 复盘报告(过程型第2款,2026-07-24)
        "record-receipt":  "schedule_record_receipt.html", # 漂亮回执(回执型首款,2026-07-24)
        "record-receipt-edit":  "schedule_record_receipt_edit.html", # 纠正记录回执(回执型第2款,蓝调,diff 视图,2026-07-24)
        "record-result":   "record_result.html",   # 记录三件套结果 HTML(T2 · 2026-08-09 · G1-A1)
        "plan-receipt":     "schedule_plan_receipt.html",   # 改/删计划回执(回执型第2款,2026-07-24)
        "plan-receipt-add": "schedule_plan_receipt_add.html", # 补计划回执(回执型第3款,2026-07-24)
        "plan-receipt-write": "schedule_plan_receipt_write.html", # 写摘要回执(回执型第4款,2026-07-24)
        "record-report":   "schedule_record_day.html",   # 兼容旧 CLI
        "record-day":      "schedule_record_day.html",
        "record-range":    "schedule_record_range.html",
        "record-compare":  "schedule_record_compare.html",
        "record-category": "schedule_record_category.html",
        "record-anomaly":  "schedule_record_anomaly.html",
        "record-detail":   "schedule_record_detail.html",  # 详情页(人工智能推理溯源)
        # === Phase E · 复盘 start-end · 跨域 dual-domain 分析 ===
        "replay":          "schedule_replay.html",
    }
    mode = payload.get("data", {}).get("meta", {}).get("mode", "list-events")
    template_name = template_map.get(mode)
    if not template_name:
        return {
            "status": "error",
            "data": None,
            "message": f"未知 mode: {mode}",
        }

    if output_path is None:
        output_path = default_output_path(payload["data"]["meta"])

    try:
        final_path = inject_into_template(template_name, payload, output_path)
    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": f"渲染失败: {type(e).__name__}: {e}",
        }

    size_kb = final_path.stat().st_size // 1024
    return {
        "status": "ok",
        "data": {
            "file_path": str(final_path),
            "size_kb": size_kb,
            "mode": mode,
        },
        "message": f"✓ HTML 已写入: {final_path} ({size_kb} KB)",
    }


if __name__ == "__main__":
    print("schedule_html_render.py — 渲染器模块")
    print("用法: 由 schedule_cli.py 的 render-list-events / render-query-plans / render-record-report 调用")
    print("直接运行无副作用")
