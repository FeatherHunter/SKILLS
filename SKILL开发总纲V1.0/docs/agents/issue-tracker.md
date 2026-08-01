# SKILL开发总纲V1.0 · 问题追踪协议

本目录的问题（issue）与规格（PRD）按仓库根协议统一发布到 **GitHub Issues**（`FeatherHunter/SKILLS`）。本文件是仓库根 `docs/agents/issue-tracker.md` 在 SKILL开发总纲V1.0 内的子协议说明。

> 完整协议与 PAT 安全备注见 `D:\2Study\StudyNotes\SKILLS\docs\agents\issue-tracker.md`。

## SKILL开发总纲V1.0 的分区标识

| 字段 | 值 |
|---|---|
| 标题前缀 | `[SKILL开发总纲V1.0]` |
| 技能 label | `skill:SKILL开发总纲V1.0` |
| 分类 label | `bug` / `enhancement` |
| 状态 label | `needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix` |

新建 issue 时**必须**同时携带 1 个 `skill:SKILL开发总纲V1.0` label + 1 个分类 label + 1 个状态 label。

## 跨技能协调

总纲项目下的 issue 多为**跨技能协调 / 协议规范**类（如 HTML 交付规范、commit 格式、HTML 镜像约定等），影响所有技能。新建 issue 时建议同时携带 `cross-skill` label，便于跨技能检索。

## 命令示例（总纲场景）

```bash
gh issue create \
  --title "[SKILL开发总纲V1.0] <标题>" \
  --body-file <(cat <<'EOF'
## 背景
...
## 影响范围
...
## 任务
...
EOF
) \
  --label "skill:SKILL开发总纲V1.0,cross-skill,<分类>,<状态>"

gh issue list --state open --label "skill:SKILL开发总纲V1.0"
gh issue list --state open --label "cross-skill"
```

## 文件历史说明

本文件原内容描述"本地 Markdown"（`.scratch/`），是仓库迁移到 GitHub Issues 之前的快照。2026-08-01 按用户决策升级为 GitHub Issues 协议，与仓库根同步。