"""
Learning System - 精通流程模块
包含精通路径 (stage 5-7) 的进度管理
"""
import sqlite3
import json
from datetime import datetime
from db_utils import get_db

MASTERY_ALLOWED_FIELDS = {"status", "current_stage", "started_at", "completed_at", "total_learning_minutes", "mastery_level"}
VALID_STATUS = {"not_started", "in_progress", "completed"}


def _ensure_mastery_level_column():
    """确保 mastery_path 表有 mastery_level 字段（ idempotent ）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(mastery_path)")
            columns = [row[1] for row in cursor.fetchall()]
            if "mastery_level" not in columns:
                cursor.execute("ALTER TABLE mastery_path ADD COLUMN mastery_level INTEGER DEFAULT 1 CHECK(mastery_level BETWEEN 1 AND 3)")
                print(f"[OK] mastery_path 表已新增 mastery_level 字段，默认值 1")
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] _ensure_mastery_level_column: {str(e)}"]}


def update_mastery_path(knowledge_id: str, data: dict) -> dict:
    """更新精通流程进度"""
    extra_fields = set(data.keys()) - MASTERY_ALLOWED_FIELDS
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] mastery_path 不允许的字段: {extra_fields}"]}

    if "status" in data and data["status"] not in VALID_STATUS:
        return {"success": False, "errors": [f"[校验失败] status 必须是 {VALID_STATUS} 之一"]}

    if "current_stage" in data:
        stage = data["current_stage"]
        if not isinstance(stage, int) or not (5 <= stage <= 7):
            return {"success": False, "errors": [f"[校验失败] current_stage 必须是 5-7 整数，当前: {stage}"]}

    if "mastery_level" in data:
        level = data["mastery_level"]
        if not isinstance(level, int) or not (1 <= level <= 3):
            return {"success": False, "errors": [f"[校验失败] mastery_level 必须是 1-3 整数，当前: {level}"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT knowledge_id FROM mastery_path WHERE knowledge_id = ?", (knowledge_id,))
            if not cursor.fetchone():
                return {"success": False, "errors": [f"[更新失败] mastery_path 不存在: {knowledge_id}"]}

            set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
            values = []

            for field in data:
                if field == "status":
                    set_clauses.append("status = ?")
                    values.append(data[field])
                elif field == "current_stage":
                    set_clauses.append("current_stage = ?")
                    values.append(data[field])
                elif field == "started_at":
                    set_clauses.append("started_at = ?")
                    values.append(data[field])
                elif field == "completed_at":
                    set_clauses.append("completed_at = ?")
                    values.append(data[field])
                elif field == "total_learning_minutes":
                    set_clauses.append("total_learning_minutes = ?")
                    values.append(data[field])
                elif field == "mastery_level":
                    set_clauses.append("mastery_level = ?")
                    values.append(data[field])

            values.append(knowledge_id)
            cursor.execute(f"UPDATE mastery_path SET {', '.join(set_clauses)} WHERE knowledge_id = ?", values)

            # 如果 mastery 完成，启用精通复习
            if data.get("status") == "completed":
                cursor.execute("""
                    UPDATE mastery_review
                    SET enabled = 1, next_review = datetime('now', '+30 days'), updated_at = CURRENT_TIMESTAMP
                    WHERE schedule_id = (SELECT id FROM review_schedule WHERE knowledge_id = ?)
                """, (knowledge_id,))

        return {"success": True, "knowledge_id": knowledge_id}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] update_mastery_path: {str(e)}"]}


def update_mastery_stage_progress(knowledge_id: str, stage_name: str, data: dict) -> dict:
    """
    更新精通阶段进度（stage_5, stage_6, stage_7）
    严格校验字段和业务规则
    """
    # 字段校验
    allowed = {"status", "step", "cases_documented", "completed_at"}
    extra_fields = set(data.keys()) - allowed
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] mastery_stage_progress 不允许的字段: {extra_fields}"]}

    # status 枚举校验
    if "status" in data and data["status"] not in VALID_STATUS:
        return {"success": False, "errors": [f"[校验失败] status 必须是 {VALID_STATUS} 之一"]}

    # step 校验
    if "step" in data:
        if not isinstance(data["step"], int) or data["step"] < 1:
            return {"success": False, "errors": [f"[校验失败] step 必须是正整数"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 检查记录是否存在
            cursor.execute("""
                SELECT status FROM mastery_stage_progress
                WHERE knowledge_id = ? AND stage_name = ?
            """, (knowledge_id, stage_name))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "errors": [f"[更新失败] mastery_stage_progress 不存在: {knowledge_id}/{stage_name}"]}

            current_status = row["status"]
            new_status = data.get("status", current_status)

            # 业务规则：不能从 not_started 直接跳到 completed
            if new_status == "completed" and current_status == "not_started":
                return {"success": False, "errors": [f"[业务规则] {stage_name} 不能直接从 not_started → completed，必须先 in_progress"]}

            # 构建更新
            set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
            values = []

            for field in data:
                if field == "status":
                    set_clauses.append("status = ?")
                    values.append(new_status)
                elif field == "step":
                    set_clauses.append("step = ?")
                    values.append(data[field])
                elif field == "cases_documented":
                    set_clauses.append("cases_documented = ?")
                    values.append(data[field])

            values.extend([knowledge_id, stage_name])
            cursor.execute(f"""
                UPDATE mastery_stage_progress
                SET {', '.join(set_clauses)}
                WHERE knowledge_id = ? AND stage_name = ?
            """, values)

        return {"success": True, "knowledge_id": knowledge_id, "stage_name": stage_name}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] update_mastery_stage_progress: {str(e)}"]}


def get_mastery_stage_progress(knowledge_id: str) -> dict:
    """
    获取精通阶段进度（stage_5, stage_6, stage_7）
    返回该 knowledge 的所有 mastery_stage 列表
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT stage_name, status, step, cases_documented, created_at, updated_at
                FROM mastery_stage_progress
                WHERE knowledge_id = ? AND stage_name IN ('stage_5', 'stage_6', 'stage_7')
                ORDER BY stage_name
            """, (knowledge_id,))
            rows = cursor.fetchall()

        if not rows:
            return {"success": False, "errors": [f"[查询失败] 没有 mastery_stage_progress 记录: {knowledge_id}"]}

        result = [dict(row) for row in rows]
        return {"success": True, "data": result, "count": len(result)}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_mastery_stage_progress: {str(e)}"]}


def update_mastery_stage(knowledge_id: str, stage_name: str, data: dict) -> dict:
    """
    更新精通阶段进度（stage_5, stage_6, stage_7）
    支持插入新记录或更新已有记录
    """
    # stage_name 校验
    valid_stages = {"stage_5", "stage_6", "stage_7"}
    if stage_name not in valid_stages:
        return {"success": False, "errors": [f"[校验失败] stage_name 必须是 {valid_stages} 之一，当前: {stage_name}"]}

    # 字段校验
    allowed = {"status", "step", "cases_documented"}
    extra_fields = set(data.keys()) - allowed
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] mastery_stage_progress 不允许的字段: {extra_fields}"]}

    # status 枚举校验
    if "status" in data and data["status"] not in VALID_STATUS:
        return {"success": False, "errors": [f"[校验失败] status 必须是 {VALID_STATUS} 之一"]}

    # step 校验
    if "step" in data:
        if not isinstance(data["step"], int) or data["step"] < 1:
            return {"success": False, "errors": [f"[校验失败] step 必须是正整数"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 检查记录是否存在
            cursor.execute("""
                SELECT status FROM mastery_stage_progress
                WHERE knowledge_id = ? AND stage_name = ?
            """, (knowledge_id, stage_name))
            row = cursor.fetchone()

            if not row:
                # 插入新记录（mastery_stage_progress 表没有 completed_at 字段）
                cursor.execute("""
                    INSERT INTO mastery_stage_progress (knowledge_id, stage_name, status, step, cases_documented)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    knowledge_id,
                    stage_name,
                    data.get("status", "not_started"),
                    data.get("step", 1),
                    data.get("cases_documented", 0)
                ))
                return {"success": True, "knowledge_id": knowledge_id, "stage_name": stage_name, "action": "inserted"}

            current_status = row["status"]
            new_status = data.get("status", current_status)

            # 业务规则：不能从 not_started 直接跳到 completed
            if new_status == "completed" and current_status == "not_started":
                return {"success": False, "errors": [f"[业务规则] {stage_name} 不能直接从 not_started → completed，必须先 in_progress"]}

            # 构建更新
            set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
            values = []

            for field in data:
                if field == "status":
                    set_clauses.append("status = ?")
                    values.append(new_status)
                elif field == "step":
                    set_clauses.append("step = ?")
                    values.append(data[field])
                elif field == "cases_documented":
                    set_clauses.append("cases_documented = ?")
                    values.append(data[field])

            values.extend([knowledge_id, stage_name])
            cursor.execute(f"""
                UPDATE mastery_stage_progress
                SET {', '.join(set_clauses)}
                WHERE knowledge_id = ? AND stage_name = ?
            """, values)

        return {"success": True, "knowledge_id": knowledge_id, "stage_name": stage_name, "action": "updated"}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] update_mastery_stage: {str(e)}"]}


if __name__ == "__main__":
    import sys

    usage = """用法:
  python progress_mastery.py update_mastery <knowledge_id> <json>
  python progress_mastery.py update_mastery_stage <knowledge_id> <stage_name> <json>
  python progress_mastery.py get_mastery_stage <knowledge_id>
  python progress_mastery.py update_mastery_level <knowledge_id> <level>
"""

    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)

    command = sys.argv[1]

    if command == "update_mastery":
        if len(sys.argv) < 4:
            print("用法: python progress_mastery.py update_mastery <knowledge_id> <json>")
            sys.exit(1)
        kid = sys.argv[2]
        data = json.loads(sys.argv[3])
        result = update_mastery_path(kid, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "update_mastery_stage":
        if len(sys.argv) < 5:
            print("用法: python progress_mastery.py update_mastery_stage <knowledge_id> <stage_name> <json>")
            sys.exit(1)
        kid = sys.argv[2]
        stage = sys.argv[3]
        data = json.loads(sys.argv[4])
        result = update_mastery_stage(kid, stage, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "get_mastery_stage":
        if len(sys.argv) < 3:
            print("用法: python progress_mastery.py get_mastery_stage <knowledge_id>")
            sys.exit(1)
        kid = sys.argv[2]
        result = get_mastery_stage_progress(kid)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif command == "update_mastery_level":
        if len(sys.argv) < 4:
            print("用法: python progress_mastery.py update_mastery_level <knowledge_id> <level>")
            sys.exit(1)
        kid = sys.argv[2]
        level = int(sys.argv[3])
        _ensure_mastery_level_column()
        result = update_mastery_path(kid, {"mastery_level": level})
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"未知命令: {command}")
        print(usage)
        sys.exit(1)
