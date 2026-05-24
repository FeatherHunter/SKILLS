# 学习系统脚本重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate code duplication across 5 API files, add WAL + busy_timeout for concurrent safety, fix connection leak and null-pointer bugs, unify error handling.

**Architecture:** Extract shared DB utilities into a new `db_utils.py` module. Each API file imports from `db_utils` instead of defining its own `_find_db_path` / `get_connection`. All DB operations use `with get_db() as conn:` context manager for automatic commit/rollback/close.

**Tech Stack:** Python 3, sqlite3, contextlib

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `scripts/db_utils.py` | **Create** | Shared DB path, connection, WAL, busy_timeout, context manager |
| `scripts/db_init.py` | **Modify** | Remove duplicate code, use `db_utils` |
| `scripts/knowledge_api.py` | **Modify** | Remove duplicate code, use `db_utils`, add exception handling |
| `scripts/progress_api.py` | **Modify** | Remove duplicate code, use `db_utils`, fix multiple commit bug |
| `scripts/review_api.py` | **Modify** | Remove duplicate code, use `db_utils`, fix null-pointer bug |
| `scripts/integration_api.py` | **Modify** | Remove duplicate code, use `db_utils`, add exception handling |
| `scripts/learning.py` | **Modify** | Add parameter validation, exception handling, help text |

---

### Task 1: Create `db_utils.py`

**Files:**
- Create: `scripts/db_utils.py`

- [ ] **Step 1: Create the shared database utilities module**

```python
# scripts/db_utils.py
"""
Learning System - 共享数据库工具
统一连接管理 + WAL 模式 + busy_timeout
所有 API 模块从此处导入，不再各自实现路径查找和连接管理
"""
import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

# ============================================
# 数据库路径查找
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


def get_connection():
    """获取数据库连接（带 WAL 和 busy_timeout）"""
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row

    # 启用 WAL 模式（并发安全）
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")  # 5秒等待
    conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全

    return conn


@contextmanager
def get_db():
    """上下文管理器，自动处理 commit/rollback/close"""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

- [ ] **Step 2: Verify the module loads correctly**

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python -c "from db_utils import DB_PATH, get_connection, get_db; print(f'DB_PATH: {DB_PATH}'); conn = get_connection(); print(f'WAL: {conn.execute(\"PRAGMA journal_mode\").fetchone()[0]}'); conn.close()"`
Expected: `DB_PATH: D:\2Study\StudyNotes\.db\learning-system.db` and `WAL: wal`

- [ ] **Step 3: Commit**

```bash
git add scripts/db_utils.py
git commit -m "feat: add db_utils.py with unified connection management, WAL, busy_timeout"
```

---

### Task 2: Refactor `db_init.py`

**Files:**
- Modify: `scripts/db_init.py`

- [ ] **Step 1: Replace imports and remove duplicate code at the top of `db_init.py`**

Replace lines 1-57 (the entire header block through `get_connection()`) with:

```python
"""
Learning System 数据库初始化脚本
对照 ls-data-structure.md 设计，所有表结构严格匹配 JSON 结构
"""
from db_utils import DB_PATH, get_connection, get_db
```

- [ ] **Step 2: Refactor `init_database()` to use context manager**

Replace the `init_database` function (lines 60-340) with:

```python
def init_database():
    """创建所有表，严格对照 ls-data-structure.md"""

    with get_db() as conn:
        cursor = conn.cursor()

        # ============================================
        # 表1: knowledge_list（知识点元数据）
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_list (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                language TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                framework TEXT,
                tags TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ============================================
        # 表2: knowledge_progress（学习进度）
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
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stage_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_id TEXT NOT NULL,
                stage_name TEXT NOT NULL CHECK(stage_name IN ('stage_1', 'stage_2', 'stage_3', 'stage_4')),
                status TEXT NOT NULL CHECK(status IN ('not_started', 'in_progress', 'completed')),
                completed_at TIMESTAMP,
                essence_keywords TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id),
                UNIQUE(knowledge_id, stage_name)
            )
        """)

        # ============================================
        # 表5: mastery_path（精通流程进度）
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
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interview_assets (
                knowledge_id TEXT PRIMARY KEY,
                star_case_path TEXT,
                failure_case_path TEXT,
                adr_path TEXT,
                validated_questions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
            )
        """)

        # ============================================
        # 表9: active_session（当前学习会话）
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
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mastery_review (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER UNIQUE NOT NULL,
                enabled INTEGER DEFAULT 0,
                last_review TIMESTAMP,
                next_review TIMESTAMP,
                history TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (schedule_id) REFERENCES review_schedule(id)
            )
        """)

        # ============================================
        # 表13: review_history（复习历史）
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
                wrong_questions TEXT,
                verification TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (knowledge_id) REFERENCES knowledge_list(id)
            )
        """)

        # ============================================
        # 表14: integration_scenario（能力整合练习记录）
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS integration_scenario (
                id TEXT PRIMARY KEY,
                scenario TEXT NOT NULL,
                mode TEXT NOT NULL CHECK(mode IN ('known', 'explore')),
                knowledge_used TEXT,
                knowledge_unlearned TEXT,
                knowledge_unlearned_explanations TEXT,
                difficulty TEXT CHECK(difficulty IN ('senior', 'architect')),
                created_at TIMESTAMP NOT NULL,
                user_solution_summary TEXT,
                ai_feedback TEXT,
                unlearned_interest TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ============================================
        # 表15: meta（版本控制）
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

    print(f"[OK] 数据库初始化完成: {DB_PATH}")
```

- [ ] **Step 3: Refactor `get_version()` to use context manager**

Replace the `get_version` function (lines 343-350) with:

```python
def get_version():
    """获取数据库版本信息"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_key, version FROM meta")
        rows = cursor.fetchall()
    return {row["file_key"]: row["version"] for row in rows}
```

- [ ] **Step 4: Verify `db_init.py` works**

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python -c "import db_init; db_init.init_database(); print(db_init.get_version())"`
Expected: `[OK] 数据库初始化完成:` followed by version dict

- [ ] **Step 5: Commit**

```bash
git add scripts/db_init.py
git commit -m "refactor: db_init.py uses db_utils, context manager, single commit"
```

---

### Task 3: Refactor `knowledge_api.py`

**Files:**
- Modify: `scripts/knowledge_api.py`

- [ ] **Step 1: Replace the header block (lines 1-66)**

Replace with:

```python
"""
Learning System - 知识点元数据 API
对照 ls-data-structure.md 中 knowledge-list.json 设计
严格校验字段，不允许多余字段
"""
import json
import sqlite3
from db_utils import get_db

# 允许的字段（严格对照 knowledge-list.json）
ALLOWED_FIELDS = {
    "id", "title", "language", "category", "subcategory",
    "framework", "tags", "metadata"
}
REQUIRED_FIELDS = {"id", "title", "language", "category"}
VALID_LANGUAGES = {"kotlin", "java", "python", "rust", "javascript", "typescript", "go", "cpp", "c", "swift", "other"}
VALID_CATEGORIES = {"编程语言", "框架", "理论", "工具", "其他"}
```

- [ ] **Step 2: Refactor `add_knowledge()`**

Replace the `add_knowledge` function (lines 118-161) with:

```python
def add_knowledge(data: dict) -> dict:
    """添加知识点"""
    errors = validate_fields(data, ALLOWED_FIELDS)
    if errors:
        return {"success": False, "errors": errors}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            tags = json.dumps(data["tags"]) if data.get("tags") else "[]"
            metadata = json.dumps(data["metadata"]) if data.get("metadata") else "{}"

            cursor.execute("""
                INSERT INTO knowledge_list (id, title, language, category, subcategory, framework, tags, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"], data["title"], data["language"], data["category"],
                data.get("subcategory"), data.get("framework"), tags, metadata
            ))

            cursor.execute("UPDATE meta SET last_updated = CURRENT_TIMESTAMP WHERE file_key = 'knowledge_list'")

        return {"success": True, "knowledge_id": data["id"]}

    except sqlite3.IntegrityError:
        return {"success": False, "errors": [f"[数据库错误] 知识点 ID 已存在: {data['id']}"]}
    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] add_knowledge: {str(e)}"]}
```

- [ ] **Step 3: Refactor `get_knowledge()`**

Replace the `get_knowledge` function (lines 164-182) with:

```python
def get_knowledge(knowledge_id: str) -> dict:
    """获取知识点详情"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM knowledge_list WHERE id = ?", (knowledge_id,))
            row = cursor.fetchone()

        if not row:
            return {"success": False, "errors": [f"[查询失败] 知识点不存在: {knowledge_id}"]}

        result = dict(row)
        if result["tags"]:
            result["tags"] = json.loads(result["tags"])
        if result["metadata"]:
            result["metadata"] = json.loads(result["metadata"])

        return {"success": True, "data": result}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_knowledge: {str(e)}"]}
```

- [ ] **Step 4: Refactor `list_knowledge()`**

Replace the `list_knowledge` function (lines 185-220) with:

```python
def list_knowledge(filters: dict = None) -> dict:
    """列出知识点，支持过滤"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM knowledge_list WHERE 1=1"
            params = []

            if filters:
                if "category" in filters:
                    query += " AND category = ?"
                    params.append(filters["category"])
                if "language" in filters:
                    query += " AND language = ?"
                    params.append(filters["language"])
                if "framework" in filters:
                    query += " AND framework = ?"
                    params.append(filters["framework"])

            cursor.execute(query, params)
            rows = cursor.fetchall()

        result = []
        for row in rows:
            item = dict(row)
            if item["tags"]:
                item["tags"] = json.loads(item["tags"])
            if item["metadata"]:
                item["metadata"] = json.loads(item["metadata"])
            result.append(item)

        return {"success": True, "data": result, "count": len(result)}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] list_knowledge: {str(e)}"]}
```

- [ ] **Step 5: Refactor `update_knowledge()`**

Replace the `update_knowledge` function (lines 223-270) with:

```python
def update_knowledge(knowledge_id: str, data: dict) -> dict:
    """更新知识点（仅允许的字段）"""
    extra_fields = set(data.keys()) - ALLOWED_FIELDS
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] 不允许的字段: {extra_fields}"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM knowledge_list WHERE id = ?", (knowledge_id,))
            if not cursor.fetchone():
                return {"success": False, "errors": [f"[更新失败] 知识点不存在: {knowledge_id}"]}

            set_clauses = []
            values = []

            for field in data:
                if field == "tags":
                    set_clauses.append("tags = ?")
                    values.append(json.dumps(data[field]) if isinstance(data[field], list) else data[field])
                elif field == "metadata":
                    set_clauses.append("metadata = ?")
                    values.append(json.dumps(data[field]) if isinstance(data[field], dict) else data[field])
                else:
                    set_clauses.append(f"{field} = ?")
                    values.append(data[field])

            if not set_clauses:
                return {"success": False, "errors": ["[校验失败] 没有提供要更新的字段"]}

            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(knowledge_id)

            query = f"UPDATE knowledge_list SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(query, values)

            cursor.execute("UPDATE meta SET last_updated = CURRENT_TIMESTAMP WHERE file_key = 'knowledge_list'")

        return {"success": True, "knowledge_id": knowledge_id}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] update_knowledge: {str(e)}"]}
```

- [ ] **Step 6: Refactor `delete_knowledge()`**

Replace the `delete_knowledge` function (lines 273-299) with:

```python
def delete_knowledge(knowledge_id: str) -> dict:
    """删除知识点（级联删除关联数据）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM knowledge_list WHERE id = ?", (knowledge_id,))
            if not cursor.fetchone():
                return {"success": False, "errors": [f"[删除失败] 知识点不存在: {knowledge_id}"]}

            # 级联删除（按依赖顺序）
            cursor.execute("DELETE FROM review_round WHERE schedule_id IN (SELECT id FROM review_schedule WHERE knowledge_id = ?)", (knowledge_id,))
            cursor.execute("DELETE FROM mastery_review WHERE schedule_id IN (SELECT id FROM review_schedule WHERE knowledge_id = ?)", (knowledge_id,))
            cursor.execute("DELETE FROM review_schedule WHERE knowledge_id = ?", (knowledge_id,))
            cursor.execute("DELETE FROM review_history WHERE knowledge_id = ?", (knowledge_id,))
            cursor.execute("DELETE FROM mastery_stage_progress WHERE knowledge_id = ?", (knowledge_id,))
            cursor.execute("DELETE FROM mastery_path WHERE knowledge_id = ?", (knowledge_id,))
            cursor.execute("DELETE FROM stage_progress WHERE knowledge_id = ?", (knowledge_id,))
            cursor.execute("DELETE FROM foundation_path WHERE knowledge_id = ?", (knowledge_id,))
            cursor.execute("DELETE FROM interview_assets WHERE knowledge_id = ?", (knowledge_id,))
            cursor.execute("DELETE FROM knowledge_progress WHERE knowledge_id = ?", (knowledge_id,))
            cursor.execute("DELETE FROM knowledge_list WHERE id = ?", (knowledge_id,))

        return {"success": True, "knowledge_id": knowledge_id}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] delete_knowledge: {str(e)}"]}
```

- [ ] **Step 7: Verify `knowledge_api.py` works**

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python -c "import knowledge_api; print(json.dumps(knowledge_api.list_knowledge(), ensure_ascii=False, indent=2))"`
Expected: JSON output with `success: true` and knowledge list

- [ ] **Step 8: Commit**

```bash
git add scripts/knowledge_api.py
git commit -m "refactor: knowledge_api.py uses db_utils, context manager, exception handling"
```

---

### Task 4: Refactor `progress_api.py`

**Files:**
- Modify: `scripts/progress_api.py`

- [ ] **Step 1: Replace the header block (lines 1-77)**

Replace with:

```python
"""
Learning System - 学习进度 API
对照 ls-data-structure.md 中 progress.json 设计
严格校验字段和业务规则，不允许多余字段
"""
import sqlite3
import json
from datetime import datetime, timedelta
from db_utils import get_db

# 允许的字段
PROGRESS_ALLOWED_FIELDS = {"target_level", "last_activity", "total_learning_minutes"}
FOUNDATION_ALLOWED_FIELDS = {"status", "current_stage", "completed_at", "total_learning_minutes"}
MASTERY_ALLOWED_FIELDS = {"status", "current_stage", "started_at", "completed_at", "total_learning_minutes", "mastery_level"}
STAGE_ALLOWED_FIELDS = {"status", "completed_at", "essence_keywords"}

VALID_STATUS = {"not_started", "in_progress", "completed"}
VALID_PATH_TYPE = {"foundation", "mastery", "unknown"}
```

- [ ] **Step 2: Refactor `_ensure_mastery_level_column()`**

Replace with:

```python
def _ensure_mastery_level_column():
    """确保 mastery_path 表有 mastery_level 字段（idempotent）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(mastery_path)")
        columns = [row[1] for row in cursor.fetchall()]
        if "mastery_level" not in columns:
            cursor.execute("ALTER TABLE mastery_path ADD COLUMN mastery_level INTEGER DEFAULT 1 CHECK(mastery_level BETWEEN 1 AND 3)")
            print(f"[OK] mastery_path 表已新增 mastery_level 字段，默认值 1")
```

- [ ] **Step 3: Refactor `calculate_level()`**

Replace with:

```python
def calculate_level(knowledge_id: str) -> int:
    """根据 stage_progress 表的真实状态计算当前 level"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT stage_name, status FROM stage_progress
            WHERE knowledge_id = ? AND stage_name IN ('stage_1','stage_2','stage_3','stage_4')
            ORDER BY stage_name
        """, (knowledge_id,))
        stage_rows = cursor.fetchall()

        cursor.execute("SELECT status, current_stage FROM mastery_path WHERE knowledge_id = ?", (knowledge_id,))
        mp_row = cursor.fetchone()

    if not stage_rows:
        return 0

    max_completed = 0
    for row in stage_rows:
        if row["status"] == "completed":
            stage_num = int(row["stage_name"].split("_")[1])
            if stage_num > max_completed:
                max_completed = stage_num

    if max_completed == 0:
        return 0

    if max_completed < 4:
        return max_completed

    mp_status = mp_row["status"] if mp_row else "not_started"

    if mp_status == "completed":
        return 7
    elif mp_status == "in_progress" and mp_row:
        stage = mp_row["current_stage"] or 5
        return 4 + (stage - 5)
    else:
        return 4
```

- [ ] **Step 4: Refactor `update_stage_progress()` - fix multiple commit bug**

Replace the `update_stage_progress` function (lines 164-267) with:

```python
def update_stage_progress(knowledge_id: str, stage_name: str, data: dict) -> dict:
    """更新阶段进度（如 stage_1, stage_2, stage_3, stage_4）"""
    extra_fields = set(data.keys()) - STAGE_ALLOWED_FIELDS
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] stage_progress 不允许的字段: {extra_fields}"]}

    if "status" in data and data["status"] not in VALID_STATUS:
        return {"success": False, "errors": [f"[校验失败] status 必须是 {VALID_STATUS} 之一"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT status FROM stage_progress
                WHERE knowledge_id = ? AND stage_name = ?
            """, (knowledge_id, stage_name))
            row = cursor.fetchone()

            current_status = row["status"] if row else "not_started"
            new_status = data.get("status", current_status)

            stage_num = int(stage_name.split("_")[1])
            errors = validate_stage_sequence(stage_num, new_status, current_status)
            if errors:
                return {"success": False, "errors": errors}

            # 完成 stage 时，检查所有前置 stage 是否已完成
            if new_status == "completed":
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
                    incomplete = " -> ".join(prerequisite_errors) if len(prerequisite_errors) <= 3 else " -> ".join(prerequisite_errors[:3]) + " -> ..."
                    return {
                        "success": False,
                        "errors": [
                            f"[业务规则] {stage_name} 不能在前置阶段未完成时完成。必须按顺序完成：stage_1 -> stage_2 -> ... -> {stage_name}。"
                            f"当前未完成的前置阶段：{incomplete}"
                        ]
                    }

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
                cursor.execute("""
                    INSERT INTO stage_progress (knowledge_id, stage_name, status, completed_at, essence_keywords)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    knowledge_id, stage_name, new_status,
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
```

- [ ] **Step 5: Refactor `update_foundation_path()`**

Replace with:

```python
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
```

- [ ] **Step 6: Refactor `update_mastery_path()`**

Replace with:

```python
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
                    level = data[field]
                    if not isinstance(level, int) or not (1 <= level <= 3):
                        return {"success": False, "errors": [f"[校验失败] mastery_level 必须是 1-3 整数，当前: {level}"]}
                    set_clauses.append("mastery_level = ?")
                    values.append(level)

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
```

- [ ] **Step 7: Refactor `update_mastery_stage_progress()`**

Replace with:

```python
def update_mastery_stage_progress(knowledge_id: str, stage_name: str, data: dict) -> dict:
    """更新精通阶段进度（stage_5, stage_6, stage_7）"""
    allowed = {"status", "step", "cases_documented", "completed_at"}
    extra_fields = set(data.keys()) - allowed
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] mastery_stage_progress 不允许的字段: {extra_fields}"]}

    if "status" in data and data["status"] not in VALID_STATUS:
        return {"success": False, "errors": [f"[校验失败] status 必须是 {VALID_STATUS} 之一"]}

    if "step" in data:
        if not isinstance(data["step"], int) or data["step"] < 1:
            return {"success": False, "errors": [f"[校验失败] step 必须是正整数"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT status FROM mastery_stage_progress
                WHERE knowledge_id = ? AND stage_name = ?
            """, (knowledge_id, stage_name))
            row = cursor.fetchone()

            if not row:
                return {"success": False, "errors": [f"[更新失败] mastery_stage_progress 不存在: {knowledge_id}/{stage_name}"]}

            current_status = row["status"]
            new_status = data.get("status", current_status)

            if new_status == "completed" and current_status == "not_started":
                return {"success": False, "errors": [f"[业务规则] {stage_name} 不能直接从 not_started -> completed，必须先 in_progress"]}

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
```

- [ ] **Step 8: Refactor `get_mastery_stage_progress()`**

Replace with:

```python
def get_mastery_stage_progress(knowledge_id: str) -> dict:
    """获取精通阶段进度"""
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
```

- [ ] **Step 9: Refactor `update_mastery_stage()`**

Replace with:

```python
def update_mastery_stage(knowledge_id: str, stage_name: str, data: dict) -> dict:
    """更新精通阶段进度，支持插入新记录或更新已有记录"""
    valid_stages = {"stage_5", "stage_6", "stage_7"}
    if stage_name not in valid_stages:
        return {"success": False, "errors": [f"[校验失败] stage_name 必须是 {valid_stages} 之一，当前: {stage_name}"]}

    allowed = {"status", "step", "cases_documented"}
    extra_fields = set(data.keys()) - allowed
    if extra_fields:
        return {"success": False, "errors": [f"[校验失败] mastery_stage_progress 不允许的字段: {extra_fields}"]}

    if "status" in data and data["status"] not in VALID_STATUS:
        return {"success": False, "errors": [f"[校验失败] status 必须是 {VALID_STATUS} 之一"]}

    if "step" in data:
        if not isinstance(data["step"], int) or data["step"] < 1:
            return {"success": False, "errors": [f"[校验失败] step 必须是正整数"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT status FROM mastery_stage_progress
                WHERE knowledge_id = ? AND stage_name = ?
            """, (knowledge_id, stage_name))
            row = cursor.fetchone()

            if not row:
                cursor.execute("""
                    INSERT INTO mastery_stage_progress (knowledge_id, stage_name, status, step, cases_documented)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    knowledge_id, stage_name,
                    data.get("status", "not_started"),
                    data.get("step", 1),
                    data.get("cases_documented", 0)
                ))
                return {"success": True, "knowledge_id": knowledge_id, "stage_name": stage_name, "action": "inserted"}

            current_status = row["status"]
            new_status = data.get("status", current_status)

            if new_status == "completed" and current_status == "not_started":
                return {"success": False, "errors": [f"[业务规则] {stage_name} 不能直接从 not_started -> completed，必须先 in_progress"]}

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
```

- [ ] **Step 10: Refactor `update_interview_assets()`**

Replace with:

```python
def update_interview_assets(knowledge_id: str, field: str, value: str) -> dict:
    """更新面试素材路径"""
    allowed_fields = {"star_case_path", "failure_case_path", "adr_path"}
    if field not in allowed_fields:
        return {"success": False, "errors": [f"[校验失败] interview_assets 不允许的字段: {field}，必须是 {allowed_fields}"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

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
```

- [ ] **Step 11: Refactor `update_knowledge_progress()`**

Replace with:

```python
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
```

- [ ] **Step 12: Refactor `init_knowledge_progress()`**

Replace with:

```python
def init_knowledge_progress(knowledge_id: str) -> dict:
    """为新知识点初始化所有进度记录（level=0 待学状态）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT knowledge_id FROM knowledge_progress WHERE knowledge_id = ?", (knowledge_id,))
            if cursor.fetchone():
                return {"success": False, "errors": [f"[初始化失败] 知识点进度已存在: {knowledge_id}"]}

            now = datetime.now().isoformat() + "+08:00"

            cursor.execute("""
                INSERT INTO knowledge_progress (knowledge_id, target_level, last_activity)
                VALUES (?, 7, ?)
            """, (knowledge_id, now))

            cursor.execute("""
                INSERT INTO foundation_path (knowledge_id, status, current_stage)
                VALUES (?, 'not_started', 1)
            """, (knowledge_id,))

            for stage in range(1, 5):
                cursor.execute("""
                    INSERT INTO stage_progress (knowledge_id, stage_name, status)
                    VALUES (?, ?, 'not_started')
                """, (knowledge_id, f"stage_{stage}"))

            cursor.execute("""
                INSERT INTO mastery_path (knowledge_id, status)
                VALUES (?, 'not_started')
            """, (knowledge_id,))

            for stage in range(5, 8):
                cursor.execute("""
                    INSERT INTO mastery_stage_progress (knowledge_id, stage_name, status)
                    VALUES (?, ?, 'not_started')
                """, (knowledge_id, f"stage_{stage}"))

            cursor.execute("""
                INSERT INTO interview_assets (knowledge_id)
                VALUES (?)
            """, (knowledge_id,))

            cursor.execute("""
                INSERT INTO review_schedule (knowledge_id, current_round)
                VALUES (?, 0)
            """, (knowledge_id,))
            schedule_id = cursor.lastrowid

            target_days = [1, 3, 7, 14, 30]
            for round_num, target_day in enumerate(target_days, 1):
                scheduled = (datetime.now() + timedelta(days=target_day)).strftime("%Y-%m-%d")
                cursor.execute("""
                    INSERT INTO review_round (schedule_id, round, target_day, scheduled_date, status)
                    VALUES (?, ?, ?, ?, 'pending')
                """, (schedule_id, round_num, target_day, scheduled))

            cursor.execute("""
                INSERT INTO mastery_review (schedule_id, enabled)
                VALUES (?, 0)
            """, (schedule_id,))

        return {"success": True, "knowledge_id": knowledge_id}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] init_knowledge_progress: {str(e)}"]}
```

- [ ] **Step 13: Refactor `get_full_progress()`**

Replace with:

```python
def get_full_progress(knowledge_id: str) -> dict:
    """获取完整进度（包含所有关联表数据）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM knowledge_progress WHERE knowledge_id = ?", (knowledge_id,))
            kp_row = cursor.fetchone()
            if not kp_row:
                return {"success": False, "errors": [f"[查询失败] 知识点进度不存在: {knowledge_id}"]}
            kp = dict(kp_row)

            cursor.execute("SELECT * FROM foundation_path WHERE knowledge_id = ?", (knowledge_id,))
            fp_row = cursor.fetchone()
            fp = dict(fp_row) if fp_row else None

            cursor.execute("SELECT * FROM stage_progress WHERE knowledge_id = ? ORDER BY stage_name", (knowledge_id,))
            stages = [dict(row) for row in cursor.fetchall()]
            for s in stages:
                if s["essence_keywords"]:
                    s["essence_keywords"] = json.loads(s["essence_keywords"])

            cursor.execute("SELECT * FROM mastery_path WHERE knowledge_id = ?", (knowledge_id,))
            mp_row = cursor.fetchone()
            mp = dict(mp_row) if mp_row else None

            cursor.execute("SELECT * FROM mastery_stage_progress WHERE knowledge_id = ? ORDER BY stage_name", (knowledge_id,))
            mastery_stages = [dict(row) for row in cursor.fetchall()]

            cursor.execute("SELECT * FROM interview_assets WHERE knowledge_id = ?", (knowledge_id,))
            ia_row = cursor.fetchone()
            ia = dict(ia_row) if ia_row else None
            if ia and ia["validated_questions"]:
                ia["validated_questions"] = json.loads(ia["validated_questions"])

        calculated_level = calculate_level(knowledge_id)

        result = {
            "knowledge_id": knowledge_id,
            "current_level": calculated_level,
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
```

- [ ] **Step 14: Refactor `update_active_session()`**

Replace with:

```python
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
```

- [ ] **Step 15: Refactor `get_active_session()`**

Replace with:

```python
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
```

- [ ] **Step 16: Verify `progress_api.py` works**

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python -c "import progress_api; print(json.dumps(progress_api.get_active_session(), ensure_ascii=False, indent=2))"`
Expected: JSON output with `success: true` and session data

- [ ] **Step 17: Commit**

```bash
git add scripts/progress_api.py
git commit -m "refactor: progress_api.py uses db_utils, context manager, fix multi-commit bug, exception handling"
```

---

### Task 5: Refactor `review_api.py`

**Files:**
- Modify: `scripts/review_api.py`

- [ ] **Step 1: Replace the header block (lines 1-65)**

Replace with:

```python
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
```

- [ ] **Step 2: Refactor `create_review_schedule()`**

Replace with:

```python
def create_review_schedule(knowledge_id: str, foundation_completed_at: str = None) -> dict:
    """创建复习计划（基础流程完成时自动调用）"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM review_schedule WHERE knowledge_id = ?", (knowledge_id,))
            if cursor.fetchone():
                return {"success": False, "errors": [f"[创建失败] 复习计划已存在: {knowledge_id}"]}

            cursor.execute("SELECT id FROM knowledge_list WHERE id = ?", (knowledge_id,))
            if not cursor.fetchone():
                return {"success": False, "errors": [f"[创建失败] 知识点不存在: {knowledge_id}"]}

            base_date = foundation_completed_at if foundation_completed_at else datetime.now().strftime("%Y-%m-%d")

            cursor.execute("""
                INSERT INTO review_schedule (knowledge_id, current_round)
                VALUES (?, 0)
            """, (knowledge_id,))
            schedule_id = cursor.lastrowid

            target_days = [1, 3, 7, 14, 30]
            for round_num, target_day in enumerate(target_days, 1):
                scheduled = (datetime.strptime(base_date, "%Y-%m-%d") + timedelta(days=target_day)).strftime("%Y-%m-%d")
                cursor.execute("""
                    INSERT INTO review_round (schedule_id, round, target_day, scheduled_date, status)
                    VALUES (?, ?, ?, ?, 'pending')
                """, (schedule_id, round_num, target_day, scheduled))

            cursor.execute("""
                INSERT INTO mastery_review (schedule_id, enabled)
                VALUES (?, 0)
            """, (schedule_id,))

        return {"success": True, "knowledge_id": knowledge_id, "schedule_id": schedule_id}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] create_review_schedule: {str(e)}"]}
```

- [ ] **Step 3: Refactor `get_review_schedule()` - fix null-pointer bug**

Replace with:

```python
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

            cursor.execute("""
                SELECT * FROM review_round
                WHERE schedule_id = ?
                ORDER BY round
            """, (schedule_id,))
            rounds = [dict(r) for r in cursor.fetchall()]
            schedule["rounds"] = rounds

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
```

- [ ] **Step 4: Refactor `get_due_reviews()`**

Replace with:

```python
def get_due_reviews(date: str = None) -> dict:
    """获取今日到期的复习列表"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    try:
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
```

- [ ] **Step 5: Refactor `complete_round()`**

Replace with:

```python
def complete_round(knowledge_id: str, round_num: int, score: int,
                   questions_count: int = None, correct_count: int = None,
                   duration_minutes: int = None, user_feedback: str = None,
                   wrong_questions: list = None) -> dict:
    """完成一轮复习"""
    if not (1 <= round_num <= 5):
        return {"success": False, "errors": [f"[校验失败] round 必须是 1-5，当前: {round_num}"]}

    if not (0 <= score <= 100):
        return {"success": False, "errors": [f"[校验失败] score 必须是 0-100，当前: {score}"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM review_schedule WHERE knowledge_id = ?", (knowledge_id,))
            row = cursor.fetchone()
            if not row:
                return {"success": False, "errors": [f"[更新失败] 复习计划不存在: {knowledge_id}"]}
            schedule_id = row["id"]

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

            cursor.execute("""
                UPDATE review_round
                SET status = 'completed', completed_at = ?, score = ?, questions_count = ?
                WHERE schedule_id = ? AND round = ?
            """, (now, score, questions_count, schedule_id, round_num))

            cursor.execute("""
                UPDATE review_schedule
                SET current_round = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (round_num, schedule_id))

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
```

- [ ] **Step 6: Refactor `add_verification()`**

Replace with:

```python
def add_verification(knowledge_id: str, round_num: int,
                     user_choice: str, results: list,
                     passed_count: int, failed_count: int) -> dict:
    """添加即时验证记录"""
    if user_choice not in VALID_USER_CHOICE:
        return {"success": False, "errors": [f"[校验失败] user_choice 必须是 {VALID_USER_CHOICE} 之一"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

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
```

- [ ] **Step 7: Refactor `add_review_history()`**

Replace with:

```python
def add_review_history(knowledge_id: str, round_num: int, review_date: str,
                          duration_minutes: int = None, questions_count: int = None,
                          correct_count: int = None, score: int = None,
                          user_feedback: str = None, wrong_questions: list = None) -> dict:
    """添加复习历史记录"""
    if round_num not in [1, 2, 3, 4, 5]:
        return {"success": False, "errors": ["[校验失败] round 必须是 1-5"]}

    if score is not None and (score < 0 or score > 100):
        return {"success": False, "errors": ["[校验失败] score 必须在 0-100 之间"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM knowledge_list WHERE id = ?", (knowledge_id,))
            if not cursor.fetchone():
                return {"success": False, "errors": [f"[校验失败] 知识点不存在: {knowledge_id}"]}

            cursor.execute("""
                INSERT INTO review_history
                (knowledge_id, round, review_date, duration_minutes, questions_count,
                 correct_count, score, user_feedback, wrong_questions)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                knowledge_id, round_num, review_date, duration_minutes,
                questions_count, correct_count, score, user_feedback,
                json.dumps(wrong_questions, ensure_ascii=False) if wrong_questions else None
            ))

            history_id = cursor.lastrowid

        return {"success": True, "id": history_id, "knowledge_id": knowledge_id, "round": round_num}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] add_review_history: {str(e)}"]}
```

- [ ] **Step 8: Refactor `get_review_history()`**

Replace with:

```python
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
```

- [ ] **Step 9: Refactor `get_weak_topics()`**

Replace with:

```python
def get_weak_topics(knowledge_id: str) -> dict:
    """获取薄弱点"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

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
```

- [ ] **Step 10: Refactor `enable_mastery_review()`**

Replace with:

```python
def enable_mastery_review(knowledge_id: str) -> dict:
    """启用精通复习"""
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
```

- [ ] **Step 11: Refactor `record_mastery_review()`**

Replace with:

```python
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

            record = {
                "date": datetime.now().isoformat() + "+08:00",
                "score": score
            }
            history.append(record)

            next_review = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

            cursor.execute("""
                UPDATE mastery_review
                SET history = ?, last_review = ?, next_review = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (json.dumps(history, ensure_ascii=False), record["date"], next_review, mr_id))

        return {"success": True, "next_review": next_review}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] record_mastery_review: {str(e)}"]}
```

- [ ] **Step 12: Refactor `get_mastery_review_status()`**

Replace with:

```python
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
```

- [ ] **Step 13: Verify `review_api.py` works**

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python -c "import review_api; print(json.dumps(review_api.get_due_reviews(), ensure_ascii=False, indent=2))"`
Expected: JSON output with `success: true`

- [ ] **Step 14: Commit**

```bash
git add scripts/review_api.py
git commit -m "refactor: review_api.py uses db_utils, context manager, fix null-pointer bug, exception handling"
```

---

### Task 6: Refactor `integration_api.py`

**Files:**
- Modify: `scripts/integration_api.py`

- [ ] **Step 1: Replace the header block (lines 1-65)**

Replace with:

```python
"""
Learning System - 能力整合 API
对照 ls-data-structure.md 中 integration-scenarios.json 设计
严格校验字段和业务规则
"""
import json
from datetime import datetime
from db_utils import get_db

ALLOWED_SCENARIO_FIELDS = {
    "id", "scenario", "mode", "knowledge_used", "knowledge_unlearned",
    "knowledge_unlearned_explanations", "difficulty", "created_at",
    "user_solution_summary", "ai_feedback", "unlearned_interest"
}
VALID_MODES = {"known", "explore"}
VALID_DIFFICULTIES = {"senior", "architect"}
```

- [ ] **Step 2: Refactor `generate_id()`**

Replace with:

```python
def generate_id() -> str:
    """生成场景 ID：int-XXX 格式"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM integration_scenario
            ORDER BY id DESC LIMIT 1
        """)
        row = cursor.fetchone()

    if row:
        last_num = int(row["id"].split("-")[1])
        return f"int-{last_num + 1:03d}"
    else:
        return "int-001"
```

- [ ] **Step 3: Refactor `create_scenario()`**

Replace with:

```python
def create_scenario(data: dict) -> dict:
    """创建能力整合练习场景"""
    errors = validate_fields(data)
    if errors:
        return {"success": False, "errors": errors}

    if data["mode"] == "explore" and not data.get("knowledge_unlearned"):
        return {"success": False, "errors": ["[校验失败] mode=explore 时 knowledge_unlearned 不能为空"]}

    scenario_id = generate_id()
    now = datetime.now().isoformat() + "+08:00"

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO integration_scenario
                (id, scenario, mode, knowledge_used, knowledge_unlearned,
                 knowledge_unlearned_explanations, difficulty, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                scenario_id, data["scenario"], data["mode"],
                json.dumps(data["knowledge_used"]) if data.get("knowledge_used") else None,
                json.dumps(data["knowledge_unlearned"]) if data.get("knowledge_unlearned") else None,
                json.dumps(data["knowledge_unlearned_explanations"]) if data.get("knowledge_unlearned_explanations") else None,
                data.get("difficulty"), now
            ))

        return {"success": True, "id": scenario_id}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] create_scenario: {str(e)}"]}
```

- [ ] **Step 4: Refactor `update_solution()`**

Replace with:

```python
def update_solution(scenario_id: str, user_solution_summary: str,
                    ai_feedback: dict, unlearned_interest: list = None) -> dict:
    """更新场景的答题结果"""
    if not isinstance(ai_feedback, dict):
        return {"success": False, "errors": ["[校验失败] ai_feedback 必须是 JSON object"]}

    score = ai_feedback.get("score")
    if score is not None and not (0 <= score <= 100):
        return {"success": False, "errors": [f"[校验失败] score 必须是 0-100，当前: {score}"]}

    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM integration_scenario WHERE id = ?", (scenario_id,))
            if not cursor.fetchone():
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

        return {"success": True, "id": scenario_id, "score": score}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] update_solution: {str(e)}"]}
```

- [ ] **Step 5: Refactor `get_scenario()`**

Replace with:

```python
def get_scenario(scenario_id: str) -> dict:
    """获取场景详情"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM integration_scenario WHERE id = ?", (scenario_id,))
            row = cursor.fetchone()

        if not row:
            return {"success": False, "errors": [f"[查询失败] 场景不存在: {scenario_id}"]}

        result = dict(row)
        for field in ["knowledge_used", "knowledge_unlearned", "knowledge_unlearned_explanations", "ai_feedback", "unlearned_interest"]:
            if result.get(field):
                result[field] = json.loads(result[field])

        return {"success": True, "data": result}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_scenario: {str(e)}"]}
```

- [ ] **Step 6: Refactor `list_scenarios()`**

Replace with:

```python
def list_scenarios(mode: str = None, difficulty: str = None, limit: int = 50) -> dict:
    """列出场景"""
    try:
        with get_db() as conn:
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

        results = []
        for row in rows:
            item = dict(row)
            for field in ["knowledge_used", "knowledge_unlearned", "knowledge_unlearned_explanations", "ai_feedback", "unlearned_interest"]:
                if item.get(field):
                    item[field] = json.loads(item[field])
            results.append(item)

        return {"success": True, "data": results, "count": len(results)}

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] list_scenarios: {str(e)}"]}
```

- [ ] **Step 7: Refactor `get_recent_practiced_knowledge()`**

Replace with:

```python
def get_recent_practiced_knowledge(limit: int = 10) -> list:
    """获取最近练习过的知识点"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT knowledge_used FROM integration_scenario
                WHERE user_solution_summary IS NOT NULL
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()

        all_ids = set()
        for row in rows:
            if row["knowledge_used"]:
                ids = json.loads(row["knowledge_used"])
                all_ids.update(ids)

        return list(all_ids)

    except Exception as e:
        return []
```

- [ ] **Step 8: Refactor `get_scenario_stats()`**

Replace with:

```python
def get_scenario_stats() -> dict:
    """获取场景统计"""
    try:
        with get_db() as conn:
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

    except Exception as e:
        return {"success": False, "errors": [f"[系统错误] get_scenario_stats: {str(e)}"]}
```

- [ ] **Step 9: Verify `integration_api.py` works**

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python -c "import integration_api; print(json.dumps(integration_api.get_scenario_stats(), ensure_ascii=False, indent=2))"`
Expected: JSON output with `success: true`

- [ ] **Step 10: Commit**

```bash
git add scripts/integration_api.py
git commit -m "refactor: integration_api.py uses db_utils, context manager, exception handling"
```

---

### Task 7: Refactor `learning.py`

**Files:**
- Modify: `scripts/learning.py`

- [ ] **Step 1: Replace the entire file**

Write the complete new `learning.py`:

```python
#!/usr/bin/env python3
"""
Learning System CLI 入口
统一路由到各个 API 模块

用法:
    python learning.py <module> <action> [args]

模块:
    knowledge  - 知识点元数据管理
    progress   - 学习进度管理
    review     - 复习计划管理
    integration - 能力整合练习
    init       - 初始化数据库
    status     - 查看系统状态

示例:
    python learning.py knowledge add '{"id":"test","title":"测试","language":"kotlin","category":"编程语言"}'
    python learning.py progress get test
    python learning.py review get_due
    python learning.py init
"""
import sys
import json
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
    if not args:
        print("[错误] knowledge 需要 action 参数")
        print("  add <json_data> | get <id> | list [category] [language] | update <id> <json> | delete <id>")
        sys.exit(1)

    action = args[0]

    try:
        if action == "add":
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
            print(f"[错误] 未知 action: {action}")
            print("  add | get | list | update | delete")
            sys.exit(1)

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except IndexError:
        print(f"[错误] {action} 缺少必要参数")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败: {e}")
        sys.exit(1)


def cmd_progress(args):
    """学习进度操作"""
    if not args:
        print("[错误] progress 需要 action 参数")
        print("  init | get | update | update_foundation | update_mastery | update_stage | update_session | get_session | update_mastery_stage | update_interview_assets")
        sys.exit(1)

    action = args[0]

    try:
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
            print(f"[错误] 未知 action: {action}")
            sys.exit(1)

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except IndexError:
        print(f"[错误] {action} 缺少必要参数")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败: {e}")
        sys.exit(1)


def cmd_review(args):
    """复习操作"""
    if not args:
        print("[错误] review 需要 action 参数")
        print("  create_schedule | get_schedule | get_due | complete_round | add_verification | add_history | get_history | get_weak | enable_mastery | record_mastery | get_mastery_status")
        sys.exit(1)

    action = args[0]

    try:
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
            print(f"[错误] 未知 action: {action}")
            sys.exit(1)

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except IndexError:
        print(f"[错误] {action} 缺少必要参数")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败: {e}")
        sys.exit(1)


def cmd_integration(args):
    """能力整合操作"""
    if not args:
        print("[错误] integration 需要 action 参数")
        print("  create | get | list | update_solution | stats | recent_practiced")
        sys.exit(1)

    action = args[0]

    try:
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
            print(f"[错误] 未知 action: {action}")
            sys.exit(1)

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except IndexError:
        print(f"[错误] {action} 缺少必要参数")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[错误] JSON 解析失败: {e}")
        sys.exit(1)


def cmd_init():
    """初始化数据库"""
    db_init.init_database()
    print("[OK] 数据库初始化完成")


def cmd_status():
    """查看整体状态"""
    from db_utils import DB_PATH, get_db

    version_info = db_init.get_version()

    with get_db() as conn:
        cursor = conn.cursor()

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

        cursor.execute("SELECT * FROM active_session WHERE id = 1")
        session = dict(cursor.fetchone())

    print("=" * 50)
    print("Learning System 状态")
    print("=" * 50)
    print(f"数据库路径: {DB_PATH}")
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
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "--help" or cmd == "-h":
        print(__doc__)
        sys.exit(0)

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
        print(f"[错误] 未知命令: {cmd}")
        print("可用命令: init | status | knowledge | progress | review | integration")
        print("使用 --help 查看详细用法")
        sys.exit(1)
```

- [ ] **Step 2: Verify `learning.py` works**

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python learning.py --help`
Expected: Full usage documentation printed

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python learning.py status`
Expected: System status output with DB path and record counts

- [ ] **Step 3: Commit**

```bash
git add scripts/learning.py
git commit -m "refactor: learning.py adds parameter validation, exception handling, help text"
```

---

### Task 8: Final verification and cleanup

**Files:**
- None (verification only)

- [ ] **Step 1: Verify no duplicate code remains**

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && grep -n "_find_db_path" *.py`
Expected: Only `db_utils.py` contains `_find_db_path`

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && grep -n "def get_connection" *.py`
Expected: Only `db_utils.py` contains `def get_connection`

- [ ] **Step 2: Verify WAL mode is active**

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python -c "from db_utils import get_connection; c = get_connection(); print('WAL:', c.execute('PRAGMA journal_mode').fetchone()[0]); print('busy_timeout:', c.execute('PRAGMA busy_timeout').fetchone()[0]); c.close()"`
Expected: `WAL: wal` and `busy_timeout: 5000`

- [ ] **Step 3: Run all CLI commands to verify no regressions**

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python learning.py knowledge list`
Expected: JSON output with `success: true`

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python learning.py progress get_session`
Expected: JSON output with `success: true`

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python learning.py review get_due`
Expected: JSON output with `success: true`

Run: `cd /mnt/d/2Study/StudyNotes/SKILLS/学习系统/scripts && python learning.py integration stats`
Expected: JSON output with `success: true`

- [ ] **Step 4: Commit final verification**

```bash
git add -A
git commit -m "refactor: complete scripts refactoring - db_utils, WAL, context manager, exception handling"
```
