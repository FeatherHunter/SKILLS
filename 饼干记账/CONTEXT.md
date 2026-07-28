# 饼干记账

本地记账 Skill。AI 解析自然语言,Python CLI 写入 SQLite,查询类操作默认输出 HTML(单文件离线、可复制 prompt)。

## Language

**Skill 标识**:
Skill 在跨 Skill 共享目录里用的唯一英文标识。本 Skill 取 `biscuit_accountant`(与 `_meta.json` 的 slug 一致),HTML 输出子目录为 `biscuit_accountant_html/`。
_Avoid_: 中文名"饼干记账"(用于 SKILL.md frontmatter / HELP 命名前缀,不作子目录名)

**command_cn**:
12.A 类 HTML 输出文件名的中文前缀,继承自 SKILL.md §唤醒词总表字面。映射表见 `scripts/html_paths.py`。
_Avoid_: CLI 子命令名(英文 add/list/summary 等)、scenario_id

**scenario / scenarios.json**:
本 Skill 的"场景资产",存在 `references/scenarios.json`,是唤醒词×使用例的二维映射,被 `scripts/render_help.py` 与 `templates/help.html` 引用,是 HELP HTML 的唯一事实源。
_Avoid_: 不再手工维护 HELP HTML 副本(应从 scenarios.json 渲染)

**_HELP_ 保留字**:
12.B 类 HELP HTML 文件名的固定中段。形态 `<skill 中文名>_HELP_<YYYYMMDD>_<HHMMSS>[_N].html`。grep 一抓就出来。

**12.A / 12.B**:
总纲 §原则 12 规定的两类 HTML 输出。12.A = 数据/过程 HTML(本 Skill 的 `查今天/查日期/查范围/查分类/查最近/搜备注/看月度/看对比/看分类/看总览/做统计`),文件名 `command_cn` 前缀。12.B = HELP HTML(`饼干记账 HELP`),文件名 `饼干记账_HELP_` 前缀。

**分类心法 / L1/L2/L3**:
支出分类三级体系,见 `references/categories.md`。
- L1 = 一级分类(10 个:餐饮/居家/穿着/出行/玩乐/学习/健康/社交/宠物/其他)
- L2 = 二级场景
- L3 = 具体品类

_Avoid_: 中文名"类目/类型/科目"

**amount 符号**:
所有金额用带符号浮点数写入。支出 = 负数(`-35.0`),收入 = 正数(`+5000.0`)。符号是分类依据,不要单独存 `type` 列。
_Avoid_: 分开存 `type: expense/income` 字段

## File structure

单一上下文(single-context):
```
饼干记账/
├── CONTEXT.md            ← 本文件,领域术语
├── SKILL.md              ← Skill 主文档,含 §📌 输出位置
├── 饼干记账.html         ← SKILL.md 镜像(手工同步)
├── _meta.json            ← ownerId/slug/version 元数据
├── docs/
│   ├── agents/           ← agent 配置(issue-tracker/triage-labels/domain)
│   └── adr/              ← 架构决策记录
├── references/           ← categories.md / scenarios.json / scenarios.md
├── templates/            ← query_view.html / help.html
├── scripts/              ← db.py / analyze.py / record_bill.py / bill_inject.py / render_help.py / html_paths.py / 3 个迁移脚本
├── backups/              ← CSV 迁移备份 (gitignored)
├── config-cookie-accounting.ts ← SkillBoard 数据层视图(独立维护)
└── .scratch/             ← 本地 markdown issue 跟踪(可选)
```

HTML 输出根在 Skill 目录外,由 env 链解析:`$SKILLS_DB_PATH` > `$SKILLS_DATA_DIR` > Skill fallback(Windows `D:\.db\`,WSL `/mnt/d/.db/`)。本 Skill 当前 fallback 解析到 `D:\.db\`,所以 HTML 输出实际在 `D:\.db\biscuit_accountant_html\`。