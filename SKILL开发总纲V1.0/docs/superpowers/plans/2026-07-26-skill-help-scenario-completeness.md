# Skill HELP 场景完备性总纲重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不丢失现有有效规范的前提下，为《SKILL开发总纲V1.0》增加每个 Skill 必须具备 HELP 唤醒词、完整场景资产和响应式 HELP HTML 的正式契约。

**Architecture:** 新增 `07-HELP与场景完备性.md` 作为唤醒词、场景、稳定 prompt、状态和 HELP HTML 之间的唯一权威章节。`SKILL.md` 保留 AI 入口和硬钩子，`03` 保留唤醒词结构，`04` 保留 HTML 技术规则，`05` 保留工程与测试流程；各处只增加职责边界和交叉引用。主 HTML 镜像与架构图同步反映新章节，但不手工复制多份独立场景规则。

**Tech Stack:** Markdown、静态 HTML 镜像、现有本地 grep/链接检查；不新增运行时依赖，不修改具体 Skill 业务代码。

---

## 文件职责与变更范围

- Create: `07-HELP与场景完备性.md`：新契约正文。
- Modify: `SKILL.md`：HELP 核心行为、文件清单和入口规则。
- Modify: `README.md`：07 章节和 HELP 资产说明。
- Modify: `01-第一性原理.md`：HELP 的可发现性和验收定位。
- Modify: `02-5层骨架.md`：场景资产在文档层、可演进和自检中的位置。
- Modify: `03-触发词设计v2.md`：唤醒词必须展开完整场景。
- Modify: `04-可视化与注入v2.md`：HELP HTML 与 HTML 技术规则的边界。
- Modify: `05-工程仪式.md`：场景资产、HELP 生成和响应式验证流程。
- Modify: `06-附录.md`：HELP 场景完备性对改造与 FAT 的影响。
- Modify: `SKILL开发总纲V1.0.html`：同步主 HTML 镜像。
- Modify: `架构图.html`：同步文件角色、阅读路径和职责映射。
- Preserve: `_assets/style.css`、`_assets/injector.py`、`_assets/template_skeleton.html`，除非发现直接冲突，不在本次文档重构中修改。

## Task 1: 建立 07 章节正文

**Files:** Create `07-HELP与场景完备性.md`; Reference `docs/superpowers/specs/2026-07-26-skill-help-scenario-completeness-design.md`。

- [ ] 写入章节职责：07 是 HELP 唤醒词、完整场景、稳定 prompt、状态和 HELP HTML 的专门权威，不重复 03 的四元组细节或 04 的注入实现细节。
- [ ] 写入 HELP 唤醒词规则：每个 Skill 必须有专属 HELP；登记在唤醒词声明中但不是普通业务词；HELP 页面不展示自身；命中后必须走 HTML 工作流。
- [ ] 写入场景完整性：每个唤醒词穷举全部合法场景；数量不设上限；不能因页面大小或开发成本删减合法组合。
- [ ] 写入场景维度：时间范围、查询视角、对比、筛选、排序、数据状态只是示例，可继续增加。
- [ ] 写入场景资产字段：`wake_word`、`scenario_id`、`scenario_title`、`dimensions`、`prompt`、`status`、`result`；场景资产是正式开发产物和 HELP 的唯一事实来源。
- [ ] 写入 prompt 与状态：prompt 只表达稳定用户意图；禁止 CLI、数据库字段、Python 文件、模板文件和易变调用步骤；无状态=可用，`【待开发】`=不可执行；待开发场景仍展示执行 prompt，但 AI 收到后停止并说明状态。
- [ ] 写入 HELP HTML 要求：全场景、独立复制按钮、Toast、大规模导航、错误页、手机/PC/横竖屏、触摸、换行、剪贴板降级和视口验证。

## Task 2: 更新 AI 入口与人类目录

**Files:** Modify `SKILL.md`, `README.md`。

- [ ] 在 `SKILL.md` 保留现有 HTML-First，增加 HELP 命中必须调用 HELP HTML、普通唤醒词按场景资产状态执行、`【待开发】`不得执行。
- [ ] 在 `SKILL.md` 文件清单中增加 07，修正章节/文件描述，保留 01—06、资产和主 HTML 镜像条目。
- [ ] 在 `README.md` 增加 07 的用途、阅读时机和“HELP 由场景资产生成”的说明。

## Task 3: 更新架构与触发词章节

**Files:** Modify `01-第一性原理.md`, `02-5层骨架.md`, `03-触发词设计v2.md`。

- [ ] 01：把 HELP 定位为可发现性入口、意图目录和完整性验收入口。
- [ ] 02：把场景资产纳入文档层正式产物、可演进规则、影响文件清单、Fresh Agent 和文档自检。
- [ ] 03：保留四元组、数量、变体、路由和相对时间规则，增加唤醒词设计后必须穷举合法场景并写入场景资产。

## Task 4: 更新 HTML、工程和附录章节

**Files:** Modify `04-可视化与注入v2.md`, `05-工程仪式.md`, `06-附录.md`。

- [ ] 04：保留 11 原则、单工铁律和 HTML-First，增加 HELP 从场景资产生成、排除自身、复制/Toast、移动端/PC 适配的交叉引用。
- [ ] 05：扩展 HTML 模板 SOP，加入场景资产、待开发状态、HELP 生成、手机/PC 视口、复制和 Toast 检查。
- [ ] 06：规定新增或修改唤醒词、场景维度、prompt、状态、CLI 或工作流时重新检查场景资产和 HELP；待开发触发行为纳入 FAT。

## Task 5: 同步两个 HTML 镜像

**Files:** Modify `SKILL开发总纲V1.0.html`, `架构图.html`。

- [ ] 主总纲 HTML 增加第七部分，包含 HELP 硬规则、场景无限上限、稳定 prompt、`【待开发】`、响应式 HTML 和唯一事实来源。
- [ ] 主 HTML 的 SOP、钩子和自检摘要纳入 HELP 场景资产检查，同时保留原有 HTML 同步、单工铁律和 HTML-First。
- [ ] 架构图标记 07 为新契约章节，说明其与 03、04、05 的职责边界，并校正文件计数和阅读路径。

## Task 6: 文档一致性验证

**Files:** Verify all files listed above。

- [ ] 逐条核对设计文档：HELP 唤醒词、自身排除、场景无限上限、场景维度、资产字段、稳定 prompt、二态状态、待开发停止执行、自动生成、复制按钮、Toast、响应式和原有内容保留。
- [ ] 运行：

```bash
grep -RInE '07-HELP与场景完备性|HELP|场景资产|待开发' SKILL.md README.md 01-第一性原理.md 02-5层骨架.md 03-触发词设计v2.md 04-可视化与注入v2.md 05-工程仪式.md 06-附录.md SKILL开发总纲V1.0.html 架构图.html 07-HELP与场景完备性.md
```

Expected：07 可定位，各章节有明确职责说明，未把 HELP 唤醒词列为 HELP 页面业务场景。

- [ ] 检查原有 5 层、6 特性、8 反模式、触发词 v2、11 HTML 原则、Fresh Agent、附录、资产和来源声明仍存在或有明确引用。
- [ ] 运行：

```bash
git status --short
git diff --stat
git diff --check
```

Expected：变更仅限总纲文档、两个 HTML 镜像和 07；无空白错误；不修改具体 Skill 业务代码或生成物。
