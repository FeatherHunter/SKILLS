# CLI命令参考

> ⚠️ **AI使用规范**：调用任何manager前，先展示完整参数示例。
> 对于用户未提供的字段，进行合理推测（基于常见值/菜系特点/烹饪逻辑）。
> 推测不出时，**必须询问用户**，不得留空。

所有数据操作必须通过CLI，禁止直连数据库。

---

## 初始化

```bash
python scripts/init_db.py
```

---

## 1. 食谱管理（recipes）

```bash
# 添加食谱 - 完整参数
python scripts/recipe_manager.py add <菜名> \
  --description "一句话描述" \
  --difficulty 难度 \
  --servings 份量 \
  --total_time 总时间分钟数 \
  --status 状态 \
  --photo_url 图片URL或本地路径 \
  --source 来源说明 \
  --source_url 原始链接

# 参数说明：
#   <菜名>                    必需：菜名
#   --description             可选：一句话描述，如"川菜经典，虾球Q弹"
#   --difficulty              可选：快手菜/简单/中等/困难/大师
#   --servings                可选：份量（人数），默认2
#   --total_time              可选：总时间（分钟），默认30
#   --status                  可选：未做/已做/熟练，默认未做
#   --photo_url               可选：成品照片URL或本地路径
#   --source                  可选：来源，如"中餐厅节目"
#   --source_url              可选：原始食谱链接

# 示例（完整）：
python scripts/recipe_manager.py add "宫保虾球" \
  --description "川菜经典，虾球Q弹，酸甜微辣" \
  --difficulty 中等 \
  --servings 2 \
  --total_time 25 \
  --status 未做 \
  --photo_url "/path/to/photo.jpg" \
  --source "中餐厅节目" \
  --source_url "https://example.com/recipe"

# 查看食谱详情
python scripts/recipe_manager.py show <菜名或ID>

# 列出食谱
python scripts/recipe_manager.py list
python scripts/recipe_manager.py list --difficulty 中等
python scripts/recipe_manager.py list --status 已做

# 搜索食谱
python scripts/recipe_manager.py search <关键词>

# 更新食谱（完整参数）
python scripts/recipe_manager.py update <recipe_id> \
  --name "新菜名" \
  --description "新描述" \
  --difficulty 困难 \
  --servings 4 \
  --total_time 45 \
  --status 熟练 \
  --photo_url "新图片URL" \
  --source "新来源"

# 健康检查
python scripts/recipe_manager.py lint <recipe_id>

# 废弃食谱
python scripts/recipe_manager.py discard <recipe_id>
```

---

## 2. 分类管理

### 2.1 菜系/地区/国家（recipe_categories）

```bash
# 添加分类 - 完整参数
python scripts/category_manager.py add <recipe_id> \
  --cuisine 菜系 \
  --region 地区 \
  --country 国家

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --cuisine                 可选：川菜/粤菜/湘菜/东北菜/台湾菜/福建菜/京菜/苏菜/浙菜/新疆菜/本帮菜
#   --region                  可选：地区，如"中国-四川"
#   --country                 可选：国家，如"中国"

# 示例（完整）：
python scripts/category_manager.py add "8f3b435b-..." \
  --cuisine 川菜 \
  --region 中国-四川 \
  --country 中国

# 列出某食谱的分类
python scripts/category_manager.py list <recipe_id>

# 搜索菜系
python scripts/category_manager.py search <菜系>

# 更新分类
python scripts/category_manager.py update <recipe_id> \
  --cuisine 新菜系 \
  --region 新地区
```

### 2.2 季节（recipe_seasons）

```bash
# 添加季节 - 完整参数（支持多选，用逗号分隔）
python scripts/season_manager.py add <recipe_id> --season 春,夏,秋,冬

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --season                  必需：季节，可多选
#                            有效值：春/夏/秋/冬

# 示例（完整）：
python scripts/season_manager.py add "8f3b435b-..." --season 春,秋

# 列出某食谱的季节
python scripts/season_manager.py list <recipe_id>

# 搜索季节
python scripts/season_manager.py search <季节>
```

### 2.3 烹饪方式（recipe_cooking_methods）

```bash
# 添加烹饪方式 - 完整参数（支持多选，用逗号分隔）
python scripts/cooking_method_manager.py add <recipe_id> --method 炒,煎,焖

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --method                  必需：烹饪方式，可多选
#                            有效值：炒/蒸/煮/烤/炸/煎/焖/炖/拌/卤/熏

# 示例（完整）：
python scripts/cooking_method_manager.py add "8f3b435b-..." --method 炒,蒸

# 列出某食谱的烹饪方式
python scripts/cooking_method_manager.py list <recipe_id>

# 搜索烹饪方式
python scripts/cooking_method_manager.py search <方式>
```

### 2.4 口味（recipe_flavors）

```bash
# 添加口味 - 完整参数（支持多选，用逗号分隔）
python scripts/flavor_manager.py add <recipe_id> --flavor 辣,酸甜,酱香

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --flavor                  必需：口味，可多选
#                            有效值：酸/甜/辣/咸/鲜/苦/麻

# 示例（完整）：
python scripts/flavor_manager.py add "8f3b435b-..." --flavor 辣,酸甜

# 列出某食谱的口味
python scripts/flavor_manager.py list <recipe_id>

# 搜索口味
python scripts/flavor_manager.py search <口味>
```

### 2.5 饮食标签（recipe_diet_tags）

```bash
# 添加饮食标签 - 完整参数（支持多选，用逗号分隔）
python scripts/diet_tag_manager.py add <recipe_id> --tag 荤菜,高蛋白,低脂

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --tag                     必需：饮食标签，可多选
#                            有效值：素食/清真/无辣/低碳/无糖/低脂/无麸质/高蛋白

# 示例（完整）：
python scripts/diet_tag_manager.py add "8f3b435b-..." --tag 荤菜,高蛋白

# 列出某食谱的饮食标签
python scripts/diet_tag_manager.py list <recipe_id>

# 搜索标签
python scripts/diet_tag_manager.py search <标签>
```

### 2.6 用餐类型（recipe_meal_types）

```bash
# 添加用餐类型 - 完整参数（支持多选，用逗号分隔）
python scripts/meal_type_manager.py add <recipe_id> --meal_type 早,中,晚,夜宵

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --meal_type               必需：用餐类型，可多选
#                            有效值：早/中/晚/夜宵/下午茶/聚会

# 示例（完整）：
python scripts/meal_type_manager.py add "8f3b435b-..." --meal_type 午,晚

# 列出某食谱的用餐类型
python scripts/meal_type_manager.py list <recipe_id>

# 搜索用餐类型
python scripts/meal_type_manager.py search <类型>
```

---

## 3. 食材管理（ingredients）

```bash
# 添加食材 - 完整参数
python scripts/ingredient_manager.py add <recipe_id> \
  --name 食材名称 \
  --quantity 用量数值 \
  --unit 单位 \
  --category 食材分类 \
  --sequence 序号 \
  --optional \
  --substitute 替代食材 \
  --quantity_text 文字描述

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --name                    必需：食材名称
#   --quantity                可选：用量数值，如300
#   --unit                    可选：单位，g/kg/ml/L/个/勺/把/茶匙/杯/段/瓣
#   --category                可选：肉类/蔬菜/调料/海鲜/豆制品/蛋类/主食/干货/其他
#   --sequence                可选：添加顺序，默认按已有顺序+1
#   --optional                可选：标记为可选食材
#   --substitute              可选：替代食材名称
#   --quantity_text           可选：文字描述，如"适量"、"少许"

# 示例（完整）：
python scripts/ingredient_manager.py add "8f3b435b-..." \
  --name 虾 \
  --quantity 300 \
  --unit g \
  --category 海鲜 \
  --sequence 1 \
  --optional \
  --substitute 鸡胸肉

# 示例（简单）：
python scripts/ingredient_manager.py add "8f3b435b-..." --name 虾 --quantity 300 --unit g --category 海鲜

# 查看食材清单
python scripts/ingredient_manager.py list <recipe_id>

# 搜索包含某食材的食谱
python scripts/ingredient_manager.py search <食材名>

# 更新食材
python scripts/ingredient_manager.py update <ingredient_id> \
  --name 新名称 \
  --quantity 350 \
  --unit g \
  --category 新分类 \
  --substitute 新替代
```

---

## 4. 步骤管理（cooking_steps）

```bash
# 添加步骤 - 完整参数
python scripts/step_manager.py add <recipe_id> \
  --action 动作描述 \
  --sequence 步骤序号 \
  --duration 时长分钟数 \
  --heat_level 火候 \
  --temperature 温度描述 \
  --expected_result 预期效果

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --action                  必需：动作描述，如"虾去壳开背，用料酒腌制10分钟"
#   --sequence                可选：步骤序号，默认自动+1
#   --duration                可选：该步时长（分钟）
#   --heat_level              可选：火候，微火/小火/中火/大火/猛火
#   --temperature             可选：温度描述，如"160度"、"中小火"
#   --expected_result         可选：预期效果，如"颜色金黄"、"汤汁浓稠"

# 示例（完整）：
python scripts/step_manager.py add "8f3b435b-..." \
  --action "大火热油，虾下锅炸至变色捞出" \
  --sequence 2 \
  --duration 3 \
  --heat_level 大火 \
  --temperature 180度 \
  --expected_result "虾肉变红，表面微焦"

# 示例（简单）：
python scripts/step_manager.py add "8f3b435b-..." --action "虾去壳开背" --duration 10

# 查看步骤列表
python scripts/step_manager.py list <recipe_id>

# 搜索步骤
python scripts/step_manager.py search <关键词>

# 更新步骤
python scripts/step_manager.py update <step_id> \
  --action 新动作 \
  --duration 5 \
  --heat_level 小火 \
  --temperature 120度 \
  --expected_result 新效果

# 调整步骤顺序
python scripts/step_manager.py reorder <recipe_id> --from 2 --to 3
```

---

## 5. 步骤×食材关联（step_ingredients）

```bash
# 关联食材到步骤 - 完整参数
python scripts/step_ingredient_manager.py add \
  --step_id <step_id> \
  --ingredient_id <ingredient_id> \
  --quantity_used 用量 \
  --introduced_at 引入时机描述

# 参数说明：
#   --step_id                 必需：步骤ID
#   --ingredient_id            必需：食材ID
#   --quantity_used            可选：该步骤中使用该食材的用量
#   --introduced_at            可选：引入时机描述，如"开局加入"、"出锅前"

# 示例（完整）：
python scripts/step_ingredient_manager.py add \
  --step_id 36d89769-5c2b-41b1-bf73-4c6b28f69506 \
  --ingredient_id 10d8baa0-9804-4e48-8114-b6be8ba38c57 \
  --quantity_used 500 \
  --introduced_at "开局加入"

# 示例（简单）：
python scripts/step_ingredient_manager.py add \
  --step_id 36d89769-... \
  --ingredient_id 10d8baa0-...

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
# 添加技法 - 完整参数
python scripts/technique_manager.py add \
  --recipe_id <recipe_id> \
  --step_id <step_id> \
  --technique_name 技法名称 \
  --description 技法解释 \
  --key_points 关键要点

# 参数说明：
#   --recipe_id               必需：食谱ID
#   --step_id                 可选：关联的步骤ID
#   --technique_name          必需：技法名称，如"爆炒"、"滑炒"、"煸炒"
#   --description              可选：技法解释，如"大火热油，快速翻炒"
#   --key_points              可选：关键要点，用/分隔，如"油温要高/翻炒要快"

# 示例（完整）：
python scripts/technique_manager.py add \
  --recipe_id 8f3b435b-... \
  --step_id 36d89769-... \
  --technique_name 爆炒 \
  --description "大火热油快速翻炒，使食材外焦里嫩" \
  --key_points "油温要高/翻炒要快/时间要短"

# 示例（简单）：
python scripts/technique_manager.py add \
  --recipe_id 8f3b435b-... \
  --technique_name 爆炒

# 查看某食谱的所有技法
python scripts/technique_manager.py list-by-recipe <recipe_id>

# 查看某步骤的技法
python scripts/technique_manager.py list-by-step <step_id>

# 搜索技法
python scripts/technique_manager.py search <关键词>

# 更新技法
python scripts/technique_manager.py update <technique_id> \
  --technique_name 新名称 \
  --key_points "新要点1/新要点2"
```

---

## 7. 小贴士（tips）

```bash
# 添加小贴士 - 完整参数（可关联到食谱/步骤/食材）
python scripts/tip_manager.py add <recipe_id> \
  --content 技巧内容 \
  --category 分类 \
  --priority 优先级 \
  --step_id <关联步骤ID> \
  --ingredient_id <关联食材ID>

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --content                  必需：技巧内容
#   --category                 可选：火候/刀工/调味/采购/设备/保存
#   --priority                 可选：优先级（数字越小越重要），默认3
#   --step_id                  可选：关联的步骤ID
#   --ingredient_id            可选：关联的食材ID

# 示例（关联到步骤）：
python scripts/tip_manager.py add "8f3b435b-..." \
  --step_id 36d89769-... \
  --content "开背时去虾线更入味" \
  --category 刀工 \
  --priority 1

# 示例（关联到食材）：
python scripts/tip_manager.py add "8f3b435b-..." \
  --ingredient_id 10d8baa0-... \
  --content "选择新鲜活虾，口感更Q弹" \
  --category 采购 \
  --priority 2

# 示例（关联到食谱全局）：
python scripts/tip_manager.py add "8f3b435b-..." \
  --content "这是一道非常经典的川菜" \
  --category 文化 \
  --priority 3

# 查看小贴士
python scripts/tip_manager.py list <recipe_id>
python scripts/tip_manager.py list-by-step <step_id>
python scripts/tip_manager.py list-by-ingredient <ingredient_id>

# 搜索小贴士
python scripts/tip_manager.py search <关键词>

# 更新小贴士
python scripts/tip_manager.py update <tip_id> \
  --content 新内容 \
  --category 新分类
```

---

## 8. 烹饪历史（recipe_history）

```bash
# 记录做菜 - 完整参数
python scripts/history_manager.py add <recipe_id> \
  --cook_date 烹饪日期 \
  --rating 评分 \
  --feedback 用户反馈

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --cook_date               可选：烹饪日期，格式YYYY-MM-DD，默认今天
#   --rating                  可选：评分（1-5）
#   --feedback                可选：用户反馈/备注

# 示例（完整）：
python scripts/history_manager.py add "8f3b435b-..." \
  --cook_date 2026-05-15 \
  --rating 4.5 \
  --feedback "味道不错，虾很Q弹，下次可以少放点盐"

# 示例（简单）：
python scripts/history_manager.py add "8f3b435b-..." --rating 4.5

# 查看历史
python scripts/history_manager.py list <recipe_id>

# 统计（次数、评分、反馈）
python scripts/history_manager.py stats <recipe_id>

# 更新记录
python scripts/history_manager.py update <history_id> \
  --rating 4.0 \
  --feedback "调整了盐量，味道更好"
```

---

## 9. 背景知识（background_knowledge）

```bash
# 添加背景知识 - 完整参数
python scripts/background_manager.py add <recipe_id> \
  --origin_story 起源故事 \
  --historical_background 历史背景 \
  --cultural_significance 文化意义

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --origin_story             可选：起源故事
#   --historical_background     可选：历史背景
#   --cultural_significance     可选：文化意义

# 示例（完整）：
python scripts/background_manager.py add "8f3b435b-..." \
  --origin_story "宫保虾球源自川菜宫保鸡丁的变体，由山东人丁宝桢发明" \
  --historical_background "清代丁宝桢任四川总督时改良此菜，成为经典川菜" \
  --cultural_significance "代表川菜小荔枝口的经典味型，流传至今"

# 示例（简单）：
python scripts/background_manager.py add "8f3b435b-..." \
  --origin_story "起源于宋代，是传统的节日菜肴"

# 查看背景
python scripts/background_manager.py get <recipe_id>

# 更新背景
python scripts/background_manager.py update <recipe_id> \
  --origin_story 新故事
```

---

## 10. 派生关系（recipe_relations）

```bash
# 创建派生关系 - 完整参数
python scripts/relation_manager.py add \
  --parent_id <父食谱ID> \
  --child_id <子食谱ID> \
  --relation_type 关系类型 \
  --change_summary 变更说明

# 参数说明：
#   --parent_id                必需：父食谱ID
#   --child_id                 必需：子食谱ID
#   --relation_type            可选：派生/变体/改良
#   --change_summary            可选：变更说明

# 示例（完整）：
python scripts/relation_manager.py add \
  --parent_id 8f3b435b-... \
  --child_id cde0db94-... \
  --relation_type 变体 \
  --change_summary "减少干辣椒用量，增加甜味，更适合儿童"

# 示例（简单）：
python scripts/relation_manager.py add \
  --parent_id 8f3b435b-... \
  --child_id cde0db94-...

# 查看派生关系
python scripts/relation_manager.py list-parent <recipe_id>
python scripts/relation_manager.py list-child <recipe_id>

# 列出所有关系
python scripts/relation_manager.py list-all

# 更新关系
python scripts/relation_manager.py update <relation_id> \
  --change_summary 新说明
```

---

## 11. 炊具（cookware）

```bash
# 添加炊具 - 完整参数
python scripts/cookware_manager.py add <recipe_id> \
  --name 炊具名称 \
  --category 炊具分类

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --name                    必需：炊具名称，如"电饭锅"/"砂锅"/"烤箱"
#   --category                可选：锅/炉/刀/其他

# 示例（完整）：
python scripts/cookware_manager.py add "8f3b435b-..." \
  --name 砂锅 \
  --category 锅

# 示例（简单）：
python scripts/cookware_manager.py add "8f3b435b-..." --name 炒锅 --category 锅

# 查看炊具
python scripts/cookware_manager.py list <recipe_id>

# 按炊具搜索食谱
python scripts/cookware_manager.py search <炊具名>

# 更新炊具
python scripts/cookware_manager.py update <cookware_id> \
  --name 新名称 \
  --category 新分类
```

---

## 12. 营养信息（nutrition_info）

```bash
# 添加营养信息 - 完整参数
python scripts/nutrition_manager.py add <recipe_id> \
  --serving_size 每份份量数值 \
  --serving_unit 每份份量单位 \
  --calories 每份热量kcal \
  --protein 每份蛋白质g \
  --fat 每份脂肪g \
  --carbs 每份碳水g \
  --fiber 每份膳食纤维g \
  --sodium 每份钠mg

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --serving_size            可选：每份份量数值，如200
#   --serving_unit            可选：每份份量单位，g/克/份/碗
#   --calories                可选：每份热量（kcal）
#   --protein                 可选：每份蛋白质（g）
#   --fat                     可选：每份脂肪（g）
#   --carbs                   可选：每份碳水化合物（g）
#   --fiber                   可选：每份膳食纤维（g）
#   --sodium                  可选：每份钠（mg）

# 示例（完整）：
python scripts/nutrition_manager.py add "8f3b435b-..." \
  --serving_size 200 \
  --serving_unit g \
  --calories 320 \
  --protein 28 \
  --fat 18 \
  --carbs 20 \
  --fiber 2 \
  --sodium 800

# 示例（简单）：
python scripts/nutrition_manager.py add "8f3b435b-..." --calories 320 --protein 28

# 查看营养信息
python scripts/nutrition_manager.py get <recipe_id>

# 列出有营养信息的食谱
python scripts/nutrition_manager.py list [--sort calories|protein|fat]

# 搜索高蛋白食谱
python scripts/nutrition_manager.py search-high-protein [--threshold 20]

# 更新营养信息
python scripts/nutrition_manager.py update <recipe_id> \
  --calories 300 \
  --protein 30 \
  --fiber 3
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
火候 / 刀工 / 调味 / 采购 / 设备 / 保存 / 文化

### 关系类型
派生 / 变体 / 改良

### 状态
未做 / 已做 / 熟练 / 已废弃

---

## AI推荐工作流

### 完整录入一道菜（按顺序执行）

```bash
# 1. 创建食谱主记录
python scripts/recipe_manager.py add "宫保虾球" \
  --description "川菜经典，虾球Q弹" \
  --difficulty 中等 \
  --total_time 25 \
  --servings 2 \
  --status 未做

# 2. 添加分类（菜系/季节/烹饪方式/口味/用餐类型）
python scripts/category_manager.py add "<上一步返回的ID>" --cuisine 川菜 --region 中国-四川 --country 中国
python scripts/season_manager.py add "<ID>" --season 春,夏,秋
python scripts/cooking_method_manager.py add "<ID>" --method 炒
python scripts/flavor_manager.py add "<ID>" --flavor 辣,酸甜
python scripts/diet_tag_manager.py add "<ID>" --tag 荤菜
python scripts/meal_type_manager.py add "<ID>" --meal_type 午,晚

# 3. 添加食材（每种食材一条命令）
python scripts/ingredient_manager.py add "<ID>" --name 虾 --quantity 300 --unit g --category 海鲜 --sequence 1
python scripts/ingredient_manager.py add "<ID>" --name 花生 --quantity 50 --unit g --category 其他 --sequence 2
# ... 继续其他食材

# 4. 添加步骤
python scripts/step_manager.py add "<ID>" --action "虾去壳开背，用料酒腌制10分钟" --sequence 1 --duration 10 --heat_level 小火
python scripts/step_manager.py add "<ID>" --action "大火热油，虾炸至变色捞出" --sequence 2 --duration 3 --heat_level 大火
# ... 继续其他步骤

# 5. 关联步骤×食材（每步每种食材各一条命令）
python scripts/step_ingredient_manager.py add --step_id "<步骤1ID>" --ingredient_id "<虾ID>" --quantity_used 300 --introduced_at "开局加入"
python scripts/step_ingredient_manager.py add --step_id "<步骤2ID>" --ingredient_id "<虾ID>" --quantity_used 300 --introduced_at "第2步加入"
# ... 继续其他关联

# 6. 添加技法（每步骤可添加）
python scripts/technique_manager.py add --recipe_id "<ID>" --step_id "<步骤1ID>" --technique_name 腌制 --description "用料酒去腥" --key_points "时间要够/料酒要适量"

# 7. 添加小贴士
python scripts/tip_manager.py add "<ID>" --step_id "<步骤1ID>" --content "开背时去虾线更入味" --category 刀工 --priority 1
python scripts/tip_manager.py add "<ID>" --content "选择新鲜活虾口感更好" --category 采购 --priority 2

# 8. 添加背景知识
python scripts/background_manager.py add "<ID>" \
  --origin_story "宫保虾球源自川菜宫保鸡丁的变体" \
  --historical_background "清代丁宝桢发明" \
  --cultural_significance "代表川菜小荔枝口经典味型"

# 9. 添加炊具
python scripts/cookware_manager.py add "<ID>" --name 炒锅 --category 锅

# 10. 添加营养信息
python scripts/nutrition_manager.py add "<ID>" \
  --serving_size 200 \
  --serving_unit g \
  --calories 320 \
  --protein 28 \
  --fat 18 \
  --carbs 20 \
  --fiber 2 \
  --sodium 800

# 11. 记录烹饪历史（可选）
python scripts/history_manager.py add "<ID>" --cook_date 2026-05-15 --rating 4.5 --feedback "第一次做，成功！"
```

---

## 缺失字段推测规则

AI在调用CLI时，对于用户未提供的字段，按以下规则推测：

| 表/字段 | 推测规则 |
|---------|---------|
| recipes.description | 如用户说"经典川菜"，则用菜名+类型描述 |
| recipes.photo_url | 留空，询问用户是否有照片 |
| recipes.source_url | 留空，询问用户是否有链接 |
| ingredients.quantity_text | 用户说"适量"、"少许"时填充，否则留空 |
| ingredients.is_optional | 用户明确说"可选"时设置为1 |
| ingredients.substitute | 用户提到"可用XX代替"时填充 |
| cooking_steps.temperature | 根据heat_level推测：中火≈160-180度，大火≈180-200度 |
| cooking_steps.expected_result | 根据步骤动作推测合理效果 |
| step_ingredients.quantity_used | 继承ingredients.quantity |
| step_ingredients.introduced_at | 根据步骤序号推测：开局/第X步加入 |

**无法推测时，必须询问用户。**