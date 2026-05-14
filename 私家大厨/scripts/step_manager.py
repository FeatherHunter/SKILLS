#!/usr/bin/env python3
"""
私家大厨 - 烹饪步骤管理脚本 v1.0
对应表：cooking_steps（39字段）
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


def step_add(
    recipe_id,
    sequence=None,
    phase=None,
    action=None,
    purpose=None,
    sub_purpose=None,
    tools=None,
    duration_minutes=None,
    temperature_value=None,
    temperature_end_value=None,
    temperature_unit=None,
    heat_level=None,
    heat_adjustment=None,
    urgency_level=None,
    expected_result=None,
    visual_signal=None,
    audio_signal=None,
    smell_signal=None,
    texture_signal=None,
    doneness_indicator=None,
    color_during=None,
    color_after=None,
    texture_during=None,
    texture_after=None,
    can_parallel=None,
    parallel_with=None,
    parallel_notes=None,
    common_mistakes=None,
    mistake_causes=None,
    mistake_fixes=None,
    is_critical=None,
    is_safety_critical=None,
    warnings=None,
    retry_strategy=None,
    can_skip=None,
    skip_effects=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """添加烹饪步骤（39字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    step_id = str(uuid.uuid4())
    now = _now()

    cursor.execute('''
        INSERT INTO cooking_steps (
            id, recipe_id, sequence, phase, action,
            purpose, sub_purpose, tools, duration_minutes,
            temperature_value, temperature_end_value, temperature_unit,
            heat_level, heat_adjustment, urgency_level,
            expected_result, visual_signal, audio_signal,
            smell_signal, texture_signal, doneness_indicator,
            color_during, color_after, texture_during, texture_after,
            can_parallel, parallel_with, parallel_notes,
            common_mistakes, mistake_causes, mistake_fixes,
            is_critical, is_safety_critical, warnings,
            retry_strategy, can_skip, skip_effects,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        step_id, recipe_id, sequence, phase, action,
        purpose, sub_purpose, _json(tools), duration_minutes,
        temperature_value, temperature_end_value, temperature_unit,
        heat_level, heat_adjustment, urgency_level,
        expected_result, visual_signal, audio_signal,
        smell_signal, texture_signal, doneness_indicator,
        color_during, color_after, texture_during, texture_after,
        1 if can_parallel else 0, parallel_with, parallel_notes,
        _json(common_mistakes), _json(mistake_causes), _json(mistake_fixes),
        1 if is_critical else 0, 1 if is_safety_critical else 0, _json(warnings),
        retry_strategy, 1 if can_skip else 0, skip_effects,
        now, now
    ])

    conn.commit()
    conn.close()
    return step_id


def step_list(recipe_id, limit=50):
    """列出某食谱的所有步骤"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM cooking_steps WHERE recipe_id = ? ORDER BY sequence',
        (recipe_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    for r in rows:
        for f in ['tools', 'common_mistakes', 'mistake_causes', 'mistake_fixes', 'warnings']:
            if r.get(f):
                try: r[f] = json.loads(r[f])
                except: pass
    return rows


def step_get(step_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cooking_steps WHERE id = ?', (step_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def step_update(
    step_id,
    recipe_id=None,
    sequence=None,
    phase=None,
    action=None,
    purpose=None,
    sub_purpose=None,
    tools=None,
    duration_minutes=None,
    temperature_value=None,
    temperature_end_value=None,
    temperature_unit=None,
    heat_level=None,
    heat_adjustment=None,
    urgency_level=None,
    expected_result=None,
    visual_signal=None,
    audio_signal=None,
    smell_signal=None,
    texture_signal=None,
    doneness_indicator=None,
    color_during=None,
    color_after=None,
    texture_during=None,
    texture_after=None,
    can_parallel=None,
    parallel_with=None,
    parallel_notes=None,
    common_mistakes=None,
    mistake_causes=None,
    mistake_fixes=None,
    is_critical=None,
    is_safety_critical=None,
    warnings=None,
    retry_strategy=None,
    can_skip=None,
    skip_effects=None,
    created_at=None,
    updated_at=None,
    **kwargs
):
    """更新烹饪步骤（显式39字段）"""
    conn = get_conn()
    cursor = conn.cursor()

    fields = {}
    if recipe_id is not None: fields['recipe_id'] = recipe_id
    if sequence is not None: fields['sequence'] = sequence
    if phase is not None: fields['phase'] = phase
    if action is not None: fields['action'] = action
    if purpose is not None: fields['purpose'] = purpose
    if sub_purpose is not None: fields['sub_purpose'] = _json(sub_purpose)
    if tools is not None: fields['tools'] = _json(tools)
    if duration_minutes is not None: fields['duration_minutes'] = duration_minutes
    if temperature_value is not None: fields['temperature_value'] = temperature_value
    if temperature_end_value is not None: fields['temperature_end_value'] = temperature_end_value
    if temperature_unit is not None: fields['temperature_unit'] = temperature_unit
    if heat_level is not None: fields['heat_level'] = heat_level
    if heat_adjustment is not None: fields['heat_adjustment'] = heat_adjustment
    if urgency_level is not None: fields['urgency_level'] = urgency_level
    if expected_result is not None: fields['expected_result'] = expected_result
    if visual_signal is not None: fields['visual_signal'] = visual_signal
    if audio_signal is not None: fields['audio_signal'] = audio_signal
    if smell_signal is not None: fields['smell_signal'] = smell_signal
    if texture_signal is not None: fields['texture_signal'] = texture_signal
    if doneness_indicator is not None: fields['doneness_indicator'] = doneness_indicator
    if color_during is not None: fields['color_during'] = color_during
    if color_after is not None: fields['color_after'] = color_after
    if texture_during is not None: fields['texture_during'] = texture_during
    if texture_after is not None: fields['texture_after'] = texture_after
    if can_parallel is not None: fields['can_parallel'] = 1 if can_parallel else 0
    if parallel_with is not None: fields['parallel_with'] = parallel_with
    if parallel_notes is not None: fields['parallel_notes'] = parallel_notes
    if common_mistakes is not None: fields['common_mistakes'] = _json(common_mistakes)
    if mistake_causes is not None: fields['mistake_causes'] = _json(mistake_causes)
    if mistake_fixes is not None: fields['mistake_fixes'] = _json(mistake_fixes)
    if is_critical is not None: fields['is_critical'] = 1 if is_critical else 0
    if is_safety_critical is not None: fields['is_safety_critical'] = 1 if is_safety_critical else 0
    if warnings is not None: fields['warnings'] = _json(warnings)
    if retry_strategy is not None: fields['retry_strategy'] = retry_strategy
    if can_skip is not None: fields['can_skip'] = 1 if can_skip else 0
    if skip_effects is not None: fields['skip_effects'] = skip_effects
    if created_at is not None: fields['created_at'] = created_at
    if updated_at is not None: fields['updated_at'] = updated_at

    if not fields:
        conn.close()
        return False

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [step_id]
    cursor.execute(f"UPDATE cooking_steps SET {set_clause} WHERE id = ?", values)
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def step_delete(step_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cooking_steps WHERE id = ?', (step_id,))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def step_search(keyword, limit=20):
    """搜索步骤"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT * FROM cooking_steps WHERE action LIKE ? ORDER BY recipe_id LIMIT ?",
        (f'%{keyword}%', limit)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python step_manager.py add <recipe_id> <sequence> <action> [--field value ...]")
        print("  python step_manager.py list <recipe_id>")
        print("  python step_manager.py get <step_id>")
        print("  python step_manager.py update <step_id> [--field value ...]")
        print("  python step_manager.py delete <step_id>")
        print("  python step_manager.py search <keyword>")
        print()
        print("字段说明:")
        fields = [
            'sequence=int, phase=str, action=str, purpose=str, sub_purpose=str',
            'tools=list, duration_minutes=int, temperature_value=float',
            'temperature_end_value=float, temperature_unit=str, heat_level=str',
            'heat_adjustment=str, urgency_level=str, expected_result=str',
            'visual_signal=str, audio_signal=str, smell_signal=str',
            'texture_signal=str, doneness_indicator=str',
            'color_during=str, color_after=str, texture_during=str, texture_after=str',
            'can_parallel=0|1, parallel_with=int, parallel_notes=str',
            'common_mistakes=list, mistake_causes=list, mistake_fixes=list',
            'is_critical=0|1, is_safety_critical=0|1, warnings=list',
            'retry_strategy=str, can_skip=0|1, skip_effects=str'
        ]
        for f in fields:
            print(f"  {f}")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        sequence = int(sys.argv[3]) if len(sys.argv) > 3 else int(input("sequence: "))
        action = sys.argv[4] if len(sys.argv) > 4 else input("action: ")

        args = sys.argv[5:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1

        step_id = step_add(recipe_id, sequence, action, **fields)
        print(f"✅ 步骤已添加 (ID: {step_id})")

    elif cmd == "list":
        recipe_id = sys.argv[2] if len(sys.argv) > 2 else input("recipe_id: ")
        steps = step_list(recipe_id)
        if not steps:
            print("暂无步骤")
        else:
            print(f"\n📝 {len(steps)}个步骤:")
            for s in steps:
                dur = f"[{s['duration_minutes']}分钟]" if s.get('duration_minutes') else ""
                heat = f"🔥{s['heat_level']}" if s.get('heat_level') else ""
                print(f"  {s['sequence']}. {s['action']} {dur} {heat}")

    elif cmd == "get":
        step_id = sys.argv[2] if len(sys.argv) > 2 else input("step_id: ")
        s = step_get(step_id)
        if not s:
            print("未找到该步骤")
        else:
            print(f"\n📝 步骤 {s['sequence']}")
            print(f"  操作: {s['action']}")
            print(f"  阶段: {s.get('phase', '-')}")
            print(f"  时长: {s.get('duration_minutes', '-')}分钟")
            print(f"  火候: {s.get('heat_level', '-')}")
            print(f"  目的: {s.get('purpose', '-')}")
            print(f"  关键步骤: {'是' if s.get('is_critical') else '否'}")

    elif cmd == "update":
        step_id = sys.argv[2] if len(sys.argv) > 2 else input("step_id: ")
        args = sys.argv[3:]
        fields = {}
        i = 0
        while i < len(args):
            if args[i].startswith('--') and i + 1 < len(args):
                fields[args[i][2:]] = args[i + 1]
            i += 1
        step_update(step_id, **fields)
        print("✅ 已更新")

    elif cmd == "delete":
        step_id = sys.argv[2] if len(sys.argv) > 2 else input("step_id: ")
        confirm = input("确认删除？(y/n): ")
        if confirm.lower() == 'y':
            step_delete(step_id)
            print("✅ 已删除")
        else:
            print("取消删除")

    elif cmd == "search":
        keyword = sys.argv[2] if len(sys.argv) > 2 else input("关键词: ")
        steps = step_search(keyword)
        print(f"\n🔍 找到{len(steps)}个相关步骤:")
        for s in steps[:10]:
            print(f"  [{s['recipe_id'][:8]}...] {s['sequence']}. {s['action']}")


if __name__ == "__main__":
    main()