# 备忘录 · 问题追踪协议

本目录的问题（issue）与规格（PRD）按仓库根协议统一发布到 **GitHub Issues**（`FeatherHunter/SKILLS`）。本文件是仓库根 `docs/agents/issue-tracker.md` 在备忘录技能内的子协议说明。

> 完整协议与 PAT 安全备注见 `D:\2Study\StudyNotes\SKILLS\docs\agents\issue-tracker.md`。

## 备忘录的分区标识

| 字段 | 值 |
|---|---|
| 标题前缀 | `[备忘录]` |
| 技能 label | `skill:备忘录` |
| 分类 label | `bug` / `enhancement` |
| 状态 label | `needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix` |

新建 issue 时**必须**同时携带 1 个 `skill:备忘录` label + 1 个分类 label + 1 个状态 label。

## 命令示例（备忘录场景）

```bash
gh issue create \
  --title "[备忘录] <标题>" \
  --body-file <(cat <<'EOF'
## 背景
...
## 任务
...
EOF
) \
  --label "skill:备忘录,<分类>,<状态>"

gh issue list --state open --label "skill:备忘录"
gh issue list --state open --label "ready-for-agent"
```

## 文件历史说明

本文件原内容描述"本地 markdown"（`.scratch/`），是仓库迁移到 GitHub Issues 之前的快照。2026-08-01 按用户决策升级为 GitHub Issues 协议，与仓库根同步。