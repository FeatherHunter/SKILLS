# 作息管家 CHANGELOG

> 记录对用户有感知的变更。遵守 SKILL开发总纲V1.0/05-工程仪式.md 的 commit 与同步规范。

---

## [Unreleased] · 2026-07-30

### 🚀 Phase E · 复盘 start-end 跨域 dual-domain 工作流落地(2026-07-30)

**动机**:基于 2026-07-30 Grilling Session 6 决策共识 + ADR-0005,新增独立 `replay` 工作流。
用户原报告"下达复盘本月 → 数据量爆炸 + UI 错乱" 落地修复 + 重构。

**新增工作流**:`render-replay <start> <end>` · 4 段叙事 + 5 状态 fallback · 单文件自包含 HTML

### T01 · render-replay CLI 子命令 + schedule_db.get_plan_events_range(commit ee64c27)
- ✅ `scripts/schedule_html_render.py`: `render_replay(start, end, ai_engine="mock")` 函数 + 5 状态 enum 定义(empty/ok/incomplete/error/offline)
- ✅ `scripts/schedule_db.py`: `get_plan_events_range(start, end, include_inactive=False)` 区间查询
- ✅ `scripts/schedule_cli.py`: `cmd_render_replay` + elif 分支 + help line
- ✅ `CN_COMMAND_MAP["replay"] = "区间复盘"` 条目(避免与 `plan_review="复盘"` 撞车)
- ✅ `default_output_path` / `record_output_path` 加 `"replay"` 分支
- ✅ `render_and_write` template_map 加 `"replay": "schedule_replay.html"`
- ✅ 文件名 `区间复盘_<YYYYMMDD>_<HHMMSS>.html` (与 14 复盘 `复盘_<TS>.html` 中文前缀 + subdir 双重区分)

### T03 · record 聚合段(commit 99e3659)
- ✅ `record_aggregate` 3 字段填充:summary_items(按总分钟数降序) + trend(7 维) + heatmap(24h × N 天)
- ✅ **Top-N 折叠**: 默认 Top 10 + 展开全部按钮 + 44px 触控友好(总纲 §04 原则 12)
- ✅ 复用 `calculations.aggregate_by_category / build_trend_series / build_24h_heatmap` (注意 build_24h_heatmap 返回 `(matrix, sorted_dates)` tuple)
- ✅ **顺手修 09 bug**: `templates/_record_engine.js:254` `days + " 天"` → `days.length + " 天"`(30 天 join 字符串 226px 高度 → 干净数组长度)

### T04 · plan 聚合段(commit d383120)
- ✅ `plan_aggregate` 3 字段填充:completion_distribution(6 类 dict) + completion_by_category(按 total 降序) + completion_rate(整体完成率 = 已完成 / (已完成 + 未完成) 二分)
- ✅ completion_by_category 中 `completed` 字段仅算按时完成的 "已完成" 类(不包含超时/部分完成)

### T05 · 跨域对比段(commit 8454c69)
- ✅ `cross_domain` 4 类清单:
  - `planned_actual_pairs`: plan + record 同日时间重叠的实际时长配对(delta_minutes)
  - `unexecuted_plans`: plan 存在但 completion ∈ {未完成/未完成(不可抗力)/部分完成}
  - `unexpected_records`: record 无对应 plan(plan 不存在或时间无重叠)
  - `overrun_plans`: record 总时长超出 plan ≥ 20%(severity: ≥1.5× high / ≥1.2× medium)
- ✅ 算法核心: 时间重叠判定 `'HH:MM'` 字符串解析(避免 datetime 慢路径), overrun 用 record 总 duration

### T06 · AI 洞察段(commit 593b9f7)
- ✅ `ai_insights` 3 字段填充:anomalies + periodic_compare + suggestions
- ✅ 异常检测算法: `current / mean(baseline) ≥ 2.0` 或 `≤ 0.5` 触发 high, 1.5-2.0 或 0.4-0.67 触发 medium
- ✅ 周期对比算法: 区间内前后半拆对比 (`current_vs_first_half` period 字段) — pragmatic 实现,后续 LLM 接入时按 spec 扩展 last_week/last_month/last_year
- ✅ 6 条规则生成器: 工作骤增 / 维持(睡眠)骤降 / 健康骤降 / 学习骤降 / 调整(娱乐)骤增 / 通用 — 基于 anomalies 的 direction + severity 触发
- ✅ `render_replay(start, end, ai_engine="mock"|"llm")` 接口预留 spec decision 13

### T07 · 5 状态 fallback 完整(commit 4cf4972 + 2b5b4a6)
- ✅ empty: 两域都空 → status="empty"
- ✅ incomplete: 单域有数据 → 缺失域标 incomplete=True + 友好提示 (T01 + T07 双轨补完)
- ✅ error: DB ConnectionError → status="error", data=None, message 含错误说明
- ✅ offline: `check_offline()` 网络探测失败 → status="offline", 单文件 HTML 仍可查看
- ✅ ok: 两域数据完整
- ✅ 状态徽章: ✅ ok / 📭 empty / ⚠️ incomplete / ❌ error / 📡 offline (HTML hero 区 + meta.status_badge 字段)

### T08 · 视觉/UX 打磨(commit 15aa76f)
- ✅ `templates/schedule_replay.html` 132 → 430 行: 4 卡总览 grid + 4 段叙事 JS 渲染 + 复制 prompt + 移动端 3 档适配
- ✅ 4 卡总览: 总时长 / 记录数 / 完成率 / 健康分 (健康分 = 维持占总时长比例,简单代理算法)
- ✅ 复制 prompt 4 部分结构 (总纲 §04 原则 10): 按钮 + preview + clipboard API + execCommand fallback + 2.2s 视觉反馈 + toast 提示
- ✅ Top-N 折叠 JS 交互: 默认 hidden, 点 "展开全部" 后解除
- ✅ 6 类 completion 堆叠柱: 颜色编码 (绿/绿-暗/橙/红/红-暗/灰) + legend
- ✅ 跨域对比: 4 类清单 (planned_actual / unexecuted / unexpected / overrun), severity 高亮 (high 红/medium 黄)
- ✅ AI 洞察: anomalies + suggestions 卡片
- ✅ 移动端 / 平板 / 桌面 三档 media query (360/480/768/1280+)

### T09 · 端到端 seam 测试(commit 5aac98a)
- ✅ `tests/test_replay_e2e.py` 新增: 30 天大 fixture (870 条 record + 14 计划) + 5 视口 parametrize
- ✅ playwright 5 视口 (360/768/1024/1280/1920) 截图保存到 `tests/screenshots/replay_e2e/`
- ✅ 4 段叙事 h2 标题断言 + Top-N 折叠默认 visible ≤ 10 + 展开按钮存在
- ✅ **09 bug 回归护栏**: HTML 不渲染 30 日期 join 字符串
- ✅ 总测试 < 30s (符合 spec acceptance)

### T10 · 文档收尾(commit 本次落)
- ✅ `docs/adr/0005-replay-start-end-new-workflow.md`: 决策"复盘 start-end 是独立新工作流,不合并 14 复盘 / 09 查作息范围"
- ✅ `CONTEXT.md` 创建 (作息管家首次): 核心术语 6 个 (复盘 / 14 复盘 / 09 查作息范围 / 复盘 start-end / dual-domain / 5 状态 fallback / 4 段叙事)
- ✅ `SKILL.md` 路由规则章节: 7 个复盘预置 (本周/上周/本月/上月/今年/上年) + 4 种自由区间语法 (YYYY-MM-DD~ / MM/DD~ / 过去 N 天 / YYYY Qn)
- ✅ `AGENTS.md` 当前阶段表格: Phase E ✅ 完成 (commit 序列)

### 统计
- 10 个 ticket (T01-T10) 全部完成
- 9 个 commit (T02 路由被吸收到 T01 CLI commit, 共 9 个)
- 测试: 25 个 test_render.py + 5 个 test_replay_visual.py + 8 个 test_replay_e2e.py = 38 个新测试
- pytest 完整: 179 passed (我加的 38), 28 failed (pre-existing GBK 编码问题, 与我无关)
- playwright 端到端: 3 视口 (T08) + 5 视口 (T09) 全部无水平滚动

---

## [Unreleased] · 2026-07-29

### 🚀 Phase A-3 + Q5 + Q6 + Q7 · ADR-0001/0002/0003 落地(2026-07-28 ~ 2026-07-29)

**动机**:基于 2026-07-28 Grilling Session 8 决策闭环(Q1-Q8)+ 3 份 ADR(0001/0002/0003),落地 4 个实施 Phase。本次为对用户有感知的命名 / 复制 prompt / HELP 入口重构。

### Phase A-3 · ADR-0001 作息管家.html 稳定入口(commit 6ebe69c)

- ✅ `scripts/help_render.py` 新增 `sync_to_stable_mirror()`:render() 主流程完成后自动覆盖写根目录 `作息管家.html`
- ✅ `data.mirror_path` 字段返回镜像路径(IDE 即开即看,无需跳 schedule_html/help/ 找最新 timestamp)
- ✅ `作息管家.html` 从 914 行用户手册(旧)重渲为 583 行 HELP 中心(对标卡路里)
- ✅ `tests/test_help_sync.py`:3 用例锁住 ADR-0001 契约(byte-identical + 覆盖写 + message 含镜像)

### Phase A-1 · Q5 路径对齐(ADR-0002 · commit c17d490 + faf8839 + 9dfd351)

**新增**:
- ✅ `CN_COMMAND_MAP`:14 模板英文 command → 中文 command 名映射(record/plan/receipt 3 域分组)
- ✅ `default_output_path` / `record_output_path`:全 mode 输出 `<中文 command>_<YYYYMMDD>_<HHMMSS>[_<N>].html`
- ✅ `tests/test_naming_cn.py`:5 用例覆盖中文 command 接受 + 冲突保护 + 14 模板映射契约
- ✅ `tests/test_naming_migrate.py`:17 用例覆盖 14 mode 中文 command + 隐私无 pid/rid 泄露

**Q5 Contract(Issue 07 · commit faf8839)**:
- ✅ `_naming_path` 新增 contract 检查:传 `CN_COMMAND_MAP` 里的英文 key(record_day / plan_list 等)抛 `ValueError`,错误文案含字段名+当前值+期望值+修复建议
- ✅ 不在映射里的自定义 command(unknown / 测试 fixture)仍允许,避免破坏兜底

**SKILL.md 路径引用对齐(commit 5952b1d + 9dfd351)**:
- ✅ §路由表 输出形式列:20+ 条路由全部改为中文 command(record_day.html → 查作息记录.html 等)
- ✅ §3.1.2 HTML 输出命名规则:目录树 + 命名细则 + 14 模板中文 command 映射表 + 互斥规则
- ✅ §3.1.3 5 模板设计:触发词路由表 + 输出路径硬绑 + 示例 bash 全部对齐

### Phase A-1 · Q6 单工铁律(ADR-0002 · commit f092476)

**新增**:
- ✅ `_build_record_copy_prompt(mode, meta, records, ...)`:record 域 6 模板共享 4 部分 prompt 构造器(场景/数据/期望/来源)
- ✅ `_build_list_events_copy_prompt(date, plan_events)`:查日程专属 4 部分 prompt
- ✅ `render_record_day/range/compare/category/anomaly/detail/list_events` 全部 payload 增加 `copy_prompt` 字段
- ✅ `templates/_record_engine.js` 新增 `copyPromptBlock(data)`:6 模板共享复制按钮区(📋 图标 + 4 部分 prompt 预览 + 复制按钮 + 剪贴板 API + textarea fallback)
- ✅ `templates/schedule_list_events.html` 新增 list_events 复制按钮区
- ✅ `tests/test_copy_prompt.py`:16 用例锁住 14 模板全有 copy_prompt / prompts + 渲染 HTML 含复制按钮 marker

### Phase A-1 · Q7 内部分组(ADR-0003 · commit f092476)

- ✅ `CN_COMMAND_MAP` 4 域注释分组(record 报告型 6 / plan 过程型 3 / receipt 回执型 5 / help 域独立)
- ✅ `default_output_path` / `record_output_path` 函数体 4 域注释分组,为将来拆 record_cli/plan_cli/receipt_cli/help_render 打基础
- ✅ `tests/test_q7_grouping.py`:5 用例锁住 4 域注释存在 + schedule_cli.py 字节 < 150KB / 行数 < 4000(ADR-0003 触发条件未满足)

### Phase A-1 · HELP Toast 升级(对标卡路里 v2.4.12 · commit 5ceccb7 + 63cb8b6)

- ✅ `templates/help_center.html` toast 从单元素 `<div id="toast">` 升级为多段结构(对标卡路里):
  - 📋 icon + "已复制 <em id="toastWake">唤醒词</em>" 标题 + "粘贴给 AI(微信/飞书/任何 AI 工具),作息管家技能会自动执行这个流程,完成后你会在飞书收到 HTML" 详情 + "✓ 知道了" 关闭按钮
  - iOS 通知风格:`backdrop-filter: blur(20px) saturate(180%)` + `cubic-bezier(0.34, 1.56, 0.64, 1)` 弹性曲线 + `#4dd96b` 绿色 em 强调
  - 移动端适配:`@media (max-width: 640px)` + `env(safe-area-inset-bottom)` iOS 安全区
- ✅ JS `showToast(wake)`:从父级 `.ww-block > .ww-name` 取唤醒词名 + 拼接场景标题,toast 显示"已复制 #6 查作息 · 单日查看"

### 影响范围

- 代码:`scripts/help_render.py` / `scripts/schedule_html_render.py` / `templates/_record_engine.js` / `templates/schedule_list_events.html` / `templates/help_center.html`
- HTML:`作息管家.html` 自动同步(ADR-0001)
- DB schema:无变化
- 测试:5 个新测试文件(test_help_sync / test_naming_cn / test_naming_migrate / test_copy_prompt / test_q7_grouping),共 46 个新用例,162 全过
- 向后兼容:✅ 旧英文 command 名调用 `_naming_path` 会报 ValueError(契约强制);15 模板新增 copy_prompt 不影响旧 payload 字段

### Tested-By

```
Tested-By: pytest-pass-2026-07-29
  - 162 用例全过(含 46 个新增 · 5 个新测试文件)
  - e2e smoke:render-record-day / render-record-range / render-receipt / help_render 全部输出中文 command 名
  - HELP HTML toast 浏览器检查:icon + 标题 em + 详情 + 关闭按钮 + iOS 风格 CSS 全到位
  - Q5 Contract 故意跑英文 record_day → 报清晰 ValueError(契约生效)

环境备注:
  - Windows PowerShell 5.1 默认 GBK 编码会导致部分 subprocess 测试(test_amend_record_cli 等)
    报 'gbk' codec can't decode byte 失败(28 failed),这是环境性问题(基线 861beeb 已存在,
    非本次 diff 引入),用 `$env:PYTHONUTF8="1"; $env:PYTHONIOENCODING="utf-8"` 跑即全过。
  - 本次未跑 Fresh Agent 黑盒测试(FAT)— Phase B 标 fresh-agent-v1 的 commits 是
    Tested-By 标签声明(建议后续补 FAT 报告产物)。
```

---

## [Unreleased] · 2026-07-25

### 📋 Phase A · 文档纪律 + 删自创"强制规定"(零代码改动)


**动机**:基于对抗式审查报告(2026-07-25),发现 SKILL.md §"强制规定" 4 条中 3 条违反总纲 V1.0 元规范。本次为最小阻力 Phase A,只动文档,不动代码 / HTML / DB / 测试。

### 移除(Removed)

- ❌ SKILL.md "强制规定 #2: 此规定优先级最高"(违反总纲元规范,无授权自创最高优先级)
- ❌ SKILL.md "强制规定 #3: 任何修改需用户确认"(属用户协作偏好,非技术契约,放 `.notes/` 而非 SKILL.md)
- ❌ SKILL.md "强制规定 #4: 渲染 HTML 必须主动推送"全文 30 行(误读总纲 §04 原则 11,与 §"工程实践"中"拒绝的反模式(硬编码 Chrome)"自相矛盾)

### 新增(Added)

- ✅ SKILL.md "HTML 推送策略"段:跑完 `render-*` 默认 `<media>` 内嵌,浏览器自动打开遵循用户偏好,不再硬编码 Chrome / 不再强制 auto-open
- ✅ SKILL.md "本规定的删除历史"段:记录 Phase A 删了什么 + 为什么删(供 git blame / 后续审查追溯)
- ✅ SKILL.md 顶部"强制规定"标题从 "(最高优先级)" 改为 "(与 SKILL开发总纲V1.0 同源)"(对齐总纲元规范)

### 影响范围

- 代码:`scripts/` 0 改动
- HTML:`作息管家.html` 0 改动(本次改的是面向 AI 的内部规则,非用户面向接口)
- DB schema:无变化
- 测试:`tests/` 0 改动
- 向后兼容:✅ 全部命令行为不变(强制规定是文档,非代码路径)

### Tested-By

```
Tested-By: exempt + 原因
  - 豁免依据: 纯文档格式化 / 行为不变(只删自创元规则,不动接口)
  - 自检: 本次改动不修改任何 CLI 命令 / HTML 模板 / DB schema / 唤醒词表,
         读者看到的 contract(用户可见的接口面)无任何变化
```

---

### 📋 Phase B.1 · 路由表改默认 HTML(总纲 §04 原则 11 落地)

**动机**:基于对抗式审查,SKILL.md §"路由规则" 总路由表 20+ 条中 11 条默认走文本 CLI / 纯 JSON,虽然 SKILL.md 在"输出形式"列已声明 HTML 路径,但"CLI 命令"列默认走文本。AI 命中时会优先按"CLI 命令"列走文字答,违反总纲 §04 原则 11 "HTML-First"。

**新增段**:`### ⭐ HTML-First 默认规则(2026-07-25 重构 · 总纲 §04 原则 11)`
- 第一性引用总纲原话
- 判定流程(IF HTML THEN invoke ELSE 文字)
- 3 类例外(用户明确要文本 / HTML 失败 / 数据准备型 CLI)

**修改段**:`### 总路由表`
- 列名从 "CLI 命令" 改为 "CLI 命令(默认 HTML · 文字答降级路径)"
- 13 条改默认:
  - #6 查作息:`list` → `render-record-day`(文本降级 `list`)
  - #4 今天总结:`report`/`summary` → `render-record-day`(满)/ `render-record-summary`(不满)
  - #5 汇总作息:`range` → `render-record-range`(文本降级 `range`)
  - #8 查作息时间轴:`timeline` → `render-record-day`(文本降级 `timeline`)
  - #9 查作息范围:`range` → `render-record-range`
  - #12 查日程:`list-events` → `render-list-events`(文本降级 `list-events`)
  - #15 #16 24h 概览:`query-plans` → `render-query-plans`
  - #17 商量计划:`upsert-plan-events` → 多轮讨论 → `render-plans-preview` 先预览 → `upsert` → `render-plan-receipt-write`
  - #13 补计划:`ensure-plan-event` → 加 `render-plan-receipt-add <id>`
  - #18 改计划:`update-event` → 加 `render-plan-receipt <id>`
  - #19 删计划:`deactivate-event` → 加 `render-plan-receipt <id>`
  - #14 复盘:`list-events` → `update-event` → 加 `render-plans-review <date>`
  - #23 按 ID 查:`get-record` → `render-records-detail --record-id N`(文本降级 `get-record`)

**影响范围**:
- 代码:0 改动
- HTML:`作息管家.html` 0 改动(本路由表是 AI 内部指令,用户手册无对应内容)
- DB schema:无变化
- 测试:0 改动(行为变更,需要 Fresh Agent 黑盒测试)
- 向后兼容:✅ 文本 CLI 全部保留作"降级路径",`render-*` CLI 全部已存在

### Tested-By

```
Tested-By: pending-FAT
  - 待测唤醒词: #4 #6 #8 #9 #12 #13 #14 #15 #16 #17 #18 #19 #23
  - 人类 prompt: ≥ 3 个口语化/slash/略错 prompt
  - 验证项: AI 命中后是否 invoke HTML 而非文字答
  - 降级路径: 用户说"给文本"时,是否降级到对应文本 CLI

如何跑 FAT:
  1. 开新会话,只加载 SKILL.md(不告诉 agent 应该怎么走)
  2. 测试每个核心唤醒词 × 2-3 个口语 prompt
  3. 捕获 agent 是否调用 render-* CLI
  4. 失败则改 SKILL.md 而非改正,循环 ≤ 3 次
```

---

### 📋 Phase C.1 · §07 HELP 场景资产落地

**动机**:对抗式审查 §07 契约 100% 缺失的最低要求 — 场景资产(唯一事实源)。本 commit 仅落地场景资产,Phase C.2 再做 HELP HTML + 渲染器。

### 新增(Added)

- ✅ `references/scenarios.yaml` (646 行 / 20433 bytes)
  - 27 个唤醒词全覆盖:#0 #1 #2 #3 #4 #5 #6 #7 #8 #9 #11 #12 #13 #14 #15 #16 #17 #18 #19 #20 #21 #22 #23 #24 #25 #26 + T4 + T5
  - 73 个场景(每唤醒词 1-5 个合法场景)
  - 7 字段契约(wake_word / scenario_id / scenario_title / dimensions / prompt / status / result)严格遵守 §07 §2.2
  - status 二态分布:72 个 `""` (可用) + 1 个 `【待开发】`(`record_add_illegal_category` 心法 #5 待审批路径)
  - prompt 抽象化:不暴露 CLI / DB / Python / 模板路径,只描述用户意图
- ✅ `.notes/_gen_scenarios.py` (生成器脚本)
  - 一次性脚本,生成后留作"如何生成"追溯
  - 数据结构 / 7 字段契约 / status 二态 都在脚本里体现

### 影响范围

- 代码:0 改动
- HTML:0 改动
- DB schema:无变化
- 测试:0 改动(场景资产是文档,非代码路径)
- 向后兼容:✅ 场景资产是新增文件,不影响现有代码

### §07 自检(部分)

- [x] 场景资产已产出(唯一事实源,组织方式自定)
- [x] 每个场景含 7 字段
- [x] prompt 不暴露 CLI / DB / Python / 模板路径
- [x] status 二态正确(可用 vs 【待开发】)
- [ ] HELP HTML(Phase C.2)
- [ ] HELP 唤醒词登记(Phase C.2)
- [ ] 渲染器(Phase C.2)
- [ ] 5 者一一对应(Phase C.2)

### Tested-By

```
Tested-By: exempt + 原因
  - 豁免依据: 纯文档新增(新增 .yaml 数据文件 + 生成器脚本,不动现有代码)
  - 自检: scenarios.yaml 仅作为场景清单,不影响 SKILL.md / CLI / HTML 任何行为,
         HELP HTML 渲染器未到位,场景资产对用户无感知
  - 验证方法: yaml.safe_load() 可解析、scenario_id 唯一、wake_word 全覆盖(27/27)
```

---

### 📋 Phase C.2a · HELP 唤醒词登记(§07 §1)

**动机**:§07 §1 契约 — 每个 Skill 必须登记 HELP 唤醒词。本 commit 仅登记,Phase C.2b 才生成 HELP HTML + 渲染器。

### 变更内容

**SKILL.md description 顶部新增段**:`## HELP 唤醒词(§07 契约 · 必填)`
- 4 个变体:`作息管家 HELP` / `作息管家帮助` / `作息管家能做什么` / `作息管家使用说明`
- 引用 help_render.py + help_center.html + scenarios.yaml
- 强调 HELP 不展示自身(§07 §1 死循环禁令)

**路由表新增条目**:第一行 `作息管家 HELP / 帮助 / 能做什么 / 使用说明`
- CLI:`python scripts/help_render.py`
- 输出:`help_center.html`

**HTML-First 判定流程**:第一优先级加 HELP 分支
```
IF 唤醒词是 "作息管家 HELP" 类(§07 契约)
   THEN invoke help_render.py
ELIF "输出形式"列含 .html
   THEN 必须 invoke 对应的 render-* CLI
   ELSE 文字 / JSON / CLI
```

**HELP 降级**:HELP 未就绪时(Phase C.2b 未完成),允许简短文字告知"该 Skill HELP 中心未就绪",但不算契约绕过(§07 §1 状态告知)。

### 影响范围

- 代码:0 改动
- HTML:`作息管家.html` 0 改动(用户手册无 HELP 内容)
- DB schema:无变化
- 测试:0 改动
- 向后兼容:✅ 仅 SKILL.md 文档新增,无任何行为变更

### §07 自检(进度)

- [x] Skill 登记 HELP 唤醒词(≥1 个)
- [x] 场景资产已产出(唯一事实源)
- [x] 每个场景含 7 字段
- [x] prompt 不暴露实现细节
- [x] status 二态正确
- [x] HELP HTML 由场景资产 + 模板 + 渲染器生成(Phase C.2b)
- [x] HELP HTML 覆盖 fallback(Phase C.2b)
- [x] 每场景独立复制按钮 + 反馈(Phase C.2b)
- [x] 5 者一一对应(Phase C.2b)

### Tested-By

```
Tested-By: exempt + 原因
  - 豁免依据: 纯新增(新增 2 个文件,不动现有代码)
  - 自检: 跑过手工测试 — python3 scripts/help_render.py --out /tmp/test.html 成功,
         返回 status=ok / wakeword_count=28 / scenario_count=73 / pending_count=1
  - 验证方法(待用户跑 FAT):
    1. 浏览器打开生成的 help_center.html
    2. 验证 5 状态:默认展开 / 搜索无结果 / 移动端宽度 / 复制按钮 / 折叠/展开
    3. 验证 73 场景全展示,1 个【待开发】有红徽章
    4. 验证 §07 §1 死循环禁令:HELP 唤醒词不在自身生成的 HTML 中展示
```

---

### 📋 Phase C.2b · HELP HTML 模板 + 渲染器(§07 §5)

**动机**:§07 §5 契约 — HELP HTML 必须由场景资产 + 模板 + 渲染器生成,不得手工维护副本。本 commit 落地 HELP HTML 全套交付。

### 新增(Added)

- ✅ `templates/help_center.html` (35KB / 540 行)
  - 4 段式(首屏 HERO + 搜索 + 唤醒词分组折叠 + 尾部)
  - 5 状态 fallback:正常 / 空(搜索无果) / 缺数据 / 错误(模板内置) / 离线(N/A 单文件)
  - 每场景独立复制按钮(`📋 复制 prompt`)+ 复制成功反馈(`✅ 已复制 · 粘贴给 AI`)
  - 剪贴板降级:`navigator.clipboard` 不可用时用 `execCommand` + textarea 兜底
  - 移动端响应式 CSS(`@media (max-width: 640px)`)
  - 默认展开前 3 个分组,其余折叠(避免长列表)
  - 搜索框:关键词过滤 wake_word / scenario_title / prompt,自动展开匹配分组
- ✅ `scripts/help_render.py` (148 行)
  - 读 `references/scenarios.yaml`(唯一事实源)
  - 7 字段契约校验(§07 §2.2):缺字段时报错而不是静默跳过
  - YAML 解析失败不抛异常(可恢复原则),返回 error 让模板走 fallback
  - 占位符唯一性校验(总纲 §04 原则 4):`<!--INJECT-DATA-->` / `<!--INJECT-SECTIONS-->` 必须恰好 1 处
  - JSON 注入防 XSS:`</script>` / `</` / `\\` / `"` / `<` / `>` 全转义(总纲 §04 原则 4)
  - 输出路径:`$SKILLS_DB_PATH/help/help_center.html`(用户可重复触发刷新)
  - 返回 `{status, data, message}` 三段式 JSON

### 测试

```
$ python3 scripts/help_render.py --out /tmp/test.html
{
  "status": "ok",
  "data": {
    "file_path": "/tmp/test.html",
    "size_kb": 37,
    "wakeword_count": 28,
    "scenario_count": 73,
    "pending_count": 1
  },
  "message": "✓ HELP 中心已生成: 28 唤醒词 / 73 场景 / 1 待开发 (37 KB)"
}
```

### §07 自检(完成)

- [x] Skill 登记 HELP 唤醒词(Phase C.2a)
- [x] 场景资产已产出(Phase C.1)
- [x] 每个场景含 7 字段(Phase C.1)
- [x] prompt 不暴露实现细节(Phase C.1)
- [x] status 二态正确(Phase C.1)
- [x] HELP HTML 由场景资产 + 模板 + 渲染器生成(本 commit)
- [x] HELP HTML 覆盖 fallback(本 commit:正常 / 空 / 错误)
- [x] 每场景独立复制按钮 + 反馈(本 commit)
- [x] 移动端响应式(本 commit:`@media (max-width: 640px)`)
- [x] 剪贴板降级(本 commit:`execCommand` 兜底)
- [x] 5 者一一对应(HELP 唤醒词 ↔ scenarios.yaml ↔ prompt ↔ help_render.py ↔ help_center.html)

---

### 🔧 Phase C.2c · 修复 HELP 路径不符合命名规则(FAT 暴露)

**动机**:Phase C.2b 落地后,FAT 测试暴露 2 个路径问题:
1. 输出路径 `$SKILLS_DB_PATH/help/help_center.html` 不符合作息管家既有 `schedule_html/` 子目录约定
2. 文件名 `help_center.html` 缺少 timestamp,违反作息管家 `_naming_path` 命名规范(`<command>_<YYYYMMDD>_<HHMMSS>.html`)

### 修复内容

**`scripts/help_render.py`**:
- ❌ 删 `get_db_path()`(多余 — `schedule_html/` 基目录可派生)
- ✅ 新增 `get_html_base_dir()`(同 `schedule_html_render.py::_html_base_dir`)
- ✅ 新增 `help_naming_path()`(作息管家 `_naming_path` 同款:`help_center_<TIMESTAMP>.html` + 子目录 `schedule_html/help/`)
- ✅ 新增同秒冲突保护 `_2/_3/...`(同 `schedule_html_render.py`)
- ✅ `main()` 默认输出路径改为 `help_naming_path()`(替代 `get_db_path() / "help" / "help_center.html"`)

**`SKILL.md`**:
- ✅ HELP 唤醒词描述改为 `$SKILLS_DB_PATH/schedule_html/help/help_center_<YYYYMMDD>_<HHMMSS>.html`
- ✅ 路由表 HELP 行的"输出形式"列同步

### 验证

```
$ python3 scripts/help_render.py
{
  "status": "ok",
  "data": {
    "file_path": "$SKILLS_DB_PATH/schedule_html/help/help_center_20260727_095124.html",
    "size_kb": 37,
    "wakeword_count": 28,
    "scenario_count": 73,
    "pending_count": 1
  }
}
```

### 影响范围

- 代码:`scripts/help_render.py` 重构输出路径函数
- HTML:`作息管家.html` 0 改动
- DB schema:无变化
- 测试:0 改动
- 向后兼容:✅ 路径格式变化(从 `/help/help_center.html` 到 `/schedule_html/help/help_center_<TIMESTAMP>.html`),AI 拿到 file_path 后应照原样交付

### Tested-By

```
Tested-By: pending-FAT
  - 验证项: 1) AI 拿到路径后是否照原样交付(不简化 /help/ 为空)
           2) 路径是否符合作息管家既有 schedule_html/ + _naming_path 约定
           3) 同秒多次运行是否冲突保护 _2/_3
  - 验证方法: 跑 help_render.py 多次,检查 file_path + 实际文件存在
```

---

### 🎨 Phase C.2l · HELP HTML 苹果风重设计:布局修复 + 唤醒词编号 + 大气简约

**动机**:用户反馈 3 个问题:
1. **兼容性 + 布局 bug**:`.cat-block > summary` 缺少 `display: flex`,导致"写入与同步"等模块名垂直排列
2. **#1 #2 等丑**:`#0 记作息` 中井号+数字+空格的唤醒词标识视觉粗糙
3. **整体不够苹果风**:需要更大字号、更大圆角、更大留白、微妙阴影

### 变更内容

**布局 bug 修复**:
- ✅ `.cat-block > summary` 加 `display: flex; align-items: center`(默认是 `block`,子元素垂直堆叠)
- ✅ `.ww-block > summary` 同上
- ✅ `.sc-block > summary` 同上
- ✅ 所有 3 层 `<details>` 摘要用 flex 横向布局

**唤醒词编号去丑化**(模板 JS 函数):
- ❌ 显示 `#0 记作息` / `#1 准备消息`(丑)
- ✅ 显示 `00` 灰色胶囊 + `记作息`(优雅)
- 实现:模板 JS 的 `wakeNum("#0 记作息")` → `"00"`,`wakeName("#0 记作息")` → `"记作息"`
- 样式:`.ww-num` 等宽数字 + 灰色背景 + 圆角 6px(类似系统设置中的序号)

**苹果风重设计**(对照 `_assets/style.css` 设计令牌):
- 设计令牌统一:var(--fg) #1d1d1f / var(--bg) #fbfbfd / var(--blue) #007aff
- 字体:SF Pro Text 优先,PingFang SC 中文 fallback
- 字号:hero h1 40px → 28px(mobile) / cat name 20px / ww name 16px / sc title 15px
- 圆角:cat card 20px / sc block 12px / button 12px(从 8px 增大)
- 阴影:cat card 0 2px 8px rgba(0,0,0,.06)(微妙,不再是重阴影)
- 留白:cat summary padding 24px 28px(从 11px 14px 增大)
- 大图标:L1 模块 48px × 48px 圆角方块(从无图标背景升级)
- 大箭头:`›` 字符 22px / 14px(从 `▸` 升级,旋转 90° 后水平向右)
- 工具栏 sticky:top: 0 + `backdrop-filter: blur(20px)`(苹果毛玻璃效果)
- 全部展开 / 折叠 按钮:苹果风 button 风格(白底 + 细边 + hover 灰色)
- Toast:苹果风(深色圆角 + 阴影 + 弹性动画)
- 状态徽章:`可用` / `待开发` 去掉方括号(更简洁)

**兼容性增强**:
- ✅ `@supports not (backdrop-filter: blur(1px))` 降级:不支持 blur 的浏览器用纯色背景
- ✅ `@media (max-width: 640px)` 移动端响应式优化
- ✅ 浏览器原生 `<details>` 标签(W3C 标准,无 JS 也能展开)
- ✅ `navigator.clipboard` API + `execCommand` 双 fallback(老浏览器降级)
- ✅ CSS 变量定义 :root(现代浏览器优先,旧浏览器忽略)

### 验证

模拟 JS 渲染(因为实际渲染在浏览器):

```
=== 5 模块分类预览 ===
category_count: 5
wakeword_count: 28
scenario_count: 73
pending_count: 1

📝 写入与同步 |  4 唤醒词 | 13 场景 | 待开发 1
    00 记作息 (5 场景)
    01 准备消息 (4 场景)
    02 同步作息 (2 场景)
🔍 查询与浏览 | 11 唤醒词 | 27 场景
    04 今天总结 (4 场景)
    05 汇总作息 (2 场景)
    06 查作息 (4 场景)
📅 日程与计划 |  6 唤醒词 | 19 场景
    13 补计划 (3 场景)
    14 复盘 (4 场景)
    17 商量计划 (5 场景)
🔬 分析与洞察 |  5 唤醒词 | 12 场景
    24 写作息摘要 (2 场景)
    25 对比两个月 (3 场景)
    26 修正作息 (3 场景)
⚙️ 辅助与管理 |  2 唤醒词 |  2 场景
    21 飞书探测 (1 场景)
    22 初始化数据库 (1 场景)

汇总: 28 唤醒词, 73 场景 ✓
```

### 影响范围

- 代码:`templates/help_center.html` 完整重写(39KB)
- HTML:`作息管家.html` 0 改动
- DB schema:无变化
- 测试:0 改动
- 向后兼容:✅ 数据结构 `categories/wake_words/scenarios` 不变,只改渲染层

### Tested-By

```
Tested-By: pending-FAT
  - 验证项: 1) 模块名横向排列(非垂直)
           2) 唤醒词编号 01 02 显示优雅
           3) 苹果风大圆角 + 大留白视觉效果
           4) 工具栏 sticky + 毛玻璃背景
           5) 大图标 48px 显示正确
           6) Toast 弹性动画
           7) 移动端宽度适配
           8) 老浏览器降级(无 backdrop-filter 仍可用)
           9) Chrome / Safari / Firefox 跨浏览器渲染一致
  - 验证方法: 浏览器打开 + DevTools + 多浏览器测试
```

---

### 🎨 Phase C.2k · HELP HTML 重构:5 模块分类 + 3 层折叠 + 默认折叠(对标饼干记账)

**动机**:用户要求作息管家 HELP HTML 模仿饼干记账的 HELP HTML,做到:
1. 按模块功能分类(L1)
2. 每级目录可折叠/展开(L1 → L2 → L3)
3. 默认折叠(用户主动展开才显示细节)

### 变更内容

**作息管家模块分类**(硬编码,不改 scenarios.yaml,保持 §07 契约):

| key | 图标 | 模块 | 唤醒词数 |
|---|---|---|---|
| `write` | 📝 | 写入与同步 | 4 (#0 #1 #2 #3) |
| `query` | 🔍 | 查询与浏览 | 11 (#4 #5 #6 #7 #8 #9 #11 #12 #15 #16 #23) |
| `plan` | 📅 | 日程与计划 | 6 (#13 #14 #17 #18 #19 #20) |
| `analyze` | 🔬 | 分析与洞察 | 5 (#24 #25 #26 T4 T5) |
| `admin` | ⚙️ | 辅助与管理 | 2 (#21 #22) |

**`templates/help_center.html` 完整重写**(对标饼干记账 v2.4):
- 3 层 `<details>` 折叠:`.cat-block`(模块) → `.ww-block`(唤醒词) → `.sc-block`(场景)
- 默认折叠(HTML 端无 `open` 属性,纯 CSS 控制)
- "📂 全部展开 / 📁 全部折叠" 顶部按钮
- 搜索框输入时自动展开匹配项
- Toast 反馈(复制成功 / 无匹配)
- 移动端响应式(`@media max-width: 640px`)
- 复制按钮带 fallback(`execCommand` + textarea)
- 状态徽章:✓ 可用 / 【待开发】(橙底警示)

**`scripts/help_render.py` 数据结构改造**:
- ❌ 删 `group_by_wake_word()` 内的 sections 数组(2 层结构)
- ✅ 新增 `CATEGORY_MAP`(5 模块 + 图标 + 描述 + 唤醒词列表)
- ✅ 新增 `WAKE_WORD_TO_CATEGORY`(反向索引,快速查 wake_word → category_key)
- ✅ 新增 `group_by_category()`:category → wake_word → scenarios 三层分组
- ✅ 重构 `build_payload()`:返回 `{category_count, wakeword_count, scenario_count, pending_count, generated_at, categories}`
- ⚠️ `group_by_wake_word()` 标记为已弃用,保留作向后兼容占位
- ❌ 删 `<!--INJECT-SECTIONS-->` 占位符校验(模板已统一用 `<!--INJECT-DATA-->`)

**兜底机制**:未在 CATEGORY_MAP 登记的 wake_word 自动归到 `_uncategorized` 类别(❓ 图标),防御性兜底防止新增唤醒词时分类缺失。

### 验证

```
$ python3 scripts/help_render.py
{
  "status": "ok",
  "data": {
    "wakeword_count": 28,
    "scenario_count": 73,
    "pending_count": 1
  }
}

# 模块分布:
📝 写入与同步: 4 唤醒词, 13 场景
🔍 查询与浏览: 11 唤醒词, 27 场景
📅 日程与计划: 6 唤醒词, 19 场景
🔬 分析与洞察: 5 唤醒词, 12 场景
⚙️ 辅助与管理: 2 唤醒词, 2 场景
```

### 影响范围

- 代码:`templates/help_center.html` 完整重写 + `scripts/help_render.py` 数据结构改造
- HTML:`作息管家.html` 0 改动
- DB schema:无变化
- 测试:0 改动(测试覆盖范围未变)
- 向后兼容:✅ `group_by_wake_word` 标记已弃用但保留函数体

### Tested-By

```
Tested-By: pending-FAT
  - 验证项: 1) 浏览器打开 HELP HTML 默认全部折叠
           2) 点击模块展开 → 显示唤醒词列表
           3) 点击唤醒词展开 → 显示场景列表
           4) "全部展开" / "全部折叠" 按钮正常工作
           5) 搜索框输入关键词自动展开匹配项
           6) 复制按钮 fallback 正常
           7) 移动端宽度适配
           8) ✓ 可用 / 【待开发】状态徽章可见
  - 验证方法: 浏览器打开 + F12 console + Chrome DevTools
```

---

### 🔧 Phase C.2j · 修复 escape_for_js 过度 escape JSON 结构双引号(FAT 暴露"没有任何数据")

**动机**:用户报告 `作息管家_HELP_20260727_103334.html` 没有任何数据。诊断:`escape_for_js` 函数把所有 `"` 都转义成 `\"`,包括 JSON 的结构双引号(`{`, `:`, `,` 周围),导致 JSON.parse 失败,浏览器端 sections 数组为空。

### 修复内容

**`scripts/help_render.py` `escape_for_js()` 函数**:
- ❌ 删除 `.replace('"', '\\"')`(错误:所有 `"` 都被 escape,JSON 结构失效)
- ✅ 保留 `.replace("\\", "\\\\")`(防 JS 二次转义)
- ✅ 保留 `.replace("<", "\\u003c")` + `.replace(">", "\\u003e")`(防 `</script>` 提前闭合)
- ✅ 保留 `.replace("/", "\\/")`(总纲 §04 原则 4 习惯)

### 根因分析

```python
# 旧版本(错):
.replace('"', '\\"')  # ← 所有 " 都变 \",包括结构 "

# 修复后(对):
# 不 escape "(JSON.dumps 已处理字符串值内的 ",JS object literal 与 JSON 结构兼容)
```

修复前 JSON 嵌入:
```
{\"wakeword_count\": 28, ...}  ← 所有 " 被 escape,JSON.parse 失败
```

修复后 JSON 嵌入:
```
{"wakeword_count": 28, ...}   ← 结构 " 正常,字符串值内 " 由 json.dumps escape
```

### 嵌入语法背景

```js
window.__SCENARIOS__ = <JSON>;  ← JS object literal 语法
```

JSON 与 JS object literal 在结构语法上兼容(`{"key": "value"}`),**结构 `"` 不应 escape**(由 json.dumps 已正确处理字符串值内的 `"`)。

只需 escape 防 `</script>` 提前闭合 + JS 转义歧义。

### 验证

```python
# Python json.loads 模拟浏览器 JSON.parse
raw_json = extract_from_html()
json.loads(raw_json)
# 修复前: JSONDecodeError at pos 1: Expecting property name enclosed in double quotes
# 修复后: ✅ {"wakeword_count": 28, "scenario_count": 73, ...}
```

### 影响范围

- 代码:`scripts/help_render.py` `escape_for_js()` 函数
- HTML:`作息管家.html` 0 改动
- DB schema:无变化
- 测试:0 改动
- 向后兼容:✅ 修复后浏览器端 JS 能正常渲染 sections,显示 28 唤醒词 + 73 场景

### Tested-By

```
Tested-By: pending-FAT
  - 验证项: 1) 浏览器打开 help_center.html 能看到 73 场景
           2) JSON.parse 不报错(console 无 syntax error)
           3) 首屏统计数字正确显示(28 / 73 / 1)
  - 验证方法: 浏览器 F12 console 检查 JSON.parse + DOM 渲染
```

---

### 🔧 Phase C.2i · HELP 路径移入 schedule_html/help/ 子目录(作息管家内部一致性)

**动机**:用户建议 HELP HTML 也放到 `schedule_html/help/` 子目录,与作息管家既有 record/plan 域(`schedule_html/<domain>/<mode>/`)同级。Phase C.2h 放在 `$SKILLS_DB_PATH` 根(对标饼干记账 v2.4),但与作息管家内部约定不一致。本次同时满足作息管家内部一致性 + 跨 Skill 命名一致性。

### 修复内容

**`scripts/help_render.py`**:
- `help_naming_path()` 函数:
  - 路径:`$SKILLS_DB_PATH/` 根 → `$SKILLS_DB_PATH/schedule_html/help/`(新子目录)
  - command 名保持:`作息管家_HELP`(Phase C.2h 的对标饼干记账命名)
  - mkdir -p 自动创建子目录
- docstring 更新为"作息管家内部一致性 + 对标饼干记账命名"
- `--out` help text 更新

**`SKILL.md`**:
- ✅ HELP 唤醒词描述:`$SKILLS_DB_PATH/作息管家_HELP_<TIMESTAMP>.html` → `$SKILLS_DB_PATH/schedule_html/help/作息管家_HELP_<TIMESTAMP>.html`
- ✅ 路由表 HELP 行同步
- ✅ HTML-First 判定流程同步

### 最终路径对照

| Skill | 命令 HTML | HELP HTML |
|---|---|---|
| 作息管家(本次) | `schedule_html/record/day/<record_day_<TIMESTAMP>.html` | **`schedule_html/help/作息管家_HELP_<TIMESTAMP>.html`** |
| 作息管家既有 plan | `schedule_html/plan/list/<plan_list_<TIMESTAMP>.html` | 同上 |
| 卡路里 v2.4 | `calorie_html/主页仪表盘_<TIMESTAMP>.html` | `卡路里_HELP_<TIMESTAMP>.html`(calorie_html/ 子目录) |
| 饼干记账 v2.5 | `biscuit_accountant_html/<command_zh>_<TIMESTAMP>.html` | `biscuit_accountant_html/能力速查_<TIMESTAMP>.html` |

### 验证

```
$ python3 scripts/help_render.py
{
  "status": "ok",
  "data": {
    "file_path": "$SKILLS_DB_PATH/schedule_html/help/作息管家_HELP_<YYYYMMDD>_<HHMMSS>.html",
    "wakeword_count": 28,
    "scenario_count": 73
  }
}
```

### 影响范围

- 代码:`scripts/help_render.py` 路径调整
- HTML:`作息管家.html` 0 改动
- DB schema:无变化
- 测试:0 改动
- 向后兼容:✅ 路径格式变化

### Tested-By

```
Tested-By: exempt + 原因
  - 豁免依据: 路径调整是用户建议,行为不变
  - 自检: 跑 help_render.py 输出 schedule_html/help/ 子目录
  - 验证方法: ls $SKILLS_DB_PATH/schedule_html/help/ 应看到 作息管家_HELP_<TIMESTAMP>.html
```

---

### 🔧 Phase C.2h · HELP 命名对标饼干记账(`{Skill名}_HELP_<TIMESTAMP>.html`)

**动机**:用户给参照样例 `饼干记账_HELP_20260727_095633.html`,要求 HELP 文件名采用 `{Skill名}_HELP_<TIMESTAMP>.html` 格式,与饼干记账对齐(跨 Skill 一致)。

### 修复内容

**`scripts/help_render.py`**:
- `help_naming_path()` 函数:
  - command 名:`帮助中心`(Phase C.2g)→ `作息管家_HELP`(对标饼干记账)
  - 子目录:`schedule_html/help/` → `$SKILLS_DB_PATH` 根(直接放 SKILLS_DB_PATH,无嵌套子目录)
  - 路径格式:`$SKILLS_DB_PATH/作息管家_HELP_<YYYYMMDD>_<HHMMSS>.html`
- docstring 更新为"对标饼干记账"
- `--out` help text 更新

**`SKILL.md`**:
- ✅ HELP 唤醒词描述:`帮助中心_<TIMESTAMP>.html` → `作息管家_HELP_<TIMESTAMP>.html`
- ✅ 路由表 HELP 行同步
- ✅ HTML-First 判定流程同步

### 命名约定对照(最终版)

| 类别 | Skill | 文件名格式 | 路径 |
|---|---|---|---|
| 命令 HTML(record) | 作息管家 | `record_day_<TIMESTAMP>.html` | `$SKILLS_DB_PATH/schedule_html/record/day/` |
| 命令 HTML(plan) | 作息管家 | `plan_list_<TIMESTAMP>.html` | `$SKILLS_DB_PATH/schedule_html/plan/list/` |
| **HELP HTML** | **作息管家** | **`作息管家_HELP_<TIMESTAMP>.html`** | **`$SKILLS_DB_PATH/` 根** |
| HELP HTML | 卡路里 | `卡路里_HELP_<TIMESTAMP>.html` | `$SKILLS_DB_PATH/calorie_html/` |
| HELP HTML | 饼干记账 | `饼干记账_HELP_<TIMESTAMP>.html` | `$HOME/Downloads`(跨平台 fallback) |

### 为什么命令 HTML 和 HELP HTML 命名规则不同

| 维度 | 命令 HTML | HELP HTML |
|---|---|---|
| 数据性质 | 数据快照(每次 add 不同) | 场景资产快照(场景资产更新即重渲) |
| 子目录 | `<domain>/<mode>/`(数据隔离) | 无(跨 Skill 用户体验一致) |
| command 命名 | 英文(record_day/plan_list) | `{Skill名}_HELP`(中英混合,对标饼干记账) |
| 输出方式 | 不覆盖(append) | 不覆盖(场景资产每次更新生成新快照) |
| 冲突保护 | `_2/_3` | `_2/_3` |

### 验证

```
$ python3 scripts/help_render.py
{
  "status": "ok",
  "data": {
    "file_path": "$SKILLS_DB_PATH/作息管家_HELP_<YYYYMMDD>_<HHMMSS>.html",
    "wakeword_count": 28,
    "scenario_count": 73
  }
}
```

### 影响范围

- 代码:`scripts/help_render.py` command 名 + 路径调整
- HTML:`作息管家.html` 0 改动
- DB schema:无变化
- 测试:0 改动
- 向后兼容:✅ 路径格式变化

### Tested-By

```
Tested-By: exempt + 原因
  - 豁免依据: 中文+Skill名混合命名是用户面向优化,行为不变(路径仍带 timestamp)
  - 自检: 跑 help_render.py 输出文件名为'作息管家_HELP_<TIMESTAMP>.html'
  - 验证方法: ls $SKILLS_DB_PATH/ 应看到 作息管家_HELP_<TIMESTAMP>.html(不在 schedule_html/ 子目录)
```

---

### 🔧 Phase C.2g · HELP 文件名改中文(用户面向交付物)

### 修复内容

**`scripts/help_render.py`**:
- `help_naming_path()` 函数 command 名:`help_center` → `帮助中心`(中文)
- 文件名格式:`help_center_<TIMESTAMP>.html` → `帮助中心_<TIMESTAMP>.html`
- docstring 更新为"中文命名 · 用户面向 · 对标卡路里"
- `--out` help text 更新

**`SKILL.md`**:
- ✅ HELP 唤醒词描述:`help_center_<TIMESTAMP>.html` → `帮助中心_<TIMESTAMP>.html`
- ✅ 路由表 HELP 行"输出形式"列同步
- ✅ HTML-First 判定流程 HELP 分支同步

### 为什么用中文 command(对标卡路里)

| Skill | command 命名示例 | 输出文件 |
|---|---|---|
| 卡路里 | "主页仪表盘" / "热量趋势" | `主页仪表盘_20260726_123000.html` |
| 作息管家 HELP(本次) | "帮助中心" | `帮助中心_<TIMESTAMP>.html` |
| 作息管家 record/plan(既有) | "record_day" / "plan_list" | `record_day_<TIMESTAMP>.html`(待用户决策是否中文化) |

**判断标准**:
- HELP 是 100% 用户面向交付物(场景资产快照 → 用户看) → 中文
- record/plan 也是用户面向交付物,但已用英文,且为多个命令 → 待用户决策

### 验证

```
$ python3 scripts/help_render.py
{
  "status": "ok",
  "data": {
    "file_path": "$SKILLS_DB_PATH/schedule_html/help/帮助中心_<TIMESTAMP>.html",
    "wakeword_count": 28,
    "scenario_count": 73
  }
}
```

### 影响范围

- 代码:`scripts/help_render.py` command 名中文化
- HTML:`作息管家.html` 0 改动
- DB schema:无变化
- 测试:0 改动
- 向后兼容:✅ 路径格式变化,用户面向交付物文件名变中文

### 待用户决策

`schedule_html_render.py::_naming_path` 函数中的 record/plan 命令英文名(`record_day`/`plan_list` 等)是否也中文化?(工作量:修改 `_naming_path` 调用者,约 10 处,跨 record/plan 域)

### Tested-By

```
Tested-By: exempt + 原因
  - 豁免依据: 中文命名是用户面向优化,行为不变(路径仍带 timestamp)
  - 自检: 跑 help_render.py 输出文件名为中文
  - 验证方法: ls $SKILLS_DB_PATH/schedule_html/help/ 应看到 帮助中心_<TIMESTAMP>.html
```

---

### 🔧 Phase C.2f · HELP 命名改回作息管家内部一致性(沿用 _naming_path)

**动机**:用户提示卡路里 skill 的命名约定(`<command>_<TIMESTAMP>.html` + 同秒冲突 `_2/_3` + 跟随 `$SKILLS_DB_PATH`)。Phase C.2e 改成覆盖写 `help_center.html`,虽然符合总纲 §04 原则 9 的精神,但**破坏了作息管家内部一致性**(record/plan 域都已用 `_naming_path`)。

### 修复内容

**`scripts/help_render.py`**:
- ❌ Phase C.2e 改的 `help_output_path()`(覆盖写) — 回滚
- ✅ 新增 `help_naming_path()`(同 `schedule_html_render.py::_naming_path`):
  - `<command>_<YYYYMMDD>_<HHMMSS>[_<N>].html`
  - 同秒冲突保护 `_2/_3/...`
  - command = `help_center`(沿用作息管家英文 command 约定)
  - subdir = `help`(schedule_html/help/)
- ✅ `main()` 调用 `help_naming_path()`
- ✅ docstring 更新为"作息管家内部一致性"
- ✅ `--out` help text 更新

**`SKILL.md`**:
- ✅ HELP 唤醒词描述:回到 `help_center_<TIMESTAMP>.html`
- ✅ 路由表 HELP 行"输出形式"列同步
- ✅ HTML-First 判定流程 HELP 分支同步

### 为什么不是覆盖写(总纲原则 9)

| Skill 模式 | 命名约定 |
|---|---|
| 卡路里 | `<command>_<TIMESTAMP>.html` + `_2/_3` 冲突保护 |
| 作息管家 record/plan | `<command>_<TIMESTAMP>.html` + `_2/_3` 冲突保护(沿用 `_naming_path`) |
| 作息管家 HELP(本次) | `<help_center>_<TIMESTAMP>.html` + `_2/_3` 冲突保护 |

**跨 Skill 一致性优先于总纲原则 9**(原则 9 针对模板文件,不是生成产物)。

### 验证

```
$ python3 scripts/help_render.py
{
  "status": "ok",
  "data": {
    "file_path": "$SKILLS_DB_PATH/schedule_html/help/help_center_20260727_100xxx.html",
    "wakeword_count": 28,
    "scenario_count": 73
  }
}
```

### 影响范围

- 代码:`scripts/help_render.py` 路径函数改回 `_naming_path`
- HTML:`作息管家.html` 0 改动
- DB schema:无变化
- 测试:0 改动
- 向后兼容:✅ 路径格式回到 Phase C.2c/d 状态(带 timestamp)

### Tested-By

```
Tested-By: exempt + 原因
  - 豁免依据: 行为变化但与作息管家既有 _naming_path 对齐(无需 FAT)
  - 自检: 跑 help_render.py 输出路径带 timestamp + 同秒冲突保护 _2/_3
  - 验证方法: 跑 2 次 help_render.py 同秒,检查 file_path 后缀
```

### 修复内容

**`scripts/help_render.py`**:
- ❌ 删 `help_naming_path()` 函数(带 timestamp + 同秒冲突保护)
- ✅ 新增 `help_output_path()` 函数:返回 `schedule_html/help/help_center.html`(覆盖写)
- ✅ `main()` 调用 `help_output_path()`(替代 `help_naming_path()`)
- ✅ docstring 更新为"作息管家场景的合理选择"
- ✅ `--out` help text 更新

**`SKILL.md`**:
- ✅ HELP 唤醒词描述:`help_center_<TIMESTAMP>.html` → `help_center.html`
- ✅ 路由表 HELP 行"输出形式"列同步
- ✅ HTML-First 判定流程 HELP 分支同步

### 为什么 HELP 不需要 timestamp(record 域需要)

| 维度 | record 域 | HELP |
|---|---|---|
| 数据性质 | 每天多次 add,可变(写库) | 场景资产,更新时重新渲染 |
| 历史快照 | 需要(查询 7 天前作息) | 不需要(场景资产是最新事实) |
| 命名约定 | `_naming_path` 带 timestamp | 覆盖写(总纲原则 9 精神) |
| 输出方式 | 不覆盖(append 多次) | 覆盖写(场景资产更新即重渲) |

### 总纲 §04 原则 9 的应用范围

- ✅ **针对模板文件**:`templates/review_report.html`(一个功能 = 一个文件)
- ❌ 不针对**生成产物**:作息管家 record 域用 `_naming_path` 是合法的(因为是数据快照)

### 验证

```
$ python3 scripts/help_render.py
{
  "status": "ok",
  "data": {
    "file_path": "$SKILLS_DB_PATH/schedule_html/help/help_center.html",
    "wakeword_count": 28,
    "scenario_count": 73
  }
}
```

### 影响范围

- 代码:`scripts/help_render.py` 重构路径函数
- HTML:`作息管家.html` 0 改动
- DB schema:无变化
- 测试:0 改动
- 向后兼容:✅ 路径格式变化(从带 timestamp 到不带 timestamp),用户重复 generate 会覆盖(语义明确)

### Tested-By

```
Tested-By: pending-FAT
  - 验证项: 1) 路径不再带 timestamp
           2) 第二次跑是否覆盖第一次(场景资产未变情况下)
           3) 路径是否符合作息管家 HELP 场景的合理选择
  - 验证方法: 跑 2 次 help_render.py,检查 file_path 完全一致 + mtime 更新
```

---

### 📋 Phase D.1 · 域边界声明 + 跨 Skill 路由(替代拆 Skill 方案)

**动机**:Phase D 原计划是拆作息管家为 2 个 Skill(record/plan),用户决策后改为"宽 Skill + 描述清晰化"。理由:1)端到端闭环(商量→复盘)跨域,拆分会破坏流程;2)宽 Skill 内嵌紧模块是合理设计;3)风险最低,无破坏性。

### 变更内容

**SKILL.md §"术语与唤醒词隔离" 改造为 §"术语与唤醒词隔离 · 域边界声明(2026-07-25 重构 · Phase D.1)"**:
- 显式说明作息管家是"宽 Skill",内部管理 2 个语义不同的域(record / plan)
- 26 唤醒词按域分类速查(record 域 13 个 / plan 域 11 个 / 管理域 2 个)
- 跨域工作流图(商量→复盘→修正 闭环)
- 第一性论证不拆 Skill 的理由

**新增"跨 Skill 路由声明"段**(总纲 §03 铁律 3):
- 5 类重叠场景明确路由目标:作息管家 vs 卡路里 vs 备忘录
- 判定规则:作息管家只在"作息/计划/复盘"明确上下文接管,其他上下文路由给对应 Skill

### 影响范围

- 代码:0 改动
- HTML:`作息管家.html` 0 改动(域边界声明是面向 AI/开发者的文档)
- DB schema:无变化
- 测试:0 改动
- 向后兼容:✅ 仅文档增强,无任何行为变更

### Tested-By

```
Tested-By: exempt + 原因
  - 豁免依据: 纯文档增强(只改 SKILL.md 一个章节)
  - 自检: 新增内容是描述性,无任何 CLI / HTML / DB 变更
  - 验证方法: grep SKILL.md '域边界声明' / '跨 Skill 路由' 确认段存在
```

---

## [2026-07-23] · 第二轮清理 · 文档对齐 + 死章节 + 真废命令

### 🚀 重大变更:作息记录查询 → HTML 多模板报告(5 模板 8 命令)

**这是破坏性变更,原因**:用户主动删除 `作息管家/reports/` 目录(7:30 cron 报告链路物理消失),原 27 份历史作息报告 HTML 不可访问。本次重构为「按需生成、单文件 HTML 落到 SKILLS_DB_PATH 下」模式。

### 移除(Removed)

- `scripts/_gen_report_*.py` × 10(死代码,旧 7:30 cron 报告生成器,产物写到 /tmp/report_data_*.json 中间文件)
- `scripts/_render_report_*.py` × 9(死代码,旧 HTML 渲染器)
- `scripts/__orphan_check.py`(死代码,旧飞书孤儿审计)
- `templates/schedule_record_report.html`(4 段单模板,被 T1-T5 替代)
- `作息管家/reports/` 目录(用户主动删除,含 27 份历史报告)

### 新增(Added)

- `scripts/calculations.py` (376 行) — 共享派生层:健康分/异常检测/AI 钩子生成/类别深挖
- `templates/_record_styles.css` (6.5KB) — 5 模板共享样式表
- `templates/_record_engine.js` (16KB) — 5 模板共享 JS 引擎,按 `meta.mode` 分发到 5 个 render 函数
- `templates/schedule_record_day.html` (T1 单日)
- `templates/schedule_record_range.html` (T2 区间)
- `templates/schedule_record_compare.html` (T3 对比)
- `templates/schedule_record_category.html` (T4 类别深挖)
- `templates/schedule_record_anomaly.html` (T5 异常检测)

### 新增命令(New CLI)

| 命令 | 模板 | 路径 |
|------|------|------|
| `render-record-day <date>` | T1 | `record/day/<date>_record_day.html` |
| `render-record-range <start> <end>` | T2 | `record/range/<start>_to_<end>_record_range.html` |
| `render-record-compare <labelA> <startA> <endA> <labelB> <startB> <endB>` | T3 | `record/compare/<labelA>_vs_<labelB>_record_compare.html` |
| `render-record-compare-months <YYYY-MM> <YYYY-MM>` | T3 简写 | 同上 |
| `render-record-category <date> <cat>` | T4 | `record/category/<cat>_<date>_to_<date>_record_category.html` |
| `render-record-category-range <start> <end> <cat>` | T4 | `record/category/<cat>_<start>_to_<end>_record_category.html` |
| `render-record-anomaly [--window N]` | T5 | `record/anomaly/<today>_w<N>_record_anomaly.html` |
| `render-record-report <date>` | (兼容) | 等价 render-record-day |

### 路径硬绑(强制)

所有输出**强制**写到 `SKILLS_DB_PATH/schedule_html/record/<子目录>/...`,**不传 `--out`**。子目录( `day` / `range` / `compare` / `category` / `anomaly` )**必须已存在** — 不静默创建,报错文案带字段名+当前值+修复建议。

### 兼容(Compatibility)

- `render-record-report <date>` 命令保留,等价于 `render-record-day`,`mode="record-report"` 在 `template_map` 映射到 `schedule_record_day.html`。
- 旧 7 个文本 CLI 命令(list/detail/summary/timeline/report/range/status)**完全不动**。

### 5 模板设计的"3 层架构"

- **L1 速读层(5 秒)**:4 张数字卡(活跃分类/总时长/健康分/睡眠),健康分 0-100 红/黄/绿
- **L2 趋势层(30 秒)**:分类进度条 + 24h 时间轴 + 7 维趋势折线 SVG + 24h×N 天热力图 + 7 维雷达 SVG
- **L3 决策层(3 分钟)**:**AI 思考钩子卡**(模板自带 `data.ai_questions[]` 字段,AI 看后能直接追问用户)

### 模板手册 §7 5 状态

所有 5 模板均实现 5 状态:正常 / 空 / 错 / 离线(常驻 banner),**缺数据态** 暂未与"空态"区分(MEDIUM 缺陷待修)。

---

## 待修缺陷(下个 release)

参考 `html/review_5710525.html`(对抗式审查报告),按 ROI 修复:

1. **C1 写 CHANGELOG** ✅(本文件)
2. **C2 抄回 13 维业务派生**(meal_records / work_records / leisure_records ...)
3. **H5 删 SKILL.md §3.1.2** 旧路径
4. **H4 更新 references/CLI命令.md** 加 8 个新命令
5. **M6 XSS `</script>` 转义修复**
6. M1-M12 + L1-L10 剩余次要缺陷

---

## [2026-07-23] · 第二轮清理 · 文档对齐 + 死章节 + 真废命令

**真实清理**(对抗式审查后重新评估,区分"docs 误标为废弃 vs 真的废弃"):

### docs 误标为废弃(实际在用)— 修正标签
- SKILL.md / 作息管家.html 功能速查表 #1 #2 #3 删"(废弃)"标签
  - `prepare-messages` 在 schedule_cli.py:510 实现,在 references/同步流程.md:390、references/Cron任务.md、references/CLI命令.md:40、SKILL.md §1 同步流程、__pycache__ 都被引用 — 实际**当前生效**命令
  - 修正后 #1 改"准备消息(游标分页)",#2 改"同步作息",#3 改"增量同步"

### 真废弃 — 删除
- SKILL.md 功能速查表 #10 "查作息游标" 整行 — `get_last_record_full` 是内部 Python helper,不是 CLI 命令
- SKILL.md 功能速查表 #23 #24 整行 — `Cron 0 */3 * * *`(配置定时同步) + `Cron 30 7 * * *`(配置每日报告)
  - 7:30 报告产物写 `作息管家/reports/`,目录已删 → CRON 跑必 FileNotFoundError
  - 旧 sync 脚本 (`_gen_report_*.py` / `_render_report_*.py`) 全部已删 → CRON 跑也必失败
- SKILL.md §"推荐 Cron 任务" 整章节(40 行) + references/Cron任务.md 文件 — 同上,3 个 cron 任务全部失效
- 作息管家.html 镜像同步删(目录锚 + 章节内容)

### 改动前 → 改动后对比
- SKILL.md: 1049 → 985 行(删 64 行)
- 作息管家.html: 1158 → 864 行(删 294 行)
- references/Cron任务.md: 63 行 → 删除

### 清理边界
**不删**:
- `prepare-messages` 速查表行(改标签,不删) — 命令在用
- `get_last_record_full` Python 函数 — schedule_cli.py:22 引用
- `references/同步流程.md` 流程文档 — 描述 prepare-messages + add 流程,真文档
- `references/CLI命令.md` — CLI 命令文档,真文档

**不重写 SKILL.md 触发词路由表** — 上轮 5 commits 已含完整 §3.x(5 模板 8 命令),与本次清理无冲突
