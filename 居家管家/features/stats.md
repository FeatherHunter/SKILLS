# 统物品 / 查高频 / 查低频

## 流程概述

1. 选择统计类型
2. 执行统计
3. 展示结果

---

## Step 1: 选择统计类型

| 唤醒词 | 类型 |
|--------|------|
| 查高频 | `frequent` |
| 查低频 | `dormant` |
| 统物品 | `summary` |

---

## Step 2: 执行统计

```bash
# 查高频（访问次数最多）
python home_manager.py stats --type frequent --limit 20

# 查低频
python home_manager.py stats --type dormant --limit 20

# 总体统计
python home_manager.py stats --type summary
```

---

## Step 3: 展示结果

AI 展示脚本输出的统计结果。

---

## 访问计数规则

只有以下操作会增加访问计数：
- `update`（明确操作）
- `detail`（明确查看）

以下操作不增加计数：
- `search`
- `list`
- `inventory`（批量查询）