"""
Learning System - 能力整合 API
对照 ls-data-structure.md 中 integration-scenarios.json 设计
严格校验字段和业务规则
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

ALLOWED_SCENARIO_FIELDS = {
    "id", "scenario", "mode", "knowledge_used", "knowledge_unlearned",
    "knowledge_unlearned_explanations", "difficulty", "created_at",
    "user_solution_summary", "ai_feedback", "unlearned_interest"
}
VALID_MODES = {"known", "explore"}
VALID_DIFFICULTIES = {"senior", "architect"}


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def generate_id() -> str:
    """生成场景 ID：int-XXX 格式，XXX 是 3 位序号"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id FROM integration_scenario 
        ORDER BY id DESC LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    
    if row:
        # 提取序号 +1
        last_num = int(row["id"].split("-")[1])
        return f"int-{last_num + 1:03d}"
    else:
        return "int-001"


def validate_fields(data: dict) -> list:
    """校验字段，返回错误列表"""
    errors = []
    
    # 检查必填字段
    if "scenario" not in data or not data["scenario"]:
        errors.append("[校验失败] scenario 是必填字段")
    
    if "mode" not in data or data["mode"] not in VALID_MODES:
        errors.append(f"[校验失败] mode 必须是 {VALID_MODES} 之一")
    
    if "difficulty" in data and data["difficulty"] not in VALID_DIFFICULTIES:
        errors.append(f"[校验失败] difficulty 必须是 {VALID_DIFFICULTIES} 之一")
    
    # 检查多余字段
    extra_fields = set(data.keys()) - ALLOWED_SCENARIO_FIELDS
    if extra_fields:
        errors.append(f"[校验失败] 不认识的字段: {extra_fields}")
    
    # 检查 knowledge_used 格式
    if "knowledge_used" in data and data["knowledge_used"] is not None:
        if isinstance(data["knowledge_used"], list):
            pass
        elif isinstance(data["knowledge_used"], str):
            try:
                parsed = json.loads(data["knowledge_used"])
                if not isinstance(parsed, list):
                    errors.append("[校验失败] knowledge_used 必须是 JSON array")
            except json.JSONDecodeError:
                errors.append("[校验失败] knowledge_used JSON 格式错误")
        else:
            errors.append("[校验失败] knowledge_used 格式错误")
    
    # 检查 knowledge_unlearned 格式
    if "knowledge_unlearned" in data and data["knowledge_unlearned"] is not None:
        if isinstance(data["knowledge_unlearned"], list):
            pass
        elif isinstance(data["knowledge_unlearned"], str):
            try:
                parsed = json.loads(data["knowledge_unlearned"])
                if not isinstance(parsed, list):
                    errors.append("[校验失败] knowledge_unlearned 必须是 JSON array")
            except json.JSONDecodeError:
                errors.append("[校验失败] knowledge_unlearned JSON 格式错误")
    
    # 检查 knowledge_unlearned_explanations 格式
    if "knowledge_unlearned_explanations" in data and data["knowledge_unlearned_explanations"] is not None:
        if isinstance(data["knowledge_unlearned_explanations"], dict):
            pass
        elif isinstance(data["knowledge_unlearned_explanations"], str):
            try:
                parsed = json.loads(data["knowledge_unlearned_explanations"])
                if not isinstance(parsed, dict):
                    errors.append("[校验失败] knowledge_unlearned_explanations 必须是 JSON object")
            except json.JSONDecodeError:
                errors.append("[校验失败] knowledge_unlearned_explanations JSON 格式错误")
    
    return errors


def create_scenario(data: dict) -> dict:
    """
    创建能力整合练习场景
    输入: {
        "scenario": "设计一个消息推送系统",
        "mode": "known" | "explore",
        "difficulty": "senior" | "architect",
        "knowledge_used": ["android-binder", "java-threadpool"],
        "knowledge_unlearned": [],  # mode=explore 时使用
        "knowledge_unlearned_explanations": {}
    }
    """
    errors = validate_fields(data)
    if errors:
        return {"success": False, "errors": errors}
    
    # mode=explore 时需要 knowledge_unlearned
    if data["mode"] == "explore" and not data.get("knowledge_unlearned"):
        return {"success": False, "errors": ["[校验失败] mode=explore 时 knowledge_unlearned 不能为空"]}
    
    scenario_id = generate_id()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat() + "+08:00"
    
    cursor.execute("""
        INSERT INTO integration_scenario 
        (id, scenario, mode, knowledge_used, knowledge_unlearned, 
         knowledge_unlearned_explanations, difficulty, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        scenario_id,
        data["scenario"],
        data["mode"],
        json.dumps(data["knowledge_used"]) if data.get("knowledge_used") else None,
        json.dumps(data["knowledge_unlearned"]) if data.get("knowledge_unlearned") else None,
        json.dumps(data["knowledge_unlearned_explanations"]) if data.get("knowledge_unlearned_explanations") else None,
        data.get("difficulty"),
        now
    ))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "id": scenario_id}


def update_solution(scenario_id: str, user_solution_summary: str, 
                    ai_feedback: dict, unlearned_interest: list = None) -> dict:
    """
    更新场景的答题结果
    ai_feedback: {"score": 78, "strengths": [...], "weak_areas": [...], "missed_tradeoffs": [...]}
    """
    if not isinstance(ai_feedback, dict):
        return {"success": False, "errors": ["[校验失败] ai_feedback 必须是 JSON object"]}
    
    score = ai_feedback.get("score")
    if score is not None and not (0 <= score <= 100):
        return {"success": False, "errors": [f"[校验失败] score 必须是 0-100，当前: {score}"]}
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM integration_scenario WHERE id = ?", (scenario_id,))
    if not cursor.fetchone():
        conn.close()
        return {"success": False, "errors": [f"[更新失败] 场景不存在: {scenario_id}"]}
    
    cursor.execute("""
        UPDATE integration_scenario 
        SET user_solution_summary = ?,
            ai_feedback = ?,
            unlearned_interest = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        user_solution_summary,
        json.dumps(ai_feedback, ensure_ascii=False),
        json.dumps(unlearned_interest) if unlearned_interest else None,
        scenario_id
    ))
    
    conn.commit()
    conn.close()
    
    return {"success": True, "id": scenario_id, "score": score}


def get_scenario(scenario_id: str) -> dict:
    """获取场景详情"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM integration_scenario WHERE id = ?", (scenario_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {"success": False, "errors": [f"[查询失败] 场景不存在: {scenario_id}"]}
    
    result = dict(row)
    
    # 反序列化 JSON 字段
    for field in ["knowledge_used", "knowledge_unlearned", "knowledge_unlearned_explanations", "ai_feedback", "unlearned_interest"]:
        if result.get(field):
            result[field] = json.loads(result[field])
    
    return {"success": True, "data": result}


def list_scenarios(mode: str = None, difficulty: str = None, limit: int = 50) -> dict:
    """列出场景（支持过滤）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM integration_scenario WHERE 1=1"
    params = []
    
    if mode:
        query += " AND mode = ?"
        params.append(mode)
    if difficulty:
        query += " AND difficulty = ?"
        params.append(difficulty)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        item = dict(row)
        for field in ["knowledge_used", "knowledge_unlearned", "knowledge_unlearned_explanations", "ai_feedback", "unlearned_interest"]:
            if item.get(field):
                item[field] = json.loads(item[field])
        results.append(item)
    
    return {"success": True, "data": results, "count": len(results)}


def get_recent_practiced_knowledge(limit: int = 10) -> list:
    """获取最近练习过的知识点（用于避免重复出题）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT knowledge_used FROM integration_scenario
        WHERE user_solution_summary IS NOT NULL
        ORDER BY updated_at DESC
        LIMIT ?
    """, (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    all_ids = set()
    for row in rows:
        if row["knowledge_used"]:
            ids = json.loads(row["knowledge_used"])
            all_ids.update(ids)
    
    return list(all_ids)


def get_scenario_stats() -> dict:
    """获取场景统计"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN user_solution_summary IS NOT NULL THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN mode = 'known' THEN 1 ELSE 0 END) as known_count,
            SUM(CASE WHEN mode = 'explore' THEN 1 ELSE 0 END) as explore_count,
            AVG(CASE WHEN ai_feedback IS NOT NULL THEN json_extract(ai_feedback, '$.score') ELSE NULL END) as avg_score
        FROM integration_scenario
    """)
    
    row = cursor.fetchone()
    conn.close()
    
    return {
        "success": True,
        "data": {
            "total": row["total"] or 0,
            "completed": row["completed"] or 0,
            "known_count": row["known_count"] or 0,
            "explore_count": row["explore_count"] or 0,
            "avg_score": round(row["avg_score"], 1) if row["avg_score"] else None
        }
    }


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python integration_api.py <action> [args]")
        print("  create <json_data>")
        print("  get <scenario_id>")
        print("  list [mode] [difficulty] [limit]")
        print("  update_solution <scenario_id> <summary> <json_feedback> [unlearned_interest_json]")
        print("  stats")
        print("  recent_practiced [limit]")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == "create":
        data = json.loads(sys.argv[2])
        result = create_scenario(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif action == "get":
        result = get_scenario(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif action == "list":
        mode = sys.argv[2] if len(sys.argv) > 2 else None
        difficulty = sys.argv[3] if len(sys.argv) > 3 else None
        limit = int(sys.argv[4]) if len(sys.argv) > 4 else 50
        result = list_scenarios(mode, difficulty, limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif action == "update_solution":
        scenario_id = sys.argv[2]
        summary = sys.argv[3]
        feedback = json.loads(sys.argv[4])
        interest = json.loads(sys.argv[5]) if len(sys.argv) > 5 else None
        result = update_solution(scenario_id, summary, feedback, interest)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif action == "stats":
        result = get_scenario_stats()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif action == "recent_practiced":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        result = get_recent_practiced_knowledge(limit)
        print(json.dumps({"success": True, "data": result}, ensure_ascii=False, indent=2))
    
    else:
        print(f"[错误] 未知 action: {action}")
        sys.exit(1)