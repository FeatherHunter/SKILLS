# DSH-Waystation · Prompt 审阅清单（v1.5）

> 全部 prompt 已集中到 L 字典 `prompt.*`（client.js / package/lib/client.js 双源，zh/en 双语跟随 DSH 语言）。
> 目标：优化 prompt，让 AGENT 更符合 **wayfinder 规则**（先对齐意图 → 建图 → 逐票 grill → 第一性原理执行）与插件设计流程（新会话/动作/沉淀/交接）。

## 1. 引导句（所有动作 prompt 的结尾）

| key | zh | en |
|---|---|---|
| prompt.guide | 从第一性原理出发完成任务，并对抗式审查。 | Approach tasks from first principles, and review adversarially. |

## 2. 动作模板（行级动作按钮 · 诊断/修复/讨论/执行 · 占位符 {url} {number} {title}）

| key | zh 摘要 | en 摘要 |
|---|---|---|
| prompt.tpl.diagnose | /triage {url} → 诊断 + 分流建议（复现/根因/分流） | /triage {url} → diagnose + triage |
| prompt.tpl.fix | /wayfinder {url} → 修复 bug（复现/根因/修复/测试/对抗审查） | /wayfinder {url} → fix bug |
| prompt.tpl.discuss | /wayfinder {url} → 讨论 grill（目标边界/风险假设/选项权衡/决策） | /wayfinder {url} → discuss (grill) |
| prompt.tpl.execute | {url} → 执行 issue（读描述/方案/实施/验收） | {url} → execute |
| prompt.tpl.handoff1 | /handoff → 生成交接文档 {ts}.md（结论/未完成/建议 skill） | /handoff → handoff doc |
| prompt.tpl.handoff2 | /read 交接文档 → 复述确认理解 | /read handoff → restate |

## 3. Map 流程 prompt

| key | 用途 | 说明 |
|---|---|---|
| prompt.mapExecute | map 行执行/新会话（未完成态）| 加载 wayfinder → 分析 map → 第一性原理挑下一个 frontier issue → 执行 |
| prompt.complete | map 完成态（完成按钮/新会话）| 完成确认 · MAP #{n}：核对完成真实性 → 收尾 close 或列未完成项（占位符 {n} {total} {closed}）|
| prompt.mapHead | 新会话/执行的 map 标识头 | ## 目标 map（#n / 标题 / 链接）（占位符 {n} {title} {url}）|

## 4. 沉淀 / 零丢失快照

| key | 说明 |
|---|---|
| prompt.fixate | 里程碑固化点：五类全量复述（目的地/约束/决定/待决/雾区）+ 出处引用 + 可疑遗漏 + 停下核对 |

## 5. 其他

| key | 用途 | 说明 |
|---|---|---|
| prompt.setup | 环境检查横幅按钮 | /setup-matt-pocock-skills（选择 GitHub Issues 作 tracker）|
| prompt.newWayfinder | 「+ 新建需求」按钮 | /wayfinder + 仓库 {repo} + 新增/复用/直接实现需求引导 |
| prompt.handoffRead | 交接第二击兜底（无文件时）| /read latest.md → 复述确认理解 |

---

## 审阅建议方向（对照 wayfinder 规则）

1. **动作模板是否引导「先对齐意图」**：诊断/修复/讨论目前直接开干——wayfinder 强调先复述/确认再执行，是否在 execute/fix 前加一步「先复述理解 + 对齐」？
2. **mapExecute 是否够 wayfinder**：现状 4 步（加载技能→分析→挑 issue→执行）——是否应补「先检查 frontier/阻塞，claim 目标 issue 后再执行」？
3. **complete 是否闭环**：已完成确认逻辑（核对/close/列遗漏）——是否补充「在 Decisions so far 写一行 gist 的格式要求」？
4. **newWayfinder 是否引导建图**：现在只是「新增/复用/直接实现」——是否补充「若目标较大，按 wayfinder 建 map（Destination/Notes/票）而非直接写码」？

> 你的优化意见 → 我改对应 `prompt.*` 键（zh/en 同步），双源 + 测试 + 推送即可。
