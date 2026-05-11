---
name: 每日检查
description: 每日健康检查 - 扫描所有技能，找到具有Lint模块的技能，由AI根据各技能Lint模块描述执行检查，记录问题到数据库并汇总展示。
---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

# 每日检查 v4.0

## 核心设计

**Lint 逻辑由 AI（我）执行**，不是写死的代码。

AI 读取每个技能的 SKILL.md，根据其中的 Lint 模块描述，结合该技能的数据库/文件，执行检查并记录问题。

`daily_checker.py` 仅负责数据库操作，不含任何 lint 逻辑。

---

## 工作流程

### Step 1：初始化数据库

检查 `D:\2Study\StudyNotes\.db\daily_check.db` 是否存在：
- 不存在 → 创建并初始化 `issues` 表
- 存在 → 连接

**issues 表结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| skill | TEXT | 技能名 |
| key | TEXT | 问题类型（如 `calorie_overdue`、`missing_weight`、`orphan`） |
| desc | TEXT | 人类可读描述 |
| status | TEXT | open / resolved / ignored |
| found_at | TIMESTAMP | 首次发现时间 |
| updated_at | TIMESTAMP | 最后更新时间 |
| count | INTEGER | 累计出现次数 |

**UNIQUE 约束**：`UNIQUE(skill, key)`

---

### Step 2：扫描技能

遍历 `~/.openclaw/workspace/skills/` 下每个子目录，读取 SKILL.md：
- 包含 `Lint` 章节 → 记录为"可检查技能"

桥接文件跟随跳转至实体文件。

---

### Step 3：AI 执行 Lint 检查

对每个具有 Lint 模块的技能，AI 执行：

1. **读取** 该技能的 SKILL.md 中的 Lint 模块描述
2. **理解** 检查项、数据源、检查逻辑
3. **执行** 检查（查询数据库/扫描文件）
4. **生成 key** 和 **desc**，调用 `upsert_issue(skill, key, desc)` 写入问题

**Key 生成规则**：
- AI 根据问题类型自行命名，简洁英文
- 示例：`calorie_overdue`、`missing_weight`、`orphan`、`broken_link`
- key 不含日期，同类问题累加 count

**问题更新逻辑**：
```
  → 不存在：INSERT，count=1，status=open
  → 存在+resolved：重新打开，count++，updated_at=now
  → 存在+open：更新 desc、count++、updated_at=now
  → 存在+ignored：跳过
```

---

### Step 4：汇总展示

AI 从 `daily_check.db` 读取所有 open 问题，按技能分组，生成报告。

**报告格式（紧凑形式）**：

```
📋 每日检查报告  YYYY-MM-DD HH:mm

【居家管家】✅
【卡路里】⚠️ 2
  🟡 热量异常  超标300卡（目标1800卡）  MM-DD HH:MM
  ℹ️ 体重未记录  MM-DD HH:MM
【饼干记账】✅
【llm-wiki】⚠️ 2
  ℹ️ 孤立页面  共35个  MM-DD HH:MM
    例: algorithm-layered-shortest-path, android-anr...

⚠️ 3技能有问题 · 39问题待处理
```

---

## 数据库路径

- 数据库文件：`D:\2Study\StudyNotes\.db\daily_check.db`

---

## daily_checker.py 提供的接口

```python
from daily_checker import (
    init_db,           # 初始化数据库
    upsert_issue,      # 写入问题（key不含日期，同类累加）
    resolve_issue,      # 标记已解决
    ignore_issue,      # 标记忽略
    get_open_issues,   # 获取所有 open 问题
    get_all_issues,    # 获取所有问题
    scan_skills_with_lint,  # 扫描有 Lint 的技能
    generate_report,   # 生成报告
    clear_all_issues,  # 清空所有问题（测试用）
)
```

---

## 触发方式

- 用户说"每日检查"、"健康检查"、"检查一下"、"lint"
- Cron 定时任务：每天 20:00 执行

---

## 注意事项

- Lint 检查由 AI 驱动，根据 SKILL.md 描述执行
- `daily_checker.py` 只做数据库操作，不含检查逻辑
- key 由 AI 动态生成，不预先固定
- 发现问题时只能建议用户处理，不能自动修改
- 问题解决后用户可手动更新 status=resolved 或 ignored