# 搜索/筛选食谱

> 触发词："找川菜"、"搜索排骨"、"有哪些菜"、"过滤"、"筛选"

---

## 功能说明

用户想找某道菜或按条件筛选时使用。

**搜索方式**：
1. 按菜名搜索（关键词模糊匹配）
2. 按分类筛选（菜系/季节/口味/烹饪方式等）
3. 按难度筛选
4. 按状态筛选
5. 按食材搜索（哪些菜用了XX食材）
6. 组合搜索（多个条件）

---

## AI调用规范

### 调用任何manager前，必须：

1. **展示完整参数示例** — 让用户知道这条命令会用哪些参数
2. **对未提供字段进行合理推测** — 基于菜系特点/常见值/烹饪逻辑
3. **推测不出时询问用户** — 不能留空不填

---

## 搜索类型

### 按菜名搜索
```
用户：搜索排骨
AI：执行命令：
python scripts/recipe_manager.py search 排骨

找到以下包含"排骨"的食谱：
1. 酱大骨（川菜，中等难度，45分钟）
2. 糯米排骨（粤菜，中等难度，60分钟）
...
```

### 按分类筛选

| 用户说 | 筛选字段 | 命令 |
|--------|---------|------|
| "川菜有哪些" | recipe_categories.cuisine_type = '川菜' | `python scripts/category_manager.py search 川菜` |
| "夏天吃什么" | recipe_seasons.season = '夏' | `python scripts/season_manager.py search 夏` |
| "炒菜有哪些" | recipe_cooking_methods.method = '炒' | `python scripts/cooking_method_manager.py search 炒` |
| "辣的有哪些" | recipe_flavors.flavor = '辣' | `python scripts/flavor_manager.py search 辣` |
| "早餐吃什么" | recipe_meal_types.meal_type = '早' | `python scripts/meal_type_manager.py search 早` |

### 按难度筛选
```
用户：来个简单的
AI：执行命令：
python scripts/recipe_manager.py list --difficulty 简单

筛选条件：难度 in (快手菜, 简单)

1. 西红柿炒蛋（快手菜，10分钟）
2. 蒜蓉青菜（简单，15分钟）
...
```

### 按状态筛选
```
用户：找已做的菜
AI：执行命令：
python scripts/recipe_manager.py list --status 已做

已做的食谱：
1. 宫保虾球（熟练，做过5次，评分4.5）
2. 麻婆豆腐（已做，做过2次，评分4.0）
...
```

### 按食材搜索
```
用户：哪些菜用了虾
AI：执行命令：
python scripts/ingredient_manager.py search 虾

用到"虾"的食谱：
1. 宫保虾球
2. 麻婆豆腐焗大虾
3. 罗汉大虾
...
```

### 组合搜索
```
用户：找个辣的川菜，30分钟能搞定的
AI：筛选条件：
- 菜系：川菜
- 口味：辣
- 总时间 ≤ 30分钟

执行命令：
python scripts/category_manager.py search 川菜

然后过滤时间：
1. 宫保虾球（25分钟，辣）
2. 鱼香肉丝（20分钟，辣）
...
```

---

## 搜索命令参考（完整参数）

```bash
# 按菜名搜索
python scripts/recipe_manager.py search <关键词>

# 示例
python scripts/recipe_manager.py search 排骨

# 按菜系搜索
python scripts/category_manager.py search <菜系>

# 示例
python scripts/category_manager.py search 川菜

# 按季节搜索
python scripts/season_manager.py search <季节>

# 示例
python scripts/season_manager.py search 夏

# 按烹饪方式搜索
python scripts/cooking_method_manager.py search <方式>

# 示例
python scripts/cooking_method_manager.py search 炒

# 按口味搜索
python scripts/flavor_manager.py search <口味>

# 示例
python scripts/flavor_manager.py search 辣

# 按饮食标签搜索
python scripts/diet_tag_manager.py search <标签>

# 示例
python scripts/diet_tag_manager.py search 高蛋白

# 按用餐类型搜索
python scripts/meal_type_manager.py search <类型>

# 示例
python scripts/meal_type_manager.py search 晚

# 按食材搜索
python scripts/ingredient_manager.py search <食材名>

# 示例
python scripts/ingredient_manager.py search 虾

# 按难度搜索
python scripts/recipe_manager.py list --difficulty <难度>

# 示例
python scripts/recipe_manager.py list --difficulty 简单

# 按状态搜索
python scripts/recipe_manager.py list --status <状态>

# 示例
python scripts/recipe_manager.py list --status 已做

# 按炊具搜索
python scripts/cookware_manager.py search <炊具名>

# 示例
python scripts/cookware_manager.py search 砂锅

# 搜索步骤
python scripts/step_manager.py search <关键词>

# 示例
python scripts/step_manager.py search 腌制

# 搜索小贴士
python scripts/tip_manager.py search <关键词>

# 示例
python scripts/tip_manager.py search 火候

# 搜索高蛋白食谱
python scripts/nutrition_manager.py search-high-protein [--threshold <数值>]

# 示例
python scripts/nutrition_manager.py search-high-protein --threshold 20

# 列出有营养信息的食谱
python scripts/nutrition_manager.py list [--sort calories|protein|fat]

# 示例
python scripts/nutrition_manager.py list --sort protein

# 查看所有食谱
python scripts/recipe_manager.py list
```

---

## 输出格式

搜索结果统一格式：
```
找到 X 道菜：

序号 | 菜名 | 难度 | 总时间 | 状态 | 评分
-----|------|------|--------|------|----
1 | 宫保虾球 | 中等 | 25分钟 | 熟练 | 4.5
2 | 麻婆豆腐焗大虾 | 困难 | 40分钟 | 已做 | 4.0
...
```

---

## 参考

- 分类参考：references/categories.md
- 命令行参考：references/commands.md
- 表结构：references/database_schema.md