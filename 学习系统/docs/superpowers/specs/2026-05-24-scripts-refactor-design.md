# 学习系统脚本重构设计文档

**日期**: 2026-05-24
**状态**: 设计完成，待实现
**目标**: 消除代码重复、提高系统稳定性、支持并发安全

---

## 一、背景与目标

### 1.1 当前问题

1. **代码重复严重**
   - `_find_db_path` 函数在 5 个文件中完全重复（150 行冗余）
   - `get_connection` 函数在 5 个文件中重复（50 行冗余）

2. **连接管理不安全**
   - 66 次 `conn.commit()` 调用，不一致
   - 26 次 `conn.close()` 调用，可能泄漏
   - 没有上下文管理器，异常时连接不会关闭

3. **错误处理不足**
   - 整个项目只有 6 个 try-catch 块
   - 大部分函数没有异常处理

4. **并发安全缺失**
   - 没有启用 WAL 模式
   - 没有设置 busy_timeout

### 1.2 优化目标

1. **消除代码重复** - 提取公共模块到 `db_utils.py`
2. **提高系统稳定性** - 统一连接管理、异常处理
3. **支持并发安全** - 启用 WAL 模式、设置 busy_timeout
4. **修复潜在 Bug** - 连接泄漏、事务不一致、空指针风险

---

## 二、设计方案

### 2.1 文件结构

```
scripts/
├── db_utils.py        # 新增：连接管理 + WAL + busy_timeout
├── db_init.py         # 重构：删除重复代码，使用 db_utils
├── knowledge_api.py   # 重构：删除重复代码，使用 db_utils
├── progress_api.py    # 重构：删除重复代码，使用 db_utils
├── review_api.py      # 重构：删除重复代码，使用 db_utils
├── integration_api.py # 重构：删除重复代码，使用 db_utils
└── learning.py        # 重构：添加参数检查和异常处理
```

### 2.2 新增 `db_utils.py`

**职责**: 统一数据库连接管理 + 并发安全

```python
# scripts/db_utils.py

import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

# 数据库路径查找
SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "learning-system.db"

def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db文件夹"""
    # 1. 环境变量
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
        return Path(env_path) / db_filename
    
    # 2. 技能目录
    p = skill_dir / db_filename
    if p.exists():
        return p
    
    # 3. 父目录找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / db_filename
            if p.exists():
                return p
            return p
    
    # 4. 默认创建
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
    """上下文管理器，自动处理连接关闭"""
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

### 2.3 重构现有 API 文件

**改动内容**:

1. **删除重复代码**
   - 删除 `_find_db_path` 函数
   - 删除 `get_connection` 函数
   - 删除 `DB_PATH` 变量

2. **改用 `db_utils`**
   - 导入 `from db_utils import get_db, get_connection, DB_PATH`
   - 使用 `with get_db() as conn:` 上下文管理器

3. **统一异常处理**
   - 添加 try-catch 块
   - 返回统一错误格式 `{"success": False, "errors": [...]}`

4. **修复潜在 Bug**
   - 空指针检查：`cursor.fetchone()` 返回 None 时
   - 事务一致性：只在最后 commit 一次
   - 连接泄漏：使用上下文管理器

### 2.4 重构 `learning.py`

**改动内容**:

1. **添加参数检查**
   - 检查 `args` 长度
   - 检查必需参数是否存在

2. **添加异常处理**
   - 捕获 `json.JSONDecodeError`
   - 捕获 `IndexError`
   - 返回友好错误信息

3. **添加帮助信息**
   - 支持 `--help` 参数
   - 显示用法说明

---

## 三、潜在 Bug 修复

### 3.1 连接泄漏修复

**问题**: 如果业务逻辑抛出异常，`conn.close()` 不会执行

**修复**: 使用 `with get_db()` 上下文管理器

```python
# 旧代码
def update_stage_progress(knowledge_id, stage_name, data):
    conn = get_connection()
    cursor = conn.cursor()
    # 如果这里抛异常，连接泄漏
    cursor.execute(...)
    conn.commit()
    conn.close()

# 新代码
def update_stage_progress(knowledge_id, stage_name, data):
    with get_db() as conn:
        cursor = conn.cursor()
        # 异常时自动 rollback，最后自动 close
        cursor.execute(...)
```

### 3.2 事务不一致修复

**问题**: 多次 commit 可能导致数据不一致

**修复**: 只在最后 commit 一次

```python
# 旧代码
conn.commit()  # 第一次 commit
if new_status == "completed":
    cursor.execute("UPDATE foundation_path ...")
    conn.commit()  # 第二次 commit，如果这里异常？

# 新代码
with get_db() as conn:
    cursor = conn.cursor()
    cursor.execute("UPDATE stage_progress ...")
    if new_status == "completed":
        cursor.execute("UPDATE foundation_path ...")
    # 只在最后 commit 一次，异常时自动 rollback
```

### 3.3 空指针风险修复

**问题**: `cursor.fetchone()` 返回 None 时，`dict(None)` 抛异常

**修复**: 先检查是否为空

```python
# 旧代码
cursor.execute("SELECT * FROM review_schedule WHERE knowledge_id = ?", (knowledge_id,))
schedule = dict(cursor.fetchone())  # 如果 fetchone() 返回 None？

# 新代码
cursor.execute("SELECT * FROM review_schedule WHERE knowledge_id = ?", (knowledge_id,))
row = cursor.fetchone()
if not row:
    return {"success": False, "errors": [f"[查询失败] 复习计划不存在: {knowledge_id}"]}
schedule = dict(row)
```

---

## 四、数据库字段审查

### 4.1 冗余字段检查

| 表 | 字段 | 状态 | 说明 |
|-----|------|------|------|
| knowledge_progress | current_level | ✅ 已删除 | 计算字段，不需要存储 |
| completed_knowledge | 整个表 | ✅ 已删除 | 只写不读，冗余表 |

### 4.2 字段类型检查

| 表 | 字段 | 当前类型 | 问题 | 建议 |
|-----|------|----------|------|------|
| knowledge_progress | created_at | TIMESTAMP | SQLite 无 TIMESTAMP 类型 | 保持现状（实际存储 TEXT） |
| foundation_path | completed_at | TIMESTAMP | 同上 | 保持现状 |

**结论**: SQLite 没有原生 TIMESTAMP 类型，实际上存储的是 TEXT，设计合理

### 4.3 外键约束检查

所有外键约束设计合理，关联正确。

### 4.4 CHECK 约束检查

所有 CHECK 约束设计合理，枚举值正确。

---

## 五、预期效果

| 优化项 | 优化前 | 优化后 |
|--------|--------|--------|
| 代码行数 | 2915 行 | ~2400 行（减少 ~500 行） |
| 重复代码 | 200+ 行 | 0 行 |
| 连接管理 | 手动 close，可能泄漏 | 上下文管理器，自动关闭 |
| 异常处理 | 6 个 try-catch | 每个函数都有异常处理 |
| 并发安全 | 无 | WAL + busy_timeout |
| 事务一致性 | 多次 commit | 统一 commit |

---

## 六、风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|----------|
| 重构引入新 Bug | 中 | 高 | 充分测试，保持 CLI 接口不变 |
| 性能下降 | 低 | 低 | WAL 模式实际上会提高性能 |
| 数据丢失 | 低 | 高 | 重构前备份数据库 |

---

## 七、实施计划

1. **Phase 1**: 创建 `db_utils.py`
2. **Phase 2**: 重构 `db_init.py`
3. **Phase 3**: 重构 `knowledge_api.py`
4. **Phase 4**: 重构 `progress_api.py`
5. **Phase 5**: 重构 `review_api.py`
6. **Phase 6**: 重构 `integration_api.py`
7. **Phase 7**: 重构 `learning.py`
8. **Phase 8**: 测试验证

---

## 八、验收标准

1. ✅ 所有重复代码已消除
2. ✅ 所有连接使用上下文管理器
3. ✅ 所有函数有异常处理
4. ✅ 启用 WAL 模式和 busy_timeout
5. ✅ 修复所有潜在 Bug
6. ✅ CLI 接口保持不变
7. ✅ 所有现有功能正常工作
