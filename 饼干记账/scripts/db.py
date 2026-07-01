"""
数据库操作模块
负责：初始化、写入、查询（合并原 query.py 的查询函数）
"""

import sqlite3
import os
from datetime import date
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "biscuit_accountant.db"


def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 父目录 > 技能目录"""
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        return Path(env_path) / db_filename
    # 2. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            return db_dir / db_filename
    # 3. 技能目录下 .db 子目录（默认 fallback）
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename


DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)

TABLE_NAME = "bills"

# ── 数据库初始化 ─────────────────────────────────────────────────────────────

def init_db():
    """初始化SQLite数据库"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
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
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (category, time_str, amount, account, ledger, currency, note))
        conn.commit()
        record_id = cursor.lastrowid
        return {"id": record_id, "category": category, "time": time_str, "amount": amount}
    finally:
        conn.close()


def add_bill(category: str, amount: float, time_str: str,
           account: str = "", ledger: str = "生活",
           currency: str = "人民币", note: str = "") -> dict:
    """添加账单记录（只写 SQLite）"""
    result = insert_record(category, amount, time_str, account, ledger, currency, note)
    return {
        "success": True, "id": result['id'],
        "category": category, "time": time_str, "amount": amount,
        "account": account, "ledger": ledger, "currency": currency, "note": note,
    }

# ── 读取记录 ──────────────────────────────────────────────────────────────────

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
    try:
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
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_by_id(record_id: int) -> dict:
    """按ID查询单条记录"""
    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# ── 便捷查询函数（合并自原 query.py）────────────────────────────────────────

def list_today() -> list:
    """查询今日所有记录"""
    today_str = date.today().strftime("%Y-%m-%d")
    start = f"{today_str} 00:00:00"
    end = f"{today_str} 23:59:59"
    return fetch_all(from_time=start, to_time=end)


def list_date(date_str: str) -> list:
    """查询指定日期所有记录"""
    start = f"{date_str} 00:00:00"
    end = f"{date_str} 23:59:59"
    return fetch_all(from_time=start, to_time=end)


def list_date_range(from_date: str, to_date: str) -> list:
    """查询日期范围记录"""
    if not from_date or not to_date:
        raise ValueError("list_date_range requires both from_date and to_date")
    start = f"{from_date} 00:00:00"
    end = f"{to_date} 23:59:59"
    return fetch_all(from_time=start, to_time=end)


def list_by_category(category: str) -> list:
    """按分类查询所有记录"""
    return fetch_all(category=category)


def search_keyword(keyword: str) -> list:
    """搜索备注关键词"""
    return fetch_all(keyword=keyword)


def list_recent(limit: int = 10) -> list:
    """查询最近N条记录"""
    return fetch_all(limit=limit)


# ── 更新记录 ──────────────────────────────────────────────────────────────────

# 允许通过 update 子命令修改的字段(id/created_at 锁定)
_UPDATE_ALLOWED = {'category', 'time', 'amount', 'account', 'ledger', 'currency', 'note'}


def update_bill(record_id: int, **fields) -> dict:
    """按ID修改记录(白名单字段)

    Args:
        record_id: 目标记录 ID
        **fields: 待修改字段,如 category="餐饮", amount=-38.0

    Returns:
        {success: True/False, id, updated_fields} 或 {success: False, error}
    """
    updates = {k: v for k, v in fields.items() if k in _UPDATE_ALLOWED and v is not None}
    if not updates:
        raise ValueError("没有可更新的字段(至少传一个: category/time/amount/account/ledger/currency/note)")

    conn = init_db()
    try:
        cursor = conn.cursor()
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        params = list(updates.values()) + [record_id]
        cursor.execute(
            f"UPDATE {TABLE_NAME} SET {set_clause} WHERE id = ?",
            params
        )
        conn.commit()
        if cursor.rowcount == 0:
            return {"success": False, "error": f"ID={record_id} 不存在"}
        return {
            "success": True,
            "id": record_id,
            "updated_fields": list(updates.keys()),
        }
    finally:
        conn.close()
