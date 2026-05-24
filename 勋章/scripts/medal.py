#!/usr/bin/env python3
"""
勋章技能 - Python脚本层

提供勋章的增、查接口
所有操作必须通过此脚本执行，禁止直接操作数据库
"""

import os
import sys
import sqlite3
import json
import argparse
from datetime import datetime

# ============================================================
# 环境变量配置
# ============================================================
SKILLS_DB_PATH = os.getenv('SKILLS_DB_PATH')
if not SKILLS_DB_PATH:
    raise ValueError('缺少环境变量：SKILLS_DB_PATH')

MEDAL_DB_PATH = os.path.join(SKILLS_DB_PATH, 'medals.db')
MEDAL_RESOURCE_PATH = os.getenv('MEDAL_RESOURCE_PATH')
if not MEDAL_RESOURCE_PATH:
    raise ValueError('缺少环境变量：MEDAL_RESOURCE_PATH')

# 确保资源目录存在
os.makedirs(MEDAL_RESOURCE_PATH, exist_ok=True)

# ============================================================
# 数据库初始化
# ============================================================
def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(MEDAL_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medals (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            medal_type  TEXT NOT NULL,
            medal_name  TEXT NOT NULL,
            gif_path    TEXT NOT NULL,
            awarded_at  TEXT DEFAULT (datetime('now')),
            remark      TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_medals_type ON medals(medal_type)')
    conn.commit()
    conn.close()

# ============================================================
# 数据库操作
# ============================================================
def add_medal(medal_type: str, medal_name: str, gif_path: str, remark: str = None) -> int:
    """
    颁发勋章（新增记录）
    
    Args:
        medal_type: 勋章类型，如 "clean" "study"
        medal_name: 勋章名称，如 "清洁达人"
        gif_path: 生成的GIF路径
        remark: 获得原因/备注
    
    Returns:
        新记录的id
    """
    conn = sqlite3.connect(MEDAL_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO medals (medal_type, medal_name, gif_path, remark, awarded_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (medal_type, medal_name, gif_path, remark, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    medal_id = cursor.lastrowid
    conn.close()
    return medal_id


def get_medals(medal_type: str = None, limit: int = 50) -> list:
    """
    查询勋章记录
    
    Args:
        medal_type: 可选，按类型筛选
        limit: 返回数量限制，默认50
    
    Returns:
        勋章记录列表
    """
    conn = sqlite3.connect(MEDAL_DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if medal_type:
        cursor.execute('''
            SELECT * FROM medals 
            WHERE medal_type = ?
            ORDER BY awarded_at DESC
            LIMIT ?
        ''', (medal_type, limit))
    else:
        cursor.execute('''
            SELECT * FROM medals 
            ORDER BY awarded_at DESC
            LIMIT ?
        ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_medal_stats() -> dict:
    """
    获取勋章统计信息
    
    Returns:
        统计数据字典
    """
    conn = sqlite3.connect(MEDAL_DB_PATH)
    cursor = conn.cursor()
    
    # 总数
    cursor.execute('SELECT COUNT(*) FROM medals')
    total = cursor.fetchone()[0]
    
    # 按类型统计
    cursor.execute('''
        SELECT medal_type, COUNT(*) as count 
        FROM medals 
        GROUP BY medal_type 
        ORDER BY count DESC
    ''')
    by_type = {row[0]: row[1] for row in cursor.fetchall()}
    
    conn.close()
    return {
        'total': total,
        'by_type': by_type
    }


# ============================================================
# CLI 入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='勋章技能 - Python脚本层')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # add 子命令
    add_parser = subparsers.add_parser('add', help='颁发勋章')
    add_parser.add_argument('--type', required=True, help='勋章类型')
    add_parser.add_argument('--name', required=True, help='勋章名称')
    add_parser.add_argument('--gif', required=True, help='GIF路径')
    add_parser.add_argument('--remark', default='', help='备注/原因')
    
    # list 子命令
    list_parser = subparsers.add_parser('list', help='查询勋章记录')
    list_parser.add_argument('--type', help='按类型筛选')
    list_parser.add_argument('--limit', type=int, default=50, help='返回数量')
    
    # stats 子命令
    stats_parser = subparsers.add_parser('stats', help='勋章统计')
    
    # init 子命令
    init_parser = subparsers.add_parser('init', help='初始化数据库')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        medal_id = add_medal(args.type, args.name, args.gif, args.remark)
        print(f'勋章颁发成功，ID: {medal_id}')
        
    elif args.command == 'list':
        medals = get_medals(args.type, args.limit)
        if not medals:
            print('暂无勋章记录')
        else:
            for m in medals:
                print(f"[{m['id']}] {m['medal_name']} ({m['medal_type']}) - {m['awarded_at']} - {m['remark'] or ''}")
                
    elif args.command == 'stats':
        stats = get_medal_stats()
        print(f"总勋章数: {stats['total']}")
        print('按类型统计:')
        for t, c in stats['by_type'].items():
            print(f'  {t}: {c}')
            
    elif args.command == 'init':
        init_db()
        print('数据库初始化完成')
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()