"""饼干记账 · 账户/账本脏名归并脚本(幂等)

用法:
    python merge_dirty_names.py --db <数据库路径> --mapping <映射.json> [--backup-dir <备份目录>] [--dry-run]

映射文件格式(不入库,含真实账户名,用后即弃):
    {
      "account": {"源变体": "规范名", ...},
      "ledger": {"源变体": "规范名", ...}
    }

流程(执行纪律 · issue #156):
    1. 备份: 复制 db + CSV 全量导出 → 备份目录/<时间戳>/
    2. 冒烟: 只读校验 db 可打开、bills 表存在、统计归并命中
    3. 执行: 按映射 UPDATE(仅改命中的源值,目标值无副作用)
    4. 验证: DISTINCT 无残留变体 + 记录总数不变

幂等性: 二次执行命中 0 条,不产生任何变更。
"""
import argparse
import csv
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def _load_mapping(path: Path) -> dict:
    """读取映射 JSON,校验结构"""
    if not path.exists():
        sys.exit(f"✗ 映射文件不存在: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    for field in ("account", "ledger"):
        if field not in data or not isinstance(data[field], dict):
            sys.exit(f"✗ 映射文件缺少 {field} 字段(须为 dict)")
    return data


def _backup(db_path: Path, backup_dir: Path) -> Path:
    """1. 备份: 复制 db + CSV 全量导出"""
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / stamp
    n = 2
    while target.exists():
        target = backup_dir / f"{stamp}_{n}"
        n += 1
    target.mkdir(parents=True)

    shutil.copy2(db_path, target / db_path.name)
    print(f"✓ db 备份: {target / db_path.name}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT id, category, time, amount, account, ledger, currency, note, deleted_at FROM bills ORDER BY id"
    ).fetchall()
    csv_path = target / f"bills_full_{stamp}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "category", "time", "amount", "account", "ledger", "currency", "note", "deleted_at"])
        for r in rows:
            writer.writerow([r["id"], r["category"], r["time"], r["amount"],
                             r["account"], r["ledger"], r["currency"], r["note"], r["deleted_at"]])
    conn.close()
    print(f"✓ CSV 全量导出: {csv_path} ({len(rows)} 行)")
    return target


def _smoke(conn: sqlite3.Connection, mapping: dict) -> None:
    """2. 冒烟: 只读校验 db 可打开 + 统计命中"""
    cur = conn.cursor()
    total = cur.execute("SELECT COUNT(*) FROM bills").fetchone()[0]
    print(f"✓ 冒烟通过: bills 共 {total} 条")

    for field in ("account", "ledger"):
        for src in mapping[field]:
            cnt = cur.execute(
                f"SELECT COUNT(*) FROM bills WHERE {field} = ?", (src,)
            ).fetchone()[0]
            print(f"  命中 {field}='{src}' → {cnt} 条")


def _apply(conn: sqlite3.Connection, mapping: dict) -> dict:
    """3. 执行归并 UPDATE,返回各映射命中数"""
    cur = conn.cursor()
    stats = {"account": {}, "ledger": {}}
    for field in ("account", "ledger"):
        for src, dst in mapping[field].items():
            cur.execute(
                f"UPDATE bills SET {field} = ? WHERE {field} = ?", (dst, src)
            )
            stats[field][src] = cur.rowcount
    conn.commit()
    return stats


def _verify(conn: sqlite3.Connection, total_before: int, mapping: dict) -> None:
    """4. 验证: DISTINCT 无残留变体 + 记录总数不变"""
    cur = conn.cursor()
    total_after = cur.execute("SELECT COUNT(*) FROM bills").fetchone()[0]
    assert total_after == total_before, f"记录数变化! {total_before} → {total_after}"
    print(f"✓ 记录总数不变: {total_after}")

    for field in ("account", "ledger"):
        residual = [src for src in mapping[field]
                    if cur.execute(f"SELECT COUNT(*) FROM bills WHERE {field} = ?", (src,)).fetchone()[0] > 0]
        if residual:
            raise SystemExit(f"✗ 变体残留! {field}: {residual}")
        print(f"✓ {field} 无残留变体")
        print(f"  DISTINCT: {[r[0] for r in cur.execute(f'SELECT DISTINCT {field} FROM bills ORDER BY {field}')]}")


def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 账户/账本脏名归并(幂等)")
    parser.add_argument("--db", required=True, type=Path, help="目标数据库路径(执行人: 真实库)")
    parser.add_argument("--mapping", required=True, type=Path, help="归并映射 JSON(不入库,含真实账户名)")
    parser.add_argument("--backup-dir", type=Path, default=None, help="备份目录(默认: db 所在目录/biscuit_accountant_backups)")
    parser.add_argument("--dry-run", action="store_true", help="只跑备份+冒烟+统计,不执行 UPDATE")
    args = parser.parse_args()

    db_path = args.db.resolve()
    if not db_path.exists():
        sys.exit(f"✗ 数据库不存在: {db_path}")
    mapping = _load_mapping(args.mapping)

    backup_dir = args.backup_dir or (db_path.parent / "biscuit_accountant_backups")
    print(f"══ 备份 ══")
    bdir = _backup(db_path, backup_dir)

    conn = sqlite3.connect(str(db_path))
    try:
        print(f"══ 冒烟 ══")
        _smoke(conn, mapping)
        total_before = conn.execute("SELECT COUNT(*) FROM bills").fetchone()[0]

        if args.dry_run:
            print(f"══ DRY-RUN: 不执行 UPDATE ══")
            return 0

        print(f"══ 执行归并 ══")
        stats = _apply(conn, mapping)
        for field in ("account", "ledger"):
            for src, cnt in stats[field].items():
                flag = "✓" if cnt else "·"
                print(f"  {flag} {field} '{src}' → {mapping[field][src]}: {cnt} 条")

        print(f"══ 验证 ══")
        _verify(conn, total_before, mapping)
        print(f"\n✅ 归并完成 · 备份在 {bdir}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
