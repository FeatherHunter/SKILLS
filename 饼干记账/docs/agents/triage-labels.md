# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this Skill's issue tracker (本地 markdown, 以 issue 文件 frontmatter / 状态行记录).

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

## How status is recorded in markdown

- 每个 issue 文件顶端写一行：`Status: needs-triage`（或上述 5 个标签之一）
- 编号连续递增（`01-`, `02-`, …）
- 关闭 issue 时改为 `Status: wontfix` 或在 `## Answer` 后归入 `ready-for-human`