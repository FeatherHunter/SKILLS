"""
Learning System - 复习历史模块
包含复习历史记录、验证、薄弱点分析
"""
import json
from datetime import datetime
from db_utils import get_db

ALLOWED_REVIEW_FIELDS = {
    "knowledge_id", "round", "review_date", "duration_minutes",
    "questions_count", "correct_count", "score", "user_feedback",
    "wrong_questions", "verification"
}
VALID_USER_CHOICE = {"now", "skip"}


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


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python review_history.py <action> [args]")
        print("  add_verification <knowledge_id> <round> <user_choice> <json_results> <passed> <failed>")
        print("  add_history <knowledge_id> <round> <review_date> [duration] [questions] [correct] [score] [feedback] [wrong_json]")
        print("  get_history [knowledge_id] [limit]")
        print("  get_weak <knowledge_id>")
        sys.exit(1)

    action = sys.argv[1]

    if action == "add_verification":
        knowledge_id = sys.argv[2]
        round_num = int(sys.argv[3])
        user_choice = sys.argv[4]
        results = json.loads(sys.argv[5])
        passed = int(sys.argv[6])
        failed = int(sys.argv[7])
        result = add_verification(knowledge_id, round_num, user_choice, results, passed, failed)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "add_history":
        knowledge_id = sys.argv[2]
        round_num = int(sys.argv[3])
        review_date = sys.argv[4]
        duration = int(sys.argv[5]) if len(sys.argv) > 5 else None
        questions = int(sys.argv[6]) if len(sys.argv) > 6 else None
        correct = int(sys.argv[7]) if len(sys.argv) > 7 else None
        score = int(sys.argv[8]) if len(sys.argv) > 8 else None
        feedback = sys.argv[9] if len(sys.argv) > 9 else None
        wrong = json.loads(sys.argv[10]) if len(sys.argv) > 10 else None
        result = add_review_history(knowledge_id, round_num, review_date, duration, questions, correct, score, feedback, wrong)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_history":
        knowledge_id = sys.argv[2] if len(sys.argv) > 2 else None
        limit = int(sys.argv[3]) if len(sys.argv) > 3 else 20
        result = get_review_history(knowledge_id, limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_weak":
        result = get_weak_topics(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"[错误] 未知 action: {action}")
        sys.exit(1)
