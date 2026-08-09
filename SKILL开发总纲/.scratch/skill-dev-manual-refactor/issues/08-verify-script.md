# 08 — 自洽校验脚本 verify.ps1 + 跑通全部校验(A 坐标最终证据)

**What to build:** 编写 .scratch/skill-dev-manual-refactor/verify.ps1,包含 spec Testing Decisions 的 5 个校验模块,跑通后所有校验项 PASS = A 坐标"100% 自洽"有客观证据:(1) 计数校验(钩子 7 / 原则 13 / fail mode 5 / 场景字段 7)(2) 不存在校验(grep "6/8" / "规模伸缩" / "附录 D" / "铁律 4" / "V3" / "6+1" / 死链 / 架构图.html 全部 = 0)(3) 字面对应校验(伪代码 timeout/5MB/二次校验 / 原则 10 标题 .md==HTML / 原则 11 含互补 / 原则 12 无 V3 / 速览表含原则 12 / §02 全名引用)(4) 引用闭合校验(§06 附录 C 单行引用 §05 / 附录 F 引用 §05 / §07 死链声明 / README 无架构图)(5) 新增文件存在校验(CONTEXT.md 含场景约束 / ADR-0001+0002 / docs/agents 3 文件 / AGENTS.md 含 Agent skills 块)。校验脚本可复用于后续 Skill 改造的文档自洽检查。同时补 CONTEXT.md "场景"术语定义后加"契约级最小必填,不准删减或重命名(§07)"(T4 之外的补丁,在此确认)。

**Blocked by:** 07(HTML 同步完才能最终校验,因为校验含 HTML 跨文件一致性)

**Status:** ready-for-agent

- [ ] verify.ps1 存在于 .scratch/skill-dev-manual-refactor/
- [ ] 脚本含 5 个校验模块(计数 / 不存在 / 字面对应 / 引用闭合 / 新增文件)
- [ ] 脚本跑通,所有校验项 PASS(0 FAIL)
- [ ] CONTEXT.md "场景"术语含"不准删减或重命名(§07)"
