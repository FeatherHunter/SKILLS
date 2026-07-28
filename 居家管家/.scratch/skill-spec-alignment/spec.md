# 居家管家 总纲合规化 Round 1

> **Status:** ready-for-agent
> **Created:** 2026-07-28
> **Source:** grill-with-docs round 1 (11 decisions, .scratch/_grilling/grilling-round-1_2026-07-28.html)
> **Author:** AI (after to-spec synthesis)
> **Spec for:** 6 commits × {doc edits + 1 code change}

---

## Problem Statement

居家管家 在 2026-07-28 完成了"原则 12 改造"(commit `7eefe69`),3 个 issue 全部 resolved。但用 **SKILL开发总纲 V1.0** 当尺审计后,仍然发现 **10 个候选优化**,其中 4 个是 P0 必修:

- **HTML-First 行为契约**未显式声明 → AI 可能偷懒用文字答(违反原则 11)
- **HELP 唤醒词**未在 frontmatter 标注 → AI 找"帮助"要去 body 搜(违反钩子 7 字面)
- **FAT 协议**未在 SKILL.md 显式 → commit 前没 fresh-agent 把关(违反钩子 6)
- **HOME_MANAGER 标识约定**未在 CONTEXT 显式 → 未来 Skill 可能各自为政(违反 ADR-worthy 条件,但属于"约定缺失")
- **ADR-0001 只覆盖 1 个偏离**(本地时间),实际还有"直接覆盖"未记录
- **唤醒词无变体管理**(33 个全是 2 元组)→ AI 难匹配口语化 prompt(违反钩子 3)

AI agent 当前使用居家管家时:**默认走文字答**(因为 SKILL.md 没强制)、**找不到 HELP**(因为 frontmatter 没标)、**听不懂口语**(因为没变体)。家庭用户的体感差。

## Solution

按 grill-with-docs Q11 决定,**6 commit 串行**执行(commit 1 已是 no-op),每个 commit 自包含、可独立 revert、跑 pytest 不退化:

| # | Commit | 类型 | 新 seam | Tested-By | 工作量 |
|---|---|---|---|---|---|
| 2 | CONTEXT.md 加 Skill 标识约定 + 通用术语引用 | doc | — | pytest-pass-2026-07-28 | 15 min |
| 3 | ADR-0001 扩充合并"直接覆盖"偏离 | doc | — | pytest-pass-2026-07-28 | 20 min |
| 4 | SKILL.md 新增 §HTML-First 章节 | doc | — | pytest-pass-2026-07-28 | 20 min |
| 5 | SKILL.md frontmatter help_wake_word + §路由表 第 1 行 | doc | — | pytest-pass-2026-07-28 | 1 h |
| 6 | scenarios.yaml 扩 variants + 新 tests/test_variants.py | **code** | **1 新** | pytest-pass-2026-07-28 | 1.5 h |
| 7 | SKILL.md §FAT 协议 + 分级 Tested-By 规则 | doc | — | pytest-pass-2026-07-28 | 30 min |

执行完成后,居家管家 在 6 个 P0/P1 项上对齐总纲 V1.0,新增 1 个 Python 测试文件 + 修改 4 个文档文件 + 1 个数据文件。

## User Stories

### AI agent(主要用户)

1. As an AI agent, I want SKILL.md to explicitly say "HTML-First is required for X wake words", so that I don't default to text answers for these commands.
2. As an AI agent, I want the HELP wake word declared in SKILL.md frontmatter metadata, so that I can find it without scanning the body.
3. As an AI agent, I want the §路由表 first row to be the HELP wake word, so that I read it before all other commands.
4. As an AI agent, I want wake word variants in `references/scenarios.yaml`, so that I can match 口语化 user prompts ("帮我找找", "那个啥在哪").
5. As an AI agent, I want each variant to be tagged by direction (同义/口语/模糊), so that I know what kind of linguistic deviation it represents.
6. As an AI agent, I want SKILL.md §FAT 协议 section, so that I know what scenarios to test before each commit.
7. As an AI agent, I want a Tested-By field rule that differentiates code vs SKILL.md changes, so that my commit messages follow the分级 convention.
8. As an AI agent, I want a Skill 标识约定 in CONTEXT.md, so that I don't reinvent naming conventions for new skills.
9. As an AI agent, I want a 通用术语引用 section in CONTEXT.md, so that I don't redefine concepts that already live in 总纲 §CONTEXT.md.
10. As an AI agent, I want ADR-0001 to capture ALL deviations in one place, so that I understand the rule landscape in one read.

### 家庭用户(最终用户)

11. As a home user, I want my 口语化 prompts ("帮我找找", "那个啥在哪") to work, so that I don't have to memorize formal 唤醒词.
12. As a home user, I want my "查物品" prompt to always produce an HTML view (never just text), so that I can see photos and locations visually.
13. As a home user, I want my "居家管家 帮助" prompt to show me the available commands with HTML preview, so that I can discover what's possible.

### 未来维护者(可能是 dev 或 AI)

14. As a future maintainer, I want ADR-0001 to capture both "本地时间" and "直接覆盖" deviations, so that I understand all principle-12 violations without grep.
15. As a future maintainer, I want variants validated by a Python test, so that I know immediately if I add a new variant with wrong shape.
16. As a future maintainer, I want each of the 6 commits to be independently revertible, so that I can roll back a bad change without losing the others.
17. As a future maintainer, I want the Tested-By field to appear in commit messages, so that git history shows what testing was done per commit.

### FAT agent(钩子 6 执行者)

18. As a FAT agent, I want a §FAT 协议 section in SKILL.md that lists which wake words need fresh-agent testing, so that I know my test scope.
19. As a FAT agent, I want variants labeled by direction (同义/口语/模糊), so that I can construct 3 distinct test prompt types per scenario.

### 跨切关注

20. As the project, I want the 6 commits to follow 总纲 principle 7 (each Phase = 1 commit), so that history is clean and grep-able by `[居家管家]` prefix.
21. As the project, I want only **1 new code seam** (`tests/test_variants.py`), so that we don't sprawl new infrastructure for a doc-heavy round.

## Implementation Decisions

### Seam 决策

**现有 seams(复用,不新加)**:
- `python -m pytest` — 全局测试入口,pre-commit hook 触发,124 tests 当前 PASS
- `scripts/build_manual.py` — 同步 HELP HTML 镜像(钩子 1)
- `scripts/render/render_page(template, payload, output_path=None)` — 单 HTML 渲染 seam(已用,本次不动)
- `scripts/routing.py` — 日期 helper(本次不动,commit 6 仍不需要,因为 variants 是 wake word 层)

**新 seam(只 1 个)**:
- `tests/test_variants.py` — 加载 `references/scenarios.yaml`,断言:
  - 5 个 TOP 核心词 scenario 各有 `variants` 字段(非空)
  - 每个 variant 是 `{direction: str, phrase: str}` 结构,`direction ∈ {同义, 口语, 模糊}`
  - 至少 2 个方向各 ≥ 1 变体(钩子 3 要求"2-3 变体")
  - variant 字符串不含禁用字符(`/ \ : * ? " < > |`)

### 模块修改清单

| 文件 | 修改 | 类型 |
|---|---|---|
| `references/scenarios.yaml` | 5 个 TOP scenario 各加 `variants` 字段;每变体含 direction + phrase | data |
| `CONTEXT.md` | 新增 "Skill 标识约定" 确认行 + "通用术语引用" 节 | doc |
| `docs/adr/0001-*.md` | 标题改为"HTML 输出命名与时间偏离(原则 12 · 本地时间 + 覆盖策略)";新增"直接覆盖"段 | doc |
| `SKILL.md` (4 处修改) | (a) frontmatter 加 `metadata.help_wake_word` (b) §路由表 第 1 行改为 HELP (c) 新增 §⛓ HTML-First 章节 (d) 新增 §🧪 FAT 协议章节 | doc |
| `tests/test_variants.py` | 新建,≥ 5 个 test case | code |

### 关键决策点(来自 grilling)

- **Q1 = alpha**:Skill 标识约定仅放居家管家 CONTEXT.md(简单);等第 2 个 Skill 出现再升级到总纲
- **Q3 = C(双层)**:5 通用术语(5 状态 fallback / 复制 prompt / 变体管理 / 相对时间 / 跨 Skill 路由) 等总纲先定义,居家管家 CONTEXT.md 加"通用术语引用"节指向总纲 §CONTEXT.md
- **Q4 = A(合并)**:`ADR-0001` 标题改为"HTML 输出命名与时间偏离(原则 12 · 本地时间 + 覆盖策略)";SKILL.md §📌 输出位置 改"详见 ADR-0001"
- **Q6 = B(强约定)**:"必须 invoke HTML,文字答视为 fail mode";但允许优雅降级(若 HTML 不可用,fallback 到结构化文本)
- **Q7 = audit**:`TOP 5` 核心 = 查物品 / 看物品 / 录物品 / 盘物品 / 统物品(按 audit 推荐的使用频率 5)
- **Q8 = A(钩子 3 字面)**:`3 方向 = 同义 / 口语 / 模糊`;SKILL.md §触发词速览表 每个 TOP 5 核心词后加 1 行变体方向标注
- **Q9 = B(扩 scenarios.yaml)**:不新建 `variants.yaml`;在 `references/scenarios.yaml` 每个 scenario 加 `variants` 字段
- **Q10 = single_first**:`metadata.help_wake_word: "居家管家 帮助"`(单数,字符串);§路由表 第 1 行移至 HELP 唤醒词
- **Q11 = serial**:6 commit 串行,每个独立 revert

### 架构决策(不动)

- 不改 `scripts/routing.py`(它只管日期,wake word 路由是 AI 在 SKILL.md §路由表 上做的)
- 不改 `scripts/home_manager/home_manager.py`(CLI 子命令入口,不参与 wake word 匹配)
- 不改 `scripts/render/render_page()`(单 seam 已稳)
- 不改 `tests/conftest.py`(共享 fixture 不需扩展)

## Testing Decisions

### Commit 6(code change,唯一需要新测试)

**TDD red → green 顺序**:

1. **RED**: 写 `tests/test_variants.py`,断言 5 个 TOP scenario 都有 `variants` 字段(此时必然 fail,因为 yaml 里还没有)
2. **GREEN**: 编辑 `references/scenarios.yaml`,给 5 个 TOP scenario 各加 `variants`(每个 ≥ 2 方向,每方向 ≥ 1 短语)
3. **REFACTOR**: 抽出 `_load_scenarios()` helper,清理 yaml

**至少 5 个 test case**:
- `test_top5_scenarios_have_variants` — 5 个 wake_word 在 scenarios.yaml 里都有 variants
- `test_variants_have_direction_label` — 每个 variant 的 direction ∈ {同义, 口语, 模糊}
- `test_variants_have_at_least_2_directions` — 每 scenario 至少 2 个 direction
- `test_variant_phrases_non_empty` — phrase 字段非空字符串
- `test_variants_no_forbidden_chars` — phrase 不含 `/ \ : * ? " < > |`

**Prior art**: 沿用 `tests/test_manual_sync.py` 风格(`pytest`, `Path`, `yaml.safe_load`)。

### Commits 2/3/4/5/7(doc-only,不需要新测试)

每个 commit 后跑:
```
python -m pytest
```
必须 **124 passed**(或者 commit 2/3/4/5/7 各自完成后仍是 124 passed,因为本次不改任何代码)。

Pre-commit hook `.githooks/pre-commit` 已强制这个 gate。

### 跨 commit 验证

每个 commit 前:
- `git status` — 只该有该 commit 的文件被修改
- `python -m pytest` — 124 PASS

每个 commit 后:
- `git log --oneline` — 看到新 commit 标题含 `[居家管家]` 前缀
- `git show` — 看 diff 只在该 commit 涉及的文件

## Out of Scope

### 本轮不做(留给后续 round)

- **总纲 §CONTEXT.md 加 5 通用术语**(5 状态 fallback / 复制 prompt 按钮 / 变体管理 / 相对时间 helper / 跨 Skill 路由)—— 跨 skill 工作,需开 `.scratch/cross-skill/generalize-context/` 单独 ticket(per Q3 = C 双层)
- **总纲自检 8 issue**——总纲自己的事(`.scratch/skill-dev-manual-refactor/` 已就绪,不在本 spec 范围)
- **6 个 P2 候选**(M3 相对时间 helper、M4 跨 Skill 路由、M5-M9 等)—— round 2
- **8 反模式逐 CLI 审计**—— 单独 ticket
- **5 状态 fallback 模板逐个验证**—— 单独 ticket
- **as_dict 模式统一**—— 重构级,单独 ticket
- **`scripts/refactor_prompts.py` 等历史脚本审计**—— 单独 ticket

### 显式不做

- 不改 `scripts/routing.py`(日期 helper 无关本次)
- 不改 CLI 入口层
- 不改 `scripts/render/render_page()` 单 seam
- 不引入新 Python 包

## Further Notes

### 决策溯源(grilling round 1)

| 决策 | 来源 | 备注 |
|---|---|---|
| Skill 标识约定 | Q1 = alpha | 简单本地化 |
| 分级 Tested-By | Q2 = yes | 改 SKILL.md 必须 fresh-agent,改代码 pytest-pass 就够 |
| 双层术语 | Q3 = C | 总纲定义基础,居家管家引用 + 扩展 |
| ADR 合并 | Q4 = A | 本地时间 + 直接覆盖 一起 |
| HTML-First 强约定 | Q6 = B | "必须 invoke HTML,文字答 fail mode" |
| TOP 5 核心 | Q7 = audit | 频率最高的 5 个 |
| 3 方向 | Q8 = A | 同义 / 口语 / 模糊(钩子 3 字面) |
| variants manifest | Q9 = B | 扩 scenarios.yaml,不新建文件 |
| help_wake_word | Q10 = single_first | 单数字符串 + 路由表第 1 行 |
| 执行顺序 | Q11 = serial | 6 commit 串行 |

### Commit 6 的 variants 数据样例(预期)

```yaml
- wake_word: 查物品
  scenario_id: search_default
  ...
  variants:
    - direction: 同义
      phrase: 搜索物品
    - direction: 口语
      phrase: 帮我找找
    - direction: 模糊
      phrase: 那个啥在哪
```

### Commit 4 的 §HTML-First 章节样例(预期)

```markdown
## HTML-First 行为契约(原则 11 · 强约定)

下列唤醒词命中后,**必须** invoke HTML,文字答视为 fail mode:
- 查物品 / 看物品 / 盘物品 / 盘全部 / 统物品
- 查高频 / 查低频 / 查过期
- 查快递 / 穿什么 / 带物品 / 归物品

优雅降级:若 HTML 生成失败(磁盘满 / 模板错),fallback 到结构化文本 + 错误回执。
```

### Commit 5 的 frontmatter 修改样例(预期)

```yaml
---
name: 居家管家
description: ...
metadata:
  help_wake_word: 居家管家 帮助
---
```

§路由表 第 1 行改为:

| 唤醒词 | 含义 | CLI 映射 | 是否需要 HTML |
|--------|------|----------|----------|
| **居家管家 帮助** | **技能速查** | **help** | **是** |
| 查物品 | 物品搜索 | search --name "XX" 等 | 是 |

### Commit 7 的 §FAT 协议样例(预期)

```markdown
## FAT 协议(钩子 6 · Fresh Agent 黑盒测试)

每个 commit 前必须经过分级 Tested-By:

- **改代码 / 数据 / CLI**:`Tested-By: pytest-pass-YYYY-MM-DD`(124 pytest 全 PASS 即可)
- **改 SKILL.md**(触发词 / 路由表 / 说明 / frontmatter):`Tested-By: fresh-agent-v1`(必须 fresh agent 实际跑过)

豁免:`Tested-By: exempt` + 豁免依据(如:typo 修正 / 格式调整)。
```

### 风险与回滚

- 6 commit 全部串行,任何 commit 失败都可独立 `git revert <sha>`
- commit 6 是唯一 code change,风险最高;但只动 1 个 yaml 数据字段 + 1 个新 test 文件,影响面小
- commit 5 改 frontmatter 字段名,如果某工具链依赖旧字段名(目前没有)会断;但 居家管家 没有外部消费者,风险低
- commit 7 加 §FAT 协议,可能让某些 AI 看到"必须 fresh-agent"后过度紧张 → 用"分级"子规则缓解

### 进度追踪

每个 commit 完成后:
1. `git log --oneline -1` 看标题
2. `python -m pytest` 看 124 PASS
3. 更新本 spec 底部"进度"节(从"[ ]" → "[x]")

---

## Progress

> **状态说明**:6 个 commit 的**文档层**已落地,但对抗式审查发现**行为层未验证**——
> variants 语料无消费方、HTML-First 无硬执行、FAT 协议定义者自己没跑过 FAT。
> 下列 `[x]` 表示文档完成,实际 AI 行为改善待 round 2 修正 + fresh-agent FAT 验证。

- [x·文档完成·行为待 FAT 验证] Commit 2 · CONTEXT.md 加 Skill 标识约定 + 通用术语引用 — 2218313
- [x·文档完成·行为待 FAT 验证] Commit 3 · ADR-0001 扩充合并"直接覆盖" — 07c633d（revert+redo of 0595641,因 GitHub Desktop 并行推送污染了 origin/main）
- [x·文档完成·行为待 FAT 验证] Commit 4 · SKILL.md §HTML-First 章节 — eae4592（软规则声明,无硬执行机制,待 round 2 加自检清单）
- [x·文档完成·行为待 FAT 验证] Commit 5 · SKILL.md frontmatter help_wake_word + §路由表 第 1 行 — 8901058（frontmatter 字段冗余,路由表第 1 行有效）
- [x·文档完成·行为待 FAT 验证] Commit 6 · scenarios.yaml 扩 variants + tests/test_variants.py (TDD) — cfe588c（语料入库但无消费方,待 round 2 加变体匹配逻辑）
- [x·文档完成·行为待 FAT 验证] Commit 7 · SKILL.md §FAT 协议 + 分级 Tested-By — ac90753（协议定义者自己违反,待 round 2 真 FAT 跑一遍）

**最终验证**:`python -m pytest` → 129 passed (124 原有 + 5 新增 variants 测试)。
**偏离记录**:commit 4 插入位置改为 §核心使用原则 之后(ticket 原说 §输出位置 之前,但 §输出位置 在 §核心使用原则 之前,顺序矛盾);commit 7 后界改为 §HTML 渲染器(ticket 原说 §场景资产 之前,但本 SKILL.md 无 §场景资产 章节)。

## Round 2 修正计划(对抗式审查结论)

- [ ] P1-4 spec.md Progress 改标注(本 commit)
- [ ] P1-3 §HTML-First 加 fail mode 自检清单
- [ ] P2-5 scenarios.yaml 5 个 TOP scenario 加 status: 【待开发】(变体语料未经验证)
- [ ] P0-1 §匹配规则 加变体匹配逻辑(让 variants 真正生效)
- [ ] HELP HTML 复制 prompt UI 对齐卡路里风格(Toast + 4 状态按钮 + 变体展示)
- [ ] P0-2 派 fresh subagent 跑 FAT 3 核心词 × ≥3 人类 prompt
- [ ] 根据 FAT 结果修正 commit 4/5/7 的 Tested-By 标签(reword,因已推 origin 需新 commit 说明)
