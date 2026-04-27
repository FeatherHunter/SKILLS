---
name: daily-recorder
description: 记录用户的语录，从 state.db 提取用户发言
---
# Daily Recorder
记录用户的语录，从 Hermes 的 state.db 数据库中提取用户发言。

工作目录是:
windows的绝对路径 D:\2Study\StudyNotes
WSL的绝对路径 /mnt/d/2Study/StudyNotes

**重要：所有文件路径操作必须使用 WSL 绝对路径 `/mnt/d/...`，严禁使用 Windows 格式路径 `D:/` 或 `D:\`**

## 安装
触发时检查**当前AI智能体**的 skills 目录：
- 不存在 `skills/daily-recorder/SKILL.md` → 创建SKILL文件(桥接器文件)，SKILL文件内容指向本文件
- 桥接器只符合SKILL规范且包含SKILL触发条件，和SKILL本体文件路径

## 触发方式
### 手动触发
- 说"记录语录"、"生成语录"、"提取今日语录"
- 支持指定日期范围，如"生成0421的语录"

## 数据来源
- 唯一数据源：`~/.hermes/state.db` (SQLite)
- 包含表：`messages`（消息）、`sessions`（会话）

### 消息表结构
```sql
messages (
  id INTEGER,
  session_id TEXT,
  role TEXT,        -- user / assistant / tool
  content TEXT,
  timestamp REAL,    -- Unix时间戳（秒级，精确到毫秒）
  ...
)
```

### 过滤规则
```python
role == 'user'
AND content NOT LIKE '[SYSTEM%'
AND content NOT LIKE '[System note%'
AND content NOT LIKE '[The user sent%'
```

## 输出格式
**⚠️ 重要：路径格式（WSL 环境必读）**
- **Windows 路径**：`D:/2Study/StudyNotes/{YYYY}/个人/{YYYYMMDD}/{YYYYMMDD}_语录.md`
- **WSL 等效路径**：`/mnt/d/2Study/StudyNotes/{YYYY}/个人/{YYYYMMDD}/{YYYYMMDD}_语录.md`
- **严禁**将 `D:/` 开头的路径直接拼接到 WSL 工作目录后面
- 所有文件操作（read_file/write_file/patch/terminal/execute_code）**必须使用 WSL 绝对路径** `/mnt/d/...`，禁止使用 `D:/` 开头的路径

**保存路径（WSL）**：`/mnt/d/2Study/StudyNotes/{YYYY}/个人/{YYYYMMDD}/{YYYYMMDD}_语录.md`

**文件格式**：
```markdown
# {日期} 语录

采集时间：{开始时间} ~ {结束时间}
总消息数：{N} 条

---

{时间1} - {内容1}
{时间2} - {内容2}
...
```

**每条消息格式**：`YYYY-MM-DD HH:MM:SS - 内容`
- 内容只取第一行，多行内容截断
- 内容超过200字符截断

## 追加逻辑
1. 检查语录文件是否存在
2. **文件不存在**：提取当天 00:00:00 至今的所有用户消息
3. **文件存在**：读取最后一行，解析时间戳，提取该时间之后的新消息
4. 将新消息追加到文件末尾

### ⚠️ 追加时的格式陷阱
**问题：** 如果文件最后一行（不含空行）不以换行符 `\n` 结尾，直接追加会导致新内容与旧内容合并到同一行。

**示例：**  
原文件最后一行为 `2026-04-26 20:59:29 - 需要一个男生一个女生。璀璨的星空。`（无换行符）  
追加时直接写入 `\n2026-04-26 21:31:53 - 我玩了会儿电脑`  
结果变成：`2026-04-26 20:59:29 - 需要一个男生一个女生。璀璨的星空。2026-04-26 21:31:53 - 我玩了会儿电脑`

**正确做法：** 追加前检查最后一行的格式：
```python
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

last_line = lines[-1].rstrip('\n')  # 去掉末尾换行符
last_ts = float(last_line.split(' - ', 1)[0].replace('20', '20'))  # 提取时间戳
```

如果最后一行是空行（`\n`），则 `last_line` 为空字符串，需要用倒数第二行。

**安全追加代码：**
```python
# 构建追加内容（每条消息带换行符）
entries = []
for ts, content in new_messages:
    dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    first_line = str(content).strip().split("\n")[0][:200]
    entries.append(f"{dt} - {first_line}")

# 读取文件，检查末尾是否有换行符
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 如果文件末尾不是换行符，先补上
if content and not content.endswith('\n'):
    content += '\n'

# 追加新内容
content += '\n'.join(entries) + '\n'

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
```

## 时间计算
**重要：** 系统时区是 Asia/Shanghai (CST, +0800)，state.db 的 timestamp 是北京时间。

```python
from datetime import datetime, timezone, timedelta

# 显式指定北京时间（推荐，避免系统时区变化影响）
beijing_tz = timezone(timedelta(hours=8))
today_start = datetime({YYYY}, {MM}, {DD}, 0, 0, 0, tzinfo=beijing_tz)
today_ts = int(today_start.timestamp())  # 北京时间00:00:00的Unix时间戳
```

**验证：** 
- `today_ts = 1776873600` 对应 `2026-04-23 00:00:00` 北京时间
- state.db 中 07:46:56 的 timestamp = `1776901616`

### ⚠️ 重要：timestamp 可能是浮点数
state.db 中 `timestamp` 字段类型是 `REAL`（SQLite float），部分消息的时间戳存储为带毫秒精度的浮点数（如 `1777121213.5775926`），而大多数消息是整数。

**追加逻辑中的陷阱：**
- 读取文件最后一行得到的时间戳是整数形式（如 `1777119722`）
- 直接用 `timestamp > last_ts` 查新消息，当 last_ts 是整数时，**浮点型时间戳（如 `1777242289.587249`）会错误地大于整数 `1777242289.0`**，导致最后一条消息被重复追加
- 即使 `timestamp >= last_ts` 也会因浮点精度产生重复

**正确做法（二选一）：**

**方案A（推荐）：内容去重**
```python
# 从文件最后一行提取内容作为去重依据
last_line = lines[-1].rstrip('\n')
last_content = last_line.split(' - ', 1)[1].strip()

# 查询今天所有消息，过滤掉已存在的
cursor.execute("""
    SELECT timestamp, content FROM messages
    WHERE role = 'user'
    AND timestamp >= ?
    AND content NOT LIKE "[SYSTEM%"
    AND content NOT LIKE "[System note%"
    AND content NOT LIKE "[The user sent%"
    ORDER BY timestamp ASC
""", (today_ts,))

all_messages = cursor.fetchall()
messages = [(ts, c) for ts, c in all_messages if c.strip() != last_content]
```

**方案B：时间戳+内容双保险**
```python
last_ts = 1777242289.0  # 文件最后一秒的整数时间戳（秒级）
cursor.execute("""
    SELECT timestamp, content FROM messages
    WHERE role = 'user'
    AND timestamp > ?
    AND content NOT LIKE "[SYSTEM%"
    AND content NOT LIKE "[System note%"
    AND content NOT LIKE "[The user sent%"
    ORDER BY timestamp ASC
""", (last_ts,))
# 之后再用内容去重过滤掉 last_ts 秒内的浮点型时间戳消息
messages = [(ts, c) for ts, c in cursor.fetchall() if c.strip() != last_content]
```

**⚠️ 从文件提取时间戳的坑：**
旧代码示例 `float(last_line.split(' - ', 1)[0].replace('20', '20'))` 中的 `replace('20','20')` 无意义，应直接解析：
```python
from datetime import datetime
last_dt_str = last_line.split(' - ', 1)[0].strip()  # e.g. "2026-04-27 06:24:49"
last_dt = datetime.strptime(last_dt_str, "%Y-%m-%d %H:%M:%S")
last_ts = last_dt.replace(tzinfo=beijing_tz).timestamp()
```

**边界查询示例：**
```python
# 查询 20:22:02 之后到 20:46:53 的消息（含首尾）
start_ts = 1777119722.0  # 用浮点数避免整数截断
end_ts = 1777121213.5775926  # 目标消息的原始浮点时间戳

cursor.execute("""
    SELECT timestamp, content FROM messages
    WHERE role = 'user'
    AND timestamp > ? AND timestamp <= ?
    ...
""", (start_ts, end_ts))
```

## 使用示例
### 提取今日语录
用户："记录今日语录"
→ 提取今天 00:00:00 至今的用户消息，保存到语录文件

### 追加今日语录
用户："追加今日语录"
→ 检查语录文件是否存在，如存在则追加新消息

### 指定日期
用户："生成0421的语录"
→ 提取 0421 全天的用户消息

## 查询模块（供其他 Skill 复用）
其他 skill 可以调用此模块查询指定时间范围内的用户说话内容。

### 调用方式
```python
# 直接调用 Python 脚本
import subprocess

result = subprocess.run([
    'python3', '-c', '''
import sqlite3
from datetime import datetime, timezone, timedelta

db_path = "/home/feather/.hermes/state.db"
beijing_tz = timezone(timedelta(hours=8))

# 时间段（传入参数）
start_dt = datetime({start_year}, {start_month}, {start_day}, {start_hour}, {start_min}, 0, tzinfo=beijing_tz)
end_dt = datetime({end_year}, {end_month}, {end_day}, {end_hour}, {end_min}, 0, tzinfo=beijing_tz)
start_ts = start_dt.timestamp()
end_ts = end_dt.timestamp()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("""
    SELECT timestamp, content FROM messages
    WHERE role = "user"
    AND timestamp >= ? AND timestamp <= ?
    AND content NOT LIKE "[SYSTEM%"
    AND content NOT LIKE "[System note%"
    AND content NOT LIKE "[The user sent%"
    ORDER BY timestamp ASC
""", (start_ts, end_ts))
messages = cursor.fetchall()
conn.close()

for ts, content in messages:
    dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    first_line = str(content).strip().split("\\n")[0]
    if len(first_line) > 200:
        first_line = first_line[:200] + "..."
    print(f"{dt} - {first_line}")
'''
], capture_output=True, text=True)

print(result.stdout)
```

### 参数说明
| 参数 | 含义 | 示例 |
|------|------|------|
| start_year | 开始年份 | 2026 |
| start_month | 开始月份 | 4 |
| start_day | 开始日期 | 21 |
| start_hour | 开始小时 | 6 |
| start_min | 开始分钟 | 30 |
| end_year | 结束年份 | 2026 |
| end_month | 结束月份 | 4 |
| end_day | 结束日期 | 22 |
| end_hour | 结束小时 | 6 |
| end_min | 结束分钟 | 30 |

### 返回格式
```
YYYY-MM-DD HH:MM:SS - 消息内容1
YYYY-MM-DD HH:MM:SS - 消息内容2
...
```

### 示例：查询 0421 06:30 ~ 0422 06:30
```python
# 北京时间 0421 06:30 到 0422 06:30
start_ts = 1776744600  # 2026-04-21 06:30:00 北京时间
end_ts = 1776831000    # 2026-04-22 06:30:00 北京时间
```

### 常用时间戳参考
| 北京时间 | timestamp |
|---------|-----------|
| 2026-04-21 00:00:00 | 1776652800 |
| 2026-04-21 06:30:00 | 1776744600 |
| 2026-04-22 00:00:00 | 1776739200 |
| 2026-04-22 06:30:00 | 1776831000 |
| 2026-04-23 00:00:00 | 1776873600 |
