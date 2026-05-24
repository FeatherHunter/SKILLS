"""
Learning System - 复习计划模块
包含复习计划创建、查询、轮次完成
"""
import json
from datetime import datetime, timedelta
from db_utils import get_db


def create_review_schedule(knowledge_id: str, foundation_completed_at: str = None) -> dict:
    """
    创建复习计划（基础流程完成时自动调用）
    创建 5 个轮次，target_day 分别为 1, 3, 7, 14, 30
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 检查是否已存在
            cursor.execute("SELECT id FROM review_schedule WHERE knowledge_id = ?", (knowledge_id,))
            if cursor.fetchone():
                return {"success": False, "errors": [f"[创建失败] 复习计划已存在: {knowledge_id}"]}

            # 检查知识点是否存在
            cursor.execute("SELECT id FROM knowledge_list WHERE id = ?", (knowledge_id,))
            if not cursor.fetchone():
                return {"success": False, "errors": [f"[创建失败] 知识点不存在: {knowledge_id}"]}

            # 计算基准日期（基础流程完成日期或今天）
            base_date = foundation_completed_at if foundation_completed_at else datetime.now().strftime("%Y-%m-%d")

            # 插入 review_schedule
            cursor.execute("""
                INSERT INTO review_schedule (knowledge_id, current_round)
                VALUES (?, 0)
            """, (knowledge_id,))
            schedule_id = cursor.lastrowid

            # 插入 5 个复习轮次
            target_days = [1, 3, 7, 14, 30]
            for round_num, target_day in enumerate(target_days, 1):
                scheduled = (datetime.strptime(base_date, "%Y-%m-%d") + timedelta(days=target_day)).strftime("%Y-%m-%d")
                cursor.execute("""
                    INSERT INTO review_round (schedule_id, round, target_day, scheduled_date, status)
                    VALUES (?, ?, ?, ?, 'pending')
                """, (schedule_id, round_num, target_day, scheduled))

            # 插入 mastery_review
            cursor.execute("""
                INSERT INTO mastery_review (schedule_id, enabled)
                VALUES (?, 0)
            """, (schedule_id,))

            return {"success": True, "knowledge_id": knowledge_id, "schedule_id": schedule_id}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] create_review_schedule: {str(e)}"]}


def get_review_schedule(knowledge_id: str) -> dict:
    """获取复习计划详情"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM review_schedule WHERE knowledge_id = ?", (knowledge_id,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "errors": [f"[查询失败] 复习计划不存在: {knowledge_id}"]}
            schedule = dict(row)

            schedule_id = schedule["id"]

            # 获取 5 个轮次
            cursor.execute("""
                SELECT * FROM review_round
                WHERE schedule_id = ?
                ORDER BY round
            """, (schedule_id,))
            rounds = [dict(r) for r in cursor.fetchall()]
            schedule["rounds"] = rounds

            # 获取 mastery_review
            cursor.execute("SELECT * FROM mastery_review WHERE schedule_id = ?", (schedule_id,))
            mr = cursor.fetchone()
            if mr:
                mr_dict = dict(mr)
                if mr_dict["history"]:
                    mr_dict["history"] = json.loads(mr_dict["history"])
                schedule["mastery_review"] = mr_dict

            return {"success": True, "data": schedule}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_review_schedule: {str(e)}"]}


def get_due_reviews(date: str = None) -> dict:
    """
    获取今日到期的复习列表
    date: YYYY-MM-DD 格式，默认今天
    """
    try:
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT rs.knowledge_id, k.title, rr.round, rr.scheduled_date, rr.status
                FROM review_schedule rs
                JOIN review_round rr ON rr.schedule_id = rs.id
                JOIN knowledge_list k ON k.id = rs.knowledge_id
                WHERE rr.scheduled_date <= ? AND rr.status = 'pending'
                ORDER BY rr.scheduled_date, rs.knowledge_id
            """, (date,))

            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    "knowledge_id": row["knowledge_id"],
                    "title": row["title"],
                    "round": row["round"],
                    "scheduled_date": row["scheduled_date"],
                    "is_overdue": row["scheduled_date"] < date
                })

            return {"success": True, "data": results, "count": len(results)}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_due_reviews: {str(e)}"]}


def complete_round(knowledge_id: str, round_num: int, score: int,
                   questions_count: int = None, correct_count: int = None,
                   duration_minutes: int = None, user_feedback: str = None,
                   wrong_questions: list = None) -> dict:
    """
    完成一轮复习
    更新 round 状态和 current_round，记录 history
    """
    try:
        if not (1 <= round_num <= 5):
            return {"success": False, "errors": [f"[校验失败] round 必须是 1-5，当前: {round_num}"]}

        if not (0 <= score <= 100):
            return {"success": False, "errors": [f"[校验失败] score 必须是 0-100，当前: {score}"]}

        with get_db() as conn:
            cursor = conn.cursor()

            # 获取 schedule_id
            cursor.execute("SELECT id FROM review_schedule WHERE knowledge_id = ?", (knowledge_id,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "errors": [f"[更新失败] 复习计划不存在: {knowledge_id}"]}
            schedule_id = row["id"]

            # 检查 round 是否存在且 pending
            cursor.execute("""
                SELECT status FROM review_round
                WHERE schedule_id = ? AND round = ?
            """, (schedule_id, round_num))
            rr_row = cursor.fetchone()
            if not rr_row:
                return {"success": False, "errors": [f"[更新失败] 轮次不存在: round={round_num}"]}
            if rr_row["status"] == "completed":
                return {"success": False, "errors": [f"[业务规则] 轮次 {round_num} 已完成，不能重复完成"]}

            now = datetime.now().isoformat() + "+08:00"

            # 更新 round 状态
            cursor.execute("""
                UPDATE review_round
                SET status = 'completed', completed_at = ?, score = ?, questions_count = ?
                WHERE schedule_id = ? AND round = ?
            """, (now, score, questions_count, schedule_id, round_num))

            # 更新 schedule.current_round
            cursor.execute("""
                UPDATE review_schedule
                SET current_round = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (round_num, schedule_id))

            # 写入 review_history
            cursor.execute("""
                INSERT INTO review_history
                (knowledge_id, round, review_date, duration_minutes, questions_count, correct_count, score, user_feedback, wrong_questions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                knowledge_id, round_num, now, duration_minutes,
                questions_count, correct_count, score, user_feedback,
                json.dumps(wrong_questions) if wrong_questions else None
            ))

            return {"success": True, "knowledge_id": knowledge_id, "round": round_num, "score": score}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] complete_round: {str(e)}"]}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python review_schedule.py <action> [args]")
        print("  create_schedule <knowledge_id> [completed_at]")
        print("  get_schedule <knowledge_id>")
        print("  get_due [date]")
        print("  complete_round <knowledge_id> <round> <score> [questions] [correct] [duration] [feedback] [wrong_json]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "create_schedule":
        knowledge_id = sys.argv[2]
        completed_at = sys.argv[3] if len(sys.argv) > 3 else None
        result = create_review_schedule(knowledge_id, completed_at)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_schedule":
        result = get_review_schedule(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_due":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        result = get_due_reviews(date)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "complete_round":
        knowledge_id = sys.argv[2]
        round_num = int(sys.argv[3])
        score = int(sys.argv[4])
        questions_count = int(sys.argv[5]) if len(sys.argv) > 5 else None
        correct_count = int(sys.argv[6]) if len(sys.argv) > 6 else None
        duration = int(sys.argv[7]) if len(sys.argv) > 7 else None
        feedback = sys.argv[8] if len(sys.argv) > 8 else None
        wrong = json.loads(sys.argv[9]) if len(sys.argv) > 9 else None

        result = complete_round(knowledge_id, round_num, score, questions_count, correct_count, duration, feedback, wrong)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"[错误] 未知 action: {action}")
        sys.exit(1)
