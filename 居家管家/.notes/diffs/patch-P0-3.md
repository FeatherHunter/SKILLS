# Patch P0-3: category_manager --force 改为方案 C(自动 backup)

## 目标
- 你选择方案 C:`--force` 不加 `--yes`(老调用方式不破),但执行前自动 backup categories 表到 `.bak/categories_YYYYMMDD_HHMMSS.sql`
- 5 秒内可回滚

## 改动文件
- `scripts/category_manager.py` cmd_import()

## diff 草案

```python
# ── 替换原 --force 分支 ──────────────────────────
if args.force and existing > 0:
    # 自动 backup(防 AI 或人误操作)
    from datetime import datetime
    bak_dir = SKILL_DIR / ".bak"
    bak_dir.mkdir(parents=True, exist_ok=True)
    bak_file = bak_dir / f"categories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    with open(bak_file, "w", encoding="utf-8") as f:
        f.write(f"-- categories 表自动备份 (执行 --force 前)\n")
        f.write(f"-- 原 {existing} 条记录\n")
        for row in cursor.execute("SELECT id,parent_id,name,description,sort_order,is_active,created_at,updated_at FROM categories"):
            safe = str(dict(row)).replace("'", "''")
            f.write(f"INSERT INTO categories VALUES({row['id']},{row['parent_id'] or 'NULL'},'{row['name'].replace(chr(39),chr(39)+chr(39))}','{(row['description'] or '').replace(chr(39),chr(39)+chr(39))}',{row['sort_order']},{row['is_active']},'{row['created_at']}','{row['updated_at']}');\n")
    print(f"  💾 已备份 categories 到 {bak_file}")

    # 加 FK SET NULL(items.category_id 自动变 NULL,不悬空)
    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DELETE FROM categories")
    cursor.execute("UPDATE items SET category_id = NULL WHERE category_id IS NOT NULL")
    cursor.execute("PRAGMA foreign_keys = ON")
    items_unlinked = cursor.execute("SELECT changes()").fetchone()[0]
    print(f"  (清空 {existing} 条旧 categories + 解绑 {items_unlinked} 件 items)")
elif args.merge:
    print(f"  (合并模式:已有 {existing} 条,同名节点将跳过)")
```

## 验证(隔离 temp DB)
```bash
T=$(mktemp -d)
cp /mnt/d/2Study/StudyNotes/.db/home.db "$T/home.db"
SKILLS_DB_PATH="$T" python3 scripts/category_manager.py import seed.json --force
# 期望: 出现 "💾 已备份 categories 到 ..." + items 自动解绑而非悬空
python3 -c "import sqlite3,os;c=sqlite3.connect(os.path.join('$T','home.db'));c.execute('PRAGMA foreign_keys=ON');print('FK violations:', len(c.execute('PRAGMA foreign_key_check').fetchall()))"
# 期望: 0 FK violations(原来 858,现在 0)
ls "$T/居家管家/.bak/" 2>/dev/null || ls "$(dirname $T)/居家管家/.bak/" 2>/dev/null
# 期望:categories_*.sql 文件存在
rm -rf "$T"
```

## 风险
- backup 文件累积:`.bak/` 目录可能堆大量 SQL。需要清理脚本(下次改进)
- 不防"AI 不读警告继续":这是方案 C 的代价,只防"AI 静默成功"