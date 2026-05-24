"""
Learning System - 复习API
对照 ls-data-structure.md 中 review-schedule.json 和 review-history.json 设计
严格校验字段和业务规则
"""
import json
from datetime import datetime, timedelta
from db_utils import get_db

ALLOWED_REVIEW_FIELDS = {
    "knowledge_id", "round", "review_date", "duration_minutes",
    "questions_count", "correct_count", "score", "user_feedback",
    "wrong_questions", "verification"
}
VALID_ROUND_STATUS = {"pending", "completed"}
VALID_USER_CHOICE = {"now", "skip"}


# ============================================
# 复习计划操作
# ============================================

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


def add_verification(knowledge_id: str, round_num: int,
                     user_choice: str, results: list,
                     passed_count: int, failed_count: int) -> dict:
    """
    添加即时验证记录（错题>=2时触发）
    更新 review_history 中最新一条记录的 verification 字段
    """
    try:
        if user_choice not in VALID_USER_CHOICE:
            return {"success": False, "errors": [f"[校验失败] user_choice 必须是 {VALID_USER_CHOICE} 之一"]}

        with get_db() as conn:
            cursor = conn.cursor()

            # 找到该知识点该轮次最新一条 history
            cursor.execute("""
                SELECT id FROM review_history
                WHERE knowledge_id = ? AND round = ?
                ORDER BY id DESC LIMIT 1
            """, (knowledge_id, round_num))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "errors": [f"[更新失败] 复习历史不存在: {knowledge_id} round={round_num}"]}

            history_id = row["id"]

            verification = {
                "user_choice": user_choice,
                "results": results,
                "passed_count": passed_count,
                "failed_count": failed_count
            }

            cursor.execute("""
                UPDATE review_history
                SET verification = ?
                WHERE id = ?
            """, (json.dumps(verification, ensure_ascii=False), history_id))

            return {"success": True, "history_id": history_id}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] add_verification: {str(e)}"]}


def add_review_history(knowledge_id: str, round_num: int, review_date: str,
                          duration_minutes: int = None, questions_count: int = None,
                          correct_count: int = None, score: int = None,
                          user_feedback: str = None, wrong_questions: list = None) -> dict:
    """
    添加复习历史记录（复习完成时写入）
    """
    try:
        if round_num not in [1, 2, 3, 4, 5]:
            return {"success": False, "errors": ["[校验失败] round 必须是 1-5"]}

        if score is not None and (score < 0 or score > 100):
            return {"success": False, "errors": ["[校验失败] score 必须在 0-100 之间"]}

        with get_db() as conn:
            cursor = conn.cursor()

            # 检查 knowledge_id 是否存在
            cursor.execute("SELECT id FROM knowledge_list WHERE id = ?", (knowledge_id,))
            if not cursor.fetchone():
                return {"success": False, "errors": [f"[校验失败] 知识点不存在: {knowledge_id}"]}

            cursor.execute("""
                INSERT INTO review_history
                (knowledge_id, round, review_date, duration_minutes, questions_count,
                 correct_count, score, user_feedback, wrong_questions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                knowledge_id,
                round_num,
                review_date,
                duration_minutes,
                questions_count,
                correct_count,
                score,
                user_feedback,
                json.dumps(wrong_questions, ensure_ascii=False) if wrong_questions else None
            ))

            history_id = cursor.lastrowid

            return {"success": True, "id": history_id, "knowledge_id": knowledge_id, "round": round_num}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] add_review_history: {str(e)}"]}


def get_review_history(knowledge_id: str = None, limit: int = 20) -> dict:
    """获取复习历史"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            if knowledge_id:
                cursor.execute("""
                    SELECT rh.*, k.title
                    FROM review_history rh
                    JOIN knowledge_list k ON k.id = rh.knowledge_id
                    WHERE rh.knowledge_id = ?
                    ORDER BY rh.review_date DESC
                    LIMIT ?
                """, (knowledge_id, limit))
            else:
                cursor.execute("""
                    SELECT rh.*, k.title
                    FROM review_history rh
                    JOIN knowledge_list k ON k.id = rh.knowledge_id
                    ORDER BY rh.review_date DESC
                    LIMIT ?
                """, (limit,))

            rows = cursor.fetchall()

            results = []
            for row in rows:
                item = dict(row)
                if item.get("wrong_questions"):
                    item["wrong_questions"] = json.loads(item["wrong_questions"])
                if item.get("verification"):
                    item["verification"] = json.loads(item["verification"])
                results.append(item)

            return {"success": True, "data": results, "count": len(results)}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_review_history: {str(e)}"]}


def get_weak_topics(knowledge_id: str) -> dict:
    """获取薄弱点（从最近一次 verification 中提取 failed=true 的 topics）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # 找到该知识点最新一条有 verification 的记录
            cursor.execute("""
                SELECT verification FROM review_history
                WHERE knowledge_id = ? AND verification IS NOT NULL
                ORDER BY id DESC LIMIT 1
            """, (knowledge_id,))
            row = cursor.fetchone()

            if not row or not row["verification"]:
                return {"success": True, "data": [], "message": "无验证记录"}

            ver = json.loads(row["verification"])
            failed_topics = [r["topic"] for r in ver.get("results", []) if not r.get("passed")]

            return {"success": True, "data": failed_topics}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_weak_topics: {str(e)}"]}


# ============================================
# 精通复习操作
# ============================================

def enable_mastery_review(knowledge_id: str) -> dict:
    """启用精通复习（精通流程完成时调用）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT mr.id FROM mastery_review mr
                JOIN review_schedule rs ON rs.id = mr.schedule_id
                WHERE rs.knowledge_id = ?
            """, (knowledge_id,))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "errors": [f"[更新失败] 复习计划不存在: {knowledge_id}"]}

            next_review = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

            cursor.execute("""
                UPDATE mastery_review
                SET enabled = 1, next_review = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (next_review, row["id"]))

            return {"success": True, "next_review": next_review}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] enable_mastery_review: {str(e)}"]}


def record_mastery_review(knowledge_id: str, score: int = None) -> dict:
    """记录一次精通复习"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT mr.id, mr.history FROM mastery_review mr
                JOIN review_schedule rs ON rs.id = mr.schedule_id
                WHERE rs.knowledge_id = ?
            """, (knowledge_id,))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "errors": [f"[更新失败] 复习计划不存在: {knowledge_id}"]}

            mr_id = row["id"]
            history = json.loads(row["history"]) if row["history"] else []

            # 添加新记录
            record = {
                "date": datetime.now().isoformat() + "+08:00",
                "score": score
            }
            history.append(record)

            # 更新 next_review（再 +30 天）
            next_review = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

            cursor.execute("""
                UPDATE mastery_review
                SET history = ?, last_review = ?, next_review = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(history, ensure_ascii=False), record["date"], next_review, mr_id))

            return {"success": True, "next_review": next_review}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] record_mastery_review: {str(e)}"]}


def get_mastery_review_status(knowledge_id: str) -> dict:
    """获取精通复习状态"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT mr.* FROM mastery_review mr
                JOIN review_schedule rs ON rs.id = mr.schedule_id
                WHERE rs.knowledge_id = ?
            """, (knowledge_id,))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "errors": [f"[查询失败] 复习计划不存在: {knowledge_id}"]}

            result = dict(row)
            if result.get("history"):
                result["history"] = json.loads(result["history"])

            return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_mastery_review_status: {str(e)}"]}


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python review_api.py <action> [args]")
        print("  create_schedule <knowledge_id> [foundation_completed_at]")
        print("  get_schedule <knowledge_id>")
        print("  get_due [date]")
        print("  complete_round <knowledge_id> <round> <score> [options]")
        print("  add_verification <knowledge_id> <round> <user_choice> <json_results>")
        print("  get_history [knowledge_id] [limit]")
        print("  get_weak <knowledge_id>")
        print("  enable_mastery <knowledge_id>")
        print("  record_mastery <knowledge_id> [score]")
        print("  get_mastery_status <knowledge_id>")
        sys.exit(1)

    action = sys.argv[1]

    if action == "create_schedule":
        completed_at = sys.argv[3] if len(sys.argv) > 3 else None
        result = create_review_schedule(sys.argv[2], completed_at)
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
        # 可选参数
        questions_count = int(sys.argv[5]) if len(sys.argv) > 5 else None
        correct_count = int(sys.argv[6]) if len(sys.argv) > 6 else None
        duration = int(sys.argv[7]) if len(sys.argv) > 7 else None
        feedback = sys.argv[8] if len(sys.argv) > 8 else None
        wrong = json.loads(sys.argv[9]) if len(sys.argv) > 9 else None

        result = complete_round(knowledge_id, round_num, score, questions_count, correct_count, duration, feedback, wrong)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "add_verification":
        knowledge_id = sys.argv[2]
        round_num = int(sys.argv[3])
        user_choice = sys.argv[4]
        results = json.loads(sys.argv[5])
        passed = int(sys.argv[6])
        failed = int(sys.argv[7])
        result = add_verification(knowledge_id, round_num, user_choice, results, passed, failed)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_history":
        knowledge_id = sys.argv[2] if len(sys.argv) > 2 else None
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        result = get_review_history(knowledge_id, limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_weak":
        result = get_weak_topics(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "enable_mastery":
        result = enable_mastery_review(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "record_mastery":
        score = int(sys.argv[3]) if len(sys.argv) > 3 else None
        result = record_mastery_review(sys.argv[2], score)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_mastery_status":
        result = get_mastery_review_status(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"[错误] 未知 action: {action}")
        sys.exit(1)
