# 02 — 集中硬规则到 `validators.py`（§02 第 ③ 规则层）

**What to build:** 用户写入「金额 0 / 金额 NaN / 分类不在白名单 / 时间格式错误」时，CLI 在写入 SQLite 前就被拒绝并返回「字段名 + 当前值 + 期望值 + 怎么修」的错误信息 —— 硬规则集中到 `validators.py`，不再散落 db.py 与 argparse 层。

**Blocked by:** 01 — tests/ 测试地基

**Status:** ready-for-agent

- [ ] 新建 `validators.py`，导出 `validate_amount` / `validate_category` / `validate_record` 三个纯函数
- [ ] 错误信息含「字段名 + 当前值 + 期望值 + 怎么修」四要素
- [ ] `tests/test_validators.py` 覆盖 4 类异常（amount=0 / amount=NaN / category 不在白名单 / time 格式错）+ 2 类正常（amount=-35 / category="餐饮/外卖/午餐"）
- [ ] `python -m pytest tests/test_validators.py` 退出码 0
- [ ] `record_bill.py` / `db.py` **尚未切换**到 validators（expand–contract 第 1 步留给 ticket 04）