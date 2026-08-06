# cli.py - SM3 穿搭出行域 CLI 子命令注册与分发(T4 · 镜像 物品/cli.py 模式)
# home_manager.py 只做 3 处加法接线: import / register / dispatch
import json
import sys

from home_manager.db import get_conn


def register(subparsers):
    """注册 SM3 子命令(全部以 sm3- 前缀,与旧命令并存)"""
    p = subparsers.add_parser("sm3-outfit", help="穿搭推荐(3-1 · 拼贴卡)")
    p.add_argument("--temperature", type=int, default=None, help="今日温度(选填,AI 获取)")
    p.add_argument("--occasion", default=None, help="场合(上班/约会/运动/家居/正式)")
    p.add_argument("--limit", type=int, default=5, help="组合套数(默认 5,本地翻页)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm3-wardrobe", help="衣橱分析(3-2 · 闲置诊断)")
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm3-season", help="换季收纳(3-3)")
    p.add_argument("--season", default="夏季", choices=["夏季", "冬季", "春秋"])
    p.add_argument("--action", default="收纳", choices=["收纳", "拿出"])
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm3-trip", help="出行清单(3-4 · 带/归)")
    p.add_argument("--trip-type", default="出差",
                   choices=["健身", "出差", "旅行", "超市", "游泳", "爬山", "滑雪", "自定义"])
    p.add_argument("--days", type=int, default=3)
    p.add_argument("--plan-type", default=None, choices=["力量", "有氧", "休息日"],
                   help="健身联动第一层: 计划类型")
    p.add_argument("--exercises", default=None, help="健身动作,逗号分隔(护具知识表第二层)")
    p.add_argument("--mode", default="pack", choices=["pack", "return"])
    p.add_argument("--output", default=None)

    p = subparsers.add_parser("sm3-trip-plan", help="旅行穿搭计划(3-5)")
    p.add_argument("--days", type=int, default=5)
    p.add_argument("--destination", default="")
    p.add_argument("--temps", default=None, help="每日温度,逗号分隔(选填,AI 获取未来预报)")
    p.add_argument("--output", default=None)


def run(args):
    """SM3 域分发(T4 · 与 sm1_run 同构)"""
    from render_穿搭 import emit_sm3, emit_error

    def _payload():
        from home_manager.outfit_ops import (
            outfit_payload_v2, wardrobe_payload, season_payload,
            trip_payload_v2, trip_plan_payload,
        )
        conn = get_conn()
        try:
            if args.command == "sm3-outfit":
                return outfit_payload_v2(conn, temperature=args.temperature,
                                         occasion=args.occasion or "", limit=args.limit)
            if args.command == "sm3-wardrobe":
                return wardrobe_payload(conn)
            if args.command == "sm3-season":
                return season_payload(conn, season=args.season, action=args.action)
            if args.command == "sm3-trip":
                exercises = [e.strip() for e in (args.exercises or "").split(",") if e.strip()]
                if args.mode == "return":
                    return _return_payload(conn)
                return trip_payload_v2(conn, trip_type=args.trip_type, days=args.days,
                                       plan_type=args.plan_type, exercises=exercises)
            if args.command == "sm3-trip-plan":
                temps = None
                if args.temps:
                    parsed = []
                    for t in args.temps.split(","):
                        try:
                            parsed.append(int(t.strip()))
                        except ValueError:
                            parsed.append(None)
                    temps = parsed
                return trip_plan_payload(conn, days=args.days,
                                         temps=temps, destination=args.destination)
        finally:
            conn.close()
        return None

    def _return_payload(conn):
        from home_manager.tag_ops import get_tags
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT i.id, i.name, il.location, il.location_status
            FROM items i JOIN item_locations il ON i.id = il.item_id
            WHERE il.location_status = '旅游中' ORDER BY i.name
        """)
        rows = cur.fetchall()
        items = []
        for r in rows:
            items.append({
                "id": r["id"], "name": r["name"], "location": r["location"],
                "location_status": r["location_status"], "tags": get_tags(conn, r["id"]),
            })
        return {
            "summary": {"title": "回家归位清单",
                        "subtitle": "逐条确认归位(恢复在家),复制回执发给 AI 批量更新",
                        "metrics": [{"label": "旅游中", "value": f"{len(items)} 件"}]},
            "trip_type": "归位", "days": 1, "plan_type": None, "mode": "return",
            "items": items, "unregistered": [],
        }

    data = _payload()
    if data is None:
        print(json.dumps({"status": "error", "message": f"未知 sm3 命令: {args.command}"},
                         ensure_ascii=False))
        return 1

    mapping = {
        "sm3-outfit": ("outfit_picker.html", "SM3-1", "穿什么", "穿什么"),
        "sm3-wardrobe": ("wardrobe_analyze.html", "SM3-2", "衣橱分析", "衣橱分析"),
        "sm3-season": ("wardrobe_season.html", "SM3-3", "换季", "换季"),
        "sm3-trip": ("travel_trip.html", "SM3-4", "带物品", "出行清单"),
        "sm3-trip-plan": ("trip_outfit_plan.html", "SM3-5", "旅行穿搭", "旅行穿搭"),
    }
    template, scene_id, wake_word, command_cn = mapping[args.command]
    if data.get("error"):
        return emit_error(wake_word, command_cn, data["error"],
                          output_path=args.output)
    target = {"command": args.command, "params": {k: v for k, v in vars(args).items()
                                                  if k not in ("output", "command")}}
    return emit_sm3(template, data, scene_id, wake_word, command_cn,
                    target=target, output_path=args.output)
