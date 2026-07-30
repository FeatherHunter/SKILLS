# v3 收尾清理 · Spec

> **状态**:ready-for-agent
> **创建日期**:2026-07-29
> **来源**:grill-with-docs 阶段(D8/D9/D11 沉淀),to-spec 整合
> **目标 issue tracker**:本仓库 `.scratch/v3-cleanup-tickets/spec.md`
> **前置依赖**:`.scratch/intent-v3-refactor/` 8 张工单已全部 implement 并 commit(详见 CONTEXT.md)

---

## Problem Statement

`intent.json v3.0` 重构主线 8 张工单已完成(从 spec §4 到 HTML 编辑器全栈落地),但 grill 阶段识别的 3 个**残留 bug / 待办**没解决。如果不收尾,这些不一致会持续误导 HTML 用户、AI 路由、未来开发者。

**3 个待办**(grill 第 3 题已确认):

1. **AI 路由表 2 处仍写 `color-grade`**(D8 决策遗漏迁移)→ 实际 JSON 用 `color`(HTML 段面板生产),AI 按路由表无法匹配,会被迫猜
2. **D1-D7 仍是 CONTEXT.md 里的"Pre-ADR"** → 没正式进 `docs/adr/`,未来工程师找不到"为什么这么设计"的权威解释
3. **`docs/superpowers/` 目录没迁到 `_archive/`**(D5 决策没执行)→ 旧(superpowers)技能产物仍在仓库顶层,误以为是生产指南

**用户视角**:
- vlog 作者用 HTML 编辑器,勾选段内"调色" op,保存 JSON 是 `color`(正确),但 AI 看路由表找 `color-grade`(旧名字),路由失败
- 6 个月后维护者看 spec,想知道"为什么 v3.0 抛弃 6 选 1 ending enum",**查不到 ADR**
- 任何人打开 `docs/superpowers/specs/`,以为是当前 spec,实则历史档案

**当前痛点**:
- AI 路由表与 HTML/JSON Schema 矛盾,任何小 bug 都会让 AI 走错路径
- D1-D7 没有 ADR,违反 **D11 最高指导原则**——"任何小 bug 必须修复,不留尾巴"
- `_archive/` 目录不存在,违反 D5 决策

---

## Solution

**3 张 vertical-slice tickets**,每个独立可执行,共享单一 seam:

1. **`01-md-color-migration.md`** — AI 路由表 2 处 `color-grade` → `color` 同步(D8 决策落地)
2. **`02-adr-formalize.md`** — 8 个 D 决策转正式 ADR,新建 `docs/adr/0001-0008-slug.md` + 1 个 D11 原则文档
3. **`03-archive-superpowers.md`** — `docs/superpowers/` → `_archive/superpowers/` 目录重命名(D5 决策落地)

完成 3 张后,v3.0 重构**完整闭环**:协议层 / 编辑器层 / 文档层 / ADR 层 / 仓库结构全部一致。

---

## User Stories

### ADR 层

1. 作为 **6 个月后维护者**,我希望能查 `docs/adr/` 找到"为什么 v3.0 抛弃 ending.type enum"的解释,以便**不需要靠 git log 推断**
2. 作为 **新加入项目的工程师**,我希望有 ADR 索引(`docs/adr/README.md` 或类似),以便**快速理解核心决策**
3. 作为 **D11 原则守护者**,我希望 `docs/adr/` 有 1 篇纲领性文件,记录"本次重构的整体哲学",以便**未来重构不偏离**

### 文档层

4. 作为 **AI 工作流**,我希望读 `references/AI路由表-意图JSON字段枚举.md` 时看到的 op 命名**与 JSON Schema 一致**,以便**不猜**
5. 作为 **HTML 编辑器用户**,我希望勾选段内"调色" op 后,AI 能**正确路由**(D8 已决策 color,本工单落地)
6. 作为 **doc 维护者**,我希望 grep `color-grade` **只命中历史档案**(spec/历史 spec),**不命中当前生产文档**

### 仓库结构层

7. 作为 **任何打开仓库的人**,我希望 `docs/` 下**只有当前生效的 spec/md**,历史产物统一在 `_archive/`,以便**不误判**
8. 作为 **执行者**,我希望 `git mv` 命令**保持 git history 连续**,以便**追溯历史修改**
9. 作为 **AI 技能加载者**,我希望 `_archive/` 是**只读语义**(看一眼就懂:这是历史),以便**不会再被加载到生产 prompt**

---

## Implementation Decisions

### ID1 · AI 路由表 D8 迁移(D8 决策遗漏)

- **修改文件**:`references/AI路由表-意图JSON字段枚举.md` 2 处
- **修改内容**:
  - 第 1 节字段枚举表 `time_segments[].ops` 枚举:`color-grade` → `color`
  - 第 2 节 AI 路由表 `time_segments[j].ops.color-grade` → `color`
- **依据**:D8 决策(2026-07-29 grill 第 1 题)— 段内调色 op 命名统一为 `color`(不带 `-grade`)
- **不动**:
  - spec §7 / JSON Schema / HTML `SEGMENT_OPS_SCHEMA` — 全部已对齐 D8
  - `lib/video_processing.py` `build_video_filter` — 读 `ops.color`,不读 op 名,不受影响
- **验证**:`references/tests/test_intent_v3_schema.py` B5 测试覆盖,本工单无新测试需求

### ID2 · 8 个 ADR 撰写

**ADR 编号规划**(8 个 + 1 个纲领):

| # | Slug | 标题 | 对应 CONTEXT D |
|---|---|---|---|
| 0001 | v3-schema-version | schema_version="3.0" 必填,D1 核心 | D1 |
| 0002 | ending-v4-template | ending 重构成 V4(template + prompt),抛弃 6 选 1 enum | D2 |
| 0003 | only-v3-schema | 只支持 schema_version=3.0,老文件报错(D4) | D4 |
| 0004 | archive-superpowers | superpowers 归档到 _archive/(D5) | D5 |
| 0005 | md-first | md 文档层(Layer 2A)优先于 Python 编排层(Layer 2B) | D6 |
| 0006 | trim-cuts-deprecated | 5 个该消失的 op(trim-head/tail/cut-middle/pin-range/target-duration)严格删除 | D7 |
| 0007 | color-op-no-grade | 段内调色 op 命名为 color(不带 -grade) | D8 |
| 0008 | segment-id-format | 段 ID 格式 seg_V_N(V 视频索引,N 段序号) | D9 |
| 0009 | v3-principles | v3.0 重构纲领(D11 最高指导原则) | D11 |

**格式**:每篇 1-3 句话正文 + 可选 `Status: accepted` frontmatter。

**位置**:`docs/adr/0001-v3-schema-version.md` 等。

### ID3 · `docs/superpowers/` 目录重命名

- **执行命令**:`git mv docs/superpowers _archive/superpowers`
- **依据**:D5 决策(2026-07-29)— superpowers 技能流不再使用,产物移到 `_archive/`
- **不动**:`.scratch/intent-v3-refactor/`(spec/issues 仍在本目录,因为它还有用)、`docs/adr/`(新建)
- **验证**:`git log --follow _archive/superpowers/specs/2026-07-25-video-time-segment-model.html` 应该看到历史 commit(可能因文件名变更显示 'renamed' 而非完整 history,这是 git 行为)

---

## Testing Decisions

### 单一 seam 测试边界:`references/tests/test_intent_v3_schema.py` + `智剪工坊-意图编辑-tests/test_html_v3_structure.py`

**为什么是这两个**:本次新工作**纯文档 + 纯目录移动 + 纯文件创建**,**不引入新代码 seam**。

### 测试策略

| Ticket | 测试需求 | 测试来源 |
|---|---|---|
| 01 md color migration | 0 新测试(回归即可) | 现有 `test_intent_v3_schema.py` 覆盖 |
| 02 ADR 撰写 | 0 测试(ADR 是文档) | 人工 review |
| 03 archive superpowers | 0 测试(目录移动) | `git log --follow` 验证 history 连续 |

### 验证标准

- **Ticket 01 完成后**:
  - `grep -n "color-grade" references/AI路由表-意图JSON字段枚举.md` 输出 0 行
  - `grep -rn "color-grade" references/` 输出只在 spec 历史档案或 ADR 8 中(已废弃标注)
  - 现有 `references/tests/test_intent_v3_schema.py` 全过
  - 现有 `智剪工坊-意图编辑-tests/test_html_v3_structure.py` 全过
- **Ticket 02 完成后**:
  - `ls docs/adr/` 列出 0001-0009 共 9 个文件
  - 每个文件 1-3 句话正文,无 TBD/占位
- **Ticket 03 完成后**:
  - `ls docs/superpowers/` 不存在(404)
  - `ls _archive/superpowers/` 存在(内容完整)
  - `git log --follow _archive/superpowers/specs/2026-07-25-video-time-segment-model.html` 显示历史

### Prior art

- **测试风格**:`references/tests/test_intent_v3_schema.py` 用 plain assert + 装饰器模式(本工单沿用)
- **ADR 格式**:按 `domain-modeling/ADR-FORMAT.md` 1-3 句话正文
- **目录归档模式**:历史上 `references/` 已有多个 md(没有 `_archive/` 先例,但有 .archive 命名约定——本次沿用 D5)

---

## Out of Scope

1. **D3(10 个 ending 模板)** —— UX 决策,不入 ADR(放 spec §3 即可)
2. **段内 op filter 实现** —— 这是 AI 工作流组合 atomic CLI 的事,不是 `lib/video_processing.py` 的职责(D11 原则)
3. **CONTEXT.md 重写** —— D1-D11 已在 CONTEXT.md 沉淀,8 个 ADR 完成后可**选择性删除** Pre-ADR 段落(避免重复),但**不重写**整个 CONTEXT
4. **新 ADR 创建工具** —— 8 个 ADR 手写,后续如果需要可单独工单
5. **`_archive/` 目录下的二级清理** —— 移完目录后,内部文件**保持原状**(只有目录移动,无内容清理)
6. **git 历史重写** —— `git mv` 已保留 history,无需 force push 或 rebase

---

## Further Notes

### 与 CONTEXT.md 关系

完成后,**8 个 ADR 是权威解释**,CONTEXT.md 里的"Pre-ADR"段落可降级为**索引摘要**(指向 `docs/adr/`)。本次 spec **不要求**改 CONTEXT.md,留给后续清理工单。

### 与 8 张主工单的关系

8 张主工单(spec/路由表/SKILL/其他 md/编排/Python/HTML)是**实现层**;
本次 3 张工单(ADR/路由表迁移/目录归档)是**收敛层**——确保"代码、文档、目录结构"三者自洽。

### D11 原则的应用

本次 spec 严格遵守 D11:**任何小 bug 必须修复,不留尾巴**。
3 个 ticket 都是"前面决策的遗漏执行",按 D11 必须收尾。

---

_Generated: 2026-07-29 · to-spec · ready-for-agent · 3 vertical-slice tickets_