# 07 — video_processing.py 重写(Layer 2B):执行层适配

**What to build:**
`lib/video_processing.py` 适配 v3.0 schema。完成本工单后,单视频处理流能正确读 `video_ops` 与 `time_segments[].ops`,5 个该消失的 op 的解析逻辑完全删除,产出符合 ffmpeg filter 链的视频。

**Blocked by:** 06(stage1 必须先读新 schema,编排层才会调用 video_processing 处理新字段)

**Status:** ready-for-agent

- [ ] 删除 line 218-234:`trim-head` / `trim-tail` / `speed-up` / `slow-down` 在 `ops` 顶层的老解析
- [ ] 删除 line 257-260:`fade-in` / `fade-out` 在 `ops` 顶层(改由 video_ops 读,但语义确认)
- [ ] 删除 line 508-509:`cut-middle` / `pin-range` 老解析
- [ ] 改读 line 466:`ops = video.get('video_ops', {}) or {}`
- [ ] 改读 line 467:`voice = video.get('video_ops', {}).get('voice', {}).get('mode', 'keep')`
- [ ] `build_video_filter` 函数签名与内部 switch 更新,与新 ops 字段对齐
- [ ] 单视频 fast-path 判定条件更新(检查 `video_ops` 而非老 `ops`)
- [ ] 段内 op 处理新增:`time_segments[].ops` 中的 op(mute / speed-up / slow-down / reverse / color-grade)应用到对应区间
- [ ] 测试用例:用 `2026-07-29-mock-spec-ideal.json` 作为输入,产出符合 fast-path / 完整转码两条路径之一
- [ ] 验证:`mute` / `speed-up` 等段内 op 不会与 video_ops 顶层 `mute` 冲突(优先级明确)