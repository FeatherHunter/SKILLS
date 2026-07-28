# 05 — 术语统一(expand-contract 三阶段 · wide refactor)

**Parent**: `00-memo-skill-v1.1.5-refactor-spec.md`

**What to build:**
AI agent / 维护者 / 用户在任何场景下读 SKILL.md / 5 个 HTML 模板 / CHANGELOG.md,看到的术语统一为"唤醒词"(不是"触发词")。整个迁移过程采用 **expand → migrate → contract** 三阶段(因为这是 wide refactor,blast radius 91+ 处,跨多个文件,不能一次性切换):

- **Phase 1 (expand)**: scenarios.yaml + memo_cli.py 加"唤醒词"作为"触发词"别名,两个都能用。期间 174 pytest 全过。
- **Phase 2 (migrate)**: SKILL.md 91 处 + 5 个 HTML 模板中所有"触发词"→"唤醒词";CHANGELOG.md 历史记录保留(≤ 5 处,作为版本演化档案)。期间 174 pytest 全过。
- **Phase 3 (contract)**: 移除"触发词"别名,只接受"唤醒词"。任何使用"触发词"的输入被显式拒绝并提示改用"唤醒词"。期间 174+ pytest 全过。

**Blocked by:** ticket 02(SKILL.md frontmatter 应先落地,避免术语与 version metadata 冲突) + ticket 04(scenarios.yaml 已清理冗余,术语别名加在干净结构上)

**Status:** ready-for-agent

## Acceptance criteria

### Phase 1 (expand)

- [ ] scenarios.yaml 顶层 `aliases` 段(新增)含 `触发词: 唤醒词` 映射
- [ ] memo_cli.py 加载别名表,支持任意别名作为 唤醒词 触发
- [ ] 174 pytest 全过(旧用法与新用法都接受)
- [ ] `memo_cli help` 输出的 HTML 显示"唤醒词"作为首选词

### Phase 2 (migrate)

- [ ] SKILL.md 中"触发词"出现次数 = 0(`grep -c 触发词 SKILL.md`)
- [ ] 5 个模板(memo_help.html / memo_query.html / sync_report.html / wish_plan.html / wish_complete.html / change_category.html)中"触发词"出现次数 = 0
- [ ] CHANGELOG.md 中"触发词"出现次数 ≤ 5(历史记录保留,加注释说明)
- [ ] 174 pytest 全过
- [ ] `git grep "触发词" -- ':!CHANGELOG.md' ':!*.bak'` 返回 0 行

### Phase 3 (contract)

- [ ] scenarios.yaml 删 `aliases` 段,只剩标准字段
- [ ] memo_cli.py 删别名解析逻辑
- [ ] 174+ pytest 全过(新增 1+ 个测试:输入"触发词"应被拒绝)
- [ ] "触发词"输入被显式拒绝,返回 `ValueError("不支持的术语,请改用'唤醒词'")`

## Out of scope

- "用例"→"场景" 替换(由 ticket 07+10+其他文件协同处理)
- "4 元组" / "4 部分" 显式区分(由 ticket 02 frontmatter + SKILL.md 后续 commit 处理)
- CHANGELOG.md 历史记录改写(伪造审计,违反 ADR-0001)
