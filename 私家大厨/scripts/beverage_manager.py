#!/usr/bin/env python3
"""
私家大厨 - 饮品搭配管理脚本 v1.0
对应表：beverage_pairings（19字段）
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


def beverage_add(
    recipe_id,
    pairing_type=None,
    beverage_name=None,
    beverage_category=None,
    pairing_reason=None,
    flavor_match=None,
    temperature=None,
    brand_recommendation=None,
    price_range=None,
    substitute_options=None,
    occasion_suitability=None,
    region_tradition=None,
    notes=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """添加饮品搭配（19字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    beverage_id = str(uuid.uuid4())
    now = _now()

    cursor.execute('''
        INSERT INTO beverage_pairings (
            id, recipe_id, pairing_type, beverage_name, beverage_category,
            pairing_reason, flavor_match, temperature, brand_recommendation,
            price_range, substitute_options, occasion_suitability,
            region_tradition, notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        beverage_id, recipe_id, pairing_type, beverage_name, beverage_category,
        pairing_reason, flavor_match, temperature, brand_recommendation,
        price_range, _json(substitute_options), occasion_suitability,
        region_tradition, notes,
        now, now
    ])

    conn.commit()
    conn.close()
    return beverage_id


def beverage_list(recipe_id, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM beverage_pairings WHERE recipe_id = ?", (recipe_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        if r.get('substitute_options'):
            try: r['substitute_options'] = json.loads(r['substitute_options'])
            except: pass
    return rows


def beverage_get(beverage_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM beverage_pairings WHERE id = ?", (beverage_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def beverage_update(
    beverage_id,
    recipe_id=None,
    pairing_type=None,
    beverage_name=None,
    beverage_category=None,
    pairing_reason=None,
    flavor_match=None,
    temperature=None,
    brand_recommendation=None,
    price_range=None,
    substitute_options=None,
    occasion_suitability=None,
    region_tradition=None,
    notes=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """更新饮品搭配（显式19字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    fields = {}
    if recipe_id is not None: fields['recipe_id'] = recipe_id
    if pairing_type is not None: fields['pairing_type'] = pairing_type
    if beverage_name is not None: fields['beverage_name'] = beverage_name
    if beverage_category is not None: fields['beverage_category'] = beverage_category
    if pairing_reason is not None: fields['pairing_reason'] = pairing_reason
    if flavor_match is not None: fields['flavor_match'] = flavor_match
    if temperature is not None: fields['temperature'] = temperature
    if brand_recommendation is not None: fields['brand_recommendation'] = brand_recommendation
    if price_range is not None: fields['price_range'] = price_range
    if substitute_options is not None: fields['substitute_options'] = _json(substitute_options)
    if occasion_suitability is not None: fields['occasion_suitability'] = occasion_suitability
    if region_tradition is not None: fields['region_tradition'] = region_tradition
    if notes is not None: fields['notes'] = notes
    if created_at is not None: fields['created_at'] = created_at
    if updated_at is not None: fields['updated_at'] = updated_at

    if not fields:
        conn.close()
        return False

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [beverage_id]
    cursor.execute(f"UPDATE beverage_pairings SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def beverage_delete(beverage_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM beverage_pairings WHERE id = ?", (beverage_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python beverage_manager.py add <recipe_id> [--field value ...]")
        print("  python beverage_manager.py list <recipe_id>")
        print("  python beverage_manager.py get <beverage_id>")
        print("  python beverage_manager.py update <beverage_id> [--field value ...]")
        print("  python beverage_manager.py delete <beverage_id>")
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
        beverage_id = beverage_add(recipe_id, **fields)
        print(f"✅ 饮品搭配已添加 (ID: {beverage_id})")

    elif cmd == "list":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        items = beverage_list(recipe_id)
        if not items:
            print("暂无饮品搭配")
        else:
            print(f"\n🍷 {len(items)}种搭配:")
            for b in items:
                print(f"  • {b.get('beverage_name','?')} | {b.get('pairing_type','?')} | {b.get('temperature','?')}")

    elif cmd == "get":
        beverage_id = sys.argv[2] if len(sys.argv) > 2 else input("beverage_id: ")
        b = beverage_get(beverage_id)
        if b:
            print(f"\n🍷 {b.get('beverage_name','?')}")
            for k, v in b.items():
                if v:
                    print(f"   {k}: {v}")

    elif cmd == "update":
        beverage_id = sys.argv[2] if len(sys.argv) > 2 else input("beverage_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        beverage_update(beverage_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        beverage_id = sys.argv[2] if len(sys.argv) > 2 else input("beverage_id: ")
        confirm = input("确认删除？(y/n): ")
        if confirm.lower() == 'y':
            beverage_delete(beverage_id)
            print("✅ 已删除")


if __name__ == "__main__":
    main()