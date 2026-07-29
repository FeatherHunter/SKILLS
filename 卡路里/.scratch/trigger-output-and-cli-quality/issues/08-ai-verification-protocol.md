# 08 — AI 验证协议 + ADR-0007(SKILL.md §⚠️ 第 7 条)

**What to build:**
When an AI agent receives a 卡路里 trigger that involves asserting user state (e.g., 查体重目标), the agent MUST first run a SELECT against the DB before claiming "user hasn't X". This is documented as a hard protocol rule, not a soft suggestion. This is the root-cause fix for Issue 6's secondary cause (AI asserting "you haven't set a goal" without verifying).

**Blocked by:** None — this is a documentation change (SKILL.md + an ADR file); no code or schema changes.

**Status:** ready-for-agent

- [ ] `SKILL.md` §⚠️ 强制性规定 gains a new section "7. ⭐ **AI 验证协议**(v2.5 增,Issue 6 反馈)" with body text:
  > "AI 在 SKILL 内声称'用户没 X / 用户从未 Y'前,**必须**先对该 X/Y 对应的 DB 表执行 SELECT 验证。3 个 fail mode 红线示例:
  > (a) **写脏数据后断言原值** — 如 weight_goal 被某次 `--help` 调用覆盖为 `'--help'`,AI 直接 SELECT 看到字符串就应识别为损坏数据,而不是回写字符串。
  > (b) **空值误判'从未设过'** — `NULL` / `None` / `0` ≠ '从未设过';可能是过期数据或损坏数据。
  > (c) **类型误判** — 当 DB 返回非预期类型(如字符串而非数字)时,AI 不得假设其为 0 或'未设'。
  > 违反 = 协议 fail mode,等同 HTML-First 反模式(第 4 条)。"
- [ ] `SKILL.md` §核心原则 gains a 7th bullet: "⭐ **AI 验证协议**(V1.3 第 7 条):写库断言前必查,空值不等于'从未'"
- [ ] The `卡路里HELP` prompt template (`scripts/_triggers.py` or equivalent) adds a top-line instruction: "对任何 '用户没 X' 类断言,先 SELECT 验证(§⚠️ 第 7 条)"
- [ ] `docs/adr/0007-ai-verification-protocol.md` written per ADR-FORMAT with Status: accepted, recording: (a) why we add this as a §⚠️ rule, not a tooling lint; (b) the 3 fail modes; (c) reversibility: a future reader can soften to a lint if compliance tooling matures
- [ ] `SKILL.md` §触发词速查表 entry for 查体重目标 includes a one-line reminder: "AI: 先 SELECT weight_goal,验证后再断言'已设/未设'"