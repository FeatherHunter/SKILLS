#!/usr/bin/env python3
"""
私家大厨 - 数据层封装(5 层架构改造)

设计原则(来自《优秀 Skill 指导手册》):
- 单一入口:所有 SQL 走本模块
- 事务包裹:BEGIN → 操作 → COMMIT,失败自动 ROLLBACK
- 自动备份:.bak.YYYYMMDD_HHMMSS 时间戳命名
- 失败降级:底层连接错误时,事务回滚 + 抛异常给上层
- 不破坏兼容:db_config.py 保留,新代码用 db.py,老代码继续跑

使用示例:
    from db import db

    # 1. 简单查询
    rows = db.query("SELECT id, name FROM recipes WHERE status != '已废弃'")
    for row in rows:
        print(row["name"])

    # 2. 简单执行
    db.execute("UPDATE recipes SET name = ? WHERE id = ?", ("新菜名", "uuid"))

    # 3. 事务(自动 commit/rollback)
    with db.transaction() as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO recipes ...")
        cur.execute("INSERT INTO ingredients ...")
        # 正常退出 → COMMIT
        # 抛异常 → 自动 ROLLBACK

    # 4. 自动备份
    backup_path = db.backup()  # → chef_data.db.bak.YYYYMMDD_HHMMSS
    print(f"备份到: {backup_path}")
"""

import os
import sys
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

# db_config.py 在同目录
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_config import get_connection, get_db_path, get_db_connection


# ====================================================================
# 备份机制
# ====================================================================

def backup(db_path: str = None, reason: str = "manual") -> str:
    """
    自动备份当前数据库,生成 .bak.YYYYMMDD_HHMMSS 格式文件。

    Args:
        db_path: 数据库路径(默认当前 db_config.DB_PATH)
        reason: 备份原因(用于日志,如 "manual"/"pre-migration"/"pre-delete")

    Returns:
        备份文件路径

    Raises:
        FileNotFoundError: 源 db 不存在
    """
    src = Path(db_path) if db_path else Path(get_db_path())
    if not src.exists():
        raise FileNotFoundError(f"数据库文件不存在: {src}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak_path = src.parent / f"{src.name}.bak.{ts}"
    shutil.copy2(src, bak_path)

    # 记录备份日志
    _log_backup(bak_path, reason)
    return str(bak_path)


def _log_backup(bak_path: str, reason: str) -> None:
    """记录备份操作(追加到 .db 目录下的 backup_log.jsonl)"""
    try:
        log_path = Path(bak_path).parent / "backup_log.jsonl"
        entry = {
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "backup_path": bak_path,
            "reason": reason,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(str(entry).replace("'", '"') + "\n")
    except Exception:
        # 备份日志失败不影响主流程
        pass


# ====================================================================
# 核心 API
# ====================================================================

def execute(sql: str, params: tuple = ()) -> int:
    """
    执行单条 SQL(INSERT/UPDATE/DELETE),自动 commit。

    Returns:
        lastrowid(INSERT)或 rowcount(UPDATE/DELETE)
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        result = cur.lastrowid if cur.lastrowid else cur.rowcount
        conn.commit()
        return result


def query(sql: str, params: tuple = (), one: bool = False) -> list:
    """
    查询 SQL,返回所有行(每行是 sqlite3.Row,可用列名访问)。

    Args:
        sql: SQL 语句
        params: 参数
        one: True 时只返回第一行(None 表示无结果)
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        if one:
            row = cur.fetchone()
            return dict(row) if row else None
        rows = cur.fetchall()
        return [dict(r) for r in rows]


@contextmanager
def transaction():
    """
    事务上下文管理器。with 块内用同一个 conn。
    正常退出 → COMMIT
    异常退出 → 自动 ROLLBACK

    Usage:
        with transaction() as conn:
            cur = conn.cursor()
            cur.execute(...)
            cur.execute(...)
    """
    conn = get_connection()
    try:
        conn.execute("BEGIN")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ====================================================================
# 迁移支持
# ====================================================================

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def ensure_migrations_dir() -> Path:
    """确保 migrations 目录存在"""
    MIGRATIONS_DIR.mkdir(exist_ok=True)
    return MIGRATIONS_DIR


def list_migrations() -> list:
    """
    列出所有 migration 脚本(按文件名排序)。

    Returns:
        文件名列表(如 ["001_init.sql", "002_add_xxx.sql"])
    """
    if not MIGRATIONS_DIR.exists():
        return []
    return sorted([f.name for f in MIGRATIONS_DIR.glob("*.sql")])


def run_migration(script_name: str, dry_run: bool = False) -> dict:
    """
    跑一个 migration 脚本(自动备份后跑)。

    Args:
        script_name: 脚本文件名(如 "001_init.sql")
        dry_run: True 时只读不跑

    Returns:
        {"status": "success"/"error", "backup": "...", "executed_lines": N}
    """
    script_path = MIGRATIONS_DIR / script_name
    if not script_path.exists():
        return {"status": "error", "message": f"脚本不存在: {script_path}"}

    sql = script_path.read_text(encoding="utf-8")

    # 跑前自动备份
    if not dry_run:
        bak = backup(reason=f"pre-migration:{script_name}")

    # 跑(每个 ; 分隔的语句)
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    executed = 0
    try:
        with transaction() as conn:
            for stmt in statements:
                conn.execute(stmt)
                executed += 1
        return {
            "status": "success",
            "backup": bak if not dry_run else None,
            "executed_lines": executed
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "executed_lines": executed
        }


# ====================================================================
# CLI(独立可调用)
# ====================================================================

def main():
    """CLI:backup / list-migrations / run-migration"""
    import json
    if len(sys.argv) < 2:
        print("""用法:
    python db.py backup                      # 备份当前 db
    python db.py list-migrations             # 列出所有 migration
    python db.py run-migration <script>      # 跑一个 migration
    python db.py run-migration <script> --dry-run  # 只读不跑
""")
        return

    action = sys.argv[1]
    if action == "backup":
        try:
            bak = backup(reason="cli-manual")
            print(json.dumps({"status": "success", "backup": bak}, ensure_ascii=False, indent=2))
        except Exception as e:
            print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False, indent=2))

    elif action == "list-migrations":
        ensure_migrations_dir()
        migrations = list_migrations()
        print(json.dumps({"status": "success", "migrations": migrations}, ensure_ascii=False, indent=2))

    elif action == "run-migration":
        if len(sys.argv) < 3:
            print("请提供脚本名")
            return
        script = sys.argv[2]
        dry_run = "--dry-run" in sys.argv
        result = run_migration(script, dry_run=dry_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"未知操作: {action}")


if __name__ == "__main__":
    main()
