#!/usr/bin/env python3
"""
私家大厨 - 食材管理脚本 v1.0
对应表：ingredients（28字段）
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


def ingredient_add(
    recipe_id,
    name,
    sequence=None,
    category=None,
    quantity=None,
    quantity_text=None,
    unit=None,
    state=None,
    size=None,
    cut_style=None,
    quality_grade=None,
    brand=None,
    purchase_place=None,
    supermarkets=None,
    price_per_unit=None,
    purchase_specs=None,
    storage_type=None,
    frozen_ok=None,
    shelf_life_days=None,
    prepped_storage=None,
    is_optional=None,
    is_staple=None,
    substitute=None,
    substitute_notes=None,
    introduced_method=None,
    notes=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """添加食材（28字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    ingredient_id = str(uuid.uuid4())
    now = _now()

    cursor.execute('''
        INSERT INTO ingredients (
            id, recipe_id, sequence, name, category,
            quantity, quantity_text, unit, state, size, cut_style,
            quality_grade, brand, purchase_place, supermarkets,
            price_per_unit, purchase_specs, storage_type,
            frozen_ok, shelf_life_days, prepped_storage,
            is_optional, is_staple, substitute, substitute_notes,
            introduced_method, notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        ingredient_id, recipe_id, sequence, name, category,
        quantity, quantity_text, unit, _json(state), _json(size), _json(cut_style),
        quality_grade, brand, purchase_place, _json(supermarkets),
        price_per_unit, purchase_specs, storage_type,
        1 if frozen_ok else 0, shelf_life_days, prepped_storage,
        1 if is_optional else 0, 1 if is_staple else 0, substitute, substitute_notes,
        introduced_method, notes, now, now
    ])

    conn.commit()
    conn.close()
    return ingredient_id


def ingredient_update(
    ingredient_id,
    recipe_id=None,
    sequence=None,
    name=None,
    category=None,
    quantity=None,
    quantity_text=None,
    unit=None,
    state=None,
    size=None,
    cut_style=None,
    quality_grade=None,
    brand=None,
    purchase_place=None,
    supermarkets=None,
    price_per_unit=None,
    purchase_specs=None,
    storage_type=None,
    frozen_ok=None,
    shelf_life_days=None,
    prepped_storage=None,
    is_optional=None,
    is_staple=None,
    substitute=None,
    substitute_notes=None,
    introduced_method=None,
    notes=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """更新食材（28字段显式）"""
    conn = get_conn()
    cursor = conn.cursor()

    fields = {}
    if recipe_id is not None: fields['recipe_id'] = recipe_id
    if sequence is not None: fields['sequence'] = sequence
    if name is not None: fields['name'] = name
    if category is not None: fields['category'] = category
    if quantity is not None: fields['quantity'] = quantity
    if quantity_text is not None: fields['quantity_text'] = quantity_text
    if unit is not None: fields['unit'] = unit
    if state is not None: fields['state'] = _json(state)
    if size is not None: fields['size'] = _json(size)
    if cut_style is not None: fields['cut_style'] = _json(cut_style)
    if quality_grade is not None: fields['quality_grade'] = quality_grade
    if brand is not None: fields['brand'] = brand
    if purchase_place is not None: fields['purchase_place'] = purchase_place
    if supermarkets is not None: fields['supermarkets'] = _json(supermarkets)
    if price_per_unit is not None: fields['price_per_unit'] = price_per_unit
    if purchase_specs is not None: fields['purchase_specs'] = purchase_specs
    if storage_type is not None: fields['storage_type'] = storage_type
    if frozen_ok is not None: fields['frozen_ok'] = 1 if frozen_ok else 0
    if shelf_life_days is not None: fields['shelf_life_days'] = shelf_life_days
    if prepped_storage is not None: fields['prepped_storage'] = prepped_storage
    if is_optional is not None: fields['is_optional'] = 1 if is_optional else 0
    if is_staple is not None: fields['is_staple'] = 1 if is_staple else 0
    if substitute is not None: fields['substitute'] = substitute
    if substitute_notes is not None: fields['substitute_notes'] = substitute_notes
    if introduced_method is not None: fields['introduced_method'] = introduced_method
    if notes is not None: fields['notes'] = notes
    if created_at is not None: fields['created_at'] = created_at
    if updated_at is not None: fields['updated_at'] = updated_at

    if not fields:
        conn.close()
        return False

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [ingredient_id]
    cursor.execute(f"UPDATE ingredients SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def ingredient_list(recipe_id, limit=100):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY sequence",
        (recipe_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        for f in ['supermarkets', 'state', 'size', 'cut_style']:
            if r.get(f):
                try: r[f] = json.loads(r[f])
                except: pass
    return rows


def ingredient_get(ingredient_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def ingredient_delete(ingredient_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python ingredient_manager.py add <recipe_id> <食材名> [--field value ...]")
        print("  python ingredient_manager.py list <recipe_id>")
        print("  python ingredient_manager.py get <ingredient_id>")
        print("  python ingredient_manager.py update <ingredient_id> [--field value ...]")
        print("  python ingredient_manager.py delete <ingredient_id>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        name = sys.argv[3] if len(sys.argv) > 3 else input("食材名: ")
        args = sys.argv[4:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        ingredient_id = ingredient_add(recipe_id, name, **fields)
        print(f"✅ 食材已添加: {name} (ID: {ingredient_id})")

    elif cmd == "list":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        items = ingredient_list(recipe_id)
        if not items:
            print("暂无食材")
        else:
            print(f"\n🥘 {len(items)}种食材:")
            for ing in items:
                qty = f"{ing['quantity']}{ing.get('unit','g')}" if ing.get('quantity') else ing.get('quantity_text','')
                print(f"  - {ing['name']} {qty} | {ing.get('category','-')}")

    elif cmd == "get":
        ingredient_id = sys.argv[2] if len(sys.argv) > 2 else input("ingredient_id: ")
        ing = ingredient_get(ingredient_id)
        if not ing:
            print("未找到")
        else:
            print(f"\n🥘 {ing['name']}")
            for k, v in ing.items():
                if v:
                    print(f"  {k}: {v}")

    elif cmd == "update":
        ingredient_id = sys.argv[2] if len(sys.argv) > 2 else input("ingredient_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        ingredient_update(ingredient_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        ingredient_id = sys.argv[2] if len(sys.argv) > 2 else input("ingredient_id: ")
        confirm = input("确认删除？(y/n): ")
        if confirm.lower() == 'y':
            ingredient_delete(ingredient_id)
            print("✅ 已删除")


if __name__ == "__main__":
    main()