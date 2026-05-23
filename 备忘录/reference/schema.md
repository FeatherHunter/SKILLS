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
| created_at | TEXT | 创建时间 |

### 重复规则格式
- **daily**: `"HH:MM"` 例 `"09:00"`
- **weekly**: `"W HH:MM"` W为0-6（周日=0） 例 `"5 17:00"` 周五下午5点
- **monthly**: `"D HH:MM"` D为1-31 例 `"1 09:00"` 每月1号9点
- **yearly**: `"MM-DD HH:MM"` 例 `"12-25 10:00"`

## CLI 命令参考
| 命令 | 说明 | 示例 |
|------|------|------|
| `add <content> [-c <category>] [-m <media_path>]` | 添加笔记 | `memo_cli.py add "明天开会" -c work` |
| `search [keyword] [-c <category>] [-l <limit>]` | 搜索笔记 | `memo_cli.py search "旅行" -c wish` |
| `edit <id> [--content] [--category] [--media]` | 修改笔记 | `memo_cli.py edit 12 --content "新内容"` |
| `delete <id>` | 删除笔记及关联提醒 | `memo_cli.py delete 12` |
| `remind <note_id> [--at <time>] [--repeat-type <type>] [--rule <rule>]` | 添加提醒 | `memo_cli.py remind 5 --at "2026-05-25 09:00"` |
| `due` | 列出未来10分钟待触发的提醒 | `memo_cli.py due` |
| `dismiss <id>` | 废弃提醒 | `memo_cli.py dismiss 3` |
| `reminders [--status active/dismissed]` | 查看提醒列表 | `memo_cli.py reminders` |

所有命令输出JSON：`{"status": "ok/error", "data": ..., "message": "..."}`