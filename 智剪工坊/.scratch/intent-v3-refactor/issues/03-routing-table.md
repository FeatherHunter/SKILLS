# 03 — 路由表(Layer 2A · md 第一件):AI 行为契约同步

**What to build:**
`references/AI路由表-意图JSON字段枚举.md` 完整改写为与 spec §4 一致。完成本工单后,AI 读到路由表就能知道:
- 所有字段的当前合法枚举
- `ending` 不再有 enum,改按 §5 E 象限文本路由
- `cover.type=image` 路由到 `cover_compose/`
- 5 个该消失的 op 不再出现

**Blocked by:** 01(spec 骨架必须先定,md 才知字段枚举)

**Status:** ready-for-agent

- [ ] §1 字段枚举表更新:
  - 增加 `_meta.schema_version` 行
  - 增加 `_meta.tool_version` 行(标注可选)
  - 删除 `_meta.history[]` 行(若有)
  - `output.aspect_ratio_custom` 行修正为"W:H"格式说明
  - `cover.type` 枚举扩到 `ai/text/image`,image 路由说明更新
  - `ending.type` 整行**删除**(不再存在该字段)
  - `ending.template` 行新增(必填 string)
  - `ending.prompt` 行新增(可选 string)
- [ ] §2 路由表(op → atomic CLI)更新:
  - 删除 `videos[i].ops.trim-head` 行
  - 删除 `videos[i].ops.trim-tail` 行
  - 删除 `videos[i].ops.cut-middle` 行
  - 删除 `videos[i].ops.pin-range` 行
  - 删除 `videos[i].ops.target-duration` 行
- [ ] §3 ending.type 路由段整段**删除**
- [ ] §3 替换为「ending.template + ending.prompt 文本路由规则」(引用 §5 E 象限)
- [ ] §4 cover.type 路由更新:image 行从「不支持」改为「路由 cover_compose/」并指向 `references/封面合成-多图拼版PIL.md`
- [ ] §5 E 象限文本路由规则强化:明确说明 ending.template 是典型 E 象限场景