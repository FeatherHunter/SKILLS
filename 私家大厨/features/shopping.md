# 采购清单

> 触发词："生成采购清单"、"要买什么"、"列出采购"、"买什么"、"准备食材"

---

## 功能说明

根据食谱生成采购清单，包括：
- 所需食材（数量单位）
- 按类别分组
- AI采购建议

---

## AI调用规范

### 调用任何manager前，必须：

1. **展示完整参数示例** — 让用户知道这条命令会用哪些参数
2. **对未提供字段进行合理推测** — 基于菜系特点/常见值/烹饪逻辑
3. **推测不出时询问用户** — 不能留空不填

---

## 使用场景

### 生成采购清单
```
用户：宫保虾球需要买什么？
AI：执行命令：
python scripts/shopping_manager.py generate <recipe_id>

【宫保虾球 - 采购清单】

📋 食材清单（共8种）
1. 虾 300g [海鲜]
2. 花生 50g [其他]
3. 干辣椒 10g [调料]
4. 花椒 5g [调料]
5. 葱 1段 [蔬菜]
6. 蒜 3瓣 [蔬菜]
7. 盐 适量 [调料]
8. 料酒 15ml [调料]

🛒 采购建议
- 海鲜类：虾建议买活的，新鲜口感好
- 调料类：花椒、干辣椒一次性多买点，用途广
- 蔬菜类：葱蒜常用，可多备

✅ 采购清单生成成功！
```

### 查看已有采购清单
```
用户：上次宫保虾球的采购清单还在吗？
AI：执行命令：
python scripts/shopping_manager.py list

📋 采购清单列表：
1. 宫保虾球（2026-05-15） ← 最近
2. 红烧肉（2026-05-10）
...
```

### 标记已购买
```
用户：虾买好了
AI：执行命令：
python scripts/shopping_manager.py mark <item_id> --purchased

✅ 已标记为已购买：虾
```

---

## 命令参考（完整参数）

```bash
# 生成采购清单（完整参数）
python scripts/shopping_manager.py generate <recipe_id> \
  [--servings 份数] \
  [--group_by 分类方式]

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --servings                可选：份数（默认使用食谱设定的份量）
#   --group_by                可选：分类方式，category（按食材分类）/ recipe（按食谱分组）

# 示例（完整）：
python scripts/shopping_manager.py generate "8f3b435b-..." \
  --servings 4 \
  --group_by category

# 示例（简单）：
python scripts/shopping_manager.py generate "8f3b435b-..."

# 查看采购清单列表
python scripts/shopping_manager.py list

# 示例
python scripts/shopping_manager.py list

# 标记已购买（完整参数）
python scripts/shopping_manager.py mark <item_id> \
  --purchased \
  [--quantity 购买数量] \
  [--price 购买价格] \
  [--store 购买地点]

# 参数说明：
#   <item_id>                 必需：采购项ID
#   --purchased               必需：标记为已购买
#   --quantity                可选：实际购买数量
#   --price                   可选：购买价格
#   --store                   可选：购买地点/渠道

# 示例（完整）：
python scripts/shopping_manager.py mark "item_uuid" \
  --purchased \
  --quantity 350g \
  --price 45.0 \
  --store 盒马鲜生

# 示例（简单）：
python scripts/shopping_manager.py mark "item_uuid" --purchased

# 清除采购清单
python scripts/shopping_manager.py clear [--recipe_id <recipe_id>]

# 参数说明：
#   --recipe_id                可选：清除指定食谱的采购清单，不填则清除所有

# 示例
python scripts/shopping_manager.py clear
python scripts/shopping_manager.py clear --recipe_id "8f3b435b-..."
```

---

## 采购建议AI逻辑

生成采购清单时，AI应提供以下建议：

| 食材类型 | 建议 |
|---------|------|
| 海鲜 | 选择新鲜的，活虾活鱼最好 |
| 肉类 | 看清日期，冷链保存 |
| 蔬菜 | 当天买当天用，避免浪费 |
| 调料 | 常用调料可一次性多买点 |
| 干货 | 密封保存，避免受潮 |

---

## 参考

- 分类参考：references/categories.md
- 命令行参考：references/commands.md
- 表结构：references/database_schema.md