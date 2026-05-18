#!/usr/bin/env python3
"""
健身目标管理 - CLI工具
支持添加、查询、更新、删除健身目标
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

DB_FILENAME = "calorie_data.db"


def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db"""
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
    # 2. 技能目录（默认）
    p = skill_dir / db_filename
    if p.exists():
        return p
    # 3. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / db_filename
            if p.exists():
                return p
    # 4. 都找不到则创建在 .db 目录
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename

SKILL_DIR = Path(__file__).parent
DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)


def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_table():
    """初始化健身目标表"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fitness_goals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            goal_type       TEXT NOT NULL,
            exercise_type   TEXT NOT NULL,
            target_unit     TEXT NOT NULL,
            target_value    INTEGER NOT NULL,
            start_date      TEXT NOT NULL,
            end_date        TEXT,
            status          TEXT DEFAULT 'active',
            note            TEXT,
            created_at      INTEGER NOT NULL,
            updated_at      INTEGER
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fg_date ON fitness_goals(start_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fg_type ON fitness_goals(exercise_type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_fg_status ON fitness_goals(status)")
    conn.commit()
    conn.close()


def add_goal(name, goal_type, exercise_type, target_unit, target_value, start_date, end_date, note):
    """添加目标"""
    conn = get_db()
    cur = conn.cursor()
    now = int(time.time())
    cur.execute("""
        INSERT INTO fitness_goals 
        (name, goal_type, exercise_type, target_unit, target_value, start_date, end_date, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, goal_type, exercise_type, target_unit, target_value, start_date, end_date, note, now))
    conn.commit()
    goal_id = cur.lastrowid
    conn.close()
    print(f"✓ 已添加目标 #{goal_id}: {name}")
    return goal_id


def list_goals(goal_type=None, status=None, exercise_type=None):
    """查询目标列表"""
    conn = get_db()
    cur = conn.cursor()
    
    conditions = []
    params = []
    
    if goal_type:
        conditions.append("goal_type = ?")
        params.append(goal_type)
    if status:
        conditions.append("status = ?")
        params.append(status)
    if exercise_type:
        conditions.append("exercise_type = ?")
        params.append(exercise_type)
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    cur.execute(f"""
        SELECT id, name, goal_type, exercise_type, target_unit, target_value, 
               start_date, end_date, status, note, created_at
        FROM fitness_goals
        WHERE {where}
        ORDER BY created_at DESC
    """, params)
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        print("没有找到目标")
        return
    
    print(f"找到 {len(rows)} 个目标：\n")
    for r in rows:
        print(f"  [{r['id']}] {r['name']}")
        print(f"      类型: {r['goal_type']} | 运动: {r['exercise_type']}")
        print(f"      目标: {r['target_value']}{r['target_unit']}")
        print(f"      时间: {r['start_date']} ~ {r['end_date'] or '永久'}")
        print(f"      状态: {r['status']}")
        if r['note']:
            print(f"      备注: {r['note']}")
        print()


def update_goal(goal_id, **kwargs):
    """更新目标"""
    conn = get_db()
    cur = conn.cursor()
    
    allowed_fields = ['name', 'goal_type', 'exercise_type', 'target_unit', 'target_value', 
                     'start_date', 'end_date', 'status', 'note']
    
    updates = []
    params = []
    for key, value in kwargs.items():
        if key in allowed_fields and value is not None:
            updates.append(f"{key} = ?")
            params.append(value)
    
    if not updates:
        print("没有需要更新的字段")
        return
    
    updates.append("updated_at = ?")
    params.append(int(time.time()))
    params.append(goal_id)
    
    cur.execute(f"""
        UPDATE fitness_goals SET {', '.join(updates)} WHERE id = ?
    """, params)
    conn.commit()
    affected = cur.rowcount
    conn.close()
    
    if affected:
        print(f"✓ 已更新目标 #{goal_id}")
    else:
        print(f"目标 #{goal_id} 不存在")


def delete_goal(goal_id):
    """删除目标"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM fitness_goals WHERE id = ?", (goal_id,))
    conn.commit()
    affected = cur.rowcount
    conn.close()
    
    if affected:
        print(f"✓ 已删除目标 #{goal_id}")
    else:
        print(f"目标 #{goal_id} 不存在")


def complete_goal(goal_id):
    """标记目标完成"""
    update_goal(goal_id, status='completed')


def main():
    parser = argparse.ArgumentParser(description="健身目标管理")
    subparsers = parser.add_subparsers(dest='cmd', help='子命令')

    # add
    p_add = subparsers.add_parser('add', help='添加目标')
    p_add.add_argument('name', help='目标名称')
    p_add.add_argument('--type', dest='goal_type', required=True, 
                       choices=['daily', 'weekly', 'monthly', 'longterm'], help='目标类型')
    p_add.add_argument('--exercise', dest='exercise_type', required=True, help='运动类型')
    p_add.add_argument('--unit', required=True, help='单位（个/分钟/公里等）')
    p_add.add_argument('--target', dest='target_value', type=int, required=True, help='目标值')
    p_add.add_argument('--start', dest='start_date', required=True, help='开始日期 YYYY-MM-DD')
    p_add.add_argument('--end', dest='end_date', help='截止日期 YYYY-MM-DD')
    p_add.add_argument('--note', help='备注')

    # list
    p_list = subparsers.add_parser('list', help='查询目标')
    p_list.add_argument('--type', dest='goal_type', choices=['daily', 'weekly', 'monthly', 'longterm'])
    p_list.add_argument('--status', help='状态')
    p_list.add_argument('--exercise', dest='exercise_type', help='运动类型')

    # update
    p_update = subparsers.add_parser('update', help='更新目标')
    p_update.add_argument('id', type=int, help='目标ID')
    p_update.add_argument('--name', help='目标名称')
    p_update.add_argument('--type', dest='goal_type', choices=['daily', 'weekly', 'monthly', 'longterm'])
    p_update.add_argument('--exercise', dest='exercise_type', help='运动类型')
    p_update.add_argument('--unit', help='单位')
    p_update.add_argument('--target', dest='target_value', type=int, help='目标值')
    p_update.add_argument('--start', dest='start_date', help='开始日期')
    p_update.add_argument('--end', dest='end_date', help='截止日期')
    p_update.add_argument('--status', choices=['active', 'paused'], help='状态')
    p_update.add_argument('--note', help='备注')

    # delete
    p_delete = subparsers.add_parser('delete', help='删除目标')
    p_delete.add_argument('id', type=int, help='目标ID')

    args = parser.parse_args()

    # 初始化表
    init_table()

    if args.cmd == 'add':
        add_goal(args.name, args.goal_type, args.exercise_type, args.unit, 
                 args.target_value, args.start_date, args.end_date, args.note)
    elif args.cmd == 'list':
        list_goals(goal_type=args.goal_type, status=args.status, exercise_type=args.exercise_type)
    elif args.cmd == 'update':
        kwargs = {k: v for k, v in vars(args).items() 
                  if k not in ['cmd', 'id'] and v is not None}
        update_goal(args.id, **kwargs)
    elif args.cmd == 'delete':
        delete_goal(args.id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()