#!/usr/bin/env python3
"""
私家大厨 - 步骤管理
管理表：cooking_steps
支持：add / list / update
"""

import sys
import uuid
from db_config import get_connection

def add(args):
    """添加步骤"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    action = args.get("--action")
    if not action:
        print("错误：请提供步骤动作（--action）")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
    
    # 获取sequence
    cursor.execute("SELECT MAX(sequence) as max_seq FROM cooking_steps WHERE recipe_id = ?", (recipe_id,))
    max_seq = cursor.fetchone()["max_seq"] or 0
    sequence = args.get("--sequence") or (max_seq + 1)
    
    step_id = str(uuid.uuid4())
    
    cursor.execute("""
        INSERT INTO cooking_steps (
            id, recipe_id, sequence, action, duration_minutes,
            heat_level, temperature, expected_result
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        step_id,
        recipe_id,
        sequence,
        action,
        args.get("--duration"),
        args.get("--heat_level"),
        args.get("--temperature"),
        args.get("--expected_result")
    ))
    
    conn.commit()
    conn.close()
    
    print(f"✅ 步骤添加成功！")
    print(f"   食谱：{recipe['name']}")
    print(f"   第{sequence}步：{action}")
    if args.get("--duration"):
        print(f"   时长：{args['--duration']}分钟")
    return True

def list(args):
    """查看某食谱的步骤"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    recipe = cursor.fetchone()
    if not recipe:
        print(f"未找到食谱：{recipe_id}")
        conn.close()
        return False
    
    cursor.execute("""
        SELECT * FROM cooking_steps 
        WHERE recipe_id = ?
        ORDER BY sequence
    """, (recipe_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"\n{recipe['name']} - 没有步骤记录")
        return True
    
    print(f"\n{recipe['name']} - 烹饪步骤：")
    for row in rows:
        dur = f"（{row['duration_minutes']}分钟）" if row['duration_minutes'] else ""
        heat = f" [{row['heat_level']}]" if row['heat_level'] else ""
        temp = f" {row['temperature']}" if row['temperature'] else ""
        result = f" → {row['expected_result']}" if row['expected_result'] else ""
        print(f"  第{row['sequence']}步{dur}{heat}：{row['action']}{temp}{result}")
    
    return True

def search(args):
    """搜索包含关键词的步骤"""
    keyword = args.get("<关键词>")
    if not keyword:
        print("错误：请提供关键词")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.name as recipe_name, cs.sequence, cs.action, cs.duration_minutes, cs.heat_level
        FROM cooking_steps cs
        JOIN recipes r ON cs.recipe_id = r.id
        WHERE cs.action LIKE ?
        ORDER BY r.name, cs.sequence
    """, (f"%{keyword}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        print(f"未找到包含'{keyword}'的步骤")
        return True
    
    print(f"\n找到 {len(rows)} 个步骤：")
    for row in rows:
        dur = f"（{row['duration_minutes']}分钟）" if row['duration_minutes'] else ""
        heat = f" [{row['heat_level']}]" if row['heat_level'] else ""
        print(f"  {row['recipe_name']} - 第{row['sequence']}步{dur}{heat}：{row['action']}")
    
    return True

def update(args):
    """更新步骤"""
    step_id = args.get("<step_id>")
    if not step_id:
        print("错误：请提供步骤ID")
        return False
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM cooking_steps WHERE id = ?", (step_id,))
    step = cursor.fetchone()
    if not step:
        print(f"未找到步骤：{step_id}")
        conn.close()
        return False
    
    updates = []
    params = []
    
    if args.get("--action"):
        updates.append("action = ?")
        params.append(args["--action"])
    if args.get("--sequence"):
        updates.append("sequence = ?")
        params.append(args["--sequence"])
    if args.get("--duration"):
        updates.append("duration_minutes = ?")
        params.append(args["--duration"])
    if args.get("--heat_level"):
        updates.append("heat_level = ?")
        params.append(args["--heat_level"])
    if args.get("--temperature"):
        updates.append("temperature = ?")
        params.append(args["--temperature"])
    if args.get("--expected_result"):
        updates.append("expected_result = ?")
        params.append(args["--expected_result"])
    
    if not updates:
        print("没有提供要更新的字段")
        conn.close()
        return False
    
    params.append(step_id)
    cursor.execute(f"UPDATE cooking_steps SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()
    
    print(f"✅ 步骤更新成功！")
    return True

def reorder(args):
    """调整步骤顺序"""
    recipe_id = args.get("<recipe_id>")
    if not recipe_id:
        print("错误：请提供食谱ID")
        return False

    from_seq = args.get("--from")
    to_seq = args.get("--to")
    if not from_seq or not to_seq:
        print("错误：请提供 --from 和 --to")
        return False

    # 转换为整数
    try:
        from_seq = int(from_seq)
        to_seq = int(to_seq)
    except ValueError:
        print("错误：--from 和 --to 必须是整数")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    # 分别查询 from_seq 和 to_seq 对应的步骤
    cursor.execute("""
        SELECT id, sequence FROM cooking_steps
        WHERE recipe_id = ? AND sequence = ?
    """, (recipe_id, from_seq))
    from_step = cursor.fetchone()

    cursor.execute("""
        SELECT id, sequence FROM cooking_steps
        WHERE recipe_id = ? AND sequence = ?
    """, (recipe_id, to_seq))
    to_step = cursor.fetchone()

    if not from_step:
        print(f"未找到第{from_seq}步")
        conn.close()
        return False

    if not to_step:
        print(f"未找到第{to_seq}步")
        conn.close()
        return False

    # 交换顺序
    cursor.execute("UPDATE cooking_steps SET sequence = ? WHERE id = ?", (to_seq, from_step["id"]))
    cursor.execute("UPDATE cooking_steps SET sequence = ? WHERE id = ?", (from_seq, to_step["id"]))

    conn.commit()
    conn.close()

    print(f"✅ 步骤顺序已调整：第{from_seq}步 ↔ 第{to_seq}步")
    return True

def main():
    if len(sys.argv) < 2:
        print("""用法：
    python step_manager.py add <recipe_id> --action <动作> [选项]
    python step_manager.py list <recipe_id>
    python step_manager.py search <关键词>
    python step_manager.py update <step_id> [选项]
    python step_manager.py reorder <recipe_id> --from <序号> --to <序号>
    python step_manager.py disable <step_id>

选项：
    --action 动作描述
    --sequence 步骤序号
    --duration 时长（分钟）
    --heat_level 火候（微火/小火/中火/大火/猛火）
    --temperature 温度描述
    --expected_result 预期效果
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
            if "<recipe_id>" not in args and action not in ("update", "disable"):
                args["<recipe_id>"] = arg
            elif action == "discard" and "<step_id>" not in args:
                args["<step_id>"] = arg
            i += 1
    
    if action == "add":
        add(args)
    elif action == "list":
        list(args)
    elif action == "search":
        search(args)
    elif action == "update":
        if len(sys.argv) > 2:
            args["<step_id>"] = sys.argv[2]
        update(args)
    elif action == "reorder":
        reorder(args)
    elif action == "discard":
        print("错误：废弃操作在食谱级别进行，使用 recipe_manager.py discard <recipe_id>")
    else:
        print(f"未知操作：{action}")

if __name__ == "__main__":
    main()