# tag_ops.py - 标签相关操作
from .db import get_conn


def get_tags(conn, item_id):
    """获取物品的所有标签（逗号分隔）"""
    cursor = conn.cursor()
    cursor.execute("SELECT tag FROM item_tags WHERE item_id = ? ORDER BY tag", (item_id,))
    return ",".join(row["tag"] for row in cursor.fetchall())


def set_tags(conn, item_id, tags_str):
    """设置物品标签（先删后插）"""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM item_tags WHERE item_id = ?", (item_id,))
    if tags_str:
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        for tag in tags:
            cursor.execute(
                "INSERT OR IGNORE INTO item_tags (item_id, tag) VALUES (?, ?)",
                (item_id, tag)
            )


def add_tag(conn, item_id, tag):
    """给物品加一个标签（接受 conn，与 update_item 同一事务）"""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO item_tags (item_id, tag) VALUES (?, ?)",
        (item_id, tag)
    )


def remove_tag(conn, item_id, tag):
    """给物品删一个标签（接受 conn，与 update_item 同一事务）"""
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM item_tags WHERE item_id = ? AND tag = ?",
        (item_id, tag)
    )


def tag_merge(from_tag, to_tag):
    """将所有 from_tag 替换为 to_tag"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as cnt FROM item_tags WHERE tag = ?", (from_tag,))
    from_count = cursor.fetchone()["cnt"]
    if from_count == 0:
        print(f"标签 '{from_tag}' 不存在")
        conn.close()
        return 1

    cursor.execute("SELECT item_id FROM item_tags WHERE tag = ?", (from_tag,))
    item_ids = [row["item_id"] for row in cursor.fetchall()]

    for item_id in item_ids:
        cursor.execute(
            "INSERT OR IGNORE INTO item_tags (item_id, tag) VALUES (?, ?)",
            (item_id, to_tag)
        )
        cursor.execute(
            "DELETE FROM item_tags WHERE item_id = ? AND tag = ?",
            (item_id, from_tag)
        )

    conn.commit()
    conn.close()
    print(f"✓ 已将 {from_count} 个 '{from_tag}' 合并为 '{to_tag}'")
    return 0


def list_tags():
    """列出所有标签及使用次数"""
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tag, COUNT(*) as cnt FROM item_tags
        GROUP BY tag ORDER BY cnt DESC
    """)
    rows = cursor.fetchall()

    if not rows:
        print("(暂无标签)")
    else:
        print(f"共 {len(rows)} 个标签：")
        for row in rows:
            print(f"  {row['tag']} ({row['cnt']})")

    conn.close()
    return 0
