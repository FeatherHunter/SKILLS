# 01 — Spec 骨架:D1+D2+D7 落地

**What to build:**
spec §4 完整版(`docs/superpowers/specs/2026-07-25-video-time-segment-model.html`)整合 D1(5 项字段定稿)+ D2(ending V4)+ D7(5 个该消失的 op),成为后续 7 个工单的**唯一权威协议蓝图**。

完成本工单后,任何后续工单都引用此 spec §4,不再有第二份 spec 文档。

**Blocked by:** None — can start immediately(起点)。

**Status:** ready-for-agent

- [ ] `_meta` 字段定稿:含 `schema_version: "3.0"` 必填 / `tool_version` 可选 / 移除 `history[]` / 移除 `version: "0.7"` 旧硬编码
- [ ] `output` 字段定稿:含 `aspect_ratio_custom`(aspect_ratio="custom" 时必填)
- [ ] `cover` 字段定稿:含 `type=image` 三选项 + `images[]` 数组(仅 type=image)
- [ ] `ending` 字段重构成 V4:仅 `{template, prompt}` 两字段,无 mode/extras/kind
- [ ] `videos[].video_ops` 列出 5 个该消失的 op(`trim-head`/`trim-tail`/`cut-middle`/`pin-range`/`target-duration`),明确标记「已废弃,不进 JSON」
- [ ] `videos[].time_segments[].ops` 列出段内 op 白名单(`mute`/`speed-up`/`slow-down`/`reverse`/`color-grade`)
- [ ] spec §7 校验规则同步更新(段内 op 白名单对齐)
- [ ] spec §5 字段对照表删除整行(5 个该消失的 op)
- [ ] spec §12「不做」清单与新设计对齐
- [ ] spec §1.5 决策记录补入 D1-D7 编号索引(供追溯)