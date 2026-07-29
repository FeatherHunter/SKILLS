Status: ready-for-agent

# 15 — Cross-page prompt 一致性 check

**What to build:** 跨页面 prompt 一致性守护:`_triggers.py` 中的 wake_word prompt 与 dashboard `quick_actions` 中的 prompt 必须来自同一 SoT,且字面一致。

依据:D7(spec 实现细节)。

**Blocked by:** 07, 09

- [ ] 扩展 `scripts/check_prompt_quality.py`(或新建 `scripts/check_prompt_soak.py`):对每个 dashboard `quick_action.wake_word`,校验 `quick_actions[i].prompt` 与 `_triggers.TRIGGERS[wake_word].main_prompt.text` 字节相同
- [ ] 校验 `help_center.html` 渲染时 `__DATA__.triggers[*].main_prompt.text` 与 `_triggers` 一致(避免 help 渲染层二次编辑漂移)
- [ ] 新增 `tests/test_redesign.py::test_cross_page_prompt_consistency`:mock 下渲染 help_center + home,parse 两个 JSON,逐 wake_word 比较 prompt 文本
- [ ] 失败时报具体 wake_word + 两端文本 diff(方便定位)