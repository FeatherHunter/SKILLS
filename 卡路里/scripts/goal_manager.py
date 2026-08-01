#!/usr/bin/env python3
"""目标管理器 — 暂停/重启全部目标（G3 改目标）

数据存储：daily_goal.goal_paused（INTEGER DEFAULT 0，db.py 迁移）
- 1 = 暂停（记录照常，仅目标暂停）
- 0 = 正常

场景：
- 暂停所有目标：临时冻结全部目标（营养 + 体重 + 饮水），后续可解冻
- 重启所有目标：从暂停恢复全部目标
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


def get_paused_state():
    """读取当前暂停状态

    Returns:
        dict {paused: bool, paused_at: str|None} 或 None(表异常)
    """
    conn = _get_db()
    try:
        row = conn.execute('SELECT goal_paused, updated_at FROM daily_goal WHERE id = 1').fetchone()
    except Exception:
        conn.close()
        return None
    conn.close()
    if row is None:
        return {'paused': False, 'paused_at': None}
    return {'paused': bool(row['goal_paused']), 'paused_at': row['updated_at']}


def pause_all_goals():
    """暂停全部目标（营养 + 体重 + 饮水）

    Returns:
        dict {id, updated_at, rows_affected, paused, note, restore_hint}
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE daily_goal
        SET goal_paused = 1, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''')
    rows_affected = c.rowcount
    conn.commit()
    c.execute('SELECT id, updated_at, goal_paused FROM daily_goal WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return {
        'id': row['id'],
        'updated_at': row['updated_at'],
        'rows_affected': rows_affected,
        'paused': True,
        'note': '记录照常，仅目标暂停（完成度显示不计入暂停期）',
        'restore_hint': '说「重启所有目标」即可恢复',
    }


def resume_all_goals():
    """从暂停恢复全部目标

    Returns:
        dict {id, updated_at, rows_affected, resume_state, resumed_at}
    """
    conn = _get_db()
    c = conn.cursor()
    c.execute('''
        UPDATE daily_goal
        SET goal_paused = 0, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''')
    rows_affected = c.rowcount
    conn.commit()
    c.execute('SELECT id, updated_at FROM daily_goal WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return {
        'id': row['id'],
        'updated_at': row['updated_at'],
        'rows_affected': rows_affected,
        'resume_state': '正常（未暂停）',
        'resumed_at': row['updated_at'],
    }


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'pause':
        r = pause_all_goals()
        print(f"✓ 全部目标已暂停 id={r['id']} | 日期 {r['updated_at']} | 影响 {r['rows_affected']} 行")
        print(f"  {r['note']} | {r['restore_hint']}")
    elif cmd == 'resume':
        r = resume_all_goals()
        print(f"✓ 全部目标已恢复 id={r['id']} | 日期 {r['updated_at']} | 影响 {r['rows_affected']} 行")
        print(f"  {r['resume_state']}")
    elif cmd == 'status':
        s = get_paused_state()
        print(f"暂停状态: {'已暂停' if s and s['paused'] else '正常'}" + (f"（{s['paused_at']}）" if s and s['paused_at'] else ''))
    else:
        print("用法: goal_manager.py pause | resume | status")
        sys.exit(1)
