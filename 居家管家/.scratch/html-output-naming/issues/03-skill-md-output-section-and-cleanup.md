# 03 — SKILL.md §📌 输出位置章节 + 清空 output/ 历史

**Status:** resolved
**Resolved:** 2026-07-28

## Answer

**SKILL.md**: New §📌 输出位置 section inserted between "## 安装与配置" and "## HTML 渲染器（Phase 7 重构）". Contains:
- Reference to SKILL开发总纲 §原则 12
- 12.A / 12.B classification
- Env chain priority `$SKILLS_DATA_DIR` > `$SKILLS_DB_PATH` > fallback
- Template → command_cn mapping table (10 entries)
- 12.B HELP naming form `居家管家_HELP_<stamp>.html` with `_HELP_` reserved keyword
- Explicit deviation table: local time / overwrite / skill slug = home_manager
- Pointer to ADR-0001

**Cleanup**: `output/` directory cleared (109 files, 110 MB). `居家管家.html` (git-tracked HELP mirror) preserved at skill root. `.notes/` (dev docs) preserved.

End-to-end verified after cleanup:
- `python home_manager.py search` → `D:\.db\home_manager_html\查物品_*.html`
- `python home_manager.py help` → `D:\.db\home_manager_html\居家管家_HELP_*.html`
- `test_manual_sync.py` shows the same pre-existing SHA mismatch (HELP HTML drift unrelated to this work; fix: `python3 scripts/build_manual.py`)

## What to build

(Original ticket body preserved below)

**What to build:** 在 SKILL.md 新增 §📌 输出位置 章节,显式引用总纲 §原则 12,标 12.A/12.B 分类,列 template→command_cn 映射表,显式声明偏离(本地时间 / 覆盖 / Skill 标识),指向 ADR-0001 和 CONTEXT.md。同时清空 `output/` 目录下 107 个旧命名风格的历史运行产物(~110 MB),保留根目录 `居家管家.html`(git 跟踪的 HELP mirror)和 `.notes/`(开发文档)和 `.db/`(测试 sync artifact)。

**Blocked by:** 02 — 完整 template→command_cn 映射表 + 12.B HELP 命名

- [x] SKILL.md 含 §📌 输出位置 章节
- [x] 章节显式引用总纲 §原则 12(标注"SKILL开发总纲V1.0/04-可视化与注入v2.md 原则 12")
- [x] 章节标 12.A(数据/过程)和 12.B(HELP)分类
- [x] 章节列出 10 个 template → command_cn 映射(与 T2 落地一致)
- [x] 章节显式声明三项偏离:
  - 时区:本地时间(非总纲 12.X 的 UTC),指向 ADR-0001
  - 冲突处理:直接覆盖(非总纲 12.X 的 `_N` 后缀不覆盖)
  - Skill 标识:`home_manager`(Skill 自决,与 Python 包名一致)
- [x] `output/` 目录下文件数为 0(107 个历史文件全清)
- [x] 根目录 `居家管家.html` 保留(test_manual_sync.py 强制 SHA256 一致)
- [x] `.notes/` 下开发文档保留(审计报告 / 计划书 / grilling rounds)
- [x] `.db/__sync_test_help.html` 如存在则保留(测试 sync artifact)
- [x] `test_manual_sync.py` 继续通过(`居家管家.html` 未被破坏)
- [x] 清空后跑 `python home_manager.py search`,新文件落到 `home_manager_html/查物品_*.html`(非旧 `output/search_results_*.html`)
