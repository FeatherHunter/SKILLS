"""
Learning System - 精通复习模块
包含精通复习启用、记录、状态查询
"""
import json
from datetime import datetime, timedelta
from db_utils import get_db


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
        print("用法: python review_mastery.py <action> [args]")
        print("  enable_mastery <knowledge_id>")
        print("  record_mastery <knowledge_id> [score]")
        print("  get_mastery_status <knowledge_id>")
        sys.exit(1)

    action = sys.argv[1]

    if action == "enable_mastery":
        if len(sys.argv) < 3:
            print("用法: python review_mastery.py enable_mastery <knowledge_id>")
            sys.exit(1)
        result = enable_mastery_review(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "record_mastery":
        if len(sys.argv) < 3:
            print("用法: python review_mastery.py record_mastery <knowledge_id> [score]")
            sys.exit(1)
        score = int(sys.argv[3]) if len(sys.argv) > 3 else None
        result = record_mastery_review(sys.argv[2], score)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif action == "get_mastery_status":
        if len(sys.argv) < 3:
            print("用法: python review_mastery.py get_mastery_status <knowledge_id>")
            sys.exit(1)
        result = get_mastery_review_status(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        print(f"未知操作: {action}")
        sys.exit(1)
