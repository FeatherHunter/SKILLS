# Patch P1-7: SKILL.md / _meta.json / features/*.md 漂移修复

## 修了 4 处漂移
| 之前 | 现在 |
|---|---|
| `49 个 pytest` (SKILL.md L39/L44) | `71 个 pytest` (实测一致) |
| `_meta.json`: `3 张SQLite表,纯Python标准库` | `5 张表...,需 cryptography` |
| `features/add.md:383` `home_manager/html_render.py` | `scripts/render/__init__.py (Phase 7 挪包)` |
| `features/search.md:95` 同样路径 | 同样修 |
| `SKILL.md:18` `python: ">=3.7"` | `python: ">=3.7", pip: ["cryptography"]` |

## 验证
- pytest 71/71
- grep 漂移关键词 → 0 命中(只剩 features/search.md 注释里提到旧路径作"已删除"说明)
- version bump 1.0.0 → 1.1.0(累计 P0/P1 patch 的语义版本升级)

## 未修(留 P2)
- references/database.md:12 "category 字段保留" → 实际生产 DB 已删,文档漂移。
  暂不动,留 phase 2 文档审计时统一刷。