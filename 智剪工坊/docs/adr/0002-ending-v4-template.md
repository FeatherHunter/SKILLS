# 0002 — ending 重构成 V4(template + prompt)

Status: accepted (2026-07-29)

`ending` 字段重构成 `{template, prompt}` 两文本字段,抛弃 6 选 1 enum。原理:枚举退守(只在真离散空间保留 enum)、HTML 是 UX 不是 schema、AI 路由推迟(让 AI 解析时再分类)、可演进 10 年。`ending.template` 必填(HTML 选中模板的人话描述),`ending.prompt` 可选(用户补充说明)。AI 按 §5 E 象限文本路由规则把 template+prompt 解析为 CLI 步骤。