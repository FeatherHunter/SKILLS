# 备忘录数据库与API参考

## 数据库表结构
详见 `script/init.sql`。

### notes 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| content | TEXT | 笔记内容 |
| summary | TEXT | AI摘要，可为空 |
| category | TEXT | 分类标签，默认 `general` |
| media_path | TEXT | 附件相对路径 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 最后更新时间 |

### reminders 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| note_id | INTEGER | 关联笔记ID，外键（ON DELETE CASCADE） |
| remind_at | TEXT | 一次性提醒时间 |
| repeat_type | TEXT | 重复类型：none/daily/weekly/monthly/yearly |
| repeat_rule | TEXT | 重复规则，格式见下 |
| status | TEXT | 状态：active / dismissed |
| notified_at | TEXT | 上次通知时间 |
| created_at | TEXT | 创建时间 |

### 重复规则格式
- **每天**: `"HH:MM"` 例 `"09:00"`
- **每周**: `"W HH:MM"` W为0-6（周日=0） 例 `"5 17:00"` 周五下午5点
- **每月**: `"D HH:MM"` D为1-31 例 `"1 09:00"` 每月1号9点
- **每年**: `"MM-DD HH:MM"` 例 `"12-25 10:00"`

## CLI 命令参考
| 命令 | 说明 | 示例 |
|------|------|------|
| `add <content> [-c <category>] [-m <media_path>]` | 添加笔记 | `script/memo_cli.py add "明天开会" -c work` |
| `search [keyword] [-c <category>] [-l <limit>]` | 搜索笔记 | `script/memo_cli.py search "旅行" -c wish` |
| `update <id> [--content] [-c category] [-m media_path]` | 修改笔记 | `script/memo_cli.py update 12 --content "新内容"` |
| `delete <id>` | 删除笔记及关联提醒 | `script/memo_cli.py delete 12` |
| `remind <note_id> [--at <time>] [--repeat-type <type>] [--rule <rule>]` | 添加提醒 | `script/memo_cli.py remind 5 --at "2026-05-25 09:00"` |
| `due` | 列出未来10分钟待触发的提醒 | `script/memo_cli.py due` |
| `dismiss <id>` | 废弃提醒 | `script/memo_cli.py dismiss 3` |
| `get <id>` | 获取笔记详情 | `script/memo_cli.py get 1` |
| `search-date <start> <end> [-c category]` | 按时间搜索 | `script/memo_cli.py search-date 2026-05-01 2026-05-31` |
| `update-category <id> <category>` | 更新分类 | `script/memo_cli.py update-category 1 work` |
| `reminders [--status active/dismissed]` | 查看提醒列表 | `script/memo_cli.py reminders` |

所有命令输出JSON：`{"status": "ok/error", "data": ..., "message": "..."}`

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MEMO_DB_PATH` | 数据库文件路径 | `memo.db` |

数据库路径通过 `MEMO_DB_PATH` 环境变量配置，默认为 `memo.db`（相对于技能目录）。

## 并发安全

数据库使用 WAL 模式和 timeout 机制确保并发安全：

- **WAL 模式**：允许并发读写，通过 `PRAGMA journal_mode=WAL` 启用
- **Timeout**：写锁等待超时 10 秒，通过 `sqlite3.connect(timeout=10)` 设置