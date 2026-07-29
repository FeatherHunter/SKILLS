# 08 — HTML 编辑器改造(Layer 3):产出 v3.0 JSON

**What to build:**
`智剪工坊-意图编辑.html` 改造为按 v3.0 spec 产出 JSON。完成本工单后,HTML 编辑器保存的任意 intent.json 必须 100% 通过 02 工单产出的 validate,且浏览器 UI 上能看到 10 个 ending 模板 + cover.type=image 上传器,且加载老 schema 时明确报错。

**Blocked by:** 01(spec 骨架)+ 07(video_processing.py 改完)

**Status:** ready-for-agent

### D1 相关

- [ ] `collectFormData`(4860)写入 `_meta.schema_version: "3.0"`
- [ ] 删除 `_meta.history` 相关代码(4864-4865 两行)
- [ ] `_meta.version: "0.7"` 改为 `_meta.tool_version: "0.7"` 或对应值(4868)
- [ ] `cover.type` select(2069-2073)增加 `<option value="image">多图拼版</option>`
- [ ] `cover` 块增加 `cover.images[]` 上传器 UI(JS 收集选中的图片路径,写入 JSON)
- [ ] `output.aspect_ratio_custom` 写入逻辑确认(2045 已实现,verify)

### D2 + D3 相关

- [ ] `ending` 字段重写:`ending.type` select 替换为 10 个效果模板 + prompt 输入框
- [ ] 10 个模板渲染为 UI 卡片(标题 + 描述,UX 规则)
- [ ] 保存时:`ending.template` = 选中模板的人话描述文本,`ending.prompt` = 用户自由输入
- [ ] 删除 `ending.type` 相关代码(2087-2093、4579-4709 的白名单)

### D7 相关

- [ ] `legacyOps` 数组(4979-4983)删除 5 个该消失的 op
- [ ] HTML UI 上 5 个对应 checkbox 移除(渲染代码)
- [ ] `collectVideoOpsForVideo` 不再尝试收集这 5 个

### 已知实现层 bug 修复

- [ ] `SegmentState.addOrSplit`(5190)移除 `user` op 注入
- [ ] `collectFormData`(4954-4960)过滤 `excluded` 段
- [ ] 段内 op 命名统一(`color` vs `color-grade`,需与 spec §7 白名单一致)
- [ ] 段 ID 格式改为 `seg_${videoIdx}_${n}`
- [ ] 加载老 schema intent.json 时明确报错(D4),不静默迁移

### 测试

- [ ] 用浏览器打开 HTML,填一份完整表单,保存后 JSON 必须通过 validate(02 工单)
- [ ] 浏览器手动验证 10 个模板 UI 渲染正确(标题 + 描述)
- [ ] 浏览器手动验证 `cover.type=image` 选项可上传图片
- [ ] 浏览器手动验证加载老 schema JSON 时显示报错弹窗