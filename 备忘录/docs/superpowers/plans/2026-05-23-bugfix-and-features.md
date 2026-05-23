# 备忘录技能 BUG 修复与功能补充计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复提醒机制 BUG，补充缺失场景，确保功能完整闭环

**Architecture:** 使用 notified_at 字段避免重复通知，修复 weekday/日期边界问题，补充 CLI 命令

**Tech Stack:** Python 3.x, SQLite WAL, FTS5

---

## 文件结构

```
备忘录/
├── SKILL.md                    # 主文档
├── script/
│   ├── init.sql               # 数据库初始化（添加 notified_at 字段）
│   ├── memo_cli.py            # CLI 工具（修复 BUG + 新增命令）
│   └── reminder_scheduler.py  # 提醒调度器
└── reference/
    ├── schema.md              # 数据库 schema（更新）
    └── examples.md            # 对话示例（补充场景）
```

---

## Task 1: 修复 init.sql - 添加 notified_at 字段和 WAL

**Files:**
- Modify: `script/init.sql`

- [ ] **Step 1: 添加 WAL 模式**

在文件开头添加：
```sql
PRAGMA journal_mode=WAL;
```

- [ ] **Step 2: 修改 reminders 表，添加 notified_at 字段**

```sql
CREATE TABLE IF NOT EXISTS reminders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    note_id     INTEGER NOT NULL,
    remind_at   TEXT,
    repeat_type TEXT DEFAULT 'none',
    repeat_rule TEXT,
    status      TEXT DEFAULT 'active',
    notified_at TEXT,                            -- 上次通知时间
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE CASCADE
);
```

- [ ] **Step 3: 验证 SQL 语法**

Run: `python -c "import sqlite3; conn = sqlite3.connect(':memory:'); conn.executescript(open('script/init.sql').read()); print('OK')"`

- [ ] **Step 4: Commit**

```bash
git add script/init.sql
git commit -m "fix: init.sql 添加 WAL 和 notified_at 字段"
```

---

## Task 2: 修复 memo_cli.py - weekday 映射和日期边界

**Files:**
- Modify: `script/memo_cli.py`

- [ ] **Step 1: 修复 weekly weekday 映射**

在文件顶部添加辅助函数：
```python
def convert_weekday(user_weekday):
    """将用户输入的 weekday (0=周日) 转换为 Python weekday (0=周一)"""
    # 用户: 0=周日, 1=周一, 2=周二, 3=周三, 4=周四, 5=周五, 6=周六
    # Python: 0=周一, 1=周二, 2=周三, 3=周四, 4=周五, 5=周六, 6=周日
    return (user_weekday + 6) % 7
```

修改 list_due_reminders 函数中的 weekly 部分（约 206-212 行）：
```python
elif rtype == "weekly":
    # "3 09:00"
    parts = rule.split()
    weekday = int(parts[0])
    t = datetime.strptime(parts[1], "%H:%M").time()
    # 计算本周的这一天
    python_weekday = convert_weekday(weekday)
    days_until = (python_weekday - now.weekday()) % 7
    target_date = now.date() + timedelta(days=days_until)
    virt_time = datetime.combine(target_date, t)
```

- [ ] **Step 2: 修复 monthly 日期越界**

修改 list_due_reminders 函数中的 monthly 部分（约 213-224 行）：
```python
elif rtype == "monthly":
    # "15 08:30"
    parts = rule.split()
    day = int(parts[0])
    t = datetime.strptime(parts[1], "%H:%M").time()
    # 安全处理日期边界
    try:
        target_date = now.date().replace(day=day)
    except ValueError:
        # 本月没有这一天（如 2 月 31 日），跳到下个月
        if now.date().month == 12:
            target_date = now.date().replace(year=now.date().year+1, month=1, day=day)
        else:
            target_date = now.date().replace(month=now.date().month+1, day=day)
    if target_date < now.date():
        # 本月已过，计算下个月
        try:
            if target_date.month == 12:
                target_date = target_date.replace(year=target_date.year+1, month=1)
            else:
                target_date = target_date.replace(month=target_date.month+1)
        except ValueError:
            continue
    virt_time = datetime.combine(target_date, t)
```

- [ ] **Step 3: 修复 yearly 闰年问题**

修改 list_due_reminders 函数中的 yearly 部分（约 226-235 行）：
```python
elif rtype == "yearly":
    # "12-25 10:00"
    parts = rule.split()
    md = parts[0]
    t = datetime.strptime(parts[1], "%H:%M").time()
    month, day = map(int, md.split("-"))
    try:
        target_date = now.date().replace(month=month, day=day)
    except ValueError:
        # 2 月 29 日在非闰年，跳过
        continue
    if target_date < now.date():
        try:
            target_date = target_date.replace(year=target_date.year+1)
        except ValueError:
            continue
    virt_time = datetime.combine(target_date, t)
```

- [ ] **Step 4: 验证语法**

Run: `python -m py_compile script/memo_cli.py`

- [ ] **Step 5: Commit**

```bash
git add script/memo_cli.py
git commit -m "fix: 修复 weekday 映射、monthly/yearly 日期边界问题"
```

---

## Task 3: 修复 memo_cli.py - notified_at 避免重复通知

**Files:**
- Modify: `script/memo_cli.py`

- [ ] **Step 1: 修改 list_due_reminders 函数**

修改一次性提醒查询（约 172-185 行）：
```python
# 一次性提醒：只查询 notified_at 为空的
cur = conn.execute("""
    SELECT r.id, r.note_id, r.remind_at, n.content
    FROM reminders r JOIN notes n ON r.note_id = n.id
    WHERE r.status = 'active' AND r.repeat_type = 'none'
      AND r.notified_at IS NULL
      AND r.remind_at BETWEEN ? AND ?
""", (now_str, window_end))
```

修改重复提醒查询（约 188-192 行）：
```python
# 重复提醒：只查询 notified_at 为空或距离现在超过 10 分钟的
cur = conn.execute("""
    SELECT r.id, r.note_id, r.repeat_type, r.repeat_rule, n.content, r.notified_at
    FROM reminders r JOIN notes n ON r.note_id = n.id
    WHERE r.status = 'active' AND r.repeat_type != 'none'
      AND (r.notified_at IS NULL OR r.notified_at <= ?)
""", (now_str,))
```

- [ ] **Step 2: 添加 notified_at 更新逻辑**

在输出 due_items 之前，更新 notified_at：
```python
# 更新通知时间
for item in due_items:
    conn.execute(
        "UPDATE reminders SET notified_at = ? WHERE id = ?",
        (now_str, item["id"])
    )

# 将过期的 active 一次性提醒标记为 dismissed
conn.execute("""
    UPDATE reminders SET status = 'dismissed'
    WHERE status = 'active' AND repeat_type = 'none'
      AND remind_at < ?
""", (now_str,))
conn.commit()
```

- [ ] **Step 3: 验证语法**

Run: `python -m py_compile script/memo_cli.py`

- [ ] **Step 4: Commit**

```bash
git add script/memo_cli.py
git commit -m "fix: 使用 notified_at 避免重复通知"
```

---

## Task 4: 补充 CLI 命令 - 查看笔记详情、按时间搜索、编辑分类

**Files:**
- Modify: `script/memo_cli.py`

- [ ] **Step 1: 添加 get_note 函数**

```python
def get_note(args):
    note_id = args.id
    conn = get_conn()
    try:
        note = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if not note:
            error_json("笔记不存在")
        output_json(dict(note))
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()
```

- [ ] **Step 2: 添加 search_by_date 函数**

```python
def search_by_date(args):
    start = args.start
    end = args.end
    category = args.category
    limit = args.limit or 20
    conn = get_conn()
    try:
        sql = "SELECT * FROM notes WHERE created_at BETWEEN ? AND ?"
        params = [start, end]
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        cur = conn.execute(sql, params)
        rows = [dict(row) for row in cur.fetchall()]
        output_json(rows, message=f"找到 {len(rows)} 条笔记")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()
```

- [ ] **Step 3: 添加 update_category 函数**

```python
def update_category(args):
    note_id = args.id
    category = args.category
    conn = get_conn()
    note = conn.execute("SELECT id FROM notes WHERE id = ?", (note_id,)).fetchone()
    if not note:
        error_json("笔记不存在")
    try:
        conn.execute(
            "UPDATE notes SET category = ?, updated_at = datetime('now','localtime') WHERE id = ?",
            (category, note_id)
        )
        conn.commit()
        output_json({"id": note_id, "category": category}, message="分类已更新")
    except Exception as e:
        error_json(str(e))
    finally:
        conn.close()
```

- [ ] **Step 4: 添加 argparse 子命令**

```python
# get note
p_get = sub.add_parser("get")
p_get.add_argument("id", type=int)

# search by date
p_date = sub.add_parser("search-date")
p_date.add_argument("start", help="开始时间 YYYY-MM-DD")
p_date.add_argument("end", help="结束时间 YYYY-MM-DD")
p_date.add_argument("--category", "-c")
p_date.add_argument("--limit", "-l", type=int)

# update category
p_cat = sub.add_parser("update-category")
p_cat.add_argument("id", type=int)
p_cat.add_argument("category")
```

- [ ] **Step 5: 添加命令分发**

```python
elif args.command == "get":
    get_note(args)
elif args.command == "search-date":
    search_by_date(args)
elif args.command == "update-category":
    update_category(args)
```

- [ ] **Step 6: 验证语法**

Run: `python -m py_compile script/memo_cli.py`

- [ ] **Step 7: 测试新命令**

Run: `python script/memo_cli.py --help`

- [ ] **Step 8: Commit**

```bash
git add script/memo_cli.py
git commit -m "feat: 添加 get、search-date、update-category 命令"
```

---

## Task 5: 更新 schema.md 和 examples.md

**Files:**
- Modify: `reference/schema.md`
- Modify: `reference/examples.md`

- [ ] **Step 1: 更新 schema.md - 添加新字段和命令**

在 reminders 表中添加：
```markdown
| notified_at | TEXT | 上次通知时间 |
```

在 CLI 命令参考中添加：
```markdown
| `get <id>` | 获取笔记详情 | `script/memo_cli.py get 1` |
| `search-date <start> <end> [-c category]` | 按时间搜索 | `script/memo_cli.py search-date 2026-05-01 2026-05-31` |
| `update-category <id> <category>` | 更新分类 | `script/memo_cli.py update-category 1 work` |
```

- [ ] **Step 2: 更新 examples.md - 添加新场景**

添加场景：
```markdown

## 10. 查看笔记详情
**用户**：“看看第一条笔记的内容。”
**系统**：`script/memo_cli.py get 1`
**助手**：“第一条笔记：张三生日10月5号，分类：social。”

## 11. 按时间搜索
**用户**：“这个月记了哪些笔记？”
**系统**：`script/memo_cli.py search-date 2026-05-01 2026-05-31`
**助手**：“这个月有 5 条笔记：...”

## 12. 编辑笔记分类
**用户**：“把那条‘买咖啡’的笔记改成记账分类。”
**系统**：先搜索找到 id=15，再 `script/memo_cli.py update-category 15 finance`
**助手**：“已更新分类为记账。”
```

- [ ] **Step 3: Commit**

```bash
git add reference/schema.md reference/examples.md
git commit -m "docs: 更新 schema 和 examples，添加新命令和场景"
```

---

## Task 6: 更新 SKILL.md

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: 添加新功能和触发词**

在"功能与触发词"部分添加：

```markdown

### 查看笔记详情
- 触发词：看看、查看、详情
- 命令：`script/memo_cli.py get <id>`

### 按时间搜索
- 触发词：这个月、最近、上周
- 命令：`script/memo_cli.py search-date <start> <end>`

### 编辑笔记分类
- 触发词：改分类、换个分类
- 先搜索找到笔记 ID，再更新分类
- 命令：`script/memo_cli.py update-category <id> <category>`
```

- [ ] **Step 2: 更新 Cron 说明**

更新"定时提醒"部分说明：
```markdown

### 定时提醒机制
- 提前 10 分钟通知
- 一次性提醒：触发后记录 notified_at，避免重复通知
- 重复提醒：每天/每周/每月/每年正常触发
- 通过 QQ 渠道推送消息
```

- [ ] **Step 3: Commit**

```bash
git add SKILL.md
git commit -m "docs: 更新 SKILL.md，添加新功能和提醒机制说明"
```

---

## 完成

计划完成后，备忘录技能将具备：
- ✅ 正确的 weekday 映射
- ✅ 安全的日期边界处理
- ✅ 避免重复通知的 notified_at 机制
- ✅ WAL 并发安全
- ✅ 查看笔记详情
- ✅ 按时间搜索
- ✅ 编辑笔记分类
