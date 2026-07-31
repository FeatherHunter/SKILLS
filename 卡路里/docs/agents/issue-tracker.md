# 卡路里 · 问题追踪协议

本目录的问题（issue）与规格（PRD）按仓库根协议统一发布到 **GitHub Issues**（`FeatherHunter/SKILLS`）。本文件是仓库根 `docs/agents/issue-tracker.md` 在卡路里技能内的子协议说明。

> 完整协议与 PAT 安全备注见 `D:\2Study\StudyNotes\SKILLS\docs\agents\issue-tracker.md`。

## 卡路里的分区标识

| 字段 | 值 |
|---|---|
| 标题前缀 | `[卡路里]` |
| 技能 label | `skill:卡路里` |
| 分类 label | `bug` / `enhancement` |
| 状态 label | `needs-triage` / `needs-info` / `ready-for-agent` / `ready-for-human` / `wontfix` |

新建 issue 时**必须**同时携带 1 个 `skill:卡路里` label + 1 个分类 label + 1 个状态 label。

## 卡路里本地 `.scratch/` 的角色（迁移后）

按仓库根协议："本次提交日为分界线"。

- **历史**：`卡路里/.scratch/` 视为只读归档（wayfinder 决策地图、help-scenario-redesign.md、cross-skill/、research/、tickets/）。
- **未来**：新建 / 讨论 / 关闭 issue 全部走 GitHub Issues。
- **本地 .scratch/ 与 GitHub 的关系**：本地是**决策地图**（work in progress），GitHub 是**用户可见问题**（bug / feature request / 跨技能协调）。

## 卡路里的 wayfinder 决策地图（已存在）

按 wayfinder 协议，卡路里的决策地图在：

```
卡路里/.scratch/wayfinder-v1.0-help-redesign.md
```

此文档是**本地决策索引**，**不提交到 GitHub Issues**（除非用户显式要求）。

## 卡路里 v1.0 的实现 ticket（本地决策）

按 wayfinder 流程，11 个分类的实现 ticket 在：

```
卡路里/.scratch/tickets/01-主页.md
卡路里/.scratch/tickets/02-饮食.md
卡路里/.scratch/tickets/03-体重.md
卡路里/.scratch/tickets/04-运动.md
卡路里/.scratch/tickets/05-健身计划.md
卡路里/.scratch/tickets/06-目标管理.md
卡路里/.scratch/tickets/07-基础信息.md
卡路里/.scratch/tickets/08-身体细节.md
卡路里/.scratch/tickets/09-身材照片.md
卡路里/.scratch/tickets/10-分析.md
卡路里/.scratch/tickets/11-技能协同.md
```

**11 个 ticket 全部将发布到 GitHub Issues**（用户已确认全部提交），以 `wayfinder:map` 风格的元 issue + 11 个子 issue 结构呈现。

## 卡路里独有约束

按 `.scratch/help-scenario-redesign.md` 与 `.scratch/wayfinder-v1.0-help-redesign.md`：

- 命名规范 v1.0（3 条核心规则）
- 推迟即砍（不存在推迟开发的功能）
- 联动分类最后开发（卡路里 ↔ 外部技能相向而行 + 对接）
- 不在脚本中强制联动约束（在协作文档 `.scratch/cross-skill/README.md` 中体现）

## 命令示例（卡路里场景）

```bash
gh issue create \
  --title "[卡路里] 主页 14 场景的 prompt 与触发词落地" \
  --body-file <(cat <<'EOF'
## 背景
按 wayfinder 决策地图，卡路里 v1.0 共 514 场景，分 11 分类。本 ticket 对应主页 14 场景。

## 任务
详见 卡路里/.scratch/tickets/01-主页.md

## 子任务
- 14 个触发词写入 scripts/_triggers.py
- 每个场景 prompt 撰写完成
- 与主页 widget 数据对接
EOF
) \
  --label "skill:卡路里,enhancement,ready-for-agent"

gh issue list --state open --label "skill:卡路里"
gh issue list --state open --label "ready-for-agent"
```

## 文件历史说明

本文件原内容描述"本地 markdown"（`.scratch/`），是仓库迁移到 GitHub Issues 之前的快照。2026-07-30 按用户决策升级为 GitHub Issues 协议，与仓库根同步。