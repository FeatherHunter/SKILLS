# 09 — HELP 路径名收敛到 §12.B 标准 + SKILL.md 显式声明

**What to build:** 用户触发 HELP 时生成的 HTML 文件名永远是 `饼干记账_HELP_<YYYYMMDD>_<HHMMSS>[_N].html`（§12.B 标准）—— 任何时候用 `ls *饼干记账_HELP_*.html` 都能搜出所有历史 HELP 页。同时 SKILL.md §📌 输出位置 章节显式标注「本 Skill 走 §04 原则 12.A / 12.B」，后续读者不会误以为可随意改 HTML 路径名。

**Blocked by:** 08 — 先统一唤醒词，HTML 路径名才有依据

**Status:** ready-for-agent

- [ ] `render_help.py` 的 `default_output_path()` 返回的 `command_zh` 部分为「饼干记账_HELP」
- [ ] `SKILL.md` §📌 输出位置 章节加显式声明「本 Skill 走 §04 原则 12.A / 12.B」+ 数据查询路径写明 `<command_zh>_<YYYYMMDD>_<HHMMSS>[_N].html`（§12.A）+ HELP 路径写明 `饼干记账_HELP_<YYYYMMDD>_<HHMMSS>[_N].html`（§12.B）
- [ ] `tests/test_render.py` 加测试：触发 HELP 后输出文件名以 `_HELP_` 开头（不含「能力速查」字样）
- [ ] 不修改 `html_paths.py` 的 `COMMAND_NAMES["help"]` 之外的键（避免影响 9 类 query_type）