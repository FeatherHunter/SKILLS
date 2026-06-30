#!/usr/bin/env python3
"""食品库 — 营养成分表 CRUD

数据存储：nutrition_products 表
- 每 100g 的营养数据（calories/protein/fat/saturated_fat/carbohydrates/sugar/dietary_fiber/sodium）
- product_name / brand 双字段搜索

使用流程：
1. 查热量（search_products）→ 找到匹配
2. 存食品（add_product）→ 录入新营养表
3. 改食品（update_product）→ 更新字段
4. 查食品库（list_products）→ 列出全部
"""

import sys
from pathlib import Path

from db import find_db_path, get_db, init_db

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def _get_db():
    if not DB_PATH.exists():
        init_db(DB_PATH)
    return get_db(DB_PATH)


def add_product(product_name, brand, calories, protein, fat, saturated_fat,
                carbohydrates, sugar, dietary_fiber, sodium, note=''):
    """添加一条食品营养成分记录

    Args:
        product_name: 产品名
        brand: 品牌
        calories: 热量（千卡/100g）
        protein: 蛋白质（克/100g）
        fat: 脂肪（克/100g）
        saturated_fat: 饱和脂肪（克/100g）
        carbohydrates: 碳水（克/100g）
        sugar: 糖（克/100g）
        dietary_fiber: 膳食纤维（克/100g）
        sodium: 钠（毫克/100g）
        note: 备注
    """
    try:
        conn = _get_db()
        c = conn.cursor()

        c.execute('''
            INSERT INTO nutrition_products
            (product_name, brand, calories, protein, fat, saturated_fat, carbohydrates, sugar, dietary_fiber, sodium, note)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (product_name, brand, calories, protein, fat, saturated_fat,
              carbohydrates, sugar, dietary_fiber, sodium, note))

        product_id = c.lastrowid
        conn.commit()
        conn.close()

        print(f"✓ 已添加营养成分表：{product_name}")
        print(f"  品牌：{brand or '-'}")
        print(f"  热量：{calories}千卡/100g")
        print(f"  蛋白质：{protein}克 | 脂肪：{fat}克 | 碳水：{carbohydrates}克")
        print(f"  饱和脂肪：{saturated_fat or '-'}克 | 糖：{sugar or '-'}克 | 膳食纤维：{dietary_fiber or '-'}克")
        print(f"  钠：{sodium}毫克")
        if note:
            print(f"  备注：{note}")
        print(f"  ID：{product_id}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def search_products(keyword):
    """模糊搜索食品营养成分（按 product_name 或 brand）

    Returns:
        list of Row: 匹配记录
    """
    conn = _get_db()
    c = conn.cursor()

    c.execute('''
        SELECT id, product_name, brand, calories, protein, fat, saturated_fat,
               carbohydrates, sugar, dietary_fiber, sodium, note, updated_at
        FROM nutrition_products
        WHERE is_deprecated = 0 AND (product_name LIKE ? OR brand LIKE ?)
        ORDER BY product_name
    ''', (f'%{keyword}%', f'%{keyword}%'))

    rows = c.fetchall()
    conn.close()

    if not rows:
        print(f"未找到包含「{keyword}」的食品")
        return []

    print(f"\n找到 {len(rows)} 个匹配的食品：")
    print("-" * 90)
    print(f"{'ID':>3} | {'产品名称':20} | {'品牌':10} | {'热量':>5} | {'蛋白':>5} | {'脂':>4} | {'碳':>5} | {'钠':>6} | 更新日期")
    print("-" * 90)

    for row in rows:
        id_, name, brand, cal, pro, fat_, sat_fat, carb, sugar, fiber, sodium, note, updated = row
        brand = brand or '-'
        print(f"{id_:>3} | {name:20} | {brand:10} | {cal:>5} | {pro:>5} | {fat_:>4} | {carb:>5} | {sodium:>6} | {updated[:10]}")

    print("-" * 90)
    return rows


def update_product(product_id, **kwargs):
    """更新食品营养成分

    Args:
        product_id: 产品 ID
        **kwargs: 字段名=新值，支持：
            product_name / brand / calories / protein / fat /
            saturated_fat / carbohydrates / sugar / dietary_fiber /
            sodium / note

    Returns:
        bool
    """
    allowed_fields = ['product_name', 'brand', 'calories', 'protein', 'fat',
                      'saturated_fat', 'carbohydrates', 'sugar', 'dietary_fiber',
                      'sodium', 'note']

    update_data = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

    if not update_data:
        print("Error: No valid fields to update")
        return False

    if not product_id:
        print("Error: Product ID is required")
        return False

    conn = _get_db()
    c = conn.cursor()

    c.execute('SELECT product_name FROM nutrition_products WHERE id = ?', (product_id,))
    row = c.fetchone()
    if not row:
        print(f"Error: Product ID {product_id} not found")
        conn.close()
        return False

    old_name = row[0]

    set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
    set_clause += ", updated_at = CURRENT_TIMESTAMP"
    values = list(update_data.values())
    values.append(product_id)

    c.execute(f'UPDATE nutrition_products SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()

    print(f"✓ 已更新「{old_name}」营养成分表")
    for k, v in update_data.items():
        print(f"  {k}: {v}")
    return True


def list_products(limit=50):
    """列出所有食品营养成分（按更新时间倒序）

    Args:
        limit: 最多显示条数，默认 50
    """
    conn = _get_db()
    c = conn.cursor()

    c.execute('''
        SELECT id, product_name, brand, calories, protein, fat, saturated_fat,
               carbohydrates, sugar, dietary_fiber, sodium, note, created_at
        FROM nutrition_products
        WHERE is_deprecated = 0
        ORDER BY updated_at DESC
        LIMIT ?
    ''', (limit,))

    rows = c.fetchall()
    conn.close()

    if not rows:
        print("营养成分库为空，请先添加食品营养成分")
        return []

    print(f"\n食品营养成分库（共{len(rows)}条）：")
    print("-" * 90)
    print(f"{'ID':>3} | {'产品名称':20} | {'品牌':10} | {'热量':>5} | {'蛋白':>5} | {'脂':>4} | {'碳':>5} | {'钠':>6}")
    print("-" * 90)

    for row in rows:
        id_, name, brand, cal, pro, fat_, sat_fat, carb, sugar, fiber, sodium, note, created = row
        brand = brand or '-'
        print(f"{id_:>3} | {name:20} | {brand:10} | {cal:>5} | {pro:>5} | {fat_:>4} | {carb:>5} | {sodium:>6}")

    print("-" * 90)
    return rows