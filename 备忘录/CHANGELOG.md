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
