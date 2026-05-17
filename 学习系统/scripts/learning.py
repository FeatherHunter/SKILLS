#!/usr/bin/env python3
"""
Learning System CLI 入口
统一路由到各个 API 模块
三层查找DB路径：环境变量 > 技能目录 > 父目录.db文件夹
"""
import sys
import json
import os
from pathlib import Path

# 添加 scripts 目录到 path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

import db_init
import knowledge_api
import progress_api
import review_api
import integration_api


def cmd_knowledge(args):
    """知识点元数据操作"""
    action = args[0] if args else None
    
    if action == "add":
        # python learning.py knowledge add <json_data>
        data = json.loads(args[1])
        result = knowledge_api.add_knowledge(data)
    
    elif action == "get":
        result = knowledge_api.get_knowledge(args[1])
    
    elif action == "list":
        filters = {}
        if len(args) > 1:
            filters["category"] = args[1]
        if len(args) > 2:
            filters["language"] = args[2]
        result = knowledge_api.list_knowledge(filters)
    
    elif action == "update":
        knowledge_id = args[1]
        data = json.loads(args[2])
        result = knowledge_api.update_knowledge(knowledge_id, data)
    
    elif action == "delete":
        result = knowledge_api.delete_knowledge(args[1])
    
    else:
        print("[错误] unknown action:", action)
        sys.exit(1)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_progress(args):
    """学习进度操作"""
    action = args[0] if args else None
    
    if action == "init":
        result = progress_api.init_knowledge_progress(args[1])
    
    elif action == "get":
        result = progress_api.get_full_progress(args[1])
    
    elif action == "update":
        knowledge_id = args[1]
        data = json.loads(args[2])
        result = progress_api.update_knowledge_progress(knowledge_id, data)
    
    elif action == "update_foundation":
        knowledge_id = args[1]
        data = json.loads(args[2])
        result = progress_api.update_foundation_path(knowledge_id, data)
    
    elif action == "update_mastery":
        knowledge_id = args[1]
        data = json.loads(args[2])
        result = progress_api.update_mastery_path(knowledge_id, data)
    
    elif action == "update_stage":
        knowledge_id = args[1]
        stage_name = args[2]
        data = json.loads(args[3])
        result = progress_api.update_stage_progress(knowledge_id, stage_name, data)
    
    elif action == "update_session":
        data = json.loads(args[1])
        result = progress_api.update_active_session(data)
    
    elif action == "get_session":
        result = progress_api.get_active_session()
    
    elif action == "update_mastery_stage":
        knowledge_id = args[1]
        stage_name = args[2]
        data = json.loads(args[3])
        result = progress_api.update_mastery_stage_progress(knowledge_id, stage_name, data)
    
    elif action == "update_interview_assets":
        knowledge_id = args[1]
        field = args[2]
        value = args[3]
        result = progress_api.update_interview_assets(knowledge_id, field, value)
    
    else:
        print("[错误] unknown action:", action)
        sys.exit(1)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_review(args):
    """复习操作"""
    action = args[0] if args else None
    
    if action == "create_schedule":
        completed_at = args[2] if len(args) > 2 else None
        result = review_api.create_review_schedule(args[1], completed_at)
    
    elif action == "get_schedule":
        result = review_api.get_review_schedule(args[1])
    
    elif action == "get_due":
        date = args[1] if len(args) > 1 else None
        result = review_api.get_due_reviews(date)
    
    elif action == "complete_round":
        knowledge_id = args[1]
        round_num = int(args[2])
        score = int(args[3])
        questions_count = int(args[4]) if len(args) > 4 else None
        correct_count = int(args[5]) if len(args) > 5 else None
        duration = int(args[6]) if len(args) > 6 else None
        feedback = args[7] if len(args) > 7 else None
        wrong = json.loads(args[8]) if len(args) > 8 else None
        result = review_api.complete_round(knowledge_id, round_num, score, questions_count, correct_count, duration, feedback, wrong)
    
    elif action == "add_verification":
        knowledge_id = args[1]
        round_num = int(args[2])
        user_choice = args[3]
        results = json.loads(args[4])
        passed = int(args[5])
        failed = int(args[6])
        result = review_api.add_verification(knowledge_id, round_num, user_choice, results, passed, failed)
    
    elif action == "add_history":
        knowledge_id = args[1]
        round_num = int(args[2])
        review_date = args[3]
        duration = int(args[4]) if len(args) > 4 else None
        questions = int(args[5]) if len(args) > 5 else None
        correct = int(args[6]) if len(args) > 6 else None
        score = int(args[7]) if len(args) > 7 else None
        feedback = args[8] if len(args) > 8 else None
        wrong_json = args[9] if len(args) > 9 else None
        wrong_list = json.loads(wrong_json) if wrong_json else None
        result = review_api.add_review_history(knowledge_id, round_num, review_date, duration, questions, correct, score, feedback, wrong_list)
    
    elif action == "get_history":
        knowledge_id = args[1] if len(args) > 1 else None
        limit = int(args[2]) if len(args) > 2 else 20
        result = review_api.get_review_history(knowledge_id, limit)
    
    elif action == "get_weak":
        result = review_api.get_weak_topics(args[1])
    
    elif action == "enable_mastery":
        result = review_api.enable_mastery_review(args[1])
    
    elif action == "record_mastery":
        score = int(args[2]) if len(args) > 2 else None
        result = review_api.record_mastery_review(args[1], score)
    
    elif action == "get_mastery_status":
        result = review_api.get_mastery_review_status(args[1])
    
    else:
        print("[错误] unknown action:", action)
        sys.exit(1)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_integration(args):
    """能力整合操作"""
    action = args[0] if args else None
    
    if action == "create":
        data = json.loads(args[1])
        result = integration_api.create_scenario(data)
    
    elif action == "get":
        result = integration_api.get_scenario(args[1])
    
    elif action == "list":
        mode = args[1] if len(args) > 1 else None
        difficulty = args[2] if len(args) > 2 else None
        limit = int(args[3]) if len(args) > 3 else 50
        result = integration_api.list_scenarios(mode, difficulty, limit)
    
    elif action == "update_solution":
        scenario_id = args[1]
        summary = args[2]
        feedback = json.loads(args[3])
        interest = json.loads(args[4]) if len(args) > 4 else None
        result = integration_api.update_solution(scenario_id, summary, feedback, interest)
    
    elif action == "stats":
        result = integration_api.get_scenario_stats()
    
    elif action == "recent_practiced":
        limit = int(args[1]) if len(args) > 1 else 10
        result = integration_api.get_recent_practiced_knowledge(limit)
        print(json.dumps({"success": True, "data": result}, ensure_ascii=False, indent=2))
        return
    
    else:
        print("[错误] unknown action:", action)
        sys.exit(1)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_init():
    """初始化数据库"""
    db_init.init_database()
    print("[OK] 数据库初始化完成")


def cmd_status():
    """查看整体状态"""
    version_info = db_init.get_version()
    
    conn = db_init.get_connection()
    cursor = conn.cursor()
    
    # 各表记录数
    tables = [
        ("knowledge_list", "知识点"),
        ("knowledge_progress", "进度记录"),
        ("review_schedule", "复习计划"),
        ("review_history", "复习历史"),
        ("integration_scenario", "整合场景"),
    ]
    
    counts = {}
    for table, name in tables:
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
        counts[name] = cursor.fetchone()["cnt"]
    
    # active_session
    cursor.execute("SELECT * FROM active_session WHERE id = 1")
    session = dict(cursor.fetchone())
    
    conn.close()
    
    print("=" * 50)
    print("Learning System 状态")
    print("=" * 50)
    print(f"数据库路径: {db_init.DB_PATH}")
    print(f"数据库版本:")
    for key, ver in version_info.items():
        print(f"  {key}: {ver}")
    print()
    print("记录统计:")
    for name, cnt in counts.items():
        print(f"  {name}: {cnt}")
    print()
    print("当前会话:")
    print(f"  knowledge_id: {session.get('knowledge_id')}")
    print(f"  path_type: {session.get('path_type')}")
    print(f"  stage: {session.get('stage')}")
    print(f"  step: {session.get('step')}")
    print(f"  total_minutes: {session.get('total_minutes', 0)}")
    print("=" * 50)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "init":
        cmd_init()
    
    elif cmd == "status":
        cmd_status()
    
    elif cmd == "knowledge":
        cmd_knowledge(sys.argv[2:])
    
    elif cmd == "progress":
        cmd_progress(sys.argv[2:])
    
    elif cmd == "review":
        cmd_review(sys.argv[2:])
    
    elif cmd == "integration":
        cmd_integration(sys.argv[2:])
    
    else:
        print("[错误] unknown command:", cmd)
        print(__doc__)
        sys.exit(1)