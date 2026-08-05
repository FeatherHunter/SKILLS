# link_center.py - SM9 联动功能域 CLI 渲染入口(独立脚本 · 不碰公共层 CLI)
#
# 用法:
#   python link_center.py overview [--output path]
#   python link_center.py food   --item-id N [--action log|query] [--output path]
#   python link_center.py price  --item-id N [--direction expense|income] [--output path]
#   python link_center.py prefs  --key food|price --value ask|remember|off
#
# 隔离契约: 本脚本 = scripts/联动/ 域的一部分;home_manager.py 由 T2 奠基统一注册,
# 本批不修改公共层(T2 完成后再按注册模式接入)。
# 输出命名: 12.A `<command_cn>_<YYYYMMDD>_<HHMMSS>.html`(与公共层规则一致)
import argparse
import io
import os
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 把 scripts/ 加入 sys.path(与 home_manager.py 同策略)
_SCRIPTS = Path(__file__).parent.resolve()
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from render import render_page, resolve_output_root

# 场景 → 模板/command_cn 映射(本域内,不写公共层映射表)
SCENES = {
    "overview": {"template": "联动/link_overview.html", "command_cn": "联动总览"},
    "food":     {"template": "联动/link_food.html",     "command_cn": "记到卡路里"},
    "price":    {"template": "联动/link_price.html",    "command_cn": "记到记账"},
}
HTML_SUBDIR = "home_manager_html"


def _auto_output_path(template_name: str, command_cn: str) -> Path:
    """12.A 自动命名: <root>/home_manager_html/<command_cn>_<ts>.html"""
    root = resolve_output_root()
    out_dir = root / HTML_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return out_dir / f"{command_cn}_{stamp}.html"


def json_dumps(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)


def _emit(payload: dict, template_name: str, output: str | None, message: str) -> int:
    cmd = next((s["command_cn"] for s in SCENES.values()
                if s["template"] == template_name), "联动")
    out = output or str(_auto_output_path(template_name, cmd))
    result = render_page(template_name, payload, out, message)
    print(json_dumps(result))
    return 0 if result["status"] == "ok" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="居家管家 · SM9 联动功能域渲染")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ov = sub.add_parser("overview", help="联动总览(能力索引 + 偏好设置)")
    p_ov.add_argument("--output", default=None, help="HTML 输出路径")

    p_food = sub.add_parser("food", help="食品联动(记到卡路里/查热量)")
    p_food.add_argument("--item-id", type=int, required=True, help="物品 ID")
    p_food.add_argument("--action", default="log", choices=["log", "query"],
                        help="联动动作: log=记到今日饮食, query=查热量")
    p_food.add_argument("--output", default=None, help="HTML 输出路径")

    p_price = sub.add_parser("price", help="价格联动(记到记账)")
    p_price.add_argument("--item-id", type=int, required=True, help="物品 ID")
    p_price.add_argument("--direction", default="expense", choices=["expense", "income"],
                         help="记账方向: expense=记支出, income=记收入(退货退款)")
    p_price.add_argument("--output", default=None, help="HTML 输出路径")

    p_prefs = sub.add_parser("prefs", help="联动偏好设置(频控)")
    p_prefs.add_argument("--key", required=True, choices=["food", "price"],
                         help="偏好项: food=食品联动, price=价格联动")
    p_prefs.add_argument("--value", required=True, choices=["ask", "remember", "off"],
                         help="频控: ask=每次询问, remember=记住上次选择, off=关闭")
    p_prefs.add_argument("--output", default=None, help="HTML 输出路径(可选,默认仅文字回执)")

    args = parser.parse_args(argv)

    if args.command == "overview":
        from 联动.ops import build_overview_payload
        payload = build_overview_payload()
        return _emit(payload, "联动/link_overview.html", args.output,
                     "联动功能总览已生成")

    if args.command == "food":
        from 联动.ops import get_item, build_food_payload
        item = get_item(args.item_id)
        if not item:
            return _emit({"status": "error",
                          "data": {"scene": "食品联动", "operation": "把物品记到卡路里",
                                   "reason": f"未找到 ID={args.item_id} 的物品",
                                   "item": {}, "next": "换一个物品 ID 重试"},
                          "message": "物品不存在"},
                         "联动/link_food.html", args.output, "物品不存在")
        payload = build_food_payload(item, args.action)
        return _emit(payload, "联动/link_food.html", args.output, payload["message"])

    if args.command == "price":
        from 联动.ops import get_item, build_price_payload
        item = get_item(args.item_id)
        if not item:
            return _emit({"status": "error",
                          "data": {"scene": "价格联动", "operation": "把物品价格记到记账",
                                   "reason": f"未找到 ID={args.item_id} 的物品",
                                   "item": {}, "next": "换一个物品 ID 重试"},
                          "message": "物品不存在"},
                         "联动/link_price.html", args.output, "物品不存在")
        payload = build_price_payload(item, args.direction)
        return _emit(payload, "联动/link_price.html", args.output, payload["message"])

    if args.command == "prefs":
        from 联动.ops import save_prefs
        result = save_prefs({args.key: args.value})
        print(json_dumps(result))
        if args.output and result.get("ok"):
            from 联动.ops import build_overview_payload
            payload = build_overview_payload()
            return _emit(payload, "联动/link_overview.html", args.output,
                         "联动总览已生成(含新偏好)")
        return 0 if result.get("ok") else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
