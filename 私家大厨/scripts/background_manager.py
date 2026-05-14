#!/usr/bin/env python3
"""
私家大厨 - 背景知识管理脚本 v1.0
对应表：background_knowledge（24字段）
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


def background_add(
    recipe_id,
    origin_story=None,
    historical_background=None,
    era=None,
    cultural_significance=None,
    story_variants=None,
    famous_restaurants=None,
    famous_chefs=None,
    related_dishes=None,
    regional_variants=None,
    nutrition_benefits=None,
    nutrition_highlights=None,
    nutrition_concerns=None,
    taboos=None,
    wine_pairing=None,
    wine_pairing_details=None,
    beverage_pairing=None,
    staplefood_pairing=None,
    side_dish_pairing=None,
    weather_suitability=None,
    external_links=None,
    media_references=None,
    cultural_notes=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """添加背景知识（24字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    bg_id = str(uuid.uuid4())
    now = _now()

    cursor.execute('''
        INSERT INTO background_knowledge (
            id, recipe_id, origin_story, historical_background,
            era, cultural_significance, story_variants,
            famous_restaurants, famous_chefs, related_dishes,
            regional_variants, nutrition_benefits, nutrition_highlights,
            nutrition_concerns, taboos, wine_pairing, wine_pairing_details,
            beverage_pairing, staplefood_pairing, side_dish_pairing,
            weather_suitability, external_links, media_references,
            cultural_notes, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        bg_id, recipe_id, origin_story, historical_background,
        era, cultural_significance, _json(story_variants),
        _json(famous_restaurants), _json(famous_chefs), _json(related_dishes),
        _json(regional_variants), nutrition_benefits, nutrition_highlights,
        nutrition_concerns, taboos, wine_pairing, wine_pairing_details,
        beverage_pairing, staplefood_pairing, side_dish_pairing,
        weather_suitability, _json(external_links), _json(media_references),
        cultural_notes, now, now
    ])

    conn.commit()
    conn.close()
    return bg_id


def background_list(recipe_id, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM background_knowledge WHERE recipe_id = ?", (recipe_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        for f in ['story_variants', 'famous_restaurants', 'famous_chefs', 'related_dishes',
                  'regional_variants', 'external_links', 'media_references']:
            if r.get(f):
                try: r[f] = json.loads(r[f])
                except: pass
    return rows


def background_get(bg_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM background_knowledge WHERE id = ?", (bg_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def background_update(
    bg_id,
    recipe_id=None,
    origin_story=None,
    historical_background=None,
    era=None,
    cultural_significance=None,
    story_variants=None,
    famous_restaurants=None,
    famous_chefs=None,
    related_dishes=None,
    regional_variants=None,
    nutrition_benefits=None,
    nutrition_highlights=None,
    nutrition_concerns=None,
    taboos=None,
    wine_pairing=None,
    wine_pairing_details=None,
    beverage_pairing=None,
    staplefood_pairing=None,
    side_dish_pairing=None,
    weather_suitability=None,
    external_links=None,
    media_references=None,
    cultural_notes=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """更新背景知识（显式24字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    fields = {}
    if recipe_id is not None: fields['recipe_id'] = recipe_id
    if origin_story is not None: fields['origin_story'] = origin_story
    if historical_background is not None: fields['historical_background'] = historical_background
    if era is not None: fields['era'] = era
    if cultural_significance is not None: fields['cultural_significance'] = cultural_significance
    if story_variants is not None: fields['story_variants'] = _json(story_variants)
    if famous_restaurants is not None: fields['famous_restaurants'] = _json(famous_restaurants)
    if famous_chefs is not None: fields['famous_chefs'] = _json(famous_chefs)
    if related_dishes is not None: fields['related_dishes'] = _json(related_dishes)
    if regional_variants is not None: fields['regional_variants'] = _json(regional_variants)
    if nutrition_benefits is not None: fields['nutrition_benefits'] = nutrition_benefits
    if nutrition_highlights is not None: fields['nutrition_highlights'] = nutrition_highlights
    if nutrition_concerns is not None: fields['nutrition_concerns'] = nutrition_concerns
    if taboos is not None: fields['taboos'] = taboos
    if wine_pairing is not None: fields['wine_pairing'] = wine_pairing
    if wine_pairing_details is not None: fields['wine_pairing_details'] = wine_pairing_details
    if beverage_pairing is not None: fields['beverage_pairing'] = beverage_pairing
    if staplefood_pairing is not None: fields['staplefood_pairing'] = staplefood_pairing
    if side_dish_pairing is not None: fields['side_dish_pairing'] = side_dish_pairing
    if weather_suitability is not None: fields['weather_suitability'] = weather_suitability
    if external_links is not None: fields['external_links'] = _json(external_links)
    if media_references is not None: fields['media_references'] = _json(media_references)
    if cultural_notes is not None: fields['cultural_notes'] = cultural_notes
    if created_at is not None: fields['created_at'] = created_at
    if updated_at is not None: fields['updated_at'] = updated_at

    if not fields:
        conn.close()
        return False

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [bg_id]
    cursor.execute(f"UPDATE background_knowledge SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def background_delete(bg_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM background_knowledge WHERE id = ?", (bg_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python background_manager.py add <recipe_id> [--field value ...]")
        print("  python background_manager.py list <recipe_id>")
        print("  python background_manager.py get <bg_id>")
        print("  python background_manager.py update <bg_id> [--field value ...]")
        print("  python background_manager.py delete <bg_id>")
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
        bg_id = background_add(recipe_id, **fields)
        print(f"✅ 背景知识已添加 (ID: {bg_id})")

    elif cmd == "list":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        items = background_list(recipe_id)
        if not items:
            print("暂无背景知识")
        else:
            print(f"\n📜 {len(items)}条背景知识:")
            for b in items:
                print(f"  • {b.get('era','?')} | {b.get('origin_story','?')[:50]}...")

    elif cmd == "get":
        bg_id = sys.argv[2] if len(sys.argv) > 2 else input("bg_id: ")
        b = background_get(bg_id)
        if b:
            print(f"\n📜 背景知识:")
            for k, v in b.items():
                if v:
                    print(f"   {k}: {v}")

    elif cmd == "update":
        bg_id = sys.argv[2] if len(sys.argv) > 2 else input("bg_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        background_update(bg_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        bg_id = sys.argv[2] if len(sys.argv) > 2 else input("bg_id: ")
        confirm = input("确认删除？(y/n): ")
        if confirm.lower() == 'y':
            background_delete(bg_id)
            print("✅ 已删除")


if __name__ == "__main__":
    main()