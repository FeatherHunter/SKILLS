#!/usr/bin/env python3
"""
饼干记账 · 写入域渲染器(采集型表单 · #201 第二块)

把 AI 解析后的写入意图 → 智能预填 + 分类建议 + 重复检测 → 注入采集模板(expense_form.html)。

第一性:AI 负责语义(理解用户话→初步字段),本脚本负责数据侧(历史检索/预填/重复检测/分类匹配),
两者分工清晰;用户拿到可确认可修改的表单,复制确认 prompt 发给 AI 即完成写入。

用法(AI 场景调用):
    python3 scripts/render_write.py expense --amount 35 --category-hint 午饭 --note 午饭
    python3 scripts/render_write.py income  --amount 8000 --category-hint 工资
    python3 scripts/render_write.py expense --amount 2000 --category-hint 房租 --account 招行

输出:注入模板的 HTML 文件(默认 $DATA_DIR/biscuit_accountant_html/,可用 --out 指定)
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# #300 Base 管线共享层:统一信封 + Base 注入器 + utf-8-sig BOM
from _base_render import envelope, inject_base, write_html

SKILL_DIR = _SCRIPT_DIR.parent
TEMPLATE = SKILL_DIR / "templates" / "写入" / "expense_form.html"
BATCH_TEMPLATE = SKILL_DIR / "templates" / "写入" / "batch_confirm.html"
FLOW_TEMPLATE = SKILL_DIR / "templates" / "写入" / "flow_confirm.html"
INSTALLMENT_TEMPLATE = SKILL_DIR / "templates" / "写入" / "installment_confirm.html"
UPDATE_TEMPLATE = SKILL_DIR / "templates" / "写入" / "update_confirm.html"
SKILL_VERSION = "2.0"

FORM_TYPES = {
    "expense": {"scene_id": "write_expense", "wake_word": "记支出", "action": "记一笔支出", "command_cn": "记支出"},
    "income":  {"scene_id": "write_income",  "wake_word": "记收入", "action": "记一笔收入", "command_cn": "记收入"},
    "photo":   {"scene_id": "write_bill_photo", "wake_word": "拍账单", "action": "拍账单记账", "command_cn": "拍账单"},
    "reimburse": {"scene_id": "write_reimburse", "wake_word": "记报销", "action": "记一笔报销支出", "command_cn": "记报销"},
}


def _load_history(limit: int = 200) -> list:
    """读最近记录(排除软删)"""
    from db import fetch_all
    return fetch_all(limit=limit)


def _extract_categories(records: list) -> list:
    """历史分类(去重保序)"""
    seen, out = set(), []
    for r in records:
        c = r.get("category") or ""
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _prefill(records: list, fields: dict, category_hint: str, note_hint: str) -> tuple:
    """智能预填:找同分类/备注关键词最近记录,补全缺失字段
    返回 (补充后的 fields, prefill_source)
    """
    if not records:
        return fields, None
    target = None
    # 1) 分类已定 → 找同分类最近
    if fields.get("category"):
        for r in records:
            if r.get("category") == fields["category"]:
                target = r
                break
    # 2) 备注关键词匹配
    if target is None and note_hint:
        for r in records:
            if note_hint and note_hint in (r.get("note") or ""):
                target = r
                break
    if target is None and category_hint:
        for r in records:
            if category_hint and category_hint in (r.get("category") or ""):
                target = r
                break
    if target is None:
        return fields, None

    filled = dict(fields)
    filled.setdefault("account", target.get("account") or "")
    filled.setdefault("ledger", target.get("ledger") or "")
    filled.setdefault("currency", target.get("currency") or "人民币")
    if not filled.get("note") and target.get("note"):
        filled["note"] = target["note"]
    src = f"根据 {str(target.get('time'))[:10]} 的{target.get('category')}记录预填"
    return filled, src


def _dup_check(records: list, category: str, amount: float) -> str | None:
    """重复检测(纯计算·统一数据源):同分类+同金额绝对值 → 提示
    注:用户输入常为正数,库中支出存负数 → 按 |amount| 比较
    """
    if not category or amount is None:
        return None
    amt = abs(float(amount))
    for r in records:
        if abs(abs(float(r.get("amount") or 0)) - amt) < 0.01:
            t = str(r.get("time") or "")
            return f"这笔和 {t[:10]} 的 {r.get('category')} {float(r.get('amount')):.2f} 元很像,确认要再记一笔吗?"
    return None


def _category_suggestions(records: list, category_hint: str, form_type: str) -> list:
    """分类建议:AI 给的 hint → 已有匹配(existing)/ 新分类(new)
    - hint 命中历史分类或白名单 L1 → existing
    - 全新词 → new
    """
    if not category_hint:
        return []
    from validators import ALL_L1
    history = _extract_categories(records)
    # 精确/包含匹配历史
    for c in history:
        if category_hint in c or c in category_hint or c.split("/")[0] == category_hint:
            return [{"name": c, "kind": "existing"}]
    # L1 白名单匹配
    for l1 in sorted(ALL_L1):
        if category_hint in l1 or l1 in category_hint:
            return [{"name": l1, "kind": "existing"}]
    # 全新 → 推荐新建
    return [{"name": category_hint, "kind": "new"}]


def build_payload(form_type: str, fields: dict, category_hint: str, note_hint: str, records: list,
                  photo_meta: dict = None) -> dict:
    """构建采集表单 payload(expense/income/photo)"""
    meta = FORM_TYPES[form_type]
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    filled, prefill_src = _prefill(records, fields, category_hint, note_hint)

    # 记报销:备注自动附加 #待报销(未显式给 #tag 时)
    if form_type == "reimburse":
        note = filled.get("note") or ""
        if "#待报销" not in note:
            filled["note"] = (note + " " if note else "") + "#待报销"

    amount = None
    try:
        amount = float(filled.get("amount")) if filled.get("amount") not in (None, "") else None
    except (TypeError, ValueError):
        amount = None

    dup_hint = _dup_check(records, filled.get("category"), amount) if filled.get("category") else None

    data = {
        "title": meta["action"],
        "generated_at": now,
        "meta": {
            "scene_id": meta["scene_id"],
            "wake_word": meta["wake_word"],
            "command_cn": meta["command_cn"] + " 采集",
            "occurred_at": now,
            "render_cmd": f"render_write.py {form_type}",
            "version": SKILL_VERSION,
        },
        "form": {
            "type": form_type,
            "fields": filled,
            "prefill_source": None if form_type == "photo" else prefill_src,
            "duplicate_hint": dup_hint if form_type != "photo" else None,
            "photo_meta": photo_meta,
            "category_suggestions": _category_suggestions(records, category_hint, form_type),
            "categories_history": _extract_categories(records),
            "categories_all": _all_l1(),
            "selector": {
                "ledger": {"options": _ledger_options()},
            },
        },
    }
    # #300 统一信封:表单数据组织进 scene.snapshot(复制数据【场景名 · 数据快照】)
    summary = [f"{meta['command_cn']} · {meta['action']}"]
    if filled.get("amount"):
        summary.append(f"金额 {filled['amount']}")
    if filled.get("category"):
        summary.append(f"分类 {filled['category']}")
    if filled.get("account"):
        summary.append(f"账户 {filled['account']}")
    if filled.get("ledger"):
        summary.append(f"账本 {filled['ledger']}")
    if filled.get("note"):
        summary.append(f"备注 {filled['note']}")
    if prefill_src and form_type != "photo":
        summary.append(f"预填 {prefill_src}")
    if dup_hint and form_type != "photo":
        summary.append(f"重复提示 {dup_hint}")
    sections = []
    suggs = data["form"]["category_suggestions"]
    if suggs:
        sections.append({"heading": "分类建议", "rows": [
            f"{s['name']}（{'已有分类' if s['kind'] == 'existing' else '推荐新建'}）" for s in suggs
        ]})
    envelope(data, meta["command_cn"] + " 采集", meta["wake_word"], meta["scene_id"],
             f"render_write.py {form_type}", summary, sections,
             data_structure="biscuit_accountant.db bills 表（待用户确认后 INSERT）")

    return {
        "status": "ok",
        "data": data,
        "message": f"{meta['command_cn']} 采集表单",
    }


def build_batch_payload(items: list, ledger: str, records: list) -> dict:
    """构建批量录入确认 payload(form.type=batch)"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    normalized = []
    missing = 0
    for it in items:
        amount = str(it.get("amount") or "").strip()
        category = str(it.get("category") or "").strip()
        note = str(it.get("note") or "").strip()
        is_missing = not amount
        if is_missing:
            missing += 1
        normalized.append({"amount": amount, "category": category, "note": note, "missing": is_missing})
    data = {
        "title": "批量录入多笔",
        "generated_at": now,
        "meta": {
            "scene_id": "write_batch",
            "wake_word": "批量录入",
            "command_cn": "批量录入 确认",
            "occurred_at": now,
            "render_cmd": "render_write.py batch",
            "version": SKILL_VERSION,
        },
        "form": {
            "type": "batch",
            "items": normalized,
            "ledger": ledger or "生活",
            "missing_count": missing,
            "categories_history": _extract_categories(records),
            "categories_all": _all_l1(),
        },
    }
    # #300 统一信封
    envelope(data, "批量录入 确认", "批量录入", "write_batch", "render_write.py batch",
             [f"共 {len(normalized)} 笔 · 缺金额 {missing} 笔", f"账本 {ledger or '生活'}"],
             [{"heading": "条目", "rows": [
                 f"{it['amount'] or '(缺金额)'} {it['category']} {it['note']}".strip()
                 for it in normalized[:20]
             ]}],
             data_structure="biscuit_accountant.db bills 表（待用户确认后批量 INSERT）")
    return {
        "status": "ok",
        "data": data,
        "message": "批量录入确认",
    }


def _all_l1() -> list:
    from validators import ALL_L1
    return sorted(ALL_L1)


def _ledger_options() -> list:
    """账本候选(goals.json ledgers 键 · T4 #308 契约 · 供 smartSelect 消费)

    返回 [{"name", "disabled"}, ...];缺键/空文件/损坏 → 空数组(组件降级普通输入)。
    只读,不写 goals.json。
    """
    from db import _find_db_path, DB_FILENAME
    p = _find_db_path(SKILL_DIR, DB_FILENAME).parent / "goals.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, dict):
        return []
    return [{"name": str(l.get("name") or ""), "disabled": bool(l.get("disabled"))}
            for l in data.get("ledgers", [])
            if str(l.get("name") or "").strip()]


def default_output_path(command_name: str) -> Path:
    from html_paths import html_path
    return html_path(command_name)


def build_flow_payload(flow_type: str, amount: str, search_hint: str = "", reason: str = "",
                       records: list = None, explicit_candidates: list = None) -> dict:
    """构建复合确认 payload(记退款 / 报销到账)

    职责分工(对抗审查 2026-08-09 修复):
      AI 语义定位候选 → 传 explicit_candidates(优先,格式 [{id,time,category,amount,note}])
      脚本仅组装 + 兜底(explicit_candidates 空时按 search_hint 简单匹配,再不行最近记录)
    """
    records = records if records is not None else _load_history()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if flow_type == "refund":
        meta = {"scene_id": "write_refund", "wake_word": "记退款", "command_cn": "记退款 确认"}
        category, note_tag, op2_label = "退款/冲销", "#退款", "标记 #已退款"
        pool = [r for r in records if float(r.get("amount") or 0) < 0]
    elif flow_type == "reimburse_done":
        meta = {"scene_id": "write_reimburse_done", "wake_word": "报销到账", "command_cn": "报销到账 确认"}
        category, note_tag, op2_label = "其他收入/报销回款", "#报销到账", "标记 #报销到账"
        pool = [r for r in records if "#待报销" in (r.get("note") or "")]
    elif flow_type == "collect":
        meta = {"scene_id": "write_collect", "wake_word": "记收回", "command_cn": "记收回 确认"}
        category, note_tag, op2_label = "借贷/收回", "#收回", "原记录 #未还 → #已还"
        pool = [r for r in records if "#借出" in (r.get("note") or "") and "#未还" in (r.get("note") or "")]
    elif flow_type == "payback":
        meta = {"scene_id": "write_payback", "wake_word": "记偿还", "command_cn": "记偿还 确认"}
        category, note_tag, op2_label = "借贷/偿还", "#偿还", "原记录 #未还 → #已还"
        pool = [r for r in records if "#借入" in (r.get("note") or "") and "#未还" in (r.get("note") or "")]
    else:  # lend / borrow(单操作,无候选)
        is_lend = flow_type == "lend"
        meta = {"scene_id": "write_lend" if is_lend else "write_borrow",
                "wake_word": "记借出" if is_lend else "记借入",
                "command_cn": ("记借出" if is_lend else "记借入") + " 确认"}
        category = "借贷/借出" if is_lend else "借贷/借入"
        tag_txt = f"#借出 #借给{{{search_hint or '对象'}}} #未还" if is_lend else f"#借入 #向{{{search_hint or '对象'}}}借 #未还"
        ops = [
            {"label": "记一笔" + ("支出" if is_lend else "收入"),
             "text": f"{category} {amount or '____'} 元", "detail": f"账本=借贷 · 备注 {tag_txt}"},
        ]
        data = {
            "title": "借给别人钱" if is_lend else "向别人借钱",
            "generated_at": now,
            "meta": {**meta, "occurred_at": now, "render_cmd": f"render_write.py {flow_type}",
                     "version": SKILL_VERSION},
            "form": {
                "type": flow_type,
                "amount": amount or "",
                "target": search_hint or "",
                "deadline": reason or "",
                "note": tag_txt,
                "candidates": [],
                "operations": ops,
            },
        }
        # #300 统一信封
        envelope(data, meta["command_cn"], meta["wake_word"], meta["scene_id"],
                 f"render_write.py {flow_type}",
                 [f"金额 {amount or '(未填)'}", f"对象 {search_hint or '(未填)'}",
                  f"备注 {tag_txt}"],
                 [{"heading": "操作预览", "rows": [
                     f"{o['label']} · {o['text']} · {o['detail']}" for o in ops
                 ]}],
                 data_structure="biscuit_accountant.db bills 表（待用户确认后 INSERT）")
        return {
            "status": "ok",
            "data": data,
            "message": meta["command_cn"],
        }

    # 1) AI 显式候选优先(已含 id 等完整字段,直接透传)
    if explicit_candidates:
        candidates = [{
            "id": c.get("id") or 0,
            "time": str(c.get("time") or ""),
            "category": str(c.get("category") or ""),
            "amount": float(c.get("amount") or 0),
            "note": str(c.get("note") or ""),
        } for c in explicit_candidates[:5]]
    # 2) 脚本兜底:search-hint 简单匹配 → 最近记录
    else:
        cands = []
        if search_hint:
            cands = [r for r in pool if search_hint in (r.get("note") or "") or search_hint in (r.get("category") or "")]
        if not cands:
            cands = pool[:5]
        candidates = [{
            "id": r.get("id") or 0,
            "time": str(r.get("time") or ""),
            "category": str(r.get("category") or ""),
            "amount": float(r.get("amount") or 0),
            "note": str(r.get("note") or ""),
        } for r in cands[:5]]

    # 两步操作预览(collect/payback:复合;refund/reimburse_done:复合)
    amt = amount or "____"
    operations = [
        {"label": "① 记一笔收入" if flow_type in ("refund", "reimburse_done", "collect") else "① 记一笔支出",
         "text": f"{category} {amt} 元", "detail": f"备注自动 {note_tag}"},
        {"label": "② 原记录标记", "text": op2_label, "detail": "执行后回执展示两笔状态"},
    ]

    data = {
        "title": meta["command_cn"].replace(" 确认", ""),
        "generated_at": now,
        "meta": {**meta, "occurred_at": now, "render_cmd": f"render_write.py {flow_type}",
                 "version": SKILL_VERSION},
        "form": {
            "type": flow_type,
            "amount": amount or "",
            "reason": reason or "",
            "candidates": candidates,
            "operations": operations,
        },
    }
    # #300 统一信封
    envelope(data, meta["command_cn"], meta["wake_word"], meta["scene_id"],
             f"render_write.py {flow_type}",
             [f"金额 {amount or '(未填)'}", f"候选原记录 {len(candidates)} 笔"]
             + ([f"原因 {reason}"] if reason else []),
             [{"heading": "候选原记录", "rows": [
                 f"#{c['id']} {c['time'][:16]} {c['category']} {c['amount']:.2f} {c['note']}".rstrip()
                 for c in candidates
             ] or ["（无候选 · 以最近记录兜底）"]},
              {"heading": "操作预览", "rows": [
                  f"{o['label']} · {o['text']} · {o['detail']}" for o in operations
              ]}],
             data_structure="biscuit_accountant.db bills 表（两步操作 · 待用户确认后执行）")
    return {
        "status": "ok",
        "data": data,
        "message": meta["command_cn"],
    }


def compute_installments(total: float, periods: int, start_date: str) -> list:
    """分期分摊计算(纯函数 · 2026-08-09 人类裁定)

    规则:
      - 每期 = round(总价 ÷ 期数, 2)
      - 首期 = 总价 - 每期 × (期数-1)(保证总和精确 = 总价,首期补差)
      - 日期 = 每月同日;该月无此日 → 月末回退 min(日, 该月天数)

    Args:
        total: 总价(元)
        periods: 期数
        start_date: 首期日 'YYYY-MM-DD'

    Returns:
        [{seq, date: 'YYYY-MM-DD', amount}...] 共 periods 条
    """
    import calendar
    if periods <= 0:
        raise ValueError("期数必须 > 0")
    if total <= 0:
        raise ValueError("总价必须 > 0")

    each = round(total / periods, 2)
    first = round(total - each * (periods - 1), 2)

    y, m, d = (int(x) for x in start_date.split("-")[:3])
    out = []
    for seq in range(1, periods + 1):
        if seq == 1:
            amount = first
        else:
            amount = each
            m += 1
            if m > 12:
                m = 1
                y += 1
        # 月末回退:取 min(日, 该月天数)
        days_in_month = calendar.monthrange(y, m)[1]
        day = min(d, days_in_month)
        out.append({"seq": seq, "date": f"{y:04d}-{m:02d}-{day:02d}", "amount": amount})
    return out


def build_installment_payload(name: str, total: str, periods: int, start_date: str,
                              account: str = "", ledger: str = "") -> dict:
    """构建记分期确认 payload(向导:参数回显 + 分摊预览)"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_f = float(total)
    items = compute_installments(total_f, periods, start_date or now[:10])
    each = round(total_f / periods, 2)
    first = items[0]["amount"]
    last = items[-1]["date"]
    data = {
        "title": "记一笔分期",
        "generated_at": now,
        "meta": {
            "scene_id": "write_installment", "wake_word": "记分期",
            "command_cn": "记分期 确认", "occurred_at": now,
            "render_cmd": f"render_write.py installment --name {name} --total {total} --periods {periods}",
            "version": SKILL_VERSION,
        },
        "form": {
            "type": "installment",
            "name": name,
            "total": round(total_f, 2),
            "periods": periods,
            "each": each,
            "first": first,
            "start_date": start_date or now[:10],
            "last_date": last,
            "account": account or "",
            "ledger": ledger or "",
            "items": items,
        },
    }
    # #300 统一信封
    envelope(data, "记分期 确认", "记分期", "write_installment",
             data["meta"]["render_cmd"],
             [f"{name} · 总价 {total_f:.2f} 元 · {periods} 期",
              f"每期 {each:.2f} · 首期 {first:.2f} · {start_date or now[:10]} ~ {last}"],
             [{"heading": "分摊明细", "rows": [
                 f"第{i['seq']}期 {i['date']} {i['amount']:.2f} 元" for i in items[:12]
             ]}],
             data_structure="biscuit_accountant.db bills 表（待用户确认后按期 INSERT）")
    return {
        "status": "ok",
        "data": data,
        "message": "记分期确认",
    }


def build_update_payload(record_id: int, new_fields: dict) -> dict:
    """构建改记录 diff 确认 payload
    数据侧:查原记录 + 计算 diff(纯查询);AI 传 id + 新字段
    """
    from db import get_by_id
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    orig = get_by_id(record_id)
    if not orig:
        raise ValueError(f"ID={record_id} 不存在或已撤销")

    changes = []
    for k, v in new_fields.items():
        if v is None:
            continue
        old_val = orig.get(k, "")
        if isinstance(old_val, float):
            old_disp = f"{old_val:.2f}"
        else:
            old_disp = str(old_val or "")
        new_disp = f"{float(v):.2f}" if k == "amount" and isinstance(v, (int, float)) else str(v)
        if old_disp != new_disp:
            changes.append({"field": k, "old": old_disp, "new": new_disp})
    if not changes:
        raise ValueError("没有实际变更的字段(原值 = 新值)")

    data = {
        "title": "修改已有记录",
        "generated_at": now,
        "meta": {
            "scene_id": "write_update", "wake_word": "改记录",
            "command_cn": "改记录 确认", "occurred_at": now,
            "render_cmd": f"render_write.py update --id {record_id}",
            "version": SKILL_VERSION,
        },
        "form": {
            "type": "update",
            "original": {
                "id": orig["id"], "time": str(orig.get("time") or ""),
                "category": str(orig.get("category") or ""),
                "amount": f"{float(orig.get('amount') or 0):.2f}",
                "account": str(orig.get("account") or ""),
                "ledger": str(orig.get("ledger") or ""),
                "note": str(orig.get("note") or ""),
            },
            "changes": changes,
        },
    }
    # #300 统一信封
    envelope(data, "改记录 确认", "改记录", "write_update",
             data["meta"]["render_cmd"],
             [f"记录 ID {record_id} · {len(changes)} 项变更",
              f"原记录 {data['form']['original']['time'][:16]} {data['form']['original']['category']} {data['form']['original']['amount']}"],
             [{"heading": "变更项", "rows": [
                 f"{c['field']}: {c['old']} → {c['new']}" for c in changes
             ]}],
             data_structure="biscuit_accountant.db bills 表（待用户确认后 UPDATE）")
    return {
        "status": "ok",
        "data": data,
        "message": "改记录确认",
    }


def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 写入域采集表单渲染")
    parser.add_argument("form_type", choices=list(FORM_TYPES.keys()) + ["batch", "refund", "reimburse_done",
                        "lend", "borrow", "collect", "payback", "installment", "update"],
                        help="expense / income / photo / reimburse / batch / refund / reimburse_done / lend / borrow / collect / payback / installment / update")
    parser.add_argument("--amount", default=None, help="金额")
    parser.add_argument("--id", type=int, default=None, help="改记录:目标 ID")
    parser.add_argument("--name", default=None, help="分期名目")
    parser.add_argument("--total", default=None, help="分期总价")
    parser.add_argument("--periods", type=int, default=None, help="分期期数")
    parser.add_argument("--start-date", default=None, help="首期日 YYYY-MM-DD")
    parser.add_argument("--category", default=None, help="分类(已确定)")
    parser.add_argument("--category-hint", default=None, help="分类名目意图(AI 语义推荐)")
    parser.add_argument("--account", default=None, help="账户")
    parser.add_argument("--ledger", default=None, help="账本")
    parser.add_argument("--time", default=None, help="时间")
    parser.add_argument("--note", default=None, help="备注")
    parser.add_argument("--currency", default=None, help="币种")
    parser.add_argument("--images", type=int, default=1, help="拍账单:已收图片数")
    parser.add_argument("--photo-note", default=None, help="拍账单:识别说明(如:识别自外卖截图)")
    parser.add_argument("--items", default=None, help="批量:条目 JSON 数组字符串")
    parser.add_argument("--search-hint", default=None, help="退款/到账:原记录定位提示(AI 语义,脚本兜底)")
    parser.add_argument("--candidates", default=None, help="退款/到账:AI 定位候选 JSON 数组(优先于 search-hint)")
    parser.add_argument("--reason", default=None, help="退款原因")
    parser.add_argument("--out", default=None, help="输出路径")
    args = parser.parse_args()

    records = _load_history()

    # ── 改记录(update) ──
    if args.form_type == "update":
        if not args.id:
            print("✗ update 需要 --id", file=sys.stderr)
            sys.exit(1)
        new_fields = {k: getattr(args, k, None) for k in
                      ("category", "amount", "note", "account", "ledger", "time", "currency")}
        try:
            payload = build_update_payload(args.id, new_fields)
        except ValueError as e:
            print(f"✗ {e}", file=sys.stderr)
            sys.exit(1)
        template_path = UPDATE_TEMPLATE
        _write_html(payload, template_path, "改记录确认", args.out)
        print(f"  diff: {len(payload['data']['form']['changes'])} 项")
        return 0

    # ── 记分期(installment) ──
    if args.form_type == "installment":
        if not args.name or not args.total or not args.periods:
            print("✗ installment 需要 --name/--total/--periods", file=sys.stderr)
            sys.exit(1)
        payload = build_installment_payload(args.name, args.total, args.periods,
                                            args.start_date or "", args.account or "", args.ledger or "")
        template_path = INSTALLMENT_TEMPLATE
        _write_html(payload, template_path, "记分期确认", args.out)
        print(f"  分摊: {len(payload['data']['form']['items'])} 期,首期 {payload['data']['form']['first']},末次 {payload['data']['form']['last_date']}")
        return 0

    # ── 复合流程分支(refund / reimburse_done / collect / payback) ──
    if args.form_type in ("refund", "reimburse_done", "collect", "payback"):
        explicit = None
        if args.candidates:
            try:
                explicit = json.loads(args.candidates)
            except json.JSONDecodeError as e:
                print(f"✗ --candidates 不是合法 JSON: {e}", file=sys.stderr)
                sys.exit(1)
        payload = build_flow_payload(args.form_type, args.amount or "", args.search_hint or "",
                                     args.reason or "", records, explicit_candidates=explicit)
        template_path = FLOW_TEMPLATE
        out_name = f"{args.form_type}确认"
        _write_html(payload, template_path, out_name, args.out)
        print(f"  候选: {len(payload['data']['form']['candidates'])} 笔({'AI 定位' if explicit else '脚本兜底'})")
        return 0

    # ── 借贷单操作(lend / borrow) ──
    if args.form_type in ("lend", "borrow"):
        payload = build_flow_payload(args.form_type, args.amount or "", args.search_hint or "",
                                     args.reason or "", records)
        template_path = FLOW_TEMPLATE
        out_name = "记借出确认" if args.form_type == "lend" else "记借入确认"
        _write_html(payload, template_path, out_name, args.out)
        return 0

    # ── batch 分支 ──
    if args.form_type == "batch":
        if not args.items:
            print("✗ batch 需要 --items(JSON 数组字符串,如 '[{\"amount\":\"35\",\"category\":\"餐饮\"}]')", file=sys.stderr)
            sys.exit(1)
        try:
            items = json.loads(args.items)
        except json.JSONDecodeError as e:
            print(f"✗ --items 不是合法 JSON: {e}", file=sys.stderr)
            sys.exit(1)
        payload = build_batch_payload(items, args.ledger or "", records)
        template_path = BATCH_TEMPLATE
        out_name = "批量录入确认"
        _write_html(payload, template_path, out_name, args.out)
        print(f"  条目: {len(payload['data']['form']['items'])} 笔,缺金额: {payload['data']['form']['missing_count']}")
        return 0

    fields = {
        "amount": args.amount or "",
        "category": args.category or "",
        "account": args.account or "",
        "ledger": args.ledger or "",
        "time": args.time or "",
        "note": args.note or "",
        "currency": args.currency or "",
    }
    photo_meta = None
    if args.form_type == "photo":
        photo_meta = {
            "image_count": args.images or 1,
            "note": args.photo_note or "AI 识别结果，请核对金额",
        }
    payload = build_payload(args.form_type, fields, args.category_hint or "", args.note or "",
                            records, photo_meta=photo_meta)
    _write_html(payload, TEMPLATE, FORM_TYPES[args.form_type]["command_cn"] + "采集", args.out)
    print(f"  分类建议: {[s['name'] for s in payload['data']['form']['category_suggestions']]}")
    if payload["data"]["form"]["prefill_source"]:
        print(f"  预填: {payload['data']['form']['prefill_source']}")
    return 0


def _write_html(payload: dict, template_path: Path, out_name: str, out_arg: str = None):
    """payload → Base 注入器 → 写文件(utf-8-sig BOM · #300 契约)"""
    if not template_path.exists():
        print(f"✗ 模板不存在: {template_path}", file=sys.stderr)
        sys.exit(1)
    template = template_path.read_text(encoding="utf-8")
    html = inject_base(template, payload)
    out = Path(out_arg) if out_arg else default_output_path(out_name)
    write_html(html, out)
    print(f"✓ 已生成采集表单: {out}")


if __name__ == "__main__":
    sys.exit(main())
