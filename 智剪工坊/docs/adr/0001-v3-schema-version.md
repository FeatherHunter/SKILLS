# 0001 — v3 schema_version 必填

Status: accepted (2026-07-29)

`intent.json` 必须含 `_meta.schema_version: "3.0"`(必填),可选含 `_meta.tool_version`(产品发布号)。AI 解析时凭 `schema_version` 决定走 v3.0 解析逻辑;`tool_version` 区分产品发布号与契约号。老的 `_meta.version` / 顶层 `version` 全部删除。