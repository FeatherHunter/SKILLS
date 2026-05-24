"""
Learning System - 会话与进度更新模块
包含 active_session 管理、knowledge_progress 更新、面试素材管理
"""
import sqlite3
import json
from datetime import datetime
from db_utils import get_db

# 允许的字段（严格对照 progress.json）
PROGRESS_ALLOWED_FIELDS = {"target_level", "last_activity", "total_learning_minutes"}

VALID_PATH_TYPE = {"foundation", "mastery", "unknown"}


def update_interview_assets(knowledge_id: str, field: str, value: str) -> dict:
    """
    更新面试素材路径（star_case_path / failure_case_path / adr_path）
    """
    allowed_fields = {"star_case_path", "failure_case_path", "adr_path"}
    if field not in allowed_fields:
        return {"success": False, "errors": [f"[校验失败] interview_assets 不允许的字段: {field}，必须是 {allowed_fields}"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 检查记录是否存在
            cursor.execute("SELECT knowledge_id FROM interview_assets WHERE knowledge_id = ?", (knowledge_id,))
            if not cursor.fetchone():
                return {"success": False, "errors": [f"[更新失败] interview_assets 不存在: {knowledge_id}"]}

            cursor.execute(f"""
                UPDATE interview_assets
                SET {field} = ?, updated_at = CURRENT_TIMESTAMP
                WHERE knowledge_id = ?
            """, (value, knowledge_id))

        return {"success": True, "knowledge_id": knowledge_id, "field": field}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] update_interview_assets: {str(e)}"]}


def update_knowledge_progress(knowledge_id: str, data: dict) -> dict:
    """更新知识点进度"""
    extra_fields = set(data.keys()) - PROGRESS_ALLOWED_FIELDS
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] knowledge_progress 不允许的字段: {extra_fields}"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT knowledge_id FROM knowledge_progress WHERE knowledge_id = ?", (knowledge_id,))
            if not cursor.fetchone():
                return {"success": False, "errors": [f"[更新失败] knowledge_progress 不存在: {knowledge_id}"]}

            set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
            values = []

            for field in data:
                if field == "target_level":
                    set_clauses.append("target_level = ?")
                    values.append(data[field])
                elif field == "last_activity":
                    set_clauses.append("last_activity = ?")
                    values.append(data[field])
                elif field == "total_learning_minutes":
                    set_clauses.append("total_learning_minutes = ?")
                    values.append(data[field])

            values.append(knowledge_id)
            cursor.execute(f"UPDATE knowledge_progress SET {', '.join(set_clauses)} WHERE knowledge_id = ?", values)

        return {"success": True, "knowledge_id": knowledge_id}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] update_knowledge_progress: {str(e)}"]}


def update_active_session(data: dict) -> dict:
    """更新当前学习会话"""
    ALLOWED_SESSION_FIELDS = {"knowledge_id", "path_type", "stage", "step", "started_at", "total_minutes"}

    extra_fields = set(data.keys()) - ALLOWED_SESSION_FIELDS
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] active_session 不允许的字段: {extra_fields}"]}

    if "path_type" in data and data["path_type"] not in VALID_PATH_TYPE:
        return {"success": False, "errors": [f"[校验失败] path_type 必须是 {VALID_PATH_TYPE} 之一"]}

    if "stage" in data:
        stage = data["stage"]
        if not isinstance(stage, int) or not (1 <= stage <= 7):
            return {"success": False, "errors": [f"[校验失败] stage 必须是 1-7 整数"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
            values = []

            for field in data:
                if field == "knowledge_id":
                    set_clauses.append("knowledge_id = ?")
                    values.append(data[field])
                elif field == "path_type":
                    set_clauses.append("path_type = ?")
                    values.append(data[field])
                elif field == "stage":
                    set_clauses.append("stage = ?")
                    values.append(data[field])
                elif field == "step":
                    set_clauses.append("step = ?")
                    values.append(data[field])
                elif field == "started_at":
                    set_clauses.append("started_at = ?")
                    values.append(data[field])
                elif field == "total_minutes":
                    set_clauses.append("total_minutes = ?")
                    values.append(data[field])

            cursor.execute(f"UPDATE active_session SET {', '.join(set_clauses)} WHERE id = 1", values)

        return {"success": True}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] update_active_session: {str(e)}"]}


def get_active_session() -> dict:
    """获取当前学习会话"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM active_session WHERE id = 1")
            row = cursor.fetchone()

        if not row:
            return {"success": False, "errors": ["[查询失败] active_session 不存在"]}

        return {"success": True, "data": dict(row)}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_active_session: {str(e)}"]}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python progress_session.py <action> [args]")
        print("  update_interview_assets <knowledge_id> <field> <value>")
        print("  update_progress <knowledge_id> <json>")
        print("  update_session <json>")
        print("  get_session")
        sys.exit(1)

    action = sys.argv[1]

    if action == "update_interview_assets":
        if len(sys.argv) < 5:
            print("用法: python progress_session.py update_interview_assets <knowledge_id> <field> <value>")
            sys.exit(1)
        result = update_interview_assets(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "update_progress":
        if len(sys.argv) < 4:
            print("用法: python progress_session.py update_progress <knowledge_id> <json>")
            sys.exit(1)
        knowledge_id = sys.argv[2]
        data = json.loads(sys.argv[3])
        result = update_knowledge_progress(knowledge_id, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "update_session":
        if len(sys.argv) < 3:
            print("用法: python progress_session.py update_session <json>")
            sys.exit(1)
        data = json.loads(sys.argv[2])
        result = update_active_session(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_session":
        result = get_active_session()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"未知操作: {action}")
        sys.exit(1)
