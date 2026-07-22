#!/usr/bin/env python3
"""
私家大厨 - 烹饪历史管理
管理表：recipe_history
支持：add / list / stats / update
"""

import sys
import uuid
from datetime import datetime
# L2: 统一从 db.py 取连接(L3 阶段再把 conn/cursor 改成 db.query/execute/transaction)
from db import get_connection

def add(args):
    """记录做菜"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID或菜名")
        return False

    # 评分范围验证
    rating = args.get("--rating")
    if rating:
        try:
            rating_val = float(rating)
            if rating_val < 1 or rating_val > 5:
                print("错误：评分必须在1-5之间")
                return False
            rating = rating_val
        except ValueError:
            print("错误：评分必须是数字")
            return False

    cook_date = args.get("--cook_date") or datetime.now().strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()

    # 支持ID和菜名两种查询方式
    cursor.execute("SELECT id, name, status FROM recipes WHERE id = ? OR name LIKE ?", (recipe_id, f"%{recipe_id}%"))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False

    recipe_id = recipe["id"]  # 确保使用UUID

    # 计算cook_sequence
    cursor.execute("SELECT MAX(cook_sequence) as max_seq FROM recipe_history WHERE recipe_id = ?", (recipe_id,))
    max_seq = cursor.fetchone()["max_seq"] or 0

    history_id = str(uuid.uuid4())

    cursor.execute("""
        INSERT INTO recipe_history (id, recipe_id, cook_date, cook_sequence, rating, feedback)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        history_id,
        recipe_id,
        cook_date,
        max_seq + 1,
        rating,
        args.get("--feedback")
    ))

    # 如果是第一次，更新recipes状态
    if recipe["status"] == "未做":
        cursor.execute("UPDATE recipes SET status = '已做' WHERE id = ?", (recipe_id,))

    conn.commit()
    conn.close()

    print(f"✅ 烹饪记录添加成功！")
    print(f"   食谱：{recipe['name']}")
    print(f"   日期：{cook_date}")
    print(f"   第{max_seq + 1}次做")
    if rating:
        print(f"   评分：{rating}")
    return True

def list_items(args):
    """查看烹饪历史"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID或菜名")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    # 支持ID和菜名两种查询方式
    cursor.execute("SELECT id, name FROM recipes WHERE id = ? OR name LIKE ?", (recipe_id, f"%{recipe_id}%"))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False

    recipe_id = recipe["id"]  # 确保使用UUID

    cursor.execute("""
        SELECT * FROM recipe_history
        WHERE recipe_id = ?
        ORDER BY cook_date DESC
    """, (recipe_id,))

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f"\n{recipe['name']} - 没有烹饪记录")
        return True

    print(f"\n{recipe['name']} - 烹饪历史：")
    for row in rows:
        rating_str = f"评分{row['rating']}" if row['rating'] else ""
        feedback_str = f"「{row['feedback']}」" if row['feedback'] else ""
        print(f"  {row['cook_date']} 第{row['cook_sequence']}次 {rating_str} {feedback_str}")

    return True

def stats(args):
    """查看统计"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID或菜名")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    # 支持ID和菜名两种查询方式
    cursor.execute("SELECT id, name FROM recipes WHERE id = ? OR name LIKE ?", (recipe_id, f"%{recipe_id}%"))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False

    recipe_id = recipe["id"]  # 确保使用UUID

    cursor.execute("""
        SELECT
            COUNT(*) as times,
            AVG(rating) as avg_rating,
            MAX(rating) as max_rating,
            MIN(rating) as min_rating,
            MAX(cook_sequence) as max_seq
        FROM recipe_history
        WHERE recipe_id = ?
    """, (recipe_id,))

    stats = cursor.fetchone()

    # 获取最后做菜日期
    cursor.execute("""
        SELECT cook_date FROM recipe_history
        WHERE recipe_id = ?
        ORDER BY cook_date DESC LIMIT 1
    """, (recipe_id,))
    last = cursor.fetchone()

    conn.close()

    # 显式转换，防止 SQLite lazy evaluation 问题
    times = int(stats['times']) if stats['times'] is not None else 0
    avg_rating = float(stats['avg_rating']) if stats['avg_rating'] is not None else None
    max_rating = float(stats['max_rating']) if stats['max_rating'] is not None else None
    min_rating = float(stats['min_rating']) if stats['min_rating'] is not None else None
    last_date = last['cook_date'] if last else None

    print(f"\n{recipe['name']} - 烹饪统计：")
    print(f"  总次数：{times}")
    print(f"  平均评分：{avg_rating:.2f}" if avg_rating else "  平均评分：-")
    if max_rating is not None:
        print(f"  最高评分：{max_rating:.1f}")
        print(f"  最低评分：{min_rating:.1f}")
    print(f"  最后做菜：{last_date if last_date else '-'}")

    return True

def update(args):
    """更新记录"""
    history_id = args.get("<history_id>")
    if not history_id:
        print("错误：请提供记录ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM recipe_history WHERE id = ?", (history_id,))
    history = cursor.fetchone()
    if not history:
        print(f"未找到记录：{history_id}")
        conn.close()
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
        conn.close()
        return False
    
    params.append(history_id)
    cursor.execute(f"UPDATE recipe_history SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    
    print(f"✅ 记录更新成功！")
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python history_manager.py add <recipe_id> --cook_date <日期> --rating <评分> --feedback <反馈>
    python history_manager.py list <recipe_id>
    python history_manager.py stats <recipe_id>
    python history_manager.py update <history_id> [选项]

选项：
    --cook_date 烹饪日期（YYYY-MM-DD）
    --rating 评分（1-5）
    --feedback 反馈内容
""")
        return
    
    action = sys.argv[1]
    
    args = {}
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
            elif action == "update" and "<history_id>" not in args:
                args["<history_id>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "list":
        list_items(args)
    elif action == "stats":
        stats(args)
    elif action == "update":
        update(args)
    else:
        print(f"未知操作：{action}")

if __name__ == "__main__":
    main()