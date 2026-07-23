---
name: 作息管家
description: >
  作息记录与日程计划管理技能。当用户使用以下指令时触发:
   准备消息(废弃)、同步作息(废弃)、增量同步(废弃)、(同步类)、
   今天总结、汇总作息(摘要类)、
   查作息、查作息详情、查作息时间轴、查作息范围、查作息游标、查作息状态(查询作息记录)、
   查日程、看日程、24h 概览、查多日计划(查询日程计划)、
   商量计划、一起规划、规划明天、规划一天、讨论计划(新版事件型日程计划 + 飞书日历联动)、
   改计划、删计划、补计划、复盘、日程管家同步(新版 6 个命令,含 Phase 0 反向对账)、
  初始化数据库(管理类)、
  配置定时同步(废弃)、配置每日报告(Cron类)。
  当本机装了飞书 CLI(lark-cli)且已授权,日程计划可一键同步到飞书日历(拆分分钟级事件、增删改实时联动)。

  ## 旧称兼容说明

  历史唤醒词"作息计划表 / 作息表 / 计划作息表 / 实测作息 / 查作息计划"已全部废弃,
  AI 不应尝试用历史理解匹配新表。若用户使用旧称,应回答
  "该术语已废弃,请改用'日程计划'(日程模块) 或'作息记录'(记录模块)"。
  所有操作通过 Python CLI 执行数据库读写,AI 负责语录分析和作息生成。
metadata: { "openclaw": { "emoji": "🌙", "requires": { "python": ">=3.7", "optional": { "lark-cli": ">=1.0.59 for feishu sync" } } } }
---

## 强制规定(最高优先级)

1. **所有变动必须体现在 HTML 上** - 本技能的任何优化、变动、脚本的所有变动,都必须同步更新 `作息管家.html` 页面。
2. **此规定优先级最高** - 优先级高于所有其他规则和流程。
3. **任何修改需用户确认** - 对本技能所有文件、脚本的任何一行修改,都必须明确得到用户的 1 次确认后才能执行。

---

> **版本**: 2026-06-29 重构版(新增:事件型计划 + 飞书日历联动)

---

## 功能速查

> **AI 使用约定**:用户说任何唤醒词后,先读"详见"列跳到"功能详细说明"对应章节,不要只看本表。本表只列功能 + CLI,详细执行流程、约束、飞书同步策略都在对应章节里。

| # | 唤醒词 | 功能 | CLI 命令 | 详见 |
|---|--------|------|----------|------|
| **0** | **记作息 / 补一条作息 / 录作息** | **单条记录写入(规范化入口,所有 9 字段强校验)** | **`add <9 字段> 或 --json @file`** | **详见 0. 记作息(add)** |
| 1 | 准备消息(游标分页) | 从 daily_recorder 拉消息供 AI 分析(默认 200 条/页) | `prepare-messages [<开始> [<结束>]] [--page N] [--page-size N]` | 详见 1. 同步作息 |
| 2 | 同步作息 | 完整同步流程(准备消息→AI 分析→逐条 add) | `prepare-messages` → AI → `add` | 详见 1. 同步作息 |
| 3 | 增量同步 | 从游标位置继续同步(自动读取 get_last_record_full 拿游标) | `prepare-messages` | 详见 1. 同步作息 |
| 4 | 今天总结 | 按分类汇总当日时间(满24h出综合报告,不满出摘要) | `report <日期>` 或 `summary <日期>` | 详见 2. 生成摘要 |
| 5 | 汇总作息 | 日期范围汇总统计 | `range <开始> <结束>` | 详见 3. 查询作息 |
| 6 | 查作息 | 查看指定日期作息列表 | `list [日期]` | 详见 3. 查询作息 |
| 7 | 查作息详情 | 含AI推理过程的详细展示 | `detail [日期]` | 详见 3. 查询作息 |
| 8 | 查作息时间轴 | 24小时时间轴展示 | `timeline [日期]` | 详见 3. 查询作息 |
| 9 | 查作息范围 | 日期范围统计 | `range <开始> <结束>` | 详见 3. 查询作息 |
| 11 | 查作息状态 | 记录数/天数/日期范围 | `status` | 详见 3. 查询作息 |
| **12** | **查日程 / 看日程(默认)** | 查单日完整事件 + 飞书同步状态(id / notes / category / feishu_event_id / completion)。**带具体标题时**(如"今天有健身吗")→ `search-plan-event` 精确匹配(2026-07-15 起可选 `--time-start/--time-end` 按三元组查重) | `list-events <日期>` 或 `search-plan-event <日期> --title X [--time-start HH:MM --time-end HH:MM]` | **详见 3.1 查询日程** |
| **13** | **补计划** | 单条追加日程事件。**幂等(2026-07-15 修复):按 (date+time_start+time_end) 三元组查重,title 不参与(title 是展示标签不是身份)**。与商量计划的区别:补 = 增量一条,商量 = 完整24h规划 | `ensure-plan-event <日期> --time-start HH:MM --time-end HH:MM --title X` | **详见 10. 补计划与程序化接口** |
| **14** | **复盘** | 对当天日程逐条回顾:哪些做了、哪些没做、为什么 → 写入 completion 字段 | `list-events` → 逐条 `update-event --completion` | **详见 11. 复盘** |
| 15 | 24h 概览 | 24h 时间表聚合视图(同小时用 + 合并) | `query-plans <日期>` | 详见 3.1 查询日程 |
| 16 | 查多日计划 | 多日简版视图(不含 notes/completion/飞书状态) | `query-plans <日期1,日期2,...>` | 详见 3.1 查询日程 |
| **17** | **商量计划** | AI + 用户多轮讨论 → 结构化事件 → 24h 录满写入 + 询问飞书同步 | `upsert-plan-events <日期> --json @plan.json` | **详见 4. 商量计划(核心入口)** |
| **18** | **改计划** | 单条精细修改(含 completion 标记) | `update-event <id> [--title/--completion/...]` | **详见 5. 改计划** |
| **19** | **删计划** | 单条软删(is_active=0),询问飞书同步删除 | `deactivate-event <id>` | **详见 6. 删计划** |
| **20** | **日程管家同步** | Phase 0 反向对账 + diff 询问 create/update/delete | `feishu-resync <日期>` | **详见 8. 日程管家同步** |
| 21 | 飞书探测 | 三档探测 cli 安装 / auth 授权 / 日历写入权限 | `python scripts/feishu_sync.py` | 详见 9. 飞书探测 |
| 22 | 初始化数据库 | 创建三张数据表(含 completion 字段) | `init` | - |

---

## 术语与唤醒词隔离

| 模块 | 主称呼 | 允许词根 | 禁止词根 | 内部表 |
|---|---|---|---|---|
| 真实发生的时间块 | 作息记录 | 作息、记录、流水、实际、同步、汇总、时间轴 | 计划、日程 | `schedule_records` |
| 未来或当天安排 | 日程计划 | 计划、日程、安排、规划、复盘 | 作息、记录 | `schedule_plans` |

**强制规则**：日程计划的唤醒词不能包含“作息/记录”；作息记录的唤醒词不能包含“计划/日程”。旧交叉词仅作为历史资料理解，不再写入唤醒词表。

---

## 分类系统（2026-07-22 重构）

作息分类采用 **8 个一级 + 白名单二级** 结构。所有写入路径都强制走 `scripts/validators.py` 校验。

### 一级（固定 8 个）

| 一级 | 含义 |
|---|---|
| 维持 | 维持个体生存和基础状态（睡眠/吃饭/洗漱/通勤）|
| 健康 | 改善身体/心理状态（运动/健身/修行/冥想）|
| 工作 | 产出价值/完成任务（与职业相关或不相关）|
| 学习 | 吸收新知/掌握技能 |
| 创作 | 输出原创内容 |
| 投入 | 与人/动物/社群互动（家人/朋友/伴侣/宠物）|
| 调整 | 主动放松/恢复/娱乐（游戏/追剧/发呆/午睡）|
| 日常 | 无明确主要目的的杂事（代办/收拾/行政）|

### 二级（白名单制）

- 初始 ~70 个，写在 `scripts/validators.py::DEFAULT_WHITELIST`
- 用户/AI 扩展项写到 `.db/category_whitelist.yaml`
- 运行时合并两层白名单
- **不允许三级**（避免爆炸）

### 心法（5 条）

详见 `references/分类心法.md`：

1. 一句话可能暗示 N 件事 → 拆 N 段，每段归类
2. 模糊兜底：无法拆解时 → 选最相似分类（兜底率 < 15%）
3. 意图 vs 实际：按当前段已说出的话判，不判打算
4. AI 对话不入作息：除非用户明确说"把对话归档"
5. **遇到白名单外活动 → 主动提议，不要静默兜底**（申请制）

### 申请新分类流程（AI/星火）

```
1. AI 录入时遇到未白名单 category → 校验报错
2. AI 输出"提议新增 X" + 场景说明
3. 用户口头确认
4. AI 调 approve-category 写入 YAML
5. 下一条 add_record 立即可用
```

### CLI 命令

```bash
python scripts/schedule_cli.py list-categories [--level 1|2] [--json]
python scripts/schedule_cli.py propose-category --code "一级.二级" --hint "场景"
python scripts/schedule_cli.py approve-category --code "一级.二级"
```

### 飞书 emoji 联动（2026-07-22）

每个 category 同步到飞书时，会在飞书事件 **description 头部** 自动加 emoji 前缀。

| 一级 | emoji | 一级 | emoji |
|---|---|---|---|
| 维持 | 🌱 | 创作 | 🎨 |
| 健康 | 💪 | 投入 | 🤝 |
| 工作 | 💼 | 调整 | 😌 |
| 学习 | 📖 | 日常 | 📋 |

二级 emoji 完整 70+ 个见 `scripts/validators.py::CATEGORY_EMOJI_LEVEL2`。

**示例**：category=`健康.健身` → 飞书 description = `[💪🏋️ 健康.健身] | 练背+有氧 | 作息管家自动同步`

> **强制规定**：分类心法变更必须同步更新 `作息管家.html` 镜像。

---

## 核心规则(违反即无效)

1. **禁止直连数据库** - 所有操作必须通过 CLI 接口
2. **禁止 DELETE** - 只允许 INSERT / UPDATE
3. **source_contents 必须是消息原文** - 一字不差,不得总结或臆造
4. **时间必须连续** - 每条 time_start = 上一条 time_end,末尾处理规则:
   - 过去日期:最后一个 block 的 time_end 可补到 23:59
   - 当天:time_end 不得超过当前时刻
5. **粒度最大化** - 能独立成一件事的不要合并:
   - 每次活动切换即切割 block,不为省记录数而合并
   - 示例1:07:58出门→08:03到公司→08:05开会
     应拆为:07:58~08:03(通勤)、08:03~08:05(到达后休息)、08:05~(会议)
     而不是:07:58~08:05(通勤+会议合并为一个block)
   - 示例2:连续消息讨论同一主题(如连续5条消息讨论同一工作问题)→合并为一个block
   - 宁可多条记录,不要漏记活动切换点

> 详细规范见: `references/操作规范.md`

---

## 📦 安装与配置

### 依赖

- Python >= 3.7
- 无第三方依赖(仅用标准库 sqlite3、argparse、datetime)

### 配置项

| 环境变量 | 说明 |
|---------|------|--------|
| `SKILLS_DB_PATH` | 数据库文件所在目录 |

DB 查找顺序:`SKILLS_DB_PATH` 环境变量 → 技能目录 → 父目录 `.db/` 文件夹 → 自动创建 `.db/` 目录。

### 一键安装 prompt

将以下内容发送给 AI 即可安装本技能:

```
请帮我安装作息管家技能:
1. 检查 Python 环境
2. 引导我配置环境变量
3. 显示当前环境变量配置
4. 告诉我如何更改数据目录
```

---

## 功能详细说明

### 0. 记作息（add · 2026-07-22 新增规范化入口）

**触发词**：记作息 / 补一条作息 / 录作息

**核心语义**：把 1 条作息记录**规范化写入** schedule_records。**所有写入路径都走这一入口**，绕过 `add` 直接调 `add_record_full` 函数属于违规。

**必填 9 字段**：
1. `date`（YYYY-MM-DD）
2. `time_start`（HH:MM）
3. `time_end`（HH:MM）
4. `duration_minutes`（整数）
5. `activity`（活动描述）
6. `category`（必须通过白名单校验，8 一级 + 70 二级）
7. `source_contents`（消息原文，一字不差）
8. `source_timestamps`（消息时间戳，原始）
9. `analysis_reasoning`（AI 推理过程）

**调用方式**：

```bash
# 方式 A: 命令行参数(适合 1 条)
python scripts/schedule_cli.py add \
  --date 2026-07-22 --time-start 10:00 --time-end 11:00 \
  --duration-minutes 60 --activity "写小帅相关代码" \
  --category "工作.AI调优" \
  --source-contents "我在优化 AI" --source-timestamps "10:00" \
  --analysis-reasoning "AI 主动优化"

# 方式 B: JSON 文件(适合批量)
python scripts/schedule_cli.py add --json @record.json
```

**返回**：

```json
{
  "status": "ok",
  "data": {"id": 3582, "category": "工作.AI调优", "date": "2026-07-22"},
  "message": "✓ 记录 id=3582 已写入 (2026-07-22 10:00~11:00 工作.AI调优)"
}
```

**一级 category 警告**（Q2=C 决策）：当你传 `category="创作"`（纯一级），会写入成功但附加 warning 提示"建议细化到二级"（给出可选二级列表）。

**失败处理**：
- 缺字段 → 返回 `{"status": "error", "missing": [...]}` 
- 非法 category → 返回 `{"status": "error", "message": "category 校验失败: ..."}` 含**字段名+当前值+期望值+怎么修**
- 字段类型错（如 `duration_minutes` 非整数）→ 返回具体错误

**为什么是规范化入口**：
- 之前版本只有 `add_record_full()` Python 函数，AI 调用时容易绕过校验
- 现在 CLI 入口强制走校验 + JSON 三段式输出，AI 无法"偷懒"
- 任何 ai/星火录入流程都应走 `add` CLI，**禁止直调函数**

### 1. 同步作息

将语录消息分析为细粒度作息记录。

**执行流程**:
1. 调用 `prepare-messages` 获取消息(始终分页,默认每页200条)
   - 检查返回 JSON 中的 `pagination.has_next`:若为 `true`,处理完当前页后用 `--page N` 获取下一页
   - 消息量少时只有1页,无需额外操作
2. **前置:获取最少 block 数量**
   ```python
   from block_count import get_required_block_count

   # 获取该时间区间最少需要的 block 数量
   # messages_per_block: 每个 block 最多承载的消息数(默认5)
   required_min = get_required_block_count(start_ts, end_ts, messages_per_block=5)
   ```
3. AI 用滑动窗口(前5后5)判断活动边界
4. 逐条调用 `add_record_full()` 写入(9字段全填)
5. 前5后5窗口推断:
   - 以block「开始时间点」为中心,取前5条消息推断该时间段起点前的活动
   - 以block「结束时间点」为中心,取后5条消息推断该时间段终点后的活动
   - 日期边界:首条消息无法说明00:00~首条时间点;末条消息无法说明末条时间点~23:59
     → 用「前一天末尾5条+当天开头5条」推断开头时段
     → 用「当天末尾5条+下一天开头5条」推断结尾时段
6. **后置:验证 block 数量是否达标**
   ```python
   from block_count import validate_record_count

   result = validate_record_count(start_ts, end_ts, messages_per_block=5)
   # result == True: 验证通过
   # result is str: 验证失败,提示词会告诉 AI 哪里不足、如何修正
   if result is not True:
       # AI 必须根据提示词重新拆分,直到验证通过
       ...
   ```
7. 保证首尾相接

**粒度原则**:按活动切换点细分,宁可多条不要合并。

> 执行同步操作必须读取: `references/同步流程.md`

---

### 2. 今天总结

按分类汇总当日作息时间(自动选择输出等级)。

**触发词**:今天总结 / 生成摘要 / 查作息报告

AI 判断逻辑:
- **records 已满 24h** → 调 `report <日期>`(list + summary + timeline 综合报告)
- **records 未满 24h** → 调 `summary <日期>`(仅按分类汇总,并提示补全记录后再看完整报告)

**输出格式**:
```
📊 2026-05-22 作息摘要
  😴 睡眠: 7h0m
  💼 工作: 4h0m
  🚴 通勤: 0h36m
  总计: 24h ✓
```

---

### 3. 查询作息

| 命令 | 说明 |
|------|------|
| `list [日期]` | 查看指定日期作息 |
| `detail [日期]` | 详细展示(含AI推理) |
| `summary [日期]` | 查看每日摘要 |
| `timeline [日期]` | 时间轴展示 |
| `report [日期]` | 完整报告 |
| `range <开始> <结束>` | 日期范围统计 |

> 详细命令见: `references/CLI命令.md`

#### 3.x 作息记录查询 → HTML 多模板报告（2026-07-23 重构 · 5 模板 8 命令）

**核心语义**：AI 收到"查作息"+日期 → 调对应命令 → 从 `schedule_records` 表现读数据 → 派生 4 段内容 + 健康分 + AI 钩子 → 写一份**单文件离线 HTML**到 `SKILLS_DB_PATH/schedule_html/record/{day|range|compare|category|anomaly}/...` → AI 拿到 `file_path` 后用 `<media>` 交付给用户。

**触发词与命令路由**：

| 触发词（用户问法示例） | 命令 | 模板 | 输出路径 |
|---|---|---|---|
| 查作息 2026-07-15 / 昨天我做了什么 | `render-record-day <date>` | T1 单日 | `record/day/<date>_record_day.html` |
| 这一周怎么样 / 7/13~7/19 看看 | `render-record-range <start> <end>` | T2 区间 | `record/range/<start>_to_<end>_record_range.html` |
| 6 月 vs 7 月 / 上周 vs 这周 | `render-record-compare-months <YYYY-MM> <YYYY-MM>` | T3 对比 | `record/compare/<labelA>_vs_<labelB>_record_compare.html` |
| 这 7 天健身什么时候做的 | `render-record-category-range <start> <end> <cat>` | T4 类别深挖 | `record/category/<cat>_<start>_to_<end>_record_category.html` |
| 最近状态 / 有没有异常 | `render-record-anomaly [--window 7]` | T5 异常 | `record/anomaly/<today>_w7_record_anomaly.html` |

**5 模板设计原则**（基于"让用户感知问题"的第一性原理）：

1. **L1 速读层（5 秒）**：4 张数字卡（活跃分类/总时长/健康分/睡眠），健康分 0-100（红/黄/绿）
2. **L2 趋势层（30 秒）**：分类进度条 + 24h 时间轴 + 7 维趋势折线 + 24h×N 天热力图 + 雷达
3. **L3 决策层（3 分钟）**：**AI 思考钩子卡**（黄底）— 模板自带 `data.ai_questions[]` 字段，AI 看后能直接追问用户
4. **对比基线**：每张报告都嵌 3 个对比维度（时间/目标/理想）让用户看到"差距"
5. **5 状态**：正常 / 空 / 缺 / 错 / 离线(常驻 banner)，手册 §7 必备

**模板文件结构**（5 模板 + 共享 CSS/JS）：

```
作息管家/templates/
├── _record_styles.css      # 5 模板共享样式表(7.0KB)
├── _record_engine.js       # 5 模板共享 JS 引擎(13.5KB)  模式分发:record-day/range/compare/category/anomaly
├── schedule_record_day.html       # T1 单日
├── schedule_record_range.html     # T2 区间
├── schedule_record_compare.html   # T3 对比
├── schedule_record_category.html  # T4 类别深挖
└── schedule_record_anomaly.html   # T5 异常
```

5 模板 HTML 全部引用共享 CSS/JS 引擎，`render-and-write` 写文件时**自动把 `_record_styles.css` 和 `_record_engine.js` 复制到输出目录**，让 HTML 离线可读。

**输出路径硬绑**：`SKILLS_DB_PATH/schedule_html/record/{子目录}/<file>.html`

- `day/YYYY-MM-DD_record_day.html`
- `range/YYYY-MM-DD_to_YYYY-MM-DD_record_range.html`
- `compare/<labelA>_vs_<labelB>_record_compare.html`
- `category/<category>_YYYY-MM-DD_to_YYYY-MM-DD_record_category.html`
- `anomaly/YYYY-MM-DD_w<N>_record_anomaly.html`

**约束**：

- 目录 `record/day/` `record/range/` 等必须已存在（**不静默建**）— 报错文案带字段名+当前值+修复建议
- 同日期/区间覆盖写（用户主动调就期望刷新）
- HTML 单文件 + 共享 CSS/JS 一起输出（不依赖 CDN）
- 第 ③ 段"AI 叙事亮点"待 Phase 2（暂用 `data.highlights=[]` 占位）

**5 模板详细技术**（与 plan 域的 1 模板设计对比）：

| 项 | plan 域 | record 域 |
|---|---|---|
| 模板数 | 1（多 mode） | 5（每 mode 一模板） |
| 核心算法 | `cat_minutes / hour_cats` | `cat_minutes / hour_dominant / 7维聚合 / 健康分 / 异常检测 / 热力图` |
| 共享层 | 1 模板 + 1 JS | 1 CSS + 1 JS + 5 薄壳 HTML |
| 派生函数 | `render_list_events / render_query_plans` | `render_record_day/range/compare/category/anomaly`（6 个） |
| 视觉设计语言 | Apple 风浅色 + 摘要+时间轴+卡片 | 同上,额外加：健康分大卡、7 维趋势 SVG、24h×N 天热力图、7 维雷达 SVG、AI 思考钩子卡 |

**实现位置**：
- 共享算法：`scripts/calculations.py`（新文件,376 行,共享派生函数:健康分/异常检测/AI 钩子生成）
- 共享样式：`templates/_record_styles.css`
- 共享 JS：`templates/_record_engine.js`
- 渲染器：`scripts/schedule_html_render.py`（6 个 `render_record_*` 函数 + `template_map` 5 条 + `default_output_path` 5 条分支）
- CLI 入口：`scripts/schedule_cli.py` 的 7 个 `cmd_render_record_*` 子命令（+ 1 兼容旧 `render-record-report`）
- 触发词路由：AI 协同时按上表"触发词"列匹配命令

**与原命令的边界**：

| 场景 | 用哪个 |
|---|---|
| 终端查、复制粘贴 | `list / detail / summary / timeline / report / range / status`（文本，7 个原命令保留） |
| 浏览器看、截图分享、可视化 | `render-record-day / range / compare / category / anomaly`（HTML，5 模板） |
| Cron 7:30 自动推送 | **已废**（reports/ 目录已删） |
| 一次性查某月 vs 某月 | `render-record-compare-months 2026-06 2026-07`（快捷） |
| 单类深挖（健身什么时候做的） | `render-record-category-range 2026-07-01 2026-07-31 健身` |
| 异常检测（最近 7 天是否有偏差） | `render-record-anomaly --window 7` |

**旧 `render-record-report` 兼容**：保留命令，`mode="record-report"` 在 `template_map` 映射到 `schedule_record_day.html`，调用 `render_record_day()` 函数，输出路径迁移到 `record/day/YYYY-MM-DD_record_day.html`。

**触发词与命令映射路由表**（AI 协同时优先查此表）：

| 用户说 | 调 |
|---|---|
| 查作息 / 查作息报告 / 查作息 YYYY-MM-DD / 昨天我做了什么 | `render-record-day <date>` |
| 这一周 / 最近 7 天 / 7/13~7/19 看看 | `render-record-range <start> <end>` |
| 6 月 vs 7 月 / 整月对比 | `render-record-compare-months 2026-06 2026-07` |
| 这周 vs 上周 / 这月 vs 上月 / 两段时间对比 | `render-record-compare <labelA> <startA> <endA> <labelB> <startB> <endB>` |
| 健身习惯 / 健身什么时候做的 / 健身频次 | `render-record-category-range <start> <end> <category>` |
| 最近状态 / 有没有异常 / 异常检测 | `render-record-anomaly --window 7` |

**完整 AI 操作流程**（M12:用户操作闭环）：

1. **校验日期/参数** — 命令入口先校验输入合法性（日期格式 / window 1-90 / 类别名已知 / 起止日期 start ≤ end）。失败时 `{"status":"error","message":"...字段名+当前值+期望值+怎么修"}` 不写盘。
2. **派生数据 + 写文件** — `render-record-*` 命令调 `calculations.py` 派生函数（健康分 / 异常检测 / AI 钩子 / 17 维业务洞察），再 `inject_into_template` 写 HTML 到 `SKILLS_DB_PATH/schedule_html/record/<sub>/<file>.html`。同时把共享 CSS/JS 引擎复制到输出目录。
3. **AI 交付给用户** — 命令 stdout 输出 `{status, data:{file_path, bytes, mode, date/range/category}, message}` 三段式 JSON。AI 用 `<media src="file_path" type="file" />` 把 HTML 推给用户，让用户在浏览器看完整可视化报告。

> 常见错误：如果 `<media>` 后用户说"打开是空白"，说明 `record/<sub>/` 目录不存在 — 文档第 3.1.2 节"约束"明确不静默建目录,需用户自己 `mkdir -p`。

---

#### 3.x.1 作息记录查询 → HTML 单日报告（2026-07-23 新增 · 4 段结构 · 兼容保留）

**4 段结构**（沿用 2026-06-25.html 等历史报告视觉）：

| 段 | 内容 | 数据来源 |
|---|---|---|
| ① 时间分配 | 12 个分类卡片（emoji + 时长 + 横向进度条 + 占比%）+ 总计 | `cat_minutes`（按 category 聚合 `duration_minutes`） |
| ② 24h 时间轴 | 24 段色块（每段 dominant category 颜色）+ hover tooltip + 图例 | `hour_cats[24]`（每条按分钟切片到小时桶，取主导分类） |
| ③ 当日亮点 | **当前为占位**（`data.highlights[]` 默认空），后续 Phase 2 可支持 AI 叙事 | 暂不派生 |
| ④ 睡眠分析 | 主睡眠段（最长睡眠段）+ 总睡眠段数 + 充足判断（≥7h） | `sleep_records`（按 `duration_minutes` 排序） |

**调用方式**：

```bash
# 标准用法（最常用）
python scripts/schedule_cli.py render-record-report 2026-07-15
# → stdout:
# {"status":"ok","data":{"file_path":"D:\\2Study\\StudyNotes\\.db\\schedule_html\\record\\2026-07-15_record_report.html","bytes":16717,...},"message":"✓ ..."}
# AI 用 <media src="D:\\...\\2026-07-15_record_report.html" type="file" /> 把文件交付给用户
```

**约束**：

- 输出文件路径**硬绑** `SKILLS_DB_PATH/schedule_html/record/<date>_record_report.html`，**不传 `--out`**（破坏兼容 — 旧 `作息管家/reports/` 已被一刀删除）
- 目录不存在 → 报错退出（**不静默创建**），错误文案带字段名+期望值+修复建议
- 同日期覆盖写（用户主动调就期望刷新）
- 模板：`templates/schedule_record_report.html`（沿用历史 CSS + 4 段布局；含 5 大状态：正常 / 空 / 缺 / 错 / 离线）

**实现位置**：
- 模板：`templates/schedule_record_report.html`
- 渲染器：`scripts/schedule_html_render.py`（`render_record_report()` 函数 + 4 段算法；`COLOR_MAP`/`EMOJI_MAP`/`_fmt_dur` 复用历史脚本）
- CLI 入口：`scripts/schedule_cli.py` 的 `cmd_render_record_report()` 子命令
- 数据来源：调用 `schedule_db.get_records_by_date()` 现读（**不依赖任何中间文件或 `/tmp` JSON**）

**与原命令的边界**：

| 场景 | 用哪个 |
|---|---|
| 终端查、复制粘贴、AI 引用 | `list / detail / summary / timeline / report / range / status`（文本） |
| 浏览器看、截图分享、可视化 | `render-record-report <日期>`（HTML） |
| Cron 7:30 自动推送 | **已废** — `reports/` 目录被删，cron 7:30 报告链路不再工作。如需恢复，需用 `render-record-report` 重写 |

---

### 3.1 查询日程(默认 `list-events`)

**核心规则**:用户说"查日程/看日程"时,AI **必须默认走 `list-events`**,**不是** `query-plans`。

**上下文路由**:
- 用户说"今天有XX计划吗?""后天安排了XX吗?"(带具体标题)→ 调 `search-plan-event <日期> --title XX`
- 用户说"查日程""看日程""今天的安排"(无具体标题)→ 调 `list-events <日期>`

**为什么**:
- `list-events` 返回完整字段(id / time_start-end / title / **notes** / category / **feishu_event_id** / last_synced_at / **completion**)
- `query-plans` 是 24h 聚合视图,同小时内的多条事件用 `+` 合并,丢失 notes / 飞书同步状态 / ID
- **从信息论角度,list-events 是上位集合,query-plans 是下位聚合**--默认应给上位

**两个命令的适用边界**:

| 用户场景 | 用哪个 |
|---|---|
| "查日程" / "看日程" / "今天的安排"(**默认**) | `list-events <日期>` |
| "给我看 24h 时间表" / "今天都干啥了" | `query-plans <日期>` |
| 检查 24h 是否有空缺(看 `(未规划)` 标记) | `query-plans <日期>` |
| 多日查询(list-events **不支持**多日) | `query-plans <日期1,日期2,...>` |
| 改某条 / 删某条 / 诊断飞书同步 | `list-events <日期>` |

**`list-events` 输出样例**:
```
📅 2026-07-01 日程列表
  飞书能力: full (CLI 可用 / 已授权 / 可写)
     ID 时段          title           notes                  飞书ID / 同步状态        完成
   544 00:00-09:00 睡眠                                   1743f09d-... / 2026-06-30 17:14:18  -
   564 17:45-18:30 健身          练背+有氧                  - / -                  已完成
   565 19:00-20:00 读书          《人类简史》第3章           - / -                  未完成
   ...
  共活跃 32 条 / 停用 0 条
```

#### 3.1.1 HTML 模式（2026-07-23 新增 · 可视化查询结果）

**触发词**：`查日程 / 看日程`（同 3.1 触发词 → AI 默认走 HTML 版）

**核心语义**：把 `list-events` / `query-plans` 的数据渲染为 HTML，提供摘要卡 + 24h 时间轴 + 事件卡片 + 筛选器 + 24h 缺口高亮。

**调用方式**：
```bash
# 单日 HTML（默认 24h 时间轴 + 卡片网格）
python scripts/schedule_cli.py render-list-events 2026-07-15
# 输出:作息管家/reports/schedule_list_2026-07-15.html

# 多日 HTML（按日聚合视图）
python scripts/schedule_cli.py render-query-plans 2026-07-13,2026-07-14,2026-07-15
# 输出:作息管家/reports/schedule_query_2026-07-13_to_2026-07-15.html

# 自定义输出路径
python scripts/schedule_cli.py render-list-events 2026-07-15 --out reports/my.html
```

**HTML 包含的派生字段**（由 `scripts/schedule_html_render.py` 计算）：
- 首屏摘要卡：活跃 / 已完成 / 未复盘 / 未同步飞书 / 24h 缺口
- 24h 时间轴（list-events 模式）：按小时桶聚合事件
- 事件卡片网格：含飞书同步状态徽章、completion 徽章、completion_note、notes
- 筛选器：按 title/notes/category 搜索；按 已同步/未同步/已软删/已完成/未复盘/跳过 筛选
- 折叠区：已软删事件、飞书侧存在但本地无的事件、错误明细
- 飞书可用度提示：探测 full/partial/missing 自动展示

**实现位置**：
- 模板：`templates/schedule_list_events.html`（静态资产，不修改）
- 渲染器：`scripts/schedule_html_render.py`（数据派生 + JSON 注入）
- CLI 入口：`scripts/schedule_cli.py` 的 `render-list-events` / `render-query-plans` 子命令
- 数据来源：调用现有的 `schedule_db.list_plan_events()` / `_read_plan_dict()` 函数，**不动数据库 schema**

**与原命令的边界**：
| 场景 | 用哪个 |
|---|---|
| 终端查、复制粘贴、AI 引用 | `list-events` / `query-plans`（文本） |
| 浏览器看、截图分享、可视化 | `render-list-events` / `render-query-plans`（HTML） |
| 程序化 JSON 调用 | `list-events` 的 JSON 输出（脚本化） |
| 单事件精确查重（带标题） | `search-plan-event`（轻量，保留 JSON） |

#### 3.1.2 HTML 输出命名规则（2026-07-23 重写 · SKILLS_DB_PATH 硬绑 · 5 模板 5 子目录）

**核心原则**：按 **域 / 模式 / 日期** 三维度分目录，HTML 输出**硬绑 `SKILLS_DB_PATH`**（不传 `--out`），不与文本 CLI 输出混存。

```
$SKILLS_DB_PATH/schedule_html/
├─ record/                                ← 作息记录域(record-*)
│  ├─ day/
│  │  └─ plan_list_2026-07-15.html
│  ├─ range/
│  │  └─ plan_query_2026-07-13_to_2026-07-15.html
│  ├─ compare/
│  │  └─ <labelA>_vs_<labelB>_record_compare.html
│  ├─ category/
│  │  └─ <cat>_<start>_to_<end>_record_category.html
│  └─ anomaly/
│     └─ <today>_w7_record_anomaly.html
└─ plan/                                  ← 日程计划域(plan-*)
   ├─ list/
   │  └─ plan_list_2026-07-15.html
   └─ query/
      └─ plan_query_2026-07-13_to_2026-07-15.html
```

**命名细则**：

| 路径段 | 取值 | 来源 |
|---|---|---|
| `record/` 或 `plan/` | 域 | `record` 对应 `schedule_records`,`plan` 对应 `schedule_plans` |
| `day/` `range/` `compare/` `category/` `anomaly/` | 子目录 | record 域 5 个 mode(子目录) |
| `list/` `query/` | 子目录 | plan 域 2 个 mode(子目录) |
| `plan_list_/plan_query_/record_day_/...` | 文件名前缀 | 与表名对齐(`plan_` for schedule_plans,无前缀 for schedule_records) |
| `YYYY-MM-DD[_to_YYYY-MM-DD]` | 日期段 | 单日 / 区间(`_to_` 分隔) |
| `.html` | 扩展名 | 单文件自包含 + 共享 CSS/JS 引擎自动复制 |

**互斥规则**：
- `record/` 域 → 禁止出现 `plan_list_/plan_query_` 前缀(互斥)
- `plan/list/` 模式 → 禁止出现 `YYYY-MM-DD_to_*` 多日文件名(互斥)
- `record/day/` 模式 → 禁止出现 `YYYY-MM-DD_to_*` 多日文件名(互斥)
- `record/range/` 模式 → 文件名必须含 `_to_`(单日退化为 `start==end` 形式)

**约束**：
- 输出目录**必须已存在**(子目录 day/range/compare/category/anomaly + plan/list/query),**不静默创建**
- 错误文案带字段名 + 当前值 + 期望值 + 修复建议
- 同日期/区间覆盖写(用户主动调就期望刷新)
- 模板按 `meta.mode` 分发,缺 key 报错清晰(MODE_HANDLERS 字典)

**自定义输出路径**：**不支持 `--out` 标志**(commit 5710525 决定)。用户需要把 HTML 落到非默认位置时,自己 `mv` 文件,或在 `SKILLS_DB_PATH` 环境变量里覆盖默认值。

**示例**：
```bash
# 单日 → $SKILLS_DB_PATH/schedule_html/record/day/2026-07-15_record_day.html
python scripts/schedule_cli.py render-record-day 2026-07-15

# 区间 → record/range/2026-07-13_to_2026-07-19_record_range.html
python scripts/schedule_cli.py render-record-range 2026-07-13 2026-07-19

# 对比 → record/compare/2026年6月_vs_2026年7月_record_compare.html
python scripts/schedule_cli.py render-record-compare-months 2026-06 2026-07

# 类别深挖 → record/category/健身_2026-07-01_to_2026-07-31_record_category.html
python scripts/schedule_cli.py render-record-category-range 2026-07-01 2026-07-31 健身

# 异常检测 → record/anomaly/2026-07-23_w7_record_anomaly.html
python scripts/schedule_cli.py render-record-anomaly --window 7
```

> 备注:本节于 2026-07-23 重写,合并原 plan 域命名 + record 域 5 模板 5 子目录。上一版本写到 `作息管家/reports/`(用户已主动删除该目录)。

---

### 4. 商量计划(核心入口)

**触发词**:商量计划 / 一起规划 / 规划明天 / 规划一天 / 规划后天 / 讨论计划

**核心语义**:AI **必须先跟用户多轮对话**细化分钟级细节,**不能直接调 CLI 写库**。

**执行流程**:
1. **确认日期**:问用户"哪一天?"(明天 / 后天 / 具体日期)
2. **拉取已固定事件**(2026-07-13 新增 - 保护其他技能预插的计划):
   - 调 `list-events <日期>`
   - **如无已有事件 → 跳过此步**,直接进入 Step 3
   - 如有事件,原样展示给用户:
     ```
     🔒 7月13日 已有事件(共 4 条):
       10:00-11:30 健身 上午·臂
       15:00-17:00 健身 下午·胸
       20:00-21:30 健身 晚上·肩+腿
       22:00-22:30 健身 居家·腹
     ```
   - **询问保留策略**:「以上事件哪些必须保留不可改?」[全保留 / 选几项保留 / 全部可调整]
     - 用户选"全保留" → 这些时段被锁定
     - 用户选"全部可调整" → 参与后续流程,可被覆盖
   - **锁定规则(关键)**:被保留的事件,其整个 `[time_start, time_end]` 区间不可被新事件占据。
     后续大块节奏围绕这些区间填空隙。AI 在 Step 7 生成 JSON 时,锁定事件的 time_start 不得出现在新事件列表中。写入时 upsert 按 `(date, time_start)` 匹配 → 锁定事件命中 UPDATE(原样保留),新事件 INSERT。
3. **拉取心愿清单**(仅当「备忘录」技能已加载时执行)
   - 调用备忘录技能的"查心愿"唤醒词 → 拉到心愿列表
   - 呈现给用户:
     ```
     📌 你心愿里有:
      1. 减肥(#234,2026-06-01 建)
      2. 读完《X》(#189,2026-05-15 建)
      3. 学 Python(#201,2026-05-22 建)
     ```
    - **询问已完成的**:用户可能某些心愿已经做完了(不是"明天的计划",是"已经完成")
      - 例:「以上有已经完成的吗?完成的帮我删掉 + 触发一次打卡」
      - 用户标 1 条已完成 → AI 调用备忘录的"删心愿"+"记打卡"两个唤醒词
    - **询问本次要推进的**:「本次计划要推进哪几条?」[编号 / 全选 / 跳过]
     - 用户选 0-N 条 → 带入 Step 4
     - **临时新增心愿**(B 阶段新增):
      - 询问:「除了清单里这些,还要临时新增几个心愿吗?」[新增 / 跳过]
      - 用户说"新增 N 个" → 跟用户确认每条心愿内容
      - 每条调备忘录的 **`记心愿`** 唤醒词(不是"新增心愿")→ 拿新 memo_id
      - 加入到"已选清单"统一列表(跟用户挑的 id 平等处理)
      - 第一性:复用备忘录现有唤醒词,不引入"商量加心愿"等新概念
4. **大块节奏**:问"上午/中午/下午/晚上大概做啥?"(4-5 段即可)
   - 若用户从心愿里挑了 N 条 → AI 主动建议:"心愿 X 安排在哪个时段?"
   - **已固定事件时段视为已占用**:跳过这些时段,围绕它们填空
5. **追问细节**:对每段追问具体时间 + 活动名
   - 例:用户说"上午工作"→ AI 问"几点开始?几点结束?做什么?中途休息吗?"
   - 例:用户说"中午吃饭"→ AI 问"几点?在家做饭还是外面吃?"
6. **覆盖校验**:合并已固定事件 + 新规划事件,确认覆盖 00:00~24:00(首段 00:00 起,末段 24:00 止,相邻事件 time_end = 下一条 time_start)
7. **AI 整理为结构化 JSON 数组**,每条含:
   ```json
   {"time_start":"HH:MM","time_end":"HH:MM","title":"事件名","notes":"细节","category":"分类"}
   ```
   分类参考:分类清单.md
8. **展示给用户确认**:"我整理了 N 条事件(含 M 条已固定),请确认/调整"
9. **写入 DB**:
   ```bash
   # 推荐:从文件读(AI 写 plan.json 后调)
   python3 scripts/schedule_cli.py upsert-plan-events <日期> --json @plan.json
   # 或 stdin
   cat plan.json | python3 scripts/schedule_cli.py upsert-plan-events <日期> --json -
   ```
10. **飞书询问**:CLI 自动检测本机 lark-cli:
    - **已安装 + 已授权** → 询问"是否同步飞书日历?[Y/n]"
    - **未安装 / 未授权** → 跳过,告知用户"装了飞书后能解锁:1 计划同步 2 拆分钟级事件 3 双向 CRUD"
11. 用户同意飞书同步 → 飞书侧 create/update/delete 自动跑(diff_and_sync 算法),feishu_event_id 回写 schedule_plans
12. **心愿排期联动**(B 阶段新增):
    - 收集"已选清单"所有心愿 id(用户挑的 + 临时新增的)
    - 调备忘录技能的 **`心愿排期`** 唤醒词
    - 命令:`memo_cli.py set-due <id1> <id2> ... --due <YYYY-MM-DD>`(YYYY-MM-DD = 步骤 1 确认的日期)
    - 飞书侧:被选中的心愿 task 自动 due = 那天,飞书日历"待办"区可见
    - **第一性**:作息 = "什么时候做什么"(飞书日历事件 time_start/end),备忘录 = "哪天做这个心愿"(飞书 task due),两个独立维度
    - **跳过条件**:用户没挑任何心愿("已选清单"为空)→ 跳过此步

**硬约束**:
- 联合区间必须 ⊇ [00:00, 23:59](首段 time_start == "00:00",末段 time_end == "23:59",相邻衔接无重叠无空隙)
- **time_end 禁止使用 24:00**:飞书 ISO 8601 不接受 24:00(会转次日 00:00),写入时 DB 端自动规范化 `24:00 → 23:59`(见 `normalize_time()`)
- 历史数据已批量回填 24:00 → 23:59(一次性脚本 `backfill_24h_to_23h59.py`)

**失败处理**:
- 24h 覆盖校验失败 → 提示具体哪条不连续/越界 → 重新生成
- 飞书同步失败 → DB 写入不回滚 → 飞书侧 list-events 可看到没同步的项
- **B 阶段新增失败处理**:
  - 临时新增心愿失败(记心愿返回 error) → 跳过该条,告知用户,建议手动加
  - 心愿排期失败(备忘录 set-due 返回 error) → DB 写入已成功,飞书侧 due 可能没同步;提示用户跑 `备忘录同步` 或 `心愿排期` 重试

---

### 5. 改计划

**触发词**:改计划 / 修改一个日程 / 改这个

**执行流程**:
1. **定位事件**:先调 `list-events <日期>` 或 `query-plans <日期>` 列出当日事件 + ID
2. **问用户改哪条** + 改什么字段(title / notes / category / time_start / time_end / completion / completion_note)
3. **DB 写入**:
   ```bash
   python3 scripts/schedule_cli.py update-event <id> [--title X] [--notes Y] [--category Z] [--time-start HH:MM] [--time-end HH:MM] [--completion 已完成] [--completion-note "拖延了1h"]
   ```
4. **飞书同步判断**(关键):
   - 若该事件**未绑飞书**(`feishu_event_id` 为 NULL)→ 询问"要同步创建飞书事件吗?"
   - 若该事件**已绑飞书** → 询问"飞书那边也要改吗?"
5. **改时段的特殊处理**:time_start / time_end 改了 → 飞书日历"无改时间按钮" → 拆为**删旧 event_id + 建新 event_id**,**回写新 feishu_event_id** 到 schedule_plans

**约束**:
- 单次只能改一个事件(要改多个 → 多次 update-event)
- 改时段 = 飞书必删旧建新(不是 update),CLI 自动处理
- completion 字段也可通过"改计划"单独修改,但批量的复盘流程请用"**复盘**"

---

### 6. 删计划

**触发词**:删计划 / 不要这条了 / 这条不要

**执行流程**:
1. **定位事件**:先 `list-events <日期>` 让用户确认要删哪条
2. **DB 软删**(is_active=0,不物理删除):
   ```bash
   python3 scripts/schedule_cli.py deactivate-event <id>
   ```
3. **飞书询问**:若该事件已绑飞书 event_id → 询问"飞书那边也删吗?",yes → 调 `feishu_delete_event` 并清空本地 feishu_event_id
4. **恢复**:操作规范禁止 DELETE。如需恢复,手动 `UPDATE schedule_plans SET is_active=1`

**约束**:
- 软删不在 list-events 默认查询结果里(要查 include_inactive=True)
- list-events 显示 ✗ 前缀的项

---

### 7. (已合并到 3.1 查询日程)

> 原"看计划"小节已合并到 `3.1 查询日程`,触发词"看日程 / 列出今日日程 / 看一天的安排"统一指向 `list-events`。

---

### 8. 日程管家同步

**触发词**:日程管家同步

**执行流程**:
1. **能力探测**:调 `is_feishu_available()`(缓存 5 分钟)
   - 不全可用 → 报错退出,告诉用户安装/授权方法
2. **Phase 0:反向对账**(2026-07-03 新增)
   - 拉飞书当日 events(用 `+search-event --query "作息管家自动同步"`)
   - 对 DB 端 `feishu_event_id` 为空的事件做严格匹配:`time_start + time_end + title` 三项精确匹配
   - **跨日边界规则**:飞书 end_time "次日 00:00" 等价于 DB "23:59"
   - 找到唯一匹配 → 询问是否回填 `feishu_event_id`(默认 Y)→ 写回
   - 找不到 / 多候选 → 跳过(标 ⚠️)
3. **拉两侧数据**:
   - DB 端:当日活跃 events(对账后可能新增了 ID)
   - 飞书端:`+search-event --start <日期> --end <日期> --query "作息管家自动同步"`
4. **diff**:按 (time_start, time_end) 配对
   - DB 有 + 飞书无 → create
   - DB 有 + 飞书有 + title/description 变了 → update
   - DB 无 + 飞书有 → delete
5. **逐个询问**(决策 C):每条 create/update/delete 单独 [Y/n]
6. **执行 + 回写**:yes → 调对应飞书 API,feishu_event_id + last_synced_at 回写

**触发场景**:
- 之前跳过同步想补
- 飞书手改了想重新对齐
- 同步失败后重试
- DB 端 feishu_event_id 缺失需要回填(Phase 0 自动处理)

```bash
python3 scripts/schedule_cli.py feishu-resync <日期>
```

---

### 9. 飞书探测

**触发词**:飞书探测 / 飞书能力探测 / 检查飞书

**执行流程**:
```bash
python3 scripts/feishu_sync.py  # self-check 模式
```

**三档探测**:
1. **lark-cli 安装**:PATH 查找 + 候选路径回退
2. **已认证**:`lark-cli auth status` 看 user/bot 至少一个 status=ready
3. **日历可写**:`+agenda` 拉到今日议程视为至少有读权限

**返回**:`FeishuStatus` 对象,含 `cli_installed / authenticated / calendar_writable / tier`(full/partial/missing)

**体验**:
- `full` → 询问"是否同步飞书?"
- `partial` → 跳过,提示"lark-cli auth login"
- `missing` → 跳过,提示安装价值(**不主动帮装**,给一行 `npm i -g lark-cli` 用户自决)

---

### 10. 补计划与程序化接口(2026-07-12 新增)

#### 补计划(用户侧唤醒词)

**触发词**:补计划 / 加一条计划

**语义**:单条追加计划事件,不触动其他已有事件。与 `商量计划` 的边界:

| | 补计划 | 商量计划 |
|---|---|---|
| 范围 | 单条增量 | 完整 24h 规划 |
| 流程 | 直接写入 | 多轮讨论 → 心愿拉取 → 大块节奏 → 24h 校验 |
| 触发的接口 | `ensure-plan-event` | `upsert-plan-events` |
| 对已有事件 | 不动 | 覆盖(不匹配即软删) |

用户说"帮我补一条健身计划到后天"、AI 直接调 `ensure-plan-event`,不进入商量计划的多轮流程。

#### 程序化接口(其他技能调用)

`ensure-plan-event` 和 `search-plan-event` 底层是 JSON 输入输出的 CLI 接口,供其他技能程序化调用:

```bash
# 其他技能 AI 直接调,不走唤醒词路由
python scripts/schedule_cli.py ensure-plan-event <日期> \
  --time-start HH:MM --time-end HH:MM --title <标题> [--notes X] [--category Y]
```

#### 轻量查询

```bash
python scripts/schedule_cli.py search-plan-event <日期> --title <标题>
# 2026-07-15 新增:可选按 (date+time) 精确查重(title 不参与)
python scripts/schedule_cli.py search-plan-event <日期> --time-start HH:MM --time-end HH:MM
# 标题+时间 一起传 → 三元组查重
```

返回:
```json
{"found": true, "id": 562, "time_start": "17:00", "time_end": "18:00", "title": "健身", ...}
{"found": false, "date": "2026-07-12", "title": "健身"}
```

- 只查 `is_active=1` 的活跃事件
- **2026-07-15 升级**:精确匹配 title(兼容路径);同时支持可选的 time_start/time_end 参数触发三元组查重
- 匹配到多条时返回第一条
- 此接口也由"查日程"上下文路由自动触发(用户说"今天有XX计划吗?")

#### 幂等性语义(2026-07-15 升级 · 修复"按 (date+time) 查重"bug)

**第一性原理**:身份 = `(date, time_start, time_end)`,title 是展示标签(不是身份)。

**查重维度优先级**:

| 调用方式 | 查重维度 | title 参与? |
|---|---|---|
| `ensure-plan-event` 传 time_start + time_end | `(date, time_start, time_end)` 三元组 | ❌ 否 |
| `search-plan-event` 传 time_start + time_end | `(date, time_start, time_end)` 三元组 | ❌ 否 |
| `search-plan-event` 只传 title(旧路径) | `(date, title)` 二元组 | ✅ 是 |

**title 语义规则**:
- 同 `(date, time_start, time_end)` + 不同 `title` → **视为同一条**(返回 found,不建新)
- 同 `date` + 不同 `time` + 同 `title` → 视为不同事件(新建)
- `title` 是给人看的"标签",不影响"是不是同一条计划"

**飞书侧查重**(`_sync_one_feishu` 内部):
- 飞书 API 不支持 time 过滤 → 先按 `title` 拉候选 → 再按 `time_start + time_end` 精确比对
- 命中 (date+time+title) → 回写现有 `event_id`(飞书侧幂等,不重创建)
- 未命中 → `create_event` 新建 + 回写 `event_id`

**修复前 vs 修复后**:
- **修复前 bug**(2026-07-15 修):`ensure-plan-event(date, 10:00, 11:30, "健身 上午·臂")` 调一次 + `ensure-plan-event(date, 10:00, 11:30, "健身·上午·臂 10:00")` 调一次 → DB 出现 2 条 7/15 10:00-11:30 计划(不幂等)
- **修复后**:同样的 2 次调用 → DB 仍是 1 条(幂等)

**为什么这个修复必要**:
- 网络抖动重试是常态--不幂等会导致数据重复
- AI 可能因为上下文混乱或自查而重复发同一命令
- 跨技能联动时(卡路里/备忘录→作息),多源调用需要幂等保护

---

### 11. 复盘(2026-07-12 新增 · 2026-07-13 升级 · 打卡联动版)

**触发词**:复盘 / 回顾今天 / 今天做得怎么样 / 复盘一下

**定位**:对标 `商量计划` 的流程级操作。商量 = 事前规划,复盘 = 事后回顾。completion 字段是复盘的**产出**,不是独立操作。

**前置 · 状态机快判**(2026-07-13 新增 · 在执行流程前先判):

1. 调 `list-events <日期>` 拉取当日活跃事件
2. **IF 活跃事件数 == 0**:
   → 提示"X 月 X 日没有计划,无法复盘",退出流程
3. **IF 所有事件 `completion IS NOT NULL`**:
   → 告知"今天的计划已全部复盘过,我们直接进入讨论" → **跳过 Step 0-5,直接进 Step 6 复盘讨论模式**
4. 否则按下面的执行流程走

**Step 0:提示同步**(2026-07-13 新增 · 仅当有未复盘事件时走):

进复盘前,AI 第一句话:

> 进复盘之前先对一下今天的打卡数据。
> 请确认:你今天有没有执行过 "/备忘录 备忘录同步"?

**用户回复分支**:

- "已同步" / "OK 了" / "好了" → 默认已同步,进 Step 1
- "没同步" / "忘了" → 引导执行 `/备忘录 备忘录同步`,等用户说"好了"再进 Step 1
- "不连飞书" / "没装" → 跳过,告知"只用本地打卡记录,可能不全",直接进 Step 1
- 任意步骤用户说"算了" / "不做了" / "等会再说" / "先到这" → 退出流程(已复盘过的保留,未复盘的留 NULL)

**降级路径**(备忘录技能不可用时):

- AI 探测不到 `memo_cli.py` → 跳过 Step 0 + Step 2 的打卡拉取,直接走原版 Step 1-6
- 告知用户"备忘录技能不可用,本次复盘不读打卡,只走用户自报"

**执行流程**:

1. **确认日期**:问用户"复盘哪天?"(默认今天,也支持昨天/指定日期)
2. **拉取计划 + 拉取打卡**(2026-07-13 升级):
   - 调 `list-events <日期>` 拉当日活跃事件
   - 调 `memo_cli.py search-date <今日> <今日> -c 打卡` 拉今日打卡(仅 Step 0 通过后)
   - 拿到 JSON 后,AI 提取字段:`content`(主关键词来源)/ `created_at`(辅助)/ `sub_category`(过滤用,见 Step 3)
   - **不向用户展示打卡原文**(留到 Step 3 配对展示)
3. **逐条回顾 + 打卡匹配预填**(2026-07-13 升级):
   - 对 completion 为 NULL 的事件,逐条问用户:
     ```
     📋 17:00-18:00 健身
       参考打卡:
         ✓ 晚上健身房健身60分钟(20:46)
         ✓ 晚上健腹轮15分钟(20:46)
       这条完成得怎么样?
         1. 已完成    2. 已完成(超时)  3. 部分完成
         4. 未完成    5. 未完成(不可抗力)  6. 跳过
     ```
   - **AI 匹配分级**(基于 title + notes 与打卡 content 的语义相似度):
     - ★★★ 强匹配(>0.7)→ 建议"已完成",等用户确认
     - ★★ 弱匹配(0.4-0.7)→ 展示打卡,询问"是不是做了?"
     - ★ 不确定(0.2-0.4)→ 不展示打卡,直接问用户
     - 0 无匹配 → 询问"是没做,还是做了但忘了打卡?"
   - **打卡过滤规则**(避免情绪/状态打卡乱入):
     - IF `sub_category` 是"家务/厨房/学习/工作/健身/阅读"等明确活动分类 → 入选
     - IF `sub_category` 是 None → 用关键词兜底:动词 + 对象 + 时长 模式才入选
     - IF `sub_category` 是"情绪/心情"等 → **不参与匹配**,留到 Step 6 讨论时引用
4. **追问原因**:选了 2/3/4/5 时追问 "为什么?"(→ 写入 `completion_note`)
5. **写入**:逐条调 `update-event <id> --completion X --completion-note Y`
6. **复盘小结 + 关联打卡统计**(2026-07-13 升级):全部过完后,汇总输出:
   ```
   📊 2026-07-12 复盘
     已完成 12 条  |  已完成(超时)2 条  |  部分完成 1 条
     未完成 3 条  |  未完成(不可抗力)1 条  |  未复盘 0 条
     关联打卡:今日 8 条(5 条匹配到计划 / 3 条未匹配)
   ```
   - 关联打卡统计(新增):今日打卡总数 / 匹配到计划的数量 / 未匹配数量
   - 未匹配打卡:留作"明天可以挑几条进计划"的输入

**completion 值清单**:

| 值 | 含义 | 怎么选 |
|---|---|---|
| `已完成` | 按时完成 | 用户说"做了""完成了" |
| `已完成(超时)` | 做了但拖延了 | 用户说"做了但晚了" |
| `部分完成` | 做了一部分 | 用户说"做了一半" |
| `未完成` | 没做,原因在己 | 用户说"没做,懒了" |
| `未完成(不可抗力)` | 没做,外部原因 | 用户说"临时加班""下雨" |

**与改计划的关系**:复盘本质上是批量调 `update-event --completion`。如果用户只改一条的完成状态,也可以直接走"改计划"。复盘的价值在于**逐条过、不遗漏、出小结**。

**找不到匹配计划时**:提示"XX这条计划在系统里不存在,要先补吗?"→ 用户确认后调 `补计划`,再走复盘流程。

---

## references/ 目录

| 文件 | 内容 |
|------|------|
| `操作规范.md` | 禁止直连DB、禁止DELETE、全字段校验 |
| `同步流程.md` | 滑动窗口规则、逐条处理、原文写入 |
| `数据库结构.md` | 三表结构、字段说明 |
| `接口清单.md` | 所有接口参数和调用方式 |
| `分类清单.md` | 建议分类列表(AI自由判定) |
| `CLI命令.md` | 所有CLI命令用法 |
| `Cron任务.md` | 定时任务详细设计 |

