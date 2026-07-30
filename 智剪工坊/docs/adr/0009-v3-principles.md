# 0009 — v3.0 重构纲领

Status: accepted (2026-07-29)

智剪工坊 v3.0 重构的最高指导原则:**HTML 开发完善 → 用户编辑产生正确 JSON → 用户和 AI 确认 JSON 已好 → AI 按工作流指引开始解析 JSON → AI 调用 atomic CLI 和 py 脚本对视频处理。不会出现 "python 完全不处理" 的情况。任何小 bug 必须修复,不留尾巴。** 分工:HTML 负责 UI 收集 + 写正确 JSON;JSON 协议层(spec §4 + `intent_v3.schema.json`)是契约;md 文档是 AI 行为的真实契约;AI 按 md 指引 + atomic CLI 文档自己组合 ffmpeg 命令;`lib/video_processing.py` 负责整段 `video_ops` 编排(非段内);atomic CLI 是单 op 工具。任何"python 不处理"的判断都是错的(要么整段处理,要么 AI 组合)。