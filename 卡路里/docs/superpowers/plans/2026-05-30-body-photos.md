# 身材照片记录功能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现身材照片记录功能，支持批量记录、查询、删除、修改标签、生成 GIF 变化动画

**Architecture:** 新增 `body_photos` 表存储照片元数据，照片文件存储在 `CALORIE_PHOTOS_DIR` 环境变量指定的目录，数据库存储相对路径。通过时间戳关联 `weight_log` 表获取最近体重。

**Tech Stack:** Python 3.7+, SQLite3, Pillow (GIF 生成), argparse (CLI)

---

## File Structure

### New Files
- `scripts/body_photo_tracker.py` — 主脚本，实现所有 CLI 命令
- `scripts/db_utils.py` — 数据库工具函数（已存在，需复用）
- `references/body_photos_schema.md` — 数据库文档

### Modified Files
- `SKILL.md` — 添加唤醒词和功能说明
- `references/database_schema.md` — 添加 body_photos 表文档
- `config-calorie.ts` — 添加新表配置
- `卡路里.html` — 添加身材照片页面

---

## Task 1: 环境变量检查函数

**Files:**
- Create: `scripts/body_photo_tracker.py`

- [ ] **Step 1: 创建脚本基础结构和环境变量检查**

```python
#!/usr/bin/env python3
"""
身材照片记录 - CLI工具
支持添加、查询、删除、修改标签、生成GIF
"""

import argparse
import os
import sys
import shutil
from datetime import datetime, date
from pathlib import Path

from db_utils import find_db_path, get_db as _get_db_conn

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

SKILL_DIR = Path(__file__).parent.parent
DB_FILENAME = "calorie_data.db"
DB_PATH = find_db_path(SKILL_DIR, DB_FILENAME)


def get_photos_dir():
    """获取照片存储目录，未配置则报错退出"""
    photos_dir = os.environ.get('CALORIE_PHOTOS_DIR')
    if not photos_dir:
        print("Error: 环境变量 CALORIE_PHOTOS_DIR 未配置")
        print("请设置环境变量指向照片存储目录，例如：")
        print("  export CALORIE_PHOTOS_DIR=/path/to/photos")
        sys.exit(1)
    
    path = Path(photos_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db():
    """获取数据库连接"""
    return _get_db_conn(DB_PATH)
```

- [ ] **Step 2: 测试环境变量检查**

```bash
# 测试未配置环境变量时是否报错
unset CALORIE_PHOTOS_DIR
python scripts/body_photo_tracker.py
```

Expected output: Error message and exit

---

## Task 2: 数据库初始化

**Files:**
- Modify: `scripts/body_photo_tracker.py`

- [ ] **Step 1: 添加数据库初始化函数**

```python
def init_table():
    """初始化身材照片表"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS body_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            photo_path TEXT NOT NULL,
            tag TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_body_photos_date ON body_photos(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_body_photos_tag ON body_photos(tag)")
    conn.commit()
    conn.close()
```

- [ ] **Step 2: 测试初始化**

```bash
# 设置测试环境变量
export CALORIE_PHOTOS_DIR=/tmp/test_photos

# 运行脚本测试初始化
python -c "
import sys
sys.path.insert(0, 'scripts')
from body_photo_tracker import init_table, get_db
init_table()
conn = get_db()
cur = conn.cursor()
cur.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='body_photos'\")
print(cur.fetchone())
conn.close()
"
```

Expected output: `('body_photos',)`

---

## Task 3: 添加照片功能

**Files:**
- Modify: `scripts/body_photo_tracker.py`

- [ ] **Step 1: 实现 add 命令**

```python
def add_photos(photo_paths, tag, note=''):
    """添加照片记录"""
    photos_dir = get_photos_dir()
    today = date.today().isoformat()
    now = datetime.now().strftime("%H:%M:%S")
    
    # 获取今天的照片数量用于生成序号
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM body_photos WHERE date = ?", (today,))
    count = cur.fetchone()[0]
    conn.close()
    
    added = []
    for i, src_path in enumerate(photo_paths):
        src = Path(src_path)
        if not src.exists():
            print(f"⚠ 文件不存在: {src_path}")
            continue
        
        # 生成目标文件名
        ext = src.suffix.lower()
        seq = count + i + 1
        dest_name = f"{today}_{seq:03d}{ext}"
        dest_path = photos_dir / dest_name
        
        # 复制文件
        shutil.copy2(src, dest_path)
        
        # 写入数据库
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO body_photos (date, time, photo_path, tag, note)
            VALUES (?, ?, ?, ?, ?)
        """, (today, now, dest_name, tag, note))
        photo_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        added.append((photo_id, dest_name))
        print(f"✓ 已添加照片 #{photo_id}: {dest_name} (标签: {tag})")
    
    return added
```

- [ ] **Step 2: 测试添加照片**

```bash
# 创建测试图片
echo "test" > /tmp/test_photo.jpg

# 测试添加
python -c "
import sys
sys.path.insert(0, 'scripts')
from body_photo_tracker import init_table, add_photos
init_table()
add_photos(['/tmp/test_photo.jpg'], '正面', '测试照片')
"
```

Expected output: `✓ 已添加照片 #1: 2026-05-30_001.jpg (标签: 正面)`

---

## Task 4: 查询照片功能

**Files:**
- Modify: `scripts/body_photo_tracker.py`

- [ ] **Step 1: 实现 list 命令**

```python
def list_photos(days=7, tag=None):
    """查询照片列表"""
    conn = get_db()
    cur = conn.cursor()
    
    # 计算起始日期
    from datetime import timedelta
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    # 构建查询
    if tag:
        cur.execute("""
            SELECT id, date, time, photo_path, tag, note, created_at
            FROM body_photos
            WHERE date >= ? AND tag = ?
            ORDER BY date DESC, time DESC
        """, (start_date, tag))
    else:
        cur.execute("""
            SELECT id, date, time, photo_path, tag, note, created_at
            FROM body_photos
            WHERE date >= ?
            ORDER BY date DESC, time DESC
        """, (start_date,))
    
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        print(f"最近{days}天没有身材照片记录")
        return []
    
    print(f"\n身材照片记录（最近{days}天）：{len(rows)}张")
    print("-" * 70)
    print(f"{'ID':>4} | {'日期':>10} | {'时间':>8} | {'标签':>8} | {'文件':20} | 备注")
    print("-" * 70)
    
    for r in rows:
        photo_id, p_date, p_time, photo_path, p_tag, p_note, created = r
        time_str = p_time[:8] if p_time else ''
        print(f"{photo_id:>4} | {p_date:>10} | {time_str:>8} | {p_tag:>8} | {photo_path:20} | {p_note or ''}")
    
    print("-" * 70)
    return rows
```

- [ ] **Step 2: 测试查询**

```bash
python -c "
import sys
sys.path.insert(0, 'scripts')
from body_photo_tracker import init_table, list_photos
init_table()
list_photos(days=1)
"
```

Expected output: Shows the photo we added in Task 3

---

## Task 5: 删除照片功能

**Files:**
- Modify: `scripts/body_photo_tracker.py`

- [ ] **Step 1: 实现 delete 命令**

```python
def delete_photo(photo_id):
    """删除照片"""
    photos_dir = get_photos_dir()
    
    conn = get_db()
    cur = conn.cursor()
    
    # 查询照片信息
    cur.execute("SELECT photo_path FROM body_photos WHERE id = ?", (photo_id,))
    row = cur.fetchone()
    
    if not row:
        print(f"Error: 照片 #{photo_id} 不存在")
        conn.close()
        return False
    
    photo_path = row[0]
    
    # 删除数据库记录
    cur.execute("DELETE FROM body_photos WHERE id = ?", (photo_id,))
    conn.commit()
    conn.close()
    
    # 删除文件
    file_path = photos_dir / photo_path
    if file_path.exists():
        file_path.unlink()
        print(f"✓ 已删除照片 #{photo_id}: {photo_path}")
    else:
        print(f"⚠ 数据库记录已删除，但文件不存在: {photo_path}")
    
    return True
```

- [ ] **Step 2: 测试删除**

```bash
python -c "
import sys
sys.path.insert(0, 'scripts')
from body_photo_tracker import init_table, delete_photo
init_table()
delete_photo(1)
"
```

Expected output: `✓ 已删除照片 #1: 2026-05-30_001.jpg`

---

## Task 6: 修改标签功能

**Files:**
- Modify: `scripts/body_photo_tracker.py`

- [ ] **Step 1: 实现 tag 命令**

```python
def update_tag(photo_id, new_tag):
    """修改照片标签"""
    conn = get_db()
    cur = conn.cursor()
    
    # 检查照片是否存在
    cur.execute("SELECT id FROM body_photos WHERE id = ?", (photo_id,))
    if not cur.fetchone():
        print(f"Error: 照片 #{photo_id} 不存在")
        conn.close()
        return False
    
    # 更新标签
    cur.execute("UPDATE body_photos SET tag = ? WHERE id = ?", (new_tag, photo_id))
    conn.commit()
    conn.close()
    
    print(f"✓ 已更新照片 #{photo_id} 标签为: {new_tag}")
    return True
```

- [ ] **Step 2: 测试修改标签**

```bash
# 先添加一张照片
python -c "
import sys
sys.path.insert(0, 'scripts')
from body_photo_tracker import init_table, add_photos, update_tag
init_table()
add_photos(['/tmp/test_photo.jpg'], '正面')
update_tag(2, '侧面')
"
```

Expected output: `✓ 已更新照片 #2 标签为: 侧面`

---

## Task 7: 获取最近体重函数

**Files:**
- Modify: `scripts/body_photo_tracker.py`

- [ ] **Step 1: 实现获取最近体重函数**

```python
def get_latest_weight():
    """获取最近的体重记录"""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT weight_kg, date, time 
        FROM weight_log 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {'weight': row[0], 'date': row[1], 'time': row[2]}
    return None
```

- [ ] **Step 2: 测试获取体重**

```bash
python -c "
import sys
sys.path.insert(0, 'scripts')
from body_photo_tracker import get_latest_weight
result = get_latest_weight()
print(result)
"
```

Expected output: Weight info or None

---

## Task 8: GIF 生成功能

**Files:**
- Modify: `scripts/body_photo_tracker.py`

- [ ] **Step 1: 实现 gif 命令**

```python
def generate_gif(tag, start_date=None, end_date=None, days=None, output=None):
    """生成 GIF 变化动画"""
    try:
        from PIL import Image
    except ImportError:
        print("Error: 需要安装 Pillow 库")
        print("请运行: pip install Pillow")
        return None
    
    photos_dir = get_photos_dir()
    gifs_dir = photos_dir / "gifs"
    gifs_dir.mkdir(exist_ok=True)
    
    # 计算日期范围
    if start_date and end_date:
        pass
    elif days:
        from datetime import timedelta
        end_date = date.today().isoformat()
        start_date = (date.today() - timedelta(days=days)).isoformat()
    else:
        print("Error: 请指定 --start/--end 或 --days")
        return None
    
    # 查询照片
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT photo_path, date
        FROM body_photos
        WHERE tag = ? AND date >= ? AND date <= ?
        ORDER BY date ASC, time ASC
    """, (tag, start_date, end_date))
    rows = cur.fetchall()
    conn.close()
    
    if not rows:
        print(f"未找到标签为 '{tag}' 的照片（{start_date} ~ {end_date}）")
        return None
    
    # 加载图片
    images = []
    for photo_path, photo_date in rows:
        file_path = photos_dir / photo_path
        if file_path.exists():
            img = Image.open(file_path)
            # 统一尺寸
            img = img.resize((400, 600), Image.Resampling.LANCZOS)
            images.append(img)
    
    if not images:
        print("没有可用的照片文件")
        return None
    
    # 生成输出文件名
    if not output:
        output = f"{tag}_{start_date}_{end_date}.gif"
    
    output_path = gifs_dir / output
    
    # 生成 GIF
    images[0].save(
        output_path,
        save_all=True,
        append_images=images[1:],
        duration=500,
        loop=0
    )
    
    print(f"✓ 已生成 GIF: {output_path}")
    print(f"  包含 {len(images)} 张照片")
    return output_path
```

- [ ] **Step 2: 测试 GIF 生成**

```bash
# 先添加几张测试照片
python -c "
import sys
sys.path.insert(0, 'scripts')
from body_photo_tracker import init_table, add_photos
init_table()
add_photos(['/tmp/test_photo.jpg'], '正面')
"

# 测试生成 GIF
python -c "
import sys
sys.path.insert(0, 'scripts')
from body_photo_tracker import generate_gif
generate_gif('正面', days=1)
"
```

Expected output: GIF file created in gifs directory

---

## Task 9: CLI 主函数

**Files:**
- Modify: `scripts/body_photo_tracker.py`

- [ ] **Step 1: 实现 argparse CLI**

```python
def main():
    parser = argparse.ArgumentParser(description="身材照片记录管理")
    subparsers = parser.add_subparsers(dest='cmd', help='子命令')
    
    # add
    p_add = subparsers.add_parser('add', help='添加照片')
    p_add.add_argument('photos', nargs='+', help='照片文件路径')
    p_add.add_argument('--tag', required=True, help='照片标签')
    p_add.add_argument('--note', default='', help='备注')
    
    # list
    p_list = subparsers.add_parser('list', help='查询照片')
    p_list.add_argument('--days', type=int, default=7, help='查询天数')
    p_list.add_argument('--tag', help='按标签筛选')
    
    # delete
    p_delete = subparsers.add_parser('delete', help='删除照片')
    p_delete.add_argument('id', type=int, help='照片ID')
    
    # tag
    p_tag = subparsers.add_parser('tag', help='修改标签')
    p_tag.add_argument('id', type=int, help='照片ID')
    p_tag.add_argument('new_tag', help='新标签')
    
    # gif
    p_gif = subparsers.add_parser('gif', help='生成GIF')
    p_gif.add_argument('--tag', required=True, help='照片标签')
    p_gif.add_argument('--start', help='开始日期 YYYY-MM-DD')
    p_gif.add_argument('--end', help='结束日期 YYYY-MM-DD')
    p_gif.add_argument('--days', type=int, help='最近N天')
    p_gif.add_argument('--output', help='输出文件名')
    
    args = parser.parse_args()
    
    # 初始化表
    init_table()
    
    if args.cmd == 'add':
        add_photos(args.photos, args.tag, args.note)
    elif args.cmd == 'list':
        list_photos(days=args.days, tag=args.tag)
    elif args.cmd == 'delete':
        delete_photo(args.id)
    elif args.cmd == 'tag':
        update_tag(args.id, args.new_tag)
    elif args.cmd == 'gif':
        generate_gif(args.tag, args.start, args.end, args.days, args.output)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 测试 CLI**

```bash
# 测试帮助信息
python scripts/body_photo_tracker.py --help

# 测试添加照片
echo "test" > /tmp/test.jpg
python scripts/body_photo_tracker.py add /tmp/test.jpg --tag 正面 --note "测试"

# 测试查询
python scripts/body_photo_tracker.py list

# 测试删除
python scripts/body_photo_tracker.py delete 1
```

Expected output: Help text and successful operations

---

## Task 10: 更新数据库文档

**Files:**
- Create: `references/body_photos_schema.md`
- Modify: `references/database_schema.md`

- [ ] **Step 1: 创建 body_photos_schema.md**

```markdown
# body_photos — 身材照片记录

```sql
CREATE TABLE body_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,           -- 日期 YYYY-MM-DD
    time TEXT NOT NULL,           -- 时间 HH:MM:SS
    photo_path TEXT NOT NULL,     -- 相对路径，如 "2026-05-30_001.jpg"
    tag TEXT NOT NULL,            -- 自定义标签：正面/背面/侧面/手臂等
    note TEXT NOT NULL,           -- 备注
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_body_photos_date ON body_photos(date);
CREATE INDEX idx_body_photos_tag ON body_photos(tag);
```

## 存储说明

- **环境变量**：`CALORIE_PHOTOS_DIR`（强制配置，无默认值）
- **照片命名**：`{date}_{序号}.{ext}`，如 `2026-05-30_001.jpg`
- **数据库**：存储相对路径

## 体重关联

照片通过时间戳关联 `weight_log` 表中最近的体重记录（按 created_at 排序取最后一条）。
```

- [ ] **Step 2: 更新 database_schema.md**

在 `database_schema.md` 的表总览中添加：

```markdown
| `body_photos` | 身材照片记录 | id |
```

在文末添加：

```markdown
---

## body_photos — 身材照片记录

```sql
CREATE TABLE body_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    photo_path TEXT NOT NULL,
    tag TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_body_photos_date ON body_photos(date);
CREATE INDEX idx_body_photos_tag ON body_photos(tag);
```

> **存储说明**：照片文件存储在 `CALORIE_PHOTOS_DIR` 环境变量指定的目录，数据库存储相对路径。
```

---

## Task 11: 更新 SKILL.md

**Files:**
- Modify: `SKILL.md`

- [ ] **Step 1: 添加身材照片唤醒词**

在 `SKILL.md` 的触发词速查表中添加新 section：

```markdown
### 📸 身材照片

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记身材照 | 记录身材照片（支持批量） | `body_photo_tracker.py add` |
| 查身材照 | 查看照片历史 | `body_photo_tracker.py list` |
| 删身材照 | 删除照片 | `body_photo_tracker.py delete` |
| 改照片标签 | 修改照片标签 | `body_photo_tracker.py tag` |
```

- [ ] **Step 2: 添加功能说明**

在功能概述中添加：

```markdown
- **身材照片**：记录身材照片，支持自定义标签（正面/背面/侧面/手臂等），可生成 GIF 变化动画
```

- [ ] **Step 3: 添加 CLI 用法**

在命令行用法部分添加：

```markdown
### 身材照片
```bash
python scripts/body_photo_tracker.py add photo1.jpg photo2.jpg --tag 正面 --note "早起"
python scripts/body_photo_tracker.py list --days 30 --tag 正面
python scripts/body_photo_tracker.py delete 1
python scripts/body_photo_tracker.py tag 1 侧面
python scripts/body_photo_tracker.py gif --tag 正面 --start 2026-01-01 --end 2026-05-30
```
```

- [ ] **Step 4: 添加 AI 路由规则**

在 AI 路由规则的功能域识别表中添加：

```markdown
| 身材照/体型照/身体照片 | 📸 身材照片 |
```

在歧义消解表中添加：

```markdown
| "记身材照" vs "查身材照" | "记"=新增，"查"=查询 |
```

---

## Task 12: 更新 config-calorie.ts

**Files:**
- Modify: `config-calorie.ts`

- [ ] **Step 1: 添加 body_photos 表配置**

在 `config-calorie.ts` 的 `schema.tables` 数组中添加：

```json
{
  "name": "body_photos",
  "fields": [
    {
      "name": "id",
      "type": "number",
      "label": "Id",
      "primaryKey": true,
      "editable": false
    },
    {
      "name": "date",
      "type": "string",
      "label": "Date",
      "format": "date",
      "editable": true
    },
    {
      "name": "time",
      "type": "string",
      "label": "Time",
      "format": "time",
      "editable": true
    },
    {
      "name": "photo_path",
      "type": "string",
      "label": "Photo path",
      "editable": true
    },
    {
      "name": "tag",
      "type": "string",
      "label": "Tag",
      "editable": true
    },
    {
      "name": "note",
      "type": "string",
      "label": "Note",
      "editable": true
    },
    {
      "name": "created_at",
      "type": "string",
      "label": "Created at",
      "default": "CURRENT_TIMESTAMP",
      "format": "datetime",
      "visible": false,
      "editable": false
    }
  ]
}
```

- [ ] **Step 2: 添加 queries**

在 `queries` 数组中添加：

```json
{
  "id": "body_photos-daily",
  "label": "今日身材照片",
  "sql": "SELECT * FROM body_photos WHERE date = '{date}' ORDER BY time",
  "params": [
    {
      "name": "date",
      "type": "date",
      "label": "日期",
      "default": "TODAY"
    }
  ]
},
{
  "id": "body_photos-history",
  "label": "身材照片历史",
  "sql": "SELECT * FROM body_photos ORDER BY date DESC, time DESC LIMIT 100",
  "params": []
}
```

- [ ] **Step 3: 添加 actions**

在 `actions` 数组中添加：

```json
{
  "id": "add-body_photos",
  "label": "添加身材照片",
  "type": "insert",
  "targetTable": "body_photos",
  "fields": [
    {
      "field": "date",
      "required": true,
      "source": "user-input",
      "prompt": "Date"
    },
    {
      "field": "time",
      "required": true,
      "source": "user-input",
      "prompt": "Time"
    },
    {
      "field": "photo_path",
      "required": true,
      "source": "user-input",
      "prompt": "Photo path"
    },
    {
      "field": "tag",
      "required": true,
      "source": "user-input",
      "prompt": "Tag"
    },
    {
      "field": "note",
      "required": true,
      "source": "user-input",
      "prompt": "Note"
    }
  ]
}
```

- [ ] **Step 4: 添加 views**

在 `views` 数组中添加：

```json
{
  "id": "body_photos",
  "label": "身材照片",
  "components": {
    "table": {
      "queryId": "body_photos-daily",
      "sortable": true,
      "pageSize": 20
    },
    "form": {
      "actionId": "add-body_photos"
    }
  }
}
```

---

## Task 13: 更新卡路里.html

**Files:**
- Modify: `卡路里.html`

- [ ] **Step 1: 添加身材照片导航项**

在导航菜单中添加身材照片链接。

- [ ] **Step 2: 添加身材照片页面**

添加照片展示页面，包含：
- 照片列表
- 标签筛选
- 日期范围选择
- 照片预览

---

## Task 14: 最终测试

- [ ] **Step 1: 运行完整测试**

```bash
# 设置环境变量
export CALORIE_PHOTOS_DIR=/tmp/test_photos

# 测试添加照片
python scripts/body_photo_tracker.py add /tmp/test.jpg --tag 正面 --note "测试"

# 测试查询
python scripts/body_photo_tracker.py list --days 1

# 测试修改标签
python scripts/body_photo_tracker.py tag 1 侧面

# 测试删除
python scripts/body_photo_tracker.py delete 1

# 测试 GIF 生成
python scripts/body_photo_tracker.py gif --tag 正面 --days 30
```

- [ ] **Step 2: 检查 HTML 页面**

打开 `卡路里.html` 确认身材照片页面正常显示。

---

## Commit Strategy

每个 Task 完成后提交：

```bash
git add -A
git commit -m "feat(body-photos): <task description>"
```

## Dependencies

- Python >= 3.7
- Pillow (GIF 生成，可选)
- 环境变量 `CALORIE_PHOTOS_DIR` 必须配置
