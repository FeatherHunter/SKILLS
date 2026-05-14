#!/usr/bin/env python3
"""
私家大厨 - 小贴士管理脚本 v1.0
对应表：tips（23字段）
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from db_config import get_conn


CATEGORIES = [
    '采购技巧', '刀工技巧', '火候控制', '调味技巧',
    '装盘技巧', '设备巧用', '食材保存', '时间管理', '健康贴士'
]


def _json(val):
    if val is None: return None
    if isinstance(val, list): return json.dumps(val)
    if isinstance(val, str) and val.startswith('['): return val
    if isinstance(val, str): return json.dumps([v.strip() for v in val.split(',')])
    return None


def tip_add(
    recipe_id,
    step_id=None,
    ingredient_id=None,
    category=None,
    content=None,
    difficulty=None,
    priority=None,
    effectiveness_rating=None,
    estimated_time_saved=None,
    applicability_scenes=None,
    related_tips=None,
    photos=None,
    user_created=None,
    created_at=None,
    updated_at=None,
    tags=None,
    source=None,
    notes=None,
    apply_to_ingredient=None,
    apply_to_step=None,
    show_sequence=None,
    **kwargs
):
    """添加小贴士（23字段全量）"""
    conn = get_conn()
    cursor = conn.cursor()

    tip_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
        INSERT INTO tips (
            id, recipe_id, step_id, ingredient_id,
            category, content,
            difficulty, priority, effectiveness_rating,
            estimated_time_saved, applicability_scenes,
            related_tips, photos, user_created,
            created_at, updated_at,
            tags, source, notes,
            apply_to_ingredient, apply_to_step, show_sequence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        tip_id, recipe_id, step_id, ingredient_id,
        category, content,
        difficulty, priority, effectiveness_rating,
        estimated_time_saved, _json(applicability_scenes),
        _json(related_tips), _json(photos), 1 if user_created else 0,
        now, now,
        _json(tags), source, notes,
        apply_to_ingredient, apply_to_step, show_sequence
    ])

    conn.commit()
    conn.close()
    return tip_id


def tip_list(recipe_id, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tips WHERE recipe_id = ? ORDER BY category", (recipe_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def tip_get(tip_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tips WHERE id = ?", (tip_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def tip_update(
    tip_id,
    recipe_id=None,
    step_id=None,
    ingredient_id=None,
    category=None,
    content=None,
    difficulty=None,
    priority=None,
    effectiveness_rating=None,
    estimated_time_saved=None,
    applicability_scenes=None,
    related_tips=None,
    photos=None,
    user_created=None,
    tags=None,
    source=None,
    notes=None,
    apply_to_ingredient=None,
    apply_to_step=None,
    show_sequence=None,
):
    """更新小贴士（显式23字段）"""
    conn = get_conn()
    cursor = conn.cursor()
    sets = []
    vals = []
    if recipe_id is not None: sets.append("recipe_id = ?"); vals.append(recipe_id)
    if step_id is not None: sets.append("step_id = ?"); vals.append(step_id)
    if ingredient_id is not None: sets.append("ingredient_id = ?"); vals.append(ingredient_id)
    if category is not None: sets.append("category = ?"); vals.append(category)
    if content is not None: sets.append("content = ?"); vals.append(content)
    if difficulty is not None: sets.append("difficulty = ?"); vals.append(difficulty)
    if priority is not None: sets.append("priority = ?"); vals.append(priority)
    if effectiveness_rating is not None: sets.append("effectiveness_rating = ?"); vals.append(effectiveness_rating)
    if estimated_time_saved is not None: sets.append("estimated_time_saved = ?"); vals.append(estimated_time_saved)
    if applicability_scenes is not None: sets.append("applicability_scenes = ?"); vals.append(_json(applicability_scenes))
    if related_tips is not None: sets.append("related_tips = ?"); vals.append(_json(related_tips))
    if photos is not None: sets.append("photos = ?"); vals.append(_json(photos))
    if user_created is not None: sets.append("user_created = ?"); vals.append(1 if user_created else 0)
    if tags is not None: sets.append("tags = ?"); vals.append(_json(tags))
    if source is not None: sets.append("source = ?"); vals.append(source)
    if notes is not None: sets.append("notes = ?"); vals.append(notes)
    if apply_to_ingredient is not None: sets.append("apply_to_ingredient = ?"); vals.append(apply_to_ingredient)
    if apply_to_step is not None: sets.append("apply_to_step = ?"); vals.append(apply_to_step)
    if show_sequence is not None: sets.append("show_sequence = ?"); vals.append(show_sequence)
    if not sets:
        conn.close()
        return False
    import datetime; sets.append("updated_at = ?"); vals.append(datetime.datetime.now().isoformat())
    cursor.execute(f"UPDATE tips SET {', '.join(sets)} WHERE id = ?", vals + [tip_id])
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def tip_delete(tip_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tips WHERE id = ?", (tip_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def tip_list_all(limit=100):
    """列出所有小贴士（按分类）"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, r.name as recipe_name
        FROM tips t
        LEFT JOIN recipes r ON t.recipe_id = r.id
        ORDER BY t.category, t.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python tip_manager.py add <recipe_id> <分类> <内容> [--field value ...]")
        print("  python tip_manager.py list <recipe_id>")
        print("  python tip_manager.py get <tip_id>")
        print("  python tip_manager.py update <tip_id> [--field value ...]")
        print("  python tip_manager.py delete <tip_id>")
        print("  python tip_manager.py list-all")
        print()
        print(f"  分类: {', '.join(CATEGORIES)}")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        category = sys.argv[3] if len(sys.argv) > 3 else input("分类: ")
        content = sys.argv[4] if len(sys.argv) > 4 else input("内容: ")
        args = sys.argv[5:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        tip_id = tip_add(recipe_id, category, content, **fields)
        print(f"✅ 小贴士已添加 (ID: {tip_id})")

    elif cmd == "list":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        tips = tip_list(recipe_id)
        if not tips:
            print("暂无小贴士")
        else:
            print(f"\n💡 {len(tips)}条小贴士:")
            for t in tips:
                print(f"  [{t['category']}] {t['content'][:50]}...")

    elif cmd == "get":
        tip_id = sys.argv[2] if len(sys.argv) > 2 else input("tip_id: ")
        t = tip_get(tip_id)
        if t:
            print(f"\n💡 [{t['category']}] {t['content']}")
            for k, v in t.items():
                if v and k not in ['id', 'content', 'category']:
                    print(f"   {k}: {v}")

    elif cmd == "update":
        tip_id = sys.argv[2] if len(sys.argv) > 2 else input("tip_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        tip_update(tip_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        tip_id = sys.argv[2] if len(sys.argv) > 2 else input("tip_id: ")
        confirm = input("确认删除？(y/n): ")
        if confirm.lower() == 'y':
            tip_delete(tip_id)
            print("✅ 已删除")

    elif cmd == "list-all":
        tips = tip_list_all()
        print(f"\n💡 全部小贴士 ({len(tips)}条):")
        by_cat = {}
        for t in tips:
            cat = t.get('category', '未分类')
            if cat not in by_cat:
                by_cat[cat] = []
            by_cat[cat].append(t)
        for cat, ts in by_cat.items():
            print(f"\n  [{cat}] ({len(ts)}条):")
            for t in ts[:5]:
                print(f"    • {t['content'][:40]}... | {t.get('recipe_name','?')}")


if __name__ == "__main__":
    main()