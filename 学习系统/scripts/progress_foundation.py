"""
Learning System - 基础流程模块
包含基础流程 (stage 1-4) 的进度管理
"""
import sqlite3
import json
from db_utils import get_db
from progress_core import validate_stage_sequence, FOUNDATION_ALLOWED_FIELDS, STAGE_ALLOWED_FIELDS, VALID_STATUS


def update_stage_progress(knowledge_id: str, stage_name: str, data: dict) -> dict:
    """
    更新阶段进度（如 stage_1, stage_2, stage_3, stage_4）
    严格校验字段和业务规则
    """
    # 字段校验
    extra_fields = set(data.keys()) - STAGE_ALLOWED_FIELDS
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] stage_progress 不允许的字段: {extra_fields}"]}

    # status 枚举校验
    if "status" in data and data["status"] not in VALID_STATUS:
        return {"success": False, "errors": [f"[校验失败] status 必须是 {VALID_STATUS} 之一"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 检查 stage_progress 是否存在
            cursor.execute("""
                SELECT status FROM stage_progress
                WHERE knowledge_id = ? AND stage_name = ?
            """, (knowledge_id, stage_name))
            row = cursor.fetchone()

            current_status = row["status"] if row else "not_started"
            new_status = data.get("status", current_status)

            # 业务规则校验
            stage_num = int(stage_name.split("_")[1])
            errors = validate_stage_sequence(stage_num, new_status, current_status)
            if errors:
                return {"success": False, "errors": errors}

            # Bug 2 修复：完成 stage 时，检查所有前置 stage 是否已完成
            if new_status == "completed":
                # 查询所有前置 stage（1 到 stage_num-1）
                prerequisite_errors = []
                for prev_stage in range(1, stage_num):
                    prev_name = f"stage_{prev_stage}"
                    cursor.execute("""
                        SELECT status FROM stage_progress
                        WHERE knowledge_id = ? AND stage_name = ?
                    """, (knowledge_id, prev_name))
                    prev_row = cursor.fetchone()
                    if not prev_row or prev_row["status"] != "completed":
                        prerequisite_errors.append(f"stage_{prev_stage}")

                if prerequisite_errors:
                    incomplete = " → ".join(prerequisite_errors) if len(prerequisite_errors) <= 3 else " → ".join(prerequisite_errors[:3]) + " → ..."
                    return {
                        "success": False,
                        "errors": [
                            f"[业务规则] {stage_name} 不能在前置阶段未完成时完成。必须按顺序完成：stage_1 → stage_2 → ... → {stage_name}。"
                            f"当前未完成的前置阶段：{incomplete}"
                        ]
                    }

            # 构建更新
            if row:
                set_clauses = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
                values = [new_status]

                if "completed_at" in data:
                    set_clauses.append("completed_at = ?")
                    values.append(data["completed_at"])

                if "essence_keywords" in data:
                    set_clauses.append("essence_keywords = ?")
                    values.append(json.dumps(data["essence_keywords"]) if isinstance(data["essence_keywords"], list) else data["essence_keywords"])

                values.extend([knowledge_id, stage_name])
                cursor.execute(f"""
                    UPDATE stage_progress
                    SET {', '.join(set_clauses)}
                    WHERE knowledge_id = ? AND stage_name = ?
                """, values)
            else:
                # 插入新记录
                cursor.execute("""
                    INSERT INTO stage_progress (knowledge_id, stage_name, status, completed_at, essence_keywords)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    knowledge_id,
                    stage_name,
                    new_status,
                    data.get("completed_at"),
                    json.dumps(data["essence_keywords"]) if data.get("essence_keywords") else "[]"
                ))

            # 如果 stage 完成，同步更新 foundation_path.current_stage（同一事务）
            if new_status == "completed":
                cursor.execute("""
                    UPDATE foundation_path
                    SET current_stage = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE knowledge_id = ?
                """, (stage_num, knowledge_id))

        return {"success": True, "knowledge_id": knowledge_id, "stage": stage_name}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] update_stage_progress: {str(e)}"]}


def update_foundation_path(knowledge_id: str, data: dict) -> dict:
    """更新基础流程进度"""
    extra_fields = set(data.keys()) - FOUNDATION_ALLOWED_FIELDS
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] foundation_path 不允许的字段: {extra_fields}"]}

    if "status" in data and data["status"] not in VALID_STATUS:
        return {"success": False, "errors": [f"[校验失败] status 必须是 {VALID_STATUS} 之一"]}

    if "current_stage" in data:
        stage = data["current_stage"]
        if not isinstance(stage, int) or not (1 <= stage <= 4):
            return {"success": False, "errors": [f"[校验失败] current_stage 必须是 1-4 整数，当前: {stage}"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 检查是否存在
            cursor.execute("SELECT knowledge_id FROM foundation_path WHERE knowledge_id = ?", (knowledge_id,))
            if not cursor.fetchone():
                return {"success": False, "errors": [f"[更新失败] foundation_path 不存在: {knowledge_id}"]}

            set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
            values = []

            for field in data:
                if field == "status":
                    set_clauses.append("status = ?")
                    values.append(data[field])
                elif field == "current_stage":
                    set_clauses.append("current_stage = ?")
                    values.append(data[field])
                elif field == "completed_at":
                    set_clauses.append("completed_at = ?")
                    values.append(data[field])
                elif field == "total_learning_minutes":
                    set_clauses.append("total_learning_minutes = ?")
                    values.append(data[field])

            values.append(knowledge_id)
            cursor.execute(f"UPDATE foundation_path SET {', '.join(set_clauses)} WHERE knowledge_id = ?", values)

        return {"success": True, "knowledge_id": knowledge_id}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] update_foundation_path: {str(e)}"]}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python progress_foundation.py <action> [args]")
        print("  update_stage <knowledge_id> <stage_name> <json>")
        print("  update_foundation <knowledge_id> <json>")
        sys.exit(1)

    action = sys.argv[1]

    if action == "update_stage":
        knowledge_id = sys.argv[2]
        stage_name = sys.argv[3]
        data = json.loads(sys.argv[4])
        result = update_stage_progress(knowledge_id, stage_name, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "update_foundation":
        knowledge_id = sys.argv[2]
        data = json.loads(sys.argv[3])
        result = update_foundation_path(knowledge_id, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"[错误] 未知 action: {action}")
        sys.exit(1)
