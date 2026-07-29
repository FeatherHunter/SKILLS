# 备忘录 Skill · 术语表

备忘录 skill 内部概念词汇表,与 `SKILL开发总纲V1.0/CONTEXT.md` 保持术语一致。

## Language

**唤醒词**:
用户用于激活备忘录 skill 的口语短语(例:"记备忘"、"搜备忘"、"按时间搜备忘")。每个唤醒词对应 `references/scenarios.yaml` 中一个稳定 scenario。
_Avoid_: 触发词、命令、指令、关键词

**场景**:
备忘录 skill 可响应的业务用例。每个场景 = 1 个唤醒词 + 1 份稳定 prompt + 1 个预期结果。
_Avoid_: 用例、test case

**4 元**:
唤醒词的 4 元素结构 = 动作 + 对象 + 维度(可选) + 类型(可选)。
_Avoid_: 4 元组(易与"4 段 prompt"混淆,本术语表显式区分)

**4 段 prompt**:
prompt 模板的 4 段结构 = 场景 + 数据 + 期望 + 来源。源自总纲 §04 4 段式 HTML。
_Avoid_: 4 部分(易与"4 元"混淆)

**HTML 镜像**:
SKILL.md 的可视化副本,位于 skill 根目录(`<SKILL_DIR>/备忘录.html`),与 SKILL.md 同 commit 同步(总纲 §04 原则 0 判定)。
运行时别名: **HELP HTML**(用户说"备忘录 HELP"时由 `render_help` 调用生成)
_Avoid_: 用户手册(v1.0.9 临时名,v1.1.4 已废弃)、落地页、官网、演示页

**渲染产物**(render artifact):
`templates/` 下 5 个数据 / 过程型 HTML 文件(`memo_query / sync_report / wish_plan / wish_complete / change_category`),由对应 CLI 调 `memo_render.py` 注入 `window.__DATA__` 后产出。**不是** SKILL.md 的副本,与 HTML 镜像完全独立(总纲 §04 原则 12.A 数据/过程 HTML 约定)。
渲染产物遵守总纲 §04 全部 11 原则(占位符 / 5 状态 fallback / escapeHTML / HTML 单工铁律 / HTML-First)。
_Avoid_: HTML 模板(笼统,易与 HTML 镜像混淆)、HTML 镜像(专指 memo_help.html,严禁类比)、模板(语义模糊,可能指 React/Vue 模板)

**模板静态扫描**(template lint):
对 `templates/*.html` 内嵌 JS 做的离线静态校验规则集合(无 Node / 浏览器依赖,Python 实现)。目的是在 pre-commit 拦截"引用未定义函数 / escape-unescape 不对称 / 单工铁律违反"三类典型 bug——模板层 JS Bug 历史上从未被 `tests/` 捕获(测试只覆盖 CLI→JSON→path 渲染管道,不覆盖浏览器行为)。
_Avoid_: ESLint(依赖 Node / npm,本仓库不引入)、jsdom(过重,设计目标=运行时模拟而非静态扫描)

**场景资产**:
`references/scenarios.yaml` 单一事实源(总纲 §07 契约),29 个场景条目的权威定义点。不允许手工维护独立副本。
_Avoid_: 场景列表、用例表、yaml(简称)

**【待开发】**:
场景条目 `status` 字段的预留值(总纲 §07 二态)。语义:"AI 不得假装执行,必须停步 + 告知"。当前 29 场景全 `status = ""`,本术语表保留以备未来扩展。
_Avoid_: WIP、TODO、暂未实现

**搜索意图**(search intent):
备忘录 templates 过滤框的语义范围(grill 决策 R2-4)。`memo_query.html` 的搜索框**只**匹配 `note.content` 字段,不命中 `id` / `feishu_task_guid` / `created_at` 等内部字段;**不**对 JSON 整串 substring(避免 UUID 全命中假象)。与 chip(按 category 过滤)的职责严格分离。
_Avoid_: 全文搜索(本模板未实现)、模糊搜索(语义模糊,本术语表选精确词)

## Commit 格式约定

本仓库 commit 信息必须全中文(硬规则,见 `docs/adr/0003-b-execution-fallback.md`):

```
[<skill 中文名>] <主题> · <细节(可选)>
```

或 `<类型>: <skill 中文名> <主题> · <细节>`(类型词必须中文)。

❌ 禁用英文类型前缀(`fix:` `docs:` `feat:` `chore:` 等)和英文括号类型(`fix(...)` `docs(...)` 等)。

## 历史

| 版本 | 变更 |
|---|---|
| v1.1.5-RFC | B.3 / B.4 / B.5 / B.6 决策落地(Grilling R1) |
| v1.1.5-RFC | B.9 / B.10 / B.11 / B.12 / B.13 + commit 格式约束(Grilling R2) |
