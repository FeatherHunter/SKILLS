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
