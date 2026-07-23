"""cleanup_test_items.py
清理所有 TEST_ 前缀测试残留物品

用法:
  python3 scripts/cleanup_test_items.py
  python3 scripts/cleanup_test_items.py --dry-run  # 仅预览不删

应用场景:
  - 测试中途崩溃, fixture cleanup 未跑
  - 手动开发调试时写入了 TEST_ 物品
  - 定期清理 (cron / 手动)
"""
import argparse
import sqlite3
import sys
from pathlib import Path

# DB 路径从 home_manager.db 读取, 避免硬编码错误
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from home_manager.db import DB_PATH as DB_PATH_FROM_DB
    DB_PATH = Path(DB_PATH_FROM_DB)
except Exception:
    DB_PATH = Path(__file__).parent.parent / ".db" / "home.db"


def find_test_items(conn):
    return conn.execute(
        "SELECT id, name FROM items WHERE name LIKE 'TEST\\_%' ESCAPE '\\'"
    ).fetchall()


def main():
    parser = argparse.ArgumentParser(description="清理 TEST_ 前缀测试物品")
    parser.add_argument("--dry-run", action="store_true", help="仅预览不删除")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"❌ DB 不存在: {DB_PATH}")
        return 1

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = find_test_items(conn)
        if not rows:
            print("✓ 无 TEST_ 前缀物品, 无需清理")
            return 0
        print(f"找到 {len(rows)} 条 TEST_ 前缀物品:")
        for row in rows[:20]:
            print(f"  ID {row[0]:>5} | {row[1]}")
        if len(rows) > 20:
            print(f"  ... 还有 {len(rows)-20} 条")
        if args.dry_run:
            print("\n(--dry-run 模式, 未实际删除)")
            return 0
        deleted = conn.execute(
            "DELETE FROM items WHERE name LIKE 'TEST\\_%' ESCAPE '\\'"
        ).rowcount
        conn.commit()
        print(f"\n✓ 已删除 {deleted} 条")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())