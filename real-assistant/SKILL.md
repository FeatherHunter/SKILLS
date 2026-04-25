---
name: real-assistant
description: 智能分析用户状态，关心用户。
---

# 真实助手

## 分析对话记录后发送消息至微信

你是最强大脑，通过最强大脑的方式 分析 用户说过的话和你最近回复过的话参考[数据来源]，选择最适合当前场景的话发给用户。
如果经过分析后无话可说，就说"师傅，真哥让我和你说，觉察你的呼吸，默念佛陀"

强制约束：
1. 严禁发送分析的过程
2. 不要重复发说过的话

## 安装

触发时检查**当前AI智能体**的 skills 目录：
- 不存在 `skills/real-assistant/SKILL.md` → 创建SKILL文件(桥接器文件)，SKILL文件内容指向本文件
- 桥接器只符合SKILL规范且包含SKILL触发条件，和SKILL本体文件路径

## 触发方式

### 方式一：cron 触发（每30分钟）
- 检测 cron 任务，不存在则创建：`*/30 * * * *` 执行 `skill real-assistant`
- 触发后读取 skill 内容，执行分析流程

### 方式二：手动触发
- 说"你在干嘛呢"、关心一下"、随便聊聊"等

---

## 数据来源

从 Hermes 数据库直接读取对话记录。

**数据库路径**：`~/.hermes/state.db`

**查询逻辑**（用 execute_code 脚本实现）：

```python
import sqlite3, datetime

db_path = "/mnt/d/Feather/.hermes/state.db"  # Windows 挂载路径
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

today = datetime.date.today().isoformat()

# 1. 读取当天用户发言（过滤空消息）
cursor.execute("""
    SELECT content, timestamp FROM messages
    WHERE role = 'user'
    AND date(timestamp) = ?
    AND content IS NOT NULL
    AND content != ''
    AND content != '[SILENT]'
    ORDER BY timestamp
""", (today,))
user_msgs = cursor.fetchall()

# 2. 读取最近1条 Hermes 回复（过滤空/SILENT消息）
cursor.execute("""
    SELECT content, timestamp FROM messages
    WHERE role = 'assistant'
    AND content IS NOT NULL
    AND content != ''
    AND content != '[SILENT]'
    AND length(content) > 10
    ORDER BY timestamp DESC
    LIMIT 1
""")
assistant_msg = cursor.fetchone()

conn.close()

# 输出结果供分析用
print("=== 当日用户发言 ===")
for ts, content in user_msgs:
    print(f"[{ts}] {content}")

print("\n=== 最近 Hermes 回复 ===")
if assistant_msg:
    print(f"[{assistant_msg[1]}] {assistant_msg[0]}")
```

**读取结果**：
- `user_msgs`：当日用户所有有内容的发言列表
- `assistant_msg`：最近一条 Hermes 回复（用于了解当前对话状态）

---


