# 0001 版本号单一事实源为 SKILL.md

备忘录 skill 当前在 `_meta.json`、`SKILL.md`、`CHANGELOG.md` 三处记录版本号,其中 `_meta.json` 自 v1.0.0 后未跟进(现落后 14 个版本)。决定以 `SKILL.md` 为 SoT,`_meta.json` 为镜像,落地机制由 `.githooks/pre-commit` 在 SKILL.md version 字段变更时同步 `_meta.json`。CHANGELOG.md 是事件流日志,不是 SoT(总纲 §05 Tested-By 字段所在)。

## Status
accepted · 2026-07-28 · Grilling R1 / B.2

## Considered Options

1. **`SKILL.md` 是 SoT,`_meta.json` 是镜像**(采纳) — 匹配总纲 §CONTEXT L13-15"S SKILL.md 是 agent 字面执行的依据"
2. `_meta.json` 是 SoT — 牺牲"SKILL.md 权威性"换取 JSON 易校验
3. 删除 `_meta.json` — 当前无消费者,留着只会腐化(它已腐化)
4. 双 SoT + lint 强制一致 — 最严谨但增加维护成本
