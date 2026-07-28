---
Status: ready-for-agent
Type: task
Feature: skill-optimize
Parent: spec.md
Issue: 11
Blocked-by: ["01", "07", "09", "10"]
---

# 11 — Phase B 验证 · pytest + Fresh Agent 黑盒测试

**What to build:** 完整验证 10 张 ticket(01-10)落地后的作息管家,确保 pytest 全绿、Fresh Agent 黑盒测试通过、SKILL.md 路径引用与实际生成一致、CHANGELOG.md 更新记录所有 Phase。

**Blocked by:** 01, 07, 09, 10(4 个 ticket 是实施产物,验证必须在它们全部完成后)

**Status:** ready-for-agent

- [ ] pytest 全绿(11+ 个测试文件,新增 test_help_sync / test_naming / test_copy_prompt)
- [ ] Fresh Agent 黑盒测试(FAT · 总纲 §05 协议)— 选 5 个核心唤醒词 × 2-3 变体,≥ 3 个口语化 prompt 各唤醒词至少 1 个
- [ ] 验证项:
  - [ ] 跑 `python scripts/help_render.py` → 作息管家.html 与 schedule_html/help/作息管家_HELP_<TS>.html 内容一致
  - [ ] 跑 6 个 record render 命令 → 输出文件名都是中文 command 名
  - [ ] 跑 5 个 plan render 命令 → 输出文件名都是中文 command 名
  - [ ] 15 模板 HTML 都有"复制 prompt"按钮
  - [ ] 故意跑英文 `record_day` → 报清晰错误(Contract 已生效)
- [ ] SKILL.md 路径引用与实际生成 100% 一致(grep 比对)
- [ ] CHANGELOG.md 更新(新增 Phase A-3 / A-1 / B 条目)
- [ ] commit Tested-By:fresh-agent-v1(完整 FAT 报告)