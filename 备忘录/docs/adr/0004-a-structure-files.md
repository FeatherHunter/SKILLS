# 0004 A 阶段结构文件决策

A 阶段 5 决策的捕获文件。同时记录本次 grilling 工作目录的范式化结果。

## Status
accepted · 2026-07-28 · Grilling R3 / A.1 + A.2 + A.3 + A.4 + A.5

## A.1 · SKILL.md YAML frontmatter

5 字段:`name` / `version` / `status` / `description` / `last_updated`。

```yaml
---
name: 备忘录
version: 1.1.5
status: active
description: 跨设备随手记录 · 结构化备忘 + 心愿 + 打卡 + 情绪追踪
last_updated: 2026-07-28
---
```

**理由**:
- `name` 与 `version` 是 ADR-0001 SoT 链路
- `status` 标记生命周期(`active` / `deprecated` / `draft`)
- 触发词表不进 frontmatter(已用 `scenarios.yaml` 单独维护,避免双源)

## A.2 · README.md 章节大纲

5 章节:

1. **这是什么** — 3 句话描述 skill 用途
2. **何时使用** — 适合场景 + 不适合场景(对照卡路里等 skill 的边界)
3. **快速开始** — 3 步上手(装环境 / 跑测试 / 看帮助)
4. **文件清单** — 目录树 + 每个文件 1 行说明
5. **状态** — 版本 + last_updated + 已知问题

预估 60-80 行。

## A.3 · pytest.ini 配置

6 项最小配置:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -ra -q --strict-markers
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
```

**理由**:
- 6 项都是"防误伤"型(避免 pytest 扫错文件/类/函数)
- `--strict-markers` 防 typos(未注册 marker 报错,比静默跳过安全)
- 不加 `xfail_strict`:当前 22 xfailed 是历史基线,改了会连锁失败
- 不加 `asyncio_mode`:测试都是同步的

## A.4 · .scratch/<feature>/ 范式

5 文件结构:

```
.scratch/<feature>/
├── spec.md          # 需求规格 / 设计草图
├── verify.ps1       # 验收脚本(总纲已示范)
├── issues/          # 问题追踪(01-xxx.md / 02-yyy.md / ...)
├── decisions.md     # 决策日志(轻量 ADR,不进 docs/adr/)
└── artifacts/       # 工作产物(HTML 报告 / 截图 / 中间文件)
```

**理由**:
- 对照总纲 `.scratch/skill-dev-manual-refactor/` 现状,补齐 5 文件结构
- `decisions.md` 是"轻量 ADR":临时性决策不进 docs/adr/(永久归档)
- `artifacts/` 是本次 grilling HTML 报告的归宿(R1/R2/R3...)

## A.5 · AGENTS.md 升级

13 行 → 25-30 行,新增内容:

- **项目定位**: "跨设备随手记录 · 结构化备忘 + 心愿 + 打卡 + 情绪追踪"
- **路径约定**: SKILL.md 在根 / scripts 在 script/ / 场景资产在 references/ / 测试在 tests/
- **决策文件位置**: 永久 ADR → `docs/adr/`; 临时决策 → `.scratch/<feature>/decisions.md`
- **commit 格式**: 引用 ADR-0003 硬规则段
- **HTML 镜像约定**: `备忘录.html` 是 SKILL.md 镜像,自动生成,不入 commit(per .githooks/pre-commit)

## 本轮范式化结果

`.scratch/grilling-alignment/` 已改造为 A.4 5 文件范式:

```
.scratch/grilling-alignment/
├── spec.md           # 备忘录 skill 整体重构 spec(B+A+D+C 全阶段)
├── decisions.md      # R1+R2+R3 决策摘要(轻量 ADR 性质)
├── artifacts/        # 历史 HTML 报告
│   ├── r1.html
│   ├── r2.html
│   └── r3.html
└── issues/           # (空,后续如有再补)
```

## Considered Options

A.1 备选(用户已选 5 字段):
- 2 字段(name + version) — 最小化(放弃)
- 8 字段(含 owner / repo_path / 等) — 信息全但维护高(放弃)
- 触发词表进 frontmatter — 与 scenarios.yaml 双源(放弃)

A.2 备选(用户已选 5 章节):
- 3 章节 — 删"何时使用"(放弃)
- 8 章节 — 加"贡献指南/架构/FAQ/致谢"(放弃)
- 不新建 — 改 SKILL.md 加目录锚点(放弃)

A.3 备选(用户已选 6 项 pytest.ini):
- 用 pyproject.toml 的 `[tool.pytest.ini_options]` 替代 — 现代化但需确认无 pyproject.toml(放弃)
- 完全照搬总纲 §05 L211-217 模板 — 字段可能不全(放弃)
- 不新建 — conftest.py 里配(放弃)

A.4 备选(用户已选 5 文件范式):
- 3 文件精简(删 verify.ps1 + decisions.md)(放弃)
- 完全照搬总纲现有结构(不补 decisions/artifacts)(放弃)
- 不固化范式 — 每个 feature 自定(放弃)

A.5 备选(用户已选 25-30 行):
- 保持 13 行 — 精简优先(放弃)
- 扩到 50+ 行 — 全量级文档(放弃)
- 删 AGENTS.md 合并到 SKILL.md — 失去"agent 专用入口"清晰度(放弃)
