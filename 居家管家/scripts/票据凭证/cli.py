"""SM6 票据凭证域 · 域 CLI 入口

用法:
  python scripts/票据凭证/cli.py purchase list [--item-id N] [--year YYYY] [--month MM] [--output PATH]
  python scripts/票据凭证/cli.py purchase add --item-id N --date YYYY-MM-DD [--price X] ...
  python scripts/票据凭证/cli.py purchase stats [--year YYYY] [--output PATH]
  python scripts/票据凭证/cli.py warranty list [--status 在保|即将到期|已过|全部] [--output PATH]
  python scripts/票据凭证/cli.py warranty register --item-id N --kind 保修|保养 --start-date D --duration-days N
  python scripts/票据凭证/cli.py warranty repair --warranty-id N --date D [--cost X] [--note]
  python scripts/票据凭证/cli.py warranty maintain --warranty-id N --date D [--note]
  python scripts/票据凭证/cli.py cert list [--output PATH]
  python scripts/票据凭证/cli.py cert add --type 护照 --holder X --number N --issued-at D --expires-at D [--photo P]
  python scripts/票据凭证/cli.py account init-master --master-key M
  python scripts/票据凭证/cli.py account list [--output PATH]
  python scripts/票据凭证/cli.py account add --platform P --user U --pass X --master-key M [--type 购物] [--note]
  python scripts/票据凭证/cli.py account show --platform P --master-key M

设计要点:
  - HTML-First: list/stats 默认输出 HTML(12.A 命名), 失败走错误回执(优雅降级)
  - 写操作(register/repair/maintain/add)输出结构化 JSON 回执(5 段式), 由 AI 交互确认
  - 敏感: 账号 show 明文只在 stdout 回显; HTML payload 永不出现密码
"""
import json
import os
import sys
from pathlib import Path

_scripts_dir = Path(__file__).parent.parent.resolve()
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from render import resolve_output_root  # noqa: E402  (公共层只调用不改)

from 票据凭证.db import get_conn  # noqa: E402
from 票据凭证 import ops  # noqa: E402
from 票据凭证.account_ops import (  # noqa: E402
    is_master_key_set, _write_master_key, account_set_master,
    account_add_typed, account_update_typed, account_list_masked, account_show_typed,
)


def _out_dir():
    d = resolve_output_root() / "home_manager_html"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _auto_output(command_cn):
    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _out_dir() / f"{command_cn}_{stamp}.html"


def _render(template_name, payload, command_cn, output_path=None):
    """域渲染入口: 复用公共 render 注入管线(只调不改), 域内命名"""
    from render import render_page
    out = Path(output_path) if output_path else _auto_output(command_cn)
    return render_page(template_name, payload, str(out))


def _emit(template_name, payload, command_cn, output_path=None):
    result = _render(template_name, payload, command_cn, output_path)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["status"] == "ok" else 1


def _err_payload(message, meta, cli_chain, target="", key_data=None):
    """错误回执(08 三层反馈 · 失败回执: 操作名/原因/关键数据/建议)"""
    return {
        "status": "error",
        "data": {
            "meta": meta,
            "occurred_at": None,
            "version": "2.0-SM6",
            "cli_chain": cli_chain,
            "error": {
                "operation": meta["command_cn"],
                "reason": message,
                "key_data": key_data or {},
                "suggestion": "修正参数后重试; 或复制下方日志发给开发者排查",
            },
            "target": target,
        },
        "message": message,
    }


def _receipt(scene_id, command_cn, target, payload, message):
    """成功回执 JSON(08 复制数据 5 段契约)"""
    from datetime import datetime
    return {
        "scene_id": scene_id,
        "command_cn": command_cn,
        "occurred_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target": target,
        "payload": payload,
        "message": message,
    }


def _print_json(obj):
    print(json.dumps(obj, ensure_ascii=False))


# ── purchase ────────────────────────────────────────────────────────

def _purchase_list(args):
    from 票据凭证.payloads import purchase_payload
    conn = get_conn()
    try:
        payload = purchase_payload(conn, item_id=args.item_id, year=args.year, month=args.month)
    finally:
        conn.close()
    return _emit("票据凭证/purchase_records.html", payload, "购买记录", args.output)


def _purchase_add(args):
    try:
        conn = get_conn()
        try:
            pid = ops.purchase_add(
                conn, args.item_id, args.date, price=args.price, channel=args.channel,
                merchant_contact=args.merchant_contact, receipt_photo=args.receipt_photo,
                return_window_days=args.return_window if args.return_window is not None else ops.DEFAULT_RETURN_WINDOW,
                note=args.note or "")
        finally:
            conn.close()
    except ValueError as e:
        _print_json({"status": "error", "message": str(e), "suggestion": "修正参数后重试"})
        return 1
    _print_json(_receipt("SM6-1", "购买记录", f"item#{args.item_id}",
                         {"id": pid, "item_id": args.item_id, "purchased_at": args.date,
                          "price": args.price}, "购买记录已登记"))
    return 0


def _purchase_stats(args):
    from 票据凭证.payloads import purchase_payload
    conn = get_conn()
    try:
        payload = purchase_payload(conn, year=args.year)
    finally:
        conn.close()
    return _emit("票据凭证/purchase_records.html", payload, "购买记录", args.output)


# ── warranty ────────────────────────────────────────────────────────

def _warranty_list(args):
    from 票据凭证.payloads import warranty_payload
    conn = get_conn()
    try:
        payload = warranty_payload(conn, status_filter=args.status)
    finally:
        conn.close()
    return _emit("票据凭证/warranty.html", payload, "保修", args.output)


def _warranty_register(args):
    try:
        conn = get_conn()
        try:
            wid = ops.warranty_register(
                conn, args.item_id, args.kind, args.start_date, args.duration_days,
                last_done_date=args.last_done, photo=args.photo or "", note=args.note or "")
        finally:
            conn.close()
    except ValueError as e:
        _print_json({"status": "error", "message": str(e), "suggestion": "修正参数后重试"})
        return 1
    _print_json(_receipt("SM6-2", "保修", f"item#{args.item_id} {args.kind}",
                         {"id": wid, "kind": args.kind, "start_date": args.start_date,
                          "duration_days": args.duration_days}, "保修/保养已登记"))
    return 0


def _warranty_repair(args):
    try:
        conn = get_conn()
        try:
            eid = ops.warranty_repair(conn, args.warranty_id, args.date,
                                      cost=args.cost or 0, note=args.note or "")
        finally:
            conn.close()
    except ValueError as e:
        _print_json({"status": "error", "message": str(e), "suggestion": "修正参数后重试"})
        return 1
    _print_json(_receipt("SM6-2", "保修", f"warranty#{args.warranty_id}",
                         {"event_id": eid, "occurred_at": args.date, "cost": args.cost}, "维修记录已登记"))
    return 0


def _warranty_maintain(args):
    try:
        conn = get_conn()
        try:
            eid = ops.warranty_maintain(conn, args.warranty_id, args.date, note=args.note or "")
        finally:
            conn.close()
    except ValueError as e:
        _print_json({"status": "error", "message": str(e), "suggestion": "修正参数后重试"})
        return 1
    _print_json(_receipt("SM6-2", "保修", f"warranty#{args.warranty_id}",
                         {"event_id": eid, "occurred_at": args.date}, "保养已执行, 下次保养日已刷新"))
    return 0


# ── cert ────────────────────────────────────────────────────────────

def _cert_list(args):
    from 票据凭证.payloads import certificates_payload
    conn = get_conn()
    try:
        payload = certificates_payload(conn)
    finally:
        conn.close()
    return _emit("票据凭证/certificates.html", payload, "证件", args.output)


def _cert_add(args):
    try:
        conn = get_conn()
        try:
            cid = ops.cert_add(conn, args.type, args.holder or "", args.number or "",
                               args.issued_at or "", args.expires_at,
                               photo=args.photo or "", note=args.note or "")
        finally:
            conn.close()
    except ValueError as e:
        _print_json({"status": "error", "message": str(e), "suggestion": "修正参数后重试"})
        return 1
    _print_json(_receipt("SM6-3", "证件", args.type,
                         {"id": cid, "cert_type": args.type, "expires_at": args.expires_at,
                          "number_masked": ops.mask_number(args.number or "")},
                         "证件已登记(号码脱敏存储)"))
    return 0


# ── account ────────────────────────────────────────────────────────

def _account_list(args):
    from 票据凭证.payloads import accounts_payload
    payload = accounts_payload()
    return _emit("票据凭证/accounts.html", payload, "账号", args.output)


def _account_add(args):
    try:
        result = account_add_typed(args.platform, args.user or "", args.password,
                                   args.master_key, account_type=args.type or "其他",
                                   note=args.note or "")
    except ValueError as e:
        _print_json({"status": "error", "message": str(e), "suggestion": "修正参数后重试"})
        return 1
    if not result.get("success"):
        _print_json({"status": "error", "message": result["message"], "suggestion": "检查主密钥/平台是否已存在"})
        return 1
    _print_json(_receipt("SM6-4", "账号", args.platform,
                         {"id": result.get("id"), "platform": args.platform,
                          "username": args.user, "type": args.type or "其他"},
                         "账号已加密存储"))
    return 0


def _account_show(args):
    if not args.master_key:
        _print_json({"status": "error", "message": "查看密码必须提供 --master-key(敏感操作)"})
        return 1
    result = account_show_typed(args.platform, args.master_key)
    if not result.get("success"):
        _print_json({"status": "error", "message": result["message"], "suggestion": "检查主密钥是否正确"})
        return 1
    # 明文仅在 stdout 回显(经 AI 对话中转), 不进任何 HTML
    _print_json(_receipt("SM6-4", "账号", args.platform,
                         {"platform": result["platform"], "username": result["username"],
                          "password": result["password"]}, "密码已解密(敏感, 仅对话回显)"))
    return 0


def _account_update(args):
    result = account_update_typed(args.platform, args.master_key,
                                  username=args.user, password=args.password,
                                  account_type=args.type, note=args.note)
    if not result.get("success"):
        _print_json({"status": "error", "message": result["message"], "suggestion": "检查主密钥/平台是否存在"})
        return 1
    _print_json(_receipt("SM6-4", "账号", args.platform,
                         {"platform": args.platform, "username": args.user,
                          "type": args.type},
                         "账号已更新(重新录入语义)"))
    return 0


def _account_init(args):
    if is_master_key_set():
        _print_json({"status": "error", "message": "主密钥已存在; 改用 set-master",
                     "suggestion": "account set-master --old X --new Y"})
        return 1
    result = _write_master_key(args.master_key)
    _print_json({"status": "ok" if result["success"] else "error",
                 "message": result["message"]})
    return 0 if result["success"] else 1


def _account_set_master(args):
    result = account_set_master(args.old, args.new)
    _print_json({"status": "ok" if result["success"] else "error",
                 "message": result["message"]})
    return 0 if result["success"] else 1


# ── main ────────────────────────────────────────────────────────────

def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(prog="票据凭证", description="SM6 票据凭证域 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_pur = sub.add_parser("purchase", help="购买记录")
    pp = p_pur.add_subparsers(dest="sub", required=True)
    pl = pp.add_parser("list", help="购买记录清单 HTML")
    pl.add_argument("--item-id", type=int, default=None)
    pl.add_argument("--year", type=int, default=None)
    pl.add_argument("--month", type=int, default=None)
    pl.add_argument("--output", default=None)
    pa = pp.add_parser("add", help="登记购买记录")
    pa.add_argument("--item-id", type=int, required=True)
    pa.add_argument("--date", required=True, help="YYYY-MM-DD")
    pa.add_argument("--price", type=float, default=None)
    pa.add_argument("--channel", default="")
    pa.add_argument("--merchant-contact", default="")
    pa.add_argument("--receipt-photo", default="")
    pa.add_argument("--return-window", type=int, default=None, help="退货窗口天数(默认7)")
    pa.add_argument("--note", default="")
    ps = pp.add_parser("stats", help="消费统计 HTML")
    ps.add_argument("--year", type=int, default=None)
    ps.add_argument("--output", default=None)

    p_war = sub.add_parser("warranty", help="保修与保养")
    wp = p_war.add_subparsers(dest="sub", required=True)
    wl = wp.add_parser("list", help="保修清单 HTML")
    wl.add_argument("--status", default=None,
                    choices=["在保", "即将到期", "已过", "到期未做", "全部"])
    wl.add_argument("--output", default=None)
    wr = wp.add_parser("register", help="登记保修/保养")
    wr.add_argument("--item-id", type=int, required=True)
    wr.add_argument("--kind", required=True, choices=["保修", "保养"])
    wr.add_argument("--start-date", required=True)
    wr.add_argument("--duration-days", type=int, required=True)
    wr.add_argument("--last-done", default=None, help="保养: 上次保养日")
    wr.add_argument("--photo", default="", help="保修卡照片路径(票据归档)")
    wr.add_argument("--note", default="")
    wre = wp.add_parser("repair", help="记录维修")
    wre.add_argument("--warranty-id", type=int, required=True)
    wre.add_argument("--date", required=True)
    wre.add_argument("--cost", type=float, default=0)
    wre.add_argument("--note", default="")
    wm = wp.add_parser("maintain", help="执行保养")
    wm.add_argument("--warranty-id", type=int, required=True)
    wm.add_argument("--date", required=True)
    wm.add_argument("--note", default="")

    p_cert = sub.add_parser("cert", help="证件管理")
    cp = p_cert.add_subparsers(dest="sub", required=True)
    cl = cp.add_parser("list", help="证件清单 HTML")
    cl.add_argument("--output", default=None)
    ca = cp.add_parser("add", help="登记证件")
    ca.add_argument("--type", required=True, choices=ops.CERT_TYPES)
    ca.add_argument("--holder", default="")
    ca.add_argument("--number", default="")
    ca.add_argument("--issued-at", default="")
    ca.add_argument("--expires-at", required=True)
    ca.add_argument("--photo", default="")
    ca.add_argument("--note", default="")

    p_acc = sub.add_parser("account", help="账号密码")
    ap = p_acc.add_subparsers(dest="sub", required=True)
    ai = ap.add_parser("init-master", help="首次设置主密钥")
    ai.add_argument("--master-key", required=True)
    al = ap.add_parser("list", help="账号清单 HTML(全脱敏)")
    al.add_argument("--output", default=None)
    aa = ap.add_parser("add", help="存账号(加密)")
    aa.add_argument("--platform", required=True)
    aa.add_argument("--user", default="")
    aa.add_argument("--pass", dest="password", required=True)
    aa.add_argument("--master-key", required=True)
    aa.add_argument("--type", default="其他", choices=ops.ACCOUNT_TYPES)
    aa.add_argument("--note", default="")
    ash = ap.add_parser("show", help="查看密码(敏感, 仅回显)")
    ash.add_argument("--platform", required=True)
    ash.add_argument("--master-key", required=True)
    aup = ap.add_parser("update", help="改账号(重新录入语义)")
    aup.add_argument("--platform", required=True)
    aup.add_argument("--master-key", required=True)
    aup.add_argument("--user", default=None)
    aup.add_argument("--pass", dest="password", default=None)
    aup.add_argument("--type", default=None, choices=ops.ACCOUNT_TYPES)
    aup.add_argument("--note", default=None)
    asm = ap.add_parser("set-master", help="改主密钥")
    asm.add_argument("--old", required=True)
    asm.add_argument("--new", required=True)

    args = None
    try:
        args = p.parse_args(argv)
    except SystemExit as e:  # argparse 参数非法 → 优雅降级(08 三层反馈)
        _print_json({"status": "error", "message": "参数校验失败(详见 usage)",
                     "suggestion": "修正参数后重试"})
        return e.code or 2

    try:
        if args.cmd == "purchase":
            if args.sub == "list":
                return _purchase_list(args)
            if args.sub == "add":
                return _purchase_add(args)
            return _purchase_stats(args)
        if args.cmd == "warranty":
            if args.sub == "list":
                return _warranty_list(args)
            if args.sub == "register":
                return _warranty_register(args)
            if args.sub == "repair":
                return _warranty_repair(args)
            return _warranty_maintain(args)
        if args.cmd == "cert":
            if args.sub == "list":
                return _cert_list(args)
            return _cert_add(args)
        if args.cmd == "account":
            if args.sub == "init-master":
                return _account_init(args)
            if args.sub == "list":
                return _account_list(args)
            if args.sub == "add":
                return _account_add(args)
            if args.sub == "show":
                return _account_show(args)
            if args.sub == "update":
                return _account_update(args)
            return _account_set_master(args)
    except Exception as e:  # 优雅降级: 任何异常 → 错误 JSON, 不裸堆栈
        _print_json({"status": "error", "message": f"{type(e).__name__}: {e}",
                     "suggestion": "复制日志排查或联系开发者"})
        return 1
    return 1


if __name__ == "__main__":
    # Windows 下仅 CLI 独立运行时包装 UTF-8(避免破坏 pytest capture)
    if sys.platform == "win32":
        import io
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    sys.exit(main())
