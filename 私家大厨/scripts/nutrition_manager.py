#!/usr/bin/env python3
"""
私家大厨 - 营养信息管理脚本 v1.0
对应表：nutrition_info（48字段）
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


def nutrition_add(
    recipe_id,
    serving_size=None,
    serving_unit=None,
    servings_total=None,
    calories_kcal=None,
    calories_per_serving=None,
    protein_grams=None,
    fat_grams=None,
    saturated_fat_g=None,
    trans_fat_g=None,
    carbohydrates_grams=None,
    fiber_grams=None,
    sugar_grams=None,
    added_sugar_g=None,
    sodium_mg=None,
    cholesterol_mg=None,
    vitamin_a_mcg=None,
    vitamin_b1_mg=None,
    vitamin_b2_mg=None,
    vitamin_b3_mg=None,
    vitamin_c_mg=None,
    vitamin_d_mcg=None,
    vitamin_e_mg=None,
    calcium_mg=None,
    iron_mg=None,
    zinc_mg=None,
    magnesium_mg=None,
    potassium_mg=None,
    selenium_mcg=None,
    calculation_method=None,
    data_source=None,
    is_estimated=None,
    confidence_level=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """添加营养信息（48字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    nutrition_id = str(uuid.uuid4())
    now = _now()

    cursor.execute('''
        INSERT INTO nutrition_info (
            id, recipe_id, serving_size, serving_unit, servings_total,
            calories_kcal, calories_per_serving,
            protein_grams, fat_grams, saturated_fat_g, trans_fat_g,
            carbohydrates_grams, fiber_grams, sugar_grams, added_sugar_g,
            sodium_mg, cholesterol_mg,
            vitamin_a_mcg, vitamin_b1_mg, vitamin_b2_mg, vitamin_b3_mg,
            vitamin_c_mg, vitamin_d_mcg, vitamin_e_mg,
            calcium_mg, iron_mg, zinc_mg, magnesium_mg, potassium_mg, selenium_mcg,
            calculation_method, data_source,
            is_estimated, confidence_level,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        nutrition_id, recipe_id, serving_size, serving_unit, servings_total,
        calories_kcal, calories_per_serving,
        protein_grams, fat_grams, saturated_fat_g, trans_fat_g,
        carbohydrates_grams, fiber_grams, sugar_grams, added_sugar_g,
        sodium_mg, cholesterol_mg,
        vitamin_a_mcg, vitamin_b1_mg, vitamin_b2_mg, vitamin_b3_mg,
        vitamin_c_mg, vitamin_d_mcg, vitamin_e_mg,
        calcium_mg, iron_mg, zinc_mg, magnesium_mg, potassium_mg, selenium_mcg,
        calculation_method, data_source,
        1 if is_estimated else 0, confidence_level,
        now, now
    ])

    conn.commit()
    conn.close()
    return nutrition_id


def nutrition_list(recipe_id=None, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    if recipe_id:
        cursor.execute("SELECT * FROM nutrition_info WHERE recipe_id = ?", (recipe_id,))
    else:
        cursor.execute("SELECT * FROM nutrition_info LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def nutrition_get(nutrition_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM nutrition_info WHERE id = ?", (nutrition_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def nutrition_update(
    nutrition_id,
    recipe_id=None,
    serving_size=None,
    serving_unit=None,
    servings_total=None,
    calories_kcal=None,
    calories_per_serving=None,
    protein_grams=None,
    fat_grams=None,
    saturated_fat_g=None,
    trans_fat_g=None,
    carbohydrates_grams=None,
    fiber_grams=None,
    sugar_grams=None,
    added_sugar_g=None,
    sodium_mg=None,
    cholesterol_mg=None,
    vitamin_a_mcg=None,
    vitamin_b1_mg=None,
    vitamin_b2_mg=None,
    vitamin_b3_mg=None,
    vitamin_c_mg=None,
    vitamin_d_mcg=None,
    vitamin_e_mg=None,
    calcium_mg=None,
    iron_mg=None,
    zinc_mg=None,
    magnesium_mg=None,
    potassium_mg=None,
    selenium_mcg=None,
    calculation_method=None,
    data_source=None,
    is_estimated=None,
    confidence_level=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """更新营养信息（显式48字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    fields = {}
    if recipe_id is not None: fields['recipe_id'] = recipe_id
    if serving_size is not None: fields['serving_size'] = serving_size
    if serving_unit is not None: fields['serving_unit'] = serving_unit
    if servings_total is not None: fields['servings_total'] = servings_total
    if calories_kcal is not None: fields['calories_kcal'] = calories_kcal
    if calories_per_serving is not None: fields['calories_per_serving'] = calories_per_serving
    if protein_grams is not None: fields['protein_grams'] = protein_grams
    if fat_grams is not None: fields['fat_grams'] = fat_grams
    if saturated_fat_g is not None: fields['saturated_fat_g'] = saturated_fat_g
    if trans_fat_g is not None: fields['trans_fat_g'] = trans_fat_g
    if carbohydrates_grams is not None: fields['carbohydrates_grams'] = carbohydrates_grams
    if fiber_grams is not None: fields['fiber_grams'] = fiber_grams
    if sugar_grams is not None: fields['sugar_grams'] = sugar_grams
    if added_sugar_g is not None: fields['added_sugar_g'] = added_sugar_g
    if sodium_mg is not None: fields['sodium_mg'] = sodium_mg
    if cholesterol_mg is not None: fields['cholesterol_mg'] = cholesterol_mg
    if vitamin_a_mcg is not None: fields['vitamin_a_mcg'] = vitamin_a_mcg
    if vitamin_b1_mg is not None: fields['vitamin_b1_mg'] = vitamin_b1_mg
    if vitamin_b2_mg is not None: fields['vitamin_b2_mg'] = vitamin_b2_mg
    if vitamin_b3_mg is not None: fields['vitamin_b3_mg'] = vitamin_b3_mg
    if vitamin_c_mg is not None: fields['vitamin_c_mg'] = vitamin_c_mg
    if vitamin_d_mcg is not None: fields['vitamin_d_mcg'] = vitamin_d_mcg
    if vitamin_e_mg is not None: fields['vitamin_e_mg'] = vitamin_e_mg
    if calcium_mg is not None: fields['calcium_mg'] = calcium_mg
    if iron_mg is not None: fields['iron_mg'] = iron_mg
    if zinc_mg is not None: fields['zinc_mg'] = zinc_mg
    if magnesium_mg is not None: fields['magnesium_mg'] = magnesium_mg
    if potassium_mg is not None: fields['potassium_mg'] = potassium_mg
    if selenium_mcg is not None: fields['selenium_mcg'] = selenium_mcg
    if calculation_method is not None: fields['calculation_method'] = calculation_method
    if data_source is not None: fields['data_source'] = data_source
    if is_estimated is not None: fields['is_estimated'] = 1 if is_estimated else 0
    if confidence_level is not None: fields['confidence_level'] = confidence_level
    if created_at is not None: fields['created_at'] = created_at
    if updated_at is not None: fields['updated_at'] = updated_at

    if not fields:
        conn.close()
        return False

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [nutrition_id]
    cursor.execute(f"UPDATE nutrition_info SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def nutrition_delete(nutrition_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM nutrition_info WHERE id = ?", (nutrition_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python nutrition_manager.py add <recipe_id> [--field value ...]")
        print("  python nutrition_manager.py list [recipe_id]")
        print("  python nutrition_manager.py get <nutrition_id>")
        print("  python nutrition_manager.py update <nutrition_id> [--field value ...]")
        print("  python nutrition_manager.py delete <nutrition_id>")
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
        nutrition_id = nutrition_add(recipe_id, **fields)
        print(f"✅ 营养信息已添加 (ID: {nutrition_id})")

    elif cmd == "list":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else None
        items = nutrition_list(recipe_id)
        if not items:
            print("暂无营养信息")
        else:
            print(f"\n📊 {len(items)}条营养记录:")
            for n in items:
                cal = n.get('calories_per_serving', n.get('calories_kcal', '?'))
                print(f"  • {n['recipe_id'][:8]}... 热量:{cal}kcal")

    elif cmd == "get":
        nutrition_id = sys.argv[2] if len(sys.argv) > 2 else input("nutrition_id: ")
        n = nutrition_get(nutrition_id)
        if n:
            print(f"\n📊 营养详情:")
            print(f"  热量: {n.get('calories_per_serving', n.get('calories_kcal','?'))} kcal/份")
            print(f"  蛋白质: {n.get('protein_grams','?')}g | 脂肪: {n.get('fat_grams','?')}g | 碳水: {n.get('carbohydrates_grams','?')}g")

    elif cmd == "update":
        nutrition_id = sys.argv[2] if len(sys.argv) > 2 else input("nutrition_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        nutrition_update(nutrition_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        nutrition_id = sys.argv[2] if len(sys.argv) > 2 else input("nutrition_id: ")
        confirm = input("确认删除？(y/n): ")
        if confirm.lower() == 'y':
            nutrition_delete(nutrition_id)
            print("✅ 已删除")


if __name__ == "__main__":
    main()