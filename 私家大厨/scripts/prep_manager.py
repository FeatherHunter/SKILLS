#!/usr/bin/env python3
"""
私家大厨 - 食材处理方式管理脚本 v1.0
对应表：ingredient_preparations（26字段）
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


def prep_add(
    recipe_id,
    ingredient_id=None,
    step_id=None,
    introduced_method=None,
    prep_name=None,
    prep_details=None,
    tools_used=None,
    duration_minutes=None,
    temperature=None,
    temperature_end=None,
    liquid_used=None,
    liquid_ratio=None,
    seasoning_added=None,
    coating_used=None,
    coating_ratio=None,
    texture_after=None,
    color_change=None,
    smell_change=None,
    storage_method=None,
    storage_duration=None,
    is_prerequisite=None,
    prerequisite_notes=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """添加食材处理方式（26字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    prep_id = str(uuid.uuid4())
    now = _now()

    cursor.execute('''
        INSERT INTO ingredient_preparations (
            id, recipe_id, ingredient_id, step_id,
            introduced_method, prep_name, prep_details, tools_used,
            duration_minutes, temperature, temperature_end,
            liquid_used, liquid_ratio, seasoning_added,
            coating_used, coating_ratio,
            texture_after, color_change, smell_change,
            storage_method, storage_duration,
            is_prerequisite, prerequisite_notes,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        prep_id, recipe_id, ingredient_id, step_id,
        introduced_method, prep_name, prep_details, _json(tools_used),
        duration_minutes, temperature, temperature_end,
        _json(liquid_used), liquid_ratio, _json(seasoning_added),
        _json(coating_used), coating_ratio,
        texture_after, color_change, smell_change,
        storage_method, storage_duration,
        1 if is_prerequisite else 0, prerequisite_notes,
        now, now
    ])

    conn.commit()
    conn.close()
    return prep_id


def prep_list(recipe_id, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingredient_preparations WHERE recipe_id = ?", (recipe_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        for f in ['tools_used', 'liquid_used', 'seasoning_added', 'coating_used']:
            if r.get(f):
                try: r[f] = json.loads(r[f])
                except: pass
    return rows


def prep_get(prep_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ingredient_preparations WHERE id = ?", (prep_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def prep_update(
    prep_id,
    recipe_id=None,
    ingredient_id=None,
    step_id=None,
    introduced_method=None,
    prep_name=None,
    prep_details=None,
    tools_used=None,
    duration_minutes=None,
    temperature=None,
    temperature_end=None,
    liquid_used=None,
    liquid_ratio=None,
    seasoning_added=None,
    coating_used=None,
    coating_ratio=None,
    texture_after=None,
    color_change=None,
    smell_change=None,
    storage_method=None,
    storage_duration=None,
    is_prerequisite=None,
    prerequisite_notes=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """更新食材处理方式（26字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    fields = {}
    if recipe_id is not None: fields['recipe_id'] = recipe_id
    if ingredient_id is not None: fields['ingredient_id'] = ingredient_id
    if step_id is not None: fields['step_id'] = step_id
    if introduced_method is not None: fields['introduced_method'] = introduced_method
    if prep_name is not None: fields['prep_name'] = prep_name
    if prep_details is not None: fields['prep_details'] = prep_details
    if tools_used is not None: fields['tools_used'] = _json(tools_used)
    if duration_minutes is not None: fields['duration_minutes'] = duration_minutes
    if temperature is not None: fields['temperature'] = temperature
    if temperature_end is not None: fields['temperature_end'] = temperature_end
    if liquid_used is not None: fields['liquid_used'] = _json(liquid_used)
    if liquid_ratio is not None: fields['liquid_ratio'] = liquid_ratio
    if seasoning_added is not None: fields['seasoning_added'] = _json(seasoning_added)
    if coating_used is not None: fields['coating_used'] = _json(coating_used)
    if coating_ratio is not None: fields['coating_ratio'] = coating_ratio
    if texture_after is not None: fields['texture_after'] = texture_after
    if color_change is not None: fields['color_change'] = color_change
    if smell_change is not None: fields['smell_change'] = smell_change
    if storage_method is not None: fields['storage_method'] = storage_method
    if storage_duration is not None: fields['storage_duration'] = storage_duration
    if is_prerequisite is not None: fields['is_prerequisite'] = 1 if is_prerequisite else 0
    if prerequisite_notes is not None: fields['prerequisite_notes'] = prerequisite_notes
    if created_at is not None: fields['created_at'] = created_at
    if updated_at is not None: fields['updated_at'] = updated_at

    if not fields:
        conn.close()
        return False

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [prep_id]
    cursor.execute(f"UPDATE ingredient_preparations SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def prep_delete(prep_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ingredient_preparations WHERE id = ?", (prep_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python prep_manager.py add <recipe_id> [--field value ...]")
        print("  python prep_manager.py list <recipe_id>")
        print("  python prep_manager.py get <prep_id>")
        print("  python prep_manager.py update <prep_id> [--field value ...]")
        print("  python prep_manager.py delete <prep_id>")
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
        prep_id = prep_add(recipe_id, **fields)
        print(f"✅ 处理方式已添加 (ID: {prep_id})")

    elif cmd == "list":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        items = prep_list(recipe_id)
        if not items:
            print("暂无处理方式")
        else:
            print(f"\n🔪 {len(items)}种处理方式:")
            for p in items:
                print(f"  • {p.get('prep_name','?')} | {p.get('duration_minutes','?')}分钟 | {p.get('texture_after','?')}")

    elif cmd == "get":
        prep_id = sys.argv[2] if len(sys.argv) > 2 else input("prep_id: ")
        p = prep_get(prep_id)
        if p:
            print(f"\n🔪 处理: {p.get('prep_name','?')}")
            for k, v in p.items():
                if v:
                    print(f"   {k}: {v}")

    elif cmd == "update":
        prep_id = sys.argv[2] if len(sys.argv) > 2 else input("prep_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        prep_update(prep_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        prep_id = sys.argv[2] if len(sys.argv) > 2 else input("prep_id: ")
        confirm = input("确认删除？(y/n): ")
        if confirm.lower() == 'y':
            prep_delete(prep_id)
            print("✅ 已删除")


if __name__ == "__main__":
    main()