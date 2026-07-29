# 02 — 协议校验:JSON Schema 提炼 + validate 同步

**What to build:**
从 spec §4 提炼出独立的 JSON Schema 草案(`references/intent_v3.schema.json`),并让两端的 validate 函数都基于此 schema 工作。完成本工单后,任意 JSON 进 validate,立刻能识别是否 v3.0 spec 合规,无论是从 HTML 写入端还是 Python 读取端。

**Blocked by:** 01(spec 骨架必须先定)

**Status:** ready-for-agent

- [ ] 提炼 spec §4 为标准 JSON Schema(放 `references/intent_v3.schema.json`,用 `$schema` 和标准字段)
- [ ] HTML `validateIntent` 函数(5079-5119)改为读 JSON Schema 校验
- [ ] Python `stage1_checklist.py` 集成 `jsonschema` 库,加载 `references/intent_v3.schema.json` 做读取校验
- [ ] validate 拒绝用例覆盖:
  - `_meta.schema_version` 缺失或非 "3.0"
  - `videos[].video_ops` 含 5 个该消失的 op
  - `time_segments[].ops` 含白名单外 op
  - `cover.type=image` 但 `cover.images[]` 缺失
  - `ending.template` 缺失(D2 必填)
- [ ] validate 通过用例:符合 spec §4 的最小完整 JSON 通过校验
- [ ] 输出 validate 错误的统一格式(spec 错误定位到字段路径)