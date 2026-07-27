# Patch P0-6: stats summary 总价值按 qty 加权

## 改前
```sql
SELECT ROUND(SUM(purchase_price), 2) AS total_value
FROM items WHERE purchase_price IS NOT NULL AND purchase_price > 0
```
→ 显示 ¥32539.67(只算 item.unit_price × 1,与实际库存价值不符)

## 改后
```sql
SELECT ROUND(SUM(COALESCE(i.purchase_price, 0) * COALESCE(q.qty, 0)), 2) AS total_value
FROM items i
LEFT JOIN (SELECT item_id, SUM(quantity) AS qty FROM item_locations GROUP BY item_id) q
  ON q.item_id = i.id
WHERE i.purchase_price IS NOT NULL AND i.purchase_price > 0
```
→ 显示 ¥256776.91(× qty 真实库存价值)

## 验证
- `python3 ... stats --type summary` 显示 ¥256776.91(原 ¥32539.67)
- pytest 71/71

## 范围
本 patch 只改 `_stats_summary` 一处(CLI 文本模式);
`_stats_summary_payload`(HTML)同样 BUG,Phase 2 一起修。