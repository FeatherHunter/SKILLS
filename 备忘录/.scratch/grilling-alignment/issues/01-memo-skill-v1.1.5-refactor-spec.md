---
triage: ready-for-agent
title: 备忘录 Skill v1.1.5 整体重构(规范合规化)
status: open
created: 2026-07-28
priority: high
grilling: R1+R2+R3+R4 (23 决策已凝固)
commit: bb7c64b(B-0 决策入库)
issue: 01
labels: [needs-agent, ready-for-agent, refactor, spec-compliance]
---

## Problem Statement

备忘录 skill 当前 v1.1.4 已功能完整(174 pytest 通过 / 29 唤醒词覆盖 / 14 项 §07 自检全 ✅),但与 `SKILL开发总纲V1.0` 比对存在 **50 项规范差距 + 30+ 项不明确**,具体表现为:

1. **术语不统一** — SKILL.md 用"触发词"(91 处)但总纲用"唤醒词";"用例"和"场景"混用;"4 元组"(触发词结构)与"4 部分"(prompt 模板结构)数字撞车导致歧义;"HTML 镜像 / 用户手册 / HELP HTML" 同一个文件三个名字。AI agent 阅读时容易混淆。
2. **必备结构文件缺失** — SKILL.md 无 YAML frontmatter;无 `CONTEXT.md` 术语表;无 `docs/adr/`;无 `README.md`;无 `pytest.ini`;无 `.scratch/` 工作目录。自动化工具无法消费。
3. **内容噪音** — `_meta.json` 自 v1.0.0 起未跟进,落后 14 个版本;SKILL.md L927 与 L1034 `## 参考文档` 章节重复;`reference/` + `references/` 双目录并存;`scenarios.yaml` L21+L23 重复 `scenarios:` 键(后者覆盖前者);CHANGELOG v1.1.0 L538 "106/106 pytest 通过" 数字与现状 174 不符。
4. **工程仪式缺失** — FAT 协议从未跑(CHANGELOG L155 "待跑 · 用户 #4");commit 无 `Tested-By` 字段;SKILL.md 无"改动前 3 问"段;无豁免矩阵记录。
5. **架构合规部分缺失** — 5 层自检清单覆盖不全;跨 Skill 路由声明不完整(仅"备忘改分类批量"声明)。

**用户(技能维护者)的真实痛点**: skill 功能 OK 但"不规范",后续 onboarding / AI agent 接入 / 自动化脚本消费都有摩擦,且每次新决策都缺乏可审计的归档。

## Solution

执行 v1.1.5 整体重构,将 4 轮 grilling(R1+R2+R3+R4)产出的 **23 个决策**分阶段 commit 落地:

| 阶段 | 决策数 | 主要动作 | 落地形式 |
|---|---|---|---|
| **B 内容一致性** | 13 | 术语统一(7 处)/ 内容清理(双目录合并 / 章节去重 / YAML 修复 / `_meta.json` 升版) | 4 commit |
| **A 结构合规** | 5 | 6 个新文件补齐(YAML frontmatter / `CONTEXT.md` / `README.md` / `pytest.ini` / `docs/adr/` / `.scratch/` 范式)+ `AGENTS.md` 升级 | 1 commit |
| **D 工程仪式** | 5 | `ADR-0005` 豁免矩阵 + `Tested-By` 字段 + SKILL.md 3 问段 + `.githooks/commit-msg` 格式检查 | 2 commit |

**已完成**: 决策入库 commit `bb7c64b`(B-0 · 13 文件 / +2913 行)。
**待执行**: 7 个 commit(分阶段执行,每个 commit 都通过 174 pytest 守护)。
**总验收**: `verify.ps1` R5 后完整化(当前是占位版)+ 174 pytest 全过 + 0 现有功能回归。

**核心承诺**: 重构不改用户可见行为(CLI 子命令 / HTML 镜像 / 29 唤醒词响应),只改"底层合规层"。

## User Stories

### 备忘录主用户(随手记录者)

1. As a 备忘录主用户, I want 用口语"记备忘"立刻触发记录, so that 不需要学命令格式。
2. As a 备忘录主用户, I want 按时间搜备忘(今天 / 昨天 / 本周 / 上周 / 本月 / 上月), so that 不用记具体日期。
3. As a 备忘录主用户, I want 给备忘打分类(工作 / 生活 / 学习 / 灵感), so that 后续检索清晰。
4. As a 备忘录主用户, I want 给分类加子分类(工作 → 项目A / 项目B), so that 层级结构清晰。
5. As a 备忘录主用户, I want 改备忘内容(发现错别字), so that 修正过去记录。
6. As a 备忘录主用户, I want 删备忘(私密 / 误录), so that 隐私和整洁。
7. As a 备忘录主用户, I want 改备忘的分类(事后归类), so that 重新组织。
8. As a 备忘录主用户, I want 批量改分类(同一项目下多条都改), so that 节省操作。
9. As a 备忘录主用户, I want 设提醒(到期通知), so that 不忘事。
10. As a 备忘录主用户, I want 查已提醒过的备忘, so that 复盘通知历史。
11. As a 备忘录主用户, I want 记心愿(未来要做的), so that 愿望不丢。
12. As a 备忘录主用户, I want 心愿排期(什么时候做什么), so that 愿望可执行。
13. As a 备忘录主用户, I want 完成心愿(标记完成), so that 知道做到没。
14. As a 备忘录主用户, I want 查打卡(连续 / 间断), so that 习惯追踪。
15. As a 备忘录主用户, I want 记情绪(开心 / 焦虑 / 平静 等), so that 情绪复盘。
16. As a 备忘录主用户, I want 查情绪趋势, so that 了解情绪周期。
17. As a 备忘录主用户, I want 备忘录数据跨设备同步, so that 手机电脑都能用。

### AI agent / opencode(技能消费者)

18. As an AI agent, I want 读 SKILL.md 顶部 YAML frontmatter 立刻知道 skill 名称 / 版本 / 状态, so that 不读全文就判断"这 skill 是否启用"。
19. As an AI agent, I want 读 `CONTEXT.md` 知道备忘录 skill 的术语定义(唤醒词 / 场景 / 4 元 / 4 段 prompt 等), so that 解析用户输入时不歧义。
20. As an AI agent, I want 读 `docs/adr/0001-0005` 知道所有历史决策与依据, so that 不重复决策 / 不违反既有约束。
21. As an AI agent, I want 通过 29 个场景的稳定 prompt 字段触发 skill, so that 不暴露 CLI / DB / 路径细节给用户。
22. As an AI agent, I want 命中"备忘录 HELP"唤醒词立刻得到可视化 HTML 手册, so that 不用口述。
23. As an AI agent, I want HTML 镜像(`备忘录.html`)与 SKILL.md 同 commit 同步, so that 文档永远不漂移。
24. As an AI agent, I want 模板的 4 状态 fallback(正常 / 空 / 缺数据 / 错误)覆盖所有 5 个模板, so that 出错时知道是哪种状态。

### 自动化工具 / 脚本消费

25. As an 自动化脚本, I want 读 `_meta.json` 立刻得到版本号, so that 不解析 SKILL.md frontmatter。
26. As an 自动化脚本, I want `pytest.ini` 6 项配置(testpaths / python_files / classes / functions / addopts / strict-markers), so that pytest 不扫错文件、不漏测。
27. As an 自动化脚本, I want `.githooks/commit-msg` 检查 commit 全中文格式, so that commit 历史风格一致。
28. As an 自动化脚本, I want `.githooks/pre-commit` 自动还原 `备忘录.html`(测试副产物不入 commit), so that 工作区永远干净。
29. As an 自动化脚本, I want `scripts/` 下 7 个 Python 模块的依赖图清晰(5 层骨架), so that 知道在哪一层加功能。

### 新人 onboarding(技能维护新手)

30. As a 新人维护者, I want 读 `README.md` 5 章节(这是什么 / 何时使用 / 快速开始 / 文件清单 / 状态)快速上手, so that 不用读完 1038 行 SKILL.md。
31. As a 新人维护者, I want `AGENTS.md` 25-30 行精炼指令(项目定位 / 路径约定 / 决策位置 / commit 格式 / HTML 镜像约定), so that 任何 agent 进入自动读。
32. As a 新人维护者, I want 读 `.scratch/grilling-alignment/spec.md` 看整轮重构的来龙去脉, so that 理解"为什么改成这样"。
33. As a 新人维护者, I want 跑 `verify.ps1` 一键验证 174 pytest 通过 + 结构合规, so that 不需要手动 5 个步骤。

### 技能维护者(长期演进)

34. As a 技能维护者, I want 任何改动前答"影响哪些文件 / 数据迁移 / 回滚方案"3 问(SKILL.md 顶部段落), so that 不破坏现有功能。
35. As a 技能维护者, I want 所有 commit 带 `Tested-By` 行末(从 v1.1.5 起强制), so that 知道是否经过端到端测试。
36. As a 技能维护者, I want `docs/adr/` 永久归档重大决策, so that 后续维护者知道"为什么这样做"。
37. As a 技能维护者, I want `.scratch/<feature>/` 工作目录范式(spec + decisions + verify + issues + artifacts), so that 临时工作也有归档。
38. As a 技能维护者, I want FAT 协议豁免矩阵(ADR-0005 表格), so that 知道哪些改动必须 FAT,哪些可豁免。
39. As a 技能维护者, I want 5 状态 fallback(已改为 4 状态:正常 / 空 / 缺数据 / 错误)模板 JS 一致, so that 错误处理行为可预测。
40. As a 技能维护者, I want 29 场景的 7 字段契约(wake_word / scenario_id / scenario_title / dimensions / prompt / status / result)守护测试, so that 不破坏场景资产。

### 跨 Skill 联动(从其他 skill 跳到备忘录)

41. As a 卡路里用户, I want 完成训练后顺手记一条备忘(联动), so that 训练日志 + 备忘一体。
42. As a 饼干记账用户, I want 记完账后记一条备忘(联动), so that 财务事件有备注。
43. As a 居家管家用户, I want 物品清单变更触发备忘, so that 物品变化有上下文。
44. As a 作息管家用户, I want 日程完成后自动记一条备忘, so that 实际执行可追溯。

### 规范合规(总纲 §02-§07)

45. As a 总纲执行者, I want 备忘录 skill 100% 通过 §02 5 层自检清单, so that 任何 skill 形态都满足。
46. As a 总纲执行者, I want §03 触发词设计 ≥ 8 + 不强制 4 元(总纲 §03 L46 允许 2-3 元), so that 灵活性 + 合规性兼得。
47. As a 总纲执行者, I want §04 13 原则全满足(其中原则 3 改为 4 状态,需向总纲提 ADR), so that 视觉与注入规范一致。
48. As a 总纲执行者, I want §05 工程仪式全部就位(FAT exempt / Tested-By / 3 问 / 豁免矩阵), so that 改动可审计。
49. As a 总纲执行者, I want §07 HELP + 场景完备性 7 字段契约全满足, so that 用户体验稳定。
50. As a 总纲执行者, I want ADR-0002 "无规模逃生口"100% 合规, so that 微型 skill 也不掉链。

## Implementation Decisions

### 模块改动清单(本 spec 涉及)

#### 内容模块

- **`SKILL.md`**: 添加 YAML frontmatter(A.1 5 字段:name / version / status / description / last_updated)→ 删 L1034 重复章节(B.7)→ 91 处"触发词"→"唤醒词"(B.3)→"用例"→"场景"(B.4)→ 显式区分"4 元"vs"4 段 prompt"(B.5)→ 统一"HTML 镜像"命名(B.6)→ 顶部加"改动前 3 问"段(D.3)。不改 29 唤醒词响应行为。

- **`CHANGELOG.md`**: L538 加注释说明"v1.1.0 时为 106,后续增长"(B.11)→ 末尾建"累计 174/174"基线(B.11)→ 每个版本段末尾加 `**Tested-By**` 字段(D.2)。

- **`scenarios.yaml`**: 删 L21 重复 `scenarios:` 块(B.10)→ EOF 补 `\n`(B.10)→ 7 字段契约不变(wake_word / scenario_id / scenario_title / dimensions / prompt / status / result)。

- **`_meta.json`**: `version` 字段从 `1.0.0` 升到 `1.1.4`(B.2 · SoT 为 SKILL.md,_meta.json 是镜像)。

#### 文件系统模块

- **`reference/` → `references/`**: 3 个 .md(git mv 到 `references/`)→ 4 处 SKILL.md 路径引用同步 → `memo_render.py` 端不动(已用 `references/`)。

- **5 个 HTML 模板** (`templates/memo_help.html` / `memo_query.html` / `sync_report.html` / `wish_plan.html` / `wish_complete.html` / `change_category.html`): fallback JS 同步改 4 状态(success / empty / missing_data / error,B.9 决策)→ 删 `offline` 分支。

#### 新建文件模块

- **`README.md`**: 5 章节(这是什么 / 何时使用 / 快速开始 / 文件清单 / 状态,A.2)。
- **`pytest.ini`**: 6 项配置(testpaths / python_files / classes / functions / addopts --strict-markers + markers 区,A.3)。不加 `xfail_strict`(防 22 xfailed 连锁失败)。
- **`CONTEXT.md`**: 术语表(7 字段:唤醒词 / 场景 / 4 元 / 4 段 prompt / HTML 镜像 / 场景资产 / 【待开发】)+ commit 格式约定段。
- **`docs/adr/0001-0005.md`**: 5 个 ADR 文件(B / A / D 各阶段决策归档)。
- **`.scratch/grilling-alignment/`**: 5 文件范式(spec.md / decisions.md / verify.ps1 / artifacts/ / issues/,A.4)。
- **`.githooks/commit-msg`**: commit 全中文格式检查 hook(D.5 决策,commit 时强制拦截)。

#### 接口与行为契约

- **CLI 接口**: 29 个子命令集合不变(`memo_cli.py` 子命令签名 0 改动)。
- **HTML 镜像同步**: `备忘录.html` 在 `memo_cli help` 时自动生成并覆盖 skill 根,经 `.githooks/pre-commit` 自动还原(2026-07-28 R3 修复的 GBK + 时间戳 bug)。
- **scenarios.yaml 7 字段契约**: 守护测试 `test_help.py` L83-89 + L96-100 + L102-112 已就位。
- **HTML 单工铁律**: 过程型 HTML(`wish_plan` / `wish_complete` / `change_category` / `sync_report`)含"复制 prompt"按钮,守护测试 `test_copy_button.py` 10 个 test_。

### Schema 变更

- **`_meta.json`**: `version` 字段值变更(`"1.0.0"` → `"1.1.4"`)。结构不变。
- **`scenarios.yaml`**: 内部结构 0 变更,只删冗余 key + EOF 补换行。
- **无 DB schema 变更**: 数据库层不在本 spec 范围(B 阶段决策不动 schema)。

### API 契约

- CLI 子命令签名 0 改动。
- HTML 输出 4 状态 fallback 新语义:`success`(新增) / `empty` / `missing_data` / `error`(原有),`offline`(删除)。
- scenarios.yaml 字段契约 0 改动。

### 架构决策

- **B 阶段先行**(依赖关系升序,总纲 §05 L5-11 "改动前 3 问"启发):B → A → D → C。
- **5 状态 → 4 状态**:用户 R1 明确决策"不存在所谓离线的场景",本地偏离总纲 §04 原则 3。后续若需向总纲提 ADR 申请"skill 自定义状态数"权限。
- **injector 私有 vs 共享**: v1.1.0 教训固化,**不重提** `_shared/` 抽取(违反总纲 §02 L99 跨 Skill 共享禁令)。
- **commit 全中文格式**: ADR-0003 硬规则,`.githooks/commit-msg` 强制执行。
- **Tested-By 字段**: ADR-0005,commit message 行末 + CHANGELOG 双写,默认 `exempt`(无 fresh agent)。

## Testing Decisions

### 测试入口决策(2 个,第一性原理收敛)

> 总原则: "The fewer seams across the codebase, the better - the ideal number is one." (to-spec 流程第 2 步)
>
> 本 spec 实际收敛到 **2 个测试入口**:1 个主入口(CLI 子进程,黑盒,最高级)+ 1 个辅助入口(结构体检,白盒,但只验静态存在性,单文件 ~30 行)。
>
> commit 全中文格式检查**不放测试**,放 `.githooks/commit-msg` hook(单独工程配置,不污染测试 seam)。

#### 主入口: CLI 子进程调用

- **形式**: `subprocess.run([sys.executable, "script/memo_cli.py", "<subcmd>"])` → 断言退出码 + stdout/stderr + 输出文件存在性 + 内容模式。
- **覆盖范围**: 4 状态 fallback / 术语替换(行为级)/ 29 唤醒词命中 / scenarios.yaml 完整性 / HTML 镜像同步 / prompt 不暴露 CLI/DB/路径。
- **Prior art**: `tests/test_help.py` 49 个 test_ 函数已大量使用 subprocess 调真 CLI(L198 / L214 / L330 / L391 等处),是最高 seam 的成熟范例。
- **优点**: 黑盒 / 行为级 / 稳定(CLI 是稳定契约)/ 高信号(模拟真实用户行为)。
- **缺点**: 较慢(每次起子进程),但 174 测试 16 秒跑完,可接受。

#### 辅助入口: 结构体检(单文件)

- **形式**: `tests/test_skill_structure.py` ~30 行 ~6-8 个 assertion,验静态文件存在 + 内容模式。
- **覆盖范围**: YAML frontmatter 存在 + `_meta.json` 版本 = SKILL.md frontmatter 版本 + `docs/adr/` 5 个 ADR 存在 + `README.md` 存在 + `pytest.ini` 存在 + `AGENTS.md` 包含项目定位关键词。
- **Prior art**: 无直接先例,新文件。
- **优点**: 单文件 / 易理解 / 快速。
- **缺点**: 白盒(断言实现细节),但只验"文件存在性 + 关键字符串",不深入。
- **原因**: 部分静态合规(如 frontmatter 5 字段名)难以用 CLI 行为断言,必须读文件。但控制范围(只 1 个文件 ~30 行),不污染主 seam。

### 测试模块清单

| 模块 | 测试数 | 覆盖范围 |
|---|---:|---|
| `tests/test_help.py`(已就位) | 49 | HELP HTML 渲染 / 7 字段契约 / prompt 不暴露 / 5 者一一对应 |
| `tests/test_html_delivery_checklist.py`(已就位) | 13 | §07 §5 反模式守护 |
| `tests/test_html_user_manual.py`(已就位) | 12 | HTML 用户手册结构 |
| `tests/test_copy_button.py`(已就位) | 10 | 复制 prompt 按钮(原则 10) |
| `tests/test_wish_complete.py`(已就位) | 16 | 心愿完成 HTML |
| `tests/test_injector_local.py`(已就位) | 17 | 注入器本地行为 |
| `tests/test_render.py`(已就位) | 10 | 渲染层 |
| `tests/test_payloads.py`(已就位) | 9 | payload 校验 |
| `tests/test_change_category.py`(已就位) | 7 | 改分类 |
| `tests/test_html_delivery.py`(已就位) | 7 | HTML 交付 |
| `tests/test_validators.py`(已就位) | 7 | 校验层 |
| `tests/test_wish_plan.py`(已就位) | 9 | 心愿排期 |
| `tests/conftest.py`(已就位) | 0 | pytest 配置 / sys.path 加 script/ |
| **`tests/test_skill_structure.py`(本 spec 新建)** | ~6-8 | frontmatter / _meta.json / 5 ADR / README / pytest.ini / AGENTS.md |
| **合计** | **180+** | (174 已有 + 6-8 新增) |

### 验收脚本

- **`.scratch/grilling-alignment/verify.ps1`**: 当前是占位版(R3 创建),R5 后完整化,运行后输出:
  1. `git status` 工作区干净检查
  2. `pytest tests/ --tb=short -q` 全过检查
  3. CLI smoke test(`memo_cli help` 落 HTML 检查)
  4. 结构体检 `pytest tests/test_skill_structure.py -v` 全过
  5. .githooks 路由检查(`memo_cli help` 落 HTML 后 git status 干净)

### 什么不算好测试(反面案例)

- ❌ 测试内部函数(应该测试 `_render_template()` 的返回值,而非测试"模板被渲染")
- ❌ 测试具体行号(SKILL.md L927 / L1034 应改为"## 参考文档 章节唯一性")
- ❌ 测试私有状态(数据库连接对象的方法)
- ❌ 测试 commit 信息格式(应该放 `.githooks/commit-msg` hook,不是 pytest)

## Out of Scope

- **跨 Skill `_shared/` 共享代码**: v1.1.0 教训固化,`script/injector.py` 私有。违反总纲 §02 L99 跨 Skill 共享禁令。
- **历史 commit 回填 Tested-By**: 历史不可改,规则自 v1.1.5 commit `bb7c64b` 起生效。
- **FAT 协议实跑**: D.1 决策 `Tested-By: exempt`(无 fresh agent 配置)。未来若用户接入 fresh agent,需新 ADR 激活。
- **4 元组触发词强制升级**: B.12 决策保持 2-3 元混合(总纲 §03 L46 允许)。用户口语习惯优先。
- **C 阶段 injector 复用 `_assets/`**: v1.1.0 私有化决策,不重提。
- **C 阶段 5 层自检清单全跑补齐**: 仅在结构体检 seam 加 ~3 个 file existence assertions,不深度重构 tests。
- **CHANGELOG 历史数字修订**: B.11 决策保留 L538 "106/106" 真实数字,加注释说明而非伪造。
- **新增 skill 功能**: 本 spec 是 v1.1.4 → v1.1.5 合规化,不引入新功能。

## Further Notes

### 路线图(从 bb7c64b 到 v1.1.5 完成)

| 步骤 | commit 信息(全中文) | 涉及文件 |
|---|---|---|
| ✅ 1 | `[备忘录] v1.1.5 · B-0 决策记录入库(...)` | 13 capture 文件 · bb7c64b |
| ⏳ 2 | `[备忘录] v1.1.5 · B-2 术语统一(...)` | SKILL.md / scenarios.yaml / 5 模板 |
| ⏳ 3 | `[备忘录] v1.1.5 · B-3 文件结构清理(...)` | reference/ → references/ / SKILL.md L1034 删 / scenarios.yaml L21 删 |
| ⏳ 4 | `[备忘录] v1.1.5 · B-4 4 状态 fallback 收尾(...)` | 5 模板 JS / _meta.json / CHANGELOG 末尾 |
| ⏳ 5 | `[备忘录] v1.1.5 · A-1 结构文件补齐(...)` | 新建 README / pytest.ini / AGENTS.md 升级 / SKILL.md frontmatter |
| ⏳ 6 | `[备忘录] v1.1.5 · D-1 仪式落地(...)` | SKILL.md 3 问段 / .githooks/commit-msg / CHANGELOG Tested-By 行末 |

每个 commit 都标 `Tested-By: exempt(无 fresh agent · 详见 ADR-0005)`。

### 决策索引

| ADR | 主题 | 阶段 |
|---|---|---|
| 0001 | 版本号单一事实源为 SKILL.md | B |
| 0002 | SKILL.md 章节去重 + 双目录合并 | B |
| 0003 | B 执行细节 + commit 全中文硬规则 | B |
| 0004 | A 阶段结构文件 5 决策 | A |
| 0005 | D 阶段豁免矩阵 + 工程仪式 | D |

### R5 未单独进行的原因

总纲 P1 路线原本规划 R5 (C 阶段架构合规),但探勘发现 C 阶段大部分决策已在 R1+R2 完成:
- 4 状态 fallback(B.9 · C 阶段核心)
- 4 元组触发词保持(B.12 · C 阶段核心)
- injector 私有(v1.1.0 教训 · C 阶段核心)
- 5 层自检清单(test_skill_structure.py 单文件覆盖 · C 阶段补齐)

剩余 C 子项(跨 Skill 路由完整声明 / 5 层自检清单全跑补齐)归入本 spec 的"Out of Scope"或下次循环。

### 跨 Skill 联动备注

备忘录 ↔ 卡路里(训练日志)↔ 饼干记账(账目)↔ 居家管家(物品)↔ 作息管家(日程)— 各自独立 skill,通过共同唤醒词约定触发联动(无需共享代码)。当前联动仅为"用户手动跨 skill 操作",未来可加 `auto_link` 字段到 scenarios.yaml 维度。

### 关联链接

- 4 轮 grilling 报告: `.scratch/grilling-alignment/artifacts/r1.html` / r2 / r3 / r4
- 整体重构 spec: `.scratch/grilling-alignment/spec.md`
- 决策日志: `.scratch/grilling-alignment/decisions.md`
- 验收脚本(占位): `.scratch/grilling-alignment/verify.ps1`
- 已入库决策 commit: `bb7c64b`

---

**Issue 编号**: 01(本文件是 `.scratch/grilling-alignment/issues/` 目录第一个 issue)
**Triage 状态**: `ready-for-agent`(可直接分配给 agent 执行)
**建议执行顺序**: 按"Futher Notes · 路线图"表的 ⏳ 顺序,每个 commit 独立完成 + 174 pytest 守护。
