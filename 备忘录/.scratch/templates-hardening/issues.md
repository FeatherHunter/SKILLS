# Issues · templates/ 防御性硬化 spec 已知风险

> 文档:spec.md
> 列出 spec 写完后仍存在 / 不可解 / 需要后续决策的问题。

## I-1 · CONTEXT.md 三个新术语是否会与 SKILL开发总纲V1.0/CONTEXT.md 冲突

- 状态:已对照总纲 `/CONTEXT.md`
- 风险:本仓库的 CONTEXT.md 是子 skill 的术语表,与总纲术语保持一致是 L1-3 明文要求
- 当前判断:三个新增 term 均不与总纲既有 term 冲突("渲染产物"对应总纲的"12.A 数据/过程 HTML 输出约定";"模板静态扫描"是本 skill 自行引入的小工具术语;"搜索意图" 是本 skill 的搜索语义决策)。需要在 to-tickets 阶段确认总纲没有反对表述
- 触发条件:如果总纲 ADR 后续新增 "Linter" / "Renderer" 等术语,且与 "模板静态扫描" 重叠

## I-2 · 静态扫描规则 3(HTML 单工铁律)的精度 vs 误报

- 状态:风险点,在 spec Testing Decisions 已加粗提示
- 风险:`<button>` 节点 + 对应 handler 的检测需要避免"按钮无 handler 时报警,但有些按钮就是静态装饰(无 handler,合法)"
- 缓解建议:Phase A 实施时,先做小范围灰度(scroll-to-top 是允许无 handler 的纯 CSS 按钮,需 spec 排除)

## I-3 · Phase C 视觉反转 — 改动范围是否包含 wish_complete / wish_plan L124-L129 注释

- 状态:已分析
- 现有 wish_complete L124-126 的注释解释了为什么 `.off` 不在 selected 渲染时应用 — spec 决策 C2 反转后,这段注释需要重写
- 当前判断:会在 to-tickets 阶段作为 wish_complete · ticket 的子任务,无独立 ticket

## I-4 · wish_plan / wish_complete 的 sticky 按钮是否会与底部"采纳 prompt pre"重叠

- 状态:开放
- 风险:C1 把「采纳」按钮 sticky 到 viewport-bottom,但 pre 区域在 fold 之外才出现
- 当前判断:C1 + C4 一起做(`max-height:340px` 删掉,pre 自适应内容高度;sticky 按钮永远叠加在最底部;长 prompt 不再被截断后,pre 与 sticky 按钮并列展示时 sticky 始终在屏内可见)。需在 Phase C 实施时跑浏览器实际验

## I-5 · memo_query 搜索字段级的内容泄露面

- 状态:无
- 用户决策 R2-4 = 只搜 `content`,绝不搜 id/UUID,这条守不可逆
- 后续如果用户想要"用 ID 查找"体验,该功能应该走"打开备忘详情"路径(后续 ticket),不是改搜索语义

## I-6 · Phase A 的 lint 可能被预提交 hook 误启

- 状态:已写明
- pre-commit hook 当前 hook path 是 `.githooks/`,调用 `PYTHONUTF8=1 python3 -m pytest tests/`
- 新增 `tests/test_template_lint.py` 后,会自动被 hook 捕获
- 如果某次 hook 因 lint 失败阻断 commit 而 lint 规则本身有缺陷,会陷入"无法 commit 含 lint 修复的 commit"的循环
- 缓解:Phase A 的 commit 不在 memo 模板内改任何 HTML(只加 tools/ + tests/),lint 规则在 Phase B 改模板前就位
