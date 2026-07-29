Status: ready-for-agent

# 03 — ADR-0002 expand: 查吃的记录 as alias 声明

**What to build:** 在不破坏现有行为的前提下,声明 `查吃的记录` 是 `查今天吃` 的 alias。两个 wake word 都触发同一条渲染路径。

依据:ADR-0002 expand 阶段。

**Blocked by:** None — can start immediately

- [ ] `_triggers.py` 中 `查吃的记录` 加 `alias_of: '查今天吃'` 字段
- [ ] `check_trigger_consistency.py` 升级识别 alias 关系:aliasOf 字段必须指向已存在的 wake_word
- [ ] 两个 wake word 各自 prompt 文本保留(暂时不变,留作 04 时统一)
- [ ] mock 数据保留(2 套不变),后续 04 再合并
- [ ] 测试:`查吃的记录` 仍能触发 HTML 渲染(行为不退化)