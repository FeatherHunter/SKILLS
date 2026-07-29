# 06 — stage1_checklist.py 重写(Layer 2B):读 v3.0 schema

**What to build:**
`scripts/_internal/stage1_checklist.py` 重写为读 v3.0 schema。完成本工单后,输入一份符合 spec §4 的 JSON,产出符合 §A-F 6 象限的操作清单,且加载老 schema 时明确报错。

**Blocked by:** 02(协议校验规则)+ 05(其他 md 同步完成)

**Status:** ready-for-agent

- [ ] 删除 `_has_any_op(v.get('ops', {}))`、`v.get('voice')`、`v.get('notes')` 等老 schema 字段读取
- [ ] 改读 `v.get('video_ops', {})`(整段 op)
- [ ] 改读 `v.get('time_segments', [])` 段列表
- [ ] 改读 `v.get('video_ops', {}).get('voice', {}).get('mode')`(voice.mode)
- [ ] 改读 `v.get('video_ops', {}).get('voice_note', '')`(voice_note)
- [ ] 改读 `v.get('video_ops', {}).get('notes', '')`(notes)
- [ ] 加载时检查 `_meta.schema_version`:
  - "3.0" → 正常解析
  - 缺失或非 "3.0" → 报错退出(D4:只支持 v3.0)
- [ ] 5 个该消失的 op(`trim-head`/`trim-tail`/`cut-middle`/`pin-range`/`target-duration`)的 switch case 全部删除
- [ ] 6 象限输出保留(videos 列表、project-level、sequence、模糊项、AI 推断标记、未覆盖字段)
- [ ] `ending` 字段在 D 象限(模糊项)中读 `template` + `prompt`(不再读 ending.type)