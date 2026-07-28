# 05 — scenarios.yaml 扩 variants + tests/test_variants.py + SKILL.md §变体管理(钩子 3)

**What to build:** AI agent reading `references/scenarios.yaml` can match 口语化 user prompts ("帮我找找", "那个啥在哪") because the 5 TOP 核心词 scenarios each carry `variants` with direction labels (同义 / 口语 / 模糊)。New test seam `tests/test_variants.py` enforces the structure。

**Blocked by:** None — can start immediately (TDD red → green)。

**Status:** ready-for-agent

**Source:** spec.md §User Stories 4-5, 11, 13, 19 · Q7=audit, Q8=A, Q9=B · 总纲钩子 3。

**Acceptance criteria:**

- [ ] `tests/test_variants.py` 新建(TDD red),含至少 5 个 test:
  - `test_top5_scenarios_have_variants` — 5 wake_word(查物品/看物品/录物品/盘物品/统物品)在 yaml 中都有 variants 字段
  - `test_variants_have_direction_label` — 每个 variant 的 `direction ∈ {"同义", "口语", "模糊"}`
  - `test_variants_have_at_least_2_directions` — 每 scenario ≥ 2 个 direction
  - `test_variant_phrases_non_empty` — `phrase` 字段非空字符串
  - `test_variants_no_forbidden_chars` — `phrase` 不含 `/ \ : * ? " < > |`
- [ ] `references/scenarios.yaml` 5 TOP scenarios 各加 `variants` 字段,数据样例:
  ```
  variants:
    - direction: 同义
      phrase: 搜索物品
    - direction: 口语
      phrase: 帮我找找
    - direction: 模糊
      phrase: 那个啥在哪
  ```
- [ ] 每个 TOP 5 scenario 至少 2 个 direction,每 direction 至少 1 phrase
- [ ] SKILL.md §触发词速览表:每个 TOP 5 核心词后加 1 行变体方向标注:`变体方向:同义+口语+模糊`
- [ ] SKILL.md 新增 §变体管理 章节,引用总纲钩子 3,说明:
  - **Risk B**: "新增 TOP 核心词需同步标注变体方向,否则视为 incomplete scenario"
  - 引用 scenarios.yaml 作为变体清单的单一事实源
- [ ] pytest 全 124 + 新增 ≥ 5 PASS(TDD green)

**Risk B:** 新核心词忘加变体标注 — 已在 SKILL.md §变体管理 章节显式声明 "incomplete scenario" 后果

**Decision trace:**
- Q7 = audit: TOP 5 = 查物品/看物品/录物品/盘物品/统物品(按使用频率)
- Q8 = A: 3 方向 = 同义/口语/模糊(钩子 3 字面)
- Q9 = B: 扩 scenarios.yaml,不新建 variants.yaml
- 不动 routing.py(日期 helper 无关 variants)
- 不动 home_manager.py(CLI 入口不参与 wake word 匹配)