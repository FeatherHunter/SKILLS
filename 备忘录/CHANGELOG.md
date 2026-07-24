# Changelog · 备忘录 (Memorandum)

所有对备忘录的 **显著** 变更记录在此。格式参照 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

> **强制性规定**(SKILL.md 顶部):HTML 镜像 + changelog 必须与代码同步。
> 本文档与 SKILL.md + 备忘录.html 共同维护。

---

## [Unreleased] · 2026-07-24 (Step 5A/5B · 过程型 HTML 系列)

### Added
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

### Changed
- 5 个过程型 HTML 向导(wish-plan/wish-complete/change-category 等)统一按 04_架构师原则 §10 设计
- 4 部分 prompt 模板(场景/数据/期望/来源)成为向导标配

---

## [Unreleased] · 2026-07-24 (Step 6 · DRY 共享抽取)

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

## [Unreleased] · 2026-07-24 (Step 1-4 · 文档对齐 + sync_report + wish_plan)

### Added
- **`sync-from-feishu --html`** · 结果型 HTML 报告页
  - 11 个统计字段(backfilled/scanned_done/synced/scanned_pending/due_added/...)
  - 3 步折叠详情 · errors 红色高亮 · 复制同步回执
  - 模板 `templates/sync_report.html` · 渲染器 `memo_render.py:render_sync_report`
  - commit `b1193c0`
- **`wish-batch-plan` 子命令**(过程型 HTML 第 1 个)
  - `memo_cli.py wish-batch-plan [--ids] [--all] [--suggest-due X] [--html]`
  - 模板 `templates/wish_plan.html` · 4 部分 prompt
  - commit `e6d5d89`

### Fixed
- **SKILL.md 与代码裂缝**(L114-L228 · 5 处"默认行为"+ "AI 推荐流程")
  - 旧文档:「默认生成 HTML 页面」「需要纯 JSON 时再显式传 `--no-html`」
  - 代码实际:默认 JSON · `--html` 生成 HTML · 无 `--no-html` flag
  - 文档对齐 + 显式标注「当前没有 `--no-html` flag」
  - HTML 镜像 `备忘录.html` 同步修订(强制性规定第 1 条)

### Changed
- 工程实践:`tests/` 目录建立 · 49 → 59 → 68 用例(逐步加)
- `.githooks/pre-commit` 加 `备忘录/*` 路由 → 改备忘录自动跑 pytest
- `memo_render.py` 重构:抽 `_inject` + `_write_output` 公共函数
- `conftest.py` 提升 `env_with_tmp_db` 让所有 subprocess 测试复用

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

- **当前**:所有 2026-07-24 累积变更都标 `[Unreleased]`
- **下一阶段**:发布稳定版时(若有)将 `[Unreleased]` → `[1.x.y - YYYY-MM-DD]`
- **孤立 1.0.0**:待 Step 5A/5B/6/7 全部稳定后定版

### 引用规则

本文件格式参考 [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-CN/1.1.0/):
- **Added** 新增的功能
- **Changed** 已有功能的变更
- **Deprecated** 已弃用(本项目暂时无)
- **Removed** 删除的功能(本项目暂时无)
- **Fixed** 任何 bug 修复
- **Security** 安全漏洞修复(本项目暂时无)
- 每个变更关联 commit SHA,便于 review
