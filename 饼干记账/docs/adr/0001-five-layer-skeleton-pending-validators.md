# ADR-0001: 总纲 V1.0 五层骨架在本 Skill 的落地状态

## Status

accepted — 2026-07-28

## Context

《SKILL 开发总纲 V1.0》第 §02 章规定所有 Skill 必须无分档全跑五层骨架:
数据层 (`db.py`) / 操作层 (`*_ops.py` + `integrations/`) / 规则层 (`validators.py` + `references/`) / 接口层 (argparse CLI) / 文档层 (`.md` + `.html` + `references/`)。ADR-0002 删除"规模分档逃生口"。

本 Skill 已落地 4 层:
- 数据层: `scripts/db.py` (SQLite + 字段白名单 `_UPDATE_ALLOWED`)
- 操作层: `scripts/analyze.py` (汇总/对比/分类)
- 接口层: `scripts/record_bill.py` (11 个子命令 + JSON 契约)
- 文档层: `SKILL.md` / `饼干记账.html` / `references/` / `templates/`

## Decision

暂时接受"五层缺一"的过渡状态。`validators.py` 尚未独立成文件,硬规则(`_UPDATE_ALLOWED` / 字段类型校验 / 默认值过滤)分散在 `db.py` 与 `record_bill.py` 的 argparse 层。

## Consequences

- 优点: 不阻塞当前 issue 处理;硬规则已落地,功能等价
- 代价: §02 第 ③ 规则层的"无跳过通道"约束未满足;后续必须建立独立 `validators.py`,否则 §02 自检清单永远无法 pass

## Follow-up

- [ ] `validators.py` 独立化
- [ ] FAT (Fresh Agent 黑盒) 测试记录归档
- [ ] HTML 镜像(`饼干记账.html`)改自动生成