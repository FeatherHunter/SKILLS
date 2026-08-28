# 0000 · ADR 目录初始化

**状态**：接受
**决策者**：setup-matt-pocock-skills 初始化流程
**日期**：2026-08-28
**相关 issue**：（本仓库初始化）

## 背景

仓库级工程技能（wayfinder / triage / domain-modeling 等）在进入仓库时需要读取 `docs/adr/` 了解历史决策。此前该目录不存在，domain-modeling 技能按懒创建原则不主动建——但在首次触发 `/domain-modeling` 时需要目录就绪。

## 决策

建立 `docs/adr/` 目录，内置一份 README.md 说明命名规范、模板和写入规则，作为技能进入时的约定入口。

## 后果

- ✅ 首次运行 domain-modeling 时无需等待 lazy creation，可直接写入 ADR
- ⚠️ ADR 目录为空意味着暂无决策记录；一旦有人填第一条，后续必须遵循本模板
