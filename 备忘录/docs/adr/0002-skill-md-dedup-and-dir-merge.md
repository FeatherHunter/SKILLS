# 0002 SKILL.md 参考文档章节去重 + 双目录合并

`备忘录/SKILL.md` 中 "## 参考文档" 章节出现两次(L927 与 L1034,因 v1.1.4 HELP 章节插入产生冗余)。决定删除 L1034,保留 L927(在 HELP 前,符合"先讲用法再讲手册"的阅读流)。

同时 `备忘录/reference/`(3 个 .md) 与 `备忘录/references/`(1 个 .yaml) 双目录并存,Python 端 `memo_render.py:30` 已用 `references/`。决定将 `reference/` 合并到 `references/`,Python 端零改动,SKILL.md 4 处引用同步修改。

## Status
accepted · 2026-07-28 · Grilling R1 / B.7 + B.8

## Considered Options

合并方向:
- **合并为 `references/`**(采纳) — Python 端不动
- 合并为 `reference/` — 反过来,需改 `memo_render.py`
- 保持双目录 — 旧 reference/ 是文档类,新 references/ 是数据类,语义不同

L927 / L1034 选择:
- **删 L1034**(采纳) — L927 位置更合理
- 合并两章 — 4 + 3 引用合 1 份,防再分裂
- 删 L927 — 让"参考文档"在 HELP 后作收尾

## Consequences

- SKILL.md 行数减少 ~5 行
- reference/ → references/ 后,需 git mv 保留历史
- 落地后将触发 ADR-0001 的 `_meta.json` 同步(因为 v1.1.4 → v1.1.5 版本号变更)
