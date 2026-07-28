---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 03
Blocked-by: ["02"]
---

# 03 — Q5 Migrate · record 域 6 模板路径对齐

**What to build:** 跑任一 record 域 render 命令(查作息记录 / 查作息区间 / 查作息对比 / 查作息类别 / 查作息异常 / 作息详情),输出文件名都是 `<中文 command>_<YYYYMMDD>_<HHMMSS>.html`,用户在 IDE 文件浏览器看到的中文文件名能直接对应 SKILL.md 唤醒词。

**Blocked by:** 02(Q5 Expand 必须先完成,提供中文 command 参数化能力)

**Status:** ready-for-agent

- [ ] 6 个 render-record-* 子命令的默认路径改为中文 command 名
- [ ] 输出文件名:`查作息记录_<TS>.html` / `查作息区间_<TS>.html` / `查作息对比_<TS>.html` / `查作息类别_<TS>.html` / `查作息异常_<TS>.html` / `作息详情_<TS>.html`
- [ ] SKILL.md §3.x 表格中 record 域 6 个命令的"输出形式"列更新为新路径
- [ ] tests/test_naming.py 扩展覆盖 6 个新文件名(命名合规正则)
- [ ] pytest 全绿
- [ ] 旧英文文件名变孤儿,提供迁移脚本(可选,标记 deprecated)
- [ ] commit Tested-By:fresh-agent-v1(6 个唤醒词各 2 个 prompt)