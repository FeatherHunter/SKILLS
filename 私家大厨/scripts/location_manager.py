#!/usr/bin/env python3
"""
私家大厨 - 地区分类管理脚本 v1.0
对应表：recipe_locations（18字段）
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from db_config import get_conn


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _json(val):
    if val is None: return None
    if isinstance(val, list): return json.dumps(val)
    if isinstance(val, str) and val.startswith('['): return val
    if isinstance(val, str): return json.dumps([v.strip() for v in val.split(',')])
    return None


def location_add(
    recipe_id,
    country=None,
    province=None,
    city=None,
    cuisine_type=None,
    cuisine_type_secondary=None,
    dish_type=None,
    meal_type=None,
    cooking_method=None,
    flavor_profile=None,
    flavor_intensity=None,
    diet_tags=None,
    seasons=None,
    occasions=None,
    target_demographic=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """添加地区分类（18字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    location_id = str(uuid.uuid4())
    now = _now()

    cursor.execute('''
        INSERT INTO recipe_locations (
            id, recipe_id, country, province, city,
            cuisine_type, cuisine_type_secondary, dish_type, meal_type,
            cooking_method, flavor_profile, flavor_intensity,
            diet_tags, seasons, occasions, target_demographic,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        location_id, recipe_id, country, province, city,
        cuisine_type, cuisine_type_secondary, dish_type, _json(meal_type),
        cooking_method, _json(flavor_profile), flavor_intensity,
        _json(diet_tags), _json(seasons), _json(occasions), target_demographic,
        now, now
    ])

    conn.commit()
    conn.close()
    return location_id


def location_list(recipe_id):
    """列出某食谱的所有地区分类"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipe_locations WHERE recipe_id = ?", (recipe_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        for f in ['meal_type', 'flavor_profile', 'diet_tags', 'seasons', 'occasions']:
            if r.get(f):
                try: r[f] = json.loads(r[f])
                except: pass
    return rows


def location_get(location_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM recipe_locations WHERE id = ?", (location_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def location_update(
    location_id,
    recipe_id=None,
    country=None,
    province=None,
    city=None,
    cuisine_type=None,
    cuisine_type_secondary=None,
    dish_type=None,
    meal_type=None,
    cooking_method=None,
    flavor_profile=None,
    flavor_intensity=None,
    diet_tags=None,
    seasons=None,
    occasions=None,
    target_demographic=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """更新地区分类（18字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    fields = {}
    if recipe_id is not None: fields['recipe_id'] = recipe_id
    if country is not None: fields['country'] = country
    if province is not None: fields['province'] = province
    if city is not None: fields['city'] = city
    if cuisine_type is not None: fields['cuisine_type'] = cuisine_type
    if cuisine_type_secondary is not None: fields['cuisine_type_secondary'] = cuisine_type_secondary
    if dish_type is not None: fields['dish_type'] = dish_type
    if meal_type is not None: fields['meal_type'] = _json(meal_type)
    if cooking_method is not None: fields['cooking_method'] = cooking_method
    if flavor_profile is not None: fields['flavor_profile'] = _json(flavor_profile)
    if flavor_intensity is not None: fields['flavor_intensity'] = flavor_intensity
    if diet_tags is not None: fields['diet_tags'] = _json(diet_tags)
    if seasons is not None: fields['seasons'] = _json(seasons)
    if occasions is not None: fields['occasions'] = _json(occasions)
    if target_demographic is not None: fields['target_demographic'] = target_demographic
    if created_at is not None: fields['created_at'] = created_at
    if updated_at is not None: fields['updated_at'] = updated_at

    if not fields:
        conn.close()
        return False

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [location_id]
    cursor.execute(f"UPDATE recipe_locations SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def location_delete(location_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recipe_locations WHERE id = ?", (location_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def query_by_cuisine(cuisine, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT r.* FROM recipes r JOIN recipe_locations l ON r.id = l.recipe_id WHERE l.cuisine_type = ? LIMIT ?",
        (cuisine, limit)
    )
    return [dict(r) for r in cursor.fetchall()]


def query_by_season(season, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT r.* FROM recipes r JOIN recipe_locations l ON r.id = l.recipe_id WHERE l.seasons LIKE ? LIMIT ?",
        (f'%{season}%', limit)
    )
    return [dict(r) for r in cursor.fetchall()]


def query_by_occasion(occasion, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT r.* FROM recipes r JOIN recipe_locations l ON r.id = l.recipe_id WHERE l.occasions LIKE ? LIMIT ?",
        (f'%{occasion}%', limit)
    )
    return [dict(r) for r in cursor.fetchall()]


def query_by_flavor(flavor, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT r.* FROM recipes r JOIN recipe_locations l ON r.id = l.recipe_id WHERE l.flavor_profile LIKE ? LIMIT ?",
        (f'%{flavor}%', limit)
    )
    return [dict(r) for r in cursor.fetchall()]


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python location_manager.py add <recipe_id> [--field value ...]")
        print("  python location_manager.py list <recipe_id>")
        print("  python location_manager.py get <location_id>")
        print("  python location_manager.py update <location_id> [--field value ...]")
        print("  python location_manager.py delete <location_id>")
        print("  python location_manager.py query-cuisine <菜系>")
        print("  python location_manager.py query-season <季节>")
        print("  python location_manager.py query-occasion <场合>")
        print("  python location_manager.py query-flavor <口味>")
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
        location_id = location_add(recipe_id, **fields)
        print(f"✅ 地区分类已添加 (ID: {location_id})")

    elif cmd == "list":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        locs = location_list(recipe_id)
        if not locs:
            print("暂无地区分类")
        else:
            for loc in locs:
                print(f"\n📍 {loc.get('cuisine_type','-')} | {loc.get('province','-')}{loc.get('city','')}")
                print(f"   烹饪: {loc.get('cooking_method','-')} | 口味: {loc.get('flavor_profile','-')}")
                print(f"   季节: {loc.get('seasons','-')} | 场合: {loc.get('occasions','-')}")

    elif cmd == "get":
        location_id = sys.argv[2] if len(sys.argv) > 2 else input("location_id: ")
        loc = location_get(location_id)
        if loc:
            print(f"\n📍 分类详情:")
            for k, v in loc.items():
                if v:
                    print(f"   {k}: {v}")
        else:
            print("未找到")

    elif cmd == "update":
        location_id = sys.argv[2] if len(sys.argv) > 2 else input("location_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        location_update(location_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        location_id = sys.argv[2] if len(sys.argv) > 2 else input("location_id: ")
        confirm = input("确认删除？(y/n): ")
        if confirm.lower() == 'y':
            location_delete(location_id)
            print("✅ 已删除")

    elif cmd == "query-cuisine":
        cuisine = sys.argv[2] if len(sys.argv) > 2 else input("菜系: ")
        recipes = query_by_cuisine(cuisine)
        print(f"\n🍜 {cuisine}食谱 ({len(recipes)}道):")
        for r in recipes:
            print(f"  • {r['name']}")

    elif cmd == "query-season":
        season = sys.argv[2] if len(sys.argv) > 2 else input("季节: ")
        recipes = query_by_season(season)
        print(f"\n🌡️ {season}食谱 ({len(recipes)}道):")
        for r in recipes:
            print(f"  • {r['name']}")

    elif cmd == "query-occasion":
        occasion = sys.argv[2] if len(sys.argv) > 2 else input("场合: ")
        recipes = query_by_occasion(occasion)
        print(f"\n🎉 {occasion}食谱 ({len(recipes)}道):")
        for r in recipes:
            print(f"  • {r['name']}")

    elif cmd == "query-flavor":
        flavor = sys.argv[2] if len(sys.argv) > 2 else input("口味: ")
        recipes = query_by_flavor(flavor)
        print(f"\n👅 {flavor}口味食谱 ({len(recipes)}道):")
        for r in recipes:
            print(f"  • {r['name']}")


if __name__ == "__main__":
    main()