# AGENTS.md — 饼干记账

## Agent skills

### Issue tracker

GitHub Issues（`FeatherHunter/SKILLS`），标题前缀 `[饼干记账]` + `skill:饼干记账` label 分区。详见仓库根 `docs/agents/issue-tracker.md`。

### Triage labels

沿用 5 个默认 triage 标签(见 `docs/agents/triage-labels.md`)。

### Domain docs

单一上下文(single-context)布局。详见 `docs/agents/domain.md`。

## Base 公共组件迁移（2026-08-13 起 · #294 grilling 已闭环）

饼干记账全部 HTML 正在迁公共组件（Base），4 张 task 票在途：`#300`①管线+复制按钮+toast / `#301`②状态层 / `#302`③图表 / `#303`④HELP+展平（②③④⛓#300）。

- 动任何模板 / 渲染脚本 / scene_data / HELP 代码前，先认领对应 task 票或经用户协调，避免撞车（本迁移 = #163 剩余批次 / #278 消费方票的前置项）
- 公共组件缺能力 / 需兼容 / 有 BUG → 公共层 ISSUE + 告知用户，禁止技能内 fork 修补
- 决议全文：#294 闭环评论（范围 / Q1-Q11 / 执行协议）