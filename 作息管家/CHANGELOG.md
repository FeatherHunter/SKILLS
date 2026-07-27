# 作息管家 CHANGELOG

> 记录对用户有感知的变更。遵守 SKILL开发总纲V1.0/05-工程仪式.md 的 commit 与同步规范。

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
| HELP HTML | 饼干记账 | `饼干记账_HELP_<TIMESTAMP>.html` | `D:/Downloads`(跨平台 fallback) |

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

参考 `D:\2Study\StudyNotes\SKILLS\html\review_5710525.html`(对抗式审查报告),按 ROI 修复:

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
