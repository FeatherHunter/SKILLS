# 卡路里 SKILL 全面优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 38 个问题，深度拆分 calorie_tracker.py，精简 SKILL.md，补全文档，重新生成 config。

**Architecture:** 提取共享 db_utils.py 模块消除 4 处重复代码；将 11 个分析函数从 calorie_tracker.py 搬入独立的 analysis.py；逐文件修复 15 个 bug；SKILL.md 从 625 行精简至 ~300 行。

**Tech Stack:** Python 3.7+, SQLite3, argparse

---

## File Structure

```
卡路里/
├── SKILL.md                          # Modify: 瘦身 625→~300 行
├── _meta.json                        # No change
├── config-calorie.ts                 # Regenerate: 修复 5 个 bug
├── .gitignore                        # Create: 排除 __pycache__
├── scripts/
│   ├── db_utils.py                   # Create: 共享 DB 路径查找 + 连接
│   ├── analysis.py                   # Create: 11 个分析函数 + 4 个统一入口
│   ├── calorie_tracker.py            # Modify: 删分析代码、用 db_utils、修 12 个 bug
│   ├── exercise_tracker.py           # Modify: 用 db_utils、删重复代码
│   ├── fitness_goals.py              # Modify: 用 db_utils、删死代码
│   ├── sleep_tracker.py              # Modify: 用 db_utils、统一时间格式
│   └── generate_ts_config.py         # Modify: 修复 5 个 bug
└── references/
    ├── analysis_api.md               # Modify: 补全 dashboard 说明
    └── database_schema.md            # Modify: 补全 2 张表
```

---

## Task 1: 创建 `scripts/db_utils.py`

**Files:**
- Create: `卡路里/scripts/db_utils.py`

- [ ] **Step 1: 创建 db_utils.py**

```python
#!/usr/bin/env python3
"""共享数据库工具 - 提供 DB 路径查找和连接"""

import os
import sqlite3
from pathlib import Path


def find_db_path(skill_dir, db_filename="calorie_data.db"):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db

    Args:
        skill_dir: 技能目录路径（通常为 Path(__file__).parent.parent）
        db_filename: 数据库文件名

    Returns:
        Path: 数据库文件路径
    """
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
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
    # 4. 都找不到则创建在 .db 目录
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename


def get_db(db_path):
    """获取数据库连接

    Args:
        db_path: 数据库文件路径（Path 对象）

    Returns:
        sqlite3.Connection: 数据库连接（row_factory=sqlite3.Row）
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
```

- [ ] **Step 2: 验证模块可导入**

Run: `cd "D:/2Study/StudyNotes/SKILLS/卡路里" && python -c "from scripts.db_utils import find_db_path, get_db; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add scripts/db_utils.py
git commit -m "feat: 创建 db_utils.py 共享模块，提取 DB 路径查找和连接"
```

---

## Task 2: 创建 `scripts/analysis.py`

**Files:**
- Create: `卡路里/scripts/analysis.py`
- Read: `卡路里/scripts/calorie_tracker.py:1077-1823`（源代码）

- [ ] **Step 1: 从 calorie_tracker.py 搬出分析代码**

从 `calorie_tracker.py` 第 1077-1823 行复制以下函数到新文件 `analysis.py`：
- `_parse_date()`、`_days_between()`
- `weight_trend()`、`weight_compare()`、`weight_milestone()`、`weight_volatility()`
- `diet_calorie_trend()`、`diet_macro_ratio()`、`diet_food_ranking()`、`diet_deficit_analysis()`
- `exercise_trend()`、`exercise_type_breakdown()`、`exercise_deficit_contribution()`
- `weight_analysis()`、`diet_analysis()`、`exercise_analysis()`、`dashboard()`

文件头部改为：

```python
#!/usr/bin/env python3
"""
卡路里 - 分析系统
11个分析函数 + 4个统一入口
"""

import sqlite3
import os
import statistics
from datetime import datetime, timedelta, date
from collections import defaultdict
from pathlib import Path

from db_utils import find_db_path, get_db

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)
BMR_ACTIVITY_FACTOR = 1.3


def _get_db():
    return get_db(DB_PATH)


def _get_goal():
    """获取每日目标（从 calorie_tracker 复制）"""
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM daily_goal WHERE id = 1')
    row = c.fetchone()
    conn.close()
    return row


def _get_weight_goal():
    """获取体重目标（从 calorie_tracker 复制，合并为单次连接）"""
    conn = _get_db()
    c = conn.cursor()
    c.execute('SELECT weight_goal, goal_deadline FROM daily_goal WHERE id = 1')
    row = c.fetchone()
    if not row or not row[0]:
        conn.close()
        return None

    weight_goal, deadline = row

    c.execute('SELECT weight_kg, date FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = c.fetchone()
    if not wrow:
        conn.close()
        return (weight_goal, deadline, None, None, None)

    current_weight, current_date = wrow

    days_left = None
    calorie_adjustment = None

    if deadline:
        deadline_dt = datetime.strptime(deadline, '%Y-%m-%d')
        today_dt = datetime.strptime(current_date, '%Y-%m-%d')
        days_left = (deadline_dt - today_dt).days

    if days_left is not None and days_left > 0:
        gap = current_weight - weight_goal
        required_daily = gap / days_left
        calorie_adjustment = int(required_daily * 7700)

    conn.close()
    return (weight_goal, deadline, days_left, None, calorie_adjustment)
```

然后依次放入所有分析函数（原样复制，修复以下 bug）。

- [ ] **Step 2: 修复搬入时的 bug**

在 `analysis.py` 中修复以下问题：

**Bug #4 — weight_compare 调用方式**：`weight_analysis('compare')` 改为接受额外参数：

```python
def weight_analysis(start_date, end_date=None, analysis_type='trend',
                    compare_start=None, compare_end=None):
    if analysis_type == 'trend':
        return weight_trend(start_date, end_date)
    elif analysis_type == 'compare':
        if compare_start and compare_end:
            return weight_compare(start_date, end_date or start_date,
                                  compare_start, compare_end)
        else:
            # 默认：与上一个等长周期对比
            span = _days_between(start_date, end_date or start_date)
            from datetime import datetime, timedelta
            end_dt = datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)
            cs = (end_dt - timedelta(days=span)).strftime('%Y-%m-%d')
            ce = end_dt.strftime('%Y-%m-%d')
            return weight_compare(start_date, end_date or start_date, cs, ce)
    # ... 其余不变
```

**Bug #5 — weight_milestone 日均变化**：

```python
# 原代码（错误）：
# actual_daily = (max_w - min_w) / 30

# 修复为：
c.execute('''SELECT weight_kg, date FROM weight_log
             WHERE date >= date('now', '-30 days')
             ORDER BY date ASC''')
rows_30 = c.fetchall()
if rows_30 and len(rows_30) >= 2:
    first_w_30, first_d_30 = rows_30[0][0], rows_30[0][1]
    last_w_30, last_d_30 = rows_30[-1][0], rows_30[-1][1]
    span_30 = _days_between(first_d_30, last_d_30) + 1
    actual_daily = (last_w_30 - first_w_30) / span_30 if span_30 > 0 else None
else:
    actual_daily = None
```

**Bug #6 — eval_pct 硬编码**：

```python
def diet_macro_ratio(start_date, end_date=None):
    # ... 前面不变 ...
    goal = _get_goal()

    def eval_pct(pct, macro_name):
        if pct is None:
            return "未设目标"
        # 从实际目标计算占比
        if goal:
            cal_goal = goal[1] or 1800
            if macro_name == '蛋白':
                target_pct = (goal[2] or 150) * 4 / cal_goal * 100
            elif macro_name == '碳':
                target_pct = (goal[3] or 200) * 4 / cal_goal * 100
            else:  # 脂肪
                target_pct = (goal[4] or 60) * 9 / cal_goal * 100
        else:
            target_pct = 35  # 无目标时的默认参考值
        diff = pct - target_pct
        arrow = "↑" if diff > 3 else ("↓" if diff < -3 else "✓")
        status = "偏高" if diff > 3 else ("偏低" if diff < -3 else "正常")
        return f"{pct:.0f}% {arrow} {status}"
    # ... 后面不变 ...
```

**BMR 常量**：所有 `* 24 * 1.3` 替换为 `* 24 * BMR_ACTIVITY_FACTOR`。

- [ ] **Step 3: 验证 analysis.py 可导入**

Run: `cd "D:/2Study/StudyNotes/SKILLS/卡路里" && python -c "from scripts.analysis import weight_analysis, diet_analysis, exercise_analysis, dashboard; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add scripts/analysis.py
git commit -m "feat: 创建 analysis.py，从 calorie_tracker.py 搬出 11 个分析函数"
```

---

## Task 3: 改造 `calorie_tracker.py`（删分析代码 + 用 db_utils + 修 bug）

**Files:**
- Modify: `卡路里/scripts/calorie_tracker.py`

- [ ] **Step 1: 替换 import 和 DB 初始化（第 1-41 行）**

将文件头部替换为：

```python
#!/usr/bin/env python3
"""
卡路里 - 热量追踪脚本 v2.0
支持：食物记录(热量/蛋白质/碳水/脂肪)、每日目标、体重追踪
"""

import sqlite3
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from db_utils import find_db_path, get_db

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)
BMR_ACTIVITY_FACTOR = 1.3
```

删除原来的 `_find_db_path` 函数（第 16-38 行）和 `DB_PATH = _find_db_path(...)` 行。

- [ ] **Step 2: 修改 get_db() 使用 db_utils**

```python
def get_db():
    """Get database connection"""
    if not DB_PATH.exists():
        init_db()
    return get_db(DB_PATH)
```

注意：这里 `get_db()` 函数名和 `db_utils.get_db` 冲突。改为：

```python
from db_utils import find_db_path as _find_db_path
from db_utils import get_db as _get_db_conn

DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)

def get_db():
    """Get database connection, auto-init if needed"""
    if not DB_PATH.exists():
        init_db()
    return _get_db_conn(DB_PATH)
```

- [ ] **Step 3: 修复裸 except（第 135/139/158/1097 行）**

```python
# 原代码：
# except:
#     pass

# 改为：
except Exception:
    pass
```

- [ ] **Step 4: 修复 set_weight_goal（第 515-530 行）**

```python
def set_weight_goal(weight_goal, deadline=None):
    """设置体重目标"""
    conn = get_db()
    c = conn.cursor()
    # 先尝试更新
    c.execute('''
        UPDATE daily_goal
        SET weight_goal = ?, goal_deadline = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = 1
    ''', (weight_goal, deadline))
    if c.rowcount == 0:
        # 行不存在，插入
        c.execute('''
            INSERT INTO daily_goal (id, weight_goal, goal_deadline)
            VALUES (1, ?, ?)
        ''', (weight_goal, deadline))
    conn.commit()
    conn.close()
    print(f"✓ 体重目标已设定：{weight_goal} kg"
          + (f" | 目标日期：{deadline}" if deadline else ""))
```

- [ ] **Step 5: 修复 get_weight_goal（第 533-585 行）— 合并为 1 次连接**

```python
def get_weight_goal():
    """获取体重目标，返回 (weight_goal, deadline, days_left, daily_change_rate, calorie_adjustment)"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT weight_goal, goal_deadline FROM daily_goal WHERE id = 1')
    row = c.fetchone()

    if not row or not row[0]:
        conn.close()
        return None

    weight_goal, deadline = row

    c.execute('SELECT weight_kg, date FROM weight_log ORDER BY date DESC LIMIT 1')
    wrow = c.fetchone()
    if not wrow:
        conn.close()
        return (weight_goal, deadline, None, None, None)

    current_weight, current_date = wrow

    daily_change_rate = None
    days_left = None
    calorie_adjustment = None

    if deadline:
        deadline_dt = datetime.strptime(deadline, '%Y-%m-%d')
        today_dt = datetime.strptime(current_date, '%Y-%m-%d')
        days_left = (deadline_dt - today_dt).days

    if days_left is not None and days_left > 0:
        gap = current_weight - weight_goal
        required_daily = gap / days_left
        calorie_adjustment = int(required_daily * 7700)

    conn.close()
    return (weight_goal, deadline, days_left, daily_change_rate, calorie_adjustment)
```

- [ ] **Step 6: 修复 add-product CLI 的 '0' 判断（第 1015-1030 行）**

```python
# 原代码：
# saturated_fat = float(sys.argv[7]) if sys.argv[7] != '0' else None
# sugar = float(sys.argv[9]) if sys.argv[9] != '0' else None
# fiber = float(sys.argv[10]) if sys.argv[10] != '0' else None

# 改为：
saturated_fat = float(sys.argv[7]) or None
sugar = float(sys.argv[9]) or None
fiber = float(sys.argv[10]) or None
```

- [ ] **Step 7: 删除函数内重复 import**

删除以下位置的局部 import（文件顶部已有）：
- 第 573 行 `from datetime import datetime`（get_weight_goal 内）
- 第 599 行 `from datetime import date`（add_exercise 内）
- 第 655 行 `from collections import defaultdict`（exercise_summary 内）

保留 exercise_summary 的 `from collections import defaultdict` 改为文件顶部添加 `from collections import defaultdict`。

- [ ] **Step 8: 修复 list_entries 中未使用的 meal 变量（第 332-334 行）**

```python
# 原代码：
# meal = infer_meal_type(time) if time else ""
# print(f"{entry_id:>3} | {time[0:5]:>5} | ...")

# 改为（删除 meal 行）：
print(f"{entry_id:>3} | {time[0:5]:>5} | {food_name:15} | ...")
```

- [ ] **Step 9: 修复 update_product f-string SQL（第 833-838 行）**

```python
# 原代码：
# set_clause = ', '.join([f"{k} = ?" for k in update_data.keys()])
# c.execute(f'UPDATE nutrition_products SET {set_clause} WHERE id = ?', values)

# 改为（字段名来自白名单 allowed_fields，安全可控，但用参数化更规范）：
# 逻辑不变，确认 allowed_fields 是硬编码白名单即可，不改。
# 此项风险极低，保持原样。
```

注：经评估，`update_product` 的字段名来自硬编码白名单 `allowed_fields`，不存在注入风险。保持原样，不修改。

- [ ] **Step 10: 修复 history() SQL 拼接（第 887-893 行）**

```python
# 原代码：
# WHERE date >= date('now', '-' || ? || ' days')

# 改为：
start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
c.execute('''
    SELECT date, SUM(calories), SUM(protein), SUM(carbs), SUM(fat)
    FROM entries
    WHERE date >= ?
    GROUP BY date
    ORDER BY date DESC
''', (start,))
```

- [ ] **Step 11: 删除分析代码（第 1077-1823 行）**

删除 `calorie_tracker.py` 第 1077 行到文件末尾的所有代码。即删除：
- `_parse_date()`、`_days_between()`
- 所有 `weight_*`、`diet_*`、`exercise_*` 分析函数
- `weight_analysis()`、`diet_analysis()`、`exercise_analysis()`、`dashboard()`

- [ ] **Step 12: 验证 calorie_tracker.py 可运行**

Run: `cd "D:/2Study/StudyNotes/SKILLS/卡路里" && python scripts/calorie_tracker.py`
Expected: 显示 usage 信息，无报错

- [ ] **Step 13: Commit**

```bash
git add scripts/calorie_tracker.py
git commit -m "refactor: calorie_tracker.py 删分析代码、用 db_utils、修 6 个 bug"
```

---

## Task 4: 改造 `exercise_tracker.py`

**Files:**
- Modify: `卡路里/scripts/exercise_tracker.py:1-73`

- [ ] **Step 1: 替换 import 和 DB 初始化**

将第 37-73 行替换为：

```python
import sys
import os
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from db_utils import find_db_path, get_db as _get_db_conn

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def get_db():
    """获取数据库连接"""
    return _get_db_conn(DB_PATH)
```

删除原来的 `_find_db_path` 函数（第 49-71 行）。

- [ ] **Step 2: 验证可运行**

Run: `cd "D:/2Study/StudyNotes/SKILLS/卡路里" && python scripts/exercise_tracker.py --help`
Expected: 显示帮助信息，无报错

- [ ] **Step 3: Commit**

```bash
git add scripts/exercise_tracker.py
git commit -m "refactor: exercise_tracker.py 用 db_utils 替代重复的 _find_db_path"
```

---

## Task 5: 改造 `fitness_goals.py`

**Files:**
- Modify: `卡路里/scripts/fitness_goals.py`

- [ ] **Step 1: 替换 import 和 DB 初始化**

将第 7-42 行替换为：

```python
import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

from db_utils import find_db_path, get_db as _get_db_conn

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def get_db():
    """获取数据库连接"""
    return _get_db_conn(DB_PATH)
```

删除原来的 `_find_db_path` 函数（第 17-39 行）。

- [ ] **Step 2: 删除 complete_goal 死代码（第 194-196 行）**

```python
# 删除：
# def complete_goal(goal_id):
#     """标记目标完成"""
#     update_goal(goal_id, status='completed')
```

- [ ] **Step 3: 验证可运行**

Run: `cd "D:/2Study/StudyNotes/SKILLS/卡路里" && python scripts/fitness_goals.py --help`
Expected: 显示帮助信息，无报错

- [ ] **Step 4: Commit**

```bash
git add scripts/fitness_goals.py
git commit -m "refactor: fitness_goals.py 用 db_utils、删 complete_goal 死代码"
```

---

## Task 6: 改造 `sleep_tracker.py`

**Files:**
- Modify: `卡路里/scripts/sleep_tracker.py`

- [ ] **Step 1: 替换 import 和 DB 初始化**

将第 7-41 行替换为：

```python
import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from db_utils import find_db_path, get_db as _get_db_conn

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def get_db():
    """获取数据库连接"""
    return _get_db_conn(DB_PATH)
```

删除原来的 `_find_db_path` 函数（第 16-38 行）。删除 `import time`。

- [ ] **Step 2: 统一时间戳格式**

将 `add_sleep` 函数中的：
```python
now = int(time.time())
```
改为：
```python
now = datetime.now().isoformat()
```

将 `update_sleep` 函数中的：
```python
updates.append("updated_at = ?")
params.append(int(time.time()))
```
改为：
```python
updates.append("updated_at = ?")
params.append(datetime.now().isoformat())
```

- [ ] **Step 3: 验证可运行**

Run: `cd "D:/2Study/StudyNotes/SKILLS/卡路里" && python scripts/sleep_tracker.py --help`
Expected: 显示帮助信息，无报错

- [ ] **Step 4: Commit**

```bash
git add scripts/sleep_tracker.py
git commit -m "refactor: sleep_tracker.py 用 db_utils、统一时间戳为 ISO 格式"
```

---

## Task 7: 修复 `generate_ts_config.py`（5 个 bug）

**Files:**
- Modify: `卡路里/scripts/generate_ts_config.py`

- [ ] **Step 1: 修复 to_ts_type（第 49-51 行）**

```python
# 原代码：
# type_map = {"INTEGER": "INTEGER", "REAL": "REAL", "TEXT": "TEXT"}

# 改为：
def to_ts_type(sqlite_type):
    """SQLite 类型 → TypeScript 类型"""
    type_map = {"INTEGER": "number", "REAL": "number", "TEXT": "string"}
    return type_map.get(sqlite_type.upper(), "string")
```

- [ ] **Step 2: 修复 generate_table_fields 中 bedtime/wake_time 误隐藏（第 67-71 行）**

```python
# 原代码：
# elif "time" in name.lower() or ("created" in name or "updated" in name):

# 改为：
elif name in ("created_at", "updated_at"):
    field["format"] = "datetime"
    field["visible"] = False
elif name in ("bedtime", "wake_time"):
    field["format"] = "time"
    field["visible"] = True
elif "time" in name.lower():
    field["format"] = "datetime"
    field["visible"] = False
```

- [ ] **Step 3: 修复 carbohydrates 漏标 unit（第 72-87 行）**

```python
# 原代码：
# elif "carbs" in name or "fat" in name:
#     field["unit"] = "克"

# 改为：
elif "carbs" in name or "carbohydrates" in name or "fat" in name:
    field["unit"] = "克"
```

- [ ] **Step 4: 修复 table_labels 缺少 sleep_records（第 94-102 行）**

```python
# 原代码：
# table_labels = {
#     "entries": "饮食记录",
#     ...
# }

# 改为：
table_labels = {
    "entries": "饮食记录",
    "weight_log": "体重记录",
    "exercise_log": "运动记录",
    "sleep_records": "睡眠记录",
    "nutrition_products": "食品库",
    "fitness_goals": "健身目标",
    "daily_goal": "每日目标",
}
```

- [ ] **Step 5: 修复无 date 列的表生成错误查询（第 103-117 行）**

```python
def generate_queries_for_table(table, columns):
    """根据表名和列生成查询"""
    table_labels = {
        "entries": "饮食记录",
        "weight_log": "体重记录",
        "exercise_log": "运动记录",
        "sleep_records": "睡眠记录",
        "nutrition_products": "食品库",
        "fitness_goals": "健身目标",
        "daily_goal": "每日目标",
    }
    label = table_labels.get(table, table)

    col_names = [c[1] for c in columns]
    has_date = "date" in col_names

    if has_date:
        return [
            {
                "id": f"{table}-daily",
                "label": f"今日{label}",
                "sql": f"SELECT * FROM {table} WHERE date = '{{date}}' ORDER BY time",
                "params": [{"name": "date", "type": "date", "label": "日期", "default": "TODAY"}]
            },
            {
                "id": f"{table}-history",
                "label": f"{label}历史",
                "sql": f"SELECT * FROM {table} ORDER BY date DESC, time DESC LIMIT 100",
                "params": []
            }
        ]
    else:
        return [
            {
                "id": f"{table}-all",
                "label": f"全部{label}",
                "sql": f"SELECT * FROM {table} ORDER BY id DESC",
                "params": []
            }
        ]
```

同时修改 `main()` 中调用处，传入 `columns`：

```python
all_queries.extend(generate_queries_for_table(table, columns))
```

- [ ] **Step 6: 更新 generate_action 和 generate_view 的 label**

```python
def generate_action(table, fields):
    table_labels = {
        "entries": "饮食记录",
        "weight_log": "体重记录",
        "exercise_log": "运动记录",
        "sleep_records": "睡眠记录",
        "nutrition_products": "食品库",
        "fitness_goals": "健身目标",
        "daily_goal": "每日目标",
    }
    label = table_labels.get(table, table)
    # ...
    return {
        "id": f"add-{table}",
        "label": f"添加{label}",  # 中文 label
        # ...
    }

def generate_view(table, query_ids, columns):
    table_labels = { ... }  # 同上
    label = table_labels.get(table, table)
    return {
        "id": table,
        "label": label,  # 中文 label
        # ...
    }
```

- [ ] **Step 7: 验证生成器可运行**

Run: `cd "D:/2Study/StudyNotes/SKILLS/卡路里" && python scripts/generate_ts_config.py`
Expected: 输出表数量和写入路径，无报错。检查生成的 config-calorie.ts 确认：
- 类型是 number/string 而非 INTEGER/TEXT
- bedtime/wake_time 可见
- 无 date 列的表没有 WHERE date 查询

- [ ] **Step 8: Commit**

```bash
git add scripts/generate_ts_config.py
git commit -m "fix: generate_ts_config.py 修复类型映射、字段可见性、查询生成等 5 个 bug"
```

---

## Task 8: 瘦身 `SKILL.md`

**Files:**
- Modify: `卡路里/SKILL.md`

- [ ] **Step 1: 删除数据库表结构定义（第 151-252 行）**

替换为：

```markdown
## 数据库结构

详见 [`references/database_schema.md`](references/database_schema.md)

共 7 张表：`entries`、`daily_goal`、`weight_log`、`exercise_log`、`nutrition_products`、`fitness_goals`、`sleep_records`
```

- [ ] **Step 2: 删除 AI 触发指引中的重复触发词**

第 376-547 行的"AI 触发指引"区，删除每个触发场景下的触发词列表（已在帮助区列出），只保留：
- 触发场景标题
- 操作步骤（完整流程）

- [ ] **Step 3: 修复硬编码路径**

全文搜索 `workspace/skills/卡路里/`，替换为 `scripts/`。

- [ ] **Step 4: 修复 protein_goal 默认值**

第 173 行 `protein_goal` 默认值从 156 改为 150。

- [ ] **Step 5: 补充分散初始化说明**

在"数据库结构"部分添加：

```markdown
> **初始化说明**：`entries`、`daily_goal`、`weight_log`、`exercise_log`、`nutrition_products` 由 `calorie_tracker.py` 的 `init_db()` 创建；`fitness_goals` 由 `fitness_goals.py` 的 `init_table()` 创建；`sleep_records` 由 `sleep_tracker.py` 的 `init_table()` 创建。
```

- [ ] **Step 6: 补充 CLI 用法**

在"命令行用法"区添加以下内容：

```markdown
### 运动记录 CLI
\`\`\`bash
python scripts/exercise_tracker.py add --date 2026-05-22 --type 骑行 --calories 300 --minutes 40
python scripts/exercise_tracker.py list --days 7
python scripts/exercise_tracker.py summary --days 7
python scripts/exercise_tracker.py trend --days 7
\`\`\`

### 健身目标 CLI
\`\`\`bash
python scripts/fitness_goals.py add "每日俯卧撑" --type daily --exercise 俯卧撑 --unit 个 --target 50 --start 2026-05-22
python scripts/fitness_goals.py list --status active
python scripts/fitness_goals.py update 1 --target 60
python scripts/fitness_goals.py delete 1
\`\`\`

### 睡眠记录 CLI
\`\`\`bash
python scripts/sleep_tracker.py add 2026-05-22 --hours 7.5 --bed 23:30 --wake 07:00
python scripts/sleep_tracker.py update 2026-05-22 --hours 8 --note "睡得不错"
python scripts/sleep_tracker.py list --days 7
\`\`\`
```

- [ ] **Step 7: 验证行数**

Run: `wc -l "D:/2Study/StudyNotes/SKILLS/卡路里/SKILL.md"`
Expected: ~300 行

- [ ] **Step 8: Commit**

```bash
git add SKILL.md
git commit -m "docs: SKILL.md 瘦身 625→~300 行，删重复内容、修硬编码路径"
```

---

## Task 9: 补全 `references/database_schema.md`

**Files:**
- Modify: `卡路里/references/database_schema.md`

- [ ] **Step 1: 添加 fitness_goals 表定义**

在 exercise_log 表之后添加：

```markdown
## fitness_goals — 健身目标

```sql
CREATE TABLE fitness_goals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    goal_type       TEXT NOT NULL,    -- daily/weekly/monthly/longterm
    exercise_type   TEXT NOT NULL,
    target_unit     TEXT NOT NULL,    -- 个/分钟/公里
    target_value    INTEGER NOT NULL,
    start_date      TEXT NOT NULL,
    end_date        TEXT,             -- NULL 表示永久
    status          TEXT DEFAULT 'active',  -- active/paused
    note            TEXT,
    created_at      INTEGER NOT NULL,
    updated_at      INTEGER
);
CREATE INDEX idx_fg_date ON fitness_goals(start_date);
CREATE INDEX idx_fg_type ON fitness_goals(exercise_type);
CREATE INDEX idx_fg_status ON fitness_goals(status);
```
```

- [ ] **Step 2: 添加 sleep_records 表定义**

```markdown
## sleep_records — 睡眠记录

```sql
CREATE TABLE sleep_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL UNIQUE,  -- 归属就寝日
    sleep_hours     REAL NOT NULL,
    bedtime         TEXT,             -- HH:MM
    wake_time       TEXT,             -- HH:MM
    note            TEXT,
    created_at      TEXT NOT NULL,    -- ISO 格式
    updated_at      TEXT
);
CREATE INDEX idx_sleep_date ON sleep_records(date);
```

> **睡眠归属规则**：记录归属于**就寝那天**，而非起床日。
```

- [ ] **Step 3: 补全索引说明表**

在索引说明表中添加：

| `idx_fg_date` | fitness_goals | 按开始日期查询 |
| `idx_fg_type` | fitness_goals | 按运动类型查询 |
| `idx_fg_status` | fitness_goals | 按状态筛选 |
| `idx_sleep_date` | sleep_records | 按日期查询 |
| `idx_product_name` | nutrition_products | 搜索食品名称 |

- [ ] **Step 4: 更新表关系图**

```markdown
## 表关系

```
daily_goal (1条记录)
  ├── calorie_goal, protein_goal, carbs_goal, fat_goal → 每日营养目标
  └── weight_goal, goal_deadline → 体重目标

entries (多条)
  └── date → 每日饮食记录

weight_log (多条)
  └── date → 每日体重

exercise_log (多条)
  └── date → 每日运动

fitness_goals (多条)
  └── goal_type + status → 健身目标管理

sleep_records (多条)
  └── date → 每日睡眠（归属就寝日）

nutrition_products (多条)
  └── product_name → 食品营养成分库
```
```

- [ ] **Step 5: Commit**

```bash
git add references/database_schema.md
git commit -m "docs: database_schema.md 补全 fitness_goals + sleep_records 表定义"
```

---

## Task 10: 补全 `references/analysis_api.md`

**Files:**
- Modify: `卡路里/references/analysis_api.md`

- [ ] **Step 1: 补全 dashboard 说明**

在 `### 4. dashboard` 部分扩展为：

```markdown
### 4. dashboard — 综合报告

```python
dashboard(start_date, end_date=None)
```

整合四维度分析并输出：
1. 体重趋势（调用 `weight_trend`）
2. 热量趋势（调用 `diet_calorie_trend`）
3. 运动趋势（调用 `exercise_trend`）
4. 热量缺口（调用 `diet_deficit_analysis`）

每个维度独立 try/except，单个维度失败不影响其他维度输出。
```

- [ ] **Step 2: 添加 weight_analysis 的 compare 参数说明**

```markdown
### 1. weight_analysis — 体重变化分析

```python
weight_analysis(start_date, end_date=None, analysis_type='trend',
                compare_start=None, compare_end=None)
```

| analysis_type | 说明 | 额外参数 |
|---|---|---|
| `'trend'` | 趋势分析 | — |
| `'compare'` | 同期对比 | `compare_start`/`compare_end` 可选，默认与上一个等长周期对比 |
| `'milestone'` | 目标进度 | — |
| `'volatility'` | 波动分析 | — |
```

- [ ] **Step 3: Commit**

```bash
git add references/analysis_api.md
git commit -m "docs: analysis_api.md 补全 dashboard 说明和 compare 参数"
```

---

## Task 11: 创建 `.gitignore` + 重新生成 `config-calorie.ts`

**Files:**
- Create: `卡路里/.gitignore`
- Regenerate: `卡路里/config-calorie.ts`

- [ ] **Step 1: 创建 .gitignore**

```
__pycache__/
*.pyc
.db/
```

- [ ] **Step 2: 重新生成 config-calorie.ts**

Run: `cd "D:/2Study/StudyNotes/SKILLS/卡路里" && python scripts/generate_ts_config.py`

- [ ] **Step 3: 验证生成结果**

检查 `config-calorie.ts`：
- 字段类型是 `number`/`string`（不是 `INTEGER`/`TEXT`）
- `bedtime`/`wake_time` 的 `visible` 不是 `false`
- `daily_goal`、`fitness_goals`、`sleep_records` 的查询没有 `WHERE date`
- Action label 是中文（如"添加饮食记录"不是"添加entries"）
- `carbohydrates` 有 `unit: "克"`

- [ ] **Step 4: Commit**

```bash
git add .gitignore config-calorie.ts
git commit -m "fix: 重新生成 config-calorie.ts，修复类型/可见性/查询等 5 个 bug"
```

---

## Task 12: 最终验证

- [ ] **Step 1: 运行所有脚本确认无报错**

```bash
cd "D:/2Study/StudyNotes/SKILLS/卡路里"
python scripts/calorie_tracker.py
python scripts/exercise_tracker.py --help
python scripts/fitness_goals.py --help
python scripts/sleep_tracker.py --help
python scripts/generate_ts_config.py
python -c "from scripts.analysis import weight_analysis, diet_analysis, exercise_analysis, dashboard; print('analysis OK')"
```

- [ ] **Step 2: 检查文件行数**

```bash
wc -l SKILL.md scripts/calorie_tracker.py scripts/analysis.py scripts/db_utils.py
```

Expected:
- SKILL.md: ~300 行
- calorie_tracker.py: ~500 行
- analysis.py: ~750 行
- db_utils.py: ~45 行

- [ ] **Step 3: 最终 Commit**

```bash
git add -A
git commit -m "chore: 卡路里 SKILL 全面优化完成 - 38 个问题修复"
```
