# 卡路里 · Domain Docs（领域文档协议）

engineering skills 在探索卡路里技能时如何消费领域文档。本文件是仓库根 `docs/agents/domain.md` 在卡路里技能内的子协议。

## 探索之前，先读这些

### 单上下文仓库布局

本仓库（`FeatherHunter/SKILLS`）是单上下文布局：

```
/
├── CONTEXT.md                              ← 仓库根术语表
├── docs/adr/                                ← 仓库级 ADR
├── docs/agents/                             ← 工程 skill 配置
│   ├── issue-tracker.md
│   ├── triage-labels.md
│   └── domain.md
└── <技能名>/                                ← 平级技能
    ├── AGENTS.md                            ← 技能级 AI 入口
    ├── CONTEXT.md                           ← 技能级术语
    ├── docs/agents/                         ← 技能级 skill 配置
    ├── docs/adr/                            ← 技能级 ADR（按需）
    └── .scratch/                            ← 工作目录
```

### 探索卡路里技能时应读

1. **`D:\2Study\StudyNotes\SKILLS\卡路里\CONTEXT.md`** —— 卡路里技能术语表
2. **`D:\2Study\StudyNotes\SKILLS\CONTEXT.md`** —— 仓库根术语表（如果有跨技能概念）
3. **`D:\2Study\StudyNotes\SKILLS\卡路里\docs\adr\`** —— 卡路里技能级 ADR
4. **`D:\2Study\StudyNotes\SKILLS\docs\adr\`** —— 仓库根 ADR（如果有跨技能决策）

## 卡路里的 ADR（已存在）

| ADR | 主题 |
|---|---|
| ADR-0001 | HELP HTML 作为根目录 mirror |
| ADR-0004 | CLI flag 校验 |
| ADR-0005 | Tested-By 行末规则 |
| ADR-0006 | 测试 DB 隔离 |
| ADR-0007 | AI 验证协议 |

## 文件结构

```
D:\2Study\StudyNotes\SKILLS\卡路里\
├── CONTEXT.md                              ← 技能术语表
├── AGENTS.md                              ← AI 协作入口
├── SKILL.md                               ← 技能说明书（AI 加载技能时阅读）
├── 卡路里.html                              ← HELP HTML（用户视角）
├── _meta.json
├── config-calorie.ts
├── 健身计划.html
├── 作者的笔记/
│   └── 卡路里场景设计.md                   ← 个人查看版
├── body_photos_gif/
├── calorie_data.db
├── calorie_html/
├── docs/
│   ├── adr/                               ← 卡路里级 ADR
│   ├── agents/
│   │   ├── issue-tracker.md               ← GitHub Issues 协议
│   │   ├── triage-labels.md               ← 5 状态 + 2 分类
│   │   └── domain.md                       ← 本文件
│   └── superpowers/
├── references/
├── scripts/                                ← CLI + 渲染脚本
├── templates/                              ← HTML 模板
└── .scratch/                               ← 工作目录
    ├── wayfinder-v1.0-help-redesign.md    ← wayfinder 决策地图
    ├── help-scenario-redesign.md           ← 命名规范 + 想法记录
    ├── cross-skill/                        ← 联动协议（最后开发）
    ├── tickets/                            ← 11 个实现 ticket
    └── research/                            ← 11 份 CLI 现状研究报告
```

## 使用 glossary 的词汇

引用卡路里技能概念时，使用 `卡路里/CONTEXT.md` 中定义的术语（如「卡路里缺口」「TDEE」「看稳不稳」）。

## 标记 ADR 冲突

如果你的输出与 ADR-0001 / ADR-0004 / ADR-0005 / ADR-0006 / ADR-0007 冲突：

> _Contradicts ADR-0007 (AI 验证协议) —— 但值得重新讨论，因为……_

## 文件历史

本文件原内容（迁移前快照）描述本地 markdown 协议。2026-07-30 按用户决策升级为 GitHub Issues 协议，与仓库根 `docs/agents/domain.md` 同步。