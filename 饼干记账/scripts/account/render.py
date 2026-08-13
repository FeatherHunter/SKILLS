#!/usr/bin/env python3
"""饼干记账 · 账户域 HTML 渲染器(4 场景 · scenes/account.yaml)

交互契约(yaml type):
    新增账户(采集)    → account_form.html(过程型表单 · 复制确认 prompt)
    账户转账(采集)    → transfer_confirm.html(过程型表单 · 账户建议下拉)
    改账户(选择)      → confirm.html(diff 确认 · 改名/停用/启用)
    看账户汇总(查看)  → account_view.html(结果型 · 余额卡 + 最近流水 · 弹层三选一)

meta.scene_id/wake_word/command_cn 对齐 scenes/account.yaml(门禁 A 层 1 数据源)。

用法:
    python3 scripts/account/render.py add-form --name 招行卡 --type 银行卡
    python3 scripts/account/render.py transfer-form --amount 500 --from 支付宝 --to 招行卡
    python3 scripts/account/render.py update-form --name 招行卡 --new-name 招行工资卡
    python3 scripts/account/render.py update-form --name 招行卡 --disable
    python3 scripts/account/render.py view

输出:默认 $DATA_DIR/biscuit_accountant_html/<中文名>_<TS>.html(§12.A,可用 --out 指定)
"""

import sys
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_SCRIPT_DIR = Path(__file__).resolve().parent
_SCRIPTS = _SCRIPT_DIR.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# #300 Base 管线共享层:统一信封 + Base 注入器 + utf-8-sig BOM
from _base_render import envelope, inject_base, write_html

SKILL_DIR = _SCRIPTS.parent
TEMPLATES = SKILL_DIR / "templates" / "账户"
SKILL_VERSION = "2.0"

SCENE_META = {
    "add":      {"scene_id": "account_add",      "wake_word": "新增账户", "command_cn": "新增账户"},
    "update":   {"scene_id": "account_update",   "wake_word": "改账户",   "command_cn": "改账户"},
    "transfer": {"scene_id": "account_transfer", "wake_word": "账户转账", "command_cn": "账户转账"},
    "summary":  {"scene_id": "account_summary",  "wake_word": "看账户汇总", "command_cn": "账户汇总"},
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _accounts_list() -> list:
    """账户表(表单下拉建议数据源 · 只读)"""
    from account.cli import _accounts
    return _accounts()


def _build_meta(key: str, render_cmd: str) -> dict:
    m = SCENE_META[key]
    now = _now()
    return {
        "scene_id": m["scene_id"],
        "wake_word": m["wake_word"],
        "command_cn": m["command_cn"],
        "occurred_at": now,
        "render_cmd": render_cmd,
        "version": SKILL_VERSION,
    }


def _write_html(payload: dict, template_path: Path, out_name: str, out_arg: str = None) -> Path:
    if not template_path.exists():
        raise FileNotFoundError(f"模板不存在: {template_path}")
    template = template_path.read_text(encoding="utf-8")
    html = inject_base(template, payload)
    from html_paths import html_path
    out = Path(out_arg) if out_arg else html_path(out_name)
    return write_html(html, out)


# ── 新增账户(采集) ───────────────────────────────────────────────────────────

def build_add_payload(name: str, acct_type: str) -> dict:
    now = _now()
    data = {
        "title": "新增账户",
        "generated_at": now,
        "meta": _build_meta("add", "account/render.py add-form"),
        "form": {
            "type": "account_add",
            "name": name or "",
            "acct_type": acct_type or "",
            "accounts": _accounts_list(),
        },
    }
    # #300 统一信封
    envelope(data, "新增账户", "新增账户", "account_add", "account/render.py add-form",
             [f"账户名 {name or '(待填)'} · 类型 {acct_type or '(选填)'}"],
             [{"heading": "已有账户", "rows": [
                 f"{a['name']}（{'已停用' if a.get('disabled') else '使用中'}）"
                 for a in data["form"]["accounts"][:15]
             ] or ["账户表为空,直接填写即可"]}],
             data_structure="goals.json(accounts) 账户表（待用户确认后写入）")
    return {
        "status": "ok",
        "data": data,
        "message": "新增账户 采集表单",
    }


def cmd_add_form(args):
    payload = build_add_payload(args.name or "", args.type or "")
    out = _write_html(payload, TEMPLATES / "account_form.html", "新增账户采集", args.out)
    print(f"✓ 已生成新增账户采集表单: {out}")
    print(f"  预填: 账户名={payload['data']['form']['name'] or '(空)'} · 类型={payload['data']['form']['acct_type'] or '(空)'}")
    return 0


# ── 账户转账(采集) ───────────────────────────────────────────────────────────

def build_transfer_payload(amount: str, from_acct: str, to_acct: str, time_str: str) -> dict:
    now = _now()
    data = {
        "title": "账户间转账",
        "generated_at": now,
        "meta": _build_meta("transfer", "account/render.py transfer-form"),
        "form": {
            "type": "account_transfer",
            "amount": amount or "",
            "from": from_acct or "",
            "to": to_acct or "",
            "time": time_str or "",
            "accounts": _accounts_list(),
        },
    }
    # #300 统一信封
    envelope(data, "账户转账", "账户转账", "account_transfer",
             "account/render.py transfer-form",
             [f"金额 {amount or '(待填)'} · {from_acct or '(待填)'} → {to_acct or '(待填)'}",
              f"时间 {time_str or '(默认现在)'}"],
             [{"heading": "已有账户", "rows": [
                 f"{a['name']}（{'已停用' if a.get('disabled') else '使用中'}）"
                 for a in data["form"]["accounts"][:15]
             ] or ["账户表为空,可直接手填"]}],
             data_structure="biscuit_accountant.db bills 表（转账两笔分录 · 待确认后 INSERT）")
    return {
        "status": "ok",
        "data": data,
        "message": "账户转账 采集表单",
    }


def cmd_transfer_form(args):
    payload = build_transfer_payload(args.amount or "", args.from_acct or "",
                                     args.to_acct or "", args.time or "")
    out = _write_html(payload, TEMPLATES / "transfer_confirm.html", "账户转账确认", args.out)
    print(f"✓ 已生成账户转账确认表单: {out}")
    return 0


# ── 改账户(选择 · diff 预览) ─────────────────────────────────────────────────

def build_update_payload(name: str, new_name: str, disable: bool, enable: bool) -> dict:
    from account.cli import _accounts, _find_account
    now = _now()
    target = _find_account(_accounts(), name or "")
    if target is None:
        raise ValueError(f"账户「{name}」不在账户表(可先用 account/render.py add-form 或提示用户新增)")

    changes = []
    if new_name and new_name.strip() and new_name.strip() != name:
        changes.append({"field": "账户名", "old": name, "new": new_name.strip()})
    if disable:
        changes.append({"field": "状态", "old": "使用中", "new": "已停用(历史记录保留)"})
    if enable:
        changes.append({"field": "状态", "old": "已停用", "new": "使用中"})
    if not changes:
        raise ValueError("没有可执行的变更(至少传 --new-name / --disable / --enable 之一)")

    data = {
        "title": "修改账户",
        "generated_at": now,
        "meta": _build_meta("update", "account/render.py update-form"),
        "form": {
            "type": "account_update",
            "account": {
                "name": target["name"],
                "type": target.get("type") or "",
                "disabled": bool(target.get("disabled")),
            },
            "changes": changes,
        },
    }
    # #300 统一信封
    envelope(data, "改账户", "改账户", "account_update", "account/render.py update-form",
             [f"账户 {name} · {len(changes)} 项变更"],
             [{"heading": "变更项", "rows": [
                 f"{c['field']}: {c['old']} → {c['new']}" for c in changes
             ]}],
             data_structure="goals.json(accounts) + bills.account（待确认后写入）")
    return {
        "status": "ok",
        "data": data,
        "message": "改账户 确认",
    }


def cmd_update_form(args):
    try:
        payload = build_update_payload(args.name or "", args.new_name or "",
                                       args.disable, args.enable)
    except ValueError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    out = _write_html(payload, TEMPLATES / "confirm.html", "改账户确认", args.out)
    print(f"✓ 已生成改账户确认: {out}")
    print(f"  diff: {len(payload['data']['form']['changes'])} 项")
    return 0


# ── 看账户汇总(结果型) ───────────────────────────────────────────────────────

def build_summary_payload() -> dict:
    """调 account/cli.py summary --json → 包 meta 注入结果型模板"""
    env = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    import os
    env = {**os.environ.copy(), **env}
    cmd = [sys.executable, str(_SCRIPT_DIR / "cli.py"), "summary", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                            env=env, timeout=30)
    if result.returncode != 0 and not result.stdout.strip():
        return {"status": "error", "data": None,
                "message": f"account/cli.py summary 调用失败: {result.stderr.strip()}"}
    try:
        cli = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        return {"status": "error", "data": None,
                "message": f"account/cli.py summary 输出非 JSON: {e}"}
    if cli.get("status") != "ok":
        return cli

    now = _now()
    data = dict(cli.get("data") or {})
    data["title"] = "账户汇总"
    data["subtitle"] = (
        f"{len(data.get('accounts') or [])} 个账户 · 最近 {data.get('flow_count') or 0} 笔流水"
    )
    data["generated_at"] = now
    data["meta"] = _build_meta("summary", "account/render.py view")
    # #300 统一信封
    totals = data.get("totals") or {}
    envelope(data, "账户汇总", "看账户汇总", "account_summary", "account/render.py view",
             [f"{len(data.get('accounts') or [])} 个账户 · 最近 {data.get('flow_count') or 0} 笔流水",
              f"总余额 {totals.get('balance', 0):.2f} · 收入 {totals.get('income', 0):.2f} · 支出 {totals.get('expense', 0):.2f}"],
             [{"heading": "账户余额", "rows": [
                 f"{a.get('name')} 余额 {a.get('balance', 0):.2f} · 收入 {a.get('income', 0):.2f} · 支出 {a.get('expense', 0):.2f}"
                 for a in (data.get("accounts") or [])[:15]
             ]}],
             data_structure="biscuit_accountant.db bills + goals.json(accounts)（只读查询）")
    return {"status": "ok", "data": data, "message": cli.get("message", "账户汇总")}


def cmd_view(args):
    payload = build_summary_payload()
    if payload.get("status") == "error":
        # #300 错误信封:错误页也带 scene.snapshot(复制数据/日志按钮可用)
        from _base_render import error_envelope
        payload = error_envelope(payload.get("message", "未知错误"), command_cn="账户汇总")
    out = _write_html(payload, TEMPLATES / "account_view.html", "账户汇总", args.out)
    if payload.get("status") == "error":
        print(f"⚠ 已生成错误页: {out}")
        print(f"  原因: {payload.get('message', '未知错误')}")
        return 0
    print(f"✓ 已生成账户汇总: {out}")
    return 0


# ── 入口 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 账户域 HTML 渲染器")
    parser.add_argument("form_type", choices=["add-form", "transfer-form", "update-form", "view"])
    parser.add_argument("--name", default=None, help="账户名")
    parser.add_argument("--type", default=None, help="账户类型(新增账户)")
    parser.add_argument("--new-name", default=None, help="新账户名(改账户)")
    parser.add_argument("--disable", action="store_true", help="停用(改账户)")
    parser.add_argument("--enable", action="store_true", help="启用(改账户)")
    parser.add_argument("--amount", default=None, help="转账金额")
    parser.add_argument("--from", dest="from_acct", default=None, help="转出账户")
    parser.add_argument("--to", dest="to_acct", default=None, help="转入账户")
    parser.add_argument("--time", default=None, help="转账时间")
    parser.add_argument("--out", default=None, help="输出路径")
    args = parser.parse_args()

    if args.form_type == "add-form":
        return cmd_add_form(args)
    if args.form_type == "transfer-form":
        return cmd_transfer_form(args)
    if args.form_type == "update-form":
        return cmd_update_form(args)
    if args.form_type == "view":
        return cmd_view(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
