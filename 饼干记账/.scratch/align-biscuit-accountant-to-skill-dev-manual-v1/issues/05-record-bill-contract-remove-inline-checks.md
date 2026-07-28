# 05 — 删除 `record_bill.py` 内联校验（expand–contract 第 2 步：contract）

**What to build:** 移除重复的硬规则代码，DRY 完成 —— `validators.py` 是单一事实源，argparse 类型校验降级为格式检查（不重复业务规则）。

**Blocked by:** 04 — 必须先 expand 才能 contract

**Status:** ready-for-agent

- [ ] `record_bill.py` 的内联 `if amount == 0` / `if category not in ALLOWED` 全部删除
- [ ] argparse 仍保留 `--amount type=float` 这类**格式**校验（非业务规则）
- [ ] `python -m pytest tests/test_render.py` 跑通（确认行为不变）
- [ ] `python -m pytest tests/test_validators.py` 跑通（确认 validators 仍兜底）