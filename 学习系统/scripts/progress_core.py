"""
Learning System - 学习进度核心模块
包含常量定义、Level 计算、进度初始化和查询
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


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python progress_core.py <action> [args]")
        print("  init <knowledge_id>           - 初始化知识点进度")
        print("  get <knowledge_id>            - 获取完整进度")
        sys.exit(1)

    action = sys.argv[1]

    if action == "init":
        result = init_knowledge_progress(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get":
        result = get_full_progress(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"[错误] 未知 action: {action}")
        sys.exit(1)
