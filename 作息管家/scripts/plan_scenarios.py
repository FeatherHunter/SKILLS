#!/usr/bin/env python3
"""plan_scenarios.py — 制定次日计划域模块(实施 T5 · 真新增自包含)

通过渐进式注册通道(T1 · schedule_cli.py 末尾 discover_domain_commands)自动挂载:
  COMMANDS = {"plan-result": cmd_plan_result}

命令:plan-result <日期> --json @plan.json [--history-days N]
  输入:候选 24h 事件 list(AI 多轮对话产物,与 render-plans-preview 同契约)
       [{time_start, time_end, title, notes?, category?}, ...]
  输出:plan_result.html —— 时间轴 + 分类色带 + 历史作息贴合提示(强化 #17 商量计划)
  流程:生成 → 调整 → 再生成(多轮)走既有商量计划流程;本命令每次渲染一版,
       同秒多次生成自动 _2/_3 命名(不覆盖),满意后复制 prompt → AI 写库。

历史贴合提示(第一性):
  过去 N 天(默认 7)schedule_records → 按小时聚合历史习惯(分类计数降序)
  → 对每个候选事件取覆盖小时段的历史主要分类对比:
      match = 候选分类命中历史主要分类(贴合) ✅
      drift = 不一致(偏离,提示历史上通常做什么) ⚠️
      none  = 该时段无历史记录(无参考,缺数据兜底不降级) ➖
"""
import json
import sys
from datetime import date as _date
from datetime import datetime
from datetime import timedelta
from pathlib import Path

DEFAULT_HISTORY_DAYS = 7


# ===== 历史习惯聚合(纯函数,可单测) =====

def _to_min(hhmm):
    h, m = (int(x) for x in hhmm.split(":"))
    return h * 60 + m


def _hour_span(time_start, time_end):
    """事件覆盖的小时集合(按起始小时取整,半开区间 [sh, eh))"""
    sh = _to_min(time_start) // 60
    eh = (_to_min(time_end) + 59) // 60
    return list(range(max(sh, 0), min(eh, 24)))


def build_history_habits(records, history_days=DEFAULT_HISTORY_DAYS):
    """历史记录 → 每小时习惯。

    Args:
        records: schedule_records 行 list(每行含 time_start/time_end/category)
        history_days: 窗口天数(仅用于描述,不做过滤——调用方已按日期拉取)

    Returns:
        dict[int, list[tuple[str, int]]]: hour → [(category, count), ...] 计数降序
        无记录的 hour 不出现。
    """
    habits = {}
    for r in records:
        try:
            hours = _hour_span(r["time_start"], r["time_end"])
        except (KeyError, ValueError):
            continue
        cat = r.get("category") or "未知"
        for h in hours:
            bucket = habits.setdefault(h, {})
            bucket[cat] = bucket.get(cat, 0) + 1
    return {
        h: sorted(cnt.items(), key=lambda kv: kv[1], reverse=True)
        for h, cnt in habits.items()
    }


def fit_events(plan_events, habits):
    """候选事件 vs 历史习惯 → 贴合判定列表。

    Returns:
        list[dict]: 每段事件:
            index / time_start / time_end / title / category
            fit: "match" | "drift" | "none"
            history_top: 历史主要分类或 None
            hint: 人类可读提示
    """
    results = []
    for i, ev in enumerate(plan_events):
        try:
            hours = _hour_span(ev["time_start"], ev["time_end"])
        except (KeyError, ValueError):
            results.append({
                "index": i,
                "time_start": ev.get("time_start", ""),
                "time_end": ev.get("time_end", ""),
                "title": ev.get("title", ""),
                "category": ev.get("category", ""),
                "fit": "none",
                "history_top": None,
                "hint": "时段无法解析,无历史参考",
            })
            continue

        # 聚合事件覆盖小时段的历史分类计数
        agg = {}
        for h in hours:
            for cat, cnt in habits.get(h, []):
                agg[cat] = agg.get(cat, 0) + cnt
        if not agg:
            results.append({
                "index": i,
                "time_start": ev["time_start"],
                "time_end": ev["time_end"],
                "title": ev.get("title", ""),
                "category": ev.get("category", ""),
                "fit": "none",
                "history_top": None,
                "hint": "该时段近几天无历史记录(全新安排,无参考)",
            })
            continue

        history_top = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[0]
        top_cat = history_top[0]
        cand_cat = ev.get("category") or ""
        if cand_cat and cand_cat == top_cat:
            fit = "match"
            hint = f"贴合历史习惯:该时段近几天主要是「{top_cat}」"
        elif cand_cat:
            fit = "drift"
            hint = (f"与历史习惯不同:历史该时段主要「{top_cat}」({history_top[1]} 次),"
                    f"本次计划「{cand_cat}」")
        else:
            fit = "drift"
            hint = f"未标分类;历史该时段主要「{top_cat}」({history_top[1]} 次)"
        results.append({
            "index": i,
            "time_start": ev["time_start"],
            "time_end": ev["time_end"],
            "title": ev.get("title", ""),
            "category": cand_cat,
            "fit": fit,
            "history_top": top_cat,
            "hint": hint,
        })
    return results


def fit_rate(fits):
    """贴合率 = match / (match + drift);无任何参考(none 全)返回 None。"""
    judged = [f for f in fits if f["fit"] in ("match", "drift")]
    if not judged:
        return None
    matched = sum(1 for f in judged if f["fit"] == "match")
    return round(matched / len(judged) * 100, 1)


# ===== 渲染 =====

def _load_json_arg(json_path):
    """读 --json 参数:@file.json 或 -(stdin)"""
    if json_path == "-":
        return sys.stdin.read(), None
    p = Path(json_path[1:]) if json_path.startswith("@") else Path(json_path)
    if not p.exists():
        return None, f"JSON 文件不存在: {p}"
    return p.read_text(encoding="utf-8"), None


def _validate_events(plan_events):
    if not isinstance(plan_events, list):
        return "plan_events 必须是 list"
    if len(plan_events) == 0:
        return "plan_events 至少 1 条"
    for i, ev in enumerate(plan_events):
        if not isinstance(ev, dict):
            return f"第 {i+1} 条不是 dict"
        for k in ("time_start", "time_end", "title"):
            if k not in ev:
                return f"第 {i+1} 条缺字段: {k}"
    return None


def _build_copy_prompt(date_str, plan_events, locked, fits, conflicts,
                       history_days, rate, now_str):
    """4 部分 prompt(单工铁律 · 总纲 §04 原则 10 + 08 §4)"""
    plan_json_str = json.dumps(plan_events, ensure_ascii=False, indent=2)
    locked_summary = ""
    if locked:
        locked_summary = "\n  - 已锁定事件(" + str(len(locked)) + " 段 · 写库时保留保护):\n" + \
            "\n".join(f"    - {e['time_start']}–{e['time_end']} {e.get('title','—')}"
                      for e in locked) + "\n"
    fit_summary = ""
    if fits:
        lines = []
        for f in fits:
            mark = {"match": "✅贴合", "drift": "⚠️偏离", "none": "➖无参考"}[f["fit"]]
            lines.append(
                f"    - {f['time_start']}–{f['time_end']} {f.get('title','—')}"
                f" [{f.get('category') or '未分类'}] {mark} {f['hint']}")
        fit_summary = "\n  - 历史贴合提示(过去 " + str(history_days) + " 天作息习惯):\n" + \
            "\n".join(lines) + "\n"
    conflicts_summary = ""
    if conflicts:
        conflicts_summary = "\n  - 冲突(" + str(len(conflicts)) + " 处):\n" + \
            "\n".join(f"    - 「{c['candidate']}」({c['candidate_time']})与「{c['locked']}」({c['locked_time']})"
                      f"重叠 {c['overlap']} · {c['overlap_minutes']} 分钟"
                      for c in conflicts) + "\n"

    rate_txt = f"贴合率 {rate}%" if rate is not None else "该窗口无历史作息记录(全新参考)"
    return (f"① 技能与唤醒词: 作息管家 · 「商量计划」\n\n"
            f"② 参数:\n"
            f"  - 日期: {date_str} · 候选事件({len(plan_events)} 段 · 24h 覆盖) · {rate_txt}\n"
            f"  - 候选事件 JSON:\n"
            f"{plan_json_str}{locked_summary}{fit_summary}{conflicts_summary}"
            f"③ 执行: 按「商量计划」流程把候选事件写入 {date_str} 的计划,写库后询问是否同步飞书\n")


def cmd_plan_result(args):
    """plan-result <日期> --json @plan.json [--history-days N]

    制定次日计划结果渲染(强化 #17 商量计划)。输出
    $SKILLS_DB_PATH/schedule_html/plan/result/制定次日计划_<ts>[__N].html
    """
    from schedule_html_render import _naming_path, inject_into_template
    from schedule_db import _normalize_date, get_records_range, list_plan_events

    def _err(msg, **extra):
        out = {"status": "error", "message": msg, "data": None}
        out.update(extra)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    if not args:
        _err("用法: plan-result <日期> --json @plan.json [--history-days N]",
             example="plan-result 2026-07-20 --json @plan.json --history-days 7")
        return

    date_str = args[0]
    json_path = None
    history_days = DEFAULT_HISTORY_DAYS
    i = 1
    while i < len(args):
        if args[i] == "--json" and i + 1 < len(args):
            json_path = args[i + 1]
            i += 2
        elif args[i] == "--history-days" and i + 1 < len(args):
            try:
                history_days = int(args[i + 1])
            except ValueError:
                _err(f"--history-days 必须为整数: {args[i+1]}")
                return
            if history_days < 1 or history_days > 365:
                _err(f"--history-days 范围 1-365: {history_days}")
                return
            i += 2
        else:
            i += 1

    if not json_path:
        _err("必填参数: --json @plan.json(从文件读)或 --json -(从 stdin 读)")
        return

    raw, load_err = _load_json_arg(json_path)
    if load_err:
        _err(load_err)
        return
    try:
        plan_events = json.loads(raw)
    except json.JSONDecodeError as e:
        _err(f"JSON 解析失败: {e.msg}(行 {e.lineno} 列 {e.colno})")
        return
    vmsg = _validate_events(plan_events)
    if vmsg:
        _err(f"plan_events 校验失败: {vmsg}")
        return

    try:
        date_str = _normalize_date(date_str)
    except ValueError:
        _err(f"date 字段格式非法: '{date_str}'(期望 YYYY-MM-DD 或 YYYYMMDD)")
        return

    # 当日已锁定事件(与 preview 同契约:is_active=1)
    try:
        locked = [e for e in list_plan_events(date_str, include_inactive=False)
                  if e.get("is_active", 1) == 1]
    except Exception:
        locked = []

    # 历史窗口:[date-history_days, date-1] 的 schedule_records
    target = _date.fromisoformat(date_str)
    start = (target - timedelta(days=history_days)).isoformat()
    end = (target - timedelta(days=1)).isoformat()
    try:
        records = get_records_range(start, end)
    except Exception:
        records = []

    habits = build_history_habits(records, history_days)
    fits = fit_events(plan_events, habits)
    rate = fit_rate(fits)
    match_n = sum(1 for f in fits if f["fit"] == "match")
    drift_n = sum(1 for f in fits if f["fit"] == "drift")
    none_n = sum(1 for f in fits if f["fit"] == "none")

    # 冲突(候选 vs 已锁定)复用 preview 语义
    conflicts = []
    for cand in plan_events:
        try:
            cs, ce = _to_min(cand["time_start"]), _to_min(cand["time_end"])
        except (KeyError, ValueError):
            continue
        for lk in locked:
            try:
                ls, le = _to_min(lk["time_start"]), _to_min(lk["time_end"])
            except (KeyError, ValueError):
                continue
            if cs < le and ls < ce:
                os_, oe = max(cs, ls), min(ce, le)
                conflicts.append({
                    "time_range": cand["time_start"] + "–" + cand["time_end"],
                    "candidate": cand.get("title", "—"),
                    "candidate_time": cand["time_start"] + "–" + cand["time_end"],
                    "locked": lk.get("title", "—"),
                    "locked_time": lk["time_start"] + "–" + lk["time_end"],
                    "overlap": f"{os_ // 60:02d}:{os_ % 60:02d}–{oe // 60:02d}:{oe % 60:02d}",
                    "overlap_minutes": oe - os_,
                })

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    copy_prompt = _build_copy_prompt(date_str, plan_events, locked, fits,
                                     conflicts, history_days, rate, now_str)

    payload = {
        "meta": {
            "mode": "plan-result",
            "date": date_str,
            "title": f"制定次日计划 · {date_str}",
            "subtitle": (
                f"候选 {len(plan_events)} 段 · 贴合 {match_n} / 偏离 {drift_n}"
                f" / 无参考 {none_n}"
                + (f" · 贴合率 {rate}%" if rate is not None else "")
                + (f" · {len(conflicts)} 处冲突" if conflicts else "")
            ),
            "generated_at": now_str,
            "_template_version": "v2026-08-09",
            "_snapshot_at": now_str,
        },
        "plan_events": plan_events,
        "locked_events": locked,
        "conflicts": conflicts,
        "history": {
            "days": history_days,
            "start": start,
            "end": end,
            "record_count": len(records),
            "habits": habits,
        },
        "fits": fits,
        "fit_rate": rate,
        "match_count": match_n,
        "drift_count": drift_n,
        "none_count": none_n,
        "copy_prompt": copy_prompt,
        "status": "ok" if not conflicts else "conflict",
        "errors": [],
    }

    # 08 契约:复制数据(5 段 JSON)/ 复制日志(6 段)
    scene = {
        "scene_id": "plan-result",
        "command_cn": "制定次日计划",
        "occurred_at": now_str,
        "target": {"date": date_str, "history_days": history_days},
        "payload": {
            "plan_events": plan_events,
            "fits": fits,
            "fit_rate": rate,
            "conflicts": conflicts,
        },
    }
    log = {
        "scene": "plan-result(制定次日计划) · 唤醒词 #17 商量计划",
        "chain": [
            "意图理解: 多轮商量 → 生成次日候选计划",
            "决策点: 历史贴合对比(match/drift/none)+ 冲突检测(候选 vs 已锁定)",
            "关键判断: 贴合率基于过去 {} 天 schedule_records 小时聚合".format(history_days),
        ],
        "data": scene,
        "call_chain": [
            "python scripts/plan_scenarios.py(域模块 · T1 通道自动发现)",
            f"plan-result {date_str} --json @plan.json --history-days {history_days}",
            "写库由 AI 按商量计划流程执行(见复制 prompt ③)",
        ],
        "timestamp": now_str,
        "errors": [],
    }
    payload["copy_data"] = scene
    payload["copy_log"] = log

    # 输出:plan/result/制定次日计划_YYYYMMDD_HHMMSS.html(同秒冲突保护 _2/_3)
    out_path = _naming_path("制定次日计划", "plan/result")
    try:
        inject_into_template("plan_result.html", {"status": "ok", "data": payload}, out_path)
    except Exception as e:
        _err(f"渲染失败: {type(e).__name__}: {e}")
        return

    size_kb = out_path.stat().st_size // 1024
    print(json.dumps({
        "status": "ok",
        "data": {
            "file_path": str(out_path),
            "size_kb": size_kb,
            "mode": "plan-result",
            "date": date_str,
            "candidate_count": len(plan_events),
            "locked_count": len(locked),
            "conflict_count": len(conflicts),
            "history_days": history_days,
            "history_record_count": len(records),
            "fit_rate": rate,
            "match_count": match_n,
            "drift_count": drift_n,
            "none_count": none_n,
        },
        "message": (f"✓ 制定次日计划已写入: {out_path}(候选 {len(plan_events)} 段"
                    + f" · 贴合 {match_n} / 偏离 {drift_n} / 无参考 {none_n}"
                    + (f" · 贴合率 {rate}%" if rate is not None else "") + ")"),
    }, ensure_ascii=False, indent=2))


COMMANDS = {
    "plan-result": cmd_plan_result,
}


if __name__ == "__main__":
    cmd_plan_result(sys.argv[1:])
