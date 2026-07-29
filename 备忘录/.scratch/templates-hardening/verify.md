# Verify · templates/ 防御性硬化 spec 自我验证

> 文档:spec.md
> 验证范围:本 spec 写完后,自我检查 spec 自身没有矛盾。

## 验证项

### 1. 问题陈述 vs 方案对照
- [x] Problem 第 1 段说 "26 个对抗式审查验证的问题" → Solution 给出 "Phase B 12 项 + Phase C 9 项 = 21 项实修,撤回 3 项" + "lint 治本"
- [x] Problem 第 1 段说 "模板层 JS Bug 从未被 tests/ 捕获" → Implementation 决策 1 给出"单一最高 seam = tests/test_template_lint.py"
- [x] 未变化:用户故事 1-24 覆盖了 spec 决策 1-4 + Phase B/C 全部要点

### 2. 术语一致性(对照 CONTEXT.md)
- [x] "渲染产物 (render artifact)" 在 Implementation Decisions 决策 2 引用,在 User Story 22 / Further Notes 一致引用
- [x] "模板静态扫描 (template lint)" 在 Implementation Decisions 决策 1 引用,在 Testing Decisions 一致引用
- [x] "搜索意图 (search intent)" 在 Implementation Decisions 决策 4 引用,对应 User Story 11
- [x] 三个术语均已落地 CONTEXT.md(grill R2 阶段已 commit 之前已经写入)

### 3. Seam 边界
- [x] 决策 1 seam = `tests/test_template_lint.py` 一个文件,与既有 pre-commit hook 无缝接通(不需要新增 cmd)
- [x] 未引入 ESLint / Node / 浏览器二进制 — 符合"Python 纯栈"约束
- [x] 新增 `tools/template_lint.py` 与 `script/` 目录并列,放在 memo_cli 既定的工具约定位置

### 4. Phase 拆分依赖链
- [x] Phase A → B → C 串行(无逆依赖)
- [x] Phase A 的 lint 规则先于 Phase B/C 的修复 — 是 lint 守护 B/C 修改不引入同类回归
- [x] Phase C UI 改动不影响 Phase B 的 fixpoint(语义修复独立)

### 5. 撤回项 vs spec 内容一致性
- [x] Implementation Decisions 明确 "撤回项" 三条,均不出现在 Phase B/C 修复清单
- [x] out of scope 未越界(不重复 grill R1 撤回的 P1-10/15/14)

### 6. ADR 触发判定
- [x] 决策 1 三条件全部成立 → to-tickets 阶段建 0006 ADR(详见 spec.md §Further Notes)
- [x] 决策 2-4 不触发 ADR(均已沉淀 CONTEXT.md)

### 7. 测试覆盖度(对 spec 范围)
- [x] `tests/test_template_lint.py` 3 个测试类对应 3 类规则
- [x] 每个 Pharse B bug 至少有 1 fixture 钉死(避免回归)
- [x] 既有 `test_render.py` / `test_4_state_fallback.py` 会自动作为 Phase B/C 修改后的全量回归

## 验证结论

spec 自洽 / 内无矛盾 / seam 清晰 / 撤回项已隔离 / ADR 触发判定齐全 → ready for to-tickets。
