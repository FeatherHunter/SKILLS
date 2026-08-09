#!/usr/bin/env python3
"""
私家大厨 - 烹饪历史管理
管理表:recipe_history
支持:add / list / stats / global-stats / delete / update

L4 阶段:函数体迁 db.execute/query/transaction
T10(2026-08-09):global-stats 全局画像(单查询)· delete 回执撤销 · add 补 json 输出(回执需 history_id)
"""

import sys
import uuid
from datetime import datetime
from db import get_connection, query, execute, transaction
from cli_formatter import emit, parse_json_flag, error
import validators  # 决策 3:接入 validate_rating_range / validate_date_format


def add(args):
    """记录做菜(INSERT + UPDATE 同事务)"""
    from cli_formatter import emit
    json_mode = args.get("_json_mode", False)
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        emit(error("请提供食谱ID或菜名"), json_mode=json_mode)
        return False

    # 决策 3:rating 范围校验(0-5,含小数)
    rating = args.get("--rating")
    if rating is not None:
        try:
            rating_val = float(rating)
        except (ValueError, TypeError):
            emit(error("--rating 必须是数字"), json_mode=json_mode)
            return False
        rt_validation = validators.validate_rating_range(rating_val)
        if not rt_validation["valid"]:
            emit(error(f"{rt_validation['error']} 怎么修:请拿 hint 去问用户,确认评分后重试。"), json_mode=json_mode)
            return False
        rating = rating_val

    # 决策 3:cook_date 日期格式校验(YYYY-MM-DD)
    cook_date = args.get("--cook_date") or datetime.now().strftime("%Y-%m-%d")
    dt_validation = validators.validate_date_format(cook_date, "cook_date")
    if not dt_validation["valid"]:
        emit(error(f"{dt_validation['error']} 怎么修:请拿 hint 去问用户,确认日期后用 --cook_date YYYY-MM-DD 重试。"), json_mode=json_mode)
        return False

    # L1 NOT NULL 兜底:feedback 必填(2026-07-22)
    feedback = args.get("--feedback")
    if not feedback:
        emit(error("缺少 --feedback(L1 NOT NULL 兜底,DB 不允许 NULL) 这是 L1 设计 —— 缺字段说明 AI 没问用户就调用了。请拿 hint 去问用户,这次做菜的反馈/改进建议是什么?"), json_mode=json_mode)
        return False

    # L4: db.query 替代 conn/cursor
    recipes = query("SELECT id, name, status FROM recipes WHERE id = ? OR name LIKE ?", (recipe_id, f"%{recipe_id}%"))
    if not recipes:
        emit(error(f"未找到食谱:{recipe_id}"), json_mode=json_mode)
        return False
    recipe = recipes[0]
    recipe_id = recipe["id"]  # 确保使用UUID

    # 计算 cook_sequence
    max_seq_rows = query("SELECT MAX(cook_sequence) as max_seq FROM recipe_history WHERE recipe_id = ?", (recipe_id,))
    max_seq = max_seq_rows[0]["max_seq"] if max_seq_rows and max_seq_rows[0]["max_seq"] is not None else 0
    new_seq = max_seq + 1

    history_id = str(uuid.uuid4())

    # L4: INSERT + UPDATE 同事务
    try:
        with transaction() as conn:
            execute(
                "INSERT INTO recipe_history (id, recipe_id, cook_date, cook_sequence, rating, feedback) VALUES (?, ?, ?, ?, ?, ?)",
                (history_id, recipe_id, cook_date, new_seq, rating, feedback)
            )

            # 如果是第一次,更新 recipes 状态
            if recipe["status"] == "未做":
                execute("UPDATE recipes SET status = '已做' WHERE id = ?", (recipe_id,))
    except Exception as e:
        emit(error(f"添加失败:{e}"), json_mode=json_mode)
        return False

    data = {
        "history_id": history_id,
        "recipe_id": recipe_id,
        "recipe_name": recipe["name"],
        "cook_date": cook_date,
        "cook_sequence": new_seq,
        "rating": rating,
        "feedback": feedback,
    }
    if json_mode:
        emit({"status": "success", "data": data,
              "message": f"烹饪记录添加成功:{recipe['name']} 第{new_seq}次"}, json_mode=True)
    else:
        print(f"✅ 烹饪记录添加成功!")
        print(f"   记录ID:{history_id}")
        print(f"   食谱:{recipe['name']}")
        print(f"   日期:{cook_date}")
        print(f"   第{new_seq}次做")
        if rating is not None:
            print(f"   评分:{rating}")
        print(f"   反馈:{feedback}")
    return True


def list_items(args):
    """查看烹饪历史"""
    from cli_formatter import emit
    json_mode = args.get("_json_mode", False)

    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        if json_mode:
            emit({"status": "error", "error": "missing_recipe_id", "message": "请提供食谱ID或菜名"}, json_mode=True)
        else:
            print("错误:请提供食谱ID或菜名")
        return False

    recipes = query("SELECT id, name FROM recipes WHERE id = ? OR name LIKE ?", (recipe_id, f"%{recipe_id}%"))
    if not recipes:
        if json_mode:
            emit({"status": "error", "error": "recipe_not_found", "message": f"未找到食谱:{recipe_id}"}, json_mode=True)
        else:
            print(f"未找到食谱:{recipe_id}")
        return False

    recipe_id = recipes[0]["id"]
    rows = query("""
        SELECT * FROM recipe_history
        WHERE recipe_id = ?
        ORDER BY cook_date DESC
    """, (recipe_id,))

    if json_mode:
        emit({
            "status": "success",
            "data": {
                "recipe_id": recipe_id,
                "recipe_name": recipes[0]['name'],
                "history": [dict(r) for r in rows],
                "history_count": len(rows)
            },
            "message": f"历史查询成功:{recipes[0]['name']} ({len(rows)} 条)"
        }, json_mode=True)
    else:
        if not rows:
            print(f"\n{recipes[0]['name']} - 没有烹饪记录")
            return True

        print(f"\n{recipes[0]['name']} - 烹饪历史:")
        for row in rows:
            rating_str = f"评分{row['rating']}" if row['rating'] else ""
            feedback_str = f"「{row['feedback']}」" if row['feedback'] else ""
            print(f"  {row['cook_date']} 第{row['cook_sequence']}次 {rating_str} {feedback_str}")

    return True


def stats(args):
    """查看统计(L4:db.query)"""
    from cli_formatter import emit
    json_mode = args.get("_json_mode", False)

    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        if json_mode:
            emit({"status": "error", "error": "missing_recipe_id", "message": "请提供食谱ID或菜名"}, json_mode=True)
        else:
            print("错误:请提供食谱ID或菜名")
        return False

    recipes = query("SELECT id, name FROM recipes WHERE id = ? OR name LIKE ?", (recipe_id, f"%{recipe_id}%"))
    if not recipes:
        if json_mode:
            emit({"status": "error", "error": "recipe_not_found", "message": f"未找到食谱:{recipe_id}"}, json_mode=True)
        else:
            print(f"未找到食谱:{recipe_id}")
        return False

    recipe_id = recipes[0]["id"]
    stats_rows = query("""
        SELECT
            COUNT(*) as times,
            AVG(rating) as avg_rating,
            MAX(rating) as max_rating,
            MIN(rating) as min_rating,
            MAX(cook_sequence) as max_seq
        FROM recipe_history
        WHERE recipe_id = ?
    """, (recipe_id,))
    stats = stats_rows[0] if stats_rows else {}

    last_rows = query("""
        SELECT cook_date FROM recipe_history
        WHERE recipe_id = ?
        ORDER BY cook_date DESC LIMIT 1
    """, (recipe_id,))
    last = last_rows[0] if last_rows else None

    times = int(stats['times']) if stats.get('times') is not None else 0
    avg_rating = float(stats['avg_rating']) if stats.get('avg_rating') is not None else None
    max_rating = float(stats['max_rating']) if stats.get('max_rating') is not None else None
    min_rating = float(stats['min_rating']) if stats.get('min_rating') is not None else None
    last_date = last['cook_date'] if last else None

    if json_mode:
        emit({
            "status": "success",
            "data": {
                "recipe_id": recipe_id,
                "recipe_name": recipes[0]['name'],
                "stats": {
                    "total_cooks": times,
                    "avg_rating": avg_rating,
                    "max_rating": max_rating,
                    "min_rating": min_rating,
                    "last_date": last_date,
                }
            },
            "message": f"统计查询成功:{recipes[0]['name']}"
        }, json_mode=True)
    else:
        print(f"\n{recipes[0]['name']} - 烹饪统计:")
        print(f"  总次数:{times}")
        print(f"  平均评分:{avg_rating:.2f}" if avg_rating else "  平均评分:-")
        if max_rating is not None:
            print(f"  最高评分:{max_rating:.1f}")
            print(f"  最低评分:{min_rating:.1f}")
        print(f"  最后做菜:{last_date if last_date else '-'}")

    return True


def global_stats(args):
    """查看全局统计(hist-4 画像版 · 一次查询即得 · 单 SQL 聚合 recipe_history + recipes)"""
    from cli_formatter import emit
    json_mode = args.get("_json_mode", False)

    rows = query("""
        SELECT
            r.id AS recipe_id,
            r.name AS recipe_name,
            r.status AS recipe_status,
            COUNT(h.id) AS cook_count,
            AVG(h.rating) AS avg_rating,
            MAX(h.cook_date) AS last_date
        FROM recipes r
        LEFT JOIN recipe_history h ON h.recipe_id = r.id
        GROUP BY r.id
    """)

    cooked = [r for r in rows if r["cook_count"] and r["cook_count"] > 0]
    never_cooked = [r for r in rows if not r["cook_count"] or r["cook_count"] == 0]

    total_cooks = sum(r["cook_count"] or 0 for r in cooked)

    # 最爱:均分最高(需有评分) + 做得最多
    rated = [r for r in cooked if r["avg_rating"] is not None]
    favorite_avg = max(rated, key=lambda r: r["avg_rating"]) if rated else None
    favorite_most = max(cooked, key=lambda r: r["cook_count"]) if cooked else None

    # 最近吃了啥:按最近做菜日期倒序取前 5
    recent = sorted(cooked, key=lambda r: r["last_date"] or "", reverse=True)[:5]

    # 还没做过的菜:无历史记录
    never_list = [r["recipe_name"] for r in never_cooked]

    data = {
        "cooked_count": len(cooked),           # 做过几道菜
        "never_cooked_count": len(never_cooked),  # 还没做过的菜数
        "total_cooks": total_cooks,            # 总次数
        "recipe_total": len(rows),
        "favorite_avg": ({"name": favorite_avg["recipe_name"], "avg_rating": round(float(favorite_avg["avg_rating"]), 2), "times": favorite_avg["cook_count"]} if favorite_avg else None),
        "favorite_most": ({"name": favorite_most["recipe_name"], "times": favorite_most["cook_count"], "avg_rating": (round(float(favorite_most["avg_rating"]), 2) if favorite_most["avg_rating"] is not None else None)} if favorite_most else None),
        "recent": [{"name": r["recipe_name"], "last_date": r["last_date"], "rating": (round(float(r["avg_rating"]), 2) if r["avg_rating"] is not None else None)} for r in recent],
        "never_cooked": never_list,
    }

    if json_mode:
        emit({"status": "success", "data": {"global": data},
              "message": f"全局统计:做过 {len(cooked)} 道菜,共 {total_cooks} 次"}, json_mode=True)
    else:
        print(f"\n📜 私家大厨 · 全局统计(整体画像):")
        print(f"  做过几道菜:{len(cooked)} / 总次数:{total_cooks}")
        if favorite_avg:
            print(f"  最爱·均分最高:{favorite_avg['recipe_name']}({favorite_avg['avg_rating']:.2f} 分,做了 {favorite_avg['cook_count']} 次)")
        if favorite_most:
            print(f"  最爱·做得最多:{favorite_most['recipe_name']}(做了 {favorite_most['cook_count']} 次)")
        if recent:
            recent_str = " → ".join(f'{r["recipe_name"]}({r["last_date"]})' for r in recent)
            print(f"  最近吃了啥: {recent_str}")
        print(f"  还没做过的菜:{'、'.join(never_list) if never_list else '(没有,全做过了)'}")

    return True


def delete(args):
    """撤销记录(T10 回执撤销 · 反悔 · 删除单条 history)"""
    from cli_formatter import emit
    json_mode = args.get("_json_mode", False)

    history_id = args.get("<history_id>")
    if not history_id:
        emit(error("请提供记录ID"), json_mode=json_mode)
        return False

    row = query("SELECT id, recipe_id FROM recipe_history WHERE id = ?", (history_id,))
    if not row:
        emit(error(f"未找到记录:{history_id}"), json_mode=json_mode)
        return False
    recipe_id = row[0]["recipe_id"]

    # 删除后若该菜再无历史,且此前由首次做菜置为"已做" → 回滚为"未做"
    try:
        with transaction() as conn:
            execute("DELETE FROM recipe_history WHERE id = ?", (history_id,))
            remain = query("SELECT COUNT(*) AS c FROM recipe_history WHERE recipe_id = ?", (recipe_id,))[0]["c"]
            if remain == 0:
                recipe = query("SELECT status FROM recipes WHERE id = ?", (recipe_id,))
                if recipe and recipe[0]["status"] == "已做":
                    execute("UPDATE recipes SET status = '未做' WHERE id = ?", (recipe_id,))
    except Exception as e:
        emit(error(f"撤销失败:{e}"), json_mode=json_mode)
        return False

    data = {"history_id": history_id, "recipe_id": recipe_id, "status_reverted": remain == 0}
    if json_mode:
        emit({"status": "success", "data": data, "message": f"记录已撤销:{history_id}"}, json_mode=True)
    else:
        print(f"✅ 记录已撤销:{history_id}")
        if remain == 0:
            print("   该菜已无历史记录,状态已回滚为「未做」")
    return True


def update(args):
    """更新记录(L4:动态 SQL)"""
    history_id = args.get("<history_id>")
    if not history_id:
        print("错误:请提供记录ID")
        return False

    history = query("SELECT id FROM recipe_history WHERE id = ?", (history_id,))
    if not history:
        print(f"未找到记录:{history_id}")
        return False

    updates = []
    params = []

    if args.get("--cook_date"):
        updates.append("cook_date = ?")
        params.append(args["--cook_date"])
    if args.get("--rating"):
        updates.append("rating = ?")
        params.append(args["--rating"])
    if args.get("--feedback"):
        updates.append("feedback = ?")
        params.append(args["--feedback"])

    if not updates:
        print("没有提供要更新的字段")
        return False

    params.append(history_id)
    execute(f"UPDATE recipe_history SET {', '.join(updates)} WHERE id = ?", params)

    print(f"✅ 记录更新成功!")
    return True


def main():
    if len(sys.argv) < 2:
        print("""用法:
    python history_manager.py add <recipe_id> --cook_date <日期> --rating <评分> --feedback <反馈>
    python history_manager.py list <recipe_id>
    python history_manager.py stats <recipe_id>
    python history_manager.py global-stats
    python history_manager.py delete <history_id>
    python history_manager.py update <history_id> [选项]

选项:
    --cook_date 烹饪日期(YYYY-MM-DD)
    --rating 评分(1-5)
    --feedback 反馈内容
""")
        return

    action = sys.argv[1]
    json_mode = parse_json_flag(sys.argv[2:])

    args = {"_json_mode": json_mode}
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg.startswith("--"):
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                args[arg] = sys.argv[i + 1]
                i += 2
            else:
                args[arg] = True
                i += 1
        else:
            if action in ("add", "list", "stats") and "<recipe_id>" not in args:
                args["<recipe_id>"] = arg
            elif action in ("update", "delete") and "<history_id>" not in args:
                args["<history_id>"] = arg
            i += 1

    if action == "add":
        add(args)
    elif action == "list":
        list_items(args)
    elif action == "stats":
        stats(args)
    elif action == "global-stats":
        global_stats(args)
    elif action == "delete":
        delete(args)
    elif action == "update":
        update(args)
    else:
        emit(error(f"未知操作:{action}"), json_mode=json_mode)


if __name__ == "__main__":
    main()