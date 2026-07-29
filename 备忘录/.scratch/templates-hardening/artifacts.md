# Artifacts · templates/ 防御性硬化(产物目录)

> 文档:spec.md
> 输出产物 / 中间产物 / 引用的资产。

## 输入产物(grill R2 → spec 之前)

- `CONTEXT.md` 已新增 3 term:
  - "渲染产物 (render artifact)"
  - "模板静态扫描 (template lint)"
  - "搜索意图 (search intent)"
- 对抗式审查 26 个问题清单(已收敛为 12 项 Phase B + 9 项 Phase C + 5 项撤回)

## 中间产物(spec 阶段已生成)

- spec.md · 本 spec 主体(用户拍板 A 方案的决策 4 已写入)
- verify.md · spec 自洽验证
- issues.md · 6 个未完全收敛的风险点
- decisions.md · 5 个轻量 ADR 草稿

## 输出产物(spec 之后的 to-tickets / 实施阶段)

- `tools/template_lint.py`(新建):3 类规则的 Python 实现
- `tests/test_template_lint.py`(新建):3 个测试类 + 钉 26 个 fixture
- `templates/memo_query.html`(改):L50/L60/L61 等 12 项 + a11y label + 长度模式切换
- `templates/wish_plan.html` / `templates/wish_complete.html` / `templates/change_category.html`(改):sticky 采纳按钮 / 视觉反转 / 颜色克制
- `templates/sync_report.html`(改):UI 一致性 8 项
- `templates/memo_help.html`(改):三处命名统一 / 回顶按钮
- `docs/adr/0006-template-lint-infrastructure.md`(新建,可选):决策 1 沉淀

## ADR-0006 草稿(预制,等实施确认后正式入库)

```md
# 0006 · templates 静态扫描基础设施

templates/*.html 内嵌 JS 历史上未被任何测试覆盖(测试只覆盖 CLI→JSON→path)。
问题:在浏览器里 JS 一旦出错(引用未定义、escape/unescape 不对称、违反 HTML 单工铁
律),用户第一手就撞到,问题以"用户报告"形式回流而非 pre-commit 拦截。

选 Python 纯静态 lint(`tools/template_lint.py`),无 Node / 浏览器 / ESLint 依赖。
三类规则守住总纲 §04 原则 4 / 8 / 10 的明文约束;集成进 pre-commit hook + 测试栈。

替代被否:
- ESLint(Node) — 引入跨运行时,且 ESLint 配置 security plugin 需要 npm 维护
- slimit — 维护弱,Python 兼容性不稳
- Playwright 运行时测试 — 引入浏览器二进制,跨 OS 不可控
```

## 参考索引

- 总纲 §04 (可视化与注入 v2) — 11 原则是 spec 决策的依据
- 既有 ADR-0003(commit 格式) — 3 commit 全中文
- 既有 ADR-0005(exemptions) — Tested-By 守护行
- 既有 tests/test_render.py(占位符 + 注入) — `test_template_lint.py` 借鉴该文件 fixture 模式
- 既有 tests/test_4_state_fallback.py(4 状态显式标记) — 借鉴"显式标记 + 报警"思路
