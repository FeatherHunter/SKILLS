# Changelog

All notable changes to **dsh-waystation** are documented here.

格式基于 [Keep a Changelog](https://keepachangelog.com/) · 版本遵循 [Semantic Versioning](https://semver.org/)。

---

## [1.3.2] - 2026-08-15 (HOTFIX)

### Fixed · 致命 bug（T12 · npm 1.3.1 bundle 不加载）

- **buildColorOf 重复 `return colorOf` + 多余 `}` 删除**（T9 commit `88d48d77` 引入）：
  - 1.3.1 npm 包里 buildColorOf 函数结尾误插入了 `return colorOf` 和 `}`
  - 多余的 `}` 让 apply 函数被提前闭合 → 整个 client bundle 语法无效 → `window.__ModuleLoader__.load` 从未执行
  - DSH 加载 1.3.1 时报 `bundle loaded without registering via ModuleLoader.load`，所有 T2-T11 改动全部失效
  - 修复：client.js + package/lib/client.js 删除多余两行，保留单份收尾

### Hardening（建议 · 待开 ticket）

- pre-publish hook 加 `node --check client.js && node --check package/lib/client.js`
- verify-t3-locale.js 扩展 bundle 语法校验

---

## [1.3.1] - 2026-08-15

v27 范式 + 13 项用户报告 bug + v27 验证后新需求（label count + 新会话按钮）。

### Changed · v27 范式（5 commit · #407/#395/#405/#394/#396）

- **#407** 配置页加「重置面板宽度」按钮
- **#395** 全控件 hover 文案重设计
- **#405** 列表默认可见 label 数改为 4（per-row + filter row 视觉一致）
- **#394** 新会话按钮明显化（ghost/icon-only → 可见文字 + external-link 图标）
- **#396** 标题换行策略改善（dsws-tt-wrap）

### Fixed · 13 项用户报告 bug（wayfinder map #409 · T1-T4）

- **#1** 配置页布局紧凑化 + group 3 可折叠（默认展开 · 详情默认折叠）
- **#2** 主面板顶部按钮重排：刷新按钮从 ListTab KPI 行上移到 OverlayPanel tabs 行末尾（紧贴环境检查右边）
- **#3** 列表项 issue 编号显示在最前方（TicketRow + issueRow · 保留 v14-2 map 行突出视觉）
- **#5** 打开面板初始加载显示 loading 全屏遮罩 + 转圈 + 禁点（替代单行"加载中"文本）
- **#6** 列表筛选状态新增「阻塞」（stateFilter 加 blocked · filter row 第 4 个 chip）
- **#7** 默认排序按 issue 编号升序（listPrefs 默认 sortKey=number / sortDir=asc · localStorage 记忆优先）
- **#8** map 完成态判断（子票全关 → 「完成」按钮绿色 + 收尾 prompt 措辞优化）
- **#9** 修复 prompt 明确化（5 步：复现/根因/实施/测试/审查）
- **#10** 执行 prompt 明确化（4 步：读/方案/实施/验收）
- **#11** 诊断 prompt 明确化（3 步：复现/根因/分流）
- **#12** 讨论 prompt 明确化（4 步：目标/风险/选项/决策）

### Changed · v27 验证后新需求（wayfinder map #409 · T8 + T9）

- **T8** label chip 不显示 issue count（filter row 移除 `· ${count}` 显示 · +N 折叠 chip 数字保留）
- **T9** 新会话按钮文字缩短（"新开会话" → "新会话"）+ 颜色与执行按钮同色（按 issue label 动态取 GitHub 配置色 · YIQ 感知亮度自适应）

### Changed · 用户微调（T11）

- **T11** 沉淀 prompt 落盘逻辑二态改三态：
  - 原：map（写进 map 正文 + ISSUE）/ 都没有（先生成快照笔记）
  - 改：map（写进 map 正文 + ISSUE）/ 只有 ISSUE（写进对应 ISSUE）/ 都没有（先生成快照笔记）

### Technical

- 双源镜像一致（client.js ↔ package/lib/client.js · 行号偏差 13）
- 6/6 host 逻辑层测试 PASS（verify-status 21/21 · verify-panel 22/22 · verify-t2a-config 6/4 · verify-t2b-templates 6/6 · verify-t3-locale 175 键 × 2 files · scan-mangle clean）
- 5 个新 ticket 实施 + 2 个 grill 票决议 + 1 个 research 票 + 1 个 pre-release 验证

### Map Reference

- wayfinder map：[#409 dsh-waystation v1.3.1 修复合并 map](https://github.com/FeatherHunter/SKILLS/issues/409)
- 12 张子票全部完成（R0 + G1 + G2 + T1-T9 · T5 close as wontfix · T7 close as completed）

---

## [1.3.0] - 2026-08-15 (v26 范式)

### Added

- 三视图（列表 / 技能 / 环境检查）
- 前置就绪绿点检查 8 项（host wf.status RPC）
- wayfinder 面板（GitHub issue 地图/列表/技能/环境检查）
- 输入区状态栏胶囊
- 开始此 Issue 流程（确认框 + 认领 + 注入 /wayfinder）
- 模板编辑器 + 占位符保护（双源镜像）
- 中英双语字典（175 键 × zh/en）
- npm 包（@dsh-waystation · postinstall 自动注册到 DSH profile）

---

## [1.2.0] - 2026-08-14

### Added

- 模板可编辑（T2a 配置页骨架）
- T2b 模板编辑器 + 占位符保护（双源镜像）
- 完成态判断（#371：子票全关 → 「完成」按钮绿）
- 双源镜像一致性核验

---

## [1.1.0] - 2026-08-14

### Added

- host 逻辑层 RPC（wf.status / wf.snapshot / wf.refresh / wf.cwd）
- 集成 v25 配置页

---

## [1.0.1] - 2026-08-14

### Fixed

- inject connection
- slots 清理
- 移除 tool.view.cordis 死代码
- 描述更新

---

## [1.0.0] - 2026-08-14

### Added

- 初始发布
- 配合 mattpocock/skills 的 wayfinder / triage / grilling / handoff
- Host 端（host.js）+ Client 端（client.js）双源镜像
- 5 张视图：列表 / 技能 / 环境检查 / 配置 / Run
- DSH 集成（settings.plugins.tab + shell.overlay + conversation.input.dock + details）
- npm 包（@dsh-waystation@1.0.0）

---
[1.3.1]: https://github.com/FeatherHunter/SKILLS/compare/v1.3.0...v1.3.1
[1.3.0]: https://github.com/FeatherHunter/SKILLS/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/FeatherHunter/SKILLS/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/FeatherHunter/SKILLS/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/FeatherHunter/SKILLS/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/FeatherHunter/SKILLS/releases/tag/v1.0.0
