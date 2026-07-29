# 04 — SKILL.md + 协作协议(Layer 2A · md 第二件):主入口契约同步

**What to build:**
`SKILL.md`(主入口)和 `references/AI协作协议-详细.md`(行为契约)同步到新设计。完成本工单后,任何人打开 SKILL.md 都不会再看到「ending.type 路由表」「cover.type=image 不支持」等与 spec 矛盾的描述。

**Blocked by:** 03(路由表先定,SKILL.md 才能联动)

**Status:** ready-for-agent

- [ ] `SKILL.md` §4(ending.type 路由表,**v1.10 扩展版本**)整段删除
- [ ] `SKILL.md` §5(cover.type 路由表,**v1.20 更新版本**)整段改写:
  - `image` 行从「当前不支持」改为「路由 cover_compose/(多图拼版),见 references/封面合成-多图拼版PIL.md」
  - 保留 ai / text 路由不变
- [ ] `SKILL.md` §G(op 白名单段,925 行附近):
  - 删除 `trim-head` / `trim-tail` / `cut-middle` / `pin-range` / `target-duration` 5 行
  - 增加「段内 op 替代说明」(指向 time_segments 边界)
- [ ] `SKILL.md` §AI 协作协议引用:`references/AI协作协议-详细.md §3.1`(ending.type fallback)整段改写为「ending.template + prompt 文本路由」
- [ ] `references/AI协作协议-详细.md` §3.1 整段改写:
  - 删除"ending.type 是 next-episode-promo/next-week/其他自定义类型时" 这段
  - 替换为「ending.template 是文本,按 §5 E 象限路由;若 AI 无法从 template 推断,必须询问用户」
- [ ] `SKILL.md` 触发词(triggers)增加「多图拼版封面」「拼图封面」「拼版封面」相关触发词已存在(86-92 行已列),核对无遗漏
- [ ] SKILL.md 顶部说明(description)末尾增加一行,指向 `references/AI路由表-意图JSON字段枚举.md`(AI 必读)