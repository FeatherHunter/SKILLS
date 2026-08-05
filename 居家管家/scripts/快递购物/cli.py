# cli.py - SM5 快递购物域 CLI 入口(域内独立入口 · 文件隔离契约)
#
# 用法:
#   python scripts/快递购物/cli.py list                     # 购物清单(HTML)
#   python scripts/快递购物/cli.py list-add --name "牛奶" --quantity 2 [--source 手动] [--routine 每周]
#   python scripts/快递购物/cli.py list-check --ids 1,2     # 销项(已买)
#   python scripts/快递购物/cli.py missing [--category-id N] [--output x.html]
#   python scripts/快递购物/cli.py missing-to-list --ids 1,2
#   python scripts/快递购物/cli.py express [--timeout-days 7] [--output x.html]
#   python scripts/快递购物/cli.py express-receive --id 3 [--to 在家]
#   python scripts/快递购物/cli.py stock [--output x.html]
#   python scripts/快递购物/cli.py stock-set-threshold --id 3 --threshold 2
#   python scripts/快递购物/cli.py stock-fix --id 3 --quantity 1 [--location "厨房/储物柜"]
#
# 公共层接入(T2 奠基后): 本域子命令注册进 scripts/home_manager.py(子命令注册模式)后,
# 本文件可保留为独立入口亦可退役;域开发期间不碰公共层(隔离契约)。
import argparse
import io
import json
import os
import sys


def _bootstrap():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    _scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)


def main():
    _bootstrap()
    from home_manager.db import get_conn
    from 快递购物 import ops

    parser = argparse.ArgumentParser(
        description="居家管家 · SM5 快递购物域(购物清单/缺货检测/快递跟踪/囤货盘点)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", help="子命令")

    # ── 购物清单 ──
    p = sub.add_parser("list", help="购物清单(HTML 视图)")
    p.add_argument("--output", default=None, help="HTML 输出路径;不填自动命名")
    p = sub.add_parser("list-add", help="添加清单条目(查重拒绝同名待买)")
    p.add_argument("--name", required=True, help="物品名")
    p.add_argument("--quantity", type=int, default=1, help="数量(默认 1)")
    p.add_argument("--source", default="手动", choices=["手动", "缺货检测", "例行"],
                   help="来源标注(默认 手动)")
    p.add_argument("--routine", default=None, choices=["每周", "每月"], help="例行采购周期")
    p.add_argument("--note", default="", help="备注")
    p = sub.add_parser("list-check", help="销项(已买),逗号分隔 ids")
    p.add_argument("--ids", required=True, help="条目 id 列表(逗号分隔)")

    # ── 缺货检测 ──
    p = sub.add_parser("missing", help="缺货检测(HTML 视图)")
    p.add_argument("--category-id", type=int, default=None, help="检测范围:分类 id(默认全屋)")
    p.add_argument("--output", default=None, help="HTML 输出路径;不填自动命名")
    p = sub.add_parser("missing-to-list", help="一键进清单(缺货 → 购物清单)")
    p.add_argument("--ids", required=True, help="缺货物品 id 列表(逗号分隔)")

    # ── 快递跟踪 ──
    p = sub.add_parser("express", help="快递跟踪(HTML 视图)")
    p.add_argument("--timeout-days", type=int, default=7, help="超时天数(默认 7)")
    p.add_argument("--output", default=None, help="HTML 输出路径;不填自动命名")
    p = sub.add_parser("express-receive", help="确认收货(快递中 → 在家/备用)")
    p.add_argument("--id", type=int, required=True, help="物品 id")
    p.add_argument("--to", default="在家", choices=["在家", "备用"], help="收货后状态(默认 在家)")
    p.add_argument("--location-id", type=int, default=None, help="指定快递中位置记录 id(可选)")

    # ── 囤货盘点 ──
    p = sub.add_parser("stock", help="囤货盘点(HTML 视图)")
    p.add_argument("--output", default=None, help="HTML 输出路径;不填自动命名")
    p = sub.add_parser("stock-set-threshold", help="设置囤货阈值")
    p.add_argument("--id", type=int, required=True, help="物品 id")
    p.add_argument("--threshold", type=int, required=True, help="阈值(≥1)")
    p = sub.add_parser("stock-fix", help="盘点修正数量(联动 3-3)")
    p.add_argument("--id", type=int, required=True, help="物品 id")
    p.add_argument("--quantity", type=int, required=True, help="修正后数量(≥0)")
    p.add_argument("--location", default=None, help="指定库存位置(多位置时必填)")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return 0

    from render_快递购物 import emit_sm5, emit_error

    def _scene_payload(template, data, scene_id, wake_word, command_cn, target=None,
                       copy_log=None, reminders=None):
        return emit_sm5(template, data, scene_id, wake_word, command_cn,
                        target=target, copy_log=copy_log, reminders=reminders,
                        output_path=getattr(args, "output", None))

    conn = get_conn()
    try:
        if args.cmd == "list":
            data = ops.list_view(conn)
            data["summary"] = {"title": "购物清单",
                               "subtitle": "勾选销项;采购闭环:新物品走录入、已有物品补数量",
                               "metrics": [
                                   {"label": "待买", "value": f"{len(data['items'])} 条"},
                                   {"label": "例行到期", "value": f"{len(data['routine_due'])} 条"},
                               ]}
            reminders = [{"type": "warn", "text": f"例行采购已到期:{d['name']}({d['routine']}),已重新加入清单"}
                         for d in data["routine_due"]]
            return _scene_payload("list.html", data, "SM5-1", "购物清单", "购物清单",
                                  target="购物清单", reminders=reminders)

        if args.cmd == "list-add":
            try:
                iid = ops.list_add(conn, args.name, quantity=args.quantity,
                                   source=args.source, routine=args.routine, note=args.note)
            except ValueError as e:
                return emit_error("购物清单", "购物清单", str(e),
                                  key_data={"name": args.name, "quantity": args.quantity})
            print(json.dumps({"status": "ok", "data": {"id": iid, "name": args.name,
                                                       "quantity": args.quantity,
                                                       "source": args.source,
                                                       "routine": args.routine},
                              "message": f"已加入购物清单:「{args.name}」×{args.quantity}"},
                             ensure_ascii=False))
            return 0

        if args.cmd == "list-check":
            ids = [int(x) for x in args.ids.split(",") if x.strip()]
            try:
                done = ops.list_check(conn, ids)
            except ValueError as e:
                return emit_error("购物清单", "购物清单", str(e), key_data={"ids": args.ids})
            print(json.dumps({"status": "ok", "data": {"done": done, "ids": ids},
                              "message": f"已销项 {done} 条(已买)"}, ensure_ascii=False))
            return 0

        if args.cmd == "missing":
            data = ops.missing_detect(conn, category_id=args.category_id)
            data["summary"] = {"title": "缺货检测",
                               "subtitle": "检测范围:" + data["scope"] + ";勾选后一键进购物清单",
                               "metrics": [
                                   {"label": "缺货/不足", "value": f"{len(data['items'])} 件"},
                                   {"label": "范围", "value": data["scope"]},
                               ]}
            reminders = ([{"type": "warn", "text": f"库存不足:{it['name']}(当前 {it['current']}/阈值 {it['threshold']})"}
                          for it in data["items"][:5]]
                         if data["items"] else [{"type": "", "text": "库存充足,无缺货"}])
            return _scene_payload("missing.html", data, "SM5-2", "缺货检测", "缺货检测",
                                  target="缺货检测", reminders=reminders)

        if args.cmd == "missing-to-list":
            ids = [int(x) for x in args.ids.split(",") if x.strip()]
            try:
                r = ops.missing_to_list(conn, ids)
            except ValueError as e:
                return emit_error("缺货检测", "缺货检测", str(e), key_data={"ids": args.ids})
            msg = f"已加入购物清单 {r['added']} 件"
            if r["dup_skips"]:
                msg += f";已在清单中跳过:{'、'.join(r['dup_skips'])}"
            print(json.dumps({"status": "ok", "data": r, "message": msg}, ensure_ascii=False))
            return 0

        if args.cmd == "express":
            data = ops.express_view(conn, timeout_days=args.timeout_days)
            overdue = [it for it in data["items"] if it["overdue"]]
            data["summary"] = {"title": "快递跟踪",
                               "subtitle": "确认收货后状态变更为在家/备用;超时默认 " + str(args.timeout_days) + " 天",
                               "metrics": [
                                   {"label": "快递中", "value": f"{len(data['items'])} 件"},
                                   {"label": "超时", "value": f"{len(overdue)} 件"},
                               ]}
            reminders = [{"type": "danger", "text": f"超时提醒:{it['name']} 已等 {it['days']} 天(> {args.timeout_days} 天),考虑联系卖家或标记遗失"}
                         for it in overdue]
            return _scene_payload("express.html", data, "SM5-3", "查快递", "查快递",
                                  target="快递跟踪", reminders=reminders)

        if args.cmd == "express-receive":
            try:
                r = ops.express_receive(conn, args.id, to_status=args.to,
                                        location_id=args.location_id)
            except ValueError as e:
                return emit_error("查快递", "查快递", str(e),
                                  key_data={"item_id": args.id, "to": args.to})
            print(json.dumps({"status": "ok", "data": r,
                              "message": f"已确认收货:{r['location']} 快递中 → {r['to_status']}"},
                             ensure_ascii=False))
            return 0

        if args.cmd == "stock":
            data = ops.stock_view(conn)
            low = [it for it in data["items"] if it["status"] != "充足"]
            data["summary"] = {"title": "囤货盘点",
                               "subtitle": "有阈值物品的库存管理;设置/修正后 AI 写库",
                               "metrics": [
                                   {"label": "囤货物品", "value": f"{len(data['items'])} 件"},
                                   {"label": "低/空", "value": f"{len(low)} 件"},
                               ]}
            reminders = [{"type": "warn", "text": f"库存不足:{it['name']}(当前 {it['current']}/阈值 {it['threshold']})"}
                         for it in low[:5]]
            return _scene_payload("stock.html", data, "SM5-4", "囤货盘点", "囤货盘点",
                                  target="囤货盘点", reminders=reminders)

        if args.cmd == "stock-set-threshold":
            try:
                ops.stock_set_threshold(conn, args.id, args.threshold)
            except ValueError as e:
                return emit_error("囤货盘点", "囤货盘点", str(e),
                                  key_data={"item_id": args.id, "threshold": args.threshold})
            print(json.dumps({"status": "ok",
                              "data": {"item_id": args.id, "threshold": args.threshold},
                              "message": f"物品 {args.id} 阈值已设置为 {args.threshold}"},
                             ensure_ascii=False))
            return 0

        if args.cmd == "stock-fix":
            try:
                r = ops.stock_fix(conn, args.id, args.quantity, location=args.location)
            except ValueError as e:
                return emit_error("囤货盘点", "囤货盘点", str(e),
                                  key_data={"item_id": args.id, "quantity": args.quantity})
            print(json.dumps({"status": "ok", "data": r,
                              "message": f"已修正:{r['location']} → {r['quantity']}"},
                             ensure_ascii=False))
            return 0

        parser.print_help()
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
