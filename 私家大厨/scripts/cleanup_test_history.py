#!/usr/bin/env python3
"""
私人大厨 · 清理 P0-4 FAT 真测副作用
删除 cook_date = 2026-07-28 的历史(测试时 case 13/14 写入)
真实数据 cook_date = 2026-07-21 seq=1 保留
"""
import sqlite3
import os
from pathlib import Path

DB = Path(os.environ.get("SKILLS_DB_PATH", "D:/2Study/StudyNotes/.db")) / "chef_data.db"

def main():
    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()
    cur.execute("DELETE FROM recipe_history WHERE cook_date = '2026-07-28'")
    deleted = cur.rowcount
    conn.commit()
    print(f"✅ 删 {deleted} 行测试副作用(2026-07-28)")
    cur.execute("SELECT cook_date, cook_sequence, rating, feedback FROM recipe_history")
    print("\n保留:")
    for row in cur.fetchall():
        print(f"  {row[0]} seq={row[1]} rating={row[2]} feedback={row[3]}")
    conn.close()

if __name__ == "__main__":
    main()
