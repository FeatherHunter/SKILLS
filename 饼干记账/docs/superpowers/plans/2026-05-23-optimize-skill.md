# 饼干记账 SKILL 优化实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复审查发现的 25 个问题，合并 query.py 到 db.py，去掉每日文件，重写 SKILL.md，修复 config.ts。

**Architecture:** db.py 作为唯一数据层（合并 query.py 的查询函数），analyze.py 作为分析层，record_bill.py 作为 CLI 入口。SQLite 为唯一存储，去掉每日账单文件。

**Tech Stack:** Python 3.x, sqlite3, argparse, TypeScript

---

## 文件结构

```
饼干记账/
├── SKILL.md                        # 重写
├── _meta.json                      # 不变
├── config-cookie-accounting.ts     # 修改
├── .gitignore                      # 修改
├── references/
│   └── categories.md               # 不变
└── scripts/
    ├── db.py                       # 重构（合并 query.py）
    ├── analyze.py                  # 修改
    └── record_bill.py              # 修改
```

**删除：** `scripts/query.py`, `scripts/__init__.py`

---

### Task 1: 重构 db.py（合并 query.py + 去掉每日文件 + 修复所有问题）

**Files:**
- Modify: `scripts/db.py`
- Create: `scripts/test_db.py`

- [ ] **Step 1: 创建测试文件**

```python
"""
db.py 测试
"""
import sys
import os
import tempfile
from pathlib import Path
from datetime import date

# 设置临时数据库环境
_TEST_DB_DIR = tempfile.mkdtemp()
os.environ['SKILLS_DB_PATH'] = _TEST_DB_DIR

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))


def test_find_db_path_env():
    """测试环境变量路径查找"""
    from db import _find_db_path
    result = _find_db_path(Path("/fake/skill"), "test.db")
    assert result == Path(_TEST_DB_DIR) / "test.db"


def test_find_db_path_parent():
    """测试父目录路径查找"""
    # 创建临时 .db 目录
    import tempfile
    parent = Path(tempfile.mkdtemp())
    db_dir = parent / ".db"
    db_dir.mkdir()
    skill_dir = parent / "skills" / "test_skill"
    skill_dir.mkdir(parents=True)
    result = _find_db_path(skill_dir, "test.db")
    assert result == db_dir / "test.db"


def test_find_db_path_fallback():
    """测试 fallback 到技能目录 .db 子目录"""
    import tempfile
    skill_dir = Path(tempfile.mkdtemp())
    # 清除环境变量以测试 fallback
    old_env = os.environ.pop('SKILLS_DB_PATH', None)
    result = _find_db_path(skill_dir, "test.db")
    assert result == skill_dir / ".db" / "test.db"
    if old_env:
        os.environ['SKILLS_DB_PATH'] = old_env


def test_init_db_creates_table():
    """测试数据库初始化创建表"""
    from db import init_db
    conn = init_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bills'")
    assert cursor.fetchone() is not None
    conn.close()


def test_insert_and_fetch():
    """测试插入和查询"""
    from db import insert_record, fetch_all
    result = insert_record("餐饮", -35.0, "2026-05-23 12:00:00", note="午饭")
    assert result['id'] > 0
    assert result['category'] == "餐饮"
    assert result['amount'] == -35.0
    records = fetch_all(from_time="2026-05-23 00:00:00", to_time="2026-05-23 23:59:59")
    assert len(records) >= 1


def test_add_bill():
    """测试 add_bill（只写 SQLite，不写文件）"""
    from db import add_bill
    result = add_bill("交通", -4.0, "2026-05-23 08:00:00", note="地铁")
    assert result['success'] is True
    assert result['id'] > 0
    assert 'file' not in result  # 不再有 file 字段


def test_list_today():
    """测试 list_today"""
    from db import list_today
    records = list_today()
    assert isinstance(records, list)


def test_list_date():
    """测试 list_date"""
    from db import list_date
    records = list_date("2026-05-23")
    assert isinstance(records, list)


def test_list_date_range():
    """测试 list_date_range"""
    from db import list_date_range
    records = list_date_range("2026-05-01", "2026-05-31")
    assert isinstance(records, list)


def test_list_date_range_missing_param():
    """测试 list_date_range 缺少参数"""
    from db import list_date_range
    try:
        list_date_range("2026-05-01", None)
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass


def test_list_by_category():
    """测试 list_by_category"""
    from db import list_by_category
    records = list_by_category("餐饮")
    assert isinstance(records, list)


def test_search_keyword():
    """测试 search_keyword"""
    from db import search_keyword
    records = search_keyword("午")
    assert isinstance(records, list)


def test_list_recent():
    """测试 list_recent"""
    from db import list_recent
    records = list_recent(5)
    assert isinstance(records, list)
    assert len(records) <= 5


def test_get_by_id():
    """测试 get_by_id"""
    from db import insert_record, get_by_id
    result = insert_record("购物", -100.0, "2026-05-23 15:00:00", note="测试")
    record = get_by_id(result['id'])
    assert record is not None
    assert record['category'] == "购物"


def test_get_by_id_not_found():
    """测试 get_by_id 不存在的 ID"""
    from db import get_by_id
    record = get_by_id(999999)
    assert record is None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
```

- [ ] **Step 2: 运行测试确认当前代码能通过基础测试**

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 -m pytest test_db.py -v`
Expected: 部分测试通过（list_today 等依赖 query.py 的会失败，因为还没合并）

- [ ] **Step 3: 重写 db.py**

```python
"""
数据库操作模块
负责：初始化、写入、查询（合并原 query.py 的查询函数）
"""

import sqlite3
import os
from datetime import date
from pathlib import Path

# ── 路径配置 ─────────────────────────────────────────────────────────────────

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "biscuit_accountant.db"


def _find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 父目录 > 技能目录"""
    # 1. 环境变量（最高优先级）
    env_path = os.environ.get('SKILLS_DB_PATH')
    if env_path:
        p = Path(env_path) / db_filename
        if p.exists():
            return p
    # 2. 父目录层层找 .db 文件夹
    for parent in skill_dir.parents:
        db_dir = parent / ".db"
        if db_dir.is_dir():
            p = db_dir / db_filename
            if p.exists():
                return p
    # 3. 技能目录下 .db 子目录（默认 fallback）
    default_db_dir = skill_dir / ".db"
    default_db_dir.mkdir(exist_ok=True)
    return default_db_dir / db_filename


DB_PATH = _find_db_path(SKILL_DIR, DB_FILENAME)

TABLE_NAME = "bills"

# ── 数据库初始化 ─────────────────────────────────────────────────────────────

def init_db():
    """初始化SQLite数据库"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            time TEXT NOT NULL,
            amount REAL NOT NULL,
            account TEXT DEFAULT '',
            ledger TEXT DEFAULT '生活',
            currency TEXT DEFAULT '人民币',
            note TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_bills_time ON {TABLE_NAME}(time)")
    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_bills_category ON {TABLE_NAME}(category)")
    conn.commit()
    return conn

# ── 写入数据库 ────────────────────────────────────────────────────────────────

def insert_record(category: str, amount: float, time_str: str,
                 account: str = "", ledger: str = "生活",
                 currency: str = "人民币", note: str = "") -> dict:
    """写入数据库"""
    conn = init_db()
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {TABLE_NAME} (category, time, amount, account, ledger, currency, note)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (category, time_str, amount, account, ledger, currency, note))
        conn.commit()
        record_id = cursor.lastrowid
        return {"id": record_id, "category": category, "time": time_str, "amount": amount}
    finally:
        conn.close()


def add_bill(category: str, amount: float, time_str: str,
           account: str = "", ledger: str = "生活",
           currency: str = "人民币", note: str = "") -> dict:
    """添加账单记录（只写 SQLite）"""
    result = insert_record(category, amount, time_str, account, ledger, currency, note)
    return {
        "success": True, "id": result['id'],
        "category": category, "time": time_str, "amount": amount,
        "account": account, "ledger": ledger, "currency": currency, "note": note,
    }

# ── 读取记录 ──────────────────────────────────────────────────────────────────

def fetch_all(category: str = None, from_time: str = None, to_time: str = None,
             keyword: str = None, limit: int = None) -> list:
    """
    通用查询接口
    - category: 按分类筛选
    - from_time / to_time: 时间范围
    - keyword: 备注关键词搜索
    - limit: 限制返回条数
    """
    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        conditions = []
        params = []

        if from_time:
            conditions.append("time >= ?")
            params.append(from_time)
        if to_time:
            conditions.append("time <= ?")
            params.append(to_time)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if keyword:
            conditions.append("note LIKE ?")
            params.append(f"%{keyword}%")

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        query = f"SELECT * FROM {TABLE_NAME}{where_clause} ORDER BY time DESC"
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_by_id(record_id: int) -> dict:
    """按ID查询单条记录"""
    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

# ── 便捷查询函数（合并自原 query.py）────────────────────────────────────────

def list_today() -> list:
    """查询今日所有记录"""
    today_str = date.today().strftime("%Y-%m-%d")
    start = f"{today_str} 00:00:00"
    end = f"{today_str} 23:59:59"
    return fetch_all(from_time=start, to_time=end)


def list_date(date_str: str) -> list:
    """查询指定日期所有记录"""
    start = f"{date_str} 00:00:00"
    end = f"{date_str} 23:59:59"
    return fetch_all(from_time=start, to_time=end)


def list_date_range(from_date: str, to_date: str) -> list:
    """查询日期范围记录"""
    if not from_date or not to_date:
        raise ValueError("list_date_range requires both from_date and to_date")
    start = f"{from_date} 00:00:00"
    end = f"{to_date} 23:59:59"
    return fetch_all(from_time=start, to_time=end)


def list_by_category(category: str) -> list:
    """按分类查询所有记录"""
    return fetch_all(category=category)


def search_keyword(keyword: str) -> list:
    """搜索备注关键词"""
    return fetch_all(keyword=keyword)


def list_recent(limit: int = 10) -> list:
    """查询最近N条记录"""
    return fetch_all(limit=limit)
```

- [ ] **Step 4: 运行测试确认全部通过**

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 -m pytest test_db.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 删除 query.py 和 __init__.py**

```bash
rm scripts/query.py scripts/__init__.py
```

- [ ] **Step 6: Commit**

```bash
git add scripts/db.py scripts/test_db.py
git rm scripts/query.py scripts/__init__.py
git commit -m "refactor(db): merge query.py into db.py, remove daily file logic

- Merge 6 query functions from query.py into db.py
- Remove write_daily_bill_file and BILLS_DIR/BILLS_FILE
- Fix path lookup order: env → parent → skill dir
- Add try/finally for connection management
- Use parameterized LIMIT in fetch_all
- Remove redundant DB_DIR alias
- Remove module-level date.today()
- Add test_db.py"
```

---

### Task 2: 修复 analyze.py

**Files:**
- Modify: `scripts/analyze.py`
- Modify: `scripts/test_db.py`（追加 analyze 测试）

- [ ] **Step 1: 追加 analyze 测试到 test_db.py**

在 `test_db.py` 末尾追加：

```python
def test_get_today_summary():
    """测试今日摘要"""
    from analyze import get_today_summary
    result = get_today_summary()
    assert 'date' in result
    assert 'count' in result
    assert 'expense' in result
    assert 'income' in result
    assert 'net' in result


def test_monthly_summary():
    """测试月度汇总"""
    from analyze import monthly_summary
    result = monthly_summary("2026-05")
    assert 'month' in result
    assert 'categories' in result
    assert 'expense' in result
    assert 'income' in result
    assert 'net' in result


def test_compare_periods_week():
    """测试周对比"""
    from analyze import compare_periods
    result = compare_periods("week")
    assert result['period'] == 'week'
    assert 'this' in result
    assert 'last' in result
    assert 'change' in result


def test_compare_periods_month():
    """测试月对比"""
    from analyze import compare_periods
    result = compare_periods("month")
    assert result['period'] == 'month'


def test_compare_periods_invalid():
    """测试无效周期"""
    from analyze import compare_periods
    result = compare_periods("year")
    assert 'error' in result


def test_get_category_breakdown():
    """测试分类明细"""
    from analyze import get_category_breakdown
    result = get_category_breakdown()
    assert 'categories' in result
    assert 'grand_total' in result
    assert 'category_pct' in result
```

- [ ] **Step 2: 运行 analyze 测试**

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 -m pytest test_db.py::test_get_today_summary test_db.py::test_monthly_summary -v`
Expected: 当前代码应该能通过（analyze.py 的函数不依赖 query.py）

- [ ] **Step 3: 重写 analyze.py**

```python
"""
分析模块
负责：今日摘要、月度汇总、周期对比
"""

import sys
from pathlib import Path
_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from datetime import date, timedelta
import sqlite3

import db as db_module
init_db = db_module.init_db
TABLE_NAME = db_module.TABLE_NAME


def _get_totals(from_time: str, to_time: str) -> dict:
    """获取指定时间范围的支出/收入汇总"""
    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT
                COUNT(*) as count,
                SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
                SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income
            FROM {TABLE_NAME}
            WHERE time >= ? AND time <= ?
        """, (from_time, to_time))

        row = cursor.fetchone()
        return {
            "count": row['count'] or 0,
            "expense": row['expense'] or 0,
            "income": row['income'] or 0,
            "net": (row['income'] or 0) - (row['expense'] or 0)
        }
    finally:
        conn.close()


def get_today_summary() -> dict:
    """获取今日摘要"""
    today_str = date.today().strftime("%Y-%m-%d")
    start = f"{today_str} 00:00:00"
    end = f"{today_str} 23:59:59"
    totals = _get_totals(start, end)
    totals["date"] = today_str
    return totals


def get_date_summary(date_str: str) -> dict:
    """获取指定日期的摘要"""
    start = f"{date_str} 00:00:00"
    end = f"{date_str} 23:59:59"
    totals = _get_totals(start, end)
    totals["date"] = date_str
    return totals


def monthly_summary(month: str) -> dict:
    """月度汇总（YYYY-MM格式）"""
    year_int = int(month.split("-")[0])
    month_int = int(month.split("-")[1])

    # 计算下月初
    if month_int == 12:
        next_month_str = f"{year_int + 1}-01-01"
    else:
        next_month_str = f"{year_int}-{month_int + 1:02d}-01"

    start_str = f"{month}-01 00:00:00"
    next_month_start = f"{next_month_str} 00:00:00"

    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT category,
                   SUM(ABS(amount)) as total,
                   COUNT(*) as count
            FROM {TABLE_NAME}
            WHERE time >= ? AND time < ? AND amount < 0
            GROUP BY category
            ORDER BY total DESC
        """, (start_str, next_month_start))

        rows = cursor.fetchall()
        totals = _get_totals(start_str, next_month_start)

        return {
            "month": month,
            "categories": [dict(row) for row in rows],
            "expense": totals["expense"],
            "income": totals["income"],
            "net": totals["net"]
        }
    finally:
        conn.close()


def compare_periods(period: str = "week") -> dict:
    """
    周期对比
    - period: "week" (本周 vs 上周) 或 "month" (本月 vs 上月)
    """
    today = date.today()

    if period == "week":
        this_week_start = today - timedelta(days=today.weekday())
        last_week_start = this_week_start - timedelta(days=7)
        last_week_end = this_week_start - timedelta(seconds=1)

        this_start_str = this_week_start.strftime("%Y-%m-%d 00:00:00")
        last_start_str = last_week_start.strftime("%Y-%m-%d 00:00:00")
        last_end_str = last_week_end.strftime("%Y-%m-%d 23:59:59")

        this_totals = _get_totals(this_start_str, f"{today.strftime('%Y-%m-%d')} 23:59:59")
        last_totals = _get_totals(last_start_str, last_end_str)

        return {
            "period": "week",
            "this": {**this_totals, "label": f"本周 ({this_week_start.strftime('%m/%d')} ~ 今天)"},
            "last": {**last_totals, "label": f"上周 ({last_week_start.strftime('%m/%d')} ~ {last_week_end.strftime('%m/%d')})"},
            "change": {
                "expense_diff": this_totals["expense"] - last_totals["expense"],
                "expense_pct": ((this_totals["expense"] - last_totals["expense"]) / last_totals["expense"] * 100) if last_totals["expense"] else 0
            }
        }

    elif period == "month":
        this_month = today.strftime("%Y-%m")
        this_year = today.year
        this_month_num = today.month

        if this_month_num == 1:
            last_year = this_year - 1
            last_month = 12
        else:
            last_year = this_year
            last_month = this_month_num - 1

        last_month_str = f"{last_year}-{last_month:02d}"

        this_summary = monthly_summary(this_month)
        last_summary = monthly_summary(last_month_str)

        return {
            "period": "month",
            "this": {**this_summary, "label": f"{this_month}月"},
            "last": {**last_summary, "label": f"{last_month_str}月"},
            "change": {
                "expense_diff": this_summary["expense"] - last_summary["expense"],
                "expense_pct": ((this_summary["expense"] - last_summary["expense"]) / last_summary["expense"] * 100) if last_summary["expense"] else 0
            }
        }

    else:
        return {"error": f"不支持的周期: {period}，可选: week, month"}


def get_category_breakdown(from_date: str = None, to_date: str = None) -> dict:
    """获取分类支出明细（不指定日期范围时默认本月）"""
    today = date.today()
    if not from_date:
        from_date = f"{today.year}-{today.month:02d}-01"
    if not to_date:
        to_date = today.strftime("%Y-%m-%d")

    # 计算 to_date 的下一天（用 < 而非 <=）
    to_date_obj = date.fromisoformat(to_date) + timedelta(days=1)
    next_day_str = to_date_obj.strftime("%Y-%m-%d")

    conn = init_db()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT category,
                   SUM(ABS(amount)) as total,
                   COUNT(*) as count,
                   AVG(ABS(amount)) as avg
            FROM {TABLE_NAME}
            WHERE time >= ? AND time < ? AND amount < 0
            GROUP BY category
            ORDER BY total DESC
        """, (f"{from_date} 00:00:00", f"{next_day_str} 00:00:00"))

        rows = cursor.fetchall()

        grand_total = sum(row['total'] for row in rows)

        return {
            "from": from_date,
            "to": to_date,
            "categories": [dict(row) for row in rows],
            "grand_total": grand_total,
            "category_pct": [
                {**dict(row), "pct": (row['total'] / grand_total * 100) if grand_total else 0}
                for row in rows
            ]
        }
    finally:
        conn.close()
```

- [ ] **Step 4: 运行全部测试**

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 -m pytest test_db.py -v`
Expected: 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/analyze.py scripts/test_db.py
git commit -m "fix(analyze): remove module-level date.today(), simplify month-end calc

- Use date.today() inside functions instead of module-level
- Simplify month-end: use time < next_month instead of <= 23:59:59
- Simplify to_date: use time < next_day instead of <= 23:59:59
- Add try/finally for connection management
- Add analyze tests to test_db.py"
```

---

### Task 3: 修复 record_bill.py

**Files:**
- Modify: `scripts/record_bill.py`

- [ ] **Step 1: 更新 record_bill.py**

```python
#!/usr/bin/env python3
"""
饼干记账 CLI v2.1（优化版）

使用方法：
    python3 record_bill.py add --category 餐饮 --amount -35
    python3 record_bill.py list
    python3 record_bill.py list --date 2026-05-01
    python3 record_bill.py list --from 2026-05-01 --to 2026-05-10
    python3 record_bill.py list --category 餐饮
    python3 record_bill.py search "单车"
    python3 record_bill.py summary
    python3 record_bill.py monthly --month 2026-05
    python3 record_bill.py compare
    python3 record_bill.py recent --limit 10
    python3 record_bill.py breakdown --from 2026-05-01 --to 2026-05-31
"""

import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from db import (
    add_bill,
    list_today, list_date, list_date_range,
    list_by_category, search_keyword, list_recent
)
from analyze import (
    get_today_summary, monthly_summary,
    compare_periods, get_category_breakdown
)


def _format_record(r: dict) -> str:
    """格式化单条记录"""
    time = r.get('time', 'N/A')
    category = r.get('category', 'N/A')
    amount = r.get('amount', 0)
    note = r.get('note', '')
    return f"{time} | {category} | {amount:.2f} | {note}"


def cmd_add(args):
    """添加账单"""
    time_str = args.time or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = add_bill(
        category=args.category,
        amount=args.amount,
        time_str=time_str,
        account=args.account or "",
        ledger=args.ledger or "生活",
        currency=args.currency or "人民币",
        note=args.note or ""
    )
    print(f"✓ 已记录：{result['category']} {result['amount']:.2f}")
    return result


def cmd_list(args):
    """查询记录"""
    records = []

    if args.date:
        records = list_date(args.date)
    elif args.from_date and args.to_date:
        records = list_date_range(args.from_date, args.to_date)
    elif args.from_date or args.to_date:
        print("错误：--from 和 --to 必须同时指定")
        return
    elif args.category:
        records = list_by_category(args.category)
    else:
        records = list_today()

    if not records:
        print("(无记录)")
        return

    for r in records:
        print(_format_record(r))


def cmd_search(args):
    """搜索备注关键词"""
    records = search_keyword(args.keyword)
    if not records:
        print(f"(无匹配 '{args.keyword}' 的记录)")
        return
    print(f"=== 搜索结果: '{args.keyword}' ({len(records)}条) ===")
    for r in records:
        print(_format_record(r))


def cmd_summary(args):
    """今日摘要"""
    result = get_today_summary()
    print(f"今日 {result.get('date', 'N/A')}")
    print(f"记录数: {result.get('count', 0)}")
    print(f"支出: {result.get('expense', 0):.2f}")
    print(f"收入: {result.get('income', 0):.2f}")
    print(f"净额: {result.get('net', 0):.2f}")


def cmd_monthly(args):
    """月度汇总"""
    result = monthly_summary(args.month)
    print(f"=== {args.month} 月度汇总 ===")
    print(f"支出: {result.get('expense', 0):.2f}")
    print(f"收入: {result.get('income', 0):.2f}")
    print(f"净额: {result.get('net', 0):.2f}")
    categories = result.get('categories', [])
    if categories:
        print("\n分类明细:")
        for c in categories:
            print(f"  {c.get('category', 'N/A')}: {c.get('total', 0):.2f} ({c.get('count', 0)}笔)")


def cmd_compare(args):
    """周期对比"""
    period = args.period or "week"
    result = compare_periods(period)

    if "error" in result:
        print(result["error"])
        return

    label = "周" if period == "week" else "月"
    print(f"=== {label}度对比 ===\n")
    this = result.get('this', {})
    last = result.get('last', {})
    print(f"{this.get('label', 'N/A')}")
    print(f"  支出: {this.get('expense', 0):.2f}")
    print(f"  收入: {this.get('income', 0):.2f}")
    print(f"  净额: {this.get('net', 0):.2f}")
    print(f"\n{last.get('label', 'N/A')}")
    print(f"  支出: {last.get('expense', 0):.2f}")
    print(f"  收入: {last.get('income', 0):.2f}")
    print(f"  净额: {last.get('net', 0):.2f}")
    print(f"\n变化:")
    change = result.get('change', {})
    diff = change.get('expense_diff', 0)
    pct = change.get('expense_pct', 0)
    direction = "↑" if diff > 0 else "↓" if diff < 0 else "→"
    print(f"  支出 {direction} {abs(diff):.2f} ({abs(pct):.1f}%)")


def cmd_recent(args):
    """最近N条"""
    limit = args.limit or 10
    records = list_recent(limit)
    if not records:
        print("(无记录)")
        return
    print(f"=== 最近 {len(records)} 条 ===")
    for r in records:
        print(_format_record(r))


def cmd_breakdown(args):
    """分类明细"""
    from_date = args.from_date
    to_date = args.to_date
    result = get_category_breakdown(from_date, to_date)

    print(f"=== 分类支出明细 ===")
    if from_date or to_date:
        print(f"期间: {result.get('from', 'N/A')} ~ {result.get('to', 'N/A')}")
    print(f"总支出: {result.get('grand_total', 0):.2f}\n")

    for c in result.get('category_pct', []):
        print(f"  {c.get('category', 'N/A')}: {c.get('total', 0):.2f} ({c.get('pct', 0):.1f}%) [{c.get('count', 0)}笔, 均{c.get('avg', 0):.1f}]")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="饼干记账 v2.1")

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # add
    p = subparsers.add_parser('add', help='添加账单')
    p.add_argument('--category', required=True, help='分类')
    p.add_argument('--amount', required=True, type=float, help='金额（负数为支出）')
    p.add_argument('--time', default=None, help='时间 YYYY-MM-DD HH:MM:SS')
    p.add_argument('--account', default='', help='账户')
    p.add_argument('--ledger', default='生活', help='账本')
    p.add_argument('--currency', default='人民币', help='货币')
    p.add_argument('--note', default='', help='备注')

    # list
    p = subparsers.add_parser('list', help='查询记录')
    p.add_argument('--date', default=None, help='日期 YYYY-MM-DD')
    p.add_argument('--from', dest='from_date', default=None, help='开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='to_date', default=None, help='结束日期 YYYY-MM-DD')
    p.add_argument('--category', default=None, help='按分类筛选')

    # search
    p = subparsers.add_parser('search', help='搜索备注关键词')
    p.add_argument('keyword', help='关键词')

    # summary
    subparsers.add_parser('summary', help='今日摘要')

    # monthly
    p = subparsers.add_parser('monthly', help='月度汇总')
    p.add_argument('--month', required=True, help='月份 YYYY-MM')

    # compare
    p = subparsers.add_parser('compare', help='周期对比')
    p.add_argument('--period', default='week', choices=['week', 'month'], help='对比周期 (week/month)')

    # recent
    p = subparsers.add_parser('recent', help='最近N条')
    p.add_argument('--limit', type=int, default=10, help='条数')

    # breakdown
    p = subparsers.add_parser('breakdown', help='分类明细')
    p.add_argument('--from', dest='from_date', default=None, help='开始日期 YYYY-MM-DD')
    p.add_argument('--to', dest='to_date', default=None, help='结束日期 YYYY-MM-DD')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        'add': cmd_add,
        'list': cmd_list,
        'search': cmd_search,
        'summary': cmd_summary,
        'monthly': cmd_monthly,
        'compare': cmd_compare,
        'recent': cmd_recent,
        'breakdown': cmd_breakdown,
    }

    cmd = commands.get(args.command)
    if cmd:
        cmd(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 语法检查**

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账" && python3 -m py_compile scripts/record_bill.py`
Expected: 无输出（语法正确）

- [ ] **Step 3: 验证 import 链**

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 -c "from db import list_today, list_date, list_date_range, list_by_category, search_keyword, list_recent, fetch_all, get_by_id, add_bill; print('OK')"`
Expected: `OK`

- [ ] **Step 4: 验证 CLI 子命令**

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py --help`
Expected: 显示 8 个子命令

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py summary`
Expected: 显示今日摘要（可能为 0）

- [ ] **Step 5: Commit**

```bash
git add scripts/record_bill.py
git commit -m "fix(record_bill): update imports from db, add defensive access

- Import query functions directly from db instead of query module
- Use .get() for all dict access in _format_record and cmd_summary
- Update version to v2.1"
```

---

### Task 4: 重写 SKILL.md

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: 重写 SKILL.md**

```markdown
---
name: 饼干记账
description: 记账技能，支持文字/图片记账、查询统计、分类分析。触发词：记账、花了、收入、账单。
---

## 操作规范（强制）

- 所有数据操作通过 CLI（`scripts/record_bill.py`），禁止直连数据库
- 只读操作（查询/统计）不需确认，写入操作（记账）需用户确认
- 不支持删除和修改已有记录
- 金额必须明确，不能猜测

---

## 安装与配置

### 依赖

- Python 3.x（系统自带 sqlite3）

### 配置项

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `SKILLS_DB_PATH` | 数据库目录 | 技能目录下 `.db/` |

### 一键安装

```
请帮我初始化饼干记账技能：
1. 确认 Python 3.x 已安装
2. 执行 python3 scripts/record_bill.py summary 验证数据库自动初始化
```

---

## 功能概述

- **文字记账**：解析自然语言，提取金额、分类、备注
- **图片记账**：看图识别账单金额，用户确认后记录
- **查询统计**：今日/指定日期/日期范围/分类查询
- **分析报表**：月度汇总、周期对比、分类明细

---

## 使用流程

### Step 1：判断输入类型

| 输入类型 | 处理方式 |
|----------|----------|
| 纯文字 | 直接解析金额、分类、备注 |
| 纯图片（无文字） | 识别图片内容，展示识别结果，用户确认后记账 |
| 图片+文字 | 看图判断金额，用户文字作为备注或分类提示 |

### Step 2：解析账单信息

提取字段：

| 字段 | 说明 |
|------|------|
| `amount` | 金额（元，负数为支出，正数为收入） |
| `category` | 分类，参考 `references/categories.md` |
| `time` | 时间（默认当前时间） |
| `note` | 备注（可选） |

**文字解析关键词：**
- "花了 / 付了 / 消费 / 支出" → 负数金额
- "收到 / 收入 / 进账" → 正数金额

### Step 3：图片识别（如有图片）

**直接观察图片内容，按以下优先级判断金额：**

1. 「实付 / 实收 / 已支付 / 需付 / 支付金额」→ 用户最终付出的钱
2. 「合计 / 总计 / 总额 / 应付」→ 订单总价
3. 忽略：单品价格、优惠减免、配送费、税额、找零
4. 若有多个候选，选语义最接近「最终实际支付」的数字
5. 无法判断时，描述看到的内容并请用户确认金额

### Step 4：执行记录

```bash
python3 scripts/record_bill.py add \
  --category 餐饮 \
  --amount -35.0 \
  --time "2026-05-23 12:30:00" \
  --note "午饭"
```

### Step 5：回复用户

```
✓ 已记录：餐饮 -35.00
```

---

## 命令行功能

### 添加记录
```bash
python3 scripts/record_bill.py add --category 餐饮 --amount -35.0 --note "午饭"
```

### 查询今日
```bash
python3 scripts/record_bill.py list
```

### 查询指定日期
```bash
python3 scripts/record_bill.py list --date 2026-05-23
```

### 查询日期范围
```bash
python3 scripts/record_bill.py list --from 2026-05-01 --to 2026-05-31
```

### 按分类查询
```bash
python3 scripts/record_bill.py list --category 餐饮
```

### 搜索备注
```bash
python3 scripts/record_bill.py search "午饭"
```

### 今日摘要
```bash
python3 scripts/record_bill.py summary
```

### 月度汇总
```bash
python3 scripts/record_bill.py monthly --month 2026-05
```

### 周期对比
```bash
python3 scripts/record_bill.py compare --period week
python3 scripts/record_bill.py compare --period month
```

### 最近N条
```bash
python3 scripts/record_bill.py recent --limit 10
```

### 分类明细
```bash
python3 scripts/record_bill.py breakdown
python3 scripts/record_bill.py breakdown --from 2026-05-01 --to 2026-05-31
```

---

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| 图片模糊/看不清金额 | 描述看到的内容，请用户确认 |
| 图片非账单 | 告知用户并询问是否手动输入 |
| 未指定分类 | 根据内容推断，告知用户可纠正 |
| 金额不明确 | 请用户确认，不自动猜测 |

---

## AI 触发指引

### 触发场景：用户提到记账/消费/收入

触发词：
- "记账"、"花了"、"付了"、"消费"
- "收到钱"、"进账"、"收入"
- 发截图/账单图片（无需文字，AI 自动识别）

操作步骤：
1. 解析用户输入，提取：分类、时间、金额、备注
2. 执行：`python3 scripts/record_bill.py add --category <分类> --amount <金额> --time "<时间>" --note "<备注>"`
3. 返回确认信息

### 触发场景：用户要查看账单

触发词：
- "今天花了多少"、"查一下账单"
- "今日支出"、"今日收入"

操作步骤：
1. 执行：`python3 scripts/record_bill.py summary`

### 触发场景：用户要查历史

触发词：
- "上周花了多少"、"上月账单"
- "这个月消费"

操作步骤：
1. 执行：`python3 scripts/record_bill.py monthly --month <YYYY-MM>`
```

- [ ] **Step 2: 验证 Markdown 格式**

用编辑器打开确认格式正确，无语法错误。

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "docs(SKILL): full rewrite per SKILL-开发规范

- Unify name to 饼干记账
- Remove all hardcoded absolute paths
- Add one-click install prompt
- Add core principles section
- Complete all 8 CLI commands
- Remove Lint and 联动 sections
- Simplify description to <50 chars"
```

---

### Task 5: 修复 config-cookie-accounting.ts

**Files:**
- Modify: `config-cookie-accounting.ts`

- [ ] **Step 1: 重写 config-cookie-accounting.ts**

在文件顶部（第1行之前）插入类型定义，并修改收入分类和注释。

完整文件内容：

```typescript
// config-cookie-accounting.ts
// SkillBoard 数据层配置文件 - 饼干记账
// 数据库文件：biscuit_accountant.db

interface SkillField {
  name: string;
  type: string;
  label: string;
  primaryKey?: boolean;
  visible?: boolean;
  nullable?: boolean;
  format?: string;
  unit?: string;
  default?: string;
  options?: string[];
}

interface SkillTable {
  name: string;
  fields: SkillField[];
}

interface SkillQuery {
  id: string;
  label: string;
  sql: string;
  params?: Array<{
    name: string;
    type: string;
    label: string;
    options?: Array<{ label: string; value: string }>;
  }>;
  chartType?: string;
  chartConfig?: {
    colorScheme?: string[];
  };
}

interface SkillAction {
  id: string;
  label: string;
  type: string;
  targetTable: string;
  fields: Array<{
    field: string;
    required?: boolean;
    source: string;
    prompt?: string;
    value?: string;
    format?: string;
    unit?: string;
    options?: string[];
  }>;
}

interface SkillView {
  id: string;
  label: string;
  icon: string;
  components: Record<string, any>;
}

interface SkillConfig {
  meta: {
    name: string;
    label: string;
    icon: string;
    description: string;
    dbFiles: string[];
  };
  schema: { tables: SkillTable[] };
  queries: SkillQuery[];
  actions: SkillAction[];
  views: SkillView[];
}

export const CookieAccountingConfig: SkillConfig = {
  // ── 1. meta（元数据）─────────────────────────────────────────
  meta: {
    name: "cookie-accounting",
    label: "饼干记账",
    icon: "Cookie",
    description: "记录饼干购买与消耗，支持日/周/月统计和分类分析",
    dbFiles: ["biscuit_accountant.db"],
  },

  // ── 2. schema（数据库结构）──────────────────────────────────
  schema: {
    tables: [
      {
        name: "bills",
        fields: [
          { name: "id",       type: "INTEGER", label: "ID",         primaryKey: true, visible: false },
          { name: "category", type: "TEXT",    label: "分类",        nullable: false,
            options: ["餐饮", "购物", "交通", "娱乐", "医疗", "住房", "教育", "通讯", "其他",
                      "工资", "奖金", "兼职", "投资", "其他"] },
          { name: "time",     type: "TEXT",    label: "时间",        nullable: false, format: "datetime" },
          { name: "amount",   type: "REAL",    label: "金额",        nullable: false, format: "currency", unit: "元" },
          { name: "account",  type: "TEXT",    label: "账户",        default: "" },
          { name: "ledger",   type: "TEXT",    label: "账本",        default: "生活" },
          { name: "currency", type: "TEXT",    label: "货币",        default: "人民币" },
          { name: "note",     type: "TEXT",    label: "备注",        default: "" },
          { name: "created_at", type: "TEXT", label: "创建时间",    visible: false },
        ],
      },
    ],
  },

  // ── 3. queries（预设查询）───────────────────────────────────
  queries: [
    // 今日记录
    {
      id: "daily-records",
      label: "今日记录",
      sql: "SELECT id, category, time, amount, note FROM bills WHERE time >= '{{date}} 00:00:00' AND time <= '{{date}} 23:59:59' ORDER BY time DESC",
      params: [
        { name: "date", type: "date", label: "日期" },
      ],
    },

    // 月度支出汇总（柱状图）
    {
      id: "monthly-summary",
      label: "月度支出汇总",
      sql: `SELECT
              category,
              SUM(ABS(amount)) as total,
              COUNT(*) as count
            FROM bills
            WHERE time >= '{{month}}-01 00:00:00'
              AND time < '{{month_end}} 00:00:00'
              AND amount < 0
            GROUP BY category
            ORDER BY total DESC`,
      params: [
        { name: "month",     type: "month", label: "月份" },
        { name: "month_end", type: "date",  label: "月末日期" },
      ],
      chartType: "bar",
      chartConfig: {
        colorScheme: ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE"],
      },
    },

    // 分类支出明细（环形图）
    {
      id: "category-breakdown",
      label: "分类分析",
      sql: `SELECT
              category,
              SUM(ABS(amount)) as total,
              COUNT(*) as count,
              AVG(ABS(amount)) as avg
            FROM bills
            WHERE time >= '{{from}} 00:00:00'
              AND time <= '{{to}} 23:59:59'
              AND amount < 0
            GROUP BY category
            ORDER BY total DESC`,
      params: [
        { name: "from", type: "date", label: "开始日期" },
        { name: "to",   type: "date", label: "结束日期" },
      ],
      chartType: "doughnut",
      chartConfig: {
        colorScheme: ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F", "#BB8FCE"],
      },
    },

    // 收支总览（月度计数/支出/收入/净额）
    // 返回标量值，适合用 card 组件展示
    {
      id: "monthly-overview",
      label: "收支总览",
      sql: `SELECT
              COUNT(*) as count,
              SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as expense,
              SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as income,
              SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END)
              - SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as net
            FROM bills
            WHERE time >= '{{month}}-01 00:00:00'
              AND time < '{{month_end}} 00:00:00'`,
      params: [
        { name: "month",     type: "month", label: "月份" },
        { name: "month_end", type: "date",  label: "月末日期" },
      ],
    },

    // 周期对比（本周 vs 上周 / 本月 vs 上月）
    // period 参数由前端用于决定调用两次本查询的日期范围，SQL 中不直接使用
    {
      id: "period-compare",
      label: "周期对比",
      sql: `SELECT
              CASE WHEN amount < 0 THEN 'expense' ELSE 'income' END as type,
              SUM(ABS(amount)) as total,
              COUNT(*) as count
            FROM bills
            WHERE time >= '{{from}} 00:00:00'
              AND time <= '{{to}} 23:59:59'
            GROUP BY type`,
      params: [
        { name: "from",   type: "date",  label: "开始日期" },
        { name: "to",     type: "date",  label: "结束日期" },
        { name: "period", type: "select", label: "周期",
          options: [
            { label: "本周 vs 上周", value: "week" },
            { label: "本月 vs 上月", value: "month" },
          ],
        },
      ],
      chartType: "bar",
    },

    // 最近记录
    {
      id: "recent-records",
      label: "最近记录",
      sql: "SELECT id, category, time, amount, note FROM bills ORDER BY time DESC LIMIT {{limit}}",
      params: [
        { name: "limit", type: "select", label: "条数",
          options: [
            { label: "10条", value: "10" },
            { label: "20条", value: "20" },
            { label: "50条", value: "50" },
          ],
        },
      ],
    },

    // 关键词搜索
    {
      id: "keyword-search",
      label: "关键词搜索",
      sql: "SELECT id, category, time, amount, note FROM bills WHERE note LIKE '%' || '{{keyword}}' || '%' ORDER BY time DESC",
      params: [
        { name: "keyword", type: "text", label: "关键词" },
      ],
    },
  ],

  // ── 4. actions（操作定义）──────────────────────────────────
  actions: [
    {
      id: "add-record",
      label: "新增记账",
      type: "insert",
      targetTable: "bills",
      fields: [
        {
          field: "category",
          required: true,
          source: "user-input",
          prompt: "选择分类",
          options: ["餐饮", "购物", "交通", "娱乐", "医疗", "住房", "教育", "通讯", "其他",
                    "工资", "奖金", "兼职", "投资", "其他"],
        },
        {
          field: "time",
          required: true,
          source: "user-input",
          prompt: "时间（格式：YYYY-MM-DD HH:MM:SS，留空填当前时间）",
          format: "datetime",
        },
        {
          field: "amount",
          required: true,
          source: "user-input",
          prompt: "输入金额（负数为支出，正数为收入）",
          format: "currency",
          unit: "元",
        },
        {
          field: "account",
          source: "user-input",
          prompt: "账户（可选）",
        },
        {
          field: "ledger",
          source: "fixed",
          value: "生活",
        },
        {
          field: "currency",
          source: "fixed",
          value: "人民币",
        },
        {
          field: "note",
          source: "user-input",
          prompt: "备注（可选）",
        },
      ],
    },
  ],

  // ── 5. views（视图定义）────────────────────────────────────
  views: [
    { id: "daily",    label: "每日记录",  icon: "CalendarBlank",
      components: { table: { queryId: "daily-records",    sortable: true,  pageSize: 20 } } },
    { id: "monthly",  label: "月度统计",  icon: "ChartBar",
      components: { chart: { queryId: "monthly-summary" } } },
    { id: "overview", label: "收支总览",  icon: "Coins",
      components: { chart: { queryId: "monthly-overview" } } },
    { id: "category", label: "分类分析",  icon: "ChartPieSlice",
      components: { chart: { queryId: "category-breakdown" } } },
    { id: "compare",  label: "周期对比",  icon: "ArrowsLeftRight",
      components: { chart: { queryId: "period-compare" } } },
    { id: "recent",   label: "最近记录",  icon: "Clock",
      components: { table: { queryId: "recent-records",   sortable: true,  pageSize: 10 } } },
    { id: "search",   label: "关键词搜索", icon: "MagnifyingGlass",
      components: { table: { queryId: "keyword-search",   sortable: true,  pageSize: 20 } } },
    { id: "add",      label: "新增记账",  icon: "Plus",
      components: { form: { actionId: "add-record" } } },
  ],
};
```

- [ ] **Step 2: Commit**

```bash
git add config-cookie-accounting.ts
git commit -m "fix(config): add SkillConfig types, fix income options, add comments

- Add inline TypeScript interface definitions for SkillConfig
- Add missing income category '其他' to options
- Add comment explaining period param is frontend-only
- Add comment noting overview returns scalar values
- Simplify month-end calc: use time < next_month instead of <= 23:59:59"
```

---

### Task 6: 修复 .gitignore + 最终验证

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: 更新 .gitignore**

```gitignore
# Python 字节码缓存
__pycache__/
*.py[cod]
*$py.class

# 环境变量文件
.env

# 数据库文件
*.db
```

- [ ] **Step 2: 运行全部测试**

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 -m pytest test_db.py -v`
Expected: 全部 PASS

- [ ] **Step 3: 语法检查全部 Python 文件**

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账" && python3 -m py_compile scripts/db.py && python3 -m py_compile scripts/analyze.py && python3 -m py_compile scripts/record_bill.py`
Expected: 无输出（语法正确）

- [ ] **Step 4: 验证 CLI 全部子命令**

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py --help`
Expected: 显示 8 个子命令

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py add --category 测试 --amount -1.0 --note "验证"`
Expected: `✓ 已记录：测试 -1.00`

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py summary`
Expected: 显示今日摘要

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py list`
Expected: 显示今日记录

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py search "验证"`
Expected: 显示搜索结果

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py monthly --month 2026-05`
Expected: 显示月度汇总

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py compare`
Expected: 显示周对比

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py recent --limit 5`
Expected: 显示最近5条

Run: `cd "D:/2Study/StudyNotes/SKILLS/饼干记账/scripts" && python3 record_bill.py breakdown`
Expected: 显示分类明细

- [ ] **Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: update .gitignore to exclude .db files"
```

- [ ] **Step 6: 清理测试数据**

删除测试中插入的验证记录（可选，或保留作为示例数据）。

- [ ] **Step 7: 最终 Commit（如果有遗漏）**

```bash
git status
```

确认无未提交的变更。
