"""
backfill_multilevel.py — 一次性 backfill 脚本
把旧的不含 / 的 category 值批量更新为 L1/_未分类 形式

【安全设计】
1. 默认 dry-run 模式,只打印不写
2. 修改前自动导出 CSV 备份
3. 只动 category 字段,不动其他字段、行、时间、金额
4. 整体事务:任何环节出错自动回滚
5. EXCLUSIVE LOCK:防止并发写入
6. --execute 模式需要输入 YES 二次确认
7. 提供 --rollback 参数:根据 CSV 备份反向还原

【使用】
python backfill_multilevel.py              # dry-run,预览
python backfill_multilevel.py --execute   # 实际执行(需 YES 确认)
python backfill_multilevel.py --rollback <backup.csv>  # 回滚
"""

import sqlite3
import csv
import sys
from datetime import datetime
from pathlib import Path

# 复用 db.py 的路径查找逻辑
sys.path.insert(0, str(Path(__file__).parent))
from db import _find_db_path, SKILL_DIR, DB_FILENAME, TABLE_NAME, init_db

DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)
BACKUP_DIR = Path(__file__).parent.parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)


def find_old_categories():
    """找出所有不含 / 的 category 值及记录数"""
    conn = init_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT category, COUNT(*) as cnt
            FROM {TABLE_NAME}
            WHERE category != ''
              AND category NOT LIKE '%/%'
            GROUP BY category
            ORDER BY category
        """)
        return cursor.fetchall()
    finally:
        conn.close()


def preview_changes():
    """预览要做的修改,返回 (old_cat, new_cat, count) 列表"""
    old_cats = find_old_categories()
    if not old_cats:
        print("\u2713 数据库中没有旧值(category 都不含 /),无需 backfill")
        return []

    print(f"\n=== 即将更新的 category 值 ===")
    print(f"{'原值':<20} {'记录数':<8} {'新值'}")
    print("-" * 55)
    changes = []
    for cat, cnt in old_cats:
        new_cat = f"{cat}/_未分类"
        changes.append((cat, new_cat, cnt))
        print(f"{cat:<20} {cnt:<8} {new_cat}")

    total = sum(cnt for _, _, cnt in changes)
    print(f"\n共 {len(changes)} 个旧值,影响 {total} 条记录")
    return changes


def export_backup(changes):
    """导出备份 CSV:每个旧值对应的所有记录 id + 原 category + 新 category"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"backfill_{timestamp}.csv"

    conn = init_db()
    try:
        cursor = conn.cursor()
        with open(backup_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'old_category', 'new_category'])
            for old_cat, new_cat, _ in changes:
                cursor.execute(f"""
                    SELECT id FROM {TABLE_NAME}
                    WHERE category = ? AND category NOT LIKE '%/%'
                """, (old_cat,))
                for (record_id,) in cursor.fetchall():
                    writer.writerow([record_id, old_cat, new_cat])
        return backup_file
    finally:
        conn.close()


def execute_changes(changes):
    """整体事务执行 backfill,异常自动回滚"""
    conn = init_db()
    try:
        cursor = conn.cursor()
        # EXCLUSIVE LOCK 防止并发写入
        cursor.execute("BEGIN EXCLUSIVE")

        total_updated = 0
        for old_cat, new_cat, _ in changes:
            cursor.execute(f"""
                UPDATE {TABLE_NAME}
                SET category = ?
                WHERE category = ? AND category NOT LIKE '%/%'
            """, (new_cat, old_cat))
            total_updated += cursor.rowcount

        conn.commit()
        return total_updated
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def rollback(backup_file: Path):
    """根据备份 CSV 反向 UPDATE 还原"""
    if not backup_file.exists():
        print(f"\u2717 备份文件不存在: {backup_file}")
        return

    conn = init_db()
    try:
        cursor = conn.cursor()
        rolled = 0
        failed = 0
        with open(backup_file, encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cursor.execute(f"""
                    UPDATE {TABLE_NAME}
                    SET category = ?
                    WHERE id = ? AND category = ?
                """, (row['old_category'], int(row['id']), row['new_category']))
                if cursor.rowcount:
                    rolled += 1
                else:
                    failed += 1
            conn.commit()
            print(f"\u2713 回滚成功 {rolled} 条,失败 {failed} 条(可能已被手动改过)")
    finally:
        conn.close()


def main():
    if "--rollback" in sys.argv:
        idx = sys.argv.index("--rollback")
        if idx + 1 >= len(sys.argv):
            print("用法: python backfill_multilevel.py --rollback <backup.csv>")
            return
        rollback(Path(sys.argv[idx + 1]))
        return

    # 1. 展示 DB 路径(dry-run 也要展示)
    print(f"将操作的数据库: {DB_PATH}")
    print(f"备份目录: {BACKUP_DIR}")
    print()

    # 2. 预览变更
    changes = preview_changes()
    if not changes:
        return

    # 3. dry-run 模式直接退出
    if "--execute" not in sys.argv:
        print("\n(dry-run 模式,未做任何修改。要执行请加 --execute 参数)")
        return

    # 4. execute 模式:最后确认
    print("\n\u26a0\ufe0f 即将执行 backfill:")
    print("  \u2022 所有旧 category 值会改成 L1/_未分类")
    print("  \u2022 任何环节出错会自动回滚(整体事务)")
    print("  \u2022 执行前会导出 CSV 备份到 backups/ 目录")
    try:
        resp = input("\n输入 YES 确认执行(其它任意输入取消): ").strip()
    except EOFError:
        print("\n\u2717 非交互模式,已取消(避免误执行)")
        return
    if resp != "YES":
        print("已取消")
        return

    # 5. 备份 + 执行
    backup = export_backup(changes)
    print(f"\n\u2713 备份已保存: {backup}")

    try:
        updated = execute_changes(changes)
        print(f"\n\u2713 已更新 {updated} 条记录")
        print(f"\n回滚命令(如有需要):")
        print(f"  python backfill_multilevel.py --rollback {backup}")
    except Exception as e:
        print(f"\n\u2717 执行失败,已自动回滚: {e}")


if __name__ == "__main__":
    main()