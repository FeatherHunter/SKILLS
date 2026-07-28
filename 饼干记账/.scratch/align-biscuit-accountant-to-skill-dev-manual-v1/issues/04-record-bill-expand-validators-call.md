# 04 — `record_bill.py` 切换到 `validators.py` 调用（expand–contract 第 1 步）

**What to build:** 用户用 `record_bill.py add --amount 0` 时看到的错误信息比之前 argparse 的「invalid float value」更清晰（字段名 + 当前值 + 期望值 + 怎么修）—— 新校验（validators）+ 旧校验（argparse + 内联 if）共存于 expand 阶段。

**Blocked by:** 02 — validators.py

**Status:** ready-for-agent

- [ ] `record_bill.py` 的 cmd_add / cmd_update 路径上调用 `validators.py` 的函数
- [ ] 旧的 argparse 类型校验与内联 `if amount == 0` / `if category not in ALLOWED` 仍保留（expand 阶段：新校验先于旧校验跑）
- [ ] 9 个 query_type 命令路径不受影响（仅写路径切到 validators）
- [ ] `tests/test_render.py` 加测试：`add --amount 0` 返回的错误信息含四要素
- [ ] 不修改 `db.py`（db.py CHECK 留给 ticket 03）