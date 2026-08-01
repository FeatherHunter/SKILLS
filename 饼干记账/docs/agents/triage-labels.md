# Triage 标签 · 饼干记账

本目录的 triage 标签按仓库根协议统一映射到 GitHub Issues（详见 `D:\2Study\StudyNotes\SKILLS\docs\agents\triage-labels.md`）。

## 分类（每个 issue 必带 1 个）

| 角色 | GitHub Label | 含义 |
| --- | --- | --- |
| `bug` | `bug` | 现有行为有缺陷 |
| `enhancement` | `enhancement` | 新功能或改进 |

## 状态（每个 issue 必带 1 个）

| 角色 | GitHub Label | 含义 |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | 维护者需要评估 |
| `needs-info` | `needs-info` | 等报告人补充信息 |
| `ready-for-agent` | `ready-for-agent` | 已规格化，可交 AFK agent 执行 |
| `ready-for-human` | `ready-for-human` | 需人工实施 |
| `wontfix` | `wontfix` | 不会处理 |

## 技能命名空间（每个 issue 必带 1 个）

| 技能目录 | GitHub Label |
| --- | --- |
| `饼干记账/` | `skill:饼干记账` |

## 维护规则

- 完整协议与 PAT 安全备注见仓库根 `docs/agents/triage-labels.md`
- 本目录只维护本技能相关的 skill-namespace 映射
- 修改实际字符串后，`/triage` 与 `/to-tickets` 会自动同步读根文件