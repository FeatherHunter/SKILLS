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

    from home_manager.db import DB_PATH, PHOTOS_DIR, init_db, get_conn
    from home_manager.item_ops import (
        add_item, search_items, update_item,
        list_items, item_detail,
        search_items_json, item_detail_json, list_items_json,
        search_items_payload, item_detail_payload, list_items_payload,
    )
    from home_manager.inventory_ops import inventory, stats
    from home_manager.tag_ops import tag_merge, list_tags
    from home_manager.location_ops import (
        suggest_locations, suggest_locations_with_examples,
        find_location_by_reference
    )

    # 导入账号模块（路径：../accounts.py）
    _scripts_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _scripts_dir)
    from accounts import (
        is_master_key_set, verify_master_key, _write_master_key,
        account_add, account_list, account_show, account_del, account_set_master
    )

    # SM1 物品管理域(T2 公共层奠基: CLI 注册 + 分发,域代码全在 scripts/物品/)
    from 物品.cli import register as sm1_register
    from 物品.cli import run as sm1_run

    import argparse

    parser = argparse.ArgumentParser(
        description="居家管家 - 家庭物品管理系统 v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python home_manager.py add --name "白T恤" --category 衣物 --location "卧室/衣柜/上层" --tags "白色,短袖"
  python home_manager.py search --name "T恤"
  python home_manager.py search --location "卧室" --status "在家"
  python home_manager.py update --id 1 --location-status "借用中"
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
    p_add.add_argument("--category-id", type=int, required=True, help="分类 ID(从 categories 表查,必填)")
    p_add.add_argument("--location", required=True, help="存放位置（路径格式）")
    p_add.add_argument("--owner", default="使用者", help="所有者")
    p_add.add_argument("--quantity", type=int, default=1, help="数量（默认1）")
    p_add.add_argument("--price", type=float, default=None, help="单价（元/件）")
    p_add.add_argument("--purchase-date", default=None, help="购买日期（YYYY-MM-DD）")
    p_add.add_argument("--expiration-date", default=None, help="过期日期（YYYY-MM-DD）")
    p_add.add_argument("--remark", default="", help="备注")
    p_add.add_argument("--tags", default="", help="标签（逗号分隔）")
    p_add.add_argument("--photo", default="", help="图片路径")
    p_add.add_argument("--location-status", default=None, help="存放状态（默认根据位置推断：位置含\"快递\"则为\"快递中\"，否则为\"在家\"")
    p_add.add_argument("--preview", action="store_true", help="先输出录入预览 HTML 再写入数据库")
    p_add.add_argument("--preview-output", default=None, help="预览 HTML 输出路径")

    # ── search ──
    p_search = subparsers.add_parser("search", help="搜索物品")
    p_search.add_argument("--name", default=None, help="物品名称（支持模糊）")
    p_search.add_argument("--category-id", type=int, default=None, help="分类 ID(从 categories 表查)")
    p_search.add_argument("--location", default=None, help="位置（支持模糊）")
    p_search.add_argument("--tag", default=None, help="标签（精确匹配）")
    p_search.add_argument("--status", default=None, help="状态")
    p_search.add_argument("--exact", action="store_true", help="名称精确匹配")
    p_search.add_argument("--limit", type=int, default=20, help="返回数量上限")
    p_search.add_argument("--output", default=None, help="HTML 输出路径；不填写到 output/")

    # ── update ──
    p_update = subparsers.add_parser("update", help="更新物品")
    p_update.add_argument("--id", type=int, required=True, help="物品ID")
    p_update.add_argument("--name", default=None, help="物品名称")
    p_update.add_argument("--category-id", type=int, default=None, help="分类 ID(从 categories 表查)")
    p_update.add_argument("--owner", default=None, help="所有者")
    p_update.add_argument("--price", type=float, default=None, help="单价（元/件）")
    p_update.add_argument("--purchase-date", default=None, help="购买日期（YYYY-MM-DD）")
    p_update.add_argument("--expiration-date", default=None, help="过期日期（YYYY-MM-DD）")
    p_update.add_argument("--remark", default=None, help="备注")
    p_update.add_argument("--tags", default=None, help="标签（逗号分隔，覆盖）")
    p_update.add_argument("--add-tag", default=None,
                         help="追加 tag（逗号分隔，如 --add-tag 红色,短袖）")
    p_update.add_argument("--remove-tag", default=None,
                         help="删除 tag（逗号分隔，如 --remove-tag 白色,旧）")
    p_update.add_argument("--photo", default=None, help="图片路径")
    p_update.add_argument("--new-location", default=None, help="新存放位置路径（改变位置）")
    p_update.add_argument("--location", default=None, help="指定位置（配合--location-status使用）")
    p_update.add_argument("--quantity", type=int, default=None, help="直接设置数量")
    p_update.add_argument("--minus", type=int, default=None, help="减少数量（如喝掉1瓶）")
    p_update.add_argument("--plus", type=int, default=None, help="增加数量（如买了3瓶）")
    p_update.add_argument("--add-location", default=None, help="追加新位置记录（不替换现有位置，一物多位置用）")
    p_update.add_argument("--add-quantity", type=int, default=1, help="追加位置的数量（默认1）")
    p_update.add_argument("--add-reason", default=None, help="追加位置的原因/备注")
    p_update.add_argument("--add-location-status", default="在家", help="追加位置的状态（默认在家）")
    p_update.add_argument("--add-purchase-date", default=None, help="追加位置的购买日期（YYYY-MM-DD）")
    p_update.add_argument("--add-expiration-date", default=None, help="追加位置的过期日期（YYYY-MM-DD）")
    p_update.add_argument("--location-status", default=None, help="存放状态（如借用中、备用、快递中）")

    # ── list ──
    p_list = subparsers.add_parser("list", help="列出物品")
    p_list.add_argument("--location", default=None, help="位置")
    p_list.add_argument("--status", default=None, help="状态")
    p_list.add_argument("--category-id", type=int, default=None, help="分类 ID(从 categories 表查)")
    p_list.add_argument("--owner", default=None, help="所有者")
    p_list.add_argument("--sort", default="name",
                        choices=["name", "recent", "frequent", "updated", "dormant"],
                        help="排序方式")
    p_list.add_argument("--limit", type=int, default=100, help="返回数量上限")
    p_list.add_argument("--output", default=None, help="HTML 输出路径；不填写到 output/")

    # ── inventory ──
    p_inventory = subparsers.add_parser("inventory", help="盘点指定位置")
    p_inventory.add_argument("--location", required=True, help="要盘点的位置")
    p_inventory.add_argument("--output", default=None, help="HTML 输出路径；不填写走 CLI 文本")

    # ── suggest-locations（位置推荐，录物品时辅助）──
    p_suggest = subparsers.add_parser("suggest-locations", help="推荐同类物品常用位置（录物品时辅助定位）")
    p_suggest.add_argument("--category-id", type=int, required=True, help="分类 ID(从 categories 表查,必填)")
    p_suggest.add_argument("--with-examples", action="store_true", help="附带显示每个位置的代表物品名")
    p_suggest.add_argument("--limit", type=int, default=10, help="返回位置数量上限")

    # ── find-location（参考物品锚定）──
    p_find = subparsers.add_parser("find-location", help="根据参考物品名找它的位置（'和XX放一起'用）")
    p_find.add_argument("--reference", required=True, help="参考物品名（支持模糊）")
    p_find.add_argument("--limit", type=int, default=5, help="返回候选物品数量上限")

    # ── stats ──
    p_stats = subparsers.add_parser("stats", help="统计(频率/过期/总览/闲置/盘点统计)")
    p_stats.add_argument("--type", default="summary",
                         choices=["frequent", "dormant", "summary", "expiring",
                                  "overview", "idle", "inventory-stat"],
                         help="统计类型：frequent=高频, dormant=长期未碰, summary=总览, "
                              "expiring=快过期, overview=物品总览HTML, idle=闲置检测HTML, "
                              "inventory-stat=盘点统计HTML")
    p_stats.add_argument("--limit", type=int, default=20, help="返回数量上限")
    p_stats.add_argument("--days", type=int, default=None, help="（expiring用）预告天数窗口，默认30，可选7/30/90；（idle用）闲置阈值，默认90，可选90/180/365")
    p_stats.add_argument("--expired-only", action="store_true", help="（expiring用）只看已过期")
    p_stats.add_argument("--category-id", type=int, default=None, help="（expiring/idle用）按分类 ID 筛选")
    p_stats.add_argument("--output", default=None, help="HTML 输出路径（overview/idle/expiring/inventory-stat 支持）")

    # ── outfit (穿什么 HTML 化) ──
    p_outfit = subparsers.add_parser("outfit", help="今日穿搭选择器")
    p_outfit.add_argument("--status", default="在家", help="筛选位置状态，默认'在家'")
    p_outfit.add_argument("--output", required=True, help="HTML 输出路径")

    # ── trip (带物品 / 归物品 HTML 化) ──
    p_trip = subparsers.add_parser("trip", help="旅行清单（打包/归位）")
    p_trip.add_argument("--mode", default="pack", choices=["pack", "return"],
                        help="pack=出门打包, return=回家归位")

    # ── P1-9c HELP 中心(总纲 07 §)──
    p_help = subparsers.add_parser("help", help="HELP 能力速查(总纲 07 §)")
    p_help.add_argument("--output", default=None, help="HTML 输出路径")
    p_trip.add_argument("--output", required=True, help="HTML 输出路径")

    # ── tag-merge ──
    p_merge = subparsers.add_parser("tag-merge", help="合并标签")
    p_merge.add_argument("--from", dest="from_tag", required=True, help="要被合并的标签")
    p_merge.add_argument("--to", dest="to_tag", required=True, help="合并目标标签")

    # ── tag-list ──
    p_taglist = subparsers.add_parser("tag-list", help="列出所有标签")

    # ── detail ──
    p_detail = subparsers.add_parser("detail", help="查看物品详情")
    p_detail.add_argument("--id", type=int, required=True, help="物品ID")
    p_detail.add_argument("--output", default=None, help="HTML 输出路径；不填写到 output/")

    # ── account ──
    p_account = subparsers.add_parser("account", help="账号管理（密码加密存储）")
    p_account.add_argument("--action", required=True,
                           choices=["init", "add", "list", "show", "del", "set-master"],
                           help="操作：init=初始化密钥, add=添加账号, list=列出账号, show=查看密码, del=删除账号, set-master=修改密钥")
    p_account.add_argument("--master-key", default=None, help="Master key（验证/设置用）")
    p_account.add_argument("--platform", default=None, help="平台名（如 zlife）")
    p_account.add_argument("--user", default=None, help="用户名/账号")
    p_account.add_argument("--pass", dest="password", default=None, help="密码")
    p_account.add_argument("--tags", default=None, help="标签（逗号分隔）")
    p_account.add_argument("--note", default=None, help="备注")
    p_account.add_argument("--new-master-key", default=None, help="新 master key（用于 set-master）")

    # ── family (SM7 家庭协作域: 家人档案 / 借用管理) ──
    p_family = subparsers.add_parser("family", help="家庭协作（家人档案/借用管理）")
    p_family.add_argument("--action", required=True,
                          choices=["borrow-add", "borrow-return", "borrow-list", "borrow-remind",
                                   "member-add", "member-remove", "member-list", "member-assign"],
                          help="操作：borrow-*=借用管理, member-*=家人档案")
    p_family.add_argument("--direction", default=None, choices=["借出", "借入"],
                          help="借出/借入（borrow-add）")
    p_family.add_argument("--item-id", type=int, default=None, help="库内物品 ID（借出必填）")
    p_family.add_argument("--item-name", default=None, help="物品名（借入自由文本/借出自动回填）")
    p_family.add_argument("--object", default=None, help="借用对象（家人称呼或外部联系人）")
    p_family.add_argument("--borrowed-at", default=None, help="借出日期（YYYY-MM-DD，默认今天）")
    p_family.add_argument("--due-date", default=None, help="约定归还日（YYYY-MM-DD）")
    p_family.add_argument("--remark", default=None, help="借用备注")
    p_family.add_argument("--borrow-id", type=int, default=None, help="借用记录 ID（归还/催还用）")
    p_family.add_argument("--name", default=None, help="成员称呼（member-* 用）")
    p_family.add_argument("--relation", default=None, help="成员关系（妈妈/老婆/宝宝…）")
    p_family.add_argument("--note", default=None, help="成员备注")
    p_family.add_argument("--item-ids", default=None, help="物品 ID 列表（逗号分隔，标记归属用）")
    p_family.add_argument("--output", default=None, help="HTML 输出路径")

    # SM1 物品管理域子命令(T2 · 29 场景)
    sm1_register(subparsers)

    args = parser.parse_args()

    if args.command == "init":
        init_db()
        print("✓ 数据库初始化完成")
        print(f"  数据库: {DB_PATH}")
        print(f"  图片目录: {PHOTOS_DIR}")

    elif args.command == "add":
        if args.preview:
            from render import render_page, build_command, split_tags
            from home_manager.validators import validate_hard_rules
            import json as _json
            draft = {
                "name": args.name, "category_id": args.category_id,
                "category_name": "", "location": args.location,
                "owner": args.owner, "quantity": args.quantity,
                "price": args.price, "purchase_date": args.purchase_date,
                "expiration_date": args.expiration_date,
                "location_status": args.location_status,
                "remark": args.remark, "tags": split_tags(args.tags),
                "photo": args.photo, "similar_items": [],
            }
            checks, missing = validate_hard_rules(draft)
            payload = {
                "status": "ok",
                "data": {
                    "draft": draft, "checks": checks, "missing": missing,
                    "command": build_command(draft),
                },
                "message": "录入预览",
            }
            result = render_page("add_preview.html", payload, args.preview_output,
                                 "录入预览 HTML 已生成")
            print(_json.dumps(result, ensure_ascii=False))
            if result["status"] != "ok":
                return 1
            print("预览已生成，请在 HTML 页面核对后再确认执行 add。")
            return 0
        return add_item(
            name=args.name, category_id=args.category_id,
            location=args.location,
            owner=args.owner, quantity=args.quantity,
            purchase_price=args.price, purchase_date=args.purchase_date,
            expiration_date=args.expiration_date, remark=args.remark, tags=args.tags,
            photo=args.photo,
            location_status=args.location_status
        )

    elif args.command == "search":
        from render import emit
        items = search_items_payload(
            name=args.name, category_id=args.category_id, location=args.location,
            tag=args.tag, status=args.status, limit=args.limit, exact=args.exact
        )
        # status=快递中 自动用快递专用模板
        template_name = "delivery_check.html" if args.status == "快递中" else "search_results.html"
        payload = {
            "status": "ok",
            "data": {
                "summary": {
                    "title": "查快递结果" if args.status == "快递中" else "查物品结果",
                    "subtitle": "在途快递追踪" if args.status == "快递中" else "居家管家查询结果",
                    "chips": [f"共 {len(items)} 件"] + ([f"名称: {args.name}"] if args.name else []),
                },
                "items": items,
            },
            "message": "查快递结果已生成" if args.status == "快递中" else "查物品结果已生成",
        }
        return emit(payload, template_name, args.output)

    elif args.command == "list":
        from render import emit
        from home_manager.inventory_ops import _stats_summary_payload
        conn = get_conn()
        try:
            stats_payload = _stats_summary_payload(conn)
        finally:
            conn.close()
        items = list_items_payload(
            location=args.location, status=args.status, category_id=args.category_id,
            owner=args.owner, sort_by=args.sort, limit=args.limit
        )
        payload = {
            "status": "ok",
            "data": {
                "summary": stats_payload["summary"],
                "items": items,
                "statuses": stats_payload["statuses"],
                "categories": stats_payload["categories"],
            },
            "message": "统物品结果已生成",
        }
        return emit(payload, "list_overview.html", args.output)

    elif args.command == "detail":
        from render import emit
        item = item_detail_payload(item_id=args.id)
        if not item:
            return emit({
                "status": "error",
                "data": {"item": {}},
                "message": f"未找到 ID={args.id} 的物品",
            }, "item_detail.html", args.output)
        payload = {
            "status": "ok",
            "data": {"item": item},
            "message": "物品详情已生成",
        }
        return emit(payload, "item_detail.html", args.output)

    elif args.command == "update":
        return update_item(
            item_id=args.id, name=args.name, category_id=args.category_id, owner=args.owner,
            remark=args.remark, tags=args.tags,
            purchase_price=args.price, purchase_date=args.purchase_date,
            expiration_date=args.expiration_date, photo=args.photo,
            new_location=args.new_location, quantity=args.quantity,
            minus=args.minus, plus=args.plus,
            location=args.location, location_status=args.location_status,
            add_location=args.add_location, add_quantity=args.add_quantity,
            add_reason=args.add_reason, add_location_status=args.add_location_status,
            add_purchase_date=args.add_purchase_date,
            add_expiration_date=args.add_expiration_date,
            add_tags=args.add_tag,
            remove_tags=args.remove_tag
        )

    elif args.command == "list":
        if args.json:
            return list_items_json(
                location=args.location, status=args.status, category_id=args.category_id,
                owner=args.owner, sort_by=args.sort, limit=args.limit
            )
        return list_items(
            location=args.location, status=args.status, category_id=args.category_id,
            owner=args.owner, sort_by=args.sort, limit=args.limit
        )

    elif args.command == "inventory":
        if args.output:
            from render import emit
            from home_manager.inventory_ops import inventory_payload
            conn = get_conn()
            try:
                payload_data = inventory_payload(conn, args.location)
            finally:
                conn.close()
            payload = {
                "status": "ok",
                "data": payload_data,
                "message": "盘点 HTML 已生成",
            }
            return emit(payload, "inventory_check.html", args.output)
        return inventory(location=args.location)

    elif args.command == "suggest-locations":
        conn = get_conn()
        try:
            if args.with_examples:
                results = suggest_locations_with_examples(
                    conn, args.category_id, limit=args.limit
                )
                print(f"📍 位置推荐（category_id={args.category_id}）：共 {len(results)} 个位置")
                print("-" * 70)
                for i, (loc, cnt, examples) in enumerate(results, 1):
                    ex_str = "、".join(examples) if examples else "(无)"
                    print(f"  {i}. {loc}  [{cnt}件同类]")
                    print(f"     └ 代表：{ex_str}")
                print(f"  {len(results)+1}. 其他位置（用户输入新位置）")
            else:
                results = suggest_locations(
                    conn, args.category_id, limit=args.limit
                )
                print(f"📍 位置推荐（category_id={args.category_id}）：共 {len(results)} 个位置")
                print("-" * 70)
                for i, (loc, cnt) in enumerate(results, 1):
                    print(f"  {i}. {loc}  [{cnt}件同类]")
                print(f"  {len(results)+1}. 其他位置（用户输入新位置）")
        finally:
            conn.close()
        return 0

    elif args.command == "find-location":
        conn = get_conn()
        try:
            results = find_location_by_reference(
                conn, args.reference, limit=args.limit
            )
        finally:
            conn.close()
        if not results:
            print(f"✗ 没找到参考物品 '{args.reference}'，换个名字试试")
            return 1
        print(f"🔍 参考「{args.reference}」找到 {len(results)} 件候选：")
        print("-" * 70)
        for i, it in enumerate(results, 1):
            print(f"  {i}. {it['item_name']}  [ID:{it['item_id']}]  分类:{it['category']}")
            if it['locations']:
                for loc in it['locations']:
                    print(f"     └ 📍 {loc['location']} ×{loc['quantity']}[{loc['location_status']}]")
            else:
                print(f"     └ (暂无位置记录)")
        return 0

    elif args.command == "stats":
        if args.output and args.type in ("expiring", "overview", "idle", "inventory-stat"):
            from render import emit
            if args.type == "expiring":
                from stats.expiring import expiring_payload
                conn = get_conn()
                try:
                    payload_data = expiring_payload(
                        conn, limit=args.limit, days=args.days or 30,
                        expired_only=args.expired_only, category_id=args.category_id
                    )
                finally:
                    conn.close()
                template_name, msg = "stats/expiring.html", "过期预警 HTML 已生成"
            elif args.type == "overview":
                from stats.overview import overview_payload
                conn = get_conn()
                try:
                    payload_data = overview_payload(conn)
                finally:
                    conn.close()
                template_name, msg = "stats/overview.html", "物品总览 HTML 已生成"
            elif args.type == "idle":
                from stats.idle import idle_payload
                conn = get_conn()
                try:
                    payload_data = idle_payload(
                        conn, days=args.days or 90,
                        category_id=args.category_id
                    )
                finally:
                    conn.close()
                template_name, msg = "stats/idle.html", "闲置检测 HTML 已生成"
            else:  # inventory-stat
                from stats.inventory_stat import inventory_stat_payload
                conn = get_conn()
                try:
                    payload_data = inventory_stat_payload(conn)
                finally:
                    conn.close()
                template_name, msg = "stats/inventory_stat.html", "盘点统计 HTML 已生成"
            payload = {
                "status": "ok",
                "data": payload_data,
                "message": msg,
            }
            return emit(payload, template_name, args.output)
        return stats(stat_type=args.type, limit=args.limit, days=args.days,
                     expired_only=args.expired_only, category_id=args.category_id)

    elif args.command == "outfit":
        from render import emit
        from home_manager.inventory_ops import _outfit_payload
        conn = get_conn()
        try:
            payload_data = _outfit_payload(conn, status_filter=args.status)
        finally:
            conn.close()
        payload = {
            "status": "ok",
            "data": payload_data,
            "message": "穿搭选择器 HTML 已生成",
        }
        return emit(payload, "outfit_picker.html", args.output)

    elif args.command == "trip":
        from render import emit
        from home_manager.inventory_ops import _trip_payload
        conn = get_conn()
        try:
            payload_data = _trip_payload(conn, mode=args.mode)
        finally:
            conn.close()
        payload = {
            "status": "ok",
            "data": payload_data,
            "message": "旅行清单 HTML 已生成",
        }
        return emit(payload, "travel_trip.html", args.output)

    elif args.command == "help":
        # P1-9c: HELP 中心 - 读 scenarios.yaml 渲染 help_center.html
        from render import emit
        from help_center import build_help_payload
        payload = build_help_payload()
        return emit(payload, "help_center.html", args.output,
                     message="HELP 中心已生成(总纲 07 §)")

    elif args.command == "tag-merge":
        return tag_merge(from_tag=args.from_tag, to_tag=args.to_tag)

    elif args.command == "tag-list":
        return list_tags()

    elif args.command == "account":
        action = args.action

        if action == "init":
            if not args.master_key:
                print("错误：--master-key 是必填的")
                return 1
            # P0-4 补丁:首次 init 走 _write_master_key;若已存在则必须用 set-master
            if is_master_key_set():
                print("✗ master key 已存在;改用 --action set-master 走密钥变更流程")
                return 1
            result = _write_master_key(args.master_key)
            print("✓ " + result["message"])

        elif action == "add":
            if not args.master_key:
                print("错误：--master-key 是必填的")
                return 1
            if not args.platform:
                print("错误：--platform 是必填的")
                return 1
            if not args.password:
                print("错误：--pass 是必填的")
                return 1
            result = account_add(
                platform=args.platform,
                username=args.user or "",
                password=args.password,
                master_key=args.master_key,
                tags=args.tags or "",
                note=args.note or ""
            )
            if result["success"]:
                print("✓ " + result["message"])
            else:
                print("✗ " + result["message"])

        elif action == "list":
            accounts = account_list()
            if not accounts:
                print("(无账号记录)")
                return 0
            print(f"=== 共 {len(accounts)} 个账号 ===")
            for acc in accounts:
                tags = acc.get('tags', '') or ''
                note = acc.get('note', '') or ''
                print(f"{acc['platform']} | {acc['username']} | **** | {tags} | {note}")

        elif action == "show":
            if not args.master_key:
                print("错误：--master-key 是必填的")
                return 1
            if not args.platform:
                print("错误：--platform 是必填的")
                return 1
            result = account_show(args.platform, args.master_key)
            if result["success"]:
                print(f"平台: {result['platform']}")
                print(f"账号: {result['username']}")
                print(f"密码: {result['password']}")
                if result.get('tags'): print(f"标签: {result['tags']}")
                if result.get('note'): print(f"备注: {result['note']}")
            else:
                print("✗ " + result["message"])

        elif action == "del":
            if not args.platform:
                print("错误：--platform 是必填的")
                return 1
            if not args.master_key:
                print("错误：--master-key 是必填的(防误删)")
                return 1
            result = account_del(args.platform, args.master_key)
            if result["success"]:
                print("✓ " + result["message"])
            else:
                print("✗ " + result["message"])

        elif action == "set-master":
            if not args.master_key:
                print("错误：--master-key（旧密钥）是必填的")
                return 1
            if not args.new_master_key:
                print("错误：--new-master-key 是必填的")
                return 1
            result = account_set_master(args.master_key, args.new_master_key)
            if result["success"]:
                print("✓ " + result["message"])
            else:
                print("✗ " + result["message"])

        return 0

    elif args.command == "family":
        import json
        from 家庭协作 import family_ops
        action = args.action

        if action == "member-add":
            conn = get_conn()
            try:
                m = family_ops.member_add(conn, args.name,
                                          relation=args.relation or "",
                                          note=args.note or "")
            except ValueError as e:
                print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
                return 1
            finally:
                conn.close()
            print(json.dumps({"status": "ok", "data": m,
                              "message": f"已添加成员「{m['name']}」"}, ensure_ascii=False))
            return 0

        elif action == "member-remove":
            conn = get_conn()
            try:
                result = family_ops.member_remove(conn, args.name)
            except ValueError as e:
                print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
                return 1
            finally:
                conn.close()
            print(json.dumps({"status": "ok", "data": result,
                              "message": f"已移除成员「{result['removed']}」，"
                                         f"{result['reassigned']} 件物品归属回「使用者」"},
                             ensure_ascii=False))
            return 0

        elif action == "member-assign":
            ids = [int(x) for x in (args.item_ids or "").split(",") if x.strip()]
            conn = get_conn()
            try:
                n = family_ops.member_assign(conn, args.name, ids)
            except ValueError as e:
                print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
                return 1
            finally:
                conn.close()
            print(json.dumps({"status": "ok", "data": {"assigned": n, "member": args.name},
                              "message": f"已标记 {n} 件物品归属「{args.name}」"}, ensure_ascii=False))
            return 0

        elif action == "member-list":
            conn = get_conn()
            try:
                payload = family_ops.member_list_payload(conn)
            finally:
                conn.close()
            if args.output:
                from render import emit
                return emit(payload, "family_members.html", args.output,
                            message="家人档案 HTML 已生成")
            print(json.dumps(payload, ensure_ascii=False))
            return 0

        elif action == "borrow-add":
            conn = get_conn()
            try:
                r = family_ops.borrow_add(
                    conn, direction=args.direction, object_name=args.object,
                    item_name=args.item_name or "", item_id=args.item_id,
                    borrowed_at=args.borrowed_at, due_date=args.due_date,
                    remark=args.remark or "",
                )
            except ValueError as e:
                print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
                return 1
            finally:
                conn.close()
            print(json.dumps({"status": "ok", "data": r,
                              "message": f"已登记{args.direction}：{r['item_name']} → {r['object_name']}"},
                             ensure_ascii=False))
            return 0

        elif action == "borrow-return":
            conn = get_conn()
            try:
                r = family_ops.borrow_return(conn, args.borrow_id)
            except ValueError as e:
                print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
                return 1
            finally:
                conn.close()
            print(json.dumps({"status": "ok", "data": r,
                              "message": f"已确认归还：{r['item_name']}（{r['object_name']}）"},
                             ensure_ascii=False))
            return 0

        elif action == "borrow-remind":
            conn = get_conn()
            try:
                cursor = conn.execute("SELECT * FROM borrow_records WHERE id = ?",
                                      (args.borrow_id,))
                row = cursor.fetchone()
                if not row:
                    raise ValueError(f"借用记录 {args.borrow_id} 不存在")
                text = family_ops.remind_text(dict(row))
            except ValueError as e:
                print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
                return 1
            finally:
                conn.close()
            print(json.dumps({"status": "ok", "data": {"text": text},
                              "message": "催还文案（复制纯文本发送）"}, ensure_ascii=False))
            return 0

        elif action == "borrow-list":
            conn = get_conn()
            try:
                payload = family_ops.borrow_list_payload(conn)
            finally:
                conn.close()
            if args.output:
                from render import emit
                return emit(payload, "family_borrow.html", args.output,
                            message="借用管理 HTML 已生成")
            print(json.dumps(payload, ensure_ascii=False))
            return 0

    elif args.command and args.command.startswith("sm1-"):
        # SM1 物品管理域(T2 公共层奠基 · 分发到 物品.cli)
        return sm1_run(args)

    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
