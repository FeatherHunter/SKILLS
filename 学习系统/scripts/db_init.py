"""
Learning System 数据库初始化脚本
对照 ls-data-structure.md 设计，所有表结构严格匹配 JSON 结构
三层查找DB路径：环境变量 > 技能目录 > 父目录.db文件夹
"""
import sqlite3
import json
import re
import os
from pathlib import Path

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
        # 环境变量目录存在但不包含文件，仍使用该路径
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
            # .db 目录存在，使用该路径
            return p
    
    # 4. 都找不到则创建在技能目录下的 .db
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(parents=True, exist_ok=True)
    return default_db_dir / db_filename


DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """创建所有表，严格对照 ls-data-structure.md"""
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # ============================================
    # 表1: knowledge_list（知识点元数据）
    # 对应 knowledge-list.json
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_list (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            language TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            framework TEXT,
            tags TEXT,  -- JSON array stored as TEXT
            metadata TEXT,  -- JSON object stored as TEXT
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ============================================
    # 表2: knowledge_progress（学习进度）
    # 对应 progress.json → knowledge_progress
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_progress (
            knowledge_id TEXT PRIMARY KEY,
            target_level INTEGER DEFAULT 7,
            last_activity TIMESTAMP,
            total_learning_minutes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
        )
    """)
    
    # ============================================
    # 表3: foundation_path（基础流程进度）
    # 对应 progress.json → knowledge_progress[].foundation_path
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foundation_path (
            knowledge_id TEXT PRIMARY KEY,
            status TEXT NOT NULL CHECK(status IN ('not_started', 'in_progress', 'completed')),
            current_stage INTEGER DEFAULT 1 CHECK(current_stage BETWEEN 1 AND 4),
            completed_at TIMESTAMP,
            total_learning_minutes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
        )
    """)
    
    # ============================================
    # 表4: stage_progress（阶段进度）
    # 对应 progress.json → foundation_path.stage_progress.stage_N
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stage_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knowledge_id TEXT NOT NULL,
            stage_name TEXT NOT NULL CHECK(stage_name IN ('stage_1', 'stage_2', 'stage_3', 'stage_4')),
            status TEXT NOT NULL CHECK(status IN ('not_started', 'in_progress', 'completed')),
            completed_at TIMESTAMP,
            essence_keywords TEXT,  -- JSON array stored as TEXT
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id),
            UNIQUE(knowledge_id, stage_name)
        )
    """)
    
    # ============================================
    # 表5: mastery_path（精通流程进度）
    # 对应 progress.json → knowledge_progress[].mastery_path
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mastery_path (
            knowledge_id TEXT PRIMARY KEY,
            status TEXT NOT NULL CHECK(status IN ('not_started', 'in_progress', 'completed')),
            current_stage INTEGER CHECK(current_stage BETWEEN 5 AND 7),
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            total_learning_minutes INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
        )
    """)
    
    # ============================================
    # 表6: mastery_stage_progress（精通阶段进度）
    # 对应 progress.json → mastery_path.stage_progress.stage_N
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mastery_stage_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knowledge_id TEXT NOT NULL,
            stage_name TEXT NOT NULL CHECK(stage_name IN ('stage_5', 'stage_6', 'stage_7')),
            status TEXT NOT NULL CHECK(status IN ('not_started', 'in_progress', 'completed')),
            step INTEGER DEFAULT 1,
            cases_documented INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id),
            UNIQUE(knowledge_id, stage_name)
        )
    """)
    
    # ============================================
    # 表7: interview_assets（面试素材路径）
    # 对应 progress.json → knowledge_progress[].interview_assets
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_assets (
            knowledge_id TEXT PRIMARY KEY,
            star_case_path TEXT,
            failure_case_path TEXT,
            adr_path TEXT,
            validated_questions TEXT,  -- JSON array stored as TEXT
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
        )
    """)
    
    
    # ============================================
    # 表9: active_session（当前学习会话）
    # 对应 progress.json → active_session
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_session (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            knowledge_id TEXT,
            path_type TEXT CHECK(path_type IN ('foundation', 'mastery', 'unknown') OR path_type IS NULL),
            stage INTEGER CHECK(stage BETWEEN 1 AND 7 OR stage IS NULL),
            step INTEGER,
            started_at TIMESTAMP,
            total_minutes INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
        )
    """)
    
    # ============================================
    # 表10: review_schedule（复习计划）
    # 对应 review-schedule.json → schedules
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knowledge_id TEXT UNIQUE NOT NULL,
            current_round INTEGER DEFAULT 0 CHECK(current_round BETWEEN 0 AND 5),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
        )
    """)
    
    # ============================================
    # 表11: review_round（复习轮次）
    # 对应 review-schedule.json → schedules[].rounds
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_round (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER NOT NULL,
            round INTEGER NOT NULL CHECK(round BETWEEN 1 AND 5),
            target_day INTEGER NOT NULL,
            scheduled_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'completed')),
            completed_at TIMESTAMP,
            score INTEGER,
            questions_count INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (schedule_id) REFERENCES review_schedule(id),
            UNIQUE(schedule_id, round)
        )
    """)
    
    # ============================================
    # 表12: mastery_review（精通复习计划）
    # 对应 review-schedule.json → schedules[].mastery_review
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mastery_review (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            schedule_id INTEGER UNIQUE NOT NULL,
            enabled INTEGER DEFAULT 0,
            last_review TIMESTAMP,
            next_review TIMESTAMP,
            history TEXT,  -- JSON array stored as TEXT
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (schedule_id) REFERENCES review_schedule(id)
        )
    """)
    
    # ============================================
    # 表13: review_history（复习历史）
    # 对应 review-history.json → history
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            knowledge_id TEXT NOT NULL,
            round INTEGER NOT NULL CHECK(round BETWEEN 1 AND 5),
            review_date TIMESTAMP NOT NULL,
            duration_minutes INTEGER,
            questions_count INTEGER,
            correct_count INTEGER,
            score INTEGER CHECK(score BETWEEN 0 AND 100),
            user_feedback TEXT,
            wrong_questions TEXT,  -- JSON array stored as TEXT
            verification TEXT,  -- JSON object stored as TEXT, optional
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
        )
    """)
    
    # ============================================
    # 表14: integration_scenario（能力整合练习记录）
    # 对应 integration-scenarios.json → history
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS integration_scenario (
            id TEXT PRIMARY KEY,
            scenario TEXT NOT NULL,
            mode TEXT NOT NULL CHECK(mode IN ('known', 'explore')),
            knowledge_used TEXT,  -- JSON array stored as TEXT
            knowledge_unlearned TEXT,  -- JSON array stored as TEXT
            knowledge_unlearned_explanations TEXT,  -- JSON object stored as TEXT
            difficulty TEXT CHECK(difficulty IN ('senior', 'architect')),
            created_at TIMESTAMP NOT NULL,
            user_solution_summary TEXT,
            ai_feedback TEXT,  -- JSON object stored as TEXT
            unlearned_interest TEXT,  -- JSON array stored as TEXT
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ============================================
    # 表15: meta（版本控制）
    # 存储各 JSON 文件的 version 和 last_updated
    # ============================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            file_key TEXT PRIMARY KEY,
            version TEXT,
            last_updated TIMESTAMP,
            last_check TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 初始化 meta 表
    cursor.execute("""
        INSERT OR IGNORE INTO meta (file_key, version, last_updated)
        VALUES 
            ('progress', '2.0', NULL),
            ('knowledge_list', '1.0', NULL),
            ('review_schedule', '1.0', NULL),
            ('review_history', '1.0', NULL),
            ('integration_scenarios', '1.0', NULL)
    """)
    
    # 初始化 active_session 表（默认一行）
    cursor.execute("""
        INSERT OR IGNORE INTO active_session (id) VALUES (1)
    """)
    
    conn.commit()
    conn.close()
    print(f"[OK] 数据库初始化完成: {DB_PATH}")


def get_version():
    """获取数据库版本信息"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_key, version FROM meta")
    rows = cursor.fetchall()
    conn.close()
    return {row["file_key"]: row["version"] for row in rows}


if __name__ == "__main__":
    init_database()
    print("\n[OK] 版本信息:")
    for key, ver in get_version().items():
        print(f"  {key}: {ver}")