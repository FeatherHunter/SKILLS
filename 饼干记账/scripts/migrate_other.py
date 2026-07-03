"""
migrate_other.py — 把"其他/_未分类"和"其他收入/_未分类"按规则链细分类
复用 backfill_multilevel.py 的 OTHER_CATEGORY_RULES

【安全】
1. 默认 dry-run 模式
2. 修改前自动导出 CSV 备份
3. 整体事务:任何环节出错自动回滚
4. EXCLUSIVE LOCK:防止并发写入
5. --force 跳过二次确认

【使用】
python migrate_other.py            # dry-run
python migrate_other.py --execute  # 执行(需 YES)
python migrate_other.py --execute --force  # 跳过确认
python migrate_other.py --rollback <backup.csv>
"""

import sys
import sqlite3
import csv
import re
from datetime import datetime
from pathlib import Path

# 复用 db.py + backfill 的规则链
sys.path.insert(0, str(Path(__file__).parent))
from db import _find_db_path, SKILL_DIR, DB_FILENAME, TABLE_NAME, init_db
from backfill_multilevel import OTHER_CATEGORY_RULES

DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)
BACKUP_DIR = Path(__file__).parent.parent / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

TARGET_CATEGORIES = ["其他/_未分类", "其他收入/_未分类", "居家/未归类"]


def find_target_records():
    """找出两个目标 category 的所有记录"""
    conn = init_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT id, time, amount, note
            FROM {TABLE_NAME}
            WHERE category IN ({','.join('?' * len(TARGET_CATEGORIES))})
            ORDER BY time
        """, TARGET_CATEGORIES)
        return cursor.fetchall()
    finally:
        conn.close()


def simulate():
    """模拟规则链,展示每条将变成什么"""
    records = find_target_records()
    if not records:
        print("\u2713 没有目标类记录,无需迁移")
        return

    print(f"\n=== 待迁移: {len(records)} 条 ===")
    for old_cat in TARGET_CATEGORIES:
        cat_records = [r for r in records if True]  # 都属于这两个类
        # 不分组,因为不同 category 走同一规则
    # 实际上两个 category 共享规则链,所以一起处理

    buckets = {}
    unmatched = []
    for rid, time, amount, note in records:
        matched = False
        for where_clause, new_cat in OTHER_CATEGORY_RULES:
            if where_clause == "amount > 0":
                if amount > 0:
                    buckets[new_cat] = buckets.get(new_cat, 0) + 1
                    matched = True
                    break
            elif where_clause == "1=1":
                buckets[new_cat] = buckets.get(new_cat, 0) + 1
                matched = True
                break
            else:
                keywords = re.findall(r"'%([^%]+)%'", where_clause)
                if note and any(kw in note for kw in keywords):
                    buckets[new_cat] = buckets.get(new_cat, 0) + 1
                    matched = True
                    break
        if not matched:
            unmatched.append((rid, time, amount, note))

    print(f"\n按规则链模拟分布(共 {len(records)} 条):")
    for cat, cnt in sorted(buckets.items(), key=lambda x: -x[1]):
        print(f"  → {cat}: {cnt} 条")

    if unmatched:
        print(f"\n\u26a0 未匹配的 {len(unmatched)} 条(将归到兜底 '居家/未归类'):")
        for rid, time, amount, note in unmatched:
            print(f"  id={rid}  {time}  {amount:>8.2f}  {note or '(无备注)'}")


def export_backup():
    """导出所有目标类记录的 id + 当前 category"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"migrate_other_{timestamp}.csv"
    conn = init_db()
    try:
        cursor = conn.cursor()
        with open(backup_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['id', 'old_category'])
            cursor.execute(f"""
                SELECT id, category FROM {TABLE_NAME}
                WHERE category IN ({','.join('?' * len(TARGET_CATEGORIES))})
            """, TARGET_CATEGORIES)
            for row in cursor.fetchall():
                writer.writerow(row)
        return backup_file
    finally:
        conn.close()


def execute_migration():
    """整体事务执行迁移"""
    conn = init_db()
    try:
        cursor = conn.cursor()
        cursor.execute("BEGIN EXCLUSIVE")

        total_updated = 0
        for old_cat in TARGET_CATEGORIES:
            for where_clause, new_cat in OTHER_CATEGORY_RULES:
                cursor.execute(f"""
                    UPDATE {TABLE_NAME}
                    SET category = ?
                    WHERE category = ? AND ({where_clause})
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
    """根据备份反向还原"""
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
                    WHERE id = ?
                """, (row['old_category'], int(row['id'])))
                if cursor.rowcount:
                    rolled += 1
                else:
                    failed += 1
            conn.commit()
            print(f"\u2713 回滚成功 {rolled} 条,失败 {failed} 条")
    finally:
        conn.close()


def main():
    if "--rollback" in sys.argv:
        idx = sys.argv.index("--rollback")
        if idx + 1 >= len(sys.argv):
            print("用法: python migrate_other.py --rollback <backup.csv>")
            return
        rollback(Path(sys.argv[idx + 1]))
        return

    print(f"将操作的数据库: {DB_PATH}")
    print(f"备份目录: {BACKUP_DIR}")
    print(f"目标分类: {TARGET_CATEGORIES}\n")

    # 1. 模拟
    simulate()

    if "--execute" not in sys.argv:
        print("\n(dry-run 模式,未做任何修改。要执行请加 --execute 参数)")
        return

    # 2. execute 模式
    print("\n\u26a0\ufe0f 即将执行迁移:")
    print("  \u2022 把 98 笔按规则链细化到具体 L2")
    print("  \u2022 任何环节出错自动回滚")
    print("  \u2022 执行前导出 CSV 备份")

    if "--force" not in sys.argv:
        try:
            resp = input("\n输入 YES 确认执行(其它任意输入取消): ").strip()
        except EOFError:
            print("\n\u2717 非交互模式,已取消")
            return
        if resp != "YES":
            print("已取消")
            return

    # 3. 备份 + 执行
    backup = export_backup()
    print(f"\n\u2713 备份已保存: {backup}")

    try:
        updated = execute_migration()
        print(f"\n\u2713 已更新 {updated} 条记录")
        print(f"回滚: python migrate_other.py --rollback {backup}")
    except Exception as e:
        print(f"\n\u2717 执行失败,已自动回滚: {e}")


if __name__ == "__main__":
    main()
