# 02 — ADR-0001 扩充合并"直接覆盖"偏离

**What to build:** Reader of `docs/adr/0001-*.md` sees BOTH deviations from 总纲 §原则 12 in a single ADR file — "本地时间" (UTC → 本地) AND "直接覆盖" (强制 _N 后缀 → 直接覆盖)。SKILL.md §📌 输出位置 改"详见 ADR-0001",单一真相。

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

**Source:** spec.md §Implementation Decisions · Q4=A。

**Acceptance criteria:**

- [ ] ADR-0001 标题改为 "HTML 输出命名与时间偏离(原则 12 · 本地时间 + 覆盖策略)"
- [ ] ADR-0001 新增 §直接覆盖偏离 节,解释:
  - 偏离的总纲条款(原则 12.A 强制 `_N` 后缀 vs 居家管家直接覆盖)
  - 理由(秒级时间戳概率性唯一 ~ 0.0001%,`_N` 后缀可作为兜底但默认不用)
  - 代价(冲突时无 `_N` 兜底,但实测 0 冲突)
- [ ] ADR-0001 §代价 节扩充,把原"时间戳不跨时区可比"也保留
- [ ] SKILL.md §📌 输出位置 删除原"偏离声明表"(本地时间 / 直接覆盖 / Skill 标识),改为引用"详见 ADR-0001"
- [ ] pytest 全 124 PASS(无代码改动,仅文档)

**Risk:** 无(纯文档,所有 ADR 性质变化在 ADR 文件本身内)

**Decision trace:**
- Q4 = A: 合并 2 个偏离到 ADR-0001,避免 SKILL.md 与 ADR 同步漂移