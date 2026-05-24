"""
Learning System - 学习进度 API
对照 ls-data-structure.md 中 progress.json 设计
严格校验字段和业务规则，不允许多余字段
"""
import sqlite3
import json
from datetime import datetime, timedelta
from db_utils import get_db

# 允许的字段（严格对照 progress.json）
PROGRESS_ALLOWED_FIELDS = {"target_level", "last_activity", "total_learning_minutes"}
FOUNDATION_ALLOWED_FIELDS = {"status", "current_stage", "completed_at", "total_learning_minutes"}
MASTERY_ALLOWED_FIELDS = {"status", "current_stage", "started_at", "completed_at", "total_learning_minutes", "mastery_level"}
STAGE_ALLOWED_FIELDS = {"status", "completed_at", "essence_keywords"}

VALID_STATUS = {"not_started", "in_progress", "completed"}
VALID_PATH_TYPE = {"foundation", "mastery", "unknown"}


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


def calculate_level(knowledge_id: str) -> int:
    """
    根据 stage_progress 表的真实状态计算当前 level
    Level 计算规则：
    - 只要 stage_N.status == "completed" 就认为该阶段完成
    - Level = 已完成的最大 stage 号（如 stage_1/2/3 completed → Level 3）
    - stage_1~4 全部 completed 时，检查 mastery_path 状态
      - mastery_path.status == "completed" → Level 7
      - mastery_path.status == "in_progress" → Level = 4 + (mastery_path.current_stage - 5)
      - 否则 → Level 4
    - 没有任何 stage completed → Level 0
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 查询所有 stage_progress（stage_1 ~ stage_4）
            cursor.execute("""
                SELECT stage_name, status FROM stage_progress
                WHERE knowledge_id = ? AND stage_name IN ('stage_1','stage_2','stage_3','stage_4')
                ORDER BY stage_name
            """, (knowledge_id,))
            stage_rows = cursor.fetchall()

            # 查询 mastery_path
            cursor.execute("SELECT status, current_stage FROM mastery_path WHERE knowledge_id = ?", (knowledge_id,))
            mp_row = cursor.fetchone()

        if not stage_rows:
            return 0  # 不存在

        # 找出已完成的最大 stage 号
        max_completed = 0
        for row in stage_rows:
            if row["status"] == "completed":
                stage_num = int(row["stage_name"].split("_")[1])
                if stage_num > max_completed:
                    max_completed = stage_num

        # 如果没有任何 stage 完成
        if max_completed == 0:
            return 0

        # 如果最大完成 stage < 4，Level = 该 stage 号
        if max_completed < 4:
            return max_completed

        # stage_1~4 全部 completed，检查 mastery_path
        mp_status = mp_row["status"] if mp_row else "not_started"

        if mp_status == "completed":
            return 7
        elif mp_status == "in_progress" and mp_row:
            stage = mp_row["current_stage"] or 5
            return 4 + (stage - 5)
        else:
            return 4
    except Exception as e:
        return 0


def validate_stage_sequence(stage: int, new_status: str, current_status: str) -> list:
    """校验阶段顺序是否合法"""
    errors = []

    # 不能从 not_started 直接跳到 completed（必须先 in_progress）
    if new_status == "completed" and current_status == "not_started":
        errors.append(f"[业务规则] stage_{stage} 不能直接从 not_started → completed，必须先经过 in_progress")

    return errors


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


def init_knowledge_progress(knowledge_id: str) -> dict:
    """为新知识点初始化所有进度记录（level=0 待学状态）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 检查是否已存在
            cursor.execute("SELECT knowledge_id FROM knowledge_progress WHERE knowledge_id = ?", (knowledge_id,))
            if cursor.fetchone():
                return {"success": False, "errors": [f"[初始化失败] 知识点进度已存在: {knowledge_id}"]}

            now = datetime.now().isoformat() + "+08:00"

            # 插入 knowledge_progress
            cursor.execute("""
                INSERT INTO knowledge_progress (knowledge_id, target_level, last_activity)
                VALUES (?, 7, ?)
            """, (knowledge_id, now))

            # 插入 foundation_path
            cursor.execute("""
                INSERT INTO foundation_path (knowledge_id, status, current_stage)
                VALUES (?, 'not_started', 1)
            """, (knowledge_id,))

            # 插入 4 个 stage_progress（全部 not_started）
            for stage in range(1, 5):
                cursor.execute("""
                    INSERT INTO stage_progress (knowledge_id, stage_name, status)
                    VALUES (?, ?, 'not_started')
                """, (knowledge_id, f"stage_{stage}"))

            # 插入 mastery_path
            cursor.execute("""
                INSERT INTO mastery_path (knowledge_id, status)
                VALUES (?, 'not_started')
            """, (knowledge_id,))

            # 插入 3 个 mastery_stage_progress
            for stage in range(5, 8):
                cursor.execute("""
                    INSERT INTO mastery_stage_progress (knowledge_id, stage_name, status)
                    VALUES (?, ?, 'not_started')
                """, (knowledge_id, f"stage_{stage}"))

            # 插入 interview_assets（空）
            cursor.execute("""
                INSERT INTO interview_assets (knowledge_id)
                VALUES (?)
            """, (knowledge_id,))

            # 插入 review_schedule
            cursor.execute("""
                INSERT INTO review_schedule (knowledge_id, current_round)
                VALUES (?, 0)
            """, (knowledge_id,))
            schedule_id = cursor.lastrowid

            # 插入 5 个复习轮次（pending）
            target_days = [1, 3, 7, 14, 30]
            for round_num, target_day in enumerate(target_days, 1):
                scheduled = (datetime.now() + timedelta(days=target_day)).strftime("%Y-%m-%d")
                cursor.execute("""
                    INSERT INTO review_round (schedule_id, round, target_day, scheduled_date, status)
                    VALUES (?, ?, ?, ?, 'pending')
                """, (schedule_id, round_num, target_day, scheduled))

            # 插入 mastery_review
            cursor.execute("""
                INSERT INTO mastery_review (schedule_id, enabled)
                VALUES (?, 0)
            """, (schedule_id,))

        return {"success": True, "knowledge_id": knowledge_id}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] init_knowledge_progress: {str(e)}"]}


def get_full_progress(knowledge_id: str) -> dict:
    """获取完整进度（包含所有关联表数据）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # knowledge_progress
            cursor.execute("SELECT * FROM knowledge_progress WHERE knowledge_id = ?", (knowledge_id,))
            kp_row = cursor.fetchone()
            if not kp_row:
                return {"success": False, "errors": [f"[查询失败] knowledge_progress 不存在: {knowledge_id}"]}
            kp = dict(kp_row)

            # foundation_path
            cursor.execute("SELECT * FROM foundation_path WHERE knowledge_id = ?", (knowledge_id,))
            fp_row = cursor.fetchone()
            fp = dict(fp_row) if fp_row else None

            # stage_progress（4个阶段）
            cursor.execute("SELECT * FROM stage_progress WHERE knowledge_id = ? ORDER BY stage_name", (knowledge_id,))
            stages = [dict(row) for row in cursor.fetchall()]
            for s in stages:
                if s["essence_keywords"]:
                    s["essence_keywords"] = json.loads(s["essence_keywords"])

            # mastery_path
            cursor.execute("SELECT * FROM mastery_path WHERE knowledge_id = ?", (knowledge_id,))
            mp_row = cursor.fetchone()
            mp = dict(mp_row) if mp_row else None

            # mastery_stage_progress（3个阶段）
            cursor.execute("SELECT * FROM mastery_stage_progress WHERE knowledge_id = ? ORDER BY stage_name", (knowledge_id,))
            mastery_stages = [dict(row) for row in cursor.fetchall()]

            # interview_assets
            cursor.execute("SELECT * FROM interview_assets WHERE knowledge_id = ?", (knowledge_id,))
            ia_row = cursor.fetchone()
            ia = dict(ia_row) if ia_row else None
            if ia and ia["validated_questions"]:
                ia["validated_questions"] = json.loads(ia["validated_questions"])

        # 重新计算 current_level（确保一致性）
        calculated_level = calculate_level(knowledge_id)

        result = {
            "knowledge_id": knowledge_id,
            "current_level": calculated_level,  # 使用计算值而非存储值
            "target_level": kp.get("target_level", 7),
            "last_activity": kp.get("last_activity"),
            "total_learning_minutes": kp.get("total_learning_minutes", 0),
            "foundation_path": fp,
            "stage_progress": {s["stage_name"]: s for s in stages},
            "mastery_path": mp,
            "mastery_stage_progress": {s["stage_name"]: s for s in mastery_stages},
            "interview_assets": ia,
        }

        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_full_progress: {str(e)}"]}


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
        print("用法: python progress_api.py <action> [args]")
        print("  init <knowledge_id>           - 初始化知识点进度")
        print("  get <knowledge_id>           - 获取完整进度")
        print("  update_progress <knowledge_id> <json>")
        print("  update_foundation <knowledge_id> <json>")
        print("  update_mastery <knowledge_id> <json>")
        print("  update_mastery_level <knowledge_id> <level>  - 更新 mastery_level (1-3)")
        print("  update_stage <knowledge_id> <stage_name> <json>")
        print("  update_session <json>")
        print("  get_session")
        sys.exit(1)

    action = sys.argv[1]

    if action == "init":
        result = init_knowledge_progress(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get":
        result = get_full_progress(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "update_progress":
        knowledge_id = sys.argv[2]
        data = json.loads(sys.argv[3])
        result = update_knowledge_progress(knowledge_id, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "update_foundation":
        knowledge_id = sys.argv[2]
        data = json.loads(sys.argv[3])
        result = update_foundation_path(knowledge_id, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "update_mastery":
        knowledge_id = sys.argv[2]
        data = json.loads(sys.argv[3])
        result = update_mastery_path(knowledge_id, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "update_stage":
        knowledge_id = sys.argv[2]
        stage_name = sys.argv[3]
        data = json.loads(sys.argv[4])
        result = update_stage_progress(knowledge_id, stage_name, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "update_session":
        data = json.loads(sys.argv[2])
        result = update_active_session(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_mastery_stage":
        knowledge_id = sys.argv[2]
        result = get_mastery_stage_progress(knowledge_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "update_mastery_stage":
        knowledge_id = sys.argv[2]
        stage_name = sys.argv[3]
        data = json.loads(sys.argv[4])
        result = update_mastery_stage(knowledge_id, stage_name, data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_session":
        result = get_active_session()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "update_mastery_level":
        # 确保字段存在（idempotent）
        _ensure_mastery_level_column()
        knowledge_id = sys.argv[2]
        level = int(sys.argv[3])
        result = update_mastery_path(knowledge_id, {"mastery_level": level})
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"[错误] 未知 action: {action}")
        sys.exit(1)
