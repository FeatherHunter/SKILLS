# 01 — 新人 onboarding 完整路径

**Parent**: `00-memo-skill-v1.1.5-refactor-spec.md`(备忘录 Skill v1.1.5 整体重构 spec)

**What to build:**
新人 clone 备忘录 skill 后,能通过单条路径走通"读 README → 跑 verify → 看测试 → 调 help"完整链路。具体讲:新人阅读 README.md 的 5 章节了解这是什么、何时使用、如何快速开始、文件清单、当前状态;然后运行 `.scratch/grilling-alignment/verify.ps1` 一键验证(git status / pytest / CLI smoke / 结构体检 / hook 路由 5 项检查);脚本结束输出"通过"或具体失败项。

**Blocked by:** None — 可立即开始

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `备忘录/README.md` 存在,含 5 个二级章节:`这是什么` / `何时使用` / `快速开始` / `文件清单` / `状态`
- [ ] README.md 行数 60-80 行(比 SKILL.md 1038 行短一个数量级,新人不会被劝退)
- [ ] `.scratch/grilling-alignment/verify.ps1` 从 R3 占位升级为完整版,运行后输出 5 项检查结果
- [ ] verify.ps1 在干净工作区跑通,退出码 0
- [ ] 174+ pytest 全过(包含 ticket 03 新增的 test_skill_structure.py)
- [ ] git status 工作区无残留(commit 跑完,`备忘录.html` 时间戳漂移被 hook 自动还原)

## Out of scope

- SKILL.md 改动(由 ticket 02 处理)
- pytest.ini / test_skill_structure.py 创建(由 ticket 03 处理)
- CLI 子命令实现(本次重构 0 行为改动)
