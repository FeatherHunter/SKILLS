# 备忘录数据库与API参考

## 场景资产契约(v1.2.0 · #31/#33/#36)

场景资产 `references/scenarios.yaml` = HELP HTML 唯一事实源(总纲 §07)。

### 字段(7 必填 + 3 新)

| 字段 | 必填 | 说明 |
|------|------|------|
| wake_word | ✅ | 唯一展示名;别名只在 SKILL.md 匹配层(#31 Q1) |
| scenario_id | ✅ | 稳定 ID,跨版本不变;全局唯一 |
| scenario_title | ✅ | 用户可读标题 |
| dimensions | ✅ | 合法维度(领域决定) |
| prompt | ✅ | 稳定用户意图,不暴露 CLI/DB/路径 |
| status | ✅ | ""(可用) / 【待开发】(禁用) |
| result | ✅ | 预期结果(用户视角) |
| category | ✅ | 引用顶层 categories key(白名单 8 个) |
| subfunction | 可选 | 空 = 「基础」兜底组 |
| dependencies | 可选 | 环境依赖清单多行文本(仅 Init) |

### categories 列表(8)

memo 备忘类📝 / search 查找类🔍 / remind 提醒类⏰ / wish 心愿类🎯 / checkin 打卡类✅ / mood 情绪类💭 / sync 同步类🔄 / init 初始化类🚀

### 约束

- 无 order:组内序 = yaml 书写序(#31 Q4)
- 禁字段:order/aliases/wake_words/wake_word_index(#31 Q1/Q4/Q6)
- wake_word 允许多对一(备忘改分类 单条+批量)
- 共享校验:script/validate_scenarios.py(测试 + 渲染前双触发)

## 数据库表结构
详见 `script/init.sql`。

### notes 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| content | TEXT | 笔记内容 |
| summary | TEXT | AI摘要，可为空 |
| category | TEXT | 顶层分类：备忘（默认）/ 心愿 / 打卡 / 情绪日记 |
| sub_category | TEXT | 子分类（**自由文本字段**）：AI 智能从用户原话推断 1 个 2 字，适用于所有 category；推断不出 → NULL，不预设白名单 |
| reminder_id | INTEGER | 关联的提醒ID（提醒完成后可追溯来源） |
| media_path | TEXT | 附件相对路径 |
| feishu_task_guid | TEXT | 飞书 task GUID（心愿同步飞书时记录，用于反向查找） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 最后更新时间 |

### sub_category 原则

sub_category 是**自由文本字段**，AI 智能从用户原话推断：

- **1 个，2 字**（简短但比 1 字精确）
- **AI 智能推断**：从用户原话提取内容维度
- **推断不出 → NULL**：AI 不乱猜、不预设白名单、不强制追问
- **适用于所有 category**：不限于 `备忘`，任何顶层分类下的笔记都可以有 sub_category

例：
- "今天跑了 5 公里" → `-c 打卡 -s 跑步`
- "今天学 Python" → `-c 备忘 -s 学习`
- "张三生日 10/3" → `-c 备忘 -s 社交`
- "今天去医院" → `-c 备忘`，`sub_category=NULL`（AI 推断不出维度）

### reminders 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| note_id | INTEGER | 关联笔记ID，外键（ON DELETE NO ACTION，删除时手动级联） |
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
| `add <content> [-c <category>] [-s <sub_category>] [-m <media_path>] [--tasklist-guid <guid>]` | 添加笔记（sub_category 是自由文本，AI 智能推断） | `script/memo_cli.py add "明天开会" -c 备忘 -s 工作` |
| `search [keyword] [-c <category>] [-s <sub_category>] [-l <limit>] [--html]` | 搜索笔记；`--html` 生成 HTML 查询结果页 | `script/memo_cli.py search "旅行" -c 心愿 --html` |
| `update <id> [--content] [-c category] [-s sub_category] [-m media_path] [--reminder-id <id>]` | 修改笔记 | `script/memo_cli.py update 12 --content "新内容"` |
| `delete <id>` | 删除笔记及关联提醒 | `script/memo_cli.py delete 12` |
| `complete-wish <id> [--content <打卡内容>]` | 完成心愿：原子删除心愿 + 自动建立打卡 + 同步飞书 | `script/memo_cli.py complete-wish 15` |
| `remind <note_id> [--at <time>] [--repeat-type <type>] [--rule <rule>]` | 添加提醒 | `script/memo_cli.py remind 5 --at "2026-05-25 09:00"` |
| `due` | 列出未来10分钟待触发的提醒 | `script/memo_cli.py due` |
| `dismiss <id>` | 废弃提醒 | `script/memo_cli.py dismiss 3` |
| `get <id>` | 获取笔记详情 | `script/memo_cli.py get 1` |
| `search-date <start> <end> [-c category]` | 按时间搜索 | `script/memo_cli.py search-date 2026-05-01 2026-05-31` |
| `update-category <id> <category>` | 更新顶层分类（**sub_category 不动**） | `script/memo_cli.py update-category 1 心愿` |
| `update-sub-category <id> <sub_category \| null>` | 更新子分类（适用于所有 category） | `script/memo_cli.py update-sub-category 1 学习` |
| `sync-from-feishu [--tasklist-guid <guid>]` | 反向同步飞书 task 状态 | `script/memo_cli.py sync-from-feishu` |
| `reminders [--status active/dismissed]` | 查看提醒列表 | `script/memo_cli.py reminders` |
| `completed` | 查询已完成提醒（一次性已通知+打卡 / 重复提醒有打卡关联） | `script/memo_cli.py completed` |

所有命令输出JSON：`{"status": "ok/error", "data": ..., "message": "..."}`

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MEMO_DB_PATH` | 数据库文件路径 | `memo.db` |
| `MEMO_CRON_INTERVAL` | cron执行间隔（分钟） | `2` |
| `MEMO_ADVANCE_MINUTES` | 提前触发分钟数 | `10` |
| `MEMO_GRACE_MULTIPLIER` | 延后窗口倍数（窗口=间隔×倍数） | `2` |

数据库路径通过 `MEMO_DB_PATH` 环境变量配置，默认为 `memo.db`（相对于技能目录）。

## 并发安全

数据库使用 WAL 模式和 timeout 机制确保并发安全：

- **WAL 模式**：允许并发读写，通过 `PRAGMA journal_mode=WAL` 启用
- **Timeout**：写锁等待超时 10 秒，通过 `sqlite3.connect(timeout=10)` 设置