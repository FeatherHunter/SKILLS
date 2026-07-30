# 0007 — 段内调色 op 命名为 color

Status: accepted (2026-07-29)

段内调色 op 命名为 `color`(不带 `-grade` 后缀)。理由:`color-grade` 的 `grade` 后缀语义模糊(中文读者第一反应"等级"而非"调色")。命名统一后:HTML / spec / JSON Schema / AI 路由表四方零冲突。spec §7 段内白名单:`['mute', 'speed-up', 'slow-down', 'reverse', 'color']`。