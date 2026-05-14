# CLI命令参考

所有数据操作必须通过CLI，禁止直连数据库。

---

## 初始化

```bash
python scripts/init_db.py
```

---

## 1. 食谱管理（recipes）

```bash
# 添加食谱
python scripts/recipe_manager.py add <菜名> [--description "..."] [--difficulty 中等] [--servings 2] [--total_time 25] [--status 未做] [--source "视频"] [--source_url "..."]

# 查看食谱详情
python scripts/recipe_manager.py show <菜名或ID>

# 列出食谱
python scripts/recipe_manager.py list
python scripts/recipe_manager.py list --difficulty 中等
python scripts/recipe_manager.py list --status 已做

# 搜索食谱
python scripts/recipe_manager.py search <关键词>

# 更新食谱
python scripts/recipe_manager.py update <recipe_id> [--name "新菜名"] [--difficulty 困难] [--status 熟练]

# 健康检查
python scripts/recipe_manager.py lint <recipe_id>

# 废弃食谱
python scripts/recipe_manager.py discard <recipe_id>
```

---

## 2. 分类管理

### 2.1 菜系/地区/国家（recipe_categories）

```bash
python scripts/category_manager.py add <recipe_id> --cuisine 川菜 [--region 中国-四川] [--country 中国]
python scripts/category_manager.py list <recipe_id>
python scripts/category_manager.py search <菜系>
python scripts/category_manager.py update <recipe_id> [--cuisine 新菜系]
```

### 2.2 季节（recipe_seasons）

```bash
python scripts/season_manager.py add <recipe_id> --season 春,秋
python scripts/season_manager.py list <recipe_id>
python scripts/season_manager.py search <季节>
```

### 2.3 烹饪方式（recipe_cooking_methods）

```bash
python scripts/cooking_method_manager.py add <recipe_id> --method 炒,煎
python scripts/cooking_method_manager.py list <recipe_id>
python scripts/cooking_method_manager.py search <方式>
```

### 2.4 口味（recipe_flavors）

```bash
python scripts/flavor_manager.py add <recipe_id> --flavor 辣,麻
python scripts/flavor_manager.py list <recipe_id>
python scripts/flavor_manager.py search <口味>
```

### 2.5 饮食标签（recipe_diet_tags）

```bash
python scripts/diet_tag_manager.py add <recipe_id> --tag 无辣,素食
python scripts/diet_tag_manager.py list <recipe_id>
python scripts/diet_tag_manager.py search <标签>
```

### 2.6 用餐类型（recipe_meal_types）

```bash
python scripts/meal_type_manager.py add <recipe_id> --meal_type 晚,夜宵
python scripts/meal_type_manager.py list <recipe_id>
python scripts/meal_type_manager.py search <类型>
```

---

## 3. 食材管理（ingredients）

```bash
# 添加食材
python scripts/ingredient_manager.py add <recipe_id> --name 虾 --quantity 300 --unit g --category 海鲜 [--sequence 1] [--optional] [--substitute 鸡肉]

# 查看食材清单
python scripts/ingredient_manager.py list <recipe_id>

# 搜索包含某食材的食谱
python scripts/ingredient_manager.py search <食材名>

# 更新食材
python scripts/ingredient_manager.py update <ingredient_id> [--name 新名称] [--quantity 350] [--category 新分类]
```

---

## 4. 步骤管理（cooking_steps）

```bash
# 添加步骤
python scripts/step_manager.py add <recipe_id> --action <动作描述> [--sequence 1] [--duration 10] [--heat_level 中火] [--temperature 160度] [--expected_result 颜色金黄]

# 查看步骤列表
python scripts/step_manager.py list <recipe_id>

# 搜索步骤
python scripts/step_manager.py search <关键词>

# 更新步骤
python scripts/step_manager.py update <step_id> [--action 新动作] [--duration 5] [--heat_level 大火]

# 调整步骤顺序
python scripts/step_manager.py reorder <recipe_id> --from 2 --to 3
```

---

## 5. 步骤×食材关联（step_ingredients）

```bash
# 关联食材到步骤
python scripts/step_ingredient_manager.py add --step_id <step_id> --ingredient_id <ingredient_id> [--quantity_used 30] [--introduced_at 出锅前]

# 查看某步骤的食材
python scripts/step_ingredient_manager.py list-by-step <step_id>

# 查看某食材被哪些步骤使用
python scripts/step_ingredient_manager.py list-by-ingredient <ingredient_id>

# 移除关联
python scripts/step_ingredient_manager.py remove <link_id>
```

---

## 6. 技法管理（step_techniques）

```bash
# 添加技法
python scripts/technique_manager.py add --recipe_id <id> --technique_name 爆炒 [--step_id <step_id>] [--description "大火热油快速翻炒"] [--key_points "油温要高/翻炒要快"]

# 查看某食谱的所有技法
python scripts/technique_manager.py list-by-recipe <recipe_id>

# 查看某步骤的技法
python scripts/technique_manager.py list-by-step <step_id>

# 搜索技法
python scripts/technique_manager.py search <关键词>

# 更新技法
python scripts/technique_manager.py update <technique_id> [--technique_name 新名称] [--key_points 新要点]
```

---

## 7. 小贴士（tips）

```bash
# 添加小贴士（关联到食谱）
python scripts/tip_manager.py add <recipe_id> --content <技巧内容> [--category 火候] [--priority 1]

# 添加小贴士（关联到步骤）
python scripts/tip_manager.py add <recipe_id> --step_id <step_id> --content <技巧内容> [--category 火候]

# 添加小贴士（关联到食材）
python scripts/tip_manager.py add <recipe_id> --ingredient_id <ingredient_id> --content <技巧内容> [--category 刀工]

# 查看小贴士
python scripts/tip_manager.py list <recipe_id>
python scripts/tip_manager.py list-by-step <step_id>
python scripts/tip_manager.py list-by-ingredient <ingredient_id>

# 搜索小贴士
python scripts/tip_manager.py search <关键词>

# 更新小贴士
python scripts/tip_manager.py update <tip_id> [--content 新内容] [--category 新分类]
```

---

## 8. 烹饪历史（recipe_history）

```bash
# 记录做菜
python scripts/history_manager.py add <recipe_id> [--cook_date 2025-07-25] [--rating 4.5] [--feedback "盐放多了"]

# 查看历史
python scripts/history_manager.py list <recipe_id>

# 统计
python scripts/history_manager.py stats <recipe_id>

# 更新记录
python scripts/history_manager.py update <history_id> [--rating 4.0] [--feedback "调整了盐量"]
```

---

## 9. 背景知识（background_knowledge）

```bash
# 添加背景知识
python scripts/background_manager.py add <recipe_id> --origin_story <起源故事> [--historical_background <历史背景>] [--cultural_significance <文化意义>]

# 查看背景
python scripts/background_manager.py get <recipe_id>

# 更新背景
python scripts/background_manager.py update <recipe_id> [--origin_story <新故事>]
```

---

## 10. 派生关系（recipe_relations）

```bash
# 创建派生关系
python scripts/relation_manager.py add --parent_id <id> --child_id <id> [--relation_type 变体] [--change_summary "减少干辣椒"]

# 查看派生关系
python scripts/relation_manager.py list-parent <recipe_id>
python scripts/relation_manager.py list-child <recipe_id>

# 列出所有关系
python scripts/relation_manager.py list-all

# 更新关系
python scripts/relation_manager.py update <relation_id> [--change_summary "新说明"]
```

---

## 11. 炊具（cookware）

```bash
# 添加炊具
python scripts/cookware_manager.py add <recipe_id> --name 电饭锅 [--category 锅]

# 查看炊具
python scripts/cookware_manager.py list <recipe_id>

# 按炊具搜索食谱
python scripts/cookware_manager.py search <炊具名>

# 更新炊具
python scripts/cookware_manager.py update <cookware_id> [--name 新名称] [--category 新分类]
```

---

## 12. 营养信息（nutrition_info）

```bash
# 添加营养信息
python scripts/nutrition_manager.py add <recipe_id> [--serving_size 200] [--serving_unit g] [--calories 320] [--protein 28] [--fat 18] [--carbs 20] [--fiber 2] [--sodium 800]

# 查看营养信息
python scripts/nutrition_manager.py get <recipe_id>

# 列出有营养信息的食谱
python scripts/nutrition_manager.py list [--sort calories|protein|fat]

# 搜索高蛋白食谱
python scripts/nutrition_manager.py search-high-protein [--threshold 20]

# 更新营养信息
python scripts/nutrition_manager.py update <recipe_id> [--calories 300] [--protein 30]
```

---

## 字段值参考

### 难度
快手菜 / 简单 / 中等 / 困难 / 大师

### 季节
春 / 夏 / 秋 / 冬

### 烹饪方式
炒 / 蒸 / 煮 / 烤 / 炸 / 煎 / 焖 / 炖 / 拌 / 卤 / 熏

### 口味
酸 / 甜 / 辣 / 咸 / 鲜 / 苦 / 麻

### 饮食标签
素食 / 清真 / 无辣 / 低碳 / 无糖 / 低脂 / 无麸质 / 高蛋白

### 用餐类型
早 / 中 / 晚 / 夜宵 / 下午茶 / 聚会

### 食材分类
肉类 / 蔬菜 / 调料 / 海鲜 / 豆制品 / 蛋类 / 主食 / 干货 / 其他

### 炊具分类
锅 / 炉 / 刀 / 其他

### 小贴士分类
火候 / 刀工 / 调味 / 采购 / 设备 / 保存

### 关系类型
派生 / 变体 / 改良

### 状态
未做 / 已做 / 熟练 / 已废弃