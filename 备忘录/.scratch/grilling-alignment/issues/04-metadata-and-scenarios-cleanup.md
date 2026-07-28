# 04 — 元数据同步 + scenarios.yaml 清理(自动化消费)

**Parent**: `00-memo-skill-v1.1.5-refactor-spec.md`

**What to build:**
任何自动化工具或 AI agent 读取元数据时,得到的是干净、一致、机器可消费的版本。具体讲:读 `_meta.json` 立刻得到 `version: 1.1.5`(与 SKILL.md frontmatter 一致,不再落后 14 个版本);用 YAML parser 读 `references/scenarios.yaml` 立刻得到单一权威场景列表(只有 1 个 `scenarios:` 键,前一个重复块已删除),文件 EOF 有换行,29 个场景可正常解析。

**Blocked by:** None — 可立即开始

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `_meta.json` 的 `version` 字段从 `"1.0.0"` 改为 `"1.1.5"`
- [ ] `_meta.json` 其他字段不动(name / description / 等保持原状)
- [ ] `references/scenarios.yaml` 顶层只有 1 个 `scenarios:` 键(Python `yaml.safe_load` 验证)
- [ ] 删 L21 重复 `scenarios:` 块
- [ ] L377(原 EOF)后补 `\n`,文件以换行符结尾
- [ ] 29 个场景数量不变(0 增删,只清理冗余)
- [ ] 174 pytest 全过(`test_help.py` 49 个测试守护 7 字段契约)

## Out of scope

- `_meta.json` 引入新字段(版本号外不增 schema)
- scenarios.yaml 场景内容调整(本 spec 不改业务)
- 数据库 schema(本 spec 不涉及 DB)
