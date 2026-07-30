# 0008 — 段 ID 格式 seg_V_N

Status: accepted (2026-07-29)

`time_segments[].id` 格式:`seg_${videoIdx}_${n}`。`videoIdx` 是视频索引(1-based,`entry.index`);`n` 是段在该视频内的序号(从 1 递增,如 `seg_2_1` / `seg_2_2`)。理由:可读、AI 友好、天然排序。JSON Schema `id.pattern` 强制 `^seg_[0-9]+_[0-9]+$`。HTML `SegmentState.addOrSplit` 用内部 `nextN` 计数器分配新段 id。