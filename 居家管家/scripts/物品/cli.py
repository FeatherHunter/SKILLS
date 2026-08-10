# cli.py - SM1 域 CLI 子命令注册与分发(T2 公共层奠基 · CLI 注册)
# home_manager.py 只做 3 处加法接线: import / register / dispatch
import json
import sys


def register(subparsers):
    """注册 SM1 子命令(全部以 sm1- 前缀,与旧命令并存)"""
    p = subparsers.add_parser("sm1-add", help="录入物品(规格口径:名称+分类必填,位置可选)")
    p.add_argument("--json-file", default=None, help="draft JSON 文件")
    p.add_argument("--name", default=None)
    p.add_argument("--category-id", type=int, default=None)
    p.add_argument("--location", default=None)
    p.add_argument("--quantity", type=int, default=None)
    p.add_argument("--price", type=float, default=None)
    p.add_argument("--purchase-date", default=None)
    p.add_argument("--expiration-date", default=None)
    p.add_argument("--backfill-date", default=None, help="补录日期(1-4)")
    p.add_argument("--remark", default=None)
    p.add_argument("--tags", default=None)
    p.add_argument("--photo", default=None)
    p.add_argument("--location-status", default=None)
    p.add_argument("--preview", action="store_true", help="生成采集表单 HTML 待确认")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-add-batch", help="批量录入(1-3)")
    p.add_argument("--json-file", required=True, help="drafts JSON 文件(list)")
    p.add_argument("--commit", action="store_true", help="确认写库(否则只出预览)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-search", help="查物品(2-1)/拍照找物品(2-5)")
    p.add_argument("--name", default=None)
    p.add_argument("--category-id", type=int, default=None)
    p.add_argument("--location", default=None)
    p.add_argument("--tag", default=None)
    p.add_argument("--status", default=None)
    p.add_argument("--price-min", type=float, default=None)
    p.add_argument("--price-max", type=float, default=None)
    p.add_argument("--include-discarded", action="store_true")
    p.add_argument("--sort", default="relevance")
    p.add_argument("--keywords", default=None, help="AI 解析的匹配关键词,逗号分隔")
    p.add_argument("--scene", default="2-1", choices=["2-1", "2-5"], help="2-1=查物品 / 2-5=拍照找物品")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-detail", help="看物品详情(2-2)")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-locate", help="紧急定位(2-3)")
    p.add_argument("--name", required=True)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-browse", help="筛选浏览(2-4)")
    p.add_argument("--group-by", default="category", choices=["category", "location", "status", "tags"])
    p.add_argument("--category-id", type=int, default=None)
    p.add_argument("--location", default=None)
    p.add_argument("--tag", default=None)
    p.add_argument("--price-min", type=float, default=None)
    p.add_argument("--price-max", type=float, default=None)
    p.add_argument("--sort", default="name", choices=["name", "recent", "price"])
    p.add_argument("--include-discarded", action="store_true")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-duplicates", help="查重复(2-6)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-update", help="改物品(3-1)")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--name", default=None)
    p.add_argument("--category-id", type=int, default=None)
    p.add_argument("--owner", default=None)
    p.add_argument("--remark", default=None)
    p.add_argument("--price", type=float, default=None)
    p.add_argument("--purchase-date", default=None)
    p.add_argument("--expiration-date", default=None)
    p.add_argument("--json-file", default=None, help="fields JSON(优先)")
    p.add_argument("--preview", action="store_true", help="生成采集表单(update 模式)待确认")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-move", help="移物品(3-2,支持批量)")
    p.add_argument("--id", type=int, default=None)
    p.add_argument("--ids", default=None, help="逗号分隔批量")
    p.add_argument("--location", required=True)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-qty", help="数量变更(3-3)")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--plus", type=int, default=None)
    p.add_argument("--minus", type=int, default=None)
    p.add_argument("--set", type=int, default=None)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-status", help="状态变更(3-4)")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--status", required=True)
    p.add_argument("--location", default=None)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-merge-preview", help="合并预览(3-5)")
    p.add_argument("--target", type=int, required=True)
    p.add_argument("--sources", required=True, help="逗号分隔")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-merge", help="合并物品(3-5)")
    p.add_argument("--target", type=int, required=True)
    p.add_argument("--sources", required=True)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-undo-list", help="可撤销列表(3-6)")
    p.add_argument("--item-id", type=int, default=None)
    p.add_argument("--limit", type=int, default=30)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-undo", help="撤销(3-6)")
    p.add_argument("--event-id", type=int, required=True)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-relate", help="设置/解除关联(3-7)")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--related", type=int, required=True)
    p.add_argument("--type", default="配件")
    p.add_argument("--action", default="link", choices=["link", "unlink"])
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-tag", help="标物品(3-8,支持批量)")
    p.add_argument("--id", type=int, default=None)
    p.add_argument("--ids", default=None)
    p.add_argument("--add", default=None, help="逗号分隔")
    p.add_argument("--remove", default=None, help="逗号分隔")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-use", help="标记使用(3-1 快捷/2-3)")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-tag-overview", help="标签总览(4-1)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-tag-purge", help="清理未使用标签(4-1)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-similar-tags", help="相近标签检测(4-3)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-category", help="分类管理(4-2)")
    p.add_argument("--action", default="overview", choices=["overview", "add", "rename", "merge"])
    p.add_argument("--id", type=int, default=None)
    p.add_argument("--to-id", type=int, default=None)
    p.add_argument("--name", default=None)
    p.add_argument("--parent-id", type=int, default=None)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-photos", help="查看物品照片(5-1)")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-photo-update", help="管照片落地(5-2)")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--json-file", required=True, help="photos JSON list [{file_path, photo_type}]")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-photo-wall", help="照片墙(5-3)")
    p.add_argument("--group-by", default="category", choices=["category", "location"])
    p.add_argument("--type", default=None, help="照片类型筛选")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-inventory-round", help="盘点核对清单(6-1)")
    p.add_argument("--scope", default="location", choices=["location", "category", "all"])
    p.add_argument("--value", default="")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-inventory-commit", help="盘点提交(6-1 完成)")
    p.add_argument("--json-file", required=True)
    p.add_argument("--scope", default="location", choices=["location", "category", "all"])
    p.add_argument("--value", default="")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-inventory-diff", help="差异处理视图(6-2)")
    p.add_argument("--record-id", type=int, default=None)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-inventory-resolve", help="差异处理落地(6-2)")
    p.add_argument("--record-id", type=int, required=True)
    p.add_argument("--json-file", required=True)
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-inventory-records", help="盘点记录(6-3)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-move-checklist", help="搬家打包清单(6-4)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-move-commit", help="搬家打包确认(6-4)")
    p.add_argument("--json-file", required=True, help='{"take": [ids], "leave": [ids]}')
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm1-history", help="物品历史(7-1)")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--output", default=None)


def _load_json_file(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def run(args):
    """SM1 命令分发(返回进程退出码)"""
    from 物品 import ops
    from render_物品 import emit_sm1, emit_error
    from render import emit

    def _receipt_scene(ok, msg, payload, scene_id, wake_word, command_cn,
                       buttons=None, reminders=None, output_path=None):
        if not ok:
            return emit_error(wake_word, command_cn, msg, payload or {},
                              suggest="修正参数后重试", output_path=args.output)
        receipt = {
            "summary": msg,
            "action": command_cn,
            "diff": payload.get("diff") or [],
            "extra": payload.get("extra"),
            "steps": payload.get("results") or payload.get("steps"),
            "next": payload.get("next"),
            "undo_prompt": payload.get("undo_prompt") or f"请加载「居家管家」技能,帮我撤销最近操作(唤醒词:撤销操作):\n\n  撤  销: 刚才的{command_cn}",
        }
        # 注意: 不再包内层 scene 键(信封 data.scene 即本数据;双重嵌套
        # scene.scene 会让 receipt.html 读不到 summary/diff,issue #127)
        data = {"receipt": receipt, "buttons": buttons or [], **payload}
        data.pop("diff", None)
        data.pop("extra", None)
        data.pop("results", None)
        data.pop("steps", None)
        data.pop("next", None)
        return emit_sm1("receipt.html", data, scene_id, wake_word, command_cn,
                        target=payload.get("item", {}).get("name") if payload.get("item") else command_cn,
                        copy_log={"call_chain": "居家管家技能内部指令(场景自动映射)", "data_structure": "写库 + 物品事件记录"},
                        reminders=reminders, output_path=args.output)

    cmd = args.command

    if cmd == "sm1-add":
        draft = _load_json_file(args.json_file) if args.json_file else {
            "name": args.name, "category_id": args.category_id, "location": args.location,
            "quantity": args.quantity, "price": args.price,
            "purchase_date": args.purchase_date, "expiration_date": args.expiration_date,
            "backfill_date": args.backfill_date, "remark": args.remark,
            "tags": args.tags, "photo": args.photo, "location_status": args.location_status,
        }
        if args.preview:
            return _add_form_render(draft, mode="backfill" if args.backfill_date else "add",
                                    output=args.output)
        ok, msg, item_id = ops.add_item_v2(
            draft, event_type="backfilled" if args.backfill_date else "created",
            cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            payload = ops.detail_payload_v2(item_id)
            payload["item"] = payload["item"]
            return _receipt_scene(True, msg, {"item": payload["item"]}, "1-1" if not args.backfill_date else "1-4",
                                  "录物品" if not args.backfill_date else "补录",
                                  "录物品" if not args.backfill_date else "补录",
                                  buttons=[{"label": "撤销", "kind": "red", "text": f"请加载「居家管家」技能,帮我撤销最近操作(唤醒词:撤销操作):\n\n  撤  销: 刚才的录入(物品 {item_id})"}],
                                  reminders=_entry_reminders(payload["item"]), output_path=args.output)
        return emit_error("录物品", "录物品", msg, {"draft": draft}, output_path=args.output)

    if cmd == "sm1-add-batch":
        drafts = _load_json_file(args.json_file)
        if not args.commit:
            data = ops.add_batch_payload(drafts)
            return _add_form_render_batch(data, output=args.output)
        result = ops.add_batch_commit(drafts, cli_cmd=" ".join(sys.argv[1:]))
        return _receipt_scene(result["ok"], result["message"],
                              {"results": result["results"], "next": "已写入;可查详情或历史"},
                              "1-3", "批量录入", "批量录入",
                              output_path=args.output)

    if cmd == "sm1-search":
        data = ops.search_payload_v2(
            name=args.name, category_id=args.category_id, location=args.location,
            tag=args.tag, status=args.status, price_min=args.price_min, price_max=args.price_max,
            include_discarded=args.include_discarded, sort=args.sort,
            match_keywords=[k.strip() for k in (args.keywords or "").split(",") if k.strip()])
        if args.scene == "2-5":
            data = ops.search_payload_v2(
                name=args.name, category_id=args.category_id, location=args.location,
                tag=args.tag, status=args.status, price_min=args.price_min, price_max=args.price_max,
                include_discarded=args.include_discarded, sort=args.sort,
                match_keywords=[k.strip() for k in (args.keywords or "").split(",") if k.strip()],
                match_score=True)
            return emit_sm1("search_list.html", data, "2-5", "拍照找物品", "拍照找物品",
                            target=args.name or "照片识别", output_path=args.output)
        return emit_sm1("search_list.html", data, "2-1", "查物品", "查物品",
                        target=args.name or "", output_path=args.output)

    if cmd == "sm1-detail":
        data = ops.detail_payload_v2(args.id)
        if not data:
            return emit_error("看物品", "看物品", f"未找到 ID={args.id} 的物品",
                              {"item_id": args.id}, output_path=args.output)
        return emit_sm1("detail.html", data, "2-2", "看物品", "看物品",
                        target=data["item"]["name"], output_path=args.output)

    if cmd == "sm1-locate":
        data = ops.locate_payload_v2(args.name)
        return emit_sm1("locate.html", data, "2-3", "紧急定位", "紧急定位",
                        target=args.name, output_path=args.output)

    if cmd == "sm1-browse":
        data = ops.browse_payload_v2(
            group_by=args.group_by, category_id=args.category_id, location=args.location,
            tag=args.tag, price_min=args.price_min, price_max=args.price_max,
            sort=args.sort, include_discarded=args.include_discarded)
        return emit_sm1("browse.html", data, "2-4", "筛选浏览", "筛选浏览",
                        target="", output_path=args.output)

    if cmd == "sm1-duplicates":
        data = ops.duplicates_payload_v2()
        return emit_sm1("duplicates.html", data, "2-6", "查重复", "查重复",
                        target="", output_path=args.output)

    if cmd == "sm1-update":
        fields = _load_json_file(args.json_file) if args.json_file else {
            k: getattr(args, k) for k in ("name", "category_id", "owner", "remark", "price",
                                          "purchase_date", "expiration_date")
            if getattr(args, k) is not None}
        if args.preview:
            conn = ops._conn()
            try:
                cur = ops._find_item(conn, args.id)
                loc = ops._loc_row(conn, args.id)
                tags = [r[0] for r in conn.execute(
                    "SELECT tag FROM item_tags WHERE item_id = ? ORDER BY rowid", (args.id,)).fetchall()]
            finally:
                conn.close()
            if not cur:
                return emit_error("改物品", "改物品", f"未找到 ID={args.id}", {"item_id": args.id})
            draft = {"name": cur["name"], "category_id": cur["category_id"],
                     "location": loc["location"] if loc else "",
                     "quantity": loc["quantity"] if loc else 1,
                     "price": cur["purchase_price"], "remark": cur["remark"],
                     "purchase_date": loc["purchase_date"] if loc else None,
                     "expiration_date": loc["expiration_date"] if loc else None,
                     "location_status": loc["location_status"] if loc else "",
                     "tags": tags}
            return _add_form_render(draft, mode="update", item_id=args.id, output=args.output)
        ok, msg, payload = ops.update_item_v2(args.id, fields, cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            payload["diff"] = [{"field": k, "before": v, "after": payload["after"][k]}
                               for k, v in payload["diff"].items()]
            return _receipt_scene(True, msg, payload, "3-1", "改物品", "改物品",
                                  output_path=args.output)
        return emit_error("改物品", "改物品", msg, {"item_id": args.id}, output_path=args.output)

    if cmd == "sm1-move":
        ids = [args.id] if args.id else [int(x) for x in (args.ids or "").split(",") if x.strip()]
        if not ids:
            return emit_error("移物品", "移物品", "缺少 --id 或 --ids", {})
        results = []
        first = None
        for iid in ids:
            ok, msg, payload = ops.move_item_v2(iid, args.location, cli_cmd=" ".join(sys.argv[1:]))
            results.append({"id": iid, "ok": ok, "message": msg})
            if ok and not first:
                first = payload
        ok_all = all(r["ok"] for r in results)
        msg = f"移动完成:{sum(1 for r in results if r['ok'])}/{len(ids)} 件到「{args.location}」"
        if ok_all:
            payload = {"results": results}
            if first:
                payload["item"] = first["item"]
            return _receipt_scene(True, msg, payload, "3-2", "移物品", "移物品",
                                  output_path=args.output)
        return emit_error("移物品", "移物品", msg, {"results": results}, output_path=args.output)

    if cmd == "sm1-qty":
        if args.plus:
            delta = args.plus
        elif args.minus:
            delta = -args.minus
        else:
            delta = 0
        ok, msg, payload = ops.change_quantity_v2(args.id, delta=delta, absolute=args.set,
                                                  cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            payload["diff"] = [{"field": "数量", "before": payload["before_qty"], "after": payload["after_qty"]}]
            reminders = [{"type": "warn", "text": payload.get("restock_tip")}] if payload.get("restock_tip") else None
            return _receipt_scene(True, msg, payload, "3-3", "数量变更", "数量变更",
                                  reminders=reminders, output_path=args.output)
        return emit_error("数量变更", "数量变更", msg, {"item_id": args.id}, output_path=args.output)

    if cmd == "sm1-status":
        ok, msg, payload = ops.change_status_v2(args.id, args.status, args.location,
                                                cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            payload["diff"] = [{"field": "状态", "before": payload["before_status"], "after": payload["after_status"]}]
            return _receipt_scene(True, msg, payload, "3-4", "状态变更", "状态变更",
                                  output_path=args.output)
        return emit_error("状态变更", "状态变更", msg, {"item_id": args.id, "status": args.status},
                          suggest=msg, output_path=args.output)

    if cmd == "sm1-merge-preview":
        sources = [int(x) for x in args.sources.split(",") if x.strip()]
        conn = ops._conn()
        try:
            target = ops._find_item(conn, args.target)
            src_list = [ops._find_item(conn, s) for s in sources]
            src_locs = {s: ops._loc_row(conn, s) for s in sources}
        finally:
            conn.close()
        if not target:
            return emit_error("合并物品", "合并物品", f"未找到主物品 ID={args.target}", {})
        entries = []
        for src in src_list:
            if not src:
                continue
            loc = src_locs.get(src["id"])
            entries.append({"name": src["name"], "sub": f"ID {src['id']}",
                            "rows": [["位置", loc["location"] if loc else ""],
                                     ["数量", loc["quantity"] if loc else 1],
                                     ["状态", loc["location_status"] if loc else "在家"]]})
        data = {"title": "合并重复物品预览", "lead": "保留主条 + 字段合并规则 + 数量相加 + 历史合并说明",
                "impact": f"主条:ID {args.target};源 {len(entries)} 件将并入并标记「已废弃」(历史可查)",
                "entries": entries,
                "buttons": [{"label": "确认合并", "text": f"请加载「居家管家」技能,帮我合并重复物品(唤醒词:合并物品):\n\n  保  留: {args.target}\n  并  入: {args.sources}"}],
                "before": {"主条": target["name"], "源数量": sum(1 for s in src_list if s)}}
        return emit_sm1("confirm.html", data, "3-5", "合并物品", "合并物品",
                        target=target["name"], output_path=args.output)

    if cmd == "sm1-merge":
        sources = [int(x) for x in args.sources.split(",") if x.strip()]
        ok, msg, payload = ops.merge_items_v2(args.target, sources, cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            return _receipt_scene(True, msg, {"results": payload["results"], "item": payload["target"],
                                              "undo_prompt": f"请加载「居家管家」技能,帮我撤销最近操作(唤醒词:撤销操作):\n\n  撤  销: 刚才的合并(目标 {args.target})"},
                                  "3-5", "合并物品", "合并物品", output_path=args.output)
        return emit_error("合并物品", "合并物品", msg, {"target": args.target, "sources": sources},
                          output_path=args.output)

    if cmd == "sm1-undo-list":
        conn = ops._conn()
        try:
            events = [dict(e) for e in conn.execute(
                "SELECT id, item_id, event_type, occurred_at, summary FROM item_events "
                "WHERE event_type != 'undone' AND id NOT IN (SELECT undo_of FROM item_events WHERE undo_of IS NOT NULL) "
                "AND item_id = COALESCE(?, item_id) ORDER BY id DESC LIMIT ?",
                (args.item_id, args.limit)).fetchall()]
        finally:
            conn.close()
        data = {"events": events}
        return emit_sm1("undo_select.html", data, "3-6", "撤销操作", "撤销操作",
                        target="", output_path=args.output)

    if cmd == "sm1-undo":
        ok, msg, payload = ops.undo_v2(args.event_id, cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            return _receipt_scene(True, msg, {"extra": f"已撤销事件 {args.event_id}", "next": "撤销一次性,不可再撤销"},
                                  "3-6", "撤销操作", "撤销操作", output_path=args.output)
        return emit_error("撤销操作", "撤销操作", msg, {"event_id": args.event_id}, output_path=args.output)

    if cmd == "sm1-relate":
        if args.action == "unlink":
            ok, msg, payload = ops.unrelate_items_v2(args.id, args.related, cli_cmd=" ".join(sys.argv[1:]))
        else:
            ok, msg, payload = ops.relate_items_v2(args.id, args.related, args.type,
                                                   cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            return _receipt_scene(True, msg, {"item": payload["item"],
                                              "extra": f"关联物品:{payload.get('related', {}).get('name', args.related)}"},
                                  "3-7", "物品关联", "物品关联", output_path=args.output)
        return emit_error("物品关联", "物品关联", msg, {"item_id": args.id, "related": args.related},
                          output_path=args.output)

    if cmd == "sm1-tag":
        ids = [args.id] if args.id else [int(x) for x in (args.ids or "").split(",") if x.strip()]
        results = []
        for iid in ids:
            ok, msg, payload = ops.tag_item_v2(
                iid, add_tags=[t.strip() for t in (args.add or "").split(",") if t.strip()],
                remove_tags=[t.strip() for t in (args.remove or "").split(",") if t.strip()],
                cli_cmd=" ".join(sys.argv[1:]))
            results.append({"id": iid, "ok": ok, "message": msg})
            if ok and "item" not in locals() and payload:
                last_item = payload["item"]
        ok_all = all(r["ok"] for r in results)
        msg = f"标签操作完成:{sum(1 for r in results if r['ok'])}/{len(ids)} 件"
        if ok_all:
            payload = {"results": results}
            if "last_item" in locals():
                payload["item"] = last_item
            return _receipt_scene(True, msg, payload, "3-8", "标物品", "标物品",
                                  output_path=args.output)
        return emit_error("标物品", "标物品", msg, {"results": results}, output_path=args.output)

    if cmd == "sm1-use":
        ok, msg, payload = ops.use_item_v2(args.id, cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            return _receipt_scene(True, msg, {"item": payload["item"]}, "2-3", "标记使用", "标记使用",
                                  output_path=args.output)
        return emit_error("标记使用", "标记使用", msg, {"item_id": args.id}, output_path=args.output)

    if cmd == "sm1-tag-overview":
        data = ops.tag_overview_payload()
        return emit_sm1("tag_manage.html", data, "4-1", "管标签", "管标签",
                        target="", output_path=args.output)

    if cmd == "sm1-tag-purge":
        result = ops.tag_purge()
        return _receipt_scene(True, f"已清理 {result['count']} 个未使用标签",
                              {"extra": {"已清理": result["removed"]}},
                              "4-1", "管标签", "清理未使用标签", output_path=args.output)

    if cmd == "sm1-similar-tags":
        data = ops.similar_tags_payload()
        data["mode"] = "suggest"
        return emit_sm1("tag_manage.html", data, "4-3", "整理建议", "整理建议",
                        target="", output_path=args.output)

    if cmd == "sm1-category":
        if args.action == "overview":
            data = ops.category_overview_payload()
            return emit_sm1("category_manage.html", data, "4-2", "管分类", "管分类",
                            target="", output_path=args.output)
        if args.action == "add":
            ok, msg, payload = ops.category_add_v2(args.name, args.parent_id)
        elif args.action == "rename":
            ok, msg, payload = ops.category_rename_v2(args.id, args.name)
        else:
            ok, msg, payload = ops.category_merge_v2(args.id, args.to_id)
        if ok:
            return _receipt_scene(True, msg, {"extra": payload}, "4-2", "管分类", "管分类",
                                  output_path=args.output)
        return emit_error("管分类", "管分类", msg, {"action": args.action}, output_path=args.output)

    if cmd == "sm1-photos":
        data = ops.photos_payload(args.id)
        if not data:
            return emit_error("查看照片", "查看照片", f"未找到 ID={args.id}", {"item_id": args.id})
        return emit_sm1("photos.html", data, "5-1", "查看照片", "查看照片",
                        target=data["item"]["name"], output_path=args.output)

    if cmd == "sm1-photo-update":
        photos = _load_json_file(args.json_file)
        ok, msg, payload = ops.photo_update_v2(args.id, photos, cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            return _receipt_scene(True, msg, {"item": payload["item"],
                                              "extra": {"新照片顺序": [p["file_path"] for p in payload["photos"]],
                                                        "主图": payload["main"]["file_path"] if payload["main"] else None}},
                                  "5-2", "管照片", "管照片", output_path=args.output)
        return emit_error("管照片", "管照片", msg, {"item_id": args.id}, output_path=args.output)

    if cmd == "sm1-photo-wall":
        data = ops.photo_wall_payload(group_by=args.group_by, photo_type=args.type)
        return emit_sm1("photo_wall.html", data, "5-3", "照片墙", "照片墙",
                        target="", output_path=args.output)

    if cmd == "sm1-inventory-round":
        data = ops.inventory_round_payload(args.scope, args.value)
        return emit_sm1("inventory_round.html", data, "6-1", "盘点", "盘点",
                        target=args.value or "全屋", output_path=args.output)

    if cmd == "sm1-inventory-commit":
        results = _load_json_file(args.json_file)
        scope = f"{args.scope}:{args.value}" if hasattr(args, "scope") else "all"
        ok, msg, payload = ops.inventory_commit_v2(scope, results, cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            return _receipt_scene(True, msg, {"extra": {"盘点记录": f"#{payload['record_id']}",
                                                        "缺": payload["missing"], "多": payload["extra"],
                                                        "异": payload["diff"], "待确认": payload["pending"]},
                                              "next": "差异可继续「差异处理」逐一落地"},
                                  "6-1", "盘点", "盘点", output_path=args.output)
        return emit_error("盘点", "盘点", msg, {}, output_path=args.output)

    if cmd == "sm1-inventory-diff":
        data = ops.inventory_diff_payload(args.record_id)
        if not data:
            return emit_error("差异处理", "差异处理", "没有可处理的盘点记录",
                              {"record_id": args.record_id})
        return emit_sm1("inventory_diff.html", data, "6-2", "差异处理", "差异处理",
                        target=f"记录#{data['record']['id']}", output_path=args.output)

    if cmd == "sm1-inventory-resolve":
        actions = _load_json_file(args.json_file)
        ok, msg, payload = ops.resolve_diff_v2(args.record_id, actions, cli_cmd=" ".join(sys.argv[1:]))
        if ok:
            return _receipt_scene(True, msg, {"steps": payload["results"],
                                              "next": f"{len(payload['extra_drafts'])} 件清单外物品生成采集表单待预览" if payload["extra_drafts"] else None},
                                  "6-2", "差异处理", "差异处理", output_path=args.output)
        return emit_error("差异处理", "差异处理", msg, {"record_id": args.record_id}, output_path=args.output)

    if cmd == "sm1-inventory-records":
        data = ops.inventory_records_payload()
        return emit_sm1("inventory_records.html", data, "6-3", "盘点记录", "盘点记录",
                        target="", output_path=args.output)

    if cmd == "sm1-move-checklist":
        data = ops.move_checklist_payload()
        return emit_sm1("move_checklist.html", data, "6-4", "搬家盘点", "搬家盘点",
                        target="", output_path=args.output)

    if cmd == "sm1-move-commit":
        plan = _load_json_file(args.json_file)
        take_ids = plan.get("take") or []
        leave_ids = plan.get("leave") or []
        return _receipt_scene(True,
                              f"搬家清单已生成:带走 {len(take_ids)} / 不带走 {len(leave_ids)}",
                              {"extra": {"带走": take_ids, "不带走": leave_ids},
                               "next": "搬家后用「移物品」(批量)把带走清单落地到新位置;不带走走废弃/送人"},
                              "6-4", "搬家盘点", "搬家盘点", output_path=args.output)

    if cmd == "sm1-history":
        data = ops.history_payload(args.id)
        if not data:
            return emit_error("历史", "历史", f"未找到 ID={args.id}", {"item_id": args.id})
        return emit_sm1("history.html", data, "7-1", "历史", "历史",
                        target=data["item"]["name"], output_path=args.output)

    return 1


def _add_form_render(draft, mode="add", item_id=None, output=None):
    """渲染采集表单(1-1/1-4/3-1 update)"""
    from render_物品 import emit_sm1
    from 物品 import ops
    conn = ops._conn()
    try:
        categories = [{"id": r["id"], "name": r["name"]} for r in conn.execute(
            "SELECT id, name FROM categories WHERE is_active = 1 ORDER BY sort_order, id").fetchall()]
        locations = [r["location"] for r in conn.execute(
            "SELECT DISTINCT location FROM item_locations WHERE location IS NOT NULL ORDER BY location").fetchall()]
        similar = ops.similar_items_check(draft.get("name"), draft.get("category_id"))
        checks, missing = validate_draft_for_render(draft, conn)
    finally:
        conn.close()
    item = {"seq": 1, "draft": draft, "checks": checks, "missing": missing,
            "similar": similar, "batch_dup": None, "low_confidence": draft.get("low_confidence") or []}
    data = {"mode": mode, "total": 1, "items": [item], "categories": categories,
            "locations": locations, "item_id": item_id,
            "statuses": STATUSES_FOR_FORM}
    wake, scene_id, cmd_cn = {
        "add": ("录物品", "1-1", "录物品"),
        "backfill": ("补录", "1-4", "补录"),
        "update": ("改物品", "3-1", "改物品"),
        "photo_scan": ("拍物品", "1-2", "拍物品"),
    }[mode]
    return emit_sm1("add_form.html", data, scene_id, wake, cmd_cn,
                    target=draft.get("name") or cmd_cn, output_path=output)


def _add_form_render_batch(data, output=None):
    """渲染批量采集(1-3)"""
    from render_物品 import emit_sm1
    return emit_sm1("add_form.html", data, "1-3", "批量录入", "批量录入",
                    target=f"{data['total']} 件", output_path=output)


def _entry_reminders(item):
    """录入回执顺路提醒: 到期日 + 联动建议(2026-08-10: 无条件,删偏好后)"""
    reminders = []
    if item.get("expiration_date"):
        reminders.append({"type": "warn", "text": f"到期日:{item['expiration_date']}"})
    # SM9 联动顺路建议(食品→卡路里 / 有价→记账);remindersBlock 支持 type=link 渲染
    try:
        from 联动.ops import build_entry_reminders
        for r in build_entry_reminders(item):
            text = f"【联动】{r['label']}: {r['reason']} —— {r['prompt']}"
            reminders.append({"type": "link", "text": text})
    except Exception:
        pass  # 联动域异常不阻断录入回执
    return reminders


STATUSES_FOR_FORM = ["在家", "备用", "快递中", "维修中", "找不到", "待处理"]


def validate_draft_for_render(draft, conn=None):
    from 物品.validators import validate_draft
    return validate_draft(draft, conn)

