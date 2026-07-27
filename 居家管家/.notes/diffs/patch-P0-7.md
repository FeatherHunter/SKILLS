# Patch P0-7: stats --type summary NULL 价格不崩

## diff
- `inventory_ops.py:745` `:priced['total_value']:.2f` → `:priced['total_value'] or 0:.2f`

## 验证
- `python3 ... stats --type summary` 在全 NULL 时 exit=0,展示 ¥0.00(原来 TypeError)