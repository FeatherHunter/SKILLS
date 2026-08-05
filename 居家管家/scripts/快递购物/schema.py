# schema.py - SM5 快递购物域表结构(实施期自持载体 · D1 批收编)
#
# 规格: .scratch/v2.0-spec-map/scenes/SM5-快递购物.md(2026-08-04 定稿)
#   shopping_items(购物清单条目): id / name / quantity / source / routine /
#     status / last_done_at / note / created_at / updated_at
#   stock_thresholds(囤货阈值): id / item_id(UNIQUE) / threshold / updated_at
#
# D1 边界(2026-08-04 用户裁定,同 SM1 events.py): 物理建表归 D1 批(总账 #103 注册);
# 实施期先按本模块约定接口,本模块自带幂等建表 ensure_tables,供本域写路径原子落库;
# D1 批落地时把 DDL 收编进 scripts/home_manager/db.py init_db。
#
# 快递跟踪(SM5-3)不建表: 快递中 = item_locations.location_status='快递中'
# (已有状态体系,参考 references/statuses.md),等待天数由位置记录 created_at 推算。
from datetime import datetime


# ── 代码层枚举 ─────────────────────────────────────────────────────────────

# 清单条目来源(购物清单「来源标注:手动/缺货检测/例行」)
SOURCE_MANUAL = "手动"
SOURCE_MISSING = "缺货检测"
SOURCE_ROUTINE = "例行"

# 例行采购周期(每周/每月:周期设置,自动生成清单)
ROUTINE_WEEKLY = "每周"
ROUTINE_MONTHLY = "每月"
ROUTINE_CYCLE_DAYS = {ROUTINE_WEEKLY: 7, ROUTINE_MONTHLY: 30}

# 条目状态: 待买 / 已买(销项)
STATUS_PENDING = "待买"
STATUS_DONE = "已买"

# 缺货检测默认阈值(规格「阈值未设置物品 → 按默认阈值估算+标注」)
DEFAULT_THRESHOLD = 1

# 快递超时默认天数(规格「超时提醒:快递中 > N 天,默认 7,顺路提醒机制」)
DEFAULT_TIMEOUT_DAYS = 7

# 库存状态(囤货盘点:充足/低/空)
STOCK_FULL = "充足"
STOCK_LOW = "低"
STOCK_EMPTY = "空"

# 计入「当前库存」的位置状态(快递中未收到不算在库;已用完/已废弃/借用中/维修中等不算)
STOCK_STATUSES = ("在家", "备用")


# ── DDL(幂等;D1 批正式收编)────────────────────────────────────────────────

_SHOPPING_DDL = """
CREATE TABLE IF NOT EXISTS shopping_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    source TEXT NOT NULL DEFAULT '手动',
    routine TEXT,
    status TEXT NOT NULL DEFAULT '待买',
    last_done_at TEXT,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""
_THRESHOLD_DDL = """
CREATE TABLE IF NOT EXISTS stock_thresholds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL UNIQUE,
    threshold INTEGER NOT NULL,
    updated_at TEXT NOT NULL
)
"""
_ALL_DDL = [_SHOPPING_DDL, _THRESHOLD_DDL]


def ensure_tables(conn):
    """幂等建表(SM5 域内自持载体;D1 批把 DDL 收编进 db.py init_db)"""
    cursor = conn.cursor()
    for ddl in _ALL_DDL:
        cursor.execute(ddl)
    conn.commit()


def now_str():
    """本地时间(ADR-0001)"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
