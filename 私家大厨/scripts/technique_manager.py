#!/usr/bin/env python3
"""
私家大厨 - 步骤技法管理脚本 v1.0
对应表：step_techniques（22字段）
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


def technique_add(
    step_id=None,
    recipe_id=None,
    technique_code=None,
    technique_name=None,
    description=None,
    key_points=None,
    wrist_action=None,
    arm_action=None,
    fire_control=None,
    timing=None,
    speed=None,
    difficulty_to_learn=None,
    learn_stage=None,
    common_errors=None,
    error_signs=None,
    fix_methods=None,
    prerequisite_skills=None,
    related_techniques=None,
    youtube_links=None,
    practice_exercises=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """添加步骤技法（22字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    technique_id = str(uuid.uuid4())
    now = _now()

    cursor.execute('''
        INSERT INTO step_techniques (
            id, step_id, recipe_id, technique_code, technique_name,
            description, key_points, wrist_action, arm_action, fire_control,
            timing, speed, difficulty_to_learn, learn_stage,
            common_errors, error_signs, fix_methods,
            prerequisite_skills, related_techniques,
            youtube_links, practice_exercises,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        technique_id, step_id, recipe_id, technique_code, technique_name,
        description, _json(key_points), wrist_action, arm_action, fire_control,
        timing, speed, difficulty_to_learn, learn_stage,
        _json(common_errors), _json(error_signs), _json(fix_methods),
        _json(prerequisite_skills), _json(related_techniques),
        _json(youtube_links), _json(practice_exercises),
        now, now
    ])

    conn.commit()
    conn.close()
    return technique_id


def technique_list(recipe_id=None, step_id=None, limit=50):
    conn = get_conn()
    cursor = conn.cursor()
    if recipe_id:
        cursor.execute("SELECT * FROM step_techniques WHERE recipe_id = ? LIMIT ?", (recipe_id, limit))
    elif step_id:
        cursor.execute("SELECT * FROM step_techniques WHERE step_id = ? LIMIT ?", (step_id, limit))
    else:
        cursor.execute("SELECT * FROM step_techniques LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        for f in ['key_points', 'common_errors', 'error_signs', 'fix_methods',
                  'prerequisite_skills', 'related_techniques', 'youtube_links', 'practice_exercises']:
            if r.get(f):
                try: r[f] = json.loads(r[f])
                except: pass
    return rows


def technique_get(technique_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM step_techniques WHERE id = ?", (technique_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def technique_update(
    technique_id,
    step_id=None,
    recipe_id=None,
    technique_code=None,
    technique_name=None,
    description=None,
    key_points=None,
    wrist_action=None,
    arm_action=None,
    fire_control=None,
    timing=None,
    speed=None,
    difficulty_to_learn=None,
    learn_stage=None,
    common_errors=None,
    error_signs=None,
    fix_methods=None,
    prerequisite_skills=None,
    related_techniques=None,
    youtube_links=None,
    practice_exercises=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """更新步骤技法（显式22字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    fields = {}
    if step_id is not None: fields['step_id'] = step_id
    if recipe_id is not None: fields['recipe_id'] = recipe_id
    if technique_code is not None: fields['technique_code'] = technique_code
    if technique_name is not None: fields['technique_name'] = technique_name
    if description is not None: fields['description'] = description
    if key_points is not None: fields['key_points'] = _json(key_points)
    if wrist_action is not None: fields['wrist_action'] = wrist_action
    if arm_action is not None: fields['arm_action'] = arm_action
    if fire_control is not None: fields['fire_control'] = fire_control
    if timing is not None: fields['timing'] = timing
    if speed is not None: fields['speed'] = speed
    if difficulty_to_learn is not None: fields['difficulty_to_learn'] = difficulty_to_learn
    if learn_stage is not None: fields['learn_stage'] = learn_stage
    if common_errors is not None: fields['common_errors'] = _json(common_errors)
    if error_signs is not None: fields['error_signs'] = _json(error_signs)
    if fix_methods is not None: fields['fix_methods'] = _json(fix_methods)
    if prerequisite_skills is not None: fields['prerequisite_skills'] = _json(prerequisite_skills)
    if related_techniques is not None: fields['related_techniques'] = _json(related_techniques)
    if youtube_links is not None: fields['youtube_links'] = _json(youtube_links)
    if practice_exercises is not None: fields['practice_exercises'] = _json(practice_exercises)
    if created_at is not None: fields['created_at'] = created_at
    if updated_at is not None: fields['updated_at'] = updated_at

    if not fields:
        conn.close()
        return False

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [technique_id]
    cursor.execute(f"UPDATE step_techniques SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def technique_delete(technique_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM step_techniques WHERE id = ?", (technique_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python technique_manager.py add [--field value ...]")
        print("  python technique_manager.py list <recipe_id>")
        print("  python technique_manager.py get <technique_id>")
        print("  python technique_manager.py update <technique_id> [--field value ...]")
        print("  python technique_manager.py delete <technique_id>")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        args = sys.argv[2:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        technique_id = technique_add(**fields)
        print(f"✅ 技法已添加 (ID: {technique_id})")

    elif cmd == "list":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        items = technique_list(recipe_id=recipe_id)
        if not items:
            print("暂无技法")
        else:
            print(f"\n🎯 {len(items)}种技法:")
            for t in items:
                print(f"  • {t.get('technique_name','?')} | {t.get('difficulty_to_learn','?')}")

    elif cmd == "get":
        technique_id = sys.argv[2] if len(sys.argv) > 2 else input("technique_id: ")
        t = technique_get(technique_id)
        if t:
            print(f"\n🎯 {t.get('technique_name','?')}")
            for k, v in t.items():
                if v:
                    print(f"   {k}: {v}")

    elif cmd == "update":
        technique_id = sys.argv[2] if len(sys.argv) > 2 else input("technique_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        technique_update(technique_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        technique_id = sys.argv[2] if len(sys.argv) > 2 else input("technique_id: ")
        confirm = input("确认删除？(y/n): ")
        if confirm.lower() == 'y':
            technique_delete(technique_id)
            print("✅ 已删除")


if __name__ == "__main__":
    main()