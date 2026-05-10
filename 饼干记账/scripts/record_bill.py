#!/usr/bin/env python3
"""
账单记录脚本 v2.0
- SQLite 数据库存储（结构化查询）
- 每日账单文件（CSV格式，人类可读）
- 双写模式：同时写入数据库和文件

数据库字段：分类, 时间, 金额, 账户, 账本, 货币, 备注

存储路径：
  - WSL: /mnt/d/2Study/StudyNotes/{年份}/个人/{日期}/bills_{日期}.md
  - Windows: D:\2Study\StudyNotes\{年份}\个人\{日期}\bills_{日期}.md
"""

import sqlite3
import csv
import os
import sys
from datetime import date, datetime
from pathlib import Path

# ── 配置 ─────────────────────────────────────────────────────────────────────

# 数据库路径 - 三层查找：环境变量 > 技能目录 > 父目录.db
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "biscuit_accountant.db"

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

DB_DIR = SKILL_DIR
DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)

# 获取今日日期
TODAY = date.today()
YEAR_STR = str(TODAY.year)
DATE_STR = TODAY.strftime("%Y%m%d")  # 如 20260507
DATE_FILE_STR = TODAY.strftime("%Y-%m-%d")  # 如 2026-05-07

# 每日账单文件目录（WSL路径）
BILLS_DIR = Path(f"/mnt/d/2Study/StudyNotes/{YEAR_STR}/个人/{DATE_STR}")
BILLS_FILE = BILLS_DIR / f"bills_{DATE_FILE_STR}.md"

# 数据库表名
TABLE_NAME = "bills"

# ── 数据库初始化 ─────────────────────────────────────────────────────────────

def init_db():
    """初始化SQLite数据库"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            time TEXT NOT NULL,
            amount REAL NOT NULL,
            account TEXT DEFAULT '',
            ledger TEXT DEFAULT '生活',
            currency TEXT DEFAULT '人民币',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 创建索引加速查询
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_bills_time ON {TABLE_NAME}(time)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_bills_category ON {TABLE_NAME}(category)")
    conn.commit()
    return conn

# ── 写入数据库 ────────────────────────────────────────────────────────────────

def add_record_db(category: str, amount: float, time_str: str,
                  account: str = "", ledger: str = "生活",
                  currency: str = "人民币", note: str = "") -> dict:
    """写入数据库"""
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (category, time_str, amount, account, ledger, currency, note))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return {"id": record_id, "category": category, "time": time_str, "amount": amount}

# ── 写入每日文件 ─────────────────────────────────────────────────────────────

def write_daily_bill_file(records: list):
    """追加记录到每日账单文件（CSV格式）"""
    # 确保目录存在
    BILLS_DIR.mkdir(parents=True, exist_ok=True)
    
    file_exists = BILLS_FILE.exists()
    
    with open(BILLS_FILE, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        # 首次写入时加表头
        if not file_exists:
            writer.writerow(['分类', '时间', '金额', '账户', '账本', '货币', '备注'])
        for r in records:
            writer.writerow([
                r['category'],
                r['time'],
                r['amount'],
                r.get('account', ''),
                r.get('ledger', '生活'),
                r.get('currency', '人民币'),
                r.get('note', '')
            ])

# ── 添加记录（双写） ─────────────────────────────────────────────────────────

def add_bill(category: str, amount: float, time_str: str,
            account: str = "", ledger: str = "生活",
            currency: str = "人民币", note: str = "") -> dict:
    """添加账单记录，同时写入数据库和每日文件"""
    
    # 写入数据库
    result = add_record_db(category, amount, time_str, account, ledger, currency, note)
    
    # 写入每日文件
    write_daily_bill_file([{
        'category': category,
        'time': time_str,
        'amount': amount,
        'account': account,
        'ledger': ledger,
        'currency': currency,
        'note': note
    }])
    
    return {
        "success": True,
        "id": result['id'],
        "category": category,
        "time": time_str,
        "amount": amount,
        "account": account,
        "ledger": ledger,
        "currency": currency,
        "note": note,
        "file": str(BILLS_FILE)
    }

# ── 查询功能 ──────────────────────────────────────────────────────────────────

def list_today() -> list:
    """查询今日所有记录"""
    conn = init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    today_start = f"{DATE_FILE_STR} 00:00:00"
    today_end = f"{DATE_FILE_STR} 23:59:59"
    
    cursor.execute(f"""
        SELECT * FROM {TABLE_NAME} 
        WHERE time >= ? AND time <= ?
        ORDER BY time DESC
    """, (today_start, today_end))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_date(date_str: str) -> list:
    """查询指定日期所有记录"""
    conn = init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    start = f"{date_str} 00:00:00"
    end = f"{date_str} 23:59:59"
    
    cursor.execute(f"""
        SELECT * FROM {TABLE_NAME} 
        WHERE time >= ? AND time <= ?
        ORDER BY time DESC
    """, (start, end))
    
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def monthly_summary(month: str) -> dict:
    """月度汇总（YYYY-MM格式）"""
    conn = init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    start = f"{month}-01 00:00:00"
    # 计算月末
    month_int = int(month.split("-")[1])
    year_int = int(month.split("-")[0])
    if month_int == 12:
        end_month = f"{year_int + 1}-01"
    else:
        end_month = f"{year_int}-{month_int + 1:02d}"
    end = f"{end_month}-01 00:00:00"
    
    cursor.execute(f"""
        SELECT category, 
               SUM(amount) as total,
               COUNT(*) as count
        FROM {TABLE_NAME} 
        WHERE time >= ? AND time < ?
        GROUP BY category
        ORDER BY total
    """, (start, end))
    
    rows = cursor.fetchall()
    
    # 计算总计
    cursor.execute(f"""
        SELECT 
            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income
        FROM {TABLE_NAME} 
        WHERE time >= ? AND time < ?
    """, (start, end))
    
    totals = cursor.fetchone()
    conn.close()
    
    return {
        "month": month,
        "categories": [dict(row) for row in rows],
        "total_expense": totals['expense'] or 0,
        "total_income": totals['income'] or 0,
        "net": (totals['income'] or 0) - (totals['expense'] or 0)
    }


def get_today_summary() -> dict:
    """获取今日摘要"""
    conn = init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    today_start = f"{DATE_FILE_STR} 00:00:00"
    today_end = f"{DATE_FILE_STR} 23:59:59"
    
    cursor.execute(f"""
        SELECT 
            COUNT(*) as count,
            SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
            SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income
        FROM {TABLE_NAME} 
        WHERE time >= ? AND time <= ?
    """, (today_start, today_end))
    
    row = cursor.fetchone()
    conn.close()
    
    return {
        "date": DATE_FILE_STR,
        "count": row['count'] or 0,
        "expense": row['expense'] or 0,
        "income": row['income'] or 0,
        "net": (row['income'] or 0) - (row['expense'] or 0),
        "file": str(BILLS_FILE)
    }


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="个人记账工具 v2.0")
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # add 子命令
    add_parser = subparsers.add_parser('add', help='添加账单')
    add_parser.add_argument('--category', required=True, help='分类')
    add_parser.add_argument('--amount', required=True, type=float, help='金额（负数为支出）')
    add_parser.add_argument('--time', default=None, help='时间 YYYY-MM-DD HH:MM:SS')
    add_parser.add_argument('--account', default='', help='账户')
    add_parser.add_argument('--ledger', default='生活', help='账本')
    add_parser.add_argument('--currency', default='人民币', help='货币')
    add_parser.add_argument('--note', default='', help='备注')
    
    # list 子命令
    list_parser = subparsers.add_parser('list', help='查询记录')
    list_parser.add_argument('--date', default=None, help='日期 YYYY-MM-DD')
    
    # summary 子命令
    summary_parser = subparsers.add_parser('summary', help='今日摘要')
    
    # monthly 子命令
    monthly_parser = subparsers.add_parser('monthly', help='月度汇总')
    monthly_parser.add_argument('--month', required=True, help='月份 YYYY-MM')
    
    args = parser.parse_args()
    
    if args.command == 'add':
        time_str = args.time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = add_bill(
            category=args.category,
            amount=args.amount,
            time_str=time_str,
            account=args.account,
            ledger=args.ledger,
            currency=args.currency,
            note=args.note
        )
        print(f"✓ 已记录：{result['category']} {result['amount']:.2f}")
        
    elif args.command == 'list':
        if args.date:
            records = list_date(args.date)
        else:
            records = list_today()
        for r in records:
            print(f"{r['time']} | {r['category']} | {r['amount']:.2f} | {r['note']}")
            
    elif args.command == 'summary':
        result = get_today_summary()
        print(f"今日 {result['date']}")
        print(f"记录数: {result['count']}")
        print(f"支出: {result['expense']:.2f}")
        print(f"收入: {result['income']:.2f}")
        print(f"净额: {result['net']:.2f}")
        
    elif args.command == 'monthly':
        result = monthly_summary(args.month)
        print(f"=== {args.month} 月度汇总 ===")
        print(f"支出: {result['total_expense']:.2f}")
        print(f"收入: {result['total_income']:.2f}")
        print(f"净额: {result['net']:.2f}")
        print("\n分类明细:")
        for c in result['categories']:
            print(f"  {c['category']}: {c['total']:.2f} ({c['count']}笔)")
            
    else:
        parser.print_help()


if __name__ == "__main__":
    main()