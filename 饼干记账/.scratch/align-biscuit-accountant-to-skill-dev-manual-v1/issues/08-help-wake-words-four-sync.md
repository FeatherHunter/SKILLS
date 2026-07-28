# 08 — `scenarios.json._meta.help_wake_words` 与 SKILL.md 同步为 4 条

**What to build:** 「饼干记账 HELP」/「饼干记账 帮助」/「查帮助」/「能做什么」4 条唤醒词都被 fresh agent 识别并路由到 `render_help.py` —— 不会再因为唤醒词漏注册而拿到 fallback 文本回执。

**Blocked by:** None — data only 改动，可与 06/07 平行

**Status:** ready-for-agent

- [ ] `references/scenarios.json` 的 `_meta.help_wake_words` 是 4 条
- [ ] `SKILL.md` §唤醒词总表 HELP 行写 4 条
- [ ] `tests/test_render.py` 加测试：`render_help.py` 输出 HTML 含全部 4 条唤醒词字符串
- [ ] 不修改 scenarios.json 的 91 个场景条目（仅 `_meta.help_wake_words` 数组）
- [ ] 不修改 SKILL.md 第一段（领域描述）