"""
数据库操作模块
负责：初始化、写入、读取
"""

import sqlite3
import csv
import os
from datetime import date
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────────────────────────────

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

TODAY = date.today()
YEAR_STR = str(TODAY.year)
DATE_FILE_STR = TODAY.strftime("%Y-%m-%d")

# 每日账单文件目录
BILLS_DIR = Path(f"/mnt/d/2Study/StudyNotes/{YEAR_STR}/个人/{TODAY.strftime('%Y%m%d')}")
BILLS_FILE = BILLS_DIR / f"bills_{DATE_FILE_STR}.md"

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
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_bills_time ON {TABLE_NAME}(time)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_bills_category ON {TABLE_NAME}(category)")
    conn.commit()
    return conn

# ── 写入数据库 ────────────────────────────────────────────────────────────────

def insert_record(category: str, amount: float, time_str: str,
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


def write_daily_bill_file(records: list):
    """追加记录到每日账单文件（CSV格式）"""
    BILLS_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = BILLS_FILE.exists()
    
    with open(BILLS_FILE, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['分类', '时间', '金额', '账户', '账本', '货币', '备注'])
        for r in records:
            writer.writerow([
                r['category'], r['time'], r['amount'],
                r.get('account', ''), r.get('ledger', '生活'),
                r.get('currency', '人民币'), r.get('note', '')
            ])


def add_bill(category: str, amount: float, time_str: str,
           account: str = "", ledger: str = "生活",
           currency: str = "人民币", note: str = "") -> dict:
    """添加账单记录，同时写入数据库和每日文件"""
    result = insert_record(category, amount, time_str, account, ledger, currency, note)
    write_daily_bill_file([{
        'category': category, 'time': time_str, 'amount': amount,
        'account': account, 'ledger': ledger, 'currency': currency, 'note': note
    }])
    return {
        "success": True, "id": result['id'],
        "category": category, "time": time_str, "amount": amount,
        "account": account, "ledger": ledger, "currency": currency, "note": note,
        "file": str(BILLS_FILE)
    }

# ── 读取记录（基础） ──────────────────────────────────────────────────────────

def fetch_all(category: str = None, from_time: str = None, to_time: str = None,
             keyword: str = None, limit: int = None) -> list:
    """
    通用查询接口
    - category: 按分类筛选
    - from_time / to_time: 时间范围
    - keyword: 备注关键词搜索
    - limit: 限制返回条数
    """
    conn = init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    conditions = []
    params = []
    
    if from_time:
        conditions.append("time >= ?")
        params.append(from_time)
    if to_time:
        conditions.append("time <= ?")
        params.append(to_time)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if keyword:
        conditions.append("note LIKE ?")
        params.append(f"%{keyword}%")
    
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    query = f"SELECT * FROM {TABLE_NAME}{where_clause} ORDER BY time DESC"
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_by_id(record_id: int) -> dict:
    """按ID查询单条记录"""
    conn = init_db()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None