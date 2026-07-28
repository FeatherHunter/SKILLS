# 作息管家 · Agent Instructions

> AGENTS.md · 项目根版本(自动加载)
> 工程 skill 配置见 `docs/agents/`

## 项目定位

作息管家 v1.1.3(2026-07-25)— 作息记录与日程计划管理技能。**宽 Skill**,内部管理 2 个语义不同的域:

- **作息记录(record)**:`schedule_records` + `daily_summary` 表,回顾性输入
- **日程计划(plan)**:`schedule_plans` 表,预测性输入

第一性:`商量计划`(plan 域)是规划未来,`复盘`(plan 域)是回顾当日 plan 执行情况,**两者闭环形成"事前规划 → 事中执行 → 事后回顾"完整循环**,不应拆分为 2 个 Skill(否则破坏跨域流程)。

## 项目根关键文件

| 文件 | 作用 |
|---|---|
| `SKILL.md` | AI 主读本(描述 / 唤醒词 / 路由规则 / 功能详细说明) |
| `作息管家.html` | 用户手册镜像(由 `help_render.py` 派生 · ADR-0001) |
| `references/scenarios.yaml` | 场景资产(§07 契约 · 唯一事实源 · 73 场景) |
| `references/*.md` | 7 份参考文档(数据库 / 操作规范 / CLI / 同步流程 / 分类心法 等) |
| `scripts/*.py` | CLI 入口 + 数据库 + 验证器 + 计算层 + 帮助渲染器 |
| `templates/*.html` | 15 个 HTML 模板(record 6 + plan 5 + receipt 2 + help 1 + 共享 CSS/JS 2) |
| `tests/*.py` | 11 个 pytest 测试文件 |
| `docs/adr/*.md` | 架构决策记录(ADR-0001/0002/0003 已落盘) |
| `CHANGELOG.md` | 12 个 Phase 变更日志 |

## 当前阶段(2026-07-28 Grilling 闭环)

8 决策全部答完,3 份 ADR 落盘,4 个实施 Phase 待执行:

| Phase | 工作 | 阻力 | Tested-By |
|---|---|---|---|
| **A-3** | ADR-0001 · `help_render.py` 同步作息管家.html | 最小 | exempt |
| A-2 | Q8 · 补 `AGENTS.md`(本文件) | 小 | exempt |
| A-1 | Q5+Q6+Q7 · 路径对齐 + 复制 prompt + 内部分组 | 大 | **pending-FAT** |
| B | pytest + FAT 验证 | — | — |

> **本文件就是 Phase A-2 的实施产物**。落地后更新此处的 "Phase A-2" 状态为"完成"。

## Agent 工作约定

1. **所有 CLI 调用** 走 `python scripts/schedule_cli.py <cmd>`,**禁止直连数据库**
2. **所有 HTML 输出** 走 `python scripts/schedule_cli.py render-*` + 派生脚本(`help_render.py`)
3. **唤醒词 → CLI 命令路由** 见 SKILL.md §"路由规则"章节(已在 § 365-486 行)
4. **HTML-First 默认**(总纲 §04 原则 11):唤醒词命中 SKILL 后,若有 HTML 输出路径,默认 invoke HTML 工作流
5. **单工铁律**(总纲 §04 原则 10):过程型 HTML 必有"复制 prompt"按钮 + 4 部分结构
6. **5 状态 fallback**(总纲 §04 原则 4):正常 / 空 / 缺数据 / 错误 / 离线

## 跨 Skill 路由

| 唤醒词重叠场景 | 路由到 |
|---|---|
| "健身"(作息上下文) | **作息管家**(record 域) |
| "健身"(饮食上下文) | 卡路里 |
| "心愿"(作息上下文) | **作息管家**(plan 域,商量计划时拉心愿) |
| "心愿"(独立) | 备忘录 |
| "打卡"(复盘上下文) | **作息管家**(plan 域,复盘时关联打卡) |
| "打卡"(独立) | 备忘录 |

判定:作息管家只在"作息/计划/复盘"明确上下文中接管;其他上下文路由给卡路里 / 备忘录。

## 引用

- 总纲:`SKILLS/SKILL开发总纲V1.0/`(元规范 · 必读)
- 本 Skill:`SKILLS/作息管家/`(本仓库)
- 总纲 §00 元规范 §02 5 层骨架 §03 触发词 §04 可视化 §05 工程仪式 §07 HELP 契约
- 本仓库根 AGENTS.md · docs/agents/issue-tracker.md · docs/agents/domain.md