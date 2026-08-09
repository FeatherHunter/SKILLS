#!/usr/bin/env python3
"""饼干记账 · 联动域 CLI(买东西联动 / 吃饭联动 · #239)

G2 场景簇 + 回执按钮设计:主操作 = 记支出(复用 write add,本 CLI 不写库);
本域职责 = ①采集表单渲染(过程确认) ②回执渲染(回执带「同时录入居家管家/同时记卡路里」联动按钮)。

第一性分工:AI 负责语义(理解用户话 → 填字段),脚本负责数据侧(历史预填/重复检测/分类匹配/回执组装),
与写入域 render_write 同构,但自包含实现(不 import 写入域文件,满足隔离契约,可并发)。

用法:
    python3 scripts/link/cli.py form purchase --amount 199 --item 空气炸锅
    python3 scripts/link/cli.py form meal --amount 35 --ate 鸡腿饭
    python3 scripts/link/cli.py receipt purchase --id 123 --item 空气炸锅
    python3 scripts/link/cli.py receipt meal --id 456 --ate 鸡腿饭

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

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from validators import ALL_L1  # noqa: E402
from html_paths import html_path  # noqa: E402

SKILL_DIR = _SCRIPTS.parent
TEMPLATE_DIR = SKILL_DIR / "templates" / "联动"
SKILL_VERSION = "2.0"

# 场景注册(与 scenes/link.yaml 对齐:scenario_id / wake_word / prompt head 逐字一致)
SCENES = {
    "purchase": {
        "scene_id": "link_purchase",
        "wake_word": "买东西",
        "title": "买东西联动",
        "action": "记一笔买东西的账并联动录入",
        "default_category": "居家/家电",
        "key_field": "item",
        "key_label": "物  品",
        "key_placeholder": "如:空气炸锅",
        "form_template": "purchase_confirm.html",
        # 联动目标(回执按钮 → 复制联动 prompt → AI 调目标技能)
        "link_target": "居家管家",
        "link_wake": "录物品",
        "link_button": "同时录入居家管家",
        "link_head": "请加载「居家管家」技能,帮我录入刚买的物品(唤醒词:录物品):",
        # (label, 取值来源, 必填, 提示):item/ate=联动关键字段;amount/category/note=bill 字段
        "link_fields": [
            ("物  品", "key", True, ""),
            ("数  量", None, False, "选填,默认 1"),
            ("金  额", "amount", False, "选填,刚记的账"),
            ("分  类", "category", False, "选填"),
        ],
    },
    "meal": {
        "scene_id": "link_meal",
        "wake_word": "吃饭",
        "title": "吃饭联动",
        "action": "记一笔吃饭的账并联动卡路里",
        "default_category": "餐饮",
        "key_field": "ate",
        "key_label": "吃  了",
        "key_placeholder": "如:午饭 鸡腿饭",
        "form_template": "meal_confirm.html",
        "link_target": "卡路里",
        "link_wake": "记一餐",
        "link_button": "同时记卡路里",
        "link_head": "请加载「卡路里」技能,帮我记一餐(唤醒词:记一餐):",
        "link_fields": [
            ("吃  了", "key", True, ""),
            ("餐  别", None, False, "选填,如:午餐"),
            ("备  注", "note", False, "选填"),
        ],
    },
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
    """智能预填:找同分类/备注关键词最近记录,补全缺失字段(与写入域同构,自包含)"""
    if not records:
        return fields, None
    target = None
    if fields.get("category"):
        for r in records:
            if r.get("category") == fields["category"]:
                target = r
                break
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


def _dup_check(records: list, category: str, amount) -> str | None:
    """重复检测:同分类+同金额绝对值 → 提示(纯计算)"""
    if not category or amount is None:
        return None
    amt = abs(float(amount))
    for r in records:
        if abs(abs(float(r.get("amount") or 0)) - amt) < 0.01:
            t = str(r.get("time") or "")
            return f"这笔和 {t[:10]} 的 {r.get('category')} {float(r.get('amount')):.2f} 元很像,确认要再记一笔吗?"
    return None


def _category_suggestions(records: list, category_hint: str) -> list:
    """分类建议:hint 命中历史/L1 白名单 → existing;全新 → new"""
    if not category_hint:
        return []
    history = _extract_categories(records)
    for c in history:
        if category_hint in c or c in category_hint or c.split("/")[0] == category_hint:
            return [{"name": c, "kind": "existing"}]
    for l1 in sorted(ALL_L1):
        if category_hint in l1 or l1 in category_hint:
            return [{"name": l1, "kind": "existing"}]
    return [{"name": category_hint, "kind": "new"}]


def _all_l1() -> list:
    return sorted(ALL_L1)


def build_form_payload(scene_key: str, fields: dict, category_hint: str, note_hint: str,
                       records: list = None) -> dict:
    """构建联动采集表单 payload(买东西联动/吃饭联动)"""
    scene = SCENES[scene_key]
    records = records if records is not None else _load_history()
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
            "title": scene["title"],
            "generated_at": now,
            "meta": {
                "scene_id": scene["scene_id"],
                "wake_word": scene["wake_word"],
                "action": scene["action"],
                "command_cn": scene["title"] + " 采集",
                "occurred_at": now,
                "render_cmd": f"link/cli.py form {scene_key}",
                "version": SKILL_VERSION,
            },
            "form": {
                "type": scene_key,
                "fields": filled,
                "default_category": scene["default_category"],
                "key_label": scene["key_label"],
                "key_placeholder": scene["key_placeholder"],
                "prefill_source": prefill_src,
                "duplicate_hint": dup_hint,
                "category_suggestions": _category_suggestions(records, category_hint),
                "categories_history": _extract_categories(records),
                "categories_all": _all_l1(),
            },
        },
        "message": scene["title"] + " 采集表单",
    }


def build_receipt_payload(scene_key: str, bill_id: int, key_value: str) -> dict:
    """构建联动回执 payload(记支出后:已记录卡片 + 联动按钮 + 撤销)

    Args:
        scene_key: purchase / meal
        bill_id: 已记录账单 ID(复用 write add 写入后的 id)
        key_value: 联动关键字段值(物品 / 吃了),AI 从采集确认中携带

    Raises:
        ValueError: 账单不存在或已撤销 / 联动关键字段缺失
    """
    scene = SCENES[scene_key]
    from db import get_by_id
    bill = get_by_id(bill_id)
    if not bill:
        raise ValueError(f"ID={bill_id} 不存在或已撤销")

    key_field = scene["key_field"]
    key_value = (key_value or "").strip()
    if not key_value:
        raise ValueError(f"缺少联动关键字段({key_field}),回执无法生成联动 prompt")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    amount_abs = f"{abs(float(bill.get('amount') or 0)):.2f}"

    def _field_value(src_key: str) -> str:
        if src_key == "key":
            return key_value
        if src_key == "amount":
            return f"{amount_abs} 元"
        if src_key == "category":
            return str(bill.get("category") or "")
        if src_key == "note":
            return str(bill.get("note") or "")
        return ""

    # 联动 prompt(预告式:按钮点击复制 → AI 调目标技能)
    lines = [scene["link_head"], ""]
    link_fields = []
    for label, src_key, required, hint in scene["link_fields"]:
        value = _field_value(src_key) if src_key else ""
        if value:
            line = f"  {label}: {value}"
        else:
            line = f"  {label}: ____ ({hint})" if hint else f"  {label}: ____"
        lines.append(line)
        link_fields.append({"label": label.strip(), "value": value or ""})
    link_prompt = "\n".join(lines)

    # 撤销 prompt(回执契约:成功回执带撤销)
    undo_prompt = (
        "请加载「饼干记账」技能,帮我撤销刚记的那笔账(唤醒词:撤销):\n\n"
        f"  目  标: ID={bill_id} ({str(bill.get('category') or '')} {float(bill.get('amount') or 0):.2f} 元"
        + (f" · {key_value}" if key_value else "") + ")"
    )

    return {
        "status": "ok",
        "data": {
            "title": scene["title"] + " · 已记账",
            "generated_at": now,
            "meta": {
                "scene_id": scene["scene_id"],
                "wake_word": scene["wake_word"],
                "command_cn": scene["title"] + " 回执",
                "occurred_at": now,
                "render_cmd": f"link/cli.py receipt {scene_key} --id {bill_id}",
                "version": SKILL_VERSION,
            },
            "receipt": {
                "type": scene_key,
                "bill": {
                    "id": bill_id,
                    "amount": f"{amount_abs}",
                    "amount_sign": f"{float(bill.get('amount') or 0):.2f}",
                    "category": str(bill.get("category") or ""),
                    "time": str(bill.get("time") or ""),
                    "account": str(bill.get("account") or ""),
                    "ledger": str(bill.get("ledger") or ""),
                    "note": str(bill.get("note") or ""),
                },
                "key": {key_field: key_value},
                "link": {
                    "target": scene["link_target"],
                    "wake_word": scene["link_wake"],
                    "button": scene["link_button"],
                    "head": scene["link_head"],
                    "fields": link_fields,
                    "prompt": link_prompt,
                },
                "undo": {"prompt": undo_prompt},
            },
        },
        "message": scene["title"] + " 回执",
    }


def _render(payload: dict, template_name: str, out_name: str, out_arg: str = None) -> Path:
    """注入 payload 到模板并写文件(BOM + </ 转义,对齐 render_write)"""
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"模板不存在: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("<!--INJECT-DATA-->", payload_json, 1)
    out = Path(out_arg) if out_arg else html_path(out_name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8-sig")
    return out


def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 联动域(买东西联动 / 吃饭联动)")
    sub = parser.add_subparsers(dest="command", help="子命令")

    p = sub.add_parser("form", help="联动采集表单渲染(主操作=记支出,复用 write add)")
    p.add_argument("scene", choices=["purchase", "meal"], help="买东西联动 / 吃饭联动")
    p.add_argument("--amount", default=None, help="金额")
    p.add_argument("--item", default=None, help="买东西联动:物品名")
    p.add_argument("--ate", default=None, help="吃饭联动:吃了什么")
    p.add_argument("--category", default=None, help="分类(已确定)")
    p.add_argument("--category-hint", default=None, help="分类名目意图(AI 语义推荐)")
    p.add_argument("--account", default=None, help="账户")
    p.add_argument("--ledger", default=None, help="账本")
    p.add_argument("--time", default=None, help="时间")
    p.add_argument("--note", default=None, help="备注")
    p.add_argument("--currency", default=None, help="币种")
    p.add_argument("--out", default=None, help="输出路径")

    p = sub.add_parser("receipt", help="联动回执渲染(记支出后,回执带联动按钮)")
    p.add_argument("scene", choices=["purchase", "meal"], help="买东西联动 / 吃饭联动")
    p.add_argument("--id", type=int, required=True, help="已记录账单 ID(write add 返回)")
    p.add_argument("--item", default=None, help="买东西联动:物品名")
    p.add_argument("--ate", default=None, help="吃饭联动:吃了什么")
    p.add_argument("--out", default=None, help="输出路径")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "form":
            key_field = SCENES[args.scene]["key_field"]
            key_value = getattr(args, key_field, None)
            fields = {
                "amount": args.amount or "",
                "category": args.category or "",
                "account": args.account or "",
                "ledger": args.ledger or "",
                "time": args.time or "",
                "note": args.note or "",
                "currency": args.currency or "",
            }
            if key_value:
                fields[key_field] = key_value
            payload = build_form_payload(args.scene, fields, args.category_hint or "", args.note or "")
            scene = SCENES[args.scene]
            out = _render(payload, scene["form_template"], scene["title"] + "采集", args.out)
            form = payload["data"]["form"]
            print(f"✓ 已生成联动采集表单: {out}")
            print(f"  联动字段({key_field}): {key_value or '(待填)'}")
            print(f"  分类建议: {[s['name'] for s in form['category_suggestions']]}")
            if form["prefill_source"]:
                print(f"  预填: {form['prefill_source']}")
            return 0

        if args.command == "receipt":
            key_field = SCENES[args.scene]["key_field"]
            key_value = getattr(args, key_field, None)
            payload = build_receipt_payload(args.scene, args.id, key_value or "")
            scene = SCENES[args.scene]
            out = _render(payload, "receipt.html", scene["title"] + "回执", args.out)
            rc = payload["data"]["receipt"]
            print(f"✓ 已生成联动回执: {out}")
            print(f"  已记录: ID={rc['bill']['id']} {rc['bill']['category']} -{rc['bill']['amount']} 元")
            print(f"  联动按钮: {rc['link']['button']}(点击复制 → AI 调{rc['link']['target']}{rc['link']['wake_word']})")
            return 0
    except (ValueError, FileNotFoundError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"✗ 执行出错: {e}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
