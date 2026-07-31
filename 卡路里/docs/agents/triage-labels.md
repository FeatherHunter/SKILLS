# Triage Labels（卡路里子协议）

engineering skills 使用五个标准的 triage 角色来表达 issue 的处理阶段。本文件是仓库根 `docs/agents/triage-labels.md` 在卡路里技能内的子协议，与根协议一致。

## 五状态二分类标签

### 状态标签（互斥）

| mattpocock/skills 标签 | 我们的标签 | 含义 |
|---|---|---|
| `needs-triage` | `needs-triage` | 维护者需要评估此 issue |
| `needs-info` | `needs-info` | 等待提交者补充更多信息 |
| `ready-for-agent` | `ready-for-agent` | 已完整定义，可交给 AFK agent 执行 |
| `ready-for-human` | `ready-for-human` | 需要人工实现 |
| `wontfix` | `wontfix` | 不会处理 |

### 分类标签

| 标签 | 含义 |
|---|---|
| `bug` | 问题报告 |
| `enhancement` | 功能增强 |

### 技能分区 label（卡路里相关）

| 标签 | 用途 |
|---|---|
| `skill:卡路里` | 卡路里技能相关 issue |

每个被处理的 issue **必须**同时携带 1 个 `skill:卡路里` + 1 个分类 + 1 个状态 = **3 个 label**。

## 卡路里 v1.0 ticket 的 label 应用

按 wayfinder 决策，所有 11 个 ticket 创建时默认打：

```
skill:卡路里,enhancement,ready-for-agent
```

- `ready-for-agent`：因为 ticket 已完整定义（含 Question + Notes + Success Criteria），可直接派给 agent
- `enhancement`：因为是 v1.0 改进而非 bug

## 联动分类特别说明

ticket 11-技能协同 = **最后开发**，初始 label：

```
skill:卡路里,enhancement,needs-triage
```

因依赖外部技能实现，需先标记 `needs-triage` 等其他技能接口就绪后才转为 `ready-for-agent`。

## 状态流转

```
needs-triage → ready-for-agent → (in_progress) → closed
     ↓              ↓
  needs-info   ready-for-human
```

## 文件历史

本文件原内容（迁移前快照）描述本地 markdown 协议。2026-07-30 按用户决策升级为 GitHub Issues 协议，与仓库根 `docs/agents/triage-labels.md` 同步。