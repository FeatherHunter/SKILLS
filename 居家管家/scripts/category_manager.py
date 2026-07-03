#!/usr/bin/env python3
"""category_manager.py - 居家管家 categories 表管理 CLI

最严格标准:
  - 新建独立 CLI,不污染 home_manager.py
  - 不改 db.py,只复用 get_conn
  - 复用 home_manager 的 DB_PATH(三层查找策略)

子命令:
  init              建表(幂等)
  list              列出分类
  tree              树形展示
  import <file>     从 JSON 文件批量导入(顶级 → 二级 → 三级 顺序)
  show --id N       查看分类详情
  count             统计数量
"""
import sys
import os
import json
import argparse
from pathlib import Path

# 复用 home_manager.db 的 get_conn 和 DB_PATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from home_manager.db import get_conn, DB_PATH


# ── Schema ──────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id    INTEGER,
    name         TEXT NOT NULL,
    description  TEXT,
    sort_order   INTEGER DEFAULT 0,
    is_active    INTEGER DEFAULT 1,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id);
CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);
"""


# ── 命令实现 ──────────────────────────────────────────────────────────────

def cmd_init(args):
    """建表(幂等)"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.executescript(SCHEMA)
    conn.commit()
    conn.close()
    print(f"✓ categories 表已就绪")
    print(f"  DB: {DB_PATH}")
    return 0


def cmd_list(args):
    """列出所有分类"""
    conn = get_conn()
    cursor = conn.cursor()
    if args.parent is not None:
        cursor.execute(
            "SELECT * FROM categories WHERE parent_id IS ? AND is_active = 1 ORDER BY sort_order, id",
            (args.parent,)
        )
    else:
        cursor.execute("SELECT * FROM categories WHERE is_active = 1 ORDER BY id")
    rows = cursor.fetchall()
    if not rows:
        print("(无分类)")
    else:
        print(f"共 {len(rows)} 个分类:")
        for row in rows:
            print(f"  id={row['id']:>3} parent={str(row['parent_id']):>4} name={row['name']}")
            if row['description']:
                print(f"         desc: {row['description']}")
    conn.close()
    return 0


def cmd_tree(args):
    """树形展示"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM categories WHERE is_active = 1 ORDER BY parent_id, sort_order, id"
    )
    rows = cursor.fetchall()

    by_parent = {}
    for row in rows:
        by_parent.setdefault(row["parent_id"], []).append(row)

    def render(parent_id, indent):
        for row in by_parent.get(parent_id, []):
            print(f"{'  ' * indent}{row['id']:>3} {row['name']}")
            render(row["id"], indent + 1)

    print(f"分类树:")
    render(None, 0)
    conn.close()
    return 0


def cmd_import(args):
    """从 JSON 文件批量导入(按层级顺序:顶级 → 二级 → 三级)

    JSON 格式:[{name, parent, description, sort_order}, ...]
    """
    src = Path(args.file)
    if not src.exists():
        print(f"✗ 文件不存在: {src}")
        return 1

    data = json.loads(src.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print(f"✗ JSON 格式错误:应为数组")
        return 1

    conn = get_conn()
    cursor = conn.cursor()

    # 三种模式:默认(报错) / --force(清空) / --merge(合并)
    cursor.execute("SELECT COUNT(*) FROM categories")
    existing = cursor.fetchone()[0]
    if existing > 0 and not args.force and not args.merge:
        print(f"✗ categories 表已有 {existing} 条记录")
        print(f"  如要清空重新导入,加 --force (危险:id 重排)")
        print(f"  如要合并导入(同名跳过),加 --merge (推荐)")
        conn.close()
        return 1

    if args.force and existing > 0:
        # --force:临时关闭 FK,一次清空
        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("DELETE FROM categories")
        cursor.execute("PRAGMA foreign_keys = ON")
        print(f"  (清空 {existing} 条旧记录)")
    elif args.merge:
        print(f"  (合并模式:已有 {existing} 条,同名节点将跳过)")

    # 按层级顺序导入
    # 第一档:parent is None
    # 第二档:parent 在第一档 name 列表
    # 第三档:parent 在第一/二档 name 列表
    name_to_id = {}

    # merge 模式:预加载 db 已有的所有 name
    existing_names = set()
    if args.merge:
        cursor.execute("SELECT name FROM categories")
        existing_names = {r["name"] for r in cursor.fetchall()}

    # merge 模式:预加载 db 已有的所有 name
    existing_names = set()
    if args.merge:
        cursor.execute("SELECT name FROM categories")
        existing_names = {r["name"] for r in cursor.fetchall()}

    level1_names = {d["name"] for d in data if d.get("parent") is None}
    level2_names = {d["name"] for d in data if d.get("parent") in level1_names}

    def insert(d):
        if d.get("parent") is None:
            parent_id = None
        elif d["parent"] in name_to_id:
            parent_id = name_to_id[d["parent"]]
        elif args.merge and d["parent"] in existing_names:
            # merge 模式:父分类可能在老节点里,跳过这条
            return None
        else:
            print(f"✗ 找不到父分类: {d['parent']}(被 {d['name']} 引用)")
            return None

        # merge 模式:检查同名节点(同 parent 下)
        if args.merge:
            cursor.execute(
                "SELECT id FROM categories WHERE name = ? AND (parent_id IS ? OR parent_id IS NULL) AND (parent_id = ? OR parent_id IS NULL)",
                (d["name"], parent_id, parent_id),
            )
            existing = cursor.fetchone()
            if existing:
                return existing["id"]

        cursor.execute("""
            INSERT INTO categories (parent_id, name, description, sort_order)
            VALUES (?, ?, ?, ?)
        """, (
            parent_id,
            d["name"],
            d.get("description", ""),
            d.get("sort_order", 0),
        ))
        return cursor.lastrowid

    # 第一档
    for d in data:
        if d.get("parent") is None:
            new_id = insert(d)
            if new_id:
                name_to_id[d["name"]] = new_id
                if d["name"] in existing_names and args.merge:
                    print(f"  · [L1] 跳过(同名): {d['name']}")
                else:
                    print(f"  + [L1] {d['name']} (id={new_id})")

    # 第二档
    for d in data:
        if d.get("parent") in level1_names and d["name"] not in name_to_id:
            new_id = insert(d)
            if new_id:
                name_to_id[d["name"]] = new_id
                if d["name"] in existing_names and args.merge:
                    print(f"  · [L2] 跳过(同名): {d['parent']} > {d['name']}")
                else:
                    print(f"  + [L2] {d['parent']} > {d['name']} (id={new_id})")

    # 第三档(及更深)
    for d in data:
        if d["name"] not in name_to_id and d.get("parent") in name_to_id:
            new_id = insert(d)
            if new_id:
                name_to_id[d["name"]] = new_id
                if d["name"] in existing_names and args.merge:
                    print(f"  · [L3] 跳过(同名): {d['parent']} > {d['name']}")
                else:
                    print(f"  + [L3] {d['parent']} > {d['name']} (id={new_id})")

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM categories")
    total = cursor.fetchone()[0]
    print(f"\n✓ 导入完成:共 {total} 条")
    conn.close()
    return 0


def cmd_count(args):
    """统计"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM categories")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM categories WHERE parent_id IS NULL")
    top = cursor.fetchone()[0]
    print(f"总分类数: {total}")
    print(f"顶级分类数: {top}")
    conn.close()
    return 0


def cmd_show(args):
    """查看分类详情"""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories WHERE id = ?", (args.id,))
    row = cursor.fetchone()
    if not row:
        print(f"✗ 未找到 id={args.id}")
        conn.close()
        return 1
    print(f"id:          {row['id']}")
    print(f"name:        {row['name']}")
    print(f"parent_id:   {row['parent_id']}")
    print(f"description: {row['description']}")
    print(f"sort_order:  {row['sort_order']}")
    print(f"is_active:   {row['is_active']}")
    print(f"created_at:  {row['created_at']}")
    print(f"updated_at:  {row['updated_at']}")

    cursor.execute(
        "SELECT id, name FROM categories WHERE parent_id = ? ORDER BY sort_order, id",
        (args.id,),
    )
    children = cursor.fetchall()
    if children:
        print(f"\n子分类:")
        for c in children:
            print(f"  - id={c['id']} name={c['name']}")
    conn.close()
    return 0


# ── 入口 ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="居家管家 - 分类管理 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python category_manager.py init
  python category_manager.py tree
  python category_manager.py import categories_seed.json
  python category_manager.py show --id 5
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    p_init = subparsers.add_parser("init", help="建表(幂等)")

    p_list = subparsers.add_parser("list", help="列出分类")
    p_list.add_argument("--parent", type=int, default=None, help="按 parent_id 筛选")

    p_tree = subparsers.add_parser("tree", help="树形展示")

    p_import = subparsers.add_parser("import", help="从 JSON 文件批量导入")
    p_import.add_argument("file", help="JSON 文件路径")
    p_import.add_argument("--force", action="store_true", help="覆盖已有数据(危险:清空全部分类,id 会重排)")
    p_import.add_argument("--merge", action="store_true", help="合并模式:同名跳过,异名新增(扩域推荐)")

    p_count = subparsers.add_parser("count", help="统计数量")

    p_show = subparsers.add_parser("show", help="查看分类详情")
    p_show.add_argument("--id", type=int, required=True, help="分类 ID")

    args = parser.parse_args()

    if args.command == "init":
        return cmd_init(args)
    elif args.command == "list":
        return cmd_list(args)
    elif args.command == "tree":
        return cmd_tree(args)
    elif args.command == "import":
        return cmd_import(args)
    elif args.command == "count":
        return cmd_count(args)
    elif args.command == "show":
        return cmd_show(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())

