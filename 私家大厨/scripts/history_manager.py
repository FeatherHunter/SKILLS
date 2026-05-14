#!/usr/bin/env python3
"""
私家大厨 - 烹饪历史管理脚本 v1.0
对应表：recipe_history（14字段）
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from db_config import get_conn


def _json(val):
    if val is None: return None
    if isinstance(val, list): return json.dumps(val)
    if isinstance(val, str) and val.startswith('['): return val
    if isinstance(val, str): return json.dumps([v.strip() for v in val.split(',')])
    return None


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def history_add(
    recipe_id,
    cook_date=None,
    cook_sequence=None,
    modifications=None,
    rating_this_time=None,
    feedback=None,
    improvements=None,
    photos=None,
    time_actual_minutes=None,
    cost_actual=None,
    tools_used=None,
    mistakes_made=None,
    appetite_rating=None,
    compared_to_last_time=None,
    comparison_notes=None,
    is_favorite=None,
    next_cook_plan=None,
    tags=None,
    weather=None,
    people_count=None,
    mood_when_cooking=None,
    energy_level=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """添加烹饪历史（26字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    history_id = str(uuid.uuid4())
    now = _now()

    cursor.execute('''
        INSERT INTO recipe_history (
            id, recipe_id, cook_date, cook_sequence,
            modifications, rating_this_time, feedback, improvements,
            photos, time_actual_minutes, cost_actual,
            tools_used, mistakes_made, appetite_rating,
            compared_to_last_time, comparison_notes,
            is_favorite, next_cook_plan, tags,
            created_at, weather, people_count,
            mood_when_cooking, energy_level, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        history_id, recipe_id, cook_date or _now()[:10], cook_sequence,
        _json(modifications), rating_this_time, feedback, _json(improvements),
        _json(photos), time_actual_minutes, cost_actual,
        _json(tools_used), _json(mistakes_made), appetite_rating,
        1 if compared_to_last_time else 0, _json(comparison_notes),
        1 if is_favorite else 0, next_cook_plan, _json(tags),
        now, weather, people_count,
        mood_when_cooking, energy_level, now
    ])

    conn.commit()
    conn.close()
    return history_id


def history_list(recipe_id, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM recipe_history WHERE recipe_id = ? ORDER BY cook_date DESC",
        (recipe_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        for f in ['modifications', 'improvements', 'photos', 'tools_used', 'mistakes_made', 'tags', 'comparison_notes']:
            if r.get(f):
                try: r[f] = json.loads(r[f])
                except: pass
    return rows


def history_get(history_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipe_history WHERE id = ?", (history_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def history_update(
    history_id,
    recipe_id=None,
    cook_date=None,
    cook_sequence=None,
    modifications=None,
    rating_this_time=None,
    feedback=None,
    improvements=None,
    photos=None,
    time_actual_minutes=None,
    cost_actual=None,
    tools_used=None,
    mistakes_made=None,
    appetite_rating=None,
    compared_to_last_time=None,
    comparison_notes=None,
    is_favorite=None,
    next_cook_plan=None,
    tags=None,
    weather=None,
    people_count=None,
    mood_when_cooking=None,
    energy_level=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """更新烹饪历史（26字段）"""
    conn = get_conn()
    cursor = conn.cursor()
    sets = []
    vals = []
    if recipe_id is not None: sets.append("recipe_id = ?"); vals.append(recipe_id)
    if cook_date is not None: sets.append("cook_date = ?"); vals.append(cook_date)
    if cook_sequence is not None: sets.append("cook_sequence = ?"); vals.append(cook_sequence)
    if modifications is not None: sets.append("modifications = ?"); vals.append(_json(modifications))
    if rating_this_time is not None: sets.append("rating_this_time = ?"); vals.append(rating_this_time)
    if feedback is not None: sets.append("feedback = ?"); vals.append(feedback)
    if improvements is not None: sets.append("improvements = ?"); vals.append(_json(improvements))
    if photos is not None: sets.append("photos = ?"); vals.append(_json(photos))
    if time_actual_minutes is not None: sets.append("time_actual_minutes = ?"); vals.append(time_actual_minutes)
    if cost_actual is not None: sets.append("cost_actual = ?"); vals.append(cost_actual)
    if tools_used is not None: sets.append("tools_used = ?"); vals.append(_json(tools_used))
    if mistakes_made is not None: sets.append("mistakes_made = ?"); vals.append(_json(mistakes_made))
    if appetite_rating is not None: sets.append("appetite_rating = ?"); vals.append(appetite_rating)
    if compared_to_last_time is not None: sets.append("compared_to_last_time = ?"); vals.append(1 if compared_to_last_time else 0)
    if comparison_notes is not None: sets.append("comparison_notes = ?"); vals.append(_json(comparison_notes))
    if is_favorite is not None: sets.append("is_favorite = ?"); vals.append(1 if is_favorite else 0)
    if next_cook_plan is not None: sets.append("next_cook_plan = ?"); vals.append(next_cook_plan)
    if tags is not None: sets.append("tags = ?"); vals.append(_json(tags))
    if weather is not None: sets.append("weather = ?"); vals.append(weather)
    if people_count is not None: sets.append("people_count = ?"); vals.append(people_count)
    if mood_when_cooking is not None: sets.append("mood_when_cooking = ?"); vals.append(mood_when_cooking)
    if energy_level is not None: sets.append("energy_level = ?"); vals.append(energy_level)
    sets.append("updated_at = ?"); vals.append(_now())
    if not sets:
        conn.close()
        return False
    cursor.execute(f"UPDATE recipe_history SET {', '.join(sets)} WHERE id = ?", vals + [history_id])
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def history_delete(history_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recipe_history WHERE id = ?", (history_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def history_stats(recipe_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipe_history WHERE recipe_id = ?", (recipe_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

    if not rows:
        return {'total_cooks': 0, 'avg_rating': 0, 'avg_time': 0}

    ratings = [r['rating_this_time'] for r in rows if r.get('rating_this_time')]
    times = [r['time_actual_minutes'] for r in rows if r.get('time_actual_minutes')]

    return {
        'total_cooks': len(rows),
        'avg_rating': sum(ratings) / len(ratings) if ratings else 0,
        'avg_time': sum(times) / len(times) if times else 0,
        'last_cook': rows[0].get('cook_date', '-') if rows else '-',
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python history_manager.py add <recipe_id> [--field value ...]")
        print("  python history_manager.py list <recipe_id>")
        print("  python history_manager.py get <history_id>")
        print("  python history_manager.py update <history_id> [--field value ...]")
        print("  python history_manager.py delete <history_id>")
        print("  python history_manager.py stats <recipe_id>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        history_id = history_add(recipe_id, **fields)
        print(f"✅ 烹饪记录已添加 (ID: {history_id})")

    elif cmd == "list":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        rows = history_list(recipe_id)
        if not rows:
            print("暂无烹饪记录")
        else:
            print(f"\n📅 {len(rows)}条烹饪记录:")
            for r in rows:
                rating = f"⭐{r['rating_this_time']}" if r.get('rating_this_time') else ""
                print(f"  • {r['cook_date']} {rating} | {r.get('feedback','')[:30]}...")

    elif cmd == "get":
        history_id = sys.argv[2] if len(sys.argv) > 2 else input("history_id: ")
        r = history_get(history_id)
        if r:
            print(f"\n📅 烹饪记录 {r['cook_date']}")
            for k, v in r.items():
                if v:
                    print(f"   {k}: {v}")

    elif cmd == "update":
        history_id = sys.argv[2] if len(sys.argv) > 2 else input("history_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        history_update(history_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        history_id = sys.argv[2] if len(sys.argv) > 2 else input("history_id: ")
        confirm = input("确认删除？(y/n): ")
        if confirm.lower() == 'y':
            history_delete(history_id)
            print("✅ 已删除")

    elif cmd == "stats":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        stats = history_stats(recipe_id)
        print(f"\n📊 统计:")
        print(f"  制作次数: {stats['total_cooks']}")
        print(f"  平均评分: {stats['avg_rating']:.1f}")
        print(f"  平均耗时: {stats['avg_time']:.0f}分钟")
        print(f"  最后制作: {stats['last_cook']}")


if __name__ == "__main__":
    main()