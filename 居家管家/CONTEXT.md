# 居家管家

家庭物品全生命周期管理 Skill。AI 解析自然语言,Python CLI 执行所有数据库读写,HTML 预览确认写入。

## Language

**Skill 标识**:
Skill 在跨 Skill 共享目录里用的唯一英文标识。本 Skill 取 `home_manager`(与 Python 包名一致),HTML 输出子目录为 `home_manager_html/`。
_Avoid_: 中文名"居家管家"(用于 SKILL.md frontmatter / HELP 命名前缀,不作子目录名)

**command_cn**:
12.A 类 HTML 输出文件名的中文前缀,继承自 SKILL.md §触发词速览表字面。每个 template 在 render 层映射到一个 command_cn,调用者无感知。
_Avoid_: template 名(如 `search_results`)、scenario_id、CLI 子命令名

**出行清单**:
`travel_trip.html` template 的 command_cn。涵盖"带物品"(pack)和"归物品"(return)两个唤醒词,因为本质都是出行相关的物品清点。
_Avoid_: 带归物品、旅行清点

**_HELP_ 保留字**:
12.B 类 HELP HTML 文件名的固定中段。形态 `<skill 中文名>_HELP_<YYYYMMDD>_<HHMMSS>.html`。grep 一抓就出来。

**12.A / 12.B**:
总纲 §原则 12 规定的两类 HTML 输出。12.A = 数据/过程 HTML(80+ render 脚本替用户查/跑),文件名 `command_cn` 前缀。12.B = HELP HTML(Skill 自我介绍),文件名 `<skill 中文名>_HELP_` 前缀。

## File structure

单一上下文(single-context):
```
居家管家/
├── CONTEXT.md            ← 本文件,领域术语
├── SKILL.md              ← Skill 主文档,含 §📌 输出位置
├── docs/
│   └── adr/
│       └── 0001-local-time-over-utc-for-html-filenames.md
├── templates/            ← 10 个 HTML 模板(template_name)
├── scripts/
│   └── render/__init__.py ← template → command_cn 映射表在此
└── output/               ← gitignored,运行产物
```

HTML 输出根在 Skill 目录外,由 env 链解析:`$SKILLS_DATA_DIR` > `$SKILLS_DB_PATH` > Skill 自带 fallback。本 Skill 当前 fallback 解析到 `D:\.db\`,所以 HTML 输出实际在 `D:\.db\home_manager_html\`。
