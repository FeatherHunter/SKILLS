#!/usr/bin/env python3
"""
私家大厨 - 食谱管理脚本 v1.0
对应表：recipes（35字段）
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


def recipe_add(
    name,
    internal_code=None,
    name_aliases=None,
    description=None,
    appearance_desc=None,
    taste_desc=None,
    texture_desc=None,
    time_total_minutes=None,
    time_prep_minutes=None,
    time_cook_minutes=None,
    time_cleanup_minutes=None,
    difficulty=None,
    difficulty_user=None,
    servings=None,
    recipe_version=None,
    parent_recipe_id=None,
    is_reference=None,
    status=None,
    times_cooked=None,
    user_rating=None,
    user_feedback=None,
    want_to_cook_level=None,
    is_favorite=None,
    is_staple=None,
    cost_per_serving=None,
    source_url=None,
    source_author=None,
    video_url=None,
    photo_urls=None,
    keywords=None,
    notes=None,

    energy_level=None,
    **kwargs
):
    """添加食谱（35字段全量）"""
    conn = get_conn()
    cursor = conn.cursor()

    recipe_id = str(uuid.uuid4())
    now = _now()

    cursor.execute('''
        INSERT INTO recipes (
            id, internal_code, name, name_aliases,
            description, appearance_desc, taste_desc, texture_desc,
            time_total_minutes, time_prep_minutes, time_cook_minutes, time_cleanup_minutes,
            difficulty, difficulty_user, servings,
            recipe_version, parent_recipe_id, is_reference,
            status, times_cooked, user_rating, user_feedback,
            want_to_cook_level, is_favorite, is_staple, cost_per_serving,
            created_at, updated_at,
            source_url, source_author, video_url, photo_urls,
            keywords, notes, energy_level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        recipe_id, internal_code, name, name_aliases,
        description, appearance_desc, taste_desc, texture_desc,
        time_total_minutes, time_prep_minutes, time_cook_minutes, time_cleanup_minutes,
        difficulty, difficulty_user, servings,
        recipe_version, parent_recipe_id, 1 if is_reference else 0,
        status or '未做', times_cooked or 0, user_rating, user_feedback,
        want_to_cook_level, 1 if is_favorite else 0, 1 if is_staple else 0, cost_per_serving,
        now, now,
        source_url, source_author, video_url, _json(photo_urls),
        _json(keywords), notes, energy_level
    ])

    conn.commit()
    conn.close()
    return recipe_id


def recipe_show(name_or_id):
    """查看食谱详情"""
    conn = get_conn()
    cursor = conn.cursor()

    if name_or_id and '-' in name_or_id:
        cursor.execute("SELECT * FROM recipes WHERE id = ?", (name_or_id,))
    else:
        cursor.execute("SELECT * FROM recipes WHERE name = ?", (name_or_id,))

    recipe = cursor.fetchone()
    if not recipe:
        conn.close()
        return None

    result = dict(recipe)

    cursor.execute("SELECT * FROM ingredients WHERE recipe_id = ? ORDER BY sequence", (result['id'],))
    result['ingredients'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM cooking_steps WHERE recipe_id = ? ORDER BY sequence", (result['id'],))
    steps = [dict(r) for r in cursor.fetchall()]
    for s in steps:
        for f in ['tools', 'common_mistakes', 'mistake_causes', 'mistake_fixes', 'warnings']:
            if s.get(f):
                try: s[f] = json.loads(s[f])
                except: pass
    result['steps'] = steps

    cursor.execute("SELECT * FROM recipe_locations WHERE recipe_id = ?", (result['id'],))
    result['location'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM tips WHERE recipe_id = ?", (result['id'],))
    result['tips'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM recipe_history WHERE recipe_id = ? ORDER BY cook_date DESC", (result['id'],))
    result['history'] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT * FROM nutrition_info WHERE recipe_id = ?", (result['id'],))
    row = cursor.fetchone()
    result['nutrition'] = dict(row) if row else None

    cursor.execute("SELECT * FROM background_knowledge WHERE recipe_id = ?", (result['id'],))
    row = cursor.fetchone()
    result['background'] = dict(row) if row else None

    cursor.execute("SELECT * FROM beverage_pairings WHERE recipe_id = ?", (result['id'],))
    result['beverages'] = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return result


def recipe_list(difficulty=None, status=None, limit=50):
    """列出食谱"""
    conn = get_conn()
    cursor = conn.cursor()
    conditions = []
    params = []

    if difficulty:
        conditions.append("difficulty = ?")
        params.append(difficulty)
    if status:
        conditions.append("status = ?")
        params.append(status)

    where = " AND ".join(conditions) if conditions else "1=1"
    cursor.execute(f"SELECT * FROM recipes WHERE {where} ORDER BY updated_at DESC LIMIT ?", params + [limit])
    recipes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return recipes


def recipe_update(
    recipe_id,
    internal_code=None,
    name=None,
    name_aliases=None,
    description=None,
    appearance_desc=None,
    taste_desc=None,
    texture_desc=None,
    time_total_minutes=None,
    time_prep_minutes=None,
    time_cook_minutes=None,
    time_cleanup_minutes=None,
    difficulty=None,
    difficulty_user=None,
    servings=None,
    recipe_version=None,
    parent_recipe_id=None,
    is_reference=None,
    status=None,
    times_cooked=None,
    user_rating=None,
    user_feedback=None,
    want_to_cook_level=None,
    is_favorite=None,
    is_staple=None,
    cost_per_serving=None,
    source_url=None,
    source_author=None,
    video_url=None,
    photo_urls=None,
    keywords=None,
    notes=None,

    energy_level=None,
    **kwargs
):
    """更新食谱（35字段全量）"""
    conn = get_conn()
    cursor = conn.cursor()

    fields = {}
    if internal_code is not None: fields['internal_code'] = internal_code
    if name is not None: fields['name'] = name
    if name_aliases is not None: fields['name_aliases'] = name_aliases
    if description is not None: fields['description'] = description
    if appearance_desc is not None: fields['appearance_desc'] = appearance_desc
    if taste_desc is not None: fields['taste_desc'] = taste_desc
    if texture_desc is not None: fields['texture_desc'] = texture_desc
    if time_total_minutes is not None: fields['time_total_minutes'] = time_total_minutes
    if time_prep_minutes is not None: fields['time_prep_minutes'] = time_prep_minutes
    if time_cook_minutes is not None: fields['time_cook_minutes'] = time_cook_minutes
    if time_cleanup_minutes is not None: fields['time_cleanup_minutes'] = time_cleanup_minutes
    if difficulty is not None: fields['difficulty'] = difficulty
    if difficulty_user is not None: fields['difficulty_user'] = difficulty_user
    if servings is not None: fields['servings'] = servings
    if recipe_version is not None: fields['recipe_version'] = recipe_version
    if parent_recipe_id is not None: fields['parent_recipe_id'] = parent_recipe_id
    if is_reference is not None: fields['is_reference'] = 1 if is_reference else 0
    if status is not None: fields['status'] = status
    if times_cooked is not None: fields['times_cooked'] = times_cooked
    if user_rating is not None: fields['user_rating'] = user_rating
    if user_feedback is not None: fields['user_feedback'] = user_feedback
    if want_to_cook_level is not None: fields['want_to_cook_level'] = want_to_cook_level
    if is_favorite is not None: fields['is_favorite'] = 1 if is_favorite else 0
    if is_staple is not None: fields['is_staple'] = 1 if is_staple else 0
    if cost_per_serving is not None: fields['cost_per_serving'] = cost_per_serving
    if source_url is not None: fields['source_url'] = source_url
    if source_author is not None: fields['source_author'] = source_author
    if video_url is not None: fields['video_url'] = video_url
    if photo_urls is not None: fields['photo_urls'] = _json(photo_urls)
    if keywords is not None: fields['keywords'] = _json(keywords)
    if notes is not None: fields['notes'] = notes
    if energy_level is not None: fields['energy_level'] = energy_level

    fields['updated_at'] = _now()

    if not fields:
        conn.close()
        return False

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [recipe_id]
    cursor.execute(f"UPDATE recipes SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def recipe_delete(recipe_id):
    """删除食谱（含级联清理）"""
    conn = get_conn()
    cursor = conn.cursor()
    for table in ['tips', 'recipe_history', 'nutrition_info', 'background_knowledge',
                  'beverage_pairings', 'recipe_locations', 'ingredient_preparations',
                  'ingredients', 'cooking_steps']:
        cursor.execute(f"DELETE FROM {table} WHERE recipe_id = ?", (recipe_id,))
    cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def recipe_lint(recipe_id):
    """检查食谱完整性"""
    conn = get_conn()
    cursor = conn.cursor()
    issues = []

    cursor.execute("SELECT name FROM recipes WHERE id = ?", (recipe_id,))
    if not cursor.fetchone():
        issues.append("食谱不存在")
        conn.close()
        return issues

    cursor.execute("SELECT COUNT(*) FROM ingredients WHERE recipe_id = ?", (recipe_id,))
    if cursor.fetchone()[0] == 0:
        issues.append("缺少食材")

    cursor.execute("SELECT COUNT(*) FROM cooking_steps WHERE recipe_id = ?", (recipe_id,))
    if cursor.fetchone()[0] == 0:
        issues.append("缺少烹饪步骤")

    cursor.execute("SELECT COUNT(*) FROM recipe_locations WHERE recipe_id = ?", (recipe_id,))
    if cursor.fetchone()[0] == 0:
        issues.append("缺少地区分类")

    conn.close()
    return issues


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python recipe_manager.py add <菜名> [--field value ...]")
        print("  python recipe_manager.py show <菜名或ID>")
        print("  python recipe_manager.py list")
        print("  python recipe_manager.py update <recipe_id> [--field value ...]")
        print("  python recipe_manager.py delete <recipe_id>")
        print("  python recipe_manager.py lint <recipe_id>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        name = sys.argv[2] if len(sys.argv) > 2 else input("菜名: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        recipe_id = recipe_add(name, **fields)
        print(f"✅ 食谱已添加: {name} (ID: {recipe_id})")

    elif cmd == "show":
        name = sys.argv[2] if len(sys.argv) > 2 else input("菜名: ")
        recipe = recipe_show(name)
        if not recipe:
            print(f"❌ 未找到食谱: {name}")
            sys.exit(1)
        print(f"\n{'='*60}")
        print(f"📖 {recipe['name']}")
        print(f"{'='*60}")
        print(f"难度: {recipe.get('difficulty', '-')} | 时间: {recipe.get('time_total_minutes', '-')}分钟 | 状态: {recipe.get('status', '-')}")
        print(f"描述: {recipe.get('description', '-')}")
        if recipe.get('ingredients'):
            print(f"\n🥘 食材 ({len(recipe['ingredients'])}种):")
            for ing in recipe['ingredients']:
                qty = f"{ing['quantity']}{ing.get('unit','g')}" if ing.get('quantity') else ''
                print(f"  - {ing['name']} {qty}")
        if recipe.get('steps'):
            print(f"\n📝 步骤 ({len(recipe['steps'])}步):")
            for step in recipe['steps']:
                print(f"  {step['sequence']}. {step['action']}")
        if recipe.get('tips'):
            print(f"\n💡 小贴士:")
            for tip in recipe['tips']:
                print(f"  [{tip['category']}] {tip['content']}")

    elif cmd == "list":
        recipes = recipe_list(limit=100)
        if not recipes:
            print("暂无食谱")
        else:
            print(f"\n共 {len(recipes)} 道菜:")
            for r in recipes:
                print(f"  • {r['name']} | {r.get('difficulty','-')} | {r.get('status','-')} | {r.get('times_cooked',0)}次")

    elif cmd == "update":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        recipe_update(recipe_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        confirm = input("确认删除（含所有子表数据）？(y/n): ")
        if confirm.lower() == 'y':
            recipe_delete(recipe_id)
            print("✅ 已删除")
        else:
            print("取消删除")

    elif cmd == "lint":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        issues = recipe_lint(recipe_id)
        if not issues:
            print("✅ 食谱完整，无问题")
        else:
            print("❌ 问题:")
            for iss in issues:
                print(f"  - {iss}")


if __name__ == "__main__":
    main()