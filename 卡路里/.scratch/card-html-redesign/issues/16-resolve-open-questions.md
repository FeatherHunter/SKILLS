Status: ready-for-agent

# 16 — Q1-Q4 open questions 决策

**What to build:** 解决 spec Further Notes 中挂起的 4 个 open questions,落定决策 + 同步实现。

**Blocked by:** None — can start immediately(parked;不阻塞其他 ticket 落地)

## 4 个问题

### Q1 — `fill_hints` 是独立字段还是合并进 body?
- [ ] 决策落定(独立字段 / 合并 body / 第三选项)
- [ ] 决策应用到 07(`fill_hints` 字段已存在,可能需微调)
- [ ] `_triggers.py` 注释更新

### Q2 — 根镜像是否包含 dashboard quick-actions 摘要?
- [ ] 决策落定(包含 / 不包含 / 作为 iOS App Switcher 风)
- [ ] 决策应用到 05(rename step)与 06(contract retire)
- [ ] 若包含,扩 `render_help_center.py` 的 quick_actions section

### Q3 — `today_diet` / `today_meals` 模板合并策略?
- [ ] 决策落定(彻底合并 / partial 共享 / 维持双模板)
- [ ] 决策应用到 04(contract 阶段)
- [ ] 若合并,删除 `templates/today_meals.html`;若 partial,提取 common block

### Q4 — `.todo-row` meta 文案是否完全删除?
- [ ] 决策落定(完全删 / 保留并入 state icon / 保留 meta 但改字)
- [ ] 决策应用到 11(今日待办 compact)
- [ ] `home_dashboard.html` 与 render 数据相应调整

## 整体 acceptance

- [ ] 4 个 Q 各自有明确决策 + 在仓库中可被 grep / search 引用
- [ ] 任何后续 ticket 引用决策时无歧义