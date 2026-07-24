# 备忘录 (Memorandum)

> **当前版本:1.0.4**(2026-07-24 发布 · 13 个 commit · git tag `v1.0.4`)
> v1.0.4:心愿完成 HTML 默认未勾选(正向操作第一性)
> v1.0.3:HTML 交付规范纠正(`<media>` + 浏览器并行)
> v1.0.2:HTML 交付规范初版(过度禁止已纠正)
> v1.0.1:wish-complete 第一性修复
> 详见 `CHANGELOG.md`

## 强制性规定(最高优先级)

1. **HTML 同步**:该技能的所有优化和变动、脚本的所有变动都必须体现在 `备忘录.html` 上。
2. **优先级**:本规定优先级最高,高于所有其他规范。
3. **用户确认**:对该技能的所有文件、脚本的任何一行修改,都需要明确得到用户的 1 次确认后才能执行。

## HTML 交付规范(2026-07-24 加 · 最高优先级 · v1.0.3 修订)

这是 5 个 HTML 模板(`memo_query.html`/`sync_report.html`/`wish_plan.html`/`wish_complete.html`/`change_category.html`)生成后,**AI 代理必须遵守的交付协议**:

1. **必须用 `<media src="..." type="file" />` 标签交付**(基础动作)。
   - 这是《预置HTML并注入数据指导手册》§4 + §9(标准工作流最后一步)规定的标准交付方式
   - HTML 内嵌 JS + clipboard + textarea,有交互,**内联展示会丢失交互**(所以内联禁止)

2. **强烈推荐:与 `<media>` 并行,同时用 Chrome 等系统默认浏览器打开**。
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
   [html 路径: /mnt/d/2Study/StudyNotes/SKILLS/备忘录/output/wish_plan_20260724_HHMMSS.html]
   <media src="/mnt/d/2Study/StudyNotes/SKILLS/备忘录/output/wish_plan_20260724_HHMMSS.html" type="file" />
   + AI 同步:用系统默认浏览器(Chrome 等)打开同一文件
   ```

5. **触发词场景对应交付协议**(每个都 `<media>` + 浏览器并行):
   - 5 个查询触发词(搜备忘/查备忘/看备忘/按时间搜备忘/查已提醒备忘 + 子唤醒词查心愿/查打卡/查情绪):AI 推荐 `--html` 后并行
   - 备忘录同步(sync-from-feishu `--html`):同上
   - 心愿排期向导(wish-batch-plan `--html`):用户勾选 + 复制 + 粘贴回 AI,**第一步并行**
   - 心愿完成向导(wish-complete `--html`):同上
   - 批量改分类向导(batch-update-category `--html`):同上

6. **优先级**:本规范与"HTML 同步"同级(最高优先级)。

7. **历史修订**:
   - v1.0.2(2026-07-24):最初版,误写"绝对禁止 AI 主动唤起浏览器"
   - v1.0.3(2026-07-24):纠正 — 用户确认 `<media>` 与浏览器打开应并行,**非互斥**


## 描述

私人备忘工具,支持随时记录、分类整理、时间检索、媒体附件、定时提醒和打卡追踪。

**触发词**:记备忘、搜备忘、查备忘、改备忘、删备忘、看备忘、按时间搜备忘、备忘改分类、备忘改子分类、记提醒、设提醒、看提醒、查已提醒备忘、完成心愿(**别名:完成打卡 · 2026-07-24 加**)、心愿排期、备忘录同步

**分类子唤醒词**(心愿/打卡/情绪日记,自带顶层分类,操作同上):
- 记心愿、删心愿、改心愿、查心愿
- 记打卡、删打卡、改打卡、查打卡
- 记情绪、删情绪、改情绪、查情绪(情绪日记的子唤醒词)

## 快速开始

复制以下 prompt 给 AI 安装技能:

```
请帮我安装备忘录技能:
1. 读取 SKILL.md 了解功能
2. 检查环境变量,交互式帮助用户配置,强烈建议用户配置属于自己专属的环境变量
3. 运行 script/init.sql 初始化数据库
4. 设置 cron 任务:每分钟检查提醒,通过 QQ 渠道推送消息
5. 验证:运行 python3 script/memo_cli.py --help
```

**⚠️ Cron 任务特性**:
- 当有待提醒事项时 → 通过 message 工具发送到 QQ
- 当无提醒事项时 → 输出「NO_REPLY」静默,不发送任何消息
- 提醒检查由 SKILL 内部逻辑决定,cron payload 只触发执行,不描述判断结果

## 环境变量

| 变量名 | 必填 | 说明 | 默认 |
|--------|------|------|------|
| `SKILLS_DB_PATH` | 否 | 数据库根目录(统一配置) | 父目录 .db/ 层层找 |
| `MEMO_MEDIA_DIR` | 否 | 媒体文件目录 | `media` |

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

## 功能与触发词

### 添加笔记
- 触发词:记备忘
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
- 触发词:搜备忘、查备忘(别名)
- 子唤醒词:查心愿、查打卡、查情绪日记(自动带 `-c 顶层分类` 过滤)
- 命令:`script/memo_cli.py search "关键词" [-c 顶层分类] [-s 子分类] [--html]`
- **过滤维度**:可同时按顶层分类和子分类过滤(如 `search -c 备忘 -s 学习`)
- **默认行为**:CLI 默认返回结构化 JSON。需要可视化时传 `--html` flag 生成 HTML 查询结果页(模板 `templates/memo_query.html`,通过 `script/memo_render.py` 注入到 `output/memo_query_*.html`)。**当前没有 `--no-html` flag**(2026-07-24 文档对齐修订)。
- **AI 推荐流程**:9 个查询类触发词(搜备忘 / 查备忘 / 看备忘 / 按时间搜备忘 / 看提醒 / 查已提醒备忘,以及子唤醒词 查心愿 / 查打卡 / 查情绪日记)在收到 JSON 后,**主动**调一次 `memo_cli.py <cmd> --html` 生成 HTML 给用户,而不是只展示 JSON 文本。理由:清单类数据"扫读 + chip 筛选 + 复制 ID/回执"在 HTML 里体验远超文字流。**例外**:用户明确说"只要 JSON" → 不传 `--html`。
- **HTML 模板模式**:CLI 仍先取 JSON 数据,再通过 `script/memo_render.py` 注入 `templates/memo_query.html`,生成 `output/memo_query_*.html`;模板只展示数据,不直连数据库、不污染原模板
- **HTML 数据契约**:`{"status":"ok","data":{"title":"...","command":"search","generated_at":"...","items":[...]}","message":"..."}`
- **页面能力**:首屏摘要卡、当前结果内搜索、分类/子分类 chip 筛选、排期/提醒/附件徽章、空态、复制 ID、复制查询回执

### 更新笔记
- 触发词:改备忘
- 子唤醒词:改心愿、改打卡、改情绪日记(先按顶层分类搜索,再更新)
- 先搜索找到笔记 ID,再更新
- 命令:`script/memo_cli.py update <id> [--content "新内容"] [-c 顶层分类] [-s 子分类]`
- **子分类规则**:sub_category 是自由文本字段,适用于所有 category(详见上方"sub_category 原则")

### 删除笔记
- 触发词:删备忘
- 子唤醒词:删心愿、删打卡、删情绪日记(先按顶层分类搜索,再删除)
- 先搜索找到笔记 ID,再删除
- 命令:`script/memo_cli.py delete <id> [--with-reminders]`

### 查看笔记详情
- 触发词:看备忘
- 命令:`script/memo_cli.py get <id> [--html]`
- **默认行为**:CLI 默认返回单条 JSON。需要 HTML 详情页时传 `--html`(复用 `templates/memo_query.html`,items 数组只有 1 条)。
- **AI 推荐流程**:与"搜索笔记"段对齐——收到 JSON 后主动调一次 `get <id> --html` 生成详情页给用户。

### 按时间搜索
- 触发词:按时间搜备忘
- 命令:`script/memo_cli.py search-date <start> <end> [-c 分类] [--html]`
- **默认行为**:CLI 默认返回 JSON。需要 HTML 时传 `--html`(复用 `templates/memo_query.html`)。
- **AI 推荐流程**:与"搜索笔记"段对齐——收到 JSON 后主动调一次 `search-date ... --html` 生成按时间查询页给用户。

### 编辑笔记顶层分类
- 触发词:备忘改分类
- 先搜索找到笔记 ID,再更新顶层分类
- 命令:`script/memo_cli.py update-category <id> <顶层分类>`
- **副作用**:改顶层分类时**不会**清空 `sub_category`(sub_category 是内容维度的二阶属性,与顶层分类独立)

### 编辑笔记子分类
- 触发词:备忘改子分类
- 先搜索找到笔记 ID,再更新子分类
- 命令:`script/memo_cli.py update-sub-category <id> <子分类 | null>`
- **规则**:适用于所有 category(sub_category 是自由文本字段);传 `null` 表示清除子分类

### 触发词路由(避免与「批量改分类向导」歧义 · 2026-07-24 加)
**触发词 `备忘改分类` 同时对应两个命令,AI 必须按以下规则二选一**:
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
- 触发词:心愿排期
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

### 完成心愿向导(2026-07-24 新增 · Step 5A · 过程型 HTML · v1.0.1 第一性修复 · v1.0.4 默认未勾)
- 触发词:完成心愿(**别名:完成打卡 · 2026-07-24 加**)· 批量场景:「这些心愿我都完成了」「心愿 #36 #48 完成」「完成打卡 #36 #48」
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
- 触发词:备忘改分类(批量场景,如「把 X 分类下这 10 条都改到 Y 分类」)
- 命令:`script/memo_cli.py batch-update-category --from-category <原> [--to-category <新>] [--html]`
- **类型**:过程型 HTML(同 wish-batch-plan/wish-complete 模式)
- **第一性**:update-category 是单 id 命令(`update-category <id> <category>`),批量场景用户在 HTML 选要改的 + 选目标分类
- **--from-category**:原分类(白名单:备忘/心愿/打卡/情绪日记)
- **--to-category**:建议目标分类(HTML 可改;硬规则:不与 --from-category 相同)
- **副作用**:只改 `category`,**不动 `sub_category`**(sub_category 是内容维度的二阶属性)
- 模板:`templates/change_category.html`(独立)
- 渲染器:`script/memo_render.py:render_change_category`
- **4 部分 prompt**(采纳按钮复制):
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
- 触发词:设提醒
- 时间识别:明天、后天、今天 + 时间
- 重复规则:每天,每天→每天,每周→每周,每月→每月,每年→每年
- 流程:直接创建提醒,无需先有笔记(提醒内容存 reminders.content)
- 命令:`script/memo_cli.py remind <note_id> --at "YYYY-MM-DD HH:MM" --content "提醒内容" --repeat-type 每天 --rule "09:00"`

### 记提醒(添笔记 + 设提醒)
- 触发词:记提醒
- 时间识别:明天、后天、今天 + 时间
- 重复规则:每天,每天→每天,每周→每周,每月→每月,每年→每年
- 流程:先添加笔记,再设置提醒(笔记内容 + 提醒内容分别存储)
- 命令示例:`script/memo_cli.py add "我要健身" -c 心愿 && script/memo_cli.py remind <id> --at "09:00" --content "跑步10分钟" --repeat-type 每天`

### 查看提醒
- 触发词:看提醒
- 命令:`script/memo_cli.py reminders [--status active|dismissed] [--html]`
- **默认行为**:CLI 默认返回 JSON。需要 HTML 时传 `--html`(复用 `templates/memo_query.html`,按重复类型提供筛选 chip)。
- **AI 推荐流程**:与"搜索笔记"段对齐——收到 JSON 后主动调一次 `reminders --html` 生成提醒列表页给用户。

### 废弃提醒
- 命令:`script/memo_cli.py dismiss <id>`

### 查询已完成提醒
- 触发词:查已提醒备忘
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

### 备忘录同步(自动 + 反向)
本技能可在**飞书 CLI 已安装**时与飞书任务双向联动:

- **触发词**:备忘录同步
- **自动联动**(无需触发词):
  - `add 心愿`:自动建飞书 task,写回 `notes.feishu_task_guid`
  - `update 心愿`:自动同步更新飞书 task 标题
  - `delete 心愿`:自动标飞书 task 完成(飞书无 delete 概念)
  - `complete-wish 心愿`:自动标飞书 task 完成
- **双向对账**(触发词触发):`备忘录同步`
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
  - 输出:`output/sync_report_YYYYMMDD_HHMMSS.html`
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

### 完成心愿:流式工作流
心愿完成是一个**原子操作**:删除原心愿 + 新建打卡 note,两步必须同时成功或同时回滚。
- 触发词:完成心愿
- 命令:`script/memo_cli.py complete-wish <心愿id> [--content "打卡内容"]`
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

**说明**:`${SKILL_DIR}` 是占位符,部署时替换为技能实际目录的绝对路径(如 `/mnt/d/2Study/StudyNotes/SKILLS/备忘录` 或 `D:\2Study\StudyNotes\SKILLS\备忘录`)。Payload 只负责触发 skill 执行,不描述"有提醒/无提醒"的判断逻辑,该逻辑由 SKILL 内部决定。

## 参考文档

- 数据库结构:`reference/schema.md`
- 对话示例:`reference/examples.md`
- Cron 配置:`reference/cron.md`
