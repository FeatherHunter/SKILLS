# 11 — `references/categories-mapping.md` 桥接表

**What to build:** 任何读 `config-cookie-accounting.ts` 的工具都能用一份桥接表把 9 L1（餐饮/购物/交通/娱乐/医疗/住房/教育/通讯/其他）映射到本 Skill 的 10 L1（餐饮/居家/穿着/出行/玩乐/学习/健康/社交/宠物/其他），不再两套分类并行漂移。

**Blocked by:** None — 纯文档

**Status:** ready-for-agent

- [ ] `references/categories-mapping.md` 存在
- [ ] 含 9 ↔ 10 L1 桥接表 + `_Avoid_` 标注哪些映射是「近似」（如 `购物` 是 `居家` + `穿着` 的并集）
- [ ] 顶部声明「权威分类体系以 `categories.md` 为准；`config-cookie-accounting.ts` 是 legacy 视图」
- [ ] 不修改 `config-cookie-accounting.ts` 的字段（仅文档化其语义）
- [ ] 不修改 `categories.md`（权威不动）