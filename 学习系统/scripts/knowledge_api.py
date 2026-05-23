"""
Learning System - 知识点元数据 API
对照 ls-data-structure.md 中 knowledge-list.json 设计
严格校验字段，不允许多余字段
三层查找DB路径：环境变量 > 技能目录 > 父目录.db文件夹
"""
import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime

# ============================================
# 数据库路径查找（与卡路里技能保持一致）
# ============================================
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "learning-system.db"


def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db文件夹"""
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
        return Path(env_path) / db_filename
    
    # 2. 技能目录（默认）
    p = skill_dir / db_filename
    if p.exists():
        return p
    
    # 3. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / db_filename
            if p.exists():
                return p
            return p
    
    # 4. 都找不到则创建在技能目录下的 .db
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(parents=True, exist_ok=True)
    return default_db_dir / db_filename


DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)

# 允许的字段（严格对照 knowledge-list.json）
ALLOWED_FIELDS = {
    "id", "title", "language", "category", "subcategory", 
    "framework", "tags", "metadata"
}
REQUIRED_FIELDS = {"id", "title", "language", "category"}
VALID_LANGUAGES = {"kotlin", "java", "python", "rust", "javascript", "typescript", "go", "cpp", "c", "swift", "other"}
VALID_CATEGORIES = {"编程语言", "框架", "理论", "工具", "其他"}  # 可扩展


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def validate_fields(data: dict, allowed_fields: set) -> list:
    """校验字段，返回错误列表"""
    errors = []
    
    # 检查必填字段
    for field in REQUIRED_FIELDS:
        if field not in data or data[field] is None:
            errors.append(f"[校验失败] 必填字段 '{field}' 缺失或为 None")
    
    # 检查多余字段
    extra_fields = set(data.keys()) - allowed_fields
    if extra_fields:
        errors.append(f"[校验失败] 不认识的字段: {extra_fields}")
        errors.append(f"允许的字段: {allowed_fields}")
    
    # 检查 language 枚举值
    if "language" in data and data["language"] not in VALID_LANGUAGES:
        errors.append(f"[校验失败] language 必须是 {VALID_LANGUAGES} 之一，当前: {data['language']}")
    
    # 检查 category 枚举值
    if "category" in data and data["category"] not in VALID_CATEGORIES:
        errors.append(f"[校验失败] category 必须是 {VALID_CATEGORIES} 之一，当前: {data['category']}")
    
    # 检查 tags 格式
    if "tags" in data and data["tags"] is not None:
        if isinstance(data["tags"], list):
            pass  # JSON array，合法
        elif isinstance(data["tags"], str):
            try:
                parsed = json.loads(data["tags"])
                if not isinstance(parsed, list):
                    errors.append("[校验失败] tags 必须是 JSON array 或 list")
            except json.JSONDecodeError:
                errors.append("[校验失败] tags 作为 JSON string 格式错误")
    
    # 检查 metadata 格式
    if "metadata" in data and data["metadata"] is not None:
        if isinstance(data["metadata"], dict):
            pass  # JSON object，合法
        elif isinstance(data["metadata"], str):
            try:
                parsed = json.loads(data["metadata"])
                if not isinstance(parsed, dict):
                    errors.append("[校验失败] metadata 必须是 JSON object 或 dict")
            except json.JSONDecodeError:
                errors.append("[校验失败] metadata 作为 JSON string 格式错误")
    
    return errors


def add_knowledge(data: dict) -> dict:
    """
    添加知识点
    输入: {"id": "...", "title": "...", "language": "...", "category": "...", ...}
    输出: {"success": True, "knowledge_id": "..."} 或 {"success": False, "errors": [...]}
    """
    errors = validate_fields(data, ALLOWED_FIELDS)
    if errors:
        return {"success": False, "errors": errors}
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 序列化 JSON 字段
        tags = json.dumps(data["tags"]) if data.get("tags") else "[]"
        metadata = json.dumps(data["metadata"]) if data.get("metadata") else "{}"
        
        cursor.execute("""
            INSERT INTO knowledge_list (id, title, language, category, subcategory, framework, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data["id"],
            data["title"],
            data["language"],
            data["category"],
            data.get("subcategory"),
            data.get("framework"),
            tags,
            metadata
        ))
        
        conn.commit()
        
        # 更新 meta
        cursor.execute("UPDATE meta SET last_updated = CURRENT_TIMESTAMP WHERE file_key = 'knowledge_list'")
        conn.commit()
        
        return {"success": True, "knowledge_id": data["id"]}
        
    except sqlite3.IntegrityError as e:
        return {"success": False, "errors": [f"[数据库错误] 知识点 ID 已存在: {data['id']}"]}
    finally:
        conn.close()


def get_knowledge(knowledge_id: str) -> dict:
    """获取知识点详情"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM knowledge_list WHERE id = ?", (knowledge_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"success": False, "errors": [f"[查询失败] 知识点不存在: {knowledge_id}"]}
    
    result = dict(row)
    # 反序列化 JSON 字段
    if result["tags"]:
        result["tags"] = json.loads(result["tags"])
    if result["metadata"]:
        result["metadata"] = json.loads(result["metadata"])
    
    return {"success": True, "data": result}


def list_knowledge(filters: dict = None) -> dict:
    """
    列出知识点，支持过滤
    filters: {"category": "...", "language": "...", "framework": "...", "tags": [...]}
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM knowledge_list WHERE 1=1"
    params = []
    
    if filters:
        if "category" in filters:
            query += " AND category = ?"
            params.append(filters["category"])
        if "language" in filters:
            query += " AND language = ?"
            params.append(filters["language"])
        if "framework" in filters:
            query += " AND framework = ?"
            params.append(filters["framework"])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        item = dict(row)
        if item["tags"]:
            item["tags"] = json.loads(item["tags"])
        if item["metadata"]:
            item["metadata"] = json.loads(item["metadata"])
        result.append(item)
    
    return {"success": True, "data": result, "count": len(result)}


def update_knowledge(knowledge_id: str, data: dict) -> dict:
    """
    更新知识点（仅允许的字段）
    """
    # 不允许的字段直接报错
    extra_fields = set(data.keys()) - ALLOWED_FIELDS
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] 不允许的字段: {extra_fields}"]}
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # 检查是否存在
    cursor.execute("SELECT id FROM knowledge_list WHERE id = ?", (knowledge_id,))
    if not cursor.fetchone():
        conn.close()
        return {"success": False, "errors": [f"[更新失败] 知识点不存在: {knowledge_id}"]}
    
    # 构建更新语句
    set_clauses = []
    values = []
    
    for field in data:
        if field == "tags":
            set_clauses.append("tags = ?")
            values.append(json.dumps(data[field]) if isinstance(data[field], list) else data[field])
        elif field == "metadata":
            set_clauses.append("metadata = ?")
            values.append(json.dumps(data[field]) if isinstance(data[field], dict) else data[field])
        else:
            set_clauses.append(f"{field} = ?")
            values.append(data[field])
    
    if not set_clauses:
        return {"success": False, "errors": ["[校验失败] 没有提供要更新的字段"]}
    
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    values.append(knowledge_id)
    
    query = f"UPDATE knowledge_list SET {', '.join(set_clauses)} WHERE id = ?"
    cursor.execute(query, values)
    conn.commit()
    
    cursor.execute("UPDATE meta SET last_updated = CURRENT_TIMESTAMP WHERE file_key = 'knowledge_list'")
    conn.commit()
    conn.close()
    
    return {"success": True, "knowledge_id": knowledge_id}


def delete_knowledge(knowledge_id: str) -> dict:
    """删除知识点（级联删除关联数据）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM knowledge_list WHERE id = ?", (knowledge_id,))
    if not cursor.fetchone():
        conn.close()
        return {"success": False, "errors": [f"[删除失败] 知识点不存在: {knowledge_id}"]}
    
    # 级联删除（按依赖顺序）
    cursor.execute("DELETE FROM review_round WHERE schedule_id IN (SELECT id FROM review_schedule WHERE knowledge_id = ?)", (knowledge_id,))
    cursor.execute("DELETE FROM mastery_review WHERE schedule_id IN (SELECT id FROM review_schedule WHERE knowledge_id = ?)", (knowledge_id,))
    cursor.execute("DELETE FROM review_schedule WHERE knowledge_id = ?", (knowledge_id,))
    cursor.execute("DELETE FROM review_history WHERE knowledge_id = ?", (knowledge_id,))
    cursor.execute("DELETE FROM mastery_stage_progress WHERE knowledge_id = ?", (knowledge_id,))
    cursor.execute("DELETE FROM mastery_path WHERE knowledge_id = ?", (knowledge_id,))
    cursor.execute("DELETE FROM stage_progress WHERE knowledge_id = ?", (knowledge_id,))
    cursor.execute("DELETE FROM foundation_path WHERE knowledge_id = ?", (knowledge_id,))
    cursor.execute("DELETE FROM interview_assets WHERE knowledge_id = ?", (knowledge_id,))
    cursor.execute("DELETE FROM knowledge_progress WHERE knowledge_id = ?", (knowledge_id,))
    cursor.execute("DELETE FROM knowledge_list WHERE id = ?", (knowledge_id,))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "knowledge_id": knowledge_id}


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python knowledge_api.py <action> [args]")
        print("  add <json_data>")
        print("  get <knowledge_id>")
        print("  list [category] [language]")
        print("  update <knowledge_id> <json_data>")
        print("  delete <knowledge_id>")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "add":
        data = json.loads(sys.argv[2])
        result = add_knowledge(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif action == "get":
        result = get_knowledge(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif action == "list":
        filters = {}
        if len(sys.argv) > 2:
            filters["category"] = sys.argv[2]
        if len(sys.argv) > 3:
            filters["language"] = sys.argv[3]
        result = list_knowledge(filters)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif action == "update":
        knowledge_id = sys.argv[2]
        data = json.loads(sys.argv[3])
        result = update_knowledge(knowledge_id, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif action == "delete":
        result = delete_knowledge(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    else:
        print(f"[错误] 未知 action: {action}")
        sys.exit(1)