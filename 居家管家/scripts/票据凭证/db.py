"""SM6 票据凭证域 · 域内数据库(懒建表 + 路径懒解析)

第一性原理:
  - 本域 4 张表 = 时间权益(purchase_records/warranties/service_events/certificates)
  - 遵循 D1 硬规则: 不动公共 schema(db.py); 域内自建表(沿 accounts.py v1 先例),
    数据层 D1 对账时统一评审(证件表对应 D1 总账 #11)
  - 路径懒解析: 每次调用现算 env, 便于 fixture 临时库测试(monkeypatch SKILLS_DB_PATH)
  - 与公共库同一文件(同 SKILLS_DB_PATH/home.db), 表独立, 互不干扰
"""
import os
import sqlite3
from pathlib import Path


def _resolve_db_path():
    """懒解析 DB 路径: $SKILLS_DB_PATH > 全局 fallback(与 home_manager.db 同策略)"""
    env_path = os.environ.get("SKILLS_DB_PATH")
    if env_path:
        return Path(env_path) / "home.db"
    if sys.platform == "win32":
        return Path("D:/.db") / "home.db"
    d_drive = Path("/mnt/d")
    if d_drive.exists():
        return d_drive / ".db" / "home.db"
    raise RuntimeError("SKILLS_DB_PATH 未设置,且 D: 盘未挂载到 /mnt/d/。")


def get_conn():
    """获取连接(每次现算路径 + 幂等建表)"""
    path = _resolve_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    init_domain_tables(conn)
    return conn


def init_domain_tables(conn):
    """幂等建 4 张域表(新表, 不触碰公共 schema)"""
    cur = conn.cursor()

    # 购买记录: 时间权益的「事实锚点」(价格/渠道/客服/退货窗口/票据照片)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS purchase_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL REFERENCES items(id),
            purchased_at TEXT NOT NULL,
            price REAL,
            channel TEXT DEFAULT '',
            merchant_contact TEXT DEFAULT '',
            receipt_photo TEXT DEFAULT '',
            return_window_days INTEGER DEFAULT 7,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pr_item ON purchase_records(item_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pr_date ON purchase_records(purchased_at)")

    # 保修与保养: 同一张「周期权益」表,kind 区分; 保养的 last_done_date 冗余 = 状态源
    cur.execute("""
        CREATE TABLE IF NOT EXISTS warranties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL REFERENCES items(id),
            kind TEXT NOT NULL CHECK(kind IN ('保修', '保养')),
            start_date TEXT NOT NULL,
            duration_days INTEGER NOT NULL,
            last_done_date TEXT,
            photo TEXT DEFAULT '',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_w_item ON warranties(item_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_w_kind ON warranties(kind)")

    # 保修卡照片(票据归档): 幂等迁移(老库已建表 → ALTER 补列, 新库建表自带)
    cols = {r[1] for r in cur.execute("PRAGMA table_info(warranties)").fetchall()}
    if "photo" not in cols:
        cur.execute("ALTER TABLE warranties ADD COLUMN photo TEXT DEFAULT ''")
        conn.commit()

    # 服务事件: 维修记录 + 保养执行历史(轻量)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS service_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            warranty_id INTEGER NOT NULL REFERENCES warranties(id),
            occurred_at TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK(event_type IN ('维修', '保养执行')),
            cost REAL DEFAULT 0,
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_se_warranty ON service_events(warranty_id)")

    # 证件: 固定到期权益(号码脱敏显示, 明文落库但永不进 payload/复制数据)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cert_type TEXT NOT NULL,
            holder TEXT DEFAULT '',
            cert_number TEXT DEFAULT '',
            issued_at TEXT,
            expires_at TEXT NOT NULL,
            photo TEXT DEFAULT '',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cert_expires ON certificates(expires_at)")

    conn.commit()
