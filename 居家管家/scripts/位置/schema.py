# 位置/schema.py - 位置体系数据结构(D1 批设计载体)
#
# D1 边界(2026-08-04 用户裁定):物理建表归 D1 批(总账 #103 → ISSUE #119/#120);
# 实施期先按本模块约定接口。本模块自带幂等 ensure_schema,供本域读写路径
# 原子落库;D1 批落地时把 DDL 收编进 scripts/home_manager/db.py init_db。
#
# location_nodes(位置体系表 · #119):
#   位置 = 自由层级(树),树结构隐含在路径字符串;节点只存规范化路径。
#   新建位置(先建后放)= INSERT 节点;空位置展示 = 节点无物品引用。
# items.fixed_location(固定位字段 · #120):
#   物品一等属性(锚定路径,可空),与当前位置分离。

# ── 路径规范化(位置体系唯一权威)───────────────────────────────────────────

SEP = "/"


def normalize_path(raw):
    """规范化位置路径:段 trim + 空段剔除 + 半角斜杠统一

    返回规范化路径字符串;非法(无有效段)返回 None。
    全角斜杠「／」与半角「/」等价;段内首尾空白剔除。
    """
    if raw is None:
        return None
    segs = [s.strip() for s in str(raw).replace("／", "/").split("/")]
    segs = [s for s in segs if s]
    if not segs:
        return None
    return SEP.join(segs)


def validate_segments(path):
    """段级命名校验:返回 (ok, 原因)。

    规则(实施定稿):段非空(规范化已保证) + 每段 1~30 字 + 禁前后空白。
    """
    if not path:
        return False, "位置路径为空"
    for seg in path.split(SEP):
        if len(seg) > 30:
            return False, f"位置段「{seg}」超过 30 字"
        if seg != seg.strip():
            return False, f"位置段「{seg}」含首尾空白"
    return True, ""


def _prefix_clause(path, col="location"):
    """路径前缀匹配 SQL 片段:匹配 path 自身或其子节点(段边界)

    如 path=卧室/衣柜 → 匹配 卧室/衣柜、卧室/衣柜/上层(不匹配 卧室/衣柜桌)
    """
    return f"({col} = ? OR {col} LIKE ?)", [path, path + "/%"]


def is_descendant_or_self(path, other):
    """other 是否为 path 的自身或后代(段边界)"""
    return other == path or other.startswith(path + SEP)


# ── DDL(D1 批 #119/#120 定义 · 幂等;D1 批正式收编)─────────────────────────

_NODES_DDL = """
CREATE TABLE IF NOT EXISTS location_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def ensure_schema(conn):
    """幂等建表 + 字段迁移(SM2 域内自持载体;D1 批把 DDL 收编进 db.py init_db)"""
    cursor = conn.cursor()
    cursor.execute(_NODES_DDL)
    cursor.execute("PRAGMA table_info(items)")
    items_cols = {row[1] for row in cursor.fetchall()}
    if "fixed_location" not in items_cols:
        cursor.execute("ALTER TABLE items ADD COLUMN fixed_location TEXT")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_items_fixed_location ON items(fixed_location)"
        )
    conn.commit()
