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
    读模板 → JSON 注入 → 写副本。
    严格遵循手册 §8:生成副本,不污染原模板。
    """
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"模板不存在: {template_path}")

    template_text = template_path.read_text(encoding="utf-8")
    payload_str = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_str = payload_str.replace("</", "<\\/")

    if "<script id=\"payload\" type=\"application/json\">" not in template_text:
        raise RuntimeError(
            f"模板 {template_name} 缺少 <script id=\"payload\" type=\"application/json\"></script> 锚点"
        )

    injected = template_text.replace(
        "<script id=\"payload\" type=\"application/json\"></script>",
        '<script id="payload" type="application/json">'
        + payload_str
        + "</script>",
        1,
    )
    # 替换 {{date}} / {{payload}} 等占位符(若模板里有)
    injected = injected.replace("{{ DATE }}", str(payload.get("data", {}).get("meta", {}).get("date", "")))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(injected, encoding="utf-8")
    return output_path


def default_output_path(meta: dict) -> Path:
    """根据 meta 决定默认输出文件名"""
    skill_dir = SKILL_DIR
    out_dir = skill_dir / "reports"
    mode = meta.get("mode", "list-events")
    if mode == "list-events":
        date = meta.get("date", "unknown")
        return out_dir / f"schedule_list_{date}.html"
    if mode == "query-plans":
        dates = meta.get("dates", [])
        if len(dates) == 1:
            return out_dir / f"schedule_query_{dates[0]}.html"
        return out_dir / f"schedule_query_{dates[0]}_to_{dates[-1]}.html"
    return out_dir / "schedule_view.html"


def render_and_write(payload: dict, output_path: Path = None) -> dict:
    """渲染 + 写入文件,返回 {status, data:{file_path, ...}, message}"""
    template_map = {
        "list-events": "schedule_list_events.html",
        "query-plans": "schedule_list_events.html",
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
    print("用法: 由 schedule_cli.py 的 render-list-events / render-query-plans 调用")
    print("直接运行无副作用")
