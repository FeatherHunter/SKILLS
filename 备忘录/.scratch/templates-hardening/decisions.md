# Decisions · templates/ 防御性硬化

> 文档:spec.md
> 轻量 ADR(to-spec 阶段已决策的不需要进 docs/adr/ 的项),沉淀临时决策。

## D-spec-01 · 决策 1 用 Python 纯静态 lint(选 N/A · 待票决)

- 上下文:grill R2 决策 1 列了三种实现选项 — Python 纯静态 lint / slimit (Python 绑定 JS parser) / subprocess 调 Node ESLint。
- 已选:**Python 纯静态 lint**(`tools/template_lint.py` + re 规则,无外部依赖)
- 原因:
  1. 本仓库是 Python 主导,引入 npm/node 链条与既有工程仪式不匹配
  2. slimit 依赖维护弱,跨 Python 版本兼容性弱
  3. 静态 lint 不需完整 AST,三类规则本质是字符串/正则匹配够用
- 替代被否:Node ESLint(配 ESLint.js security 插件)— 有更强分析能力,但需要 CI 配 Node,违背"Python 纯栈"
- 何时复议:如果规则 1 (引用未定义) 在 memo_query 复杂 JS 段失效率 > 30%,考虑换 slimit。

## D-spec-02 · 决策 2 CONTEXT.md 加 3 个术语(已落地)

- 上下文:domain-modeling skill 要求术语解析即更新 CONTEXT.md
- 已选:加 "渲染产物 (render artifact)" + "模板静态扫描 (template lint)" + "搜索意图 (search intent)" 3 个 term
- 实施时间:本 spec 写之前已落地(grill R2 阶段)

## D-spec-03 · 决策 3 拆 3 commit(已选)

- 上下文:总纲原则 7 要求每 Phase 一个 commit
- 已选:A / B / C 三段 commit,每段独立 revert 友好
- 撤回:无,沿用总纲约定

## D-spec-04 · 决策 4 字段级搜索(已选)

- 上下文:用户拍板 A 方案(只搜 content)
- 已选:仅匹配 `note.content` 字段
- 同时决策 4 不需建 ADR(因 in CONTEXT.md "搜索意图" term 已沉淀)
- 钉死:**任何未来 ticket 改 memo_query 搜索逻辑,必须保留 "仅 content" 语义**(lint 守护 + test_template_lint.py 永久 fixture)

## D-spec-05 · Phase A 静态扫描规则 3 的细则(草稿,待 to-tickets 阶段复审)

- 上下文:spec Implementation Decisions 决策 1 给出三类规则的高层描述,具体正则 / AST 边界留给实施
- 草拟规则:
  - 规则 1:`function name` 提取 → 对比所有 `name(` 调用 → 报警
  - 规则 2:`esc(`/`escapeHTML(` 调用 vs `.replace(/&[#\w]+;/g, ...)` 中的字符集合 → 报警前者集合超过后者
  - 规则 3:扫描所有 `<button class="...">` 节点 → 对应 selector 必须有 `.addEventListener('click'` 或 `onclick=` 处理;**例外**:`.copy-btn-fallback` 类(已知静态按钮类)
- 待复审:Phase A 实施时如果误报 > 5 例/模板,需调整白名单
