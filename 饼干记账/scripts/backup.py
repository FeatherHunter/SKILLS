#!/usr/bin/env python3
"""
饼干记账 · 备份机制(公共层 · T0 #164 清单第 9 项)

备份 = db + goals.json(G2 决议;goals.json 为目标域载体,存在才备份)
备份目录 = $DATA_DIR/biscuit_accountant_backups/<YYYYMMDD_HHMMSS>/
恢复前自动备份现状(防覆盖丢失);软删契约:自有备份恢复原样保留(G7)

用法:
    python3 scripts/backup.py create            # 一键备份
    python3 scripts/backup.py list              # 查看备份
    python3 scripts/backup.py restore <名称>    # 从备份恢复
"""

import sys
import shutil
import argparse
import sqlite3
from pathlib import Path
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

SKILL_DIR = _SCRIPT_DIR.parent
GOALS_FILENAME = "goals.json"


def _data_dir() -> Path:
    """数据目录 = db 文件所在目录(SKILLS_DB_PATH env > D:/.db fallback)"""
    from db import _find_db_path, DB_FILENAME
    return _find_db_path(SKILL_DIR, DB_FILENAME).parent


def backups_dir(*, mkdir: bool = True) -> Path:
    """备份目录 = $DATA_DIR/biscuit_accountant_backups/"""
    d = _data_dir() / "biscuit_accountant_backups"
    if mkdir:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _db_path() -> Path:
    from db import _find_db_path, DB_FILENAME
    return _find_db_path(SKILL_DIR, DB_FILENAME)


def _goals_path() -> Path:
    return _data_dir() / GOALS_FILENAME


def create_backup() -> Path:
    """一键备份:db + goals.json → 备份目录/<时间戳>[/_N]/;goals.json 存在才备份"""
    bdir = backups_dir()
    # 防同名冲突:同一秒内多次备份 → 追加 _2/_3 后缀
    base = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = bdir / base
    n = 2
    while target.exists():
        target = bdir / f"{base}_{n}"
        n += 1
    target.mkdir(parents=True)

    copied = []
    dbp = _db_path()
    if dbp.exists():
        shutil.copy2(dbp, target / dbp.name)
        copied.append(f"{dbp.name} ({dbp.stat().st_size} 字节)")
    else:
        copied.append(f"{dbp.name} (⚠ 数据库不存在,跳过)")

    gp = _goals_path()
    if gp.exists():
        shutil.copy2(gp, target / gp.name)
        copied.append(f"{gp.name} ({gp.stat().st_size} 字节)")
    else:
        copied.append(f"{gp.name} (不存在,跳过)")

    print(f"✓ 备份完成: {target}")
    for c in copied:
        print(f"   · {c}")
    return target


def list_backups() -> list:
    """列出备份(名称/时间/文件/大小)"""
    bdir = backups_dir(mkdir=False)
    if not bdir.exists():
        print("⚠ 暂无备份")
        return []
    items = []
    for d in sorted(bdir.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        files = []
        size = 0
        for f in d.iterdir():
            files.append(f.name)
            size += f.stat().st_size
        items.append(d)
        print(f"· {d.name}  ({size} 字节 · {', '.join(files)})")
    if not items:
        print("⚠ 备份目录为空")
    return items


def restore_backup(name: str) -> Path:
    """从备份恢复:先自动备份现状(防覆盖丢失)→ 拷贝回数据目录 → 校验 db 可打开"""
    bdir = backups_dir(mkdir=False)
    src = bdir / name
    if not src.is_dir():
        print(f"✗ 备份不存在: {name} (可用 list 查看)")
        sys.exit(1)

    # 1. 恢复前自动备份现状
    print(f"🛡 恢复前自动备份现状…")
    safety = create_backup()

    # 2. 拷贝回数据目录
    restored = []
    for f in src.iterdir():
        if f.is_file():
            shutil.copy2(f, _data_dir() / f.name)
            restored.append(f.name)
    if not restored:
        print(f"✗ 备份 {name} 内无文件")
        sys.exit(1)

    # 3. 校验 db 可打开
    dbp = _db_path()
    if dbp.exists():
        try:
            conn = sqlite3.connect(str(dbp))
            conn.execute("SELECT 1 FROM bills LIMIT 1")
            conn.close()
            print("✓ db 校验通过(可正常打开)")
        except sqlite3.Error as e:
            print(f"⚠ db 校验异常: {e} (备份文件可能损坏,现状备份在 {safety})")
            sys.exit(1)

    print(f"✓ 已从备份恢复: {name} → {', '.join(restored)}")
    print(f"  恢复前现状已备份: {safety}")
    return src


def main():
    parser = argparse.ArgumentParser(description="饼干记账 · 备份机制")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create", help="一键备份(db + goals.json)")
    sub.add_parser("list", help="查看备份")
    p_restore = sub.add_parser("restore", help="从备份恢复")
    p_restore.add_argument("name", help="备份名称(如 20260808_090000)")
    args = parser.parse_args()

    if args.cmd == "create":
        create_backup()
    elif args.cmd == "list":
        list_backups()
    elif args.cmd == "restore":
        restore_backup(args.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
