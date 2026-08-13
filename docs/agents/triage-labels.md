# Triage 标签

技能以七个标准 triage 角色表述。本文件把这些角色映射到本仓库 issue tracker（GitHub Issues）实际使用的 label 字符串。

## 分类（Category，每个 issue 必带 1 个）

| mattpocock/skills 角色 | GitHub Label | 含义 |
| --- | --- | --- |
| `bug` | `bug` | 现有行为有缺陷 |
| `enhancement` | `enhancement` | 新功能或改进 |

## 状态（State，每个 issue 必带 1 个）

| mattpocock/skills 角色 | GitHub Label | 含义 |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | 维护者需要评估 |
| `needs-info` | `needs-info` | 等报告人补充信息 |
| `ready-for-agent` | `ready-for-agent` | 已规格化，可交 AFK agent 执行 |
| `ready-for-human` | `ready-for-human` | 需人工实施 |
| `wontfix` | `wontfix` | 不会处理 |

## 技能命名空间（每个 issue 必带 1 个）

| 技能目录 | GitHub Label |
| --- | --- |
| `备忘录/` | `skill:备忘录` |
| `卡路里/` | `skill:卡路里` |
| `居家管家/` | `skill:居家管家` |
| `饼干记账/` | `skill:饼干记账` |
| `智剪工坊/` | `skill:智剪工坊` |
| `作息管家/` | `skill:作息管家` |
| `SKILL开发总纲/` | `skill:SKILL开发总纲` |
| `公共组件/`（Base Skill, 跨技能公共层） | `skill:公共组件` |

## 跨技能主题（可选）

| GitHub Label | 含义 |
| --- | --- |
| `cross-skill` | 同时影响多个技能（如共享脚本、文档规范） |
| `docs` | 纯文档 / ADR / 注释 |
| `infra` | 仓库基础设施（钩子、CI、submodule） |

## 维护规则

- 当某技能说"应用 triage 标签"时，按上表查实际字符串。
- 新增技能目录时同步在本文件追加一行 `skill:<名>`。
- 修改实际字符串后，`/triage` 与 `/to-tickets` 会自动同步读本文件。