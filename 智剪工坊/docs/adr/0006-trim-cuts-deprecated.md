# 0006 — 5 个该消失的 op 严格删除

Status: accepted (2026-07-29)

intent.json v3.0 不再包含以下 5 个 op:`trim-head` / `trim-tail` / `cut-middle` / `pin-range` / `target-duration`。语义改由 `videos[i].time_segments[]` 边界表达:`trim-head sec=N` ≡ `time_segments[0].start_sec = N`;`trim-tail sec=N` ≡ `time_segments[last].end_sec = duration_sec - N`;`cut-middle [X,Y]` ≡ 创建相邻两个 time_segments(中间不进 JSON);`pin-range [X,Y]` ≡ 单个 time_segments 区间;`target-duration` ≡ 拼接后时长 = 各段相加(无需声明)。HTML UI 移除对应 checkbox;JSON Schema 拒绝;`lib/video_processing.py` 删除对应解析逻辑。