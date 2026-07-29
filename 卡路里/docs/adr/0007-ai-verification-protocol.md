# AI 验证协议(SELECT 先于断言)

Status: accepted

Issue 6 表面症状:AI 说"你还没设定体重目标"前没查 DB,凭直觉(或损坏数据)就断言"没设过"。根因:SKILL.md 没有"AI 在断言前必须验证"的硬约束,跟 HTML-First / Wizard Verify 同类问题。

我们决定:**所有 AI 在 SKILL 内声称"用户没 X / 用户从未 Y"前,必须先对该 X/Y 对应的 DB 表执行 SELECT 验证**。3 个 fail mode 红线作为判定标准。违反 = 协议 fail mode,等同 HTML-First 反模式。

考虑过的选项:
- **加 lint_health 自动检查** — 检测 AI 输出断言 vs DB 真实状态的一致性。缺点:实现成本高(需要审计 AI 输出),对单次对话成本不划算。
- **改 CLI 设计,加 `--show-query` 强制打印 SQL** — 用户跑 CLI 时看到实际查询。缺点:只对 CLI 有效,AI 自主判断场景管不到。
- **当前方案(SKILL.md §⚠️ 第 7 条)** — 把"SELECT 先于断言"写进最高优先级协议段,跟 HTML-First / Wizard Verify 同等地位。改动小,跟现有协议条款对齐,执行点由 AI 自身遵守 + 用户反馈触发 review。

后果:
- 不强制 lint,依赖 AI 自身遵守 + 用户对话中指出 → AI 必须立刻 SELECT 重新回答并道歉。
- 文档约束,不是工具约束,reversibility 高(git revert 即可)。
- `卡路里HELP` prompt 模板顶部加 hint("对任何'用户没 X'类断言,先 SELECT 验证(§⚠️ 第 7 条)"),把提醒放到 AI 触发 wake word 时的可见位置。

详见:`SKILL.md §⚠️ 强制性规定 第 7 条` + `tests/test_ai_verification_protocol.py:1`(seam 8 守门)。