# Spec Map: align-biscuit-accountant-to-skill-dev-manual-v1

Status: ready-for-agent
Created: 2026-07-28

## Notes

- 由 grill-with-docs 强制对照《SKILL 开发总纲 V1.0》十轮决策清单（Round 1-10 共 14 项偏差 + Round 11 HTML BOM 修复）合并而成
- 接缝 = `bill_inject.py <query_type> [args]` 端到端调用（最高级，与 §02 + §04 + §05 三方一致）
- 落地顺序见 spec.md §Further Notes #3
- 一份 spec 不拆 ticket，由实现时按 implementation decision #3 顺序编号建 issue

## Decisions-so-far

- 接缝 = 单 seam（最高级）
- 范围 = 14 项决策 + HTML BOM（合并）
- 测试 = tests/ 四件套 + FAT 手跑 + `Tested-By:` commit 字段
- 不动 HTML 镜像自动生成器、不删 config-cookie-accounting.ts、不重写分类体系

## Fog

- (none)