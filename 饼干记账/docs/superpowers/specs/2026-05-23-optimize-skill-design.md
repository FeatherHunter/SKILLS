# 饼干记账 SKILL 优化设计

> 基于 SKILL-开发规范.md 审查发现的 25 个问题，全面修复。

## 决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 优化范围 | 全部 25 个问题 | 一步到位 |
| query.py 处理 | 合并到 db.py | 函数都是一行包装，无独立价值 |
| 每日账单文件 | 去掉 | SQLite 为唯一存储，简化架构 |
| .db 跟踪 | 不提交 | 运行时数据，不该进 git |
| SKILL 名称 | 统一中文"饼干记账" | 与目录名、slug 一致 |
| config.ts | 一起修 | 属于同一技能生态 |

## 方案选择

**方案 B：结构优化 + 全面修复**

- 合并 query.py → db.py，删除 query.py
- 去掉每日文件相关代码
- 修复所有 25 个问题
- db.py 作为唯一数据层，analyze.py 作为分析层，record_bill.py 作为 CLI 入口

## 文件结构变更

### 删除
- `scripts/query.py` — 合并到 db.py
- `scripts/__init__.py` — 空文件，不需要

### 修改
- `scripts/db.py` — 合并 query.py 函数 + 去掉每日文件逻辑 + 修复连接管理
- `scripts/analyze.py` — 去掉每日文件引用 + 修复模块级 date.today()
- `scripts/record_bill.py` — 更新 import（从 db 直接导入查询函数）
- `SKILL.md` — 全面重写
- `config-cookie-accounting.ts` — 补类型、补分类、修 SQL
- `.gitignore` — 取消注释 *.db

### 不变
- `_meta.json`
- `references/categories.md`

### 最终目录结构
```
饼干记账/
├── SKILL.md
├── _meta.json
├── config-cookie-accounting.ts
├── .gitignore
├── references/
│   └── categories.md
└── scripts/
    ├── db.py
    ├── analyze.py
    └── record_bill.py
```

## db.py 重构

### 合并 query.py 函数

从 query.py 合并以下函数到 db.py：
- `list_today()` → 内部调用 `fetch_all(from_time=..., to_time=...)`
- `list_date(date_str)` → 同上
- `list_date_range(from_date, to_date)` → 同上，带参数校验
- `list_by_category(category)` → `fetch_all(category=category)`
- `search_keyword(keyword)` → `fetch_all(keyword=keyword)`
- `list_recent(limit)` → `fetch_all(limit=limit)`

### 修复项

| 原行号 | 问题 | 修改 |
|--------|------|------|
| 17-39 | 路径查找顺序与规范不一致 | 改为：环境变量 → 父目录 → 技能目录（三层查找） |
| 41 | `DB_DIR` 多余别名 | 删除，直接用 `SKILL_DIR` |
| 44-46 | 模块级 `date.today()` | 删除模块级变量，改为函数内获取 |
| 48-50 | 每日账单路径硬编码 | 整段删除（BILLS_DIR, BILLS_FILE） |
| 58 | `DB_DIR.mkdir` 多余 | 删除 |
| 85-93 | 连接未保护 | 改用 try/finally 确保 conn.close() |
| 96-128 | write_daily_bill_file + add_bill 双写 | 删除 write_daily_bill_file，add_bill 只写 SQLite |
| 132-170 | fetch_all 的 limit 用 f-string | 改为参数化 `LIMIT ?` |

### 路径查找规范

```
1. 环境变量 SKILLS_DB_PATH → {path}/biscuit_accountant.db
2. 父目录向上查找 .db/ 目录
3. 技能目录下 .db/ 子目录（默认 fallback）
```

## analyze.py 修改

| 原行号 | 问题 | 修改 |
|--------|------|------|
| 19-20 | 模块级 `date.today()` | 删除，函数内获取 |
| 73-81 | 月末计算冗余 | 简化：用 `time < '{next_month}-01 00:00:00'` 替代 `<= 23:59:59` |

保持直接写 SQL 的方式（分析查询与 CRUD 逻辑不同，合理分离）。

## record_bill.py 修改

| 原行号 | 问题 | 修改 |
|--------|------|------|
| 27-33 | import query 和 analyze | 去掉 `from query import ...`，改为 `from db import list_today, list_date, ...` |
| 39 | `_format_record` 无防御 | 用 `.get()` 取所有字段 |
| 96-100 | cmd_summary 字段访问 | 安全取值 |
| 整体 | python vs python3 | SKILL.md 统一用 `python3` |

保留 8 个子命令：add, list, search, summary, monthly, compare, recent, breakdown。

## SKILL.md 重写

### 结构（按规范 2.2）

```
frontmatter (name: 饼干记账, description: 精简到 50 字)
├── 操作规范（强制）
├── 安装与配置
│   ├── 依赖说明（Python 3.x, sqlite3）
│   ├── 一键安装 prompt
│   └── 配置项说明（环境变量 + 默认值）
├── 功能概述（3-5 个核心功能）
├── 使用流程
│   ├── 触发词 → 功能映射表
│   ├── Step 1-5（保留图片识别逻辑）
│   └── 命令行功能（完整 8 个子命令）
├── 核心原则（什么能做/不能做）
├── 错误处理
└── （联动说明和 Lint 章节均删除）
```

### 关键修改

| # | 问题 | 修改 |
|---|------|------|
| 2 | 硬编码绝对路径 | 全部改为相对路径 + 环境变量说明 |
| 3 | AI 触发指引路径错误 | 改为 `scripts/record_bill.py` |
| 8 | python vs python3 | 统一 `python3` |
| 9 | 命令行只列 5 个 | 补全 8 个子命令 |
| 10 | 英文名 personal-accounting | 统一为"饼干记账" |
| 11 | .md 存 CSV | 去掉每日文件描述 |
| 12 | Lint TODO 空壳 | 删除整个 Lint 章节 |
| 13 | 缺一键安装 prompt | 新增 |
| 14 | 缺核心原则 | 新增 |
| 15 | 联动技能不存在 | 删除联动章节 |
| 16 | description 过长 | 精简 |

### 核心原则内容

- 所有数据操作通过 CLI，禁止直连数据库
- 只读操作（查询/统计）不需确认，写入操作（记账）需用户确认
- 不支持删除和修改已有记录
- 金额必须明确，不能猜测

## config-cookie-accounting.ts 修改

| # | 问题 | 修改 |
|---|------|------|
| 5 | `SkillConfig` 类型未定义 | 文件顶部补 interface 定义 |
| 23 | `period` 参数 SQL 未使用 | 加注释说明前端用途 |
| 24 | overview 用 chart 展示标量 | 加注释说明数据形态 |
| 31 | 收入缺"其他" | options 补上 `"其他"` |

### 类型定义

```typescript
interface SkillField {
  name: string; type: string; label: string;
  primaryKey?: boolean; visible?: boolean; nullable?: boolean;
  format?: string; unit?: string; default?: string; options?: string[];
}
interface SkillTable { name: string; fields: SkillField[]; }
interface SkillQuery {
  id: string; label: string; sql: string;
  params?: any[]; chartType?: string; chartConfig?: any;
}
interface SkillAction {
  id: string; label: string; type: string;
  targetTable: string; fields: any[];
}
interface SkillView {
  id: string; label: string; icon: string; components: any;
}
interface SkillConfig {
  meta: any; schema: { tables: SkillTable[] };
  queries: SkillQuery[]; actions: SkillAction[]; views: SkillView[];
}
```

## .gitignore

```gitignore
__pycache__/
*.py[cod]
*$py.class
.env
*.db
```

## 质量保障

改完后执行验证：

1. `python3 -m py_compile scripts/db.py scripts/analyze.py scripts/record_bill.py`
2. `python3 -c "from db import list_today, list_date, list_date_range, list_by_category, search_keyword, list_recent, fetch_all, get_by_id, add_bill"`
3. 逐个执行 8 个子命令确认无报错
4. 验证三层路径查找逻辑
5. config.ts 无 TypeScript 编译错误

## 问题清单对照

| # | 文件 | 问题 | 状态 |
|---|------|------|------|
| 1 | db.py:49 | 每日账单路径硬编码 | 删除（去掉每日文件） |
| 2 | SKILL.md | 硬编码绝对路径 | 改为相对路径 |
| 3 | SKILL.md | AI 触发指引路径错误 | 改为 scripts/ |
| 4 | config.ts:38 | 收入缺"其他" | 补上 |
| 5 | config.ts:18 | SkillConfig 类型未定义 | 补定义 |
| 6 | db.py:85 | 连接未保护 | try/finally |
| 7 | db.py:17 | 路径查找顺序不一致 | 统一为规范顺序 |
| 8 | SKILL.md | python vs python3 | 统一 python3 |
| 9 | SKILL.md | 命令行只列 5 个 | 补全 8 个 |
| 10 | SKILL.md:12 | 英文名不一致 | 统一中文名 |
| 11 | SKILL.md:51 | .md 存 CSV | 删除（去掉每日文件） |
| 12 | SKILL.md:219 | Lint TODO 空壳 | 删除 |
| 13 | SKILL.md | 缺一键安装 prompt | 新增 |
| 14 | SKILL.md | 缺核心原则 | 新增 |
| 15 | SKILL.md:208 | 联动技能不存在 | 删除 |
| 16 | SKILL.md:3 | description 过长 | 精简 |
| 17 | query.py | 与 db.py 重复 | 合并后删除 |
| 18 | analyze.py | 直接写 SQL | 保持（合理分离） |
| 19 | analyze.py:73 | 月末计算冗余 | 简化 |
| 20 | db.py:41 | DB_DIR 多余 | 删除 |
| 21 | db.py:44 | 模块级 date.today() | 改为函数内 |
| 22 | record_bill.py:39 | 无防御取值 | 用 .get() |
| 23 | config.ts:166 | period 参数 SQL 未使用 | 加注释 |
| 24 | config.ts:276 | overview 用 chart 展示标量 | 加注释 |
| 25 | .gitignore:10 | *.db 注释掉 | 取消注释 |
