Status: ready-for-agent

# 14 — 记吃了 prompt body 4-step flow

**What to build:** `_triggers.py` 中 `记吃了` 的 `main_prompt.body` 重写为 4 步流程,AI 不再 blind-write,单位区分(ml vs g)显式说明。

依据:D6(spec 实现细节);保持 §04 ❌ 不做 HTML(回执 仍 text-only)。

**Blocked by:** None — can start immediately

- [ ] `_triggers.py` 中 `记吃了` `main_prompt.body` 改写:
  ```
  我刚吃了一顿,需要写进 food_log。

  AI 流程:
  1. 在食品库查询食物名(如 "元气森林 冰红茶汽水")。
  2. 若命中:展示营养数据(每 100g 的热量/蛋白/碳水/脂肪),等我确认后写库。
  3. 若无命中:区分单位(ml vs g),如必要请我提供克数或包装营养数据,标注估算来源。
  4. 完成后给 1 句话总结,不需要过多文字解释。
  ```
- [ ] `记吃了 [补录历史]` variant 同步(若其 prompt 与 main 不同)
- [ ] SKILL.md §触发词速查表 L279 "记录饮食(库匹配/图片识别/外部搜索统一入口)" 描述与新 prompt 对齐
- [ ] `check_prompt_quality.py` 加 assertion:`body` 含 `食品库` / `用户确认` / `单位` 关键词(否则 fail)
- [ ] 测试:prompt 文本字节快照与 4 步 流程 一致;variants 同样含 4 步精神