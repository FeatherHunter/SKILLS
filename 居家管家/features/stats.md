# 统物品 / 查高频 / 查低频 / 查过期

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
| 查过期 | `expiring`（心愿 ID: 1） |

---

## Step 2: 执行统计

```bash
# 查高频（访问次数最多）
python home_manager.py stats --type frequent --limit 20

# 查低频
python home_manager.py stats --type dormant --limit 20

# 查过期（默认 30 天窗口）
python home_manager.py stats --type expiring

# 查过期（自定义窗口：7 天）
python home_manager.py stats --type expiring --days 7

# 查过期（只看已过期）
python home_manager.py stats --type expiring --expired-only

# 查过期（按顶级分类筛选：食物与饮品）
python home_manager.py stats --type expiring --category-id 137

# 查过期（医药用品二级 60 天内）
python home_manager.py stats --type expiring --category-id 233 --days 60

# 总体统计
python home_manager.py stats --type summary
```

---

## Step 3: 展示结果

AI 展示脚本输出的统计结果。

**查过期输出格式**：

```
⏰ 快过期物品（30天内） TOP20
----------------------------------------------------------------------
  已过期：8  |  3天内：1  |  7天内：0  |  30天内：1
----------------------------------------------------------------------
  ❌已过期 321天 ID:188  太太乐松茸醇鲜调味料 (调味品)
     └ 📍 厨房/东南角/壁柜 ×1[在家]  到期:2025-07-17
  ❌已过期 3天   ID:255  百乐眠胶囊 (医药用品)
     └ 📍 客厅/书架/药箱 ×1[在家]  到期:2026-05-31
  ⏰3天          ID:209  妃子笑荔枝 (食物)
     └ 📍 快递/山姆 ×1[在家]  到期:2026-06-07
  ...
```

**标记说明**：
- `❌已过期 X天`：剩余 X 天（已过期）
- `⏰X天`：X 天后到期（< 8天）
- `📅X天`：X 天后到期（>= 8天）

---

## 访问计数规则

只有以下操作会增加访问计数：
- `update`（明确操作）
- `detail`（明确查看）

以下操作不增加计数：
- `search`
- `list`
- `inventory`（批量查询）
- `stats`（统计不增加访问计数）
