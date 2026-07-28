# 备忘录 (Memorandum)

> 跨设备随手记录 · 结构化备忘 + 心愿 + 打卡 + 情绪追踪。
> 29 个业务唤醒词 + 1 个 HELP 唤醒词,SQLite 持久化 + 飞书 task 双向联动。

## 这是什么

备忘录是一个私人随手记录技能,把"想到就记"做到极致:你说口语化的一句,AI 帮你结构化成笔记 + 分类 + 子分类,需要时还能挂提醒、排期、媒体附件。它不是待办清单,不是笔记软件,而是"想到 - 说出 - 落地"的最短路径。

支持四类顶层分类:**备忘**(默认,日常记录)/ **心愿**(未来想做)/ **打卡**(已做到的事)/ **情绪日记**(情绪复盘)。每类下面可挂自由文本子分类(AI 智能推断 2 字)。心愿可自动同步飞书 task,完成时原子转换为打卡记录。

## 何时使用

**适合**:
- 通勤、走路、睡前想到一句话,不想打开 app 点 5 层菜单
- 心愿/想法需要排期、提醒、跨设备同步
- 习惯打卡、情绪周期复盘
- 跨 Skill 联动(卡路里训练完记一条、记账后记备注、作息日程归档)

**不适合**:
- 长文档写作(用笔记软件)
- 项目管理(用待办工具)
- 复杂数据分析(用表格)
- 需要团队协作的记录

对照卡路里(饮食) / 饼干记账(财务) / 居家管家(物品) / 作息管家(日程) — 各自独立 skill,通过共同唤醒词约定触发联动,不共享代码。

## 快速开始

1. **读 SKILL.md** — AI 决策用完整规范(1038 行),Agent 必读
2. **跑测试** — `cd 备忘录 && python -m pytest`(185 用例 · 17 秒 · 全过即可用)
3. **看帮助** — `python script/memo_cli.py help` 生成可视化 HTML 手册(覆盖 skill 根 `备忘录.html`)

新维护者:先读 `AGENTS.md`(26 行精炼入口) → 读 `README.md`(本文档) → 跑 `.scratch/grilling-alignment/verify.ps1` 一键验收。

## 文件清单

```
备忘录/
├── SKILL.md              # AI 决策用完整规范(1038 行 · SoT)
├── AGENTS.md             # Agent 入口(26 行 · 项目定位/路径/决策/commit/HTML)
├── README.md             # 本文档(新人 onboarding)
├── CONTEXT.md            # 术语表(唤醒词/场景/4 元/4 段 prompt 等)
├── CHANGELOG.md          # 变更日志(每个版本含 Tested-By)
├── _meta.json            # 版本号镜像(SoT 为 SKILL.md frontmatter)
├── pytest.ini            # pytest 配置(6 项 · --strict-markers)
├── 备忘录.html            # SKILL.md 镜像(memo_cli help 自动生成)
├── script/               # 5 个 Python 模块
│   ├── memo_cli.py       # CLI 入口(add/search/update/delete/.../help)
│   ├── memo_render.py    # HTML 渲染器(6 个 render_* 函数)
│   ├── injector.py       # HTML 注入器(私有 · v1.1.0 教训)
│   ├── feishu_sync.py    # 飞书 task 双向对账
│   └── reminder_scheduler.py  # Cron 提醒调度
├── templates/            # 6 个 HTML 模板
│   ├── memo_help.html        # HELP 手册(4 状态 fallback)
│   ├── memo_query.html       # 结果型查询页(复制按钮 + 富内容)
│   ├── sync_report.html      # 同步报告(11 字段 + 3 步折叠)
│   ├── wish_plan.html        # 过程型:心愿排期向导
│   ├── wish_complete.html   # 过程型:心愿完成向导
│   └── change_category.html # 过程型:批量改分类向导
├── references/           # 场景资产 + 参考文档
│   ├── scenarios.yaml    # 唯一事实源(29 场景 × 7 字段)
│   ├── schema.md         # 数据库结构
│   ├── examples.md       # 对话示例
│   └── cron.md           # Cron 配置
├── tests/                # 13 个 test_*.py(185 pytest · CLI 子进程主 seam)
├── docs/adr/             # 5 个永久 ADR(B/A/D 各阶段决策归档)
│   ├── 0001-version-sot.md
│   ├── 0002-skill-md-dedup-and-dir-merge.md
│   ├── 0003-b-execution-fallback.md
│   ├── 0004-a-structure-files.md
│   └── 0005-d-exemptions-and-rituals.md
└── .scratch/<feature>/  # 临时工作目录(A.4 5 文件范式)
    └── grilling-alignment/  # v1.1.5 整体重构工作目录
```

## 状态

- **版本**:1.1.5(2026-07-28 发布 · git tag `v1.1.5`)
- **测试基线**:185 passed + 1 xfailed(README.md 落地后转 pass)
- **commit 格式**:全中文硬规则(`[备忘录] <主题> · <细节>` + `Tested-By:` 行末,详见 `docs/adr/0003` + `0005`)
- **FAT 协议**:`exempt`(无 fresh agent,详见 `docs/adr/0005` D.1)
- **已知问题**:无(v1.1.5 整体重构后无回归)
- **HTML 镜像**:`备忘录.html` 由 `memo_cli.py help` 自动生成,`.githooks/pre-commit` 自动还原测试副产物
