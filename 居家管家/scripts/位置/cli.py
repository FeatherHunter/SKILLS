# 位置/cli.py - SM2 域 CLI 子命令注册与分发(T3 · 公共层 3 处接线)
# home_manager.py 只做 3 处加法接线: import / register / dispatch
import json
import sys


def register(subparsers):
    """注册 SM2 子命令(全部以 sm2- 前缀)"""
    p = subparsers.add_parser("sm2-view", help="空间视图浏览(位置树下钻 · SM2-4)")
    p.add_argument("--path", default=None, help="从哪层开始(空 = 顶层)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm2-manage", help="位置管理(查看/新建/改名/合并/删除 · SM2-1)")
    p.add_argument("--action", default="view",
                   choices=["view", "similar", "selectors",
                            "create", "rename-preview", "rename",
                            "merge-preview", "merge", "delete-preview", "delete"])
    p.add_argument("--path", default=None, help="create/delete 的目标路径")
    p.add_argument("--old", default=None, help="rename/merge 源路径")
    p.add_argument("--new", default=None, help="rename/merge 目标路径")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm2-fixed", help="固定位(设置/解除/清单 · SM2-2)")
    p.add_argument("--action", default="list", choices=["list", "set", "clear"])
    p.add_argument("--item-id", type=int, default=None)
    p.add_argument("--location", default=None, help="固定位路径(set 用)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm2-suggest", help="收纳位置建议(AI 推荐 · SM2-3)")
    p.add_argument("--item-id", type=int, default=None, help="单件建议(优先)")
    p.add_argument("--item-ids", default=None, help="指定多件(逗号分隔,prompt「可多件」落地)")
    p.add_argument("--batch", action="store_true", help="批量:没有固定位的常用件")
    p.add_argument("--limit", type=int, default=50, help="批量上限")
    p.add_argument("--output", default=None)


def _emit(template, data, scene_id, wake_word, command_cn, target=None,
          copy_log=None, reminders=None, output_path=None):
    from render_位置 import emit_sm2
    return emit_sm2(template, data, scene_id, wake_word, command_cn,
                    target=target, copy_log=copy_log, reminders=reminders,
                    output_path=output_path)


def _emit_err(wake_word, command_cn, reason, key_data=None, suggest=None,
              output_path=None):
    from render_位置 import emit_error
    return emit_error(wake_word, command_cn, reason, key_data or {},
                      suggest=suggest, output_path=output_path)


def _receipt_scene(ok, msg, payload, scene_id, wake_word, command_cn,
                   buttons=None, reminders=None, output_path=None):
    """回执统一封装(08 §4 结果阶段: 确认/撤销/复制数据/复制日志)"""
    if not ok:
        return _emit_err(wake_word, command_cn, msg, payload or {},
                         suggest="修正参数后重试", output_path=output_path)
    receipt = {
        "summary": msg,
        "action": command_cn,
        "diff": payload.get("diff") or [],
        "extra": payload.get("extra"),
        "steps": payload.get("steps"),
        "next": payload.get("next"),
    }
    # 注意: 不再包内层 scene 键(信封 data.scene 即本数据;双重嵌套会让模板读不到)
    data = {"receipt": receipt, "buttons": buttons or [], **payload}
    for k in ("diff", "extra", "steps", "next"):
        data.pop(k, None)
    return _emit("receipt.html", data, scene_id, wake_word, command_cn,
                 target=payload.get("target") or command_cn,
                 output_path=output_path)


def run(args):
    """SM2 命令分发(返回进程退出码)"""
    from 位置 import ops, scenes, tree
    from home_manager.db import get_conn

    cmd = args.command

    # ── SM2-4 空间视图 ──
    if cmd == "sm2-view":
        conn = get_conn()
        try:
            data = tree.build_tree(conn, current_path=args.path)
        finally:
            conn.close()
        data["start_hint"] = not data["current_path"]
        return _emit("space_view.html", data, scenes.scene_id("sm2-view"), "空间视图", "空间视图",
                     target=data["current_path"] or "(全屋)", output_path=args.output)

    # ── SM2-1 位置管理 ──
    if cmd == "sm2-manage":
        conn = ops._conn()
        try:
            if args.action in ("view", "similar"):
                data = ops.manage_payload(conn)
                if args.action == "similar":
                    data["focus_similar"] = True
                return _emit("location_manage.html", data, scenes.scene_id("sm2-manage"), "管位置", "管位置",
                             target="", output_path=args.output)

            if args.action == "selectors":
                print(json.dumps({"status": "ok",
                                  "data": {"locations": ops.all_locations_for_selector(conn)}},
                                 ensure_ascii=False))
                return 0

            if args.action == "create":
                ok, msg, payload = ops.create_node(conn, args.path, cli_cmd=" ".join(sys.argv[1:]))
                return _receipt_scene(ok, msg, {"target": payload}, scenes.scene_id("sm2-manage"),
                                      "管位置", "新建位置",
                                      buttons=[{"label": "去放物品", "text": f"移物品(居家管家): 把物品移到「{payload}」"}],
                                      output_path=args.output)

            if args.action in ("rename-preview", "rename"):
                preview = ops.rename_preview(conn, args.old, args.new)
                if not preview:
                    return _emit_err("管位置", "位置改名", "位置路径无效(段不能为空)",
                                     {"old": args.old, "new": args.new}, output_path=args.output)
                if args.action == "rename-preview":
                    preview["mode"] = "rename"
                    return _emit("confirm.html", preview, scenes.scene_id("sm2-manage"), "管位置", "位置改名",
                                 target=preview["old"], output_path=args.output)
                ok, msg, payload = ops.rename_node(conn, args.old, args.new,
                                                   cli_cmd=" ".join(sys.argv[1:]))
                if not ok or payload is None:
                    return _emit_err("管位置", "位置改名", msg or "位置改名失败",
                                     {"old": args.old, "new": args.new},
                                     suggest="目标已是独立位置时,请改用「合并」;修正路径后重试",
                                     output_path=args.output)
                payload["target"] = f"{preview['old']} → {preview['new']}"
                payload["diff"] = [{"field": "位置路径", "before": preview["old"], "after": preview["new"]}]
                payload["extra"] = {"涉及物品": preview["items_affected"]}
                return _receipt_scene(ok, msg, payload, scenes.scene_id("sm2-manage"), "管位置", "位置改名",
                                      buttons=[{"label": "撤销改名", "text": f"管位置(居家管家): 改名回退,把「{preview['new']}」改回「{preview['old']}」"}],
                                      output_path=args.output)

            if args.action in ("merge-preview", "merge"):
                old, new = args.old, args.new
                if args.action == "merge-preview":
                    preview = ops.rename_preview(conn, old, new)
                    if not preview:
                        return _emit_err("管位置", "位置合并", "位置路径无效",
                                         {"src": old, "tgt": new}, output_path=args.output)
                    preview["src"], preview["tgt"] = old, new
                    preview["mode"] = "merge"
                    return _emit("confirm.html", preview, scenes.scene_id("sm2-manage"), "管位置", "位置合并",
                                 target=f"{old} → {new}", output_path=args.output)
                ok, msg, payload = ops.merge_node(conn, old, new,
                                                  cli_cmd=" ".join(sys.argv[1:]))
                if not ok or payload is None:
                    return _emit_err("管位置", "位置合并", msg or "位置合并失败",
                                     {"src": old, "tgt": new},
                                     suggest="先确认 src 存在后重试,或改用「改名/删除」修正",
                                     output_path=args.output)
                payload["target"] = f"{old} → {new}"
                payload["diff"] = [{"field": "位置路径", "before": old, "after": new}]
                merged = payload.get("merged_items") or []
                payload["extra"] = {"本次合并迁移物品数": len(merged)}
                # 撤销合并: 精确到本次迁移的物品清单(避免路径级回退误伤 tgt 原有物品)
                if merged:
                    items_lines = "\n".join(f"    {i+1}. {it['name']} (ID {it['id']})" for i, it in enumerate(merged))
                    undo_text = (
                        "请加载「居家管家」技能,帮我撤销位置合并(唤醒词:管位置):\n"
                        f"  操  作: 撤销合并\n"
                        f"  从  位  置: 「{new}」\n"
                        f"  移  回  位  置: 「{old}」\n"
                        f"  物  品(本次合并迁移的 {len(merged)} 件,逐项移回):\n{items_lines}"
                    )
                else:
                    undo_text = f"管位置(居家管家): 合并回退,把「{new}」改回「{old}」"
                return _receipt_scene(ok, msg, payload, scenes.scene_id("sm2-manage"), "管位置", "位置合并",
                                      buttons=[{"label": "撤销合并", "text": undo_text}],
                                      output_path=args.output)

            if args.action in ("delete-preview", "delete"):
                path = args.path
                if args.action == "delete-preview":
                    from .schema import normalize_path
                    p = normalize_path(path)
                    if not p:
                        return _emit_err("管位置", "删除位置", "位置路径无效", {"path": path},
                                         output_path=args.output)
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT COUNT(*) AS n FROM item_locations WHERE location = ? OR location LIKE ?",
                        (p, p + "/%"))
                    n = cursor.fetchone()["n"]
                    return _emit("confirm.html", {"mode": "delete", "path": p,
                                                  "items_affected": n},
                                 scenes.scene_id("sm2-manage"), "管位置", "删除位置", target=p, output_path=args.output)
                ok, msg, payload = ops.delete_node(conn, path, cli_cmd=" ".join(sys.argv[1:]))
                return _receipt_scene(ok, msg, {"target": path, "extra": payload},
                                      scenes.scene_id("sm2-manage"), "管位置", "删除位置", output_path=args.output)
        finally:
            conn.close()

    # ── SM2-2 固定位 ──
    if cmd == "sm2-fixed":
        conn = ops._conn()
        try:
            if args.action == "list":
                data = ops.fixed_list_payload(conn)
                return _emit("fixed_spot.html", data, scenes.scene_id("sm2-fixed"), "固定位", "固定位",
                             target="", output_path=args.output)
            if args.action == "set":
                ok, msg, payload = ops.fixed_set(conn, args.item_id, args.location,
                                                 cli_cmd=" ".join(sys.argv[1:]))
                if ok:
                    payload["diff"] = [{"field": "固定位", "before": None, "after": args.location}]
                    return _receipt_scene(True, msg, payload, scenes.scene_id("sm2-fixed"), "固定位", "设置固定位",
                                          buttons=[{"label": "解除固定位", "text": f"固定位(居家管家): 解除 ID={args.item_id} 的固定位"}],
                                          output_path=args.output)
                return _emit_err("固定位", "设置固定位", msg, {"item_id": args.item_id},
                                 output_path=args.output)
            if args.action == "clear":
                ok, msg, payload = ops.fixed_clear(conn, args.item_id,
                                                   cli_cmd=" ".join(sys.argv[1:]))
                if ok:
                    return _receipt_scene(True, msg, payload, scenes.scene_id("sm2-fixed"), "固定位", "解除固定位",
                                          output_path=args.output)
                return _emit_err("固定位", "解除固定位", msg, {"item_id": args.item_id},
                                 output_path=args.output)
        finally:
            conn.close()

    # ── SM2-3 收纳建议 ──
    if cmd == "sm2-suggest":
        conn = ops._conn()
        try:
            if args.batch:
                recs = ops.recommend_batch(conn, limit=args.limit)
                recs = [r for r in recs if r]
                data = {"batch": True, "mode": "batch", "recommendations": recs,
                        "total": len(recs),
                        "hint": "没有固定位的常用件全部列出;逐条确认后建议去设置固定位"}
                return _emit("suggest_storage.html", data, scenes.scene_id("sm2-suggest"), "收纳建议", "收纳建议",
                             target=f"{len(recs)} 件", output_path=args.output)
            if args.item_ids:
                ids = [int(x) for x in args.item_ids.split(",") if x.strip()]
                recs = ops.recommend_items(conn, ids)
                data = {"batch": False, "mode": "multi", "recommendations": recs,
                        "total": len(recs), "hint": f"指定 {len(ids)} 件逐条给建议"}
                return _emit("suggest_storage.html", data, scenes.scene_id("sm2-suggest"), "收纳建议", "收纳建议",
                             target=f"{len(recs)} 件", output_path=args.output)
            rec = ops.recommend_item(conn, args.item_id)
            if not rec:
                return _emit_err("收纳建议", "收纳建议", f"未找到 ID={args.item_id} 的物品",
                                 {"item_id": args.item_id}, output_path=args.output)
            data = {"batch": False, "mode": "single", "recommendations": [rec], "total": 1}
            return _emit("suggest_storage.html", data, scenes.scene_id("sm2-suggest"), "收纳建议", "收纳建议",
                         target=rec["item"]["name"], output_path=args.output)
        finally:
            conn.close()

    return 1
