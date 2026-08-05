# cli.py - SM9 域 CLI 子命令注册与分发(T2 公共层奠基 · CLI 注册模式)
# home_manager.py 接线: import 联动.cli / register(subparsers) / run(args)
# 独立运行: python -m 联动.cli overview ...(T2 完成前 AI 直接调用)
import argparse
import io
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))


def register(subparsers):
    """注册 SM9 子命令(sm9- 前缀,与旧命令并存)"""
    p = subparsers.add_parser("sm9-overview", help="联动总览(能力索引 + 偏好设置 · SM9-1)")
    p.add_argument("--output", default=None, help="HTML 输出路径")

    p = subparsers.add_parser("sm9-food", help="食品联动(记到卡路里/查热量 · SM9-2)")
    p.add_argument("--item-id", type=int, required=True, help="物品 ID")
    p.add_argument("--action", default="log", choices=["log", "query"],
                   help="联动动作: log=记到今日饮食, query=查热量")
    p.add_argument("--output", default=None, help="HTML 输出路径")

    p = subparsers.add_parser("sm9-price", help="价格联动(记到记账 · SM9-3)")
    p.add_argument("--item-id", type=int, required=True, help="物品 ID")
    p.add_argument("--direction", default="expense", choices=["expense", "income"],
                   help="记账方向: expense=记支出, income=记收入(退货退款)")
    p.add_argument("--output", default=None, help="HTML 输出路径")

    p = subparsers.add_parser("sm9-prefs", help="联动偏好设置(频控)")
    p.add_argument("--key", required=True, choices=["food", "price"],
                   help="偏好项: food=食品联动, price=价格联动")
    p.add_argument("--value", required=True, choices=["ask", "remember", "off"],
                   help="频控: ask=每次询问, remember=记住上次选择, off=关闭")
    p.add_argument("--output", default=None, help="HTML 输出路径(可选,默认仅文字回执)")


def run(args):
    """SM9 命令分发(返回进程退出码)"""
    from 联动 import ops
    from render_联动 import emit_link, emit_error

    cmd = args.command

    if cmd == "sm9-overview":
        data = ops.overview_data()
        return emit_link("link_overview.html", data, "SM9-1", "联动总览", "联动总览",
                         target="联动条目", copy_log={"call_chain": "python home_manager.py sm9-overview",
                                                      "data_structure": "LINK_CATALOG + link_prefs.json"},
                         output_path=args.output)

    if cmd == "sm9-food":
        item = ops.get_item(args.item_id)
        if not item:
            return emit_error("记到卡路里", "食品联动", f"未找到 ID={args.item_id} 的物品",
                              {"item_id": args.item_id}, "换一个物品 ID 重试",
                              output_path=args.output)
        ok, msg, data = ops.food_data(item, args.action)
        if not ok:
            return emit_error("记到卡路里", "食品联动", msg, data.get("item", {}),
                              data.get("suggest"), output_path=args.output)
        return emit_link("link_food.html", data, "SM9-2", "记到卡路里", "食品联动",
                         target=item.get("name"),
                         copy_log={"call_chain": "python home_manager.py sm9-food "
                                                  f"--item-id {args.item_id} --action {args.action}",
                                   "data_structure": "items/item_locations 只读 + 启发式判定"},
                         output_path=args.output, message=msg)

    if cmd == "sm9-price":
        item = ops.get_item(args.item_id)
        if not item:
            return emit_error("记到记账", "价格联动", f"未找到 ID={args.item_id} 的物品",
                              {"item_id": args.item_id}, "换一个物品 ID 重试",
                              output_path=args.output)
        ok, msg, data = ops.price_data(item, args.direction)
        if not ok:
            return emit_error("记到记账", "价格联动", msg, data.get("item", {}),
                              data.get("suggest"), output_path=args.output)
        return emit_link("link_price.html", data, "SM9-3", "记到记账", "价格联动",
                         target=item.get("name"),
                         copy_log={"call_chain": "python home_manager.py sm9-price "
                                                  f"--item-id {args.item_id} --direction {args.direction}",
                                   "data_structure": "items.purchase_price × quantity → 总价"},
                         output_path=args.output, message=msg)

    if cmd == "sm9-prefs":
        ok, msg, _ = ops.save_prefs({args.key: args.value})
        if not ok:
            return emit_error("联动总览", "联动偏好", msg, {args.key: args.value},
                              output_path=args.output)
        print(msg)
        if args.output:
            data = ops.overview_data()
            return emit_link("link_overview.html", data, "SM9-1", "联动总览", "联动总览",
                             target="联动条目",
                             copy_log={"call_chain": "python home_manager.py sm9-prefs "
                                                      f"--key {args.key} --value {args.value}",
                                       "data_structure": "link_prefs.json"},
                             output_path=args.output)
        return 0

    return 1


def main(argv=None):
    """独立运行入口(T2 接线前 AI 直接调用 python -m 联动.cli)"""
    parser = argparse.ArgumentParser(description="居家管家 · SM9 联动功能域")
    sub = parser.add_subparsers(dest="command", required=True)
    register(sub)
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
