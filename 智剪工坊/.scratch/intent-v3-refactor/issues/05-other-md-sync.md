# 05 — 其他 md 同步(Layer 2A · md 第三件):消除残留矛盾

**What to build:**
清理其他 `references/*.md` 中残留的旧 enum / 5 个 op / `ending.type` 描述,使整个 md 文档层完全自洽。完成本工单后,任何人读 `references/` 任意文件都看不到与 spec §4 矛盾的描述。

**Blocked by:** 04(SKILL.md 改完才能联动)

**Status:** ready-for-agent

- [ ] `references/原子操作-14种基础剪辑指令.md` 重写:
  - 删除 5 个 op(`trim-head`/`trim-tail`/`cut-middle`/`pin-range`/`target-duration`)行
  - 标题改为「原子操作」并补全到 v3.0 当前数量(约 17 个 op + 段内 5 个)
  - 增加「v3.0 双字段分离」说明(`video_ops` vs `time_segments[].ops`)
- [ ] `references/主流程-阶段编排.md` §阶段 5 ending 段:
  - 删除「ending.type=next-episode-promo」具体路由
  - 改为「读 ending.template + ending.prompt,按 AI 路由表 §5 E 象限文本路由」
- [ ] `references/精剪-剪头剪尾保留段切中间.md`:
  - 整段改写:用户视角的"剪头/剪尾/删中间/只保留/目标时长"操作,改用 `time_segments` 边界表达
  - 文档标题可保留(用户视角),但内容更新
- [ ] `references/time_segments-ops-schema.md`(若存在):核对与 spec §7 段内 op 白名单一致
- [ ] `references/调用范式/`、`references/粗加工-执行契约.md`、`references/精加工-两路径.md` 等中所有提及 `ending.type` 的地方改写为 `ending.template` / `ending.prompt`
- [ ] `references/Jargon-用户口语映射.md`(若含 ending / trim 相关口语)同步更新
- [ ] 全仓库 `grep -r "ending\.type"` 验证无残留(除 spec §4 历史归档区)