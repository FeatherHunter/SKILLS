#!/usr/bin/env python3
"""
私家大厨 - 全量食谱导出脚本

用途:把当前 DB 里所有菜的全量数据(17 张表)导出为单个 JSON 文件。
供"重构前后 round-trip 测试"使用:重构后用 recipe_import.py import 这个 JSON,
验证 schema 变化后老数据能完整还原。

设计原则(来自《优秀 Skill 指导手册》):
- 单文件输出,JSON 格式
- 每个菜一个对象,内含 17 张表的全量字段
- 含 NULL 字段保留为 null(JSON 标准)
- 含 id 字段,供 import 时复用(recipe_import.py 的 merge 模式)

用法:
    python export_recipes.py <output_json_path>

示例:
    python export_recipes.py D:\\2Study\\StudyNotes\\.db\\recipes_export_20260722.json

CLI 输出:
    {status, data: {exported_count, file_path}, message}
"""

import sys
import os
import json
import sqlite3
from pathlib import Path

# 5 层架构:从 db_config 拿连接
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_config import get_db_path


# 17 张表清单(按"先主表后从表"顺序,导出时方便排查)
TABLES = [
    "recipes",                       # 1. 主表
    "recipe_categories",             # 2. 分类 1:1
    "recipe_seasons",                # 3. 季节 1:N
    "recipe_cooking_methods",        # 4. 烹饪方式 1:N
    "recipe_flavors",                # 5. 口味 1:N
    "recipe_diet_tags",              # 6. 饮食标签 1:N
    "recipe_meal_types",             # 7. 用餐类型 1:N
    "ingredients",                   # 8. 食材 1:N
    "cooking_steps",                 # 9. 步骤 1:N
    "step_ingredients",              # 10. 步骤×食材 N:M 桥
    "step_techniques",               # 11. 步骤技法 1:N
    "tips",                          # 12. 贴士 1:N
    "recipe_history",                # 13. 烹饪历史 1:N
    "background_knowledge",          # 14. 背景知识 1:1
    "recipe_relations",              # 15. 派生关系 1:N
    "cookware",                      # 16. 炊具 1:N
    "nutrition_info",                # 17. 营养 1:1
]


def _fetch_table(conn, table, recipe_id=None):
    """读单张表全部行;按表的 FK 结构选查询字段。
    - 大多数表:WHERE recipe_id = ?
    - recipes 主表:WHERE id = ?
    - step_ingredients 桥表:step_id IN (该菜所有 step)
    - recipe_relations 自引用:parent_id 或 child_id 等于该菜
    """
    cur = conn.cursor()

    if table == "recipes":
        if recipe_id:
            cur.execute(f"SELECT * FROM recipes WHERE id = ?", (recipe_id,))
        else:
            cur.execute("SELECT * FROM recipes")
    elif table == "step_ingredients":
        if recipe_id:
            # 通过 cooking_steps 关联到 recipe_id,拿到 step_ids 再 join
            cur.execute("SELECT id FROM cooking_steps WHERE recipe_id = ?", (recipe_id,))
            step_ids = [r[0] for r in cur.fetchall()]
            if step_ids:
                placeholders = ",".join("?" * len(step_ids))
                cur.execute(
                    f"SELECT * FROM step_ingredients WHERE step_id IN ({placeholders})",
                    step_ids,
                )
            else:
                return []
        else:
            cur.execute("SELECT * FROM step_ingredients")
    elif table == "recipe_relations":
        if recipe_id:
            cur.execute(
                "SELECT * FROM recipe_relations WHERE parent_id = ? OR child_id = ?",
                (recipe_id, recipe_id),
            )
        else:
            cur.execute("SELECT * FROM recipe_relations")
    else:
        # 默认:绝大多数表用 recipe_id
        if recipe_id:
            cur.execute(f"SELECT * FROM {table} WHERE recipe_id = ?", (recipe_id,))
        else:
            cur.execute(f"SELECT * FROM {table}")

    rows = cur.fetchall()
    return [dict(r) for r in rows]


def export_recipes(output_path, include_archived=False):
    """
    导出所有食谱(默认排除"已废弃"软删除)。
    返回:
        {
            "exported_at": "YYYY-MM-DD HH:MM:SS",
            "db_path": "...",
            "recipe_count": N,
            "tables": {表名: 行数},
            "recipes": [{完整字段...}, ...],
        }
    """
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # 1. 取所有非废弃菜(排除软删除)
    cur = conn.cursor()
    if include_archived:
        cur.execute("SELECT * FROM recipes ORDER BY created_at")
    else:
        cur.execute("SELECT * FROM recipes WHERE status != '已废弃' ORDER BY created_at")
    recipes_raw = [dict(r) for r in cur.fetchall()]

    # 2. 每道菜的 17 张表数据
    recipes_full = []
    tables_count = {}

    for recipe in recipes_raw:
        rid = recipe["id"]
        record = {"_recipe": recipe}

        for table in TABLES:
            if table == "recipes":
                continue  # 主表已存 _recipe
            rows = _fetch_table(conn, table, rid)
            tables_count[table] = tables_count.get(table, 0) + len(rows)
            record[table] = rows

        recipes_full.append(record)

    # 3. 统计每张表行数
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    for (tname,) in cur.fetchall():
        if tname in tables_count:
            continue  # 已统计
        cur.execute(f"SELECT COUNT(*) FROM {tname}")
        tables_count[tname] = cur.fetchone()[0]

    conn.close()

    # 4. 写 JSON
    output = {
        "exported_at": _now(),
        "db_path": str(db_path),
        "include_archived": include_archived,
        "recipe_count": len(recipes_full),
        "tables": tables_count,
        "recipes": recipes_full,
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return output


def _now():
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "status": "error",
            "data": {},
            "message": "用法:python export_recipes.py <output_json_path> [--include-archived]"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    output_path = sys.argv[1]
    include_archived = "--include-archived" in sys.argv

    try:
        result = export_recipes(output_path, include_archived=include_archived)
        print(json.dumps({
            "status": "success",
            "data": {
                "exported_count": result["recipe_count"],
                "file_path": output_path,
                "tables": result["tables"],
                "include_archived": include_archived,
            },
            "message": f"已导出 {result['recipe_count']} 道菜到 {output_path}"
        }, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({
            "status": "error",
            "data": {"error": str(e)},
            "message": f"导出失败: {e}"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()