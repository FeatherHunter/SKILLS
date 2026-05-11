# home_manager.py - CLI 入口（argparse + 命令路由）
# 内部引用 home_manager/ 包中的模块

import sys
import os

# 强制 UTF-8 输出（修复 Windows GBK 编码问题）
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def main():
    # 添加包路径，确保能找到 home_manager 包
    _pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _pkg_dir not in sys.path:
        sys.path.insert(0, _pkg_dir)

    from home_manager.db import DB_PATH, PHOTOS_DIR, init_db
    from home_manager.item_ops import (
        add_item, search_items, update_item,
        list_items, item_detail
    )
    from home_manager.inventory_ops import inventory, stats
    from home_manager.tag_ops import tag_merge, list_tags

    import argparse

    parser = argparse.ArgumentParser(
        description="居家管家 - 家庭物品管理系统 v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python home_manager.py add --name "白T恤" --category 衣物 --location "卧室/衣柜/上层" --tags "白色,短袖"
  python home_manager.py search --name "T恤"
  python home_manager.py search --location "卧室" --status "在家"
  python home_manager.py update --id 1 --status "借用中"
  python home_manager.py list --location "卧室/衣柜"
  python home_manager.py inventory --location "卧室"
  python home_manager.py stats --type summary
  python home_manager.py tag-merge --from "白" --to "白色"
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # ── init ──
    p_init = subparsers.add_parser("init", help="初始化数据库（建表+索引）")

    # ── add ──
    p_add = subparsers.add_parser("add", help="添加物品")
    p_add.add_argument("--name", required=True, help="物品名称")
    p_add.add_argument("--category", required=True, help="分类")
    p_add.add_argument("--location", required=True, help="存放位置（路径格式）")
    p_add.add_argument("--owner", default="使用者", help="所有者")
    p_add.add_argument("--quantity", type=int, default=1, help="数量（默认1）")
    p_add.add_argument("--price", type=float, default=None, help="单价（元/件）")
    p_add.add_argument("--purchase-date", default=None, help="购买日期（YYYY-MM-DD）")
    p_add.add_argument("--expiration-date", default=None, help="过期日期（YYYY-MM-DD）")
    p_add.add_argument("--remark", default="", help="备注")
    p_add.add_argument("--tags", default="", help="标签（逗号分隔）")
    p_add.add_argument("--photo", default="", help="图片路径")
    p_add.add_argument("--location-status", default="在家", help="存放状态（默认在家）")

    # ── search ──
    p_search = subparsers.add_parser("search", help="搜索物品")
    p_search.add_argument("--name", default=None, help="物品名称（支持模糊）")
    p_search.add_argument("--category", default=None, help="分类")
    p_search.add_argument("--location", default=None, help="位置（支持模糊）")
    p_search.add_argument("--tag", default=None, help="标签（精确匹配）")
    p_search.add_argument("--status", default=None, help="状态")
    p_search.add_argument("--exact", action="store_true", help="名称精确匹配")
    p_search.add_argument("--limit", type=int, default=20, help="返回数量上限")

    # ── update ──
    p_update = subparsers.add_parser("update", help="更新物品")
    p_update.add_argument("--id", type=int, required=True, help="物品ID")
    p_update.add_argument("--name", default=None, help="物品名称")
    p_update.add_argument("--category", default=None, help="分类")
    p_update.add_argument("--owner", default=None, help="所有者")
    p_update.add_argument("--price", type=float, default=None, help="单价（元/件）")
    p_update.add_argument("--purchase-date", default=None, help="购买日期（YYYY-MM-DD）")
    p_update.add_argument("--expiration-date", default=None, help="过期日期（YYYY-MM-DD）")
    p_update.add_argument("--remark", default=None, help="备注")
    p_update.add_argument("--tags", default=None, help="标签（逗号分隔，覆盖）")
    p_update.add_argument("--photo", default=None, help="图片路径")
    p_update.add_argument("--new-location", default=None, help="新存放位置路径（改变位置）")
    p_update.add_argument("--location", default=None, help="指定位置（配合--location-status使用）")
    p_update.add_argument("--quantity", type=int, default=None, help="直接设置数量")
    p_update.add_argument("--minus", type=int, default=None, help="减少数量（如喝掉1瓶）")
    p_update.add_argument("--plus", type=int, default=None, help="增加数量（如买了3瓶）")
    p_update.add_argument("--location-status", default=None, help="存放状态（如借用中、备用、快递中）")

    # ── list ──
    p_list = subparsers.add_parser("list", help="列出物品")
    p_list.add_argument("--location", default=None, help="位置")
    p_list.add_argument("--status", default=None, help="状态")
    p_list.add_argument("--category", default=None, help="分类")
    p_list.add_argument("--owner", default=None, help="所有者")
    p_list.add_argument("--sort", default="name",
                        choices=["name", "recent", "frequent", "updated", "dormant"],
                        help="排序方式")
    p_list.add_argument("--limit", type=int, default=100, help="返回数量上限")

    # ── inventory ──
    p_inventory = subparsers.add_parser("inventory", help="盘点指定位置")
    p_inventory.add_argument("--location", required=True, help="要盘点的位置")

    # ── stats ──
    p_stats = subparsers.add_parser("stats", help="频率统计")
    p_stats.add_argument("--type", default="summary",
                         choices=["frequent", "dormant", "summary"],
                         help="统计类型：frequent=高频, dormant=长期未碰, summary=总览")
    p_stats.add_argument("--limit", type=int, default=20, help="返回数量上限")

    # ── tag-merge ──
    p_merge = subparsers.add_parser("tag-merge", help="合并标签")
    p_merge.add_argument("--from", dest="from_tag", required=True, help="要被合并的标签")
    p_merge.add_argument("--to", dest="to_tag", required=True, help="合并目标标签")

    # ── tag-list ──
    p_taglist = subparsers.add_parser("tag-list", help="列出所有标签")

    # ── detail ──
    p_detail = subparsers.add_parser("detail", help="查看物品详情")
    p_detail.add_argument("--id", type=int, required=True, help="物品ID")

    args = parser.parse_args()

    if args.command == "init":
        init_db()
        print("✓ 数据库初始化完成")
        print(f"  数据库: {DB_PATH}")
        print(f"  图片目录: {PHOTOS_DIR}")

    elif args.command == "add":
        return add_item(
            name=args.name, category=args.category,
            location=args.location,
            owner=args.owner, quantity=args.quantity,
            purchase_price=args.price, purchase_date=args.purchase_date,
            expiration_date=args.expiration_date, remark=args.remark, tags=args.tags,
            photo=args.photo,
            location_status=args.location_status
        )

    elif args.command == "search":
        return search_items(
            name=args.name, category=args.category, location=args.location,
            tag=args.tag, status=args.status, limit=args.limit, exact=args.exact
        )

    elif args.command == "update":
        return update_item(
            item_id=args.id, name=args.name, category=args.category, owner=args.owner,
            remark=args.remark, tags=args.tags,
            purchase_price=args.price, purchase_date=args.purchase_date,
            expiration_date=args.expiration_date, photo=args.photo,
            new_location=args.new_location, quantity=args.quantity,
            minus=args.minus, plus=args.plus,
            location=args.location, location_status=args.location_status
        )

    elif args.command == "list":
        return list_items(
            location=args.location, status=args.status, category=args.category,
            owner=args.owner, sort_by=args.sort, limit=args.limit
        )

    elif args.command == "inventory":
        return inventory(location=args.location)

    elif args.command == "stats":
        return stats(stat_type=args.type, limit=args.limit)

    elif args.command == "tag-merge":
        return tag_merge(from_tag=args.from_tag, to_tag=args.to_tag)

    elif args.command == "tag-list":
        return list_tags()

    elif args.command == "detail":
        return item_detail(item_id=args.id)

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
