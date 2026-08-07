---
name: 备忘录
version: 1.2.1
status: active
description: 跨设备随手记录 · 结构化备忘 + 心愿 + 打卡 + 情绪追踪
last_updated: 2026-08-07
---

# 备忘录 (Memorandum)

> **当前版本:1.2.1**(2026-08-07 · git tag `v1.2.1` · SoT 对齐:1.2.0 元数据欠账修复,内容与 CHANGELOG 1.2.1 一致)
> v1.2.0:HELP HTML 4 级重构 + 首次使用模块(wayfinder #30 map · ADR-0007)
> v1.1.5:整体重构(规范合规化 · B+A+D 三阶段 23 决策落地 · 术语统一 + 结构文件 + 工程仪式)
> v1.1.4:备忘录 HELP 唤醒词(总纲 §07 契约 · 场景资产 + HELP HTML + skill 根目录覆盖)
> v1.1.3:复制按钮改造(文案简化 + 富内容 + 视觉反馈)
> v1.1.2:HTML 交付 checklist 化(checkbox + 回复模板)
> v1.1.1:HTML 交付规范加强(主动发送是核心,Chrome 打开是加分)
> v1.1.0:修复 _shared/injector.py 被清理后 --html 跑不动的真实运行时 bug
> v1.0.9:备忘录.html 转为"纯用户手册"(从 SKILL.md 镜像分离)
> v1.0.8:HTML 镜像设计原则 + 唤醒词段可展开底层原理
> v1.0.7:唤醒词 → HTML 生成对照表 + 文档裂缝守护
> v1.0.6:命名 + 输出目录规则同步到通用手册(跨 Skill)
> v1.0.5:HTML 输出目录 = DB_PATH.parent / memo_html/(与 DB 同级)
> v1.0.4:心愿完成 HTML 默认未勾选(正向操作第一性)
> v1.0.3:HTML 交付规范纠正(`<media>` + 浏览器并行)
> v1.0.2:HTML 交付规范初版(过度禁止已纠正)
> v1.0.1:wish-complete 第一性修复
> 详见 `CHANGELOG.md`

## 改动前 3 问(总纲 §05 L5-11 · 强制肉眼自检)

每次改动前必答(可不写下来,但要在脑子里过):

1. **影响哪些文件?** — 列出本次改动涉及的所有文件路径
2. **数据迁移?** — 是否需要 schema 变更 / 数据迁移 / 兼容老版本?
3. **回滚方案?** — 如果改动有 bug,如何 revert? 是否会丢数据?

豁免: 仅文档/注释/comment 改动可豁免(如本段本身的修订)

## 强制性规定(最高优先级)

1. **HTML 同步**:该技能的所有优化和变动、脚本的所有变动都必须体现在 `备忘录.html` 上。
   - **v1.1.4 起**:`备忘录.html` 不再手写,**由 HELP 命令自动生成并覆盖**(总纲 §07 契约 + 用户约定)。
   - 时间戳副本:`D:\.db\memo_html\备忘录_HELP_<YYYYMMDD>_<HHMMSS>.html`(§04 原则 12.B)
2. **优先级**:本规定优先级最高,高于所有其他规范。
3. **用户确认**:对该技能的所有文件、脚本的任何一行修改,都需要明确得到用户的 1 次确认后才能执行。

## HTML 镜像设计原则(v1.0.8 · 最高优先级 · 用户认知转变)

**备忘录.html 的真实定位**:**用户手册**(用户视角) + **可展开底层原理**(技术视角) · **不是日志/改动记录**

| 内容 | 在哪看 |
|---|---|
| 用户视角:唤醒词 + 使用方法 + 注意事项 | `备忘录.html`(默认展开) |
| 技术视角:CLI 命令 / SQL / Python 代码 / 流程 | `备忘录.html` `<details>` 折叠区 |
| 改动日志 / 版本历史 / 变更明细 | `CHANGELOG.md`(不要混到 HTML) |
| AI 阅读的统一权威源 | `SKILL.md`(HTML 镜像源) |

**可展开详情语法**(每个唤醒词段下方):

```markdown
<details>
<summary>🔍 查看底层原理</summary>

**CLI**: `...`
**SQL**: `...`
**返回 JSON**: `...`
**失败路径**: `...`
**原子性 / 副作用**: `...`
</details>
```

**为什么这样设计**:
- 用户看 HTML 找"我能用什么 / 怎么用",不需要看 SQL
- 探究层原理时,点开 `<details>` 看到 CLI/SQL/代码,**渐进式信息披露**
- 改动日志在 CHANGELOG.md(独立文件),不污染用户手册
- HTML 仍是 SKILL.md 镜像(AI 阅读统一权威源)

## HTML 交付规范(2026-07-24 加 · 最高优先级 · v1.0.3 修订 · v1.1.1 加强)

**v1.1.1 加强**(2026-07-25 · 用户反馈):
浏览器打开 ≠ 主动交付。用户可能不在 Chrome 前面看,
而是手机/微信/飞书/QQ 等。**AI 必须主动把 HTML 文件通过用户当前可用的工具发送出去**——浏览器打开是加分项,主动发送是核心。

**HTML 输出目录规则**(v1.0.5):

```
HTML_DIR = DB_PATH.parent / f"{SKILL_HTML_NAME}_html"
```

- HTML 是 DB 的快照视图 → 与 DB 在同一目录
- `SKILLS_DB_PATH` 环境变量 / fallback 都生效(`D:/.db/` 或 `/mnt/d/.db/`)
- 备忘录的 `SKILL_HTML_NAME = "memo"` → 例子:`/mnt/d/.db/memo_html/`
- **实际路径** = `<SKILLS_DB_PATH>/memo_html/`,**受环境变量影响**
  - `SKILLS_DB_PATH` 未设 + Windows → `D:\.db\memo_html\`
  - `SKILLS_DB_PATH` 未设 + WSL/Linux → `/mnt/d/.db/memo_html/`
  - `SKILLS_DB_PATH=/tmp/test` → `/tmp/test/memo_html/`
- 多 skill 共用 SKILLS_DB_PATH 时,按 skill 子目录隔离
- 同秒内多次生成同一文件,自动追加 `_2` / `_3` 后缀(冲突保护)

**命名规则**(v1.0.5 明确化):

```
<command_name>_<YYYYMMDD>_<HHMMSS>[_<N>].html
```

- `command_name`:CLI 子命令名(5 个模板对应 5 个命令)
- `YYYYMMDD_HHMMSS`:本地时间
- `_<N>`:冲突保护(可选,如 `_2` / `_3`)

---

下面是 5 个 HTML 模板(`memo_query.html`/`sync_report.html`/`wish_plan.html`/`wish_complete.html`/`change_category.html`)生成后,**AI 代理必须遵守的交付协议**:

1. **必须用 `<media src="..." type="file" />` 标签交付 + 主动发送给用户**(基础动作 · v1.1.1 加强,v1.1.2 checklist 化)。
   - 这是《预置HTML并注入数据指导手册》§4 + §9(标准工作流最后一步)规定的标准交付方式
   - HTML 内嵌 JS + clipboard + textarea,有交互,**内联展示会丢失交互**(所以内联禁止)

### ⚠️ HTML 交付 checklist(v1.1.2 · 任务结束前必走一遍)

**触发场景**:任何生成 HTML 的命令(13 个会触发的命令,见 §唤醒词速查表)

**任务结束前必走 checklist**:
- [ ] HTML 文件路径已生成?(是 → 继续;否 → 重新跑命令)
- [ ] 我用什么消息工具主动发送?(飞书/微信/QQ/邮件)
- [ ] 用户能在他的设备上收到?
- [ ] 我没有"只输出路径就结束"吧?

**AGENT 回复模板(必须含全部 · 不要省略)**:

```
✅ [已生成 X]
   文件路径: <HTML 路径>
   我主动发送到了: [QQ/微信/飞书/邮件] ← 必含,不能只给路径
   (Chrome 已打开做本地预览 · 可选)
```

**反例(以下都是不合格)**:
- ❌ "HTML 已生成在 /path/to/..."(只给路径,没主动发送)
- ❌ "你可以打开 Chrome 看"(推给用户不主动)
- ❌ "Chrome 已打开"(只提加分项,缺主动发送)

---

## 用户原话 → 唤醒词 反向指引表(v1.1.4 · FAT G3 修复)

**目的**:消除"用户口语化表达 → 哪个唤醒词"的歧义。FAT 实测 AI 缺乏反查表时易误判。

**第一原则**(优先级):
1. **意图优先**:用户语义决定唤醒词,不靠字面死匹配
2. **子唤醒词优先**:用户说"心愿/打卡/情绪"时,优先用对应子唤醒词(自动带分类)
3. **同义触发**:口语化变体走同一个唤醒词

| # | 用户原话(口语化) | 唤醒词 | CLI 命令 |
|---|---|---|---|
| 1 | "帮我记一下:今天开了个会" / "备忘一下 xxx" / "写下 xxx" | 记备忘 | `add` |
| 2 | "搜一下 xxx" / "找 xxx" / "看下有哪些备忘" | 搜备忘 | `search` |
| 3 | "改一下 #15" / "把这条改成 xxx" | 改备忘 | `update` |
| 4 | "删掉 #15" / "这条不要了" | 删备忘 | `delete` |
| 5 | "看下 #15 的详情" / "#15 是什么" | 看备忘 | `get` |
| 6 | "上周做了什么" / "7月1号到7月7号备忘" | 按时间搜备忘 | `search-date` |
| 7 | "我想学 Python" / "心愿:健身" / "想要 xxx" | 记心愿 | `add -c 心愿` |
| 8 | "这条心愿做完了" / "#15 完成" / "完成 #15" | 完成心愿 | `wish-complete` 或 `complete-wish` |
| 9 | "心愿放到 7/3 完成" / "给心愿设排期" / "#15 7月3号" | 心愿排期 | `set-due` 或 `wish-batch-plan` |
| 10 | "提醒我 xxx" / "明早 9 点叫我" / "设个闹钟" | 记提醒 / 设提醒 | `add` + `remind` 或 `remind` |
| 11 | "看下提醒" / "还有什么提醒" / "今天的提醒" | 看提醒 | `reminders` |
| 12 | "把 X 都改成 Y" / "X 分类下都改 Y" / "批量改分类" | 备忘改分类(批量) | `batch-update-category` |
| 13 | "把 #15 改成心愿" / "改这条的分类" | 备忘改分类(单条) | `update-category` |
| 14 | "和飞书对账" / "飞书那边同步一下" / "同步" | 备忘录同步 | `sync-from-feishu` |
| 15 | "备忘录怎么用" / "使用说明" / "help" / "manual" / "指南" | 备忘录 HELP | `help` |

**反查步骤**(AI 处理时):
1. 用户原话 → 找最接近的"用户原话"行
2. 命中行 → 用对应唤醒词 + CLI 命令
3. 多义时 → 看上下文(数字 ID / "都/全部" / "刚刚")
4. 不命中 → 反问用户

**不命中场景**(反例):
- ❌ "你在吗" → 不触发任何
- ❌ "今天的日期" → 不触发(虽然有"今天"字样,但无备忘录意图)
- ❌ "我要睡了" → 不触发(无明确意图)

---

**v1.1.1 加强(背景)**:`<media>` 不够 —— 用户可能在手机/微信/飞书/QQ 等,**AI 必须主动把 HTML 文件发送出去**:
- 不能假设用户就在 Chrome 前看
- 发送工具不硬编码:用户用飞书就发飞书、用 QQ 就发 QQ、用邮件就发邮件 —— AI 自己判断用户当前可用的工具
- **HTML 必须到用户手上是硬规定**(方式可灵活)

2. **强烈推荐:主动发完之后,并行用 Chrome 等系统默认浏览器打开**(加分项 · v1.1.1 重排)。
   - 用户场景:用户在 IDE 里用 `<media>` 预览的同时,Chrome 窗口也打开了
   - 好处:Chrome 渲染 JS / 持久化窗口 / 多窗口并存 / 移动设备同步
   - 实现方式:AI 可调用 IDE/平台提供的 open file 工具或 subprocess + 系统默认应用
   - **不冲突**:`<media>`(IDE 内嵌)与 Chrome(系统浏览器)是**两个独立通道**,并行不冲突

3. **禁止**:
   - ❌ 只输出文件路径文字让用户"自己去打开"(用户必须去 bash terminal 复制粘贴,体验差)
   - ❌ 内联读 HTML 全部内容塞进对话(交互丢失 + 上下文中毒)
   - ❌ 备注 "AI 建议你用 Chrome 打开"等绕过 `<media>` 的指引(应该直接做,不要"建议")

4. **正确做法**(并行交付,举例):
   ```
   找到 3 条心愿。
   [html 路径: ${SKILL_DIR}/output/心愿排期_20260724_HHMMSS.html]
   <media src="${SKILL_DIR}/output/心愿排期_20260724_HHMMSS.html" type="file" />
   + AI 同步:用系统默认浏览器(Chrome 等)打开同一文件
   ```

5. **唤醒词场景对应交付协议**(每个都 `<media>` + 浏览器并行):
   - 5 个查询唤醒词(搜备忘/查备忘/看备忘/按时间搜备忘/查已提醒备忘 + 子唤醒词查心愿/查打卡/查情绪):AI 推荐 `--html` 后并行
   - 备忘录同步(sync-from-feishu `--html`):同上
   - 心愿排期向导(wish-batch-plan `--html`):用户勾选 + 复制 + 粘贴回 AI,**第一步并行**
   - 心愿完成向导(wish-complete `--html`):同上
   - 批量改分类向导(batch-update-category `--html`):同上

6. **优先级**:本规范与"HTML 同步"同级(最高优先级)。

7. **历史修订**:
   - v1.0.2(2026-07-24):最初版,误写"绝对禁止 AI 主动唤起浏览器"
   - v1.0.3(2026-07-24):纠正 — 用户确认 `<media>` 与浏览器打开应并行,**非互斥**

---

## 唤醒词 → HTML 生成对照表(2026-07-24 加 · v1.0.7 · 最高优先级)

**目的**:消除"AGENT 是否要生成 HTML"的歧义。28 个唤醒词明确分类,AI 不再从叙述中"凑"出完整图。

**图例**:
- ✅ **必须生成 HTML**(AI 收到 JSON 后**主动**调 `--html`,再 `<media>` 交付)
- ❌ **不生成 HTML**(只返回 JSON 三段式简短回执,文字流展示)
- 🟡 **过程型 HTML**(必须生成,用户在 HTML 里勾选+复制+粘贴)

| # | 唤醒词 | HTML? | 命令 | 模板 / 备注 |
|---|---|---|---|---|
| 1 | 记备忘 | ❌ | `add` | 单条回执 |
| 2 | 搜备忘 | ✅ | `search --html` | `memo_query.html` |
| 3 | 查备忘(搜备忘别名) | ✅ | 同上 | 同上 |
| 4 | 改备忘 | ❌ | `update` | 单条回执 |
| 5 | 删备忘 | ❌ | `delete` | 单条回执 |
| 6 | 看备忘 | ✅ | `get --html` | `memo_query.html`(items 1 条) |
| 7 | 按时间搜备忘 | ✅ | `search-date --html` | `memo_query.html` |
| 8 | 备忘改分类(单条) | ❌ | `update-category <id> <cat>` | 单条回执 |
| 9 | 备忘改子分类 | ❌ | `update-sub-category` | 单条回执 |
| 10 | 记提醒 | ❌ | `add` + `remind` | 双步骤简短回执 |
| 11 | 设提醒 | ❌ | `remind` | 单条回执 |
| 12 | 看提醒 | ✅ | `reminders --html` | `memo_query.html` |
| 13 | 查已提醒备忘 | ✅ | `completed --html` | `memo_query.html` |
| 14 | 记心愿(子唤醒词) | ❌ | `add -c 心愿` | 单条回执 |
| 15 | 删心愿 | ❌ | `delete` | 单条回执 |
| 16 | 改心愿 | ❌ | `update` | 单条回执 |
| 17 | 查心愿 | ✅ | `search -c 心愿 --html` | `memo_query.html` |
| 18 | 记打卡(子唤醒词) | ❌ | `add -c 打卡` | 单条回执 |
| 19 | 删打卡 | ❌ | `delete` | 单条回执 |
| 20 | 改打卡 | ❌ | `update` | 单条回执 |
| 21 | 查打卡 | ✅ | `search -c 打卡 --html` | `memo_query.html` |
| 22 | 记情绪(子唤醒词) | ❌ | `add -c 情绪日记` | 单条回执 |
| 23 | 删情绪 | ❌ | `delete` | 单条回执 |
| 24 | 改情绪 | ❌ | `update` | 单条回执 |
| 25 | 查情绪 | ✅ | `search -c 情绪日记 --html` | `memo_query.html` |
| 26 | 完成心愿(别名:完成打卡) | 🟡 | `wish-complete --html` | `wish_complete.html`(过程型) |
| 27 | 心愿排期 | 🟡 | `wish-batch-plan --html` | `wish_plan.html`(过程型) |
| 28 | 备忘录同步 | ✅ | `sync-from-feishu --html` | `sync_report.html` |
| - | **备忘改分类(批量)**(由"备忘改分类" + "都/全部/多 id" 触发) | 🟡 | `batch-update-category --from-category X --html` | `change_category.html`(过程型) |
| 29 | **备忘录 HELP** | ✅ | `memo_cli.py help` | `memo_help.html`(HELP 自描述 · **不展示自身**) |

### 统计

| HTML? | 数量 | 唤醒词 |
|---|---|---|
| ✅ 必须生成 HTML | 10 | 搜备忘/查备忘/看备忘/按时间搜备忘/看提醒/查已提醒备忘/查心愿/查打卡/查情绪/备忘录 HELP |
| 🟡 过程型 HTML | 4 | 完成心愿(完成打卡)/心愿排期/备忘改分类(批量)/(批量场景) |
| ❌ 不生成 HTML | 15 | 记备忘/改备忘/删备忘/备忘改分类(单条)/备忘改子分类/记提醒/设提醒/记心愿/删心愿/改心愿/记打卡/删打卡/改打卡/记情绪/删情绪/改情绪 |
| **合计** | **29** | (含 12 个子唤醒词) |

### AGENT 决策流程

```
收到用户原话 → 路由到唤醒词 → 查本表
  ├─ ✅ → CLI 命令 + 调 --html → <media> 交付
  ├─ 🟡 → CLI 命令 + --html(过程型) → <media> 交付 + 用户采纳复制 → 调精确命令
  └─ ❌ → CLI 命令 → 返回 JSON 三段式 → 文字流回执
```

### 优先级

本对照表与"HTML 同步"+"HTML 交付规范"同级(最高优先级)。任何 AGENT 处理备忘录相关唤醒词必须先查本表。

### 防文档裂缝守护

`tests/test_html_trigger_coverage.py` 扫描 SKILL.md + 本表,确保所有 29 个唤醒词(含 HELP)在本表出现。改 SKILL.md 时自动验证。

---

## 描述

私人备忘工具,支持随时记录、分类整理、时间检索、媒体附件、定时提醒和打卡追踪。

**唤醒词**:记备忘、搜备忘、查备忘、改备忘、删备忘、看备忘、按时间搜备忘、备忘改分类、备忘改子分类、记提醒、设提醒、看提醒、查已提醒备忘、完成心愿(**别名:完成打卡 · 2026-07-24 加**)、心愿排期、备忘录同步、**首次使用**(v1.2.0 加 · **别名:初始化 / 新手** · 触发层在 SKILL.md,scenarios.yaml 只存主词 #31 Q1)、**备忘录 HELP**(v1.1.4 加 · 总纲 §07 契约)

**分类子唤醒词**(心愿/打卡/情绪日记,自带顶层分类,操作同上):
- 记心愿、删心愿、改心愿、查心愿
- 记打卡、删打卡、改打卡、查打卡
- 记情绪、删情绪、改情绪、查情绪(情绪日记的子唤醒词)

## 快速开始

复制以下 prompt 给 AI 安装技能:

```
请帮我初始化备忘录,我是第一次使用(唤醒词:首次使用):
1. 检查环境:运行环境、数据存储、飞书联动(可选),缺什么逐项告诉我
2. 初始化数据库:建好备忘录的数据表
3. 引导我配置数据目录和媒体目录
4. 配置提醒调度:让我设的备忘提醒能按时推送
5. 完成后报告就绪情况,并带我浏览一遍全部功能
```

> v1.2.0:快速开始 prompt 与 Init 场景(首次使用)统一为**唯一入口**。原 prompt 暴露 `script/init.sql` 路径违反 prompt 契约(§07 §3),已废弃。AI 收到「首次使用 / 初始化 / 新手」均走同一初始化流程,诊断复用现有命令,不新增 CLI 子命令。

### 首次使用行为规范

AI 命中「首次使用 / 初始化 / 新手」时,按以下规则执行。**核心:引导式环境搭建 —— 检测 → 安装/配置 → 验证 → 下一步,假设用户环境可能什么都没做,每步必须给出可执行指引,不允许只报告「缺什么」而不给「怎么装」。**

**执行前提**:
- **先定位 SKILL 目录**:找到包含 `script/memo_cli.py` 的目录,记为 `${SKILL_DIR}`(AI 加载 SKILL.md 时已知技能目录;不确定时询问用户或搜索 `memo_cli.py`)
- 下文所有相对路径均基于 `${SKILL_DIR}` 执行

**执行原则**:
- 每步:先检测 → 缺失/未就绪 → **优先自动化安装**(包管理器,用户同意后 AI 直接执行)→ 自动失败 → 给手动指引 → 验证 → 下一步
- **检测必须全面,禁止误判「没装」**:PATH 命令找不到 ≠ 没装。依次探测:① PATH 命令 → ② 常见自定义安装路径(`C:\Python3*` / `%LOCALAPPDATA%\Programs\Python\Python3*` 等)→ ③ 包管理器查询(`winget list Python` / `brew list python`)。全部找不到才算「没装」
- **自动安装优先(Windows)**:用户同意后直接用包管理器安装:
  - Python:`winget install Python.Python.3.12 --scope user`(或 3.11/3.13)
  - Node.js:`winget install OpenJS.NodeJS.LTS --scope user`
  - 包管理器不可用或安装失败 → 才给手动指引(python.org / nodejs.org 下载,勾选 Add to PATH)
- macOS:`brew install python@3.12` / `brew install node`;Linux:发行版包管理器(apt/dnf/pacman)
- **并行原则**:多个独立缺失(如 Python + Node)→ 并行执行安装,不要串行等待
- **禁止编造规则**:所有行为约束以 SKILL.md 为唯一依据;SKILL.md 未禁止的操作不自行发明「禁止」借口
- **winget 探测协议**:执行 winget 前先定位:① `Get-Command winget` → ② 探测 `%LOCALAPPDATA%\Microsoft\WindowsApps\winget.exe`;找不到可用 winget → 转手动指引
- **安装后 PATH 刷新协议**:任何安装器装完 Python/Node,**当前会话 PATH 不会刷新**,同会话立刻验证必然失败。必须:① `cmd /c "python --version"` 用新解析的 PATH 验证,或 ② 用刚安装的完整路径直接验证,或 ③ 提示用户「新开终端再验证」;**禁止**在安装后同会话直接 `python --version` 判失败
- 任何一步失败 → 报告页标 err/warn + 在「待办指引」给具体下一步,不静默跳过
- 完成后生成初始化报告页(init-report CLI)+ 逐项验证清单

**逐步流程**:

1. **Python 运行环境**(3.10+ 必装):
   - 检测:`python --version` → 常见自定义路径探测(`C:\Python3*` / `%LOCALAPPDATA%\Programs\Python\Python3*` 的 python.exe 直接跑)→ `winget list Python`
   - **找到可用 Python 且 ≥3.10 → 直接用它的完整路径执行后续步骤**(不需要它进 PATH)
   - 确认缺失 → 自动安装:`winget install Python.Python.3.12 --scope user`(用户同意后 AI 执行);winget 不可用 → 手动指引 python.org 下载(勾选 Add to PATH)
   - 验证(按 PATH 刷新协议):用安装路径直接跑 `python.exe --version`,或 `cmd /c "python --version"`,或提示用户新开终端;确认 ≥3.10 才进入下一步
2. **数据存储(SQLite + FTS5)**(Python 内置,验证即可):
   - 检测:`python -c "import sqlite3;conn=sqlite3.connect(':memory:');conn.execute('CREATE VIRTUAL TABLE t USING fts5(x)')"`
   - FTS5 不可用 → 指引重装/换发行版(Python 官方构建含 FTS5)
3. **飞书 CLI(@larksuite/cli ≥1.0.59)**(默认安装 + **强烈建议配置**,不默认跳过):
   - **官方文档(遇到问题先查)**:https://open.feishu.cn/document/mcp_open_tools/feishu-cli-let-ai-actually-do-your-work-in-feishu(安装/授权/FAQ 全在;官方安装指南:https://open.feishu.cn/document/no_class/mcp-archive/feishu-cli-installation-guide.md)
   - 检测:`python ${SKILL_DIR}/script/feishu_sync.py check`(输出 JSON:available/cli_path/auth)
   - ⚠️ **包名陷阱**:官方包是 **`@larksuite/cli`**(bin 名恰为 `lark-cli`);npm registry 上的 `lark-cli` 是 2017 年僵尸包(0.1.0,无 auth 命令),**严禁指引安装 `lark-cli`**
   - **先说明为什么强烈建议配**:飞书联动是备忘录的核心能力 —— 心愿自动生成飞书任务、备忘录同步(双向对账)。**不配 = 这两个核心功能不可用**
   - 未安装 → **直接引导安装**(默认路径,不问「要不要装」):
      a. 检测 Node.js:`node --version`(需 ≥ 18;可用 `cmd /c "node --version"` 或探测 `%APPDATA%\npm\node.exe` 等路径);未装 → **自动安装** `winget install OpenJS.NodeJS.LTS --scope user`(winget 不可用 → nodejs.org 手动)
      b. 安装 CLI:`npm install -g @larksuite/cli`(**AI 直接执行**;npm 不在 PATH → 用完整路径 `%ProgramFiles%\nodejs\npm.cmd` 或新会话验证)
      c. **安装 CLI SKILL**:`npx -y skills add https://open.feishu.cn --skill -y`(**AI 直接执行**)—— 官方 Required,跳过会导致快捷命令不可用
      d. 验证:`lark-cli --version` 可执行;`lark-cli auth status` 能输出 JSON(仅验证 CLI 工作,授权另看下一步)
   - **配置 app(先让用户选场景)**:
      - **必须先于 auth login**:无 app 配置时 `auth login` 直接失败(not_configured)
      - **⚠️ 强制非阻塞模式(2026-08-04 增 · 第一性原理)**:
        - **根因**:AI 工具 timeout 是秒级(2-5 分钟),用户浏览器操作是分钟级(1-10 分钟),时间维度不匹配。**AI 同步阻塞等用户操作 = 必被强杀**。
        - **正解**:lark-cli 1.0.82+ 提供了非阻塞多轮协议(`--no-wait --json` 拿 device_code + `--device-code` 续轮询)。**AI 必须用这个模式**,不要直接跑同步阻塞的 `lark-cli config init --new`。
        - **标准入口**:`scripts/feishu_auth_helper.py`(本 SKILL 自带,封装 3 个非阻塞函数,物理上不暴露同步阻塞 API):
          - `init_app()` → 调 `lark-cli config init --new --no-wait --json`,秒返,拿 device_code + verification_url
          - `generate_qr(url, out_path)` → 调 `lark-cli auth qrcode`,生成 PNG
          - `poll_auth(device_code, domain)` → 调 `lark-cli auth login --device-code <code>`,用户"好了"后调
        - **4 轮交互流程**:
          1. AI 调 `init_app()` → 拿 `device_code` + `verification_url`
          2. AI 调 `generate_qr(url)` → 拿 QR PNG 路径
          3. AI 把 `verification_url` + `<media src=QR_PNG />` 发给用户,**本轮结束**(等用户操作,时间不在 AI 控制范围)
          4. 用户回"好了" → AI 调 `poll_auth(device_code, "task")` → 成功
        - **绝对禁止**:
          - ❌ `subprocess.run(["lark-cli", "config", "init", "--new"])` 不带 `--no-wait`(会卡到 timeout)
          - ❌ 给 lark-cli 相关命令设任何 timeout(包括 `run_in_background: true` + `timeout: N`)
          - ❌ 同一个 device_code 跑两次 init(第二次会让第一次作废)
      - **场景 A · 用户从未创建过 app** → 走上面"强制非阻塞模式",**不要同步阻塞跑**:
        - AI 调 `init_app()` + `generate_qr()` → 拿 device_code + URL + QR
        - AI 把 URL + QR 发给用户(扫码或点链接都行)
        - 等用户回"好了" → AI 调 `poll_auth(device_code, "task")`
        - **提醒用户**:「扫二维码(或点链接)在飞书里点同意,完了回来说一声」
      - **场景 B · 用户已有 app** → 用户提供 App ID + App Secret,非交互配置:
        - 引导用户到飞书开放平台开发者后台(open.feishu.cn)→ 应用列表 → 找到自己的应用 → 复制 App ID 和 App Secret
        - 配置:`echo "<App Secret>" | lark-cli config init --app-id "<App ID>" --app-secret-stdin`(Secret 从 stdin 读,不暴露进程列表)
      - 若在 OPENCLAW_HOME/HERMES_HOME 已设的环境运行,CLI 会拒绝 init,改用 `config bind` 绑定环境已有 app
   - **用户授权(必须用户本人操作,同样走非阻塞模式)**:
      - **必须完成,不可按官方「可选」跳过**:此步开启「以你的身份操作」模式(AI 访问你的个人数据、以你名义执行);备忘录的飞书联动(心愿→飞书任务、备忘录同步)依赖你的用户身份(任务 assignee 是你,同步按你的 open_id 匹配),跳过 = 这两个核心功能不可用
      - **执行**(强制非阻塞,与配置 app 同理):
        - AI 调 `init_app()`(如果还没创建 app)→ `generate_qr()` → 发用户 → 等"好了" → `poll_auth(device_code, "task")`
        - **必须传 `--device-code`**,不能直接 `lark-cli auth login --domain task` 同步跑(会卡死)
        - `--domain` 按需授予对应域权限;`--recommend` 在 poll_auth 调用前由 `init_app` 后的 user 决定
      - **备忘录需要的权限域**:`task`(心愿→飞书任务、备忘录同步,必授)+ `calendar`(日程,若用户要用飞书日历);缺哪个域补哪个:重新走一遍 `init_app` + `poll_auth(domain="calendar")`
      - **对用户讲清**:「这一步让备忘录以你的身份在飞书创建/同步任务;跳过则心愿→飞书、备忘录同步不可用」
      - 授权验证:
        a. `python ${SKILL_DIR}/script/feishu_sync.py check` → `auth: true`
        b. 真实 API 探测:`lark-cli task +get-my-tasks`,返回 `ok: true` = 授权真实可用;报错(如 token 过期/权限不足)→ 重新走 `init_app` + `poll_auth(device_code, "task")`
      - 权限不足:重跑 `init_app` + `poll_auth(device_code, domain="<缺失权限>")`
      - 授权码过期(默认 10 分钟):重跑 `init_app` 拿新 device_code,旧 device_code 自动作废
   - **只有用户明确拒绝**(如「不用飞书」「跳过」)才标 warn 跳过 —— 但必须**醒目告知功能残缺**:心愿→飞书、备忘录同步 两个核心功能不可用,后续想用时说「配置飞书」即可补装
4. **环境变量 + 数据位置**(SKILLS_DB_PATH / MEMO_MEDIA_DIR) —— **主动告知,不强制配置**:
   - **告知数据在哪**(知情权):备忘录的所有数据 = 1 个 SQLite 文件(memo.db)+ 媒体目录。默认位置(客观事实):
     - Windows:`D:\.db\memo.db` + `media\`(多技能共用目录)
     - Linux/macOS:`~/.local/share/memo/memo.db`(无 /mnt/d 时)+ `media\`
   - **说明可配置性**:环境变量可不设(默认位置功能完全正常);若用户想自定义目录(备份/迁移/个人偏好),可设置 `SKILLS_DB_PATH` / `MEMO_MEDIA_DIR`
   - **不强制选择,不推荐外部路径**:用户无偏好 → 保持默认,不打扰;用户主动要求配置 → 按**用户给的路径**设置(用户级持久化):
     - Windows:`setx SKILLS_DB_PATH "用户指定路径"` / `setx MEMO_MEDIA_DIR "用户指定路径"`(用用户路径替换)
     - macOS/Linux:写入 ~/.zshrc 或 ~/.bashrc 后 `source`
   - **报告页明示数据位置**:完成时在报告页写明「数据位于 <实际路径>」,并提示「想改位置说『移动备忘录数据』」—— 留改的口子,不阻塞初始化
   - ⚠️ **禁止把作者机器约定路径(如 D:/.db、D:/media)作为推荐** —— 只能作为「默认位置」客观陈述;AI 也不自作主张推荐其他具体路径(如 D:\MyData),路径应由用户主动决定
5. **数据库初始化**:
   - 检测:数据表是否就绪(通过 memo_cli 任意命令试探,如 `${SKILL_DIR}/script/memo_cli.py search ""` 不报错即就绪)
    - 未就绪 → 建表(memo_cli 无内建建表入口):
      - AI 执行:`python -c "import sqlite3;c=sqlite3.connect('<DB 路径>');c.executescript(open(r'${SKILL_DIR}/script/init.sql',encoding='utf-8').read())"`
     - DB 路径 = 第 4 步确定的位置(SKILLS_DB_PATH 或默认位置)+ `memo.db`
   - 建表后验证:重跑 `search ""` 应返回 `{"status":"ok",...}`(不再报 no such table)
6. **提醒调度(Cron)**:
   - 说明:提醒由宿主平台定时任务触发(Windows 任务计划程序 / macOS launchd / Linux crontab),调用提醒检查命令
   - 无法在会话内验证 → 标 warn + 在待办指引给宿主差异说明
7. **过程 HTML + 回执**:以上全部完成后,调用 `${SKILL_DIR}/script/memo_cli.py init-report --data '<诊断结果 JSON>'` 生成初始化报告页(items 检查清单 + todos 待办 + verify 完成验证清单),发给用户;再给一句话总结
   - `--data` 数据契约:`{"items":[{name,status(ok/warn/err),desc,action}], "todos":[{title,steps:[str]}], "verify":[str]}`
    - status 取值:ok=就绪 / warn=可选缺失(cron 未验证等)/ err=必装缺失(Python、数据库等);**用户拒绝飞书 → 标 err 级醒目提示(核心功能残缺),但流程不阻断**
   - 报告页「完成验证清单」= 用户可勾选:Python 可运行 / 数据库已建 / 飞书已授权(强烈建议,用户明确拒绝才可不勾)/ 数据位置已确认(默认或自定义)/ HELP 页面可打开
8. **承诺↔兑现**:prompt 说的每项 → 报告页必须有对应物(检查项/待办/验证清单);缺失即流程断裂
9. **飞书强烈建议 + 拒绝不阻断**:飞书是核心联动能力,默认引导安装;**只有用户明确拒绝才跳过**,且报告页醒目标注「心愿→飞书、备忘录同步 不可用」,后续想用说「配置飞书」即可补装

**⚠️ Cron 任务特性**:
- 当有待提醒事项时 → 通过 message 工具发送到 QQ
- 当无提醒事项时 → 输出「NO_REPLY」静默,不发送任何消息
- 提醒检查由 SKILL 内部逻辑决定,cron payload 只触发执行,不描述判断结果

## 环境变量

| 变量名 | 必填 | 说明 | 默认 |
|--------|------|------|------|
| `SKILLS_DB_PATH` | 否 | 数据库根目录(多技能统一配置) | Windows `D:/.db` · Linux/macOS `~/.local/share/memo`(WSL 有 /mnt/d 则 `/mnt/d/.db`) |
| `MEMO_MEDIA_DIR` | 否 | 媒体文件目录 | `media`(相对当前工作目录) |

**注**:
- 没有 `MEMO_FEISHU_USER_OPEN_ID` -- 飞书 task assignee 自动从 `lark-cli auth status` 读取(lark-cli 已登录的用户就是 assignee)
- 没有 tasklist 环境变量 -- tasklist 由 `add --tasklist-guid <guid>` 每次显式传入(少用场景)

## 操作规范

- 所有操作通过 `script/memo_cli.py` 执行
- 提醒必须关联笔记,不可独立存在
- 媒体文件路径使用相对路径存储
- CLI 返回 JSON:`{"status": "ok/error", "data": ..., "message": "..."}`

### 媒体附件
- 参数:`--media <文件名>`
- 支持类型:图片(jpg/png/gif)、音频、视频
- 存储路径:`MEMO_MEDIA_DIR/` 目录下
- 示例:`script/memo_cli.py add "购物小票" -c 记账 --media slip_20260522.jpg`

## ⚠️ 重要约定:提醒路由

所有「提醒」类请求(无论是否以「备忘录」开头):
- **必须**走备忘录 CLI(先 add → 再 remind)
- **禁止**使用 qqbot_remind 或其他提醒工具
- 这是技能内置的强制路由规则

---

## 功能与唤醒词

### 添加笔记
- 唤醒词:记备忘
- 子唤醒词:记心愿、记打卡、记情绪日记(自带顶层分类,跳过分类确认)
- 命令:`script/memo_cli.py add "内容" [-c 顶层分类] [-s 子分类] [--due YYYY-MM-DD]`
- **顶层分类**(4 种):备忘(默认)/ 心愿 / 打卡 / 情绪日记
- **子分类**:自由文本字段,AI 智能从用户原话推断 → 见下方"sub_category 原则"
- **`--due`**(仅心愿生效,2026-07-13 改):
  - add 心愿时传 `--due YYYY-MM-DD` → 本地 note + 飞书 task + 飞书 task.due **1 次原子建好**
  - 与 title 同属"创建时即带"的核心字段,无需后续 `set-due` 补救
  - 不传/非心愿 → 静默忽略,无回归
- **AI交互规范**:添加前必须先问用户一个问题确认分类(如下示例),不得直接使用默认分类写入
  - 示例1:用户说「去医院」→ AI问「这个是工作相关还是心愿?」→ 用户选心愿 → 写入 `-c 心愿`
  - 示例2:用户说「今天运动」→ AI问「这是打卡还是心愿?」→ 用户选打卡 → 写入 `-c 打卡`
  - 示例3:用户说「今天心情很差」→ AI问「这是情绪日记还是心愿?」→ 用户选情绪日记 → 写入 `-c 情绪日记`
  - 示例4:用户说「张三生日10月3号」→ AI问「这是社交类的备忘吗?」→ 写 `-c 备忘 -s 社交`
  - 示例5:用户已明确指定分类 → 直接写入
  - **例外**:使用子唤醒词(记心愿/记打卡/记情绪)时,顶层分类已确定,跳过确认直接写入
  - **子分类默认行为**:用户说"记备忘"但没说子分类时 → sub_category 可为 NULL,AI 不必追问

<details>
<summary>🔍 记备忘(add)</summary>

- - CLI: memo_cli.py add "内容" [-c 备忘|心愿|打卡|情绪日记] [-s 子分类] [--due YYYY-MM-DD]
- - SQL: INSERT INTO notes (content, category, sub_category, ...) VALUES (...)
- - 飞书 hook: category == "心愿" 自动建飞书 task(失败降级)
- - 失败: 空内容 / 无效分类 / DB 异常 → status: error + 自动 rollback

</details>

### sub_category 原则

sub_category 是**自由文本字段**,AI 智能从用户原话推断:

- **1 个,2 字**(简短但比 1 字精确)
- **AI 智能推断**:从用户原话提取内容维度
- **推断不出 → NULL**:AI 不乱猜、不强制追问、不预设列表
- **适用于所有 category**:不限于 `备忘`,任何顶层分类下的笔记都可以有 sub_category
- **不预设任何白名单**:任何有意义的 2 字都可以(如"工作"/"学习"/"跑步"/"社交"等)

**例子**:
- "今天跑了 5 公里" → 写入 `-c 打卡 -s 跑步`(顶层分类=打卡,AI 推断 sub_category=跑步)
- "今天学 Python" → 写入 `-c 备忘 -s 学习`
- "张三生日 10/3" → 写入 `-c 备忘 -s 社交`
- "今天去医院" → 写入 `-c 备忘`,`sub_category=NULL`(AI 推断不出维度)
- "看到一只猫" → 写入 `-c 备忘`,`sub_category=NULL`(AI 推断不出维度)

### 搜索笔记
- 唤醒词:搜备忘、查备忘(别名)
- 子唤醒词:查心愿、查打卡、查情绪日记(自动带 `-c 顶层分类` 过滤)

<details>
<summary>🔍 搜备忘/查备忘(search)</summary>

- CLI: `memo_cli.py search "关键词" [-c 分类] [-s 子分类] [--html]`
- 底层: 三字段子串检索(2026-08-07 #180:content + category + sub_category 任一命中,LIKE + ESCAPE 通配符转义)。背景:FTS5 unicode61 分词器不切分中文,MATCH 对中文关键词 100% 失效,已停用为查询路径(表结构保留)。无关键字时按分类列
- SQL: `SELECT n.* FROM notes n WHERE (n.content LIKE ? ESCAPE '\' OR n.category LIKE ? ESCAPE '\' OR n.sub_category LIKE ? ESCAPE '\') ...`
- 语义: 搜「打卡」= 内容含「打卡」或分类是「打卡」;搜「跑步」= 子分类命中。与 HTML 页内过滤框(仅 content,决策 4)层级不同:CLI 是检索,HTML 是结果内筛选
- HTML: 加 `--html` 触发 `memo_query.html` 渲染(`<media>` 交付)
</details>
- 子唤醒词:查心愿、查打卡、查情绪日记(自动带 `-c 顶层分类` 过滤)
- 命令:`script/memo_cli.py search "关键词" [-c 顶层分类] [-s 子分类] [--html]`
- **过滤维度**:可同时按顶层分类和子分类过滤(如 `search -c 备忘 -s 学习`)
- **默认行为**:CLI 默认返回结构化 JSON。需要可视化时传 `--html` flag 生成 HTML 查询结果页(模板 `templates/memo_query.html`,通过 `script/memo_render.py` 注入到 `output/备忘录查询_*.html`)。**当前没有 `--no-html` flag**(2026-07-24 文档对齐修订)。
- **AI 推荐流程**:9 个查询类唤醒词(搜备忘 / 查备忘 / 看备忘 / 按时间搜备忘 / 看提醒 / 查已提醒备忘,以及子唤醒词 查心愿 / 查打卡 / 查情绪日记)在收到 JSON 后,**主动**调一次 `memo_cli.py <cmd> --html` 生成 HTML 给用户,而不是只展示 JSON 文本。理由:清单类数据"扫读 + chip 筛选 + 复制 ID/回执"在 HTML 里体验远超文字流。**例外**:用户明确说"只要 JSON" → 不传 `--html`。
- **HTML 模板模式**:CLI 仍先取 JSON 数据,再通过 `script/memo_render.py` 注入 `templates/memo_query.html`,生成 `output/备忘录查询_*.html`;模板只展示数据,不直连数据库、不污染原模板
- **HTML 数据契约**:`{"status":"ok","data":{"title":"...","command":"search","generated_at":"...","items":[...]}","message":"..."}`
- **页面能力**:首屏摘要卡、当前结果内搜索、分类/子分类 chip 筛选、排期/提醒/附件徽章、空态、复制 ID、复制查询回执

### 更新笔记
- 唤醒词:改备忘
- 子唤醒词:改心愿、改打卡、改情绪日记(先按顶层分类搜索,再更新)
- 先搜索找到笔记 ID,再更新
- 命令:`script/memo_cli.py update <id> [--content "新内容"] [-c 顶层分类] [-s 子分类]`
- **子分类规则**:sub_category 是自由文本字段,适用于所有 category(详见上方"sub_category 原则")

<details>
<summary>🔍 改备忘(update)</summary>

- - CLI: memo_cli.py update <id> [--content 新内容] [-c 分类] [-s 子分类]
- - SQL: UPDATE notes SET ..., updated_at = datetime('now','localtime') WHERE id = ?
- - 飞书 hook: category == 心愿 + 内容变 → 同步飞书 task 标题

</details>

### 删除笔记
- 唤醒词:删备忘
- 子唤醒词:删心愿、删打卡、删情绪日记(先按顶层分类搜索,再删除)
- 先搜索找到笔记 ID,再删除
- 命令:`script/memo_cli.py delete <id> [--with-reminders]`

<details>
<summary>🔍 删备忘(delete)</summary>

- - CLI: memo_cli.py delete <id> [--with-reminders]
- - SQL: DELETE FROM reminders WHERE note_id = ? → DELETE FROM notes WHERE id = ?(避开 FK)
- - 原子性: 事务包裹

</details>

### 查看笔记详情
- 唤醒词:看备忘
- 命令:`script/memo_cli.py get <id> [--html]`
- **默认行为**:CLI 默认返回单条 JSON。需要 HTML 详情页时传 `--html`(复用 `templates/memo_query.html`,items 数组只有 1 条)。
- **AI 推荐流程**:与"搜索笔记"段对齐——收到 JSON 后主动调一次 `get <id> --html` 生成详情页给用户。

<details>
<summary>🔍 看备忘(get)</summary>

- - CLI: memo_cli.py get <id> [--html]
- - SQL: SELECT * FROM notes WHERE id = ?
- - HTML: items 数组 1 条,复用 memo_query.html

</details>

### 按时间搜索
- 唤醒词:按时间搜备忘
- 命令:`script/memo_cli.py search-date <start> <end> [-c 分类] [--html]`
- **默认行为**:CLI 默认返回 JSON。需要 HTML 时传 `--html`(复用 `templates/memo_query.html`)。
- **AI 推荐流程**:与"搜索笔记"段对齐——收到 JSON 后主动调一次 `search-date ... --html` 生成按时间查询页给用户。

<details>
<summary>🔍 按时间搜备忘(search-date)</summary>

- - CLI: memo_cli.py search-date <start> <end> [-c 分类] [--html]
- - SQL: SELECT * FROM notes WHERE created_at BETWEEN ? AND ?
- - 日期格式: YYYY-MM-DD(start ≤ end 校验)

</details>

### 编辑笔记顶层分类
- 唤醒词:备忘改分类
- 先搜索找到笔记 ID,再更新顶层分类
- 命令:`script/memo_cli.py update-category <id> <顶层分类>`
- **副作用**:改顶层分类时**不会**清空 `sub_category`(sub_category 是内容维度的二阶属性,与顶层分类独立)

<details>
<summary>🔍 备忘改分类(单条 update-category / 批量 batch-update-category)</summary>

- - 单条 CLI: memo_cli.py update-category <id> <新分类>
- - 批量: batch-update-category --from-category X --html(过程型,见路由规则)
- - SQL: UPDATE notes SET category = ?, updated_at = ... WHERE id = ?
- - 副作用: 不动 sub_category

</details>

### 编辑笔记子分类
- 唤醒词:备忘改子分类
- 先搜索找到笔记 ID,再更新子分类
- 命令:`script/memo_cli.py update-sub-category <id> <子分类 | null>`
- **规则**:适用于所有 category(sub_category 是自由文本字段);传 `null` 表示清除子分类

<details>
<summary>🔍 备忘改子分类(update-sub-category)</summary>

- - CLI: memo_cli.py update-sub-category <id> <子分类 | null>
- - SQL: UPDATE notes SET sub_category = ?, updated_at = ... WHERE id = ?
- - null 处理: "null"/"" 传 → 清除
- - 适用于所有 category

</details>

### 唤醒词路由(避免与「批量改分类向导」歧义 · 2026-07-24 加)
**唤醒词 `备忘改分类` 同时对应两个命令,AI 必须按以下规则二选一**:
- **单条改分类**(默认):
  - 触发语:「改 #15 的分类」「把 #15 备忘改成心愿」「这条改成打卡」
  - 命令:`memo_cli.py update-category <id> <category>`
  - 路径:搜索找 id → 单条 update-category
- **批量改分类**(多 id 或带"都/全部")· 过程型 HTML:
  - 触发语:「把所有 X 分类都改到 Y」「X 这几条都改 Y」「把 X 分类下所有笔记改到 Y」
  - 命令:`memo_cli.py batch-update-category --from-category X [--to-category Y] --html`
  - 路径:用户在 HTML 里勾选 + 选目标分类 → 采纳复制 → AI 调多条 `update-category`
- **判定启发(按优先级)**:
  1. 原话**只含一个具体 id**(如 #15 / 笔记 A) → 单条
  2. 原话**含"都/全部/这 N 条"或多个 id** → 批量
  3. 原话**没有 id 也没有"都/全部"** → 反问用户:「是想单条还是批量?」
- **不冲突场景**(永远单条,不走批量):改 sub_category、调单个提醒、心愿排期/完成、所有写入类(add/update/delete)
- **反例**(误判示例):
  - ❌ "把 #15 #20 #25 都改心愿" → 错走单条;应走批量
  - ❌ "把备忘分类所有都改心愿" → 错走反问;应走批量

### 心愿排期
- 唤醒词:心愿排期
- 给心愿设置期望完成日期(due),**自动同步到飞书 task due**
- 第一性:备忘录 `notes.due` 是 source of truth,飞书 `task.due` 是镜像
- **单条**:`script/memo_cli.py set-due <id> --due <YYYY-MM-DD>`
- **批量**:`script/memo_cli.py set-due <id1> <id2> <id3> ... --due <YYYY-MM-DD>`
- **清除**:`script/memo_cli.py set-due <id> --due null`
- 飞书侧:飞书 task 自动出现 `is_all_day=true` 的 due,飞书日历"待办"区可见
- **使用场景**:
  - 单独使用:用户说"心愿 #36 #48 安排在 6/30" → AI 调批量 set-due
  - cross-skill 联动:作息"商量计划"流程最后一步(待 B 阶段实现),统一调"心愿排期"批量设 due = 那天
- **失败降级**:
  - 飞书同步失败 → 本地 due 仍生效,errors 累积
  - 心愿无 feishu_task_guid → 提示用户跑 `备忘录同步` 补建后重试
- **心愿排期向导**(2026-07-24 新增 · 过程型 HTML):
  - 命令:`script/memo_cli.py wish-batch-plan [--ids 1 2 3] [--all] [--suggest-due YYYY-MM-DD] [--html]`
  - **触发场景**:用户原话含多个心愿 + 时间锚点(「这 3 个都排到 7/3」「心愿 #36 #48 安排到 6/30」),AI 识别后**主动**调 `wish-batch-plan --suggest-due X --html` 生成向导页给用户在 HTML 里调,而不是逐条 ID 往返
  - **默认(无 --all)**:搜 `category='心愿' AND due IS NULL` 最近 50 条
  - **--all**:含已排期心愿(用于微调)
  - **--ids**:精确指定(与 --all 互斥,硬规则)
  - **模板**:`templates/wish_plan.html`(独立,过程型 HTML,不复用 memo_query.html)
  - **渲染器**:`script/memo_render.py:render_wish_plan`(复用 `_inject` 公共逻辑)
  - **类型**:过程型 HTML · 按 04_架构师原则 §10 设计 · 含"采纳并复制"按钮 + 4 部分 prompt
  - **4 部分 prompt**(采纳按钮复制):
    ① 场景: 我用心愿排期向导给 N 个心愿设了排期(原建议 X)
    ② 数据(采纳后): 表格列出心愿 id + 排期日期(含"原排期"列,帮助审计覆盖)
    ③ 期望: 按 set-due 命令列表(日期相同 → 一次批量;日期不同 → 每条单独;feishu task 自动同步)
    ④ 来源: wish-batch-plan --suggest-due X / 2026-07-24 14:00
  - **数据契约**:`{"status":"ok","data":{"title":"...","command":"wish-batch-plan","generated_at":"...","suggest_due":"YYYY-MM-DD"|null,"all":bool,"items":[{id,content,category,sub_category,current_due,feishu_task_guid,selected,suggested_due}, ...]},"message":"找到 N 个心愿"}`
  - **AI 推荐流程**:跑到 `add 心愿` 批量场景 → **不直接**批量 `set-due` → 先调 `wish-batch-plan --suggest-due <识别到的锚点> --html` → 用户在 HTML 里微调 → 采纳复制 → 粘贴给 AI → AI 调精确 `set-due` 命令

<details>
<summary>🔍 心愿排期(wish-batch-plan)</summary>

- - CLI: memo_cli.py wish-batch-plan [--ids 1 2 3] [--all] [--suggest-due YYYY-MM-DD] [--html]
- - 批量执行: set-due <id1> <id2> ... --due X(批量 SQL UPDATE)
- - HTML: 过程型 wish_plan.html(默认未勾 + 全局建议日期)
- - 飞书: 同步飞书 task due(UTC ms → 北京日期)
- - 副作用: 心愿无 feishu_task_guid → 需先备忘录同步 补建

</details>

### 完成心愿向导(2026-07-24 新增 · Step 5A · 过程型 HTML · v1.0.1 第一性修复 · v1.0.4 默认未勾)
- 唤醒词:完成心愿(**别名:完成打卡 · 2026-07-24 加**)· 批量场景:「这些心愿我都完成了」「心愿 #36 #48 完成」「完成打卡 #36 #48」
- 命令:`script/memo_cli.py wish-complete [--ids 1 2 3] [--only-overdue] [--all(已弃用)] [--content "打卡内容"] [--html]`
- **类型**:过程型 HTML(同 wish-batch-plan 模式)
- **第一性**:complete-wish 是原子操作(删心愿 + 建打卡),用户先在 HTML 选要完成的 + 填打卡内容,采纳后给 AI 批量调
- **v1.0.1 修复**(默认语义回归第一性):
  - 旧默认 = `NOT IN reminders AND due IS NULL OR due < today` → 用户"我加的 20 条心愿,wish-complete 给 0 条"
  - 新默认 = 所有 `category='心愿'` 的 · 让用户在 HTML 里勾(过程型 HTML 的本职)
  - 真理:**CLI 不应该替用户预设决策,该预设归 UI**
- **v1.0.1 命令选项**:
  - 默认(不加 flag):全部心愿 · 让用户在 HTML 里勾
  - **`--only-overdue`**:仅未排期+已过期排期(v1.0.0 默认行为迁至此显式 flag)
  - `--all`:**deprecated** · 等同不加 flag · 仅保留向后兼容
  - `--ids N M ...`:显式指定(与 `--only-overdue`/`--all` 互斥)
  - `--content X`:默认打卡内容(HTML 可逐条覆盖;留空用原心愿 content)
  - `--html`:生成过程型 HTML
- **v1.0.4 HTML 默认未勾选**(过程型 HTML 正向操作):
  - `items[].selected = False` · 用户主动勾选要完成的(不是反向删勾)
  - 模板渲染:`<article class="wish">` 始终 normal(不依赖 selected 加 .off)
  - 用户切换 checkbox 时才动态加 .off class(opacity:.5)
  - 第一性:过程型 HTML 的价值是让用户主动表达意图(正向 > 反向)
- 模板:`templates/wish_complete.html`(独立,不与 wish_plan 复用)
- 渲染器:`script/memo_render.py:render_wish_complete`
- **4 部分 prompt**(采纳按钮复制):
  ① 场景: 我用心愿完成向导标记 N 个心愿为已完成(原子转换心愿→打卡)
  ② 数据(采纳后): 表格列出 #id + content + 打卡内容(覆盖默认/用原内容)
  ③ 期望: 按 complete-wish 命令列表(每步:删心愿+建打卡 原子;有飞书 task 的同步标完成)
  ④ 来源: wish-complete / 2026-07-24 14:00
- **数据契约**:`{"status":"ok","data":{"title":"...","command":"wish-complete","generated_at":"...","default_content":"..."|null,"items":[{id,content,category,sub_category,due,feishu_task_guid,selected}, ...]},"message":"..."}`
- **AI 推荐流程**:用户说"这些心愿都完成了" → AI 调 `wish-complete --ids 1 2 3 --html`(或先 search 取 ids) → 用户在 HTML 里勾选 + 填打卡内容 → 采纳复制 → 粘贴给 AI → AI 按 complete-wish 命令逐条执行(原子转换)
- **与 wish-batch-plan 的协同**:用户可先排期后完成;两个向导是心愿生命周期的两端工具

### 批量改分类向导(2026-07-24 新增 · Step 5B · 过程型 HTML)
- 唤醒词:备忘改分类(批量场景,如「把 X 分类下这 10 条都改到 Y 分类」)
- 命令:`script/memo_cli.py batch-update-category --from-category <原> [--to-category <新>] [--html]`
- **类型**:过程型 HTML(同 wish-batch-plan/wish-complete 模式)
- **第一性**:update-category 是单 id 命令(`update-category <id> <category>`),批量场景用户在 HTML 选要改的 + 选目标分类
- **--from-category**:原分类(白名单:备忘/心愿/打卡/情绪日记)
- **--to-category**:建议目标分类(HTML 可改;硬规则:不与 --from-category 相同)
- **副作用**:只改 `category`,**不动 `sub_category`**(sub_category 是内容维度的二阶属性)
- 模板:`templates/change_category.html`(独立)
- 渲染器:`script/memo_render.py:render_change_category`
- **4 部分 prompt**(采纳按钮复制):

<details>
<summary>🔍 查看底层原理</summary>

- **CLI**: `memo_cli.py batch-update-category --from-category <原> [--to-category <新>] [--html]`
- **触发路由**: 原话含"都/全部/这 N 条"或多个 id → 批量(否则走单条 `update-category`)
- **SQL**: 单条 update-category `UPDATE notes SET category = ?, updated_at = ... WHERE id = ?`
- **HTML**: 过程型 `change_category.html`(用户勾选 + 选目标分类)
- **硬规则**: `--from-category ≠ --to-category`
- **副作用**: 不动 sub_category
</details>

  ① 场景: 我用批量改分类向导把 N 条<原分类>笔记改到<新分类>(sub_category 不动)
  ② 数据(采纳后): 表格列出 #id + content + from → to
  ③ 期望: 按 update-category 命令列表(每条 id 单独调,sub_category 字段不动)
  ④ 来源: batch-update-category --from-category X --to-category Y / 2026-07-24
- **AI 推荐流程**:用户说"把 X 分类这些都改了" → AI 调 `batch-update-category --from-category X --html` → 用户在 HTML 选要改的 + 选目标分类 → 采纳复制 → 粘贴给 AI → AI 按 update-category 命令逐条执行

#### 排期日期的用户-facing 表达(中文)
- 对用户说的时候,**不要用 "due" 这个英文术语**,用以下中文之一:
  - "排期日期"
  - "放到 X 日完成"
  - "哪天想做"
- 表述转换示例:
  - ❌ "给这条心愿 due 到 7/3"
  - ✅ "给这条心愿设个排期日期 = 7/3" / "放到 7/3 完成"
  - ❌ "due 已同步到飞书"
  - ✅ "飞书 task 也带上日期了"
- 技术字段名不动:`notes.due` 字段、CLI 参数 `--due`、飞书 `task.due` 仍是英文(这层是数据/接口,不是 UI)

#### 心愿 add 时的时间锚点识别(B 方案 / 2026-07-02 定稿)
- **触发条件**:`add 心愿` 时,AI 检测原话里的明确时间锚点
  - **识别**:`明天` / `后天` / `今天` / 具体日期("7/3"、"7 月 3 日")/ 周 X(周一、周二...)
  - **不触发**:原话没有时间词(如"想学 Python")-- 强加排期 = 污染
- **批量优先**:同一段话多个心愿 + 同一锚点 → 收成 **1 次询问**,不逐条烦人
- **多日期智能识别**:原话含多个不同日期锚点 → AI 内部智能拆分不同组,**一次询问里列出所有组**,不让用户多轮交互
- **询问模板(标准版)**:
  > 刚才那 N 条全部进了心愿库。看时间提到了 [锚点],
  > 默认安排到 [日期](本地存"排期日期",飞书 task 也会带上)。
  > 要不要都给 [日期]?还是有几条要换日子?
- **选项维度**:用户可回应
  - "都 X 日" → AI 批量 set-due
  - "X/Y/Z 几条不要"(保留无排期日期)→ AI 仅对剩下的 set-due
  - "X 条改 Y 日" → AI 分组批量 set-due
- **精度**:仅日期级(YYYY-MM-DD),不精确到时分(飞书日历只挂日期)
- **飞书缺失优雅降级**:未装飞书 CLI 或未登录时本地排期日期照常生效,飞书同步步骤跳过,流程不阻断;本地 `notes.due` 是 source of truth,飞书是 best-effort 镜像
- **回执**:每次批量 set-due 后列回执(如"10088-10095 → 7/3"),透明优先
- **changelog**:
  - 2026-07-02 B 方案首次定稿。下次有疑问或新增场景先翻这一节

### 设置提醒
- 唤醒词:设提醒
- 时间识别:明天、后天、今天 + 时间
- 重复规则:每天,每天→每天,每周→每周,每月→每月,每年→每年
- 流程:直接创建提醒,无需先有笔记(提醒内容存 reminders.content)
- 命令:`script/memo_cli.py remind <note_id> --at "YYYY-MM-DD HH:MM" --content "提醒内容" --repeat-type 每天 --rule "09:00"`

<details>
<summary>🔍 设提醒(remind)</summary>

- - CLI: memo_cli.py remind <note_id> [--at YYYY-MM-DD HH:MM] [--content 提醒内容] [--repeat-type 每天|每周|每月|每年] [--rule HH:MM]
- - SQL: INSERT INTO reminders (note_id, remind_at, repeat_type, repeat_rule, ...) VALUES (...)
- - FK: note_id → notes(id) ON DELETE NO ACTION
- - 重复规则格式: HH:MM / W HH:MM / D HH:MM / MM-DD HH:MM

</details>

### 记提醒(添笔记 + 设提醒)
- 唤醒词:记提醒
- 时间识别:明天、后天、今天 + 时间
- 重复规则:每天,每天→每天,每周→每周,每月→每月,每年→每年
- 流程:先添加笔记,再设置提醒(笔记内容 + 提醒内容分别存储)
- 命令示例:`script/memo_cli.py add "我要健身" -c 心愿 && script/memo_cli.py remind <id> --at "09:00" --content "跑步10分钟" --repeat-type 每天`

<details>
<summary>🔍 记提醒(add + remind)</summary>

- - 两步: add 笔记 → remind 加提醒
- - 等价: 笔记与提醒分别存储,关联通过 note_id

</details>

### 查看提醒
- 唤醒词:看提醒
- 命令:`script/memo_cli.py reminders [--status active|dismissed] [--html]`
- **默认行为**:CLI 默认返回 JSON。需要 HTML 时传 `--html`(复用 `templates/memo_query.html`,按重复类型提供筛选 chip)。
- **AI 推荐流程**:与"搜索笔记"段对齐——收到 JSON 后主动调一次 `reminders --html` 生成提醒列表页给用户。

<details>
<summary>🔍 看提醒(reminders)</summary>

- - CLI: memo_cli.py reminders [--status active|dismissed] [--html]
- - SQL: SELECT * FROM reminders WHERE status = ?
- - HTML: 复用 memo_query.html

</details>

### 废弃提醒
- 命令:`script/memo_cli.py dismiss <id>`

### 查询已完成提醒
- 唤醒词:查已提醒备忘
- 命令:`script/memo_cli.py completed [--html]`
- **默认行为**:CLI 默认返回 JSON。需要 HTML 时传 `--html`(复用 `templates/memo_query.html`,支持复制提醒 ID / 打卡 ID 回执)。
- **AI 推荐流程**:与"搜索笔记"段对齐——收到 JSON 后主动调一次 `completed --html` 生成已完成提醒页给用户。
- **匹配逻辑**:
  - **一次性提醒**:有 `notified_at`(已触发过)+ 关联打卡笔记 → 算已完成
  - **每天重复**:关联打卡笔记 → 算今天已完成
  - **每周重复**:打卡日期在当周 + 对应星期符合规则 → 算本周已完成
  - **每月重复**:打卡日期在当月 + 对应日期符合规则 → 算本月已完成
  - **每年重复**:打卡日期在年内 + 对应月日符合规则 → 算今年已完成
- **返回字段**:提醒内容、打卡笔记、打卡时间、周期描述、类型

<details>
<summary>🔍 查已提醒备忘(completed)</summary>

- - CLI: memo_cli.py completed [--html]
- - 匹配: 一次性已通知+关联打卡 / 重复型有关联打卡
- - HTML: 复用 memo_query.html

</details>

### 备忘录同步(自动 + 反向)
本技能可在**飞书 CLI 已安装**时与飞书任务双向联动:

- **唤醒词**:备忘录同步
- **自动联动**(无需唤醒词):
  - `add 心愿`:自动建飞书 task,写回 `notes.feishu_task_guid`
  - `update 心愿`:自动同步更新飞书 task 标题
  - `delete 心愿`:自动标飞书 task 完成(飞书无 delete 概念)
  - `complete-wish 心愿`:自动标飞书 task 完成
- **双向对账**(唤醒词触发):`备忘录同步`
  - **第一步:本地补建**(本地 → 飞书)
    - 查 `notes WHERE category='心愿' AND feishu_task_guid IS NULL`
    - 对每个 note 调 `add_wish_sync` 建飞书 task,写回 `feishu_task_guid`
    - 处理历史心愿 / 旧 demo 残留 / 之前同步失败的心愿
  - **第二步:反向同步 done**(飞书 → 本地)
    - 筛飞书 `status=done` 的 task,反查 `notes.feishu_task_guid`
    - 对本地还在的心愿触发 `complete-wish`
  - **第三步:反向同步 due**(飞书 → 本地 · 仅 `status=todo`)
    - 用户在飞书 App 改/清 due 后,本地 `notes.due` 不会自动跟上 → 跑这里反向同步
    - list 接口 `task +get-related-tasks` **不带 due 字段**,所以步骤 3 对每个 todo task 单独调 `task tasks get` 取 `due.timestamp`
    - 时间戳换算:UTC ms → 北京日期(UTC +8h)→ `YYYY-MM-DD` 字符串
    - **飞书优先**四象限处理(用户决策:飞书说了算):
      - 飞书有 due / 本地无 → 写本地(`due_added`)
      - 飞书有 due / 本地有但不同 → 覆盖本地(`due_overridden`)
      - 飞书无 due / 本地有 → 清本地(`due_removed`,飞书清 → 本地也清)
      - 一致 → 跳过(不计入 `due_*` 字段)
    - 性能:N 个 todo wish 需 N 次 `task tasks get` API call(串行,单次 <1s)。N≤50 时通常 <10s 完成
  - **报告字段**:
    - `backfilled`(步骤 1 本地补建数)
    - `scanned_done` / `synced`(步骤 2 done 反向同步数)
    - `scanned_pending` / `due_added` / `due_overridden` / `due_removed`(步骤 3 due 反向同步)
    - `skipped_no_memo_id` / `skipped_already_done` / `skipped_no_local_note`
    - `errors[]`
- **自动检测**:`is_feishu_available()` 检查 lark-cli 是否在 `%APPDATA%\npm\`(Windows)或 `which lark-cli`(WSL/Linux/Mac)
- **失败降级**:飞书 API 失败不阻塞本地操作(仅 stderr 记录)
- 命令:`script/memo_cli.py sync-from-feishu [--html]` 或 `script/feishu_sync.py sync-from-feishu`
- **HTML 同步报告**(2026-07-24 新增):
  - 命令:`script/memo_cli.py sync-from-feishu --html`
  - 模板:`templates/sync_report.html`(独立于 `memo_query.html`)
  - 渲染器:`script/memo_render.py:render_sync_report`(复用 `_inject` 公共逻辑)
  - 输出:`output/同步报告_YYYYMMDD_HHMMSS.html`
  - **页面能力**:首屏徽章总览(完全一致/补建/同步完成/due 变更/错误数)、4 个 KPI 卡(本地补建/扫 done/同步完成/扫 pending)、3 步折叠详情(本地补建/反向同步 done/反向同步 due)、errors 红色高亮、复制同步回执(11 字段结构化文本)
  - **AI 推荐流程**:跑完 `备忘录同步` 后,**主动**追加一次 `sync-from-feishu --html` 生成报告页给用户,而不是只展示 JSON 文字流。理由:11 个统计字段在卡片化 + 三步折叠视图里阅读体验远超文字
  - **数据契约**:`{"status":"ok","data":{"title":"...","command":"sync-from-feishu","generated_at":"...","backfilled":N,...,"errors":[]},"message":"..."}`(result 字段平铺到 data 下)

#### 飞书联动环境变量(用户特定,必须自己配置)

⚠️ **不要硬编码用户特定信息到代码里**。所有用户/本机特定配置通过环境变量传入。

**默认行为**:飞书 task **不指定 tasklist**(建在飞书"我的任务"主页)。零配置即可使用飞书联动。

**tasklist 怎么传**:每次 `add` 心愿时**显式传** `--tasklist-guid <guid>`。**没有环境变量预配置**--用户完全控制。

| 环境变量 | 必填 | 说明 | 示例 |
|---|---|---|---|
| ~~`MEMO_FEISHU_USER_OPEN_ID`~~ | **已删除** | 不再需要 -- assignee 自动从 `lark-cli auth status` 读取 | -- |

**未设置时行为**:
- 不存在 -- **lark-cli auth login 之后自动可用**(`lark-cli auth status` 返回 identities.user.openId 作为 assignee)
- 飞书同步失败原因只会是:lark-cli 未安装 / 未登录 / 提取失败

#### tasklist 显式传入流程(少用场景)

用户偶尔想把心愿放进特定 tasklist:

1. **AI 跑 `feishu_sync.py list-tasklists`** → 列飞书侧所有 tasklist(含 name 和 guid)
2. **AI 给用户看**:列出如 `📋 备忘录心愿 (guid=xxx)`, `🛒 购物 (guid=yyy)`
3. **用户说"进 备忘录心愿"**
4. **AI 传 `--tasklist-guid xxx`** → 飞书 task 进指定 tasklist

**CLI 用法**:
```bash
# 默认(不指定 tasklist)→ 飞书主页
memo_cli.py add "今天买咖啡" -c 心愿

# 显式指定 tasklist → 飞书指定清单
memo_cli.py add "今天买咖啡" -c 心愿 --tasklist-guid <xxx-xxx-xxx>
```

#### AI 首次引导(用户首次使用飞书联动时)

当用户第一次说"我想让心愿同步到飞书"或类似意图时:

1. **检测 lark-cli**(运行 `python script/feishu_sync.py check` 看可用性)
2. **如果 lark-cli 不可用**:
   - 提示用户先 `lark-cli auth login`(标准飞书开发者授权)
3. **否则零配置直接生效**:
   - 自动从 `lark-cli auth status` 读 user open_id
   - 创建的飞书 task 自动指派给当前 lark-cli 登录的用户
4. **如果用户想要分到 tasklist**:
   - 引导用户在飞书 App 手动建 tasklist
   - AI 跑 `list-tasklists` 列出飞书侧 tasklist
   - 用户说"这个心愿进 🧹" → AI 传 `--tasklist-guid <guid>`
   - 不存环境变量,每次 add 显式传

<details>
<summary>🔍 备忘录同步(sync-from-feishu)</summary>

- - CLI: memo_cli.py sync-from-feishu [--html]
- - 3 步对账:
-   1. 本地补建: 心愿无 feishu_task_guid → add_wish_sync 建飞书 task
-   2. 反向同步 done: 飞书 status=done → complete-wish
-   3. 反向同步 due: 飞书 todo task.due → 本地 notes.due(飞书优先 4 象限)
- - HTML: 结果型 sync_report.html(11 统计字段 · 3 步折叠 · errors 高亮)
- - 失败降级: 飞书 API 失败不阻塞本地

</details>

### 完成心愿:流式工作流
心愿完成是一个**原子操作**:删除原心愿 + 新建打卡 note,两步必须同时成功或同时回滚。
- 唤醒词:完成心愿
- 命令:`script/memo_cli.py complete-wish <心愿id> [--content "打卡内容"]`
- 行为:
  1. 校验 `id` 存在于 `notes`,且 `category='心愿'`(不是心愿分类报错)
  2. 决定打卡 content:用户提供 → 用用户的;没提供 → 拷贝原心愿 `notes.content`
  3. 事务原子执行(兼容 NO ACTION / CASCADE 两种 FK 行为):
     - `DELETE FROM reminders WHERE note_id = ?`(先删提醒,避开 FK 约束)
     - `DELETE FROM notes WHERE id = ?`
     - `INSERT INTO notes (content, category='打卡', created_at, updated_at)`
- 行为:
  1. 校验 `id` 存在于 `notes`,且 `category='心愿'`(不是心愿分类报错)
  2. 决定打卡 content:用户提供 → 用用户的;没提供 → 拷贝原心愿 `notes.content`
  3. 事务原子执行(兼容 NO ACTION / CASCADE 两种 FK 行为):
     - `DELETE FROM reminders WHERE note_id = ?`(先删提醒,避开 FK 约束)
     - `DELETE FROM notes WHERE id = ?`
     - `INSERT INTO notes (content, category='打卡', created_at, updated_at)`
- 设计取舍:
  - **不写 `reminder_id`**:CASCADE 删 reminders 后该字段会悬空,留 NULL 更干净
  - **硬删除**:流式工作流意味着心愿生命终结于"完成"那一刻
- 与「完成提醒:提醒与打卡的完整流程」的关系:
  - 旧流程:add → remind → 关联 → 打卡追加(手动 4 步)
  - 新流程:complete-wish(一步原子,自动完成删心愿 + 建打卡)
  - 推荐用新流程

<details>
<summary>🔍 完成心愿(complete-wish / wish-complete)</summary>

- - 直接 CLI: memo_cli.py complete-wish <id> [--content 打卡内容](原子操作)
- - 批量过程型 HTML: wish-complete --ids 1 2 3 [--only-overdue] --html(推荐批量场景)
- - 原子操作: DELETE reminders → DELETE notes → INSERT notes(category=打卡) 事务包裹
- - HTML: 过程型 wish_complete.html(默认未勾,用户主动勾)
- - 飞书: 心愿有 feishu_task_guid → 标飞书 task 完成

</details>

### 完成提醒:提醒与打卡的完整流程(旧流程,推荐用「完成心愿」替换)
提醒完成后,可以追加打卡记录,形成完整的"计划→提醒→完成"链路:

| 步骤 | 操作 | 字段关联 |
|------|------|----------|
| 1. 添加笔记 | `add "晒衣服"` → 获得 `notes.id=12` |
| 2. 设置提醒 | `remind 12 --at "19:30"` → `reminders.note_id=12, reminders.id=5` |
| 3. 笔记关联提醒 | `notes.reminder_id=5`(自动或手动) |
| 4. 提醒触发后打卡 | `add "晒衣服" -c 打卡` → 获得 `notes.id=20`,并设置 `notes.reminder_id=5` |

**通过 `reminder_id` 可以追溯**:
- 这条打卡记录源自哪个提醒
- 提醒什么时候触发过
- 原笔记内容是什么

## 定时提醒机制

### Cron 配置
- **触发频率**:每 {CRON_INTERVAL_MINUTES} 分钟检查一次(可配置 `MEMO_CRON_INTERVAL` 环境变量)
- **无提醒时**:静默处理,输出「NO_REPLY」,不发送任何消息
- **有待提醒时**:通过 message 工具发送到 QQ,target 由 cron job 的 delivery 配置决定(禁止在 SKILL 中硬编码)

### 提醒逻辑
- **提前a分钟**:提前a分钟的时间点精确触发(可配置 `MEMO_ADVANCE_MINUTES`,默认10;如 8:50 触发 9:00 的提醒)
- **准点触发**:提醒时间 T ~ T+窗口分钟内任意一次检查都会触发(窗口 = cron间隔 × `MEMO_GRACE_MULTIPLIER`,默认 T~T+4)
- 一次性提醒:触发后记录 notified_at,避免重复通知
- 重复提醒(每天/每周/每月/每年):正常触发,下次周期重置 notified_at

### 提醒输出格式(SKILL 内部执行时使用)
```
🔔 {内容}
⏰ {时间} · {重复类型}
```

**示例**:
```
🔔 检查烤箱状态
⏰ 19:08 · 一次性
```

**设计原则**:
- 内容在第一行,换行不影响核心信息
- 时间+重复在第二行,跟内容保持关联
- 用 `·` 分隔,视觉清晰
- `{重复类型}` 可选值:一次性 / 每天 / 每周 / 每月 / 每年

**SKILL 执行提醒时的行为**:
1. 执行 reminder_scheduler.py 检查到期提醒
2. 有提醒 → 按上述格式输出 → 通过 message 工具发送
3. 无提醒 → 输出 NO_REPLY

### Cron Payload 示例
```
请读取 ${SKILL_DIR}/SKILL.md 并执行提醒检查流程
```

**说明**:`${SKILL_DIR}` 是占位符,部署时替换为技能实际目录的绝对路径(你的宿主环境实际安装位置)。Payload 只负责触发 skill 执行,不描述"有提醒/无提醒"的判断逻辑,该逻辑由 SKILL 内部决定。

## 参考文档

- 数据库结构:`references/schema.md`
- 对话示例:`references/examples.md`
- Cron 配置:`references/cron.md`
- **场景资产**(v1.1.4 · 总纲 §07 契约):`references/scenarios.yaml` — HELP HTML 的唯一事实源

---

## 备忘录 HELP(v1.1.4 · 总纲 §07 契约)

### 唤醒词

- **`备忘录 HELP`**(字面)

### 唤醒词灵活匹配(FAT 发现 · G1 修复)

**HIT 规则**:不是仅 `备忘录 HELP` 严格 4 字命中,所有 HELP 类意图都应触发 `memo_cli.py help`:

| 用户原话示例 | 类型 | 是否触发 |
|---|---|---|
| `备忘录 HELP` | 字面 | ✅ |
| `备忘录 help` | 大小写变体 | ✅ |
| `备忘 HELP`(少"录"字) | 缩字变体 | ✅ |
| `备忘录的help在哪` | 口语化 + 略错 | ✅ |
| `帮我看下备忘录的使用说明` | 口语 + 同义("使用说明"="HELP") | ✅ |
| `/备忘录-help` | slash command 风格 | ✅ |
| `/备忘录 help` | slash + 空格 | ✅ |
| `备忘录 manual` / `备忘录 guide` | 英文同义词 | ✅ |

**判定原则**(优先级从高到低):
1. **意图优先**:用户语义是"想要帮助/说明/手册/功能介绍" → 触发
2. **字面匹配**:含 "HELP" / "help" / "使用说明" / "说明书" / "manual" / "guide" 字样
3. **不要的字面**:不含上述任何字样且无 HELP 意图 → **不**触发(避免误命中)

**反例**(不触发):
- ❌ "备忘录" 单独出现(无 HELP 字样) → 走默认唤醒词路由
- ❌ "Help me find ..."(help 作动词"帮助"非"手册") → 不触发
- ❌ "我要帮你 ..."(help 是动词) → 不触发

**理由**:FAT 实测 4 个自然语言变体全部正确触发,但 SKILL.md 没明文规则 → 依赖 AI 自我推断。补这条消除推断歧义。

### 行为

`备忘录 HELP` 命中后:

1. 读 `references/scenarios.yaml`(场景资产,HELP HTML 唯一事实源)
2. 渲染 `templates/memo_help.html` → 产出 HELP HTML
3. 写**时间戳副本**:`D:\.db\memo_html\备忘录_HELP_<YYYYMMDD>_<HHMMSS>.html`(§04 原则 12.B)
4. ★ **覆盖 skill 根目录 `备忘录.html`**(用户额外要求 · 取代旧手写用户手册)

### 场景资产契约(§07 §2.2)

每条场景必含 8 字段:
| 字段 | 含义 |
|---|---|
| `wake_word` | 关联业务唤醒词(唯一展示名;别名在 SKILL.md 匹配层 #31 Q1) |
| `scenario_id` | 稳定 ID,跨版本不变 |
| `scenario_title` | 用户可读标题 |
| `type` | 流程类型徽章(08-HTML交互规范 · 与居家管家同词汇,白名单见 validate_scenarios.py) |
| `dimensions` | 合法维度字典 |
| `prompt` | 稳定用户意图(**不暴露** CLI / DB / Python / 模板路径) |
| `status` | `""`(可用)或 `"【待开发】"`(禁用) |
| `result` | 预期结果(用户视角) |
| `category` | 必填,引用顶层 categories key(#31 Q2/Q5) |
| `subfunction` | 可选,子功能分组(空 = 「基础」兜底 #31 Q3) |
| `dependencies` | 可选,环境依赖清单多行文本(#32 · 仅 Init) |

### HELP HTML 必须(§07 §5)

- 展示除 HELP 自身外的**全部 29 个业务唤醒词**(28 唯一 + 首次使用;备忘改分类 单条+批量 共用)
- 每场景独立**复制按钮**(剪贴板 API + `execCommand` 降级)
- 5 状态 fallback(正常 / 空 / 缺失 / 错误 / 离线)
- 移动端 + PC 适配
- **不展示 HELP 唤醒词自身**(避免死循环)

### 守门测试

`tests/test_help.py` 22 用例守护:
- scenarios.yaml schema(8 字段齐全、ID 唯一、prompt 无实现细节)
- 场景数 = SKILL.md 唤醒词数
- render_help 产出合法 HTML(占位符、转义)
- **skill 根目录 `备忘录.html` 被覆盖**
- HELP HTML 不展示自身
- CLI `help` 子命令可执行

### CLI

```bash
python3 script/memo_cli.py help                    # 必生成 HELP HTML + 覆盖 skill 根 备忘录.html
python3 script/memo_cli.py help --output /tmp/x    # + 额外副本 /tmp/x(备忘录.html 仍覆盖)
```

**无 `--html` / `--json` flag**(用户约定 #3:必生成,简化调用)。

**`--output` / `-o`(B 方案,1.1.4 post-审查加入)**:在两份标准副本之外**追加**一份额外副本。
- **永远写两份**:时间戳副本 + skill 根 `备忘录.html`(用户 v1.1.4 额外要求)
- **`--output` 是 +1 份额外投放**(给开发测试 / 单次分享用,不替换任何标准副本)
- 父目录不存在时自动 `mkdir -p`
- 适用场景:
  - 跑测试不想污染 `memo_html/` 时:`--output ./test_help.html`
  - 给同事单次分享:`--output /tmp/备忘录_manual_for_同事.html`
  - 调试场景资产渲染:`--output /tmp/dbg.html`(同时看 skill 根版本对比)

### 历史

- v1.0.9:旧 `备忘录.html`(475 行手写用户手册)已废弃
- v1.1.4:新 `备忘录.html` = `memo_cli.py help` 自动生成的 HELP HTML
