# Changelog · 备忘录 (Memorandum)

所有对备忘录的 **显著** 变更记录在此。格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

> **强制性规定**(SKILL.md 顶部):HTML 镜像 + changelog 必须与代码同步。
> 本文档与 SKILL.md + 备忘录.html 共同维护。

---

## [1.0.0] · 2026-07-24

> **首个正式版本**。9 个 commit 闭环,5 个 HTML 模板(2 结果型 + 3 过程型),68 个 pytest 用例全过。
> 6 大特性(可识别/可验证/可恢复/可约束/可联动/可演进)全部具备。

### Added
- **`wish-batch-plan` 子命令**(过程型 HTML 第 1 个)· `memo_cli.py wish-batch-plan [--ids] [--all] [--suggest-due X] [--html]`
  - 模板 `templates/wish_plan.html` · 4 部分 prompt(场景/数据/期望/来源)
  - 9 个新 pytest 用例
  - commit `e6d5d89`
- **`wish-complete` 子命令**(过程型 HTML 第 2 个)· `memo_cli.py wish-complete [--ids] [--all] [--content] [--html]`
  - 默认搜未排期+已过期心愿(50 条)
  - `--all` 含全部心愿
  - `--content` 默认打卡内容(HTML 可逐条覆盖)
  - 模板 `templates/wish_complete.html` · 渲染器 `memo_render.py:render_wish_complete`
  - 9 个新 pytest 用例
  - commit `6944912`
- **`batch-update-category` 子命令**(过程型 HTML 第 3 个)· `memo_cli.py batch-update-category --from-category <X> [--to-category <Y>] [--html]`
  - 一次列出同分类所有笔记(限 200 条)
  - HTML 中下拉选目标分类
  - 硬规则:`from-category ≠ to-category`
  - 副作用:只改 `category`,**不动 `sub_category`**
  - 模板 `templates/change_category.html` · 渲染器 `memo_render.py:render_change_category`
  - 7 个新 pytest 用例
  - commit `7a4e37f`
- **`sync-from-feishu --html`** · 结果型 HTML 报告页
  - 11 个统计字段(backfilled/scanned_done/synced/scanned_pending/due_added/...)
  - 3 步折叠详情 · errors 红色高亮 · 复制同步回执
  - 模板 `templates/sync_report.html` · 渲染器 `memo_render.py:render_sync_report`
  - commit `b1193c0`
- **`模板HTML并注入数据/_shared/injector.py`** · 跨 Skill 共享 HTML 注入器
  - 3 个公共函数:`inject_html` / `write_output` / `render`
  - 占位符唯一性校验(数量 ≠ 1 → raise ValueError)
  - `</` 转义防 `<script>` 提前闭合
  - 出处引用《预置HTML并注入数据指导手册》§8
  - 10 个新 pytest 用例(占位符/转义/UTF-8/进程间 import)
  - commit `5378005`
- **触发词别名 "完成打卡" → "完成心愿"**(Step 9)· 解决用户口语化 vs 内部术语 gap
  - commit `5a78779`
- **触发词路由规则**(Step 8)· `update-category` vs `batch-update-category` 二选一
  - 判定启发:含 1 个 id → 单条;含"都/全部/多 id" → 批量;无 id 无都 → 反问
  - commit `c667ef2`
- **tests/ 目录建立** · `conftest.py` + 4 测试模块,68 个用例覆盖 validators/render/payloads/wish_plan/wish_complete/change_category/shared_injector
- **`.githooks/pre-commit` 加 `备忘录/*` 路由** · 改备忘录自动跑 pytest

### Changed
- **SKILL.md 与代码裂缝修复**(L114-L228 · 5 处"默认行为")
  - 旧:「默认生成 HTML」「需要纯 JSON 时再显式传 `--no-html`」
  - 新:「默认返回 JSON · 传 `--html` 生成 HTML · 当前没有 `--no-html` flag」
  - commit `b1193c0`
- **备忘录.html HTML 镜像同步**(强制规定 1 条 · 5 阶段都同步修订)
- **`memo_render.py` 重构** · 抽 `_inject` + `_write_output` 公共函数 → 后被 `_shared/injector.py` 取代
- **5 模板统一设计** · 首屏 KIPI 卡 + 主体分组 + 尾部"采纳/复制"按钮(过程型);3 步折叠(结果型 sync_report)
- **4 部分 prompt 成为向导标配** · 采纳按钮一键复制(场景/数据/期望/来源)

### Deprecated
- 无

### Removed
- 无

### Fixed
- **SKILL.md / 代码裂缝**(Step 1)· 5 处"默认行为"与 CLI 不一致,文档对齐
- **3 个测试脚本错误**(对抗式审查发现)· `</script>` 转义误判 / fixture 路径不一致等

### Security
- 无

---

## [1.1.4] · 2026-07-28

> **patch**(语义化版本规则):备忘录 HELP 唤醒词(总纲 §07 契约)
> 用户回复 4 选:yaml / 老的直接删掉 / 必须要 / FAT 最后再说

### Added(按总纲 §07 HELP 与场景完备性契约)

- **触发词 `备忘录 HELP`**(第 29 个)
- **场景资产**:`references/scenarios.yaml`
  - 29 条场景(对应 28 个业务唤醒词 + 备忘改分类批量版)
  - 7 字段必填契约:`wake_word / scenario_id / scenario_title / dimensions / prompt / status / result`
  - prompt 不暴露 CLI / DB / Python / 模板路径(§07 §3)
  - 全部 `status = ""`(本期无【待开发】)
- **HELP HTML 模板**:`templates/memo_help.html`
  - 4 段式 + 5 状态 fallback(§04 原则 3)
  - 7 分组:记录类 / 查找类 / 提醒类 / 心愿类 / 批量类 / 跨 Skill / 子唤醒词
  - 每场景独立复制按钮(剪贴板 API + `execCommand` 降级)
  - 搜索 / 分类筛选 / 详情折叠
  - 不展示 HELP 唤醒词自身(§07 §5 反模式 3)
- **渲染器**:`script/memo_render.py:render_help`
  - 路径(§04 原则 12.B):`memo_html/备忘录_HELP_<YYYYMMDD>_<HHMMSS>[_<N>].html`
  - ★ **额外要求**:渲染后自动复制到 `<SKILL_DIR>/备忘录.html`,覆盖旧版
- **CLI 子命令**:`memo_cli.py help`
  - 必生成 HELP HTML + 覆盖 skill 根目录 备忘录.html
  - 无 `--html` / `--json` flag(用户约定 #3:简化调用)

### Removed(用户约定 #2)

- **旧 `备忘录.html` 已删除**(475 行手写用户手册,v1.0.9 起)
  - 不再有"第二份"HTML 在 skill 根目录
  - 新 `备忘录.html` = `memo_cli.py help` 产物(单一来源)

### Added(post-FT · `--output` B 方案)

- **`help` 子命令加 `--output` / `-o` 旗标**(总纲 §04 原则 12.X "显式 override 允许")
- **render_help 函数加 `output_path` kwarg**

**B 方案语义**(用户选定):
- 默认(无 `--output`):写 2 份(时间戳副本 + skill 根 `备忘录.html`)
- 加 `--output /path`:写 3 份(`备忘录.html` **永远**被覆盖,`--output` 是 +1 份额外投放)

适用场景:
- 跑测试不想污染 `memo_html/` 目录
- 给同事单次分享 HTML(不污染历史)
- 调试对比:skill 根 vs 自定义输出

**父目录自动 mkdir**(不需要预先 `mkdir -p`)。

### Tests(post-FT · +8 用例)

`tests/test_help.py:TestHelpOutputFlag` 8 个新用例:
1. `test_render_help_output_path_kwarg` — 函数级 kwarg 工作
2. `test_render_help_output_none_default` — 默认 None
3. `test_render_help_creates_parent_dir` — 嵌套父目录自动创建
4. `test_render_help_output_does_not_skip_skill_root` — **核心 B 方案保证**
5. `test_cli_help_with_output_flag` — CLI `--output` 工作
6. `test_cli_help_short_output_flag` — 短旗标 `-o`
7. `test_cli_help_output_message_notes_extra_copy` — UX 反馈
8. `test_cli_help_without_output_no_extra_path_in_json` — 默认无额外字段

全量:156/156 pytest 通过(v1.1.4 首次 148 + 8 个 `--output` 用例)

### Changed(post-FAT · G1 修复)

- **SKILL.md §备忘录 HELP 新增"唤醒词灵活匹配"段**
  - FAT(§05 钩子 ⑥)发现:G1 · SKILL.md 没明文规定 HELP 唤醒词的灵活匹配规则
  - 风险:Fresh Agent 看到字面 `备忘录 HELP` 可能误判需要完全匹配 → 漏触发口语化变体
  - 修复:加 8 种变体示例(字面 / 大小写 / 缩字 / 口语化 / slash / 英文同义) + 判定优先级 + 反例
  - 守门:`tests/test_help.py` 加 2 个回归用例

### Tests(post-FAT · +2 用例)

`tests/test_help.py:TestHelpWakeWordFlexibility` 2 个新用例:
1. `test_skill_md_documents_wake_word_flexibility` — SKILL.md 含 "灵活匹配" 段
2. `test_skill_md_documents_variations_examples` — SKILL.md 含变体示例(口语化 / slash 等)

全量:158/156 pytest 通过(148 → 158 · +8 个 `--output` + +2 个 flex)

### Changed(post-FAT · G2 + G3 修复)

- **SKILL.md §HTML 输出目录规则(G2 修复)**:
  - FAT 发现:HTML 路径受 `SKILLS_DB_PATH` 影响没强调,AI 可能误用硬编码 `D:\.db\memo_html\`
  - 修复:加"实际路径 = `<SKILLS_DB_PATH>/memo_html/`"明文 + 3 种环境示例
- **SKILL.md 新增 §用户原话 → 触发词 反向指引表(G3 修复)**:
  - FAT 发现:缺"用户口语 → 哪个触发词"反查表,AI 处理多义口语化表达时易误判
  - 修复:15 行反查表(覆盖核心 6 触发词 + 9 子唤醒词场景)+ 4 步反查流程 + 3 反例

### Tests(post-FAT · +4 用例)

`tests/test_help.py` +4 用例:
1. `test_skill_md_documents_skills_db_path_influence` — SKILL.md 含 G2 提示
2. `test_html_output_uses_skills_db_path_when_set` — **实测 env var 影响路径**(集成测试)
3. `test_skill_md_has_reverse_lookup_section` — SKILL.md 含 G3 反向指引段
4. `test_reverse_lookup_table_covers_core_triggers` — 反向指引表覆盖 ≥5 核心触发词

全量:162/162 pytest 通过(158 → 162 · +4)

### Changed(重构 · 三层折叠结构)

按用户反馈重构 HELP HTML 为**三级折叠**结构(去除 KPI / 筛选 / TOC 状态摘要):

| 层级 | 元素 | 默认 | 折叠后行为 |
|---|---|---|---|
| Level 1 | 功能模块(`<details class="module">`) | **折叠** | 只看模块标题 |
| Level 2 | 场景卡片(头:chip + 标题 + 复制按钮) | 展开 | 看场景列表 |
| Level 3 | 维度/prompt/result(`<details class="details">`) | **折叠** | 只看场景头 |

**设计原则**:
- 复制按钮在场景**头部**(用户:"场景的末尾有这个 复制prompt 挺好,省得我还要看详情才能复制")→ 总是可见,无需展开细节
- 模块/细节默认折叠 → 用户点开看 → 大规模场景不显凌乱
- 不再有 KPI 卡 / 筛选 / TOC → 总纲 §07 §5 禁止"纯状态告知列表"

**清理项**(状态摘要 · 违反 §07 §5):
- 删除 KPI 网格(场景总数 / 业务唤醒词 / 分组 / 【待开发】)
- 删除筛选面板(搜索框 + 分类 chips)
- 删除 TOC 锚点导航
- 删除分组计数(记录类(5) → 记录类)
- 删除元信息里的"场景数:N"计数(版本 + 生成时间保留为元数据)

### Tests(+6 用例 · 重构守护)

`tests/test_help.py:TestHelpThreeLevelCollapse` 6 个新用例:
1. `test_template_has_level1_module_creation` — 模块用 JS createElement
2. `test_template_has_level3_details_creation` — 细节用 JS createElement
3. `test_modules_default_collapsed` — 模块默认折叠
4. `test_scenario_details_default_collapsed` — 细节默认折叠
5. `test_copy_button_visible_at_scenario_level` — 复制按钮在场景头
6. `test_no_kpi_grid_or_filter_or_toc` — 无状态摘要元素
7. `test_three_level_structure_via_js_simulation` — 模拟渲染 7 模块 + 29 场景

`tests/test_html_user_manual.py` 同步清理:
- 删除 `test_has_toc`(TOC 已移除)
- 删除 `test_has_search_filter`(筛选已移除)
- 新增 `test_no_search_or_toc`(反向守护)

全量:168/168 pytest 通过(162 → 168 · +6)

### Changed

- `SKILL.md`:
  - 触发词表新增 `备忘录 HELP` 行(第 29)
  - 统计从 28 → 29
  - 「HTML 同步」条款新增 v1.1.4 例外说明(自动生成)
  - 新增「备忘录 HELP」专章,引用总纲 §07 契约

### Tests(`tests/test_help.py` 新增 22 用例守护)

1. `test_file_exists` — 场景资产文件存在
2. `test_skill_and_version_keys` — 顶层字段齐全
3. `test_28_wake_words_minimum` — 触发词 ≥ 28
4. `test_scenario_count_matches_skill_md` — SKILL.md ↔ scenarios 一致
5. `test_all_7_fields_present` — 契约 §07 §2.2 7 字段必填
6. `test_scenario_id_unique` — scenario_id 跨场景唯一
7. `test_no_pending_dev_status` — 本期无【待开发】
8. `test_no_cli_or_db_leak_in_prompt` — prompt 抽象(§07 §3)
9. `test_template_exists` — 模板存在
10. `test_placeholder_unique` — `<!--INJECT-DATA-->` 唯一
11. `test_no_help_wake_word_in_template` — 模板静态文本不含 HELP 自身
12. `test_produces_timestamped_copy` — §04 原则 12.B 命名
13. `test_overwrites_skill_root_help` — **用户额外要求**覆盖生效
14. `test_skill_root_content_matches_timestamped` — 内容一致
15. `test_html_contains_window_data` — 注入成功
16. `test_html_contains_all_wake_words` — §07 §5 全业务唤醒词
17. `test_html_does_not_show_help_itself` — §07 §5 反模式 3
18. `test_has_5_state_fallback` — §04 原则 3 5 状态
19. `test_has_copy_button_mechanism` — 每场景独立复制按钮
20. `test_help_subcommand_runs` — CLI help 可执行
21. `test_help_has_no_html_flag` — 用户约定 #3 必生成

**`tests/test_html_user_manual.py`** 退役重写:
- 旧测试守护的是手写用户手册(已删除)
- 新测试守护 HELP HTML 可读性(总纲 §07 §5)

### 范围

- 新增 1 个资产文件 + 1 个 HTML 模板 + 1 个 CLI 子命令 + 22 个测试
- 删除 1 个手写 HTML(用户约定 #2)
- 改动 2 个核心 Python 文件 + 1 个 SKILL.md

### 测试

- 全量:148/148 pytest 通过(126 → 148 · +22 来自 HELP 测试)
- 端到端:`memo_cli.py help` 实际生成 HELP HTML + 覆盖 skill 根 备忘录.html
- 失败路径:SCENARIOS_PATH 缺失 → 报错"场景资产缺失"
- 守门:prompt 不含 `memo_cli.py` / `memo.db` / `templates/` 等关键字

### 总纲 §07 自检(14 项)

| # | 检查项 | 状态 |
|---|---|---|
| 1 | 登记 HELP 唤醒词 + 不在 HTML 展示自身 | ✅ |
| 2 | 场景资产 = 唯一事实源 | ✅ |
| 3 | 7 字段必填 | ✅ |
| 4 | prompt 不暴露 CLI / DB / 路径 | ✅ |
| 5 | status 二态(本期全可用) | ✅ |
| 6 | 【待开发】AI 停步逻辑(本期无触发) | ✅(逻辑已就绪) |
| 7 | HELP HTML 由资产+模板+渲染器生成 | ✅ |
| 8 | 5 状态 fallback | ✅ |
| 9 | 搜索 / 筛选 / 折叠 | ✅ |
| 10 | 多端适配(@media) | ✅ |
| 11 | 每场景独立复制按钮 + 反馈 + 降级 | ✅ |
| 12 | 5 者一一对应(唤醒词 ↔ 资产 ↔ prompt ↔ 底层 ↔ HTML) | ✅ |
| 13 | FAT 协议(待跑 · 用户 #4) | ⏸ 用户决定 FAT 时机 |
| 14 | 跨 Skill 路由冲突声明 | ✅(备忘改分类批量场景已声明) |

---

## [1.1.3] · 2026-07-25

> **patch**(语义化版本规则):复制按钮改造 — 文案简化 + 富内容 + 视觉反馈
> 来源:用户反馈"复制的内容不是单纯 ID,是里面的相关信息,这样复制错了能看到"

### Changed (templates/memo_query.html)
- **每条 item 的"复制 ID"按钮改造**:
  - 按钮文案 `复制ID` → `复制` (简化 · 用户明确要求)
  - 复制内容从纯 ID 数字 → 含完整信息的可读文本:
    ```
    备忘录 #42
    分类: 备忘 / 工作
    创建: 2026-07-24 10:00
    内容: 今天开了个会
    排期: 2026-07-30(如有)
    提醒: ...(如有)
    ```
  - 用户点击 → 剪贴板得到富文本 → 可看到内容确认是否复制错误
- **新函数 `copyInfo(btn)`**:从按钮 `data-item` 属性反序列化 item,构造富文本,调用 `navigator.clipboard.writeText`
- **视觉反馈**:点击后按钮文字临时 `✓ 已复制`,2 秒后还原 → 用户知道是否成功
- **降级**:`navigator.clipboard` 不可用 / 抛出异常时按钮显 `✗ 复制失败`,不静默失败
- **底部"复制查询回执"按钮改造**:
  - 复制内容从纯 ID 列表 → 含每条详情:
    ```
    备忘录查询回执
    命令: search
    结果数: 5/20
    筛选: 全部

    【5 条详情】

    #42 · [备忘/工作] · 2026-07-24 10:00
        今天开了个会
    #43 · [备忘/生活] · 2026-07-23 09:15
        买菜
    ...
    ```
  - 用户看到每条的全部信息(分类/时间/内容),能确认复制正确

### Tests (tests/test_copy_button.py 新增 10 用例守护)
1. `test_copy_button_label_simplified` — 按钮文案是"复制"(不是"复制ID")
2. `test_no_old_copy_id_label` — 防回退(不应有'复制 ID' 字样)
3. `test_copy_button_exists_per_item` — renderItem 内有 class='copy' 按钮
4. `test_copy_info_function_exists` — copyInfo 函数存在
5. `test_copy_info_includes_id_with_hash` — 含 #+id 形式(AI 可解析)
6. `test_copy_info_includes_content` — 含 content 字段引用(用户关键诉求)
7. `test_copy_info_includes_category` — 含 category 字段引用
8. `test_copy_info_includes_created_at` — 含 created_at 字段引用
9. `test_copy_feedback_label_exists` — "✓ 已复制"反馈文案存在
10. `test_copy_receipt_includes_item_details` — receiptText 含每条详情

边界声明:
- 这些测试守护**文档层回归**(字面/字段/函数存在)
- **不**守护运行时行为(JS 语法错、按钮点击无反应、clipboard API 改动)
- 防的回退:文案回退、函数删除、字段缺失、反馈消失、详情降级

### 范围
- 只改 templates/memo_query.html(1 个模板)
- 其他 4 个模板(wish_plan / wish_complete / sync_report / change_category)的"复制"是 `<pre>` 文本,用户自己手动复制,不需要改造

### 测试
- 全量:136/136 pytest 通过(126 → 136 · +10 来自新测试)
- 端到端跑 `search -c 打卡 --html`:实际生成的 HTML 含完整 copyInfo / receiptText 函数
  - 单条复制:`备忘录 #1\n分类: 打卡 / 咖啡\n...`(富内容)
  - 整批复制:含【N 条详情】 + 每条 #ID + 分类 + 时间 + 内容预览

---

## [1.1.2] · 2026-07-25

> **patch**(语义化版本规则):HTML 交付 checklist 化 — 把 v1.1.1 的"陈述"转"checkbox + 回复模板"
> 来源:用户实测"搜最近一周备忘" → AGENT 用 Chrome 打开但**没主动发送** + AGENT 自我检查也**没发现**

### Fixed (文档加强)

**问题根因**(第一性分析):
- SKILL.md v1.1.1 的"AI 必须主动把 HTML 发送出去"是**陈述**
- AGENT 读到了但**没主动对照执行**(LLM agent 默认"答完即结束",不内置流程自检)
- 用户让 AGENT "自我检查"也没发现(自查意识是被动的,不主动反问)

**修复(v1.1.2 = v1.1.1 的 checklist 化)**:
- SKILL.md "HTML 交付规范"段改"陈述"为"checklist + 回复模板":
  - 真正的 markdown checkbox(`- [ ]`,非 prose)AGENT 视觉上能识别
  - **4 项必检**:HTML 路径 / 主动发送工具 / 用户能收到 / 没只输出路径
  - **AGENT 回复模板强制格式**:"✅ [已生成 X][文件路径: XX][我主动发送到了: YY]"(3 段都不能省略)
  - **反例** ≥3 种 ❌ 表达:"只输出路径"、"推给用户 Chrome"、"只提 Chrome"
- 测试守护 `tests/test_html_delivery_checklist.py`(新)13 用例:
  - 4 项 checkbox 必含
  - 回复模板必含"文件路径"+"主动发送"+ 3 个消息工具示例
  - 反例 ≥3
  - "必走一遍"标识
- 用户选择"最小改动先看效果":暂不加 13 处触发词引用 / quick reference / 跨测试

### 影响范围
- SKILL.md 改动范围:**"HTML 交付规范"段**(1 个段,从 v1.1.1 陈述 → v1.1.2 checklist)
- 不影响代码、不影响其他段、不影响其他 Skill

### 已知边界(待用户验)
- LLM agent 默认不内置流程自检 → checklist 是**陈述性提醒**,不是**架构强约束**
- 真正强约束需要 IDE/平台加"任务结束反思 hook"(AGENT 应用层)
- 用户仍是**主动验证方**:`说一句"搜最近一周备忘"`验 AGENT 是否按 checklist 回复

---

## [1.1.1] · 2026-07-25

> **patch**(语义化版本规则):HTML 交付规范加强 — 主动发送是核心,Chrome 打开是加分
> 来源:用户反馈"AGENT 用 Chrome 打开了,但没主动把 HTML 发送到飞书/QQ/微信"

### Fixed
- **SKILL.md "HTML 交付规范"段 v1.1.1 加强**:
  - 之前 v1.0.3:<media> + 浏览器并行,措辞模糊,AI 可能理解为"浏览器打开就够了"
  - **真正问题**:用户可能不在 Chrome 前(手机/微信/飞书等),AI 只打开浏览器 = 没真正送达
  - v1.1.1 修订:
    - **基础动作**: `<media>` 交付 **+ AI 主动发送 HTML 文件到用户可用的工具**
    - **核心**: 主动发送(必须) · Chrome 打开(加分,可同时)
    - **不硬编码消息工具**:用户用飞书就发飞书、用 QQ 就发 QQ、用邮件就发邮件——AI 自己判断用户当前可用工具
    - **HTML 必须到用户手上是硬规定**(方式灵活)
    - 表达示例:"已为你生成查打卡结果。我用 Chrome 打开了本地预览,同时把 HTML 文件发到 [你的常用消息工具]"

### Changed
- SKILL.md "HTML 交付规范"段加 v1.1.1 加强标识 + 重排 Chrome 为"加分项"

### Tests
- `tests/test_html_delivery.py`(新)7 用例守护:
  - 含 `<media>` 交付规则
  - 含"主动发送"硬性规则(必须/核心/不可省略级标识)
  - 不硬编码消息工具
  - 含 Chrome 规则但为可选
  - 用户可能不在 Chrome 前

### 关联
- 这是对 v1.0.3 修订的**进一步修正** —— v1.0.3 没说"主动发送"是核心,只说"`<media>` + 浏览器并行"
- 不影响 v1.1.0(只是文档加强,无代码改动)

---

## [1.1.0] · 2026-07-25

> **bug fix**(语义化版本规则 · 不兼容修复升 1 级):修复 `_shared/injector.py` 被清理后 `备忘录.html` 实际跑不动
> 来源:其他 AGENT 跑 "查打卡 --html" 报 ImportError,根因诊断
> 注:**本 commit 在 v1.0.9 之前(2026-07-24 09:28)的 commit 里,**因为 v1.0.9 commit "重写 备忘录.html" 之后其他 session 跑了 SKILL开发总纲V1.0 的清理 commit(f304e4f 2026-07-24 16:56)删了 _shared/injector.py

### Fixed (真实运行 bug)

**问题**:`备忘录/script/memo_render.py` 的 `from injector import inject_html, write_output` 引用了**已被清理的 `_shared/injector.py`**

| 时间 | 事件 |
|---|---|
| 2026-07-24 09:28 | v1.0.9 commit"备忘录.html 转为纯用户手册" |
| 2026-07-24 16:56 | f304e4f commit"清理已沉淀的旧模板目录"删了 `_shared/` |
| 2026-07-25 之后 | 跑 `--html` 命令 → `ImportError: cannot import name 'inject_html'` |

**根因**:
1. v1.0.6 我设计了"跨 Skill 共享 `_shared/injector.py`"
2. f304e4f 清理者认为内容已沉淀到 `SKILL开发总纲V1.0/_assets/` → 删整个目录
3. **没人通知备忘录**(依赖此文件的 Skill)
4. 测试也"假阳性 PASS" —— `tests/test_shared_injector.py` 用 `sys.path.insert` 加路径,但路径指向不存在的目录,实际找到的是 `备忘录/script/injector.py`(另一个**占位**脚本,导出 `inject` 不导出 `inject_html`)。import 应该 ImportError 但 pytest 把它当 `ERROR` 不是 `FAILURE`,CI 漏报

### Changed

**修复方案 A + 保护补丁**(备忘录私有化):
1. **`备忘录/script/injector.py` 重新创建**(私有 · 不再依赖外部共享模块):
   - 3 个公共 API:`inject_html` / `write_output` / `render`
   - 保留所有 v1.0.6/v1.0.7 增强:占位符唯一性校验 / `</` 转义 / 同秒冲突保护(_2/_3)
   - 详细 docstring 解释从 shared → private 的原因
2. **删除 `memo_render.py` 的 `sys.path.insert` 操作 + 引 _shared 的代码** → 改用本地 `from injector import`(同目录)
3. **`tests/test_injector_local.py`**(新)24 个用例守护:
   - `TestInjectorModuleExists`:module path 真实在 备忘录/script/,不在 _shared/
   - `TestInjectHtml`:占位符/转义/自定义占位符/`</` 转义
   - `TestWriteOutput`:mkdir/UTF-8/冲突保护(_2/_3)/不同 ts 不冲突
   - `TestRenderIntegration`:一站式
   - `TestMemoRenderCanUseInjector`:子进程验证 5 个 render 函数可 import
4. **删除 `tests/test_shared_injector.py`**(测试目标已删,且自身不可信)

**关系重定义**:
- 之前:备忘录 → `_shared/injector.py`(跨 Skill,易被误清理)
- 现在:备忘录 → `script/injector.py`(私有,自包含)
- DRY 共享仍需做,但应在 git submodule / 独立 package / 显式版本管理 · 不是简单目录

### 设计认知(本 bug 的根本教训)

跨 session / 跨 commit 的"简单目录"共享不可靠:
- 谁负责记录依赖?
- 谁负责通知 cleanup?
- 测试如何守护"被删的外部依赖"?

答案:**测试 module 顶部 `from xxx import yyy` 失败时,pytest 应该报 ERROR(模块加载失败),这是真信号**。
但**只要 sys.path 让模块加载能继续,导入仍可能假阳性 PASS**(因为可能被映射到本地的"占位版本")。
**测试守护关键路径**:
- `assert Path(injector.__file__).resolve()` 必须在期望路径
- `assert inject_html is not None` 必须真实存在
- 否则**测试假设的"导入成功"是真信号还是假信号?不确定**

下一阶段v1.1.x 可做:把"跨 Skill 共享"提到 git submodule 或 README 显式声明。

### Tests
- 全量:106/106 pytest 通过(105 → 106 · +1 是 TestMemoRenderCanUseInjector)

---

## [1.0.9] · 2026-07-24

> **设计转变**(语义化版本规则):备忘录.html 从"SKILL.md 镜像"转为"纯用户手册"
> 来源:用户纠正 — `<skill>.html` 不是日志/改动记录,而是**用户手册**(用户看唤醒词/使用方法 + 点击展开看底层)
> 改动日志在哪: `CHANGELOG.md`(独立) · AI 决策用完整规范: `SKILL.md`

### Changed
- **备忘录.html 彻底重写**(纯用户手册):
  - ❌ 删除:版本号 + 8 行历史 · 强制性规定 · HTML 交付规范 · 触发词 → HTML 对照表 · AGENT 决策流程 · 提醒逻辑 · 防文档裂缝守护 · 旧完成提醒流程
  - ✅ 新增:简介(这是什么/不是什么)+ 快速开始 + 环境变量 + 操作规范 + ⚠️ 提醒路由 + 触发词速查表(28 + 一句话)+ 触发词详细(按"做什么"分组,每个含 `<details>` 折叠区)+ 定时提醒(Cron)
  - footer: 链接到 CHANGELOG.md(日志)和 SKILL.md(AI 文档)
- **结构重组**: 触发词从"按功能模块"改为"按用户操作分类"(记录 / 查找 / 提醒 / 心愿 / 批量 / 跨 Skill / 子唤醒词)
- **视觉改进**: Apple 风格 CSS(渐变 / 阴影 / 响应式 / details 折叠动画)

### Removed
- `tests/test_html_trigger_coverage.py` (v1.0.7 的"对照表"已删,测试无关)
- `tests/test_html_expandable.py` (v1.0.8 的"段匹配"已被新结构取代,测试无关)
- 新增:`tests/test_html_user_manual.py` (23 个用例,守护"纯用户手册"不混入日志/AI 规则)

### Tests
- 全量: 105/105 pytest 通过(177 → 105,-72 来自删除过时测试)
- 新 user_manual 测试 23 用例覆盖:
  - 不应含(日志/规则):8 项
  - 应含(用户手册):11 项
  - 可读性:4 项

### 关系重定义

| 文件 | 用途 | 读者 |
|---|---|---|
| `备忘录.html` | 纯用户手册(唤醒词 + 用法 + 展开底层) | 用户 |
| `CHANGELOG.md` | 改动日志 / 版本历史 | 用户 + 维护者 |
| `SKILL.md` | AI 决策用完整规范(HTML 交付 / 触发词对照 / 强制规定 / Cron 机制) | AI + 维护者 |

---

## [1.0.8] · 2026-07-24

> **改进**(语义化版本规则):HTML 镜像设计原则 + 触发词段可展开底层原理
> 来源:用户观点纠正 — `<skill>.html` 不是日志/改动记录,而是**用户手册 + 可展开底层原理**(改动日志在 CHANGELOG.md)

### Added
- **SKILL.md "HTML 镜像设计原则"段**(最高优先级 · 用户认知转变):
  - 表格化:`用户视角` / `技术视角` / `改动日志` / `AI 阅读` 各在哪看
  - `<details>` 折叠语法示范
  - 设计原因:渐进式信息披露(用户看 HTML 找用法,探究层原理点开 details)
- **17 个 `<details>` 折叠区**(15 个具体触发词 + 1 个子唤醒词统一 + 1 个设计原则示例)
  - 每个 details 含:CLI 命令 / SQL / Python 调用链 / 飞书 hook / 失败路径
  - 用户点开看底层,不点开只看主流程
- **`tests/test_html_expandable.py`** 文档裂缝守护
  - 14 段参数化测试 + 设计原则段测试
  - 改 SKILL.md / 备忘录.html 时自动验证任何遗漏

### Changed
- **SKILL.md L13 顶部触发词表 + 子唤醒词列表保留** + 15 段加 details
- **备忘录.html 镜像同步**(强制规定 1 条)· 14 个 h3/h4 段加 details 折叠区
- 行为变化:无(纯文档 + 可展开 UI)

---

## [1.0.7] · 2026-07-24

> **改进**(语义化版本规则):触发词 → HTML 生成对照表 + 文档裂缝守护测试
> 来源:用户问"AGENT 执行 SKILL 时是真的生成 HTML 还是发大量文字?"→ 发现 SKILL.md 没明确每触发词的 HTML 决策

### Added
- **SKILL.md + 备忘录.html 加"触发词 → HTML 生成对照表"**(最高优先级)
  - 28 个触发词明确分类:
    - ✅ 必须生成 HTML(9):搜备忘/查备忘/看备忘/按时间搜备忘/看提醒/查已提醒备忘/查心愿/查打卡/查情绪
    - 🟡 过程型 HTML(4):完成心愿(完成打卡)/心愿排期/备忘改分类(批量)/备忘录同步
    - ❌ 不生成 HTML(15):记备忘/改备忘/删备忘/备忘改分类(单条)/备忘改子分类/记提醒/设提醒/记心愿/删心愿/改心愿/记打卡/删打卡/改打卡/记情绪/删情绪/改情绪
  - 含 AGENT 决策流程图 + 统计表
- **`tests/test_html_trigger_coverage.py`** 文档裂缝守护
  - 61 个参数化测试(每个触发词 2 个 + 表行数 + 标志完整 + 合计 + L157/L161 一致性)
  - 改 SKILL.md 时自动验证任何遗漏

### Tests
- 全量:143/143 pytest 通过(82 → 143 · +61)
- 文档测试守护:防止未来 SKILL.md 改时遗漏任何触发词

---

## [1.0.6] · 2026-07-24

> **改进**(语义化版本规则):命名规则 + 输出目录规则 同步到通用手册(跨 Skill)
> 来源:用户问"其他 AGENT 看哪个文件知道命名规则?"→ 发现 v1.0.5 只写在备忘录私有文档里,其他 Skill 看不到

### Changed
- **《预置HTML并注入数据指导手册》§4 加 "输出目录与命名规范" 子段**(跨 Skill 通用)
  - 完整规则:`HTML_DIR = DATA_DIR / f"{SKILL_HTML_NAME}_html"`
  - 完整命名:`<command_name>_<YYYYMMDD>_<HHMMSS>[_<N>].html`
  - 3 个 Skill ASCII 短码映射表(备忘录=memo · 卡路里=calorie · 居家管家=home)
- **案例 03 加 "原则 6: 文件命名与输出目录规范"**(承接通用手册)
- 行为变化:无(纯文档)

---

## [1.0.5] · 2026-07-24

> **改进**(语义化版本规则):HTML 输出目录与 DB 同级 + 命名规则明确化
> 来源:用户提问"目录规则和命名规则是什么?手册里有没有?"→ 发现手册未规定,做第一性改造

### Changed
- **HTML 输出目录**(承袭第一性:HTML 是 DB 的快照视图)
  - 旧:`<skill_dir>/output/`(写死,与 DB 分离)
  - 新:`DB_PATH.parent / f"{SKILL_HTML_NAME}_html"`(与 DB 同级)
  - 例子:`/mnt/d/.db/memo_html/` · `D:/.db/memo_html/` · `自定义路径/memo_html/`
  - 好处:HTML 跟着 DB 走 · 跨平台 fallback 一致 · 多 skill 共用 SKILLS_DB_PATH 时自动隔离
- **删除旧 `备忘录/output/` 目录**(用户主动要求)· 119 个旧 HTML 文件清空
- **命名规则明确化**(写入 `_shared/injector.py` docstring + 《预置HTML并注入数据指导手册》§7)
  - 格式:`<command_name>_<YYYYMMDD>_<HHMMSS>[_<N>].html`
  - `<N>` = 冲突保护(同秒多次生成自动 `_2` / `_3` 后缀)
- **SKILL.md + 备忘录.html "HTML 交付规范"段加目录 + 命名规则子段**

### Added
- **冲突保护**(`write_output` 写文件前 `Path.exists()` 检查,自动 `_2` / `_3`)
- **`SKILL_HTML_NAME = "memo"`**(`memo_render.py` 顶部常量,避免中文路径跨平台编码问题)
- **`_get_html_output_dir()` 函数**(动态计算输出目录,与 DB_PATH 同步)
- **`.gitignore` 加 `memo_html/`**(防 SKILLS_DB_PATH 设到仓库内误跟踪)

### Tests
- `tests/test_shared_injector.py` 加 5 个用例:
  - `TestWriteOutputCollisionProtection` 3 个(冲突保护 / 3 次 / 不同 ts)
  - `TestNamingRuleContract` 2 个(格式 / 5 个命令名匹配)
- `tests/test_shared_injector.py` 加 2 个 `TestMemoHtmlOutputDir`(目录在 DB_PATH.parent / 自动 mkdir)
- `tests/test_render.py` 修复 `OUTPUT_DIR` 引用改为 `_get_html_output_dir()`
- 全量回归:82/82 pytest 通过(75 → 82 · +7)

---

## [1.0.4] · 2026-07-24

> **bug fix**(语义化版本规则):过程型 HTML 默认未勾选(正向操作第一性)
> 来源:用户反馈"心愿完成 HTML 默认未选中,用户选中哪个就完成哪个"

### Changed
- **`wish-complete` HTML 默认未勾选**(过程型 HTML 正向操作)
  - 旧:`items[].selected = True`(全勾) → 用户被迫反向操作(在已勾清单里删勾),反直觉且易误完成
  - 新:`items[].selected = False`(全未勾) → 用户主动勾要完成的(正向表达意图),精准
  - **第一性**:过程型 HTML 的价值是让用户主动表达意图
- **HTML 模板 `templates/wish_complete.html`** 调整
  - `renderWish(w)`:删除 `const cls=w.selected?'':'off'`
  - `<article>` 不再根据 selected 加 .off class(默认 normal 样式)
  - 用户切换 checkbox 时,JS event handler 仍动态加 .off(opacity:.5)
  - 原因:默认未勾的卡片若加 .off 会视觉误导(看起来"已禁用")

### Tests
- `tests/test_wish_complete.py` 加 3 个用例:
  - `test_default_selected_false_v1_0_4` 默认 selected=False
  - `test_html_default_unchecked_v1_0_4` HTML 注入数据验证
  - `test_html_renderwish_template_no_checked_default` 模板代码层验证
- 全量回归:75/75 pytest 通过(原 72 + 新增 3)

---

## [1.0.3] · 2026-07-24

> **bug fix**(语义化版本规则):纠正 v1.0.2 过度禁止 — 用户确认 `<media>` 与浏览器打开应并行
> 来源:用户提问"为什么禁止 AI 用 Chrome 打开?"→ 我承认 v1.0.2 措辞过度,无文档明文规定

### Fixed
- **HTML 交付规范段 v1.0.3 修订**(承袭用户决策)
  - **删除**:v1.0.2 的"❌ AI 主动 subprocess/webbrowser 唤起浏览器(绝对禁止)"
  - **新增**:"强烈推荐:与 `<media>` 并行,同时用 Chrome 等系统默认浏览器打开"
  - 理由:`<media>`(IDE 内嵌)与 Chrome(系统浏览器)是**两个独立通道**,并行不冲突
  - 用户场景:IDE 预览 + Chrome 窗口同时打开,各自发挥长处
  - **保留禁止项**:只输出路径文字 / 内联读 HTML 塞进对话 / 提示绕过 `<media>`
- 行为变化:无功能改动,纯文档
- 历史说明:v1.0.2 是过度禁止,v1.0.3 是用户决策版

---

## [1.0.2] · 2026-07-24

> **bug fix**(语义化版本规则):补 HTML 交付规范文档裂缝
> 来源:用户提问"是否发送文件/Chrome 打开?"→ 发现 SKILL.md 没承袭《预置HTML并注入数据指导手册》§4 + §9 的 `<media>` 交付协议

### Fixed
- **SKILL.md + 备忘录.html 加《HTML 交付规范》段**(最高优先级,与"HTML 同步"同级)
  - **必须**:`<media src="..." type="file" />` 交付(5 个 HTML 模板生成后)
  - **禁止**:自动唤起 Chrome(webbrowser/subprocess) / 只输出路径 / 内联展示 / 提示"用 Chrome 打开"
  - **出处**:《预置HTML并注入数据指导手册》§4 + §9
  - 5 个触发词场景分别说明交付协议(查询类 + sync + 3 个过程型向导)
- 行为变化:无(纯文档)

---

## [1.0.1] · 2026-07-24

> **bug fix**(语义化版本规则):向下兼容,修 wish-complete 默认筛条件过严的回归第一性 bug
> 来源:实际用户场景触发(AGENT 调用 wish-complete 返回 0 条,但 search -c 心愿 有 20 条)

### Fixed
- **`wish-complete` 默认筛条件过严**(过程型 HTML 第一性回归)· `script/memo_cli.py:wish_complete`
  - 旧 SQL(过严):
    ```sql
    WHERE category='心愿'
      AND id NOT IN (SELECT note_id FROM reminders)   -- 排除有提醒的心愿
      AND (due IS NULL OR due < date('now','localtime'))   -- 排除未来排期
    ```
  - 新 SQL(回归第一性):
    ```sql
    WHERE category='心愿'   -- 只按分类,余下让用户在 HTML 里勾选
    ```
  - **第一性**:**过程型 HTML 的核心价值就是让用户在 UI 决定,CLI 不应该预设决策**。
  - 影响:用户有 20 条心愿 → 旧默认推 0 条 → 新默认推 20 条
  - 加 `--only-overdue` flag(显式 opt-in):保留 v1.0.0 默认行为,但需要用户显式选
  - `--all` 标记 deprecated(等同默认):仅保留向后兼容

### Deprecated
- `--all` flag(等同默认行为,保留仅作向后兼容提示)

### Tests
- `tests/test_wish_complete.py` 13 用例 → 关键回归测试:
  - `test_default_lists_all_wishes` 默认列 3 条(覆盖未来/未排期/过期)
  - `test_only_overdue_lists_unset_and_overdue` 显式 flag 只列 2 条(未排期+过期)
  - `test_wish_with_reminder_still_listed` ⭐ 关键:心愿绑提醒后默认仍列出
  - `test_only_overdue_with_reminder` `--only-overdue` 也不排除有提醒的心愿
  - `test_ids_and_only_overdue_mutually_exclusive` 新互斥规则
- 全量回归:72/72 pytest 通过(原 68 + 新增 4)

---

## [Unreleased]

### Added
- (暂无)

### Changed
- (暂无)

### Deprecated
- (暂无)

### Removed
- (暂无)

### Fixed
- (暂无)

### Security
- (暂无)

---

## 2026-07-23 之前 · 历史变更


### Added
- **`模板HTML并注入数据/_shared/injector.py`** · 跨 Skill 共享 HTML 注入器
  - 3 个公共函数:`inject_html` / `write_output` / `render`
  - 占位符唯一性校验(数量 ≠ 1 → raise ValueError)
  - `</` 转义防 `<script>` 提前闭合
  - 出处引用《预置HTML并注入数据指导手册》§8
  - 10 个新 pytest 用例(占位符/转义/UTF-8/进程间 import)
  - commit `5378005`

### Changed
- `备忘录/script/memo_render.py` 删除自写 `_inject` / `_write_output`
  - 改为 `from injector import inject_html, write_output`
  - 文件行数:100 → 95
  - 跨 Skill 影响:卡路里/居家管家将来可同样 import

---

## 2026-07-23 之前 · 历史变更

详见 `git log -- 备忘录/`:
- `1d48917` 备忘录：查询类功能接入 HTML 模板
- `322a24c` 重构: 备忘录标点规范化 + 命令命名统一
- `5512fff` 杂务: 批量同步 14 个现有技能 HTML 镜像
- `e47bcfb` 修复: 备忘录CLI修复Windows stdout GBK编码崩溃
- `4aad6cc` 🐛 修复: 飞书心愿查重改三步走,防止重复 task 创建

---

## 备注

### 归档周期

- **[1.0.0 - 2026-07-24]** 已发布(本次 9 个 commit 闭环)
- 后续变更累积到 `[Unreleased]`,再次稳定时升 `[1.x.y]`
- 语义化版本:
  - 1.0.1 = bug fix(向下兼容)
  - 1.1.0 = 新功能(向下兼容)
  - 2.0.0 = 破坏性 CLI 改动(签名/参数/JSON 三段式)

### 引用规则

本文件格式参考 [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-CN/1.1.0/):
- **Added** 新增的功能
- **Changed** 已有功能的变更
- **Deprecated** 已弃用(本项目暂时无)
- **Removed** 删除的功能(本项目暂时无)
- **Fixed** 任何 bug 修复
- **Security** 安全漏洞修复(本项目暂时无)
- 每个变更关联 commit SHA,便于 review
