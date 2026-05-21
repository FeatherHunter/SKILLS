#!/usr/bin/env python3
"""
生成卡路里技能 TypeScript 配置文件
- 表结构从数据库动态读取（方案三）
- queries/actions/views 由 AI 根据表能力自动设计
- 用法: python generate_ts_config.py
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

# ============ 配置 ============
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
OUTPUT_FILE = SKILL_DIR / "config-calorie.ts"

def find_db(skill_dir):
    """找数据库路径"""
    # 1. 环境变量
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / DB_FILENAME
        if p.exists():
            return p
    # 2. 技能目录
    p = skill_dir / DB_FILENAME
    if p.exists():
        return p
    # 3. 父目录 .db 文件夹
    for parent in skill_dir.parents:
        p = parent / ".db" / DB_FILENAME
        if p.exists():
            return p
    raise FileNotFoundError(f"找不到数据库: {DB_FILENAME}")

def get_tables(cursor):
    """获取所有表名"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [row[0] for row in cursor.fetchall()]

def get_columns(cursor, table):
    """获取表的所有字段"""
    cursor.execute(f"PRAGMA table_info({table})")
    return cursor.fetchall()

def to_ts_type(sqlite_type):
    """SQLite 类型 → TypeScript 类型"""
    type_map = {"INTEGER": "INTEGER", "REAL": "REAL", "TEXT": "TEXT"}
    return type_map.get(sqlite_type.upper(), "TEXT")

def generate_table_fields(columns):
    """生成单个表的 fields 数组"""
    fields = []
    for col in columns:
        _, name, col_type, _, default, _ = col[:6]
        field = {
            "name": name,
            "type": to_ts_type(col_type),
            "label": name.replace("_", " ").capitalize(),
        }
        if name == "id":
            field["primaryKey"] = True
        if default is not None:
            field["default"] = default
        if "date" in name.lower() and "time" not in name.lower():
            field["format"] = "date"
        elif "time" in name.lower() or ("created" in name or "updated" in name):
            field["format"] = "datetime"
            field["visible"] = False
        if "calories" in name or "cal" in name:
            field["unit"] = "千卡"
        elif "protein" in name:
            field["unit"] = "克"
        elif "carbs" in name or "fat" in name:
            field["unit"] = "克"
        elif "weight" in name:
            field["unit"] = "公斤"
        elif "height" in name:
            field["unit"] = "厘米"
        elif "grams" in name:
            field["unit"] = "克"
        elif "duration" in name:
            field["unit"] = "分钟"
        elif "reps" in name:
            field["unit"] = "个"
        field["editable"] = name not in ["id", "created_at", "updated_at"]
        fields.append(field)
    return fields

def generate_queries_for_table(table):
    """根据表名生成默认查询"""
    table_labels = {
        "entries": "饮食记录",
        "weight_log": "体重记录",
        "exercise_log": "运动记录",
        "sleep_records": "睡眠记录",
        "nutrition_products": "食品库",
        "fitness_goals": "健身目标",
        "daily_goal": "每日目标",
    }
    label = table_labels.get(table, table)
    return [
        {
            "id": f"{table}-daily",
            "label": f"今日{label}",
            "sql": f"SELECT * FROM {table} WHERE date = '{{date}}' ORDER BY time",
            "params": [{"name": "date", "type": "date", "label": "日期", "default": "TODAY"}]
        },
        {
            "id": f"{table}-history",
            "label": f"{label}历史",
            "sql": f"SELECT * FROM {table} ORDER BY date DESC, time DESC LIMIT 100",
            "params": []
        }
    ]

def generate_action(table, fields):
    """根据表结构生成默认 Action"""
    action_fields = []
    for f in fields:
        if f["name"] in ["id", "created_at", "updated_at"]:
            continue
        action_fields.append({
            "field": f["name"],
            "required": f["name"] in ["date"],
            "source": "user-input",
            "prompt": f["label"]
        })
    return {
        "id": f"add-{table}",
        "label": f"添加{table}",
        "type": "insert",
        "targetTable": table,
        "fields": action_fields
    }

def generate_view(table, query_ids):
    """根据表生成默认 View"""
    return {
        "id": table,
        "label": table.replace("_", " ").capitalize(),
        "components": {
            "table": {"queryId": query_ids[0], "sortable": True, "pageSize": 20},
            "form": {"actionId": f"add-{table}"}
        }
    }

def py_to_ts(obj, indent=0):
    """Python 对象 → TS 代码"""
    spaces = "  " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        items = [f'"{k}": {py_to_ts(v, indent+1)}' for k, v in obj.items()]
        return "{\n" + ",\n".join(f"{spaces}  {item}" for item in items) + "\n" + spaces + "}"
    elif isinstance(obj, list):
        if not obj:
            return "[]"
        items = [py_to_ts(item, indent+1) for item in obj]
        return "[\n" + ",\n".join(f"{spaces}  {item}" for item in items) + "\n" + spaces + "]"
    elif isinstance(obj, str):
        return f'"{obj}"'
    elif isinstance(obj, bool):
        return "true" if obj else "false"
    elif isinstance(obj, (int, float)):
        return str(obj)
    else:
        return str(obj)

def main():
    print(f"[generate_ts_config] 读取数据库...")
    db_path = find_db(SKILL_DIR)
    print(f"  数据库: {db_path}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    tables = get_tables(cursor)
    print(f"  发现 {len(tables)} 个表: {tables}")

    all_schema_tables = []
    all_queries = []
    all_actions = []
    all_views = []

    for table in tables:
        columns = get_columns(cursor, table)
        fields = generate_table_fields(columns)

        all_schema_tables.append({"name": table, "fields": fields})
        all_queries.extend(generate_queries_for_table(table))
        all_actions.append(generate_action(table, fields))
        all_views.append(generate_view(table, [f"{table}-daily"]))

    conn.close()

    config = {
        "meta": {
            "name": "calorie",
            "label": "卡路里",
            "icon": "ForkKnife",
            "description": "热量与营养追踪，记录饮食、体重、运动、睡眠，支持每日目标和目标进度分析",
            "dbFiles": ["calorie_data.db"]
        },
        "schema": {"tables": all_schema_tables},
        "queries": all_queries,
        "actions": all_actions,
        "views": all_views
    }

    ts_content = (
        "// 自动生成 by generate_ts_config.py\n"
        f"// 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        "// 表结构从数据库动态读取（方案三）\n"
        "// queries/actions/views 由 AI 根据表能力设计\n\n"
        + py_to_ts(config)
    )

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(ts_content)

    print(f"  写入: {OUTPUT_FILE}")
    print(f"[generate_ts_config] 完成！")

if __name__ == "__main__":
    main()