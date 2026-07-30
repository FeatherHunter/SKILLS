# 0003 — 只支持 schema_version=3.0

Status: accepted (2026-07-29)

智剪工坊 v3.0 只支持 `_meta.schema_version="3.0"`。加载老 schema 文件(缺失或非 "3.0")时直接报错"请删除重填",不做自动迁移。理由:简单明确;`migrateLegacyIntent` 函数保留作为参考但不启用。