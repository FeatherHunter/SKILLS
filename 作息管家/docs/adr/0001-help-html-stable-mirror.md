# ADR-0001: 作息管家.html 作为 HELP HTML 的稳定入口

作息管家根目录的 `作息管家.html` 作为 HELP HTML 的稳定入口 — 每次 `help_render.py` 跑完自动同步(覆盖写),与 `schedule_html/help/作息管家_HELP_<TIMESTAMP>.html`(历史快照,遵守总纲 §04 原则 12)并存。

## 理由

1. IDE 根目录即开即看(无需跳路径)
2. 配合总纲 §05 钩子 #1 "HTML 同步硬规则" 完全自洽 — SKILL.md / scenarios.yaml 改动 → 跑 `help_render.py` → 作息管家.html 自动同步
3. git diff 看得见帮助文档变更,审计强约束

## 总纲 §04 原则 12 例外

此 ADR 即覆盖授权 — 原则 12 "绝不覆盖 + _N 冲突保护" 在作息管家根目录的 `作息管家.html` 上被显式豁免(`schedule_html/help/` 子目录内的快照仍遵守原则 12)。

## 考虑过的替代方案

- **B · 固定快照**(commit 锁定)— 无 ADR 例外,但失去 IDE 即开即看便利
- **C · 派生文件**(.gitignore 排除)— 零 ADR 风险,但失去 git diff 可见性
- **D · 软链**(→ schedule_html/help/作息管家_HELP_latest.html)— Windows + git 兼容性问题,放弃

## 后果

1. `help_render.py` 每次跑都同步作息管家.html(无 flag,自动)
2. `.gitignore` 不排除作息管家.html(根目录文件全部 git 跟踪)
3. 未来其他 skill 若要复用此模式,需各自写 ADR
4. 改动前 3 问(总纲 §05)适用:影响 help_render.py + 作息管家.html 两文件;无数据迁移;回滚 = git revert

## Status

`accepted` · 2026-07-28 · Grilling Session Q2/Q3 共识
