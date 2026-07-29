# 查询类 trigger 默认 HTML(HTML-First 升级)

Status: accepted

Issue 1(查热量 32 匹配返回纯文本表格)、Issue 2(查食品库 50 行 LIMIT + TXT 返回)都源于同一个根因:`查热量` / `查食品库` 不在 SKILL.md §已实现模板表的"强制 trigger"列,所以 AI 走文字答。HTML-First 规则(V1.3 原则 11)只对"已有模板的 trigger"生效,这两个是漏网之鱼。

我们决定:**所有"查询类 trigger"(返回 ≥1 行数据)默认 HTML;text 只保留给单条 CRUD 回执、单值状态查询、嵌入日志 3 类场景**。判据可机器验证:`check_html_responsive.py` 升级 + 新增 trigger 时强制走 HTML。

考虑过的选项:
- **维持现状(有模板走 HTML,无模板走 text)** — 补 查热量/查食品库 2 个模板即可,其它不动。缺点:"看有没有"这个隐式规则仍在,下一个新 trigger 仍会漏。Issue 5.4 已实证(查体重波动 4 mode 没想清楚就被贴上"现状最佳")。
- **AI 每次询问"要不要 HTML?"** — 让用户掌控输出格式。缺点:违背 HTML-First 自动渲染原则,每次问一句打断对话流;实测 73 个 trigger,频繁询问会让 AI 失去判断力。
- **当前方案(强制 HTML)** — 把 HTML-First 适用范围从"有模板"扩展到"查询类"。判据:"≥1 行数据" + "非回执格式",机器可验证。

后果:
- 文字答只在 3 类场景:单条 CRUD 回执 / 单值状态 / 嵌入日志。其它一律 HTML。
- 已有 26 个 HTML 模板基本覆盖查询类(查今天吃 / 查营养结构 / 查食物排行等);只有 查热量 / 查食品库 / 查体重波动 v2 待补(由 ticket 06/07/Q8 落地)。
- ADR-0003 已把 查今天喝水 从 text 改 HTML,与本 ADR 同一方向。
- Reversibility:删除 §触发词速查表 + §已实现模板表 的强制 trigger 行即可回滚。

详见:`tests/test_food_search.py:1` + `tests/test_cli_validation.py:79`(seam 5 list-products --text escape hatch) + ADR-0003。