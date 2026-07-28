# Spec: 饼干记账 Skill 对齐《SKILL 开发总纲 V1.0》

Status: ready-for-agent
Created: 2026-07-28
Slug: align-biscuit-accountant-to-skill-dev-manual-v1

## Problem Statement

本地记账 Skill「饼干记账」当前虽然 80% 落地《SKILL 开发总纲 V1.0》的关键规则（HTML-First / 场景资产 / 5 状态 fallback / 占位符注入安全 / 路径冲突保护），但经过 `grill-with-docs` 十轮强制对照，仍有 14 项结构性与一致性偏差未解决，外加 1 项 HTML 文件编码隐患。问题集中在三类：

1. **§02 五层骨架不完整** —— 缺少 `validators.py`（规则层），硬规则散落 db.py 与 argparse 层；§02 自检清单永远无法 pass。
2. **§05 测试 / FAT 缺失** —— 无独立 `tests/` 目录，无 FAT 记录，无 `Tested-By:` commit；commit 前未跑 fresh agent 黑盒测试。
3. **§04 §07 声明漂移** —— SKILL.md / html_paths.py / render_help.py / scenarios.json 多处事实源不一致；HELP 路径在 3 个位置描述 3 个不同文件名；HTML 镜像手工同步 30KB 漂移风险。

此外，HTML 输出文件被 Windows 老旧工具（记事本 / PowerShell 5.1）按 GBK 误判打开导致显示乱码 —— 这虽是 BOM 缺失，但与 §04 §原则 6「HTML 镜像必同步」+ §05 §「工程仪式」一并纳入。

## Solution

把 14 项偏差收敛为一份**端到端 spec**，验收接缝 = 一次 `bill_inject.py <query_type> [args]` 的完整调用（最高级 seam；与 §02 + §04 单文件离线 + §05 验收一致）。验收只看最终 HTML：含正确 `<title>` / `<script id="payload">` / 5 状态 fallback / 移动端适配 / `escapeHTML()` 守卫 / 占位符注入安全；所有 9 类 query_type + HELP + 空数据 + 错误路径都跑通 FAT。

新增/补强模块清单（不写文件路径，写接缝）：
- 新增 `validators.py` 集中硬规则
- 新增 `tests/` 目录四件套（conftest / test_validators / test_render / test_payloads）
- 新增 `docs/adr/0002-utf-8-bom-for-html-output.md`
- 新增 `references/categories-mapping.md`（如与 config-cookie-accounting.ts 桥接）
- 改 SKILL.md：显式声明走 §04 原则 12.A / 12.B；HELP 行补全 4 条唤醒词
- 改 html_paths.py：HELP 路径名统一为 `饼干记账_HELP_`（§12.B 标准）
- 改 render_help.py：使用统一 HELP 路径
- 改 references/scenarios.json：`_meta.help_wake_words` 与 SKILL.md 同步 4 条
- 改 .gitignore：补 `*.bak`

## User Stories

1. As a 个人记账用户, I want Skill 自带的查询 HTML 在浏览器与 Windows 老旧工具（记事本 / PowerShell ISE）中都能正确显示中文, so that 我不会再看到乱码怀疑 Skill 损坏。
2. As a 个人记账用户, I want `记支出 -35 餐饮/外卖` 后再 `查今天`, so that 我能立刻看到新记录出现在今日摘要里（无需手动刷新或重启）。
3. As a 个人记账用户, I want `查最近 20` 在数据为空时显示一个友好的「暂无记录」卡片, so that 我不会以为是 Skill 坏了。
4. As a 个人记账用户, I want `饼干记账 HELP` 输出 HTML 而非文本, so that 我可以在手机上复制 prompt 直接贴给 AI。
5. As a 个人记账用户, I want `查分类` 时能筛三级分类（餐饮 / 外卖 / 午餐）, so that 我能精确回顾某具体品类的支出。
6. As a 个人记账用户, I want `看对比` 自动选上个月作为对比期, so that 我不用每月手填日期。
7. As a 个人记账用户, I want `看月度` 在跨年时（如 `2025-12` vs `2026-01`）正确显示完整月, so that 我不会因月底跨年而漏算。
8. As a 个人记账用户, I want `做统计` 给出首末时间、总笔数、记账天数, so that 我能衡量自己的记账坚持度。
9. As a 个人记账用户, I want `改记录` 时只能改白名单字段（category / amount / note / time / account / ledger / currency），其他字段（id / created_at）无法被 CLI 参数覆盖, so that 我的账本不会被任意篡改。
10. As a 个人记账用户, I want `记支出` 校验金额不为零, so that 不会出现「餐饮 0.00」这类无效记录污染统计。
11. As a 个人记账用户, I want `拍账单`（OCR / 图片识别）后预填分类建议, so that 我可以一键确认无需手输分类心法。
12. As a 个人记账用户, I want 数据库位置解析 fallback 到 `D:\.db\` 在没设环境变量时也能跑, so that 我换电脑不用配置环境。
13. As a 个人记账用户, I want 同秒触发同一查询时 HTML 文件名追加 `_2` / `_3` 后缀而不覆盖, so that 我能保留历史快照对比。
14. As a 个人记账用户, I want HTML 文件含 `<meta charset="UTF-8">` + BOM, so that 双击直接用浏览器打开能正确渲染。
15. As a 个人记账用户, I want HTML 在手机端（≤640px）自动调整 KPI grid / compare grid / record 列宽, so that 我在地铁上用手机也能看清。
16. As a 个人记账用户, I want `饼干记账_HELP_<TS>.html` 这个文件名固定（不是 `能力速查_<TS>.html`）, so that 我能用 grep 一抓抓出所有历史 HELP 页。
17. As a 个人记账用户, I want SKILL.md 里写的 HELP 唤醒词与 `scenarios.json._meta.help_wake_words` 完全一致（4 条）, so that 我不会触发未在 SKILL.md 登记的唤醒词导致 AI 行为漂移。
18. As a 个人记账用户, I want 4 条 HELP 唤醒词都能在 fresh agent 测试里被正确路由到 `render_help.py`, so that 我不会因为唤醒词漏注册而拿到 fallback 文本回执。
19. As a 开发者, I want `scripts/validators.py` 集中持有所有硬规则（分类白名单 / 金额校验 / 字段类型 / 默认值）, so that 改一处就改全部（DRY），不再散在 db.py 与 record_bill.py 里。
20. As a 开发者, I want `scripts/validators.py` 错误信息含「字段名 + 当前值 + 期望值 + 怎么修」, so that 用户能自助修输入而不是反复来问。
21. As a 开发者, I want `tests/conftest.py` 提供共享 fixture（临时 DB / 临时 HTML_DIR / sample_bills）, so that 每个测试文件不必重写样板。
22. As a 开发者, I want `tests/test_validators.py` 覆盖「金额=0 拒绝 / 金额=NaN 拒绝 / 分类不在白名单拒绝 / 时间格式错误拒绝」, so that 硬规则回归有迹可循。
23. As a 开发者, I want `tests/test_render.py` 覆盖「9 类 query_type + 空数据 + 错误 CLI 输出」均生成合法 HTML, so that 模板改动可回归。
24. As a 开发者, I want `tests/test_payloads.py` 覆盖「`</` 转义成 `<\/` 防 XSS」「占位符唯一性校验」「`escapeHTML()` 函数单元测试」, so that 注入层不会引入新漏洞。
25. As a 开发者, I want commit 时自动跑 fresh agent 黑盒测试（FAT）并把 `Tested-By: fresh-agent-v1` 写进 commit message, so that 每个改 SKILL.md 的 commit 都过一道外部审计。
26. As a 开发者, I want SKILL.md 在 §📌 输出位置 章节显式写「本 Skill 走 §04 原则 12.A / 12.B」字样, so that 后续读者不会误以为可随意改 HTML 路径名。
27. As a 开发者, I want SKILL.md 与 `饼干记账.html` 同 commit 同步（依赖手工 + CI grep 校验作为临时方案）, so that HTML 镜像不会漂移。
28. As a 开发者, I want `references/scenarios.json` 的 `_meta.help_wake_words` 是 4 条且与 SKILL.md 一致, so that 任何唤醒词增删都从事实源驱动。
29. As a 开发者, I want `config-cookie-accounting.ts` 与本 Skill 的分类体系桥接到 `references/categories-mapping.md`, so that SkillBoard 数据层视图与本 Skill 视图不会冲突。
30. As a 开发者, I want `.gitignore` 排除 `*.bak` 一次性备份, so that 仓库不会带历史包袱。

## Implementation Decisions

1. **测试接缝（最高级 seam）**: 唯一接缝 = `bill_inject.py <query_type> [args]` 端到端调用；不拆 CLI JSON 与模板渲染为两层 seam（避免 §04 §原则 5-7 单文件离线被破坏）。
2. **新增 `validators.py`**（§02 第 ③ 规则层）: 集中持有分类白名单 / 金额校验（非零、有限数）/ 字段类型 / 默认值；导出 `validate_amount`、`validate_category`、`validate_record` 三个纯函数。
3. **`record_bill.py` argparse 与 db.py 旧校验**: 在过渡期保留；新增 `validators.py` 后，`record_bill.py` 改为调用 `validators.py` 而非内联 if。
4. **`db.py` 新增 CHECK 约束**: `amount != 0`、`currency IN ('CNY', '人民币')`、`ledger NOT NULL`；迁移脚本 `scripts/migrations/add_bills_check_constraints.py` 支持 `--dry-run` + `--rollback`。
5. **`tests/` 目录**: 与 §05 §验收模板对齐——`conftest.py` / `test_validators.py` / `test_render.py` / `test_payloads.py`；旧 `scripts/test_db.py` 与 `scripts/run_tests.py` 删除。
6. **FAT 协议**: 每次 commit 写 `Tested-By: fresh-agent-v1`；本 spec 第一次验收跑通后首次填 `Tested-By:`；如失败改 SKILL.md 而非改正（§05 钩子 ⑥）。
7. **SKILL.md 显式声明**: 在 §📌 输出位置 章节加「本 Skill 走 §04 原则 12.A / 12.B」字样；HELP 路径写明 `饼干记账_HELP_<YYYYMMDD>_<HHMMSS>[_N].html`（§12.B 标准）；数据查询路径写明 `<command_zh>_<YYYYMMDD>_<HHMMSS>[_N].html`（§12.A 标准）。
8. **HELP 路径名收敛**: `html_paths.py` 把 `help` 映射从 `饼干记账_HELP` 改为 `饼干记账_HELP`（保留 §12.B 标准命名）；`render_help.py` 的 `default_output_path()` 改用 `html_path("饼干记账_HELP")`。
9. **`scenarios.json._meta.help_wake_words`**: 与 SKILL.md L77 同步为 4 条——`饼干记账 HELP` / `饼干记账 帮助` / `查帮助` / `能做什么`。
10. **HTML BOM 修复**: `bill_inject.py` 与 `render_help.py` 写文件改 `encoding="utf-8-sig"`；`record_bill.py` 顶部加 `sys.stdout.reconfigure(encoding="utf-8")` 防 cp936 污染；归档到 ADR-0002。
11. **`.gitignore`**: 补一行 `*.bak`；清理历史遗留的 2 个 `.bak` 文件（不删，工作区外归档）。
12. **`config-cookie-accounting.ts`**: 不删（跨工具边界未澄清）；新增 `references/categories-mapping.md` 桥接 9 L1 ↔ 10 L1；SKILL.md 加一节「与其他工具的边界」声明此文件为 SkillBoard 数据层视图，独立维护。
13. **`categories-mapping.md`**: 桥接表（餐饮↔餐饮、购物↔居家+穿着、出行↔出行、娱乐↔玩乐、通讯↔居家、医疗↔健康、教育↔学习、住房↔居家、其他↔其他）；标记「`config-cookie-accounting.ts` 视为本 Skill 的 legacy 视图，权威分类体系以 `categories.md` 为准」。
14. **ADR-0002**: `docs/adr/0002-utf-8-bom-for-html-output.md` 记录 BOM 修复决策（防御 Windows 老旧工具 GBK 误判；不影响浏览器，浏览器认 `<meta charset="UTF-8">`）。
15. **架构形态**（决策性强项）: 保持「数据层 db.py + 操作层 analyze.py + 规则层 validators.py + 接口层 record_bill.py + 文档层 references/+templates/」五层；ADR-0002 删除「规模分档逃生口」，无任何 Skill 例外（与 ADR-0002 同步）。
16. **不实施 FAT 自动化**: 本 spec 验收要求「提交时手跑一次 fresh agent」；自动化 CI 留作未来 spec。
17. **不重写 `饼干记账.html` 镜像自动生成器**: 本 spec 仅要求 CI grep 校验（关键章节一致性），自动生成器留作下一份 spec。
18. **不删 `config-cookie-accounting.ts`**: 与第 12 项一致；如未来澄清为废弃，再独立 spec 处理。

## Testing Decisions

1. **好测试的判据**: 只测外部行为（HTML 文件包含 `<title>` 正确 + `<script id="payload">` 唯一 + 5 状态 fallback 命中 + 移动端 CSS 命中）；不测内部函数（`_find_db_path`、`html_name` 的 `_N` 冲突保护算法）。
2. **测试模块清单**:
   - `tests/conftest.py` —— 共享 fixture：临时 SQLite DB（含 30 条 sample_bills 含空数据 / 跨月 / 跨年）、临时 HTML_DIR、临时 CLI 子进程 wrapper
   - `tests/test_validators.py` —— 单元：`validate_amount(-35)` 通过 / `validate_amount(0)` 拒绝 / `validate_amount(float('nan'))` 拒绝 / `validate_category("餐饮/外卖/午餐")` 通过 / `validate_category("不存在")` 拒绝
   - `tests/test_render.py` —— 集成：跑 `bill_inject.py <9 种 query_type>` 校验输出 HTML 含 `<title>` / `<script id="payload">` / `<meta charset="UTF-8">` / 含 BOM（`bytes[0:3] == b'\xef\xbb\xbf'`）
   - `tests/test_payloads.py` —— 注入安全：`</` 转义成 `<\/` / 占位符 `<!--INJECT-DATA-->` 唯一 / `escapeHTML()` 函数单元 / `breakdown` 命令的 donut SVG 渲染非空
3. **先验测试**: 仓内已存在 `scripts/test_db.py` 与 `scripts/run_tests.py` 21 个用例，可作为先验；本 spec 验收时把它们迁到 `tests/` 下重写（如命名规范冲突则重写）。
4. **FAT（fresh agent 黑盒）测试协议**: 每次 commit 前由人跑——给 fresh agent 一段「用户口吻」的唤醒词（如「帮我看下今天花了多少」「`饼干记账 HELP`」），检查 fresh agent 是否正确路由到 `bill_inject.py` 或 `render_help.py` 并生成 HTML（不调代码生成）。FAT 结果写进 commit message 的 `Tested-By:` 字段。
5. **HTML BOM 测试**: 在 `tests/test_render.py` 加 `assert output_path.read_bytes()[:3] == b'\xef\xbb\xbf'`。
6. **回归保护**: 删 `scripts/test_db.py` 与 `scripts/run_tests.py` 后统一用 pytest 入口；CI 缺失下用 `python -m pytest tests/` 本地手跑。

## Out of Scope

1. **不实现 FAT 自动化 CI**：本 spec 仅要求「提交时手跑一次」；自动化 FAT runner（每次 commit 自动跑 fresh agent + 校验）留作未来 spec。
2. **不重写 `饼干记账.html` 镜像自动生成器**：仅用 CI grep 校验（关键章节对齐）作为临时方案；自动生成器（含 build_skill_html_mirror.py）留作下一份 spec。
3. **不删 `config-cookie-accounting.ts`**：跨工具边界未澄清，本 spec 仅做桥接文档。
4. **不重写分类体系**：本 spec 仅在 `references/categories-mapping.md` 做桥接；如有冲突需重写，留作单独 spec。
5. **不动 SKILL.md 第一段**（领域描述 + 强制性规定）：本 spec 仅修改 §📌 输出位置 章节与 §唤醒词总表 + §使用流程 步骤 6 的 HTML 工作流路径说明；其他章节不在本 spec 范围。
6. **不动场景资产 91 个场景**：本 spec 仅修改 `_meta.help_wake_words` 数组；具体场景增删留作单独 spec。
7. **不做数据库 schema 大改**：本 spec 仅新增 CHECK 约束；任何字段类型 / 索引 / 表拆分（如 ledger 分账户、account 拆多账户）不在范围。
8. **不做浏览器侧 JS 框架升级**：保持单文件离线 HTML + 原生 SVG，不引 Chart.js / Vue / React。
9. **不做移动端 PWA / 离线缓存**：超出本 spec 范围。

## Further Notes

1. **本 spec 的对话来源**: 由 `grill-with-docs` 强制对照《SKILL 开发总纲 V1.0》十轮决策清单固化（决策项 1-14）+ 中途的 HTML BOM 修复（决策项 15）合并而成。
2. **接缝决策依据**: §02 自检清单要求「所有 Skill 必须全跑，无规模分档」；§04 §原则 5-7 要求单文件离线；§05 §验收要求「commit 前必跑 FAT」；三者合一指向「端到端 seam + FAT」。
3. **优先级建议**: 落地顺序建议为 ② validators.py → ⑤ tests/ → ④ db.py CHECK → ⑦⑧ SKILL.md 显式声明 + HELP 路径统一 → ⑨ scenarios.json 同步 → ⑩ BOM + ADR-0002 → ⑪ .gitignore → ⑫⑬ categories-mapping.md → ⑥ FAT 协议 → ⑳ record_bill.py 改 validators 调用。
4. **历史遗留**: `scripts/test_db.py` 与 `scripts/run_tests.py` 是同一作者的两次实现，本 spec 验收时合并到 `tests/` 后删除原文件；`.bak.20260723_*` 两个备份文件归档到 `backups/` 而非删除（一次性）。
5. **追踪与依赖**: 发布到 `.scratch/align-biscuit-accountant-to-skill-dev-manual-v1/` 目录下，spec.md 即本文件；落地时按实现决策 #3 顺序逐项推进，每完成一项新增 `.scratch/<feature>/issues/<NN>-<slug>.md` 编号追踪。
6. **不属于本 spec 但建议留意**: `__pycache__/` 9 个新文件 (2026-07-27) — git 已排除但工作区残留；`backups/` 9 个 CSV 迁移产物 — 不进 git 但占空间，可考虑定期压缩归档。