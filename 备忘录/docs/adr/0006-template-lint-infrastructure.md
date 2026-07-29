# 0006 · templates 静态扫描基础设施

templates/*.html 内嵌 JS 历史上未被 `tests/` 覆盖:`test_render.py` 只验证 CLI→JSON→path 渲染管道,不感知浏览器内 JS 行为。模板层 Bug 一旦落地,以"用户报告"形式回流,而非 pre-commit 拦截 — 这次对抗式审查出的 26 个问题中,3 个 P0 都是 JS Bug(引用未定义函数 / escape-unescape 不对称 / 单工铁律违反),均未被既有测试捕获即明证。

## 决策

`script/template_lint.py` 纯 Python 静态 lint(无 Node / 浏览器 / ESLint 依赖),三类规则守住总纲 §04 原则 4 / 8 / 10 的明文约束;集成进 pre-commit hook + pytest 测试栈。

### 三类规则(参见 spec.md §Implementation Decisions 决策 1)

1. **lint_undefined_funcs**:inline `<script>` 内 `funcName(` 调用但文件内无 `function funcName` 定义 → 报警
2. **lint_escape_asymmetry**:`esc(...)` 输出 5 entity(`amp` / `lt` / `gt` / `quot` / `#39`),但反序列化 `.replace(/&XXX;/g, ...)` 处理的 entity 集合不全 → 报警
3. **lint_copy_fallback**:`<button ...>` 节点无对应 `.addEventListener('click'` 或 `onclick=` handler → 报警(违反原则 10 HTML 单工铁律)

整合入口 `lint_templates_dir(templates_path)` 一键跑三类规则。

## 替代被否

- **Node + ESLint**:引入 npm 跨运行时,违背"Python 纯栈"约束
- **slimit(Python 绑定 JS parser)**:维护弱,跨 Python 版本兼容性不稳
- **Playwright 运行时测试**:引入浏览器二进制,跨 OS 不可控(Windows / macOS / Linux 行为差异)

## Status

accepted · 2026-07-29 · Grill R2 + to-spec + to-tickets 决策沉淀。

## 何时复议

若规则 1(引用未定义)在 memo_query / wish_*.html 之类复杂 JS 段失效率 > 30%,考虑换 slimit 或纯 AST 解析方案。

## 与既有 ADR 关系

- ADR-0003(commit 全中文)· 本 ADR 不涉及 commit,引用"Phase A 落地"在 b4187e2 commit message 中已执行
- ADR-0005(豁免矩阵)· 本 ADR 的 script/template_lint.py 属"script 改动",按 D.4 矩阵必须回归 pytest 全过(b4187e2 已实现)
- ADR-0004(A.4 .scratch 5 文件范式)· 本 ADR 的 spec 沉淀在 `.scratch/templates-hardening/spec.md`

## Related

- spec: `.scratch/templates-hardening/spec.md`
- decisions: `.scratch/templates-hardening/decisions.md` D-spec-01
- artifacts: `.scratch/templates-hardening/artifacts.md`
- ticket: `.scratch/templates-hardening/issues/01-template-lint-infrastructure.md`
- ticket: `.scratch/templates-hardening/issues/10-adr-0006-template-lint.md`
