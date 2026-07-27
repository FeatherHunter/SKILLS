# Patch P0-2: update_item 硬规则统一校验

## diff
- `scripts/home_manager/item_ops.py:update_item` 入口加硬规则守卫

## 实测(隔离 temp DB)
| 输入 | 旧行为 | 新行为 |
|---|---|---|
| `--quantity -5` | ✓ 写 -5 入 DB | ✗ 拒绝 exit=1 |
| `--purchase-date not-a-date` | ✓ 写字符串入 DB | ✗ 拒绝 exit=1 |
| `--new-location 客厅`(单级) | ✓ 写单级入 DB | ✗ 拒绝 exit=1 |
| `--purchase-date 2026-01-15 --quantity 5` | ✓ | ✓ 通过 |