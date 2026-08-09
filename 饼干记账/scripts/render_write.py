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

SKILL_DIR = _SCRIPT_DIR.parent
TEMPLATE = SKILL_DIR / "templates" / "写入" / "expense_form.html"
BATCH_TEMPLATE = SKILL_DIR / "templates" / "写入" / "batch_confirm.html"
SKILL_VERSION = "2.0"

FORM_TYPES = {
    "expense": {"scene_id": "write_expense", "wake_word": "记支出", "action": "记一笔支出", "command_cn": "记支出"},
    "income":  {"scene_id": "write_income",  "wake_word": "记收入", "action": "记一笔收入", "command_cn": "记收入"},
    "photo":   {"scene_id": "write_bill_photo", "wake_word": "拍账单", "action": "拍账单记账", "command_cn": "拍账单"},
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

    amount = None
    try:
        amount = float(filled.get("amount")) if filled.get("amount") not in (None, "") else None
    except (TypeError, ValueError):
        amount = None

    dup_hint = _dup_check(records, filled.get("category"), amount) if filled.get("category") else None

    return {
        "status": "ok",
        "data": {
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
            },
        },
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
    return {
        "status": "ok",
        "data": {
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
        },
        "message": "批量录入确认",
    }


def _all_l1() -> list:
    from validators import ALL_L1
    return sorted(ALL_L1)


def default_output_path(command_name: str) -> Path:
    from html_paths import html_path
    return html_path(command_name)


def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 写入域采集表单渲染")
    parser.add_argument("form_type", choices=list(FORM_TYPES.keys()) + ["batch"], help="expense / income / photo / batch")
    parser.add_argument("--amount", default=None, help="金额")
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
    parser.add_argument("--out", default=None, help="输出路径")
    args = parser.parse_args()

    records = _load_history()

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
    else:
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
        template_path = TEMPLATE
        out_name = FORM_TYPES[args.form_type]["command_cn"] + "采集"

    if not template_path.exists():
        print(f"✗ 模板不存在: {template_path}", file=sys.stderr)
        sys.exit(1)
    template = template_path.read_text(encoding="utf-8")
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("<!--INJECT-DATA-->", payload_json, 1)

    out = Path(args.out) if args.out else default_output_path(out_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8-sig")
    print(f"✓ 已生成采集表单: {out}")
    if args.form_type == "batch":
        print(f"  条目: {len(payload['data']['form']['items'])} 笔,缺金额: {payload['data']['form']['missing_count']}")
    else:
        print(f"  分类建议: {[s['name'] for s in payload['data']['form']['category_suggestions']]}")
        if payload["data"]["form"]["prefill_source"]:
            print(f"  预填: {payload['data']['form']['prefill_source']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
