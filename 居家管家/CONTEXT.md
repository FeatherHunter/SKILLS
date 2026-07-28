# 居家管家

家庭物品全生命周期管理 Skill。AI 解析自然语言,Python CLI 执行所有数据库读写,HTML 预览确认写入。

## Language

**Skill 标识**:
Skill 在跨 Skill 共享目录里用的唯一英文标识。本 Skill 取 `home_manager`(与 Python 包名一致),HTML 输出子目录为 `home_manager_html/`。(2026-07-28 grilling round 1 确认:此为本 Skill 约定,非偏离;等第 2 个 Skill 出现再升级到总纲 §CONTEXT.md。)
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

## 通用术语引用

本 Skill 不重复定义总纲 §CONTEXT.md 已收录的领域术语,只指向对应位置。下列 5 个通用术语的基础定义属于跨 Skill 工作(总纲 §CONTEXT.md 扩展),按 spec Q3 = C(双层)约定,本节先建指针,定义落地后跟随总纲。

| 术语 | 本 Skill 用途 | 总纲 §CONTEXT.md 对应位置 |
|------|--------------|------------------------|
| **5 状态 fallback** | HTML 模板必含 正常 / 空 / 缺数据 / 错误 / 离线 5 状态(本 Skill 全部 10 个模板已落地) | [`占位符注入`](../SKILL开发总纲V1.0/CONTEXT.md) 第 113 行 + [`4 段式模板`](../SKILL开发总纲V1.0/CONTEXT.md) 第 117 行(术语级条目待补) |
| **复制 prompt 按钮** | 过程型 HTML 必须让用户选择回到 AI(HTML 单工铁律 · 原则 10) | [`HTML 单工铁律`](../SKILL开发总纲V1.0/CONTEXT.md) 第 70 行(术语级条目待补) |
| **变体 (variant)** | 唤醒词配 2-3 个等价表达,覆盖 3 方向(同义 / 口语 / 模糊),本 Skill 在 `references/scenarios.yaml` 落地 | [`变体 (variant)`](../SKILL开发总纲V1.0/CONTEXT.md) 第 31 行(已收录) |
| **相对时间 helper** | "今天/昨天/最近 N 天"等相对时间词的统一解析(本 Skill 暂用 `scripts/routing.py` 局部实现,待总纲标准化) | 待补 |
| **跨 Skill 路由** | 用户意图跨多个 Skill(如物品价格→饼干记账)时的路由规则,本 Skill 联动逻辑在 `图片路由/SKILL.md` | 待补 |

> **状态(2026-07-28 grilling round 1)**:5 术语中,`变体` 已在总纲 §CONTEXT.md 收录;其余 4 个待总纲补录。本 Skill 不预定义,只建指针,避免与总纲同步漂移。
