# Patch P1-3 + P1-4 + P1-5: 低风险清理三件套

## P1-3 · _category_condition 死代码
- `item_ops.py:73-78` 改为注释清楚的空函数(避免外部 import 引用突然删除报错)
- 真工作的是 `_category_in_clause(conn, category_id)`

## P1-4 · emoji 检测全覆盖
- `category_manager.py` emoji 检测从手写 3 个 unicode range 改用 `unicodedata.category(c) == 'So'`
- 覆盖 emoji 13+ 的 🪑🩰🪓 等所有 So 字符

实测:
  '🪑桌子' → ✗ name 禁 emoji
  '🩰芭蕾鞋' → ✗ name 禁 emoji
  '🎉庆祝' → ✗ name 禁 emoji
  '⚽足球' → ✗ name 禁 emoji
  '普通分类' → OK

## P1-5 · travel_trip.html 标签搜索一致性
- L109 `arr(it.tags).join(' ')` 改为 `arr(it.tags).map(t=>esc(t)).join(' ')`
- 与其他 8 个模板(渲染 .tag chip)对齐,且顺手 XSS 防护
- L142 已是 chips 形式(原本正确),不动

## 验证
- pytest 71/71
- 隔离 emoji 测试通过