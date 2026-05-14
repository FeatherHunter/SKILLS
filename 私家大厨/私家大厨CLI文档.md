# 私家大厨 CLI 脚本文档

## 一、CLI 脚本总览

每个脚本对应一张表，提供该表的增删改查等操作。

---

### 1. `recipe_manager.py` → `recipes` 表

| 函数名 | 作用 |
|--------|------|
| `recipe_add(...)` | 添加食谱（36字段全量INSERT） |
| `recipe_show(name_or_id)` | 按名称或ID完整查看一条食谱 |
| `recipe_list(difficulty, status, limit)` | 列出食谱列表（支持难度/状态筛选） |
| `recipe_update(recipe_id, ...)` | 更新食谱（36字段显式参数，只写想改的字段） |
| `recipe_delete(recipe_id)` | 删除一条食谱 |
| `recipe_lint(recipe_id)` | 检查食谱完整性（是否缺少关键关联数据） |
| `main()` | CLI入口（add/show/list/update/delete/lint子命令） |

---

### 2. `location_manager.py` → `recipe_locations` 表

| 函数名 | 作用 |
|--------|------|
| `location_add(recipe_id, ...)` | 添加地区分类（16字段） |
| `location_list(recipe_id)` | 查看某食谱的地区分类 |
| `location_get(location_id)` | 按ID查一条记录 |
| `location_update(location_id, ...)` | 更新地区分类（16字段显式） |
| `location_delete(location_id)` | 删除 |
| `query_by_cuisine(cuisine, limit)` | 按菜系查询食谱 |
| `query_by_season(season, limit)` | 按季节查询 |
| `query_by_occasion(occasion, limit)` | 按场合查询 |
| `query_by_flavor(flavor, limit)` | 按口味查询 |
| `main()` | CLI入口 |

---

### 3. `ingredient_manager.py` → `ingredients` 表

| 函数名 | 作用 |
|--------|------|
| `ingredient_add(recipe_id, name, ...)` | 添加食材（28字段全量） |
| `ingredient_update(ingredient_id, ...)` | 更新食材（28字段显式） |
| `ingredient_list(recipe_id, limit)` | 列出某食谱的所有食材 |
| `ingredient_get(ingredient_id)` | 按ID查一条食材 |
| `ingredient_delete(ingredient_id)` | 删除一条食材 |
| `main()` | CLI入口 |

---

### 4. `step_manager.py` → `cooking_steps` 表

| 函数名 | 作用 |
|--------|------|
| `step_add(recipe_id, sequence, action, ...)` | 添加烹饪步骤（37字段全量） |
| `step_update(step_id, ...)` | 更新步骤（37字段显式） |
| `step_list(recipe_id, limit)` | 列出某食谱的所有步骤 |
| `step_get(step_id)` | 按ID查一条步骤 |
| `step_delete(step_id)` | 删除步骤 |
| `step_search(keyword, limit)` | 搜索含有关键字的步骤（查action/purpose） |
| `main()` | CLI入口 |

---

### 5. `technique_manager.py` → `step_techniques` 表

| 函数名 | 作用 |
|--------|------|
| `technique_add(step_id, recipe_id, technique_code, ...)` | 添加技法（21字段全量） |
| `technique_update(technique_id, ...)` | 更新技法（21字段显式） |
| `technique_list(recipe_id=None, step_id=None, limit=50)` | 列出技法（可按食谱或步骤筛选） |
| `technique_get(technique_id)` | 按ID查一条技法 |
| `technique_delete(technique_id)` | 删除技法 |
| `query_by_code(code, limit)` | 按技法代码查询（如"爆炒""滑炒"） |
| `main()` | CLI入口 |

---

### 6. `prep_manager.py` → `ingredient_preparations` 表

| 函数名 | 作用 |
|--------|------|
| `prep_add(recipe_id, ingredient_id, step_sequence, ...)` | 添加食材预处理方式（22字段全量） |
| `prep_update(prep_id, ...)` | 更新预处理（22字段显式） |
| `prep_list(recipe_id, limit)` | 列出某食谱的所有预处理记录 |
| `prep_get(prep_id)` | 按ID查一条 |
| `prep_delete(prep_id)` | 删除 |
| `main()` | CLI入口 |

---

### 7. `tip_manager.py` → `tips` 表

| 函数名 | 作用 |
|--------|------|
| `tip_add(recipe_id, category, content, ...)` | 添加小贴士（23字段全量） |
| `tip_update(tip_id, ...)` | 更新小贴士（23字段显式） |
| `tip_list(recipe_id, limit)` | 列出某食谱的所有贴士 |
| `tip_get(tip_id)` | 按ID查一条 |
| `tip_delete(tip_id)` | 删除贴士 |
| `tip_list_all(limit)` | 列出全部贴士（不按食谱） |
| `main()` | CLI入口 |

---

### 8. `background_manager.py` → `background_knowledge` 表

| 函数名 | 作用 |
|--------|------|
| `background_add(recipe_id, ...)` | 添加背景知识（24字段全量） |
| `background_update(bg_id, ...)` | 更新背景知识（24字段显式） |
| `background_get(recipe_id)` | 按recipe_id查背景知识 |
| `background_delete(bg_id)` | 删除 |
| `background_list(recipe_id, limit)` | 列出某食谱的背景知识 |
| `main()` | CLI入口 |

---

### 9. `nutrition_manager.py` → `nutrition_info` 表

| 函数名 | 作用 |
|--------|------|
| `nutrition_add(recipe_id, ...)` | 添加营养信息（34字段全量） |
| `nutrition_update(recipe_id, ...)` | 更新营养信息（34字段显式，用recipe_id而非营养记录ID） |
| `nutrition_get(recipe_id)` | 按recipe_id查营养信息 |
| `nutrition_delete(recipe_id)` | 删除营养信息 |
| `main()` | CLI入口 |

---

### 10. `history_manager.py` → `recipe_history` 表

| 函数名 | 作用 |
|--------|------|
| `history_add(recipe_id, cook_date, ...)` | 添加一次烹饪记录（25字段全量） |
| `history_update(history_id, ...)` | 更新烹饪记录（25字段显式） |
| `history_list(recipe_id, limit)` | 列出某食谱的历史记录（按cook_date倒序） |
| `history_get(history_id)` | 按ID查一条记录 |
| `history_delete(history_id)` | 删除记录 |
| `history_stats(recipe_id)` | 统计某食谱的烹饪次数、平均评分等 |
| `main()` | CLI入口 |

---

### 11. `beverage_manager.py` → `beverage_pairings` 表

---

## 二、数据库表结构

---

### `recipes` — 食谱主表（36字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识（UUID） |
| `internal_code` | TEXT | 内部编码（如"R001"） |
| `name` | TEXT | 食谱名称（必须） |
| `name_aliases` | TEXT | 名称别名/曾用名，JSON数组格式 |
| `description` | TEXT | 综合描述（味道/口感/特色） |
| `appearance_desc` | TEXT | 外观描述（颜色/形状/光泽） |
| `taste_desc` | TEXT | 口味描述（咸/甜/辣/鲜等） |
| `texture_desc` | TEXT | 口感描述（软/硬/弹/滑等） |
| `time_total_minutes` | INTEGER | 总耗时（分钟） |
| `time_prep_minutes` | INTEGER | 备菜耗时 |
| `time_cook_minutes` | INTEGER | 烹饪耗时 |
| `time_cleanup_minutes` | INTEGER | 收拾清洁耗时 |
| `difficulty` | TEXT | 难度等级（简单/中等/困难/大师） |
| `difficulty_user` | TEXT | 用户自评难度 |
| `servings` | INTEGER | 份量（几人份） |
| `recipe_version` | TEXT | 版本号 |
| `parent_recipe_id` | TEXT | 父食谱ID（派生时填） |
| `is_reference` | INTEGER | 是否为参考食谱（1/0） |
| `status` | TEXT | 状态（草稿/验证/公开/废弃） |
| `times_cooked` | INTEGER | 烹饪次数 |
| `user_rating` | REAL | 用户评分（1-5分） |
| `user_feedback` | TEXT | 用户反馈 |
| `want_to_cook_level` | INTEGER | 想做程度（1-5） |
| `is_favorite` | INTEGER | 是否收藏（1/0） |
| `is_staple` | INTEGER | 是否常备菜（1/0） |
| `cost_per_serving` | REAL | 每份成本（元） |
| `created_at` | TEXT | 创建时间（ISO格式） |
| `updated_at` | TEXT | 更新时间 |
| `source_url` | TEXT | 配方来源URL |
| `source_author` | TEXT | 配方作者/来源 |
| `video_url` | TEXT | 视频教程URL |
| `photo_urls` | TEXT | 照片URL列表，JSON数组 |
| `keywords` | TEXT | 关键词，JSON数组 |
| `notes` | TEXT | 备注说明 |
| `energy_level` | TEXT | 做这道菜需要的精力（高/中/低） |

> 注：`mood_when_cooking` 在 `recipe_history` 表，不在 `recipes` 表。

---

### `recipe_locations` — 地区分类表（16字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识 |
| `recipe_id` | TEXT | 关联食谱ID |
| `country` | TEXT | 国家 |
| `province` | TEXT | 省/州 |
| `city` | TEXT | 城市 |
| `cuisine_type` | TEXT | 菜系（如川菜/粤菜/鲁菜） |
| `cuisine_type_secondary` | TEXT | 二级菜系 |
| `dish_type` | TEXT | 菜品类型（热菜/凉菜/汤/主食等） |
| `meal_type` | TEXT | 餐次类型，JSON数组（早餐/午餐/晚餐/夜宵） |
| `cooking_method` | TEXT | 烹调方式（炒/煮/蒸/炸/烤等） |
| `flavor_profile` | TEXT | 风味特征，JSON数组（酸/甜/苦/辣/咸/鲜） |
| `flavor_intensity` | TEXT | 口味浓淡（清淡/适中/浓郁） |
| `diet_tags` | TEXT | 饮食标签，JSON数组（素食/低糖/无麸质等） |
| `seasons` | TEXT | 适合季节，JSON数组 |
| `occasions` | TEXT | 适合场合，JSON数组 |
| `target_demographic` | TEXT | 目标人群（老人/儿童/孕妇等） |

---

### `ingredients` — 食材表（28字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识 |
| `recipe_id` | TEXT | 关联食谱ID |
| `sequence` | INTEGER | 在食谱中的顺序号 |
| `name` | TEXT | 食材名称（必须） |
| `category` | TEXT | 分类（肉类/蔬菜/豆制品/调料等） |
| `quantity` | REAL | 数量（数值） |
| `quantity_text` | TEXT | 数量描述（"适量""少许"） |
| `unit` | TEXT | 单位（克/毫升/个/把） |
| `state` | TEXT | 食材状态/形态，JSON数组（块/片/丝/末） |
| `size` | TEXT | 尺寸大小（大/中/小/末） |
| `cut_style` | TEXT | 切法/刀工，JSON数组（切丁/切片/切丝） |
| `quality_grade` | TEXT | 品质等级（特级/一级/二级） |
| `brand` | TEXT | 品牌 |
| `purchase_place` | TEXT | 购买地点 |
| `supermarkets` | TEXT | 超市来源，JSON数组 |
| `price_per_unit` | REAL | 单价（元） |
| `purchase_specs` | TEXT | 采购规格 |
| `storage_type` | TEXT | 储存方式（冷藏/冷冻/常温/通风） |
| `frozen_ok` | INTEGER | 是否可冷冻（1/0） |
| `shelf_life_days` | INTEGER | 保质期（天） |
| `prepped_storage` | TEXT | 处理后如何存放 |
| `is_optional` | INTEGER | 是否可选食材（1/0） |
| `is_staple` | INTEGER | 是否常备食材（1/0） |
| `substitute` | TEXT | 替代食材 |
| `substitute_notes` | TEXT | 替代说明 |
| `introduced_at_step` | INTEGER | 在哪一步引入 |
| `introduced_method` | TEXT | 引入方式（直接加入/先炒香等） |
| `notes` | TEXT | 备注 |

---

### `ingredient_preparations` — 食材预处理表（22字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识 |
| `recipe_id` | TEXT | 关联食谱ID |
| `ingredient_id` | TEXT | 关联食材ID |
| `step_sequence` | INTEGER | 在哪一步处理 |
| `prep_name` | TEXT | 预处理名称（如"焯水""上浆"） |
| `prep_details` | TEXT | 预处理详细说明 |
| `tools_used` | TEXT | 使用的工具，JSON数组 |
| `duration_minutes` | INTEGER | 处理时长（分钟） |
| `temperature` | TEXT | 处理温度 |
| `temperature_end` | TEXT | 结束温度 |
| `liquid_used` | TEXT | 使用的液体（水/油/盐水），JSON数组 |
| `liquid_ratio` | TEXT | 液体比例（如"1:3"） |
| `seasoning_added` | TEXT | 添加的调味品，JSON数组 |
| `coating_used` | TEXT | 使用的挂糊/上浆材料，JSON数组 |
| `coating_ratio` | TEXT | 挂糊比例 |
| `texture_after` | TEXT | 处理后质感（嫩/脆/弹） |
| `color_change` | TEXT | 颜色变化 |
| `smell_change` | TEXT | 气味变化 |
| `storage_method` | TEXT | 处理后储存方式 |
| `storage_duration` | TEXT | 储存时长 |
| `is_prerequisite` | INTEGER | 是否为后续步骤的前提（1/0） |
| `prerequisite_notes` | TEXT | 前提条件说明 |

---

### `cooking_steps` — 烹饪步骤表（37字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识 |
| `recipe_id` | TEXT | 关联食谱ID |
| `sequence` | INTEGER | 步骤序号（1,2,3…） |
| `phase` | TEXT | 阶段（备菜/主烹/调味/装盘） |
| `action` | TEXT | 具体动作（切块/热油/大火翻炒） |
| `purpose` | TEXT | 这个动作的目的 |
| `sub_purpose` | TEXT | 子目的/原理，JSON数组 |
| `tools` | TEXT | 使用的工具，JSON数组 |
| `duration_minutes` | REAL | 预计时长（分钟） |
| `temperature_value` | REAL | 目标温度（数值） |
| `temperature_end_value` | REAL | 结束温度 |
| `temperature_unit` | TEXT | 温度单位（℃/℉），JSON数组 |
| `heat_level` | TEXT | 火候，JSON数组（大火/中火/小火） |
| `heat_adjustment` | TEXT | 火候调整方式 |
| `urgency_level` | TEXT | 紧迫程度（立即/30秒内/1分钟内） |
| `expected_result` | TEXT | 预期达到的状态 |
| `visual_signal` | TEXT | 视觉信号（颜色变化/冒烟），JSON数组 |
| `audio_signal` | TEXT | 听觉信号（响声变化），JSON数组 |
| `smell_signal` | TEXT | 嗅觉信号（香味），JSON数组 |
| `texture_signal` | TEXT | 触觉/口感信号，JSON数组 |
| `doneness_indicator` | TEXT | 成熟度判断标准，JSON数组 |
| `color_during` | TEXT | 过程中颜色，JSON数组 |
| `color_after` | TEXT | 完成后颜色 |
| `texture_during` | TEXT | 过程中口感，JSON数组 |
| `texture_after` | TEXT | 完成后口感 |
| `can_parallel` | INTEGER | 能否与其他步骤并行（1/0） |
| `parallel_with` | INTEGER | 可并行的步骤序号 |
| `parallel_notes` | TEXT | 并行注意事项，JSON数组 |
| `common_mistakes` | TEXT | 常见错误，JSON数组 |
| `mistake_causes` | TEXT | 错误原因，JSON数组 |
| `mistake_fixes` | TEXT | 补救方法，JSON数组 |
| `is_critical` | INTEGER | 是否关键步骤（1/0） |
| `is_safety_critical` | INTEGER | 是否安全关键（1/0） |
| `warnings` | TEXT | 警告事项，JSON数组 |
| `retry_strategy` | TEXT | 重试策略 |
| `can_skip` | INTEGER | 能否跳过（1/0） |
| `skip_effects` | TEXT | 跳过的后果 |

---

### `step_techniques` — 步骤技法表（21字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识 |
| `step_id` | TEXT | 关联步骤ID |
| `recipe_id` | TEXT | 关联食谱ID |
| `technique_code` | TEXT | 技法代码（如"爆炒""滑炒""颠勺"） |
| `technique_name` | TEXT | 技法名称 |
| `description` | TEXT | 技法描述 |
| `key_points` | TEXT | 关键要点，JSON数组 |
| `wrist_action` | TEXT | 腕部动作说明，JSON数组 |
| `arm_action` | TEXT | 手臂动作说明，JSON数组 |
| `fire_control` | TEXT | 火候控制要点 |
| `timing` | TEXT | 时机把握 |
| `speed` | TEXT | 速度/节奏要求 |
| `difficulty_to_learn` | TEXT | 学习难度 |
| `learn_stage` | TEXT | 适合的学习阶段 |
| `common_errors` | TEXT | 常见错误，JSON数组 |
| `error_signs` | TEXT | 错误表现，JSON数组 |
| `fix_methods` | TEXT | 纠正方法，JSON数组 |
| `prerequisite_skills` | TEXT | 前置技能要求，JSON数组 |
| `related_techniques` | TEXT | 相关技法，JSON数组 |
| `youtube_links` | TEXT | 教学视频链接，JSON数组 |
| `practice_exercises` | TEXT | 练习方法，JSON数组 |

---

### `tips` — 小贴士表（23字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识 |
| `recipe_id` | TEXT | 关联食谱ID（可为null） |
| `category` | TEXT | 分类（采购技巧/刀工技巧/火候控制/调味技巧/装盘技巧/设备巧用/食材保存/时间管理/健康贴士） |
| `content` | TEXT | 贴士内容（必须） |
| `apply_to_step` | INTEGER | 适用的步骤序号 |
| `apply_to_ingredient` | INTEGER | 适用的食材序号 |
| `cost_level` | TEXT | 成本等级（经济/普通/昂贵） |
| `time_cost` | TEXT | 时间成本 |
| `equipment_needed` | TEXT | 所需设备 |
| `difficulty` | TEXT | 难度（易/中/难） |
| `effectiveness_proven` | INTEGER | 有效性已验证（1/0） |
| `difficulty_proven` | TEXT | 难度验证结果 |
| `effectiveness_rating` | INTEGER | 效果评分（1-5） |
| `source` | TEXT | 来源（原创/网络/书籍） |
| `author` | TEXT | 作者 |
| `author_url` | TEXT | 作者链接 |
| `is_verified` | INTEGER | 是否官方验证（1/0） |
| `verified_by_user` | INTEGER | 用户已验证（1/0） |
| `verified_date` | TEXT | 验证日期 |
| `user_modified_content` | TEXT | 用户修改后的内容 |
| `user_verified_result` | TEXT | 用户验证结果 |
| `is_public` | INTEGER | 是否公开（1/0） |
| `likes_count` | INTEGER | 点赞数 |

---

### `background_knowledge` — 背景知识表（24字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识 |
| `recipe_id` | TEXT | 关联食谱ID |
| `origin_story` | TEXT | 起源故事 |
| `historical_background` | TEXT | 历史背景 |
| `era` | TEXT | 所处时代/年代 |
| `cultural_significance` | TEXT | 文化意义 |
| `story_variants` | TEXT | 故事变体，JSON数组 |
| `famous_restaurants` | TEXT | 著名餐馆，JSON数组 |
| `famous_chefs` | TEXT | 名厨，JSON数组 |
| `related_dishes` | TEXT | 相关菜品，JSON数组 |
| `regional_variants` | TEXT | 地域变体，JSON数组 |
| `nutrition_benefits` | TEXT | 营养价值，JSON数组 |
| `nutrition_highlights` | TEXT | 营养亮点，JSON数组 |
| `nutrition_concerns` | TEXT | 营养注意点，JSON数组 |
| `taboos` | TEXT | 饮食禁忌，JSON数组 |
| `wine_pairing` | TEXT | 葡萄酒搭配 |
| `wine_pairing_details` | TEXT | 葡萄酒搭配详情 |
| `beverage_pairing` | TEXT | 饮品搭配 |
| `staplefood_pairing` | TEXT | 主食搭配 |
| `side_dish_pairing` | TEXT | 配菜搭配 |
| `weather_suitability` | TEXT | 天气适宜性，JSON数组 |
| `external_links` | TEXT | 外部链接，JSON数组 |
| `media_references` | TEXT | 媒体报道，JSON数组 |
| `cultural_notes` | TEXT | 文化备注 |

---

### `nutrition_info` — 营养信息表（34字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识 |
| `recipe_id` | TEXT | 关联食谱ID |
| `serving_size` | REAL | 每份大小（数值） |
| `serving_unit` | TEXT | 每份单位（克/毫升/个） |
| `servings_total` | INTEGER | 总份数 |
| `calories_kcal` | INTEGER | 总热量（千卡） |
| `calories_per_serving` | INTEGER | 每份热量 |
| `protein_grams` | REAL | 蛋白质（克） |
| `fat_grams` | REAL | 脂肪（克） |
| `saturated_fat_g` | REAL | 饱和脂肪（克） |
| `trans_fat_g` | REAL | 反式脂肪（克） |
| `carbohydrates_grams` | REAL | 碳水化合物（克） |
| `fiber_grams` | REAL | 膳食纤维（克） |
| `sugar_grams` | REAL | 总糖（克） |
| `added_sugar_g` | REAL | 添加糖（克） |
| `sodium_mg` | REAL | 钠（毫克） |
| `cholesterol_mg` | REAL | 胆固醇（毫克） |
| `vitamin_a_mcg` | REAL | 维生素A（微克） |
| `vitamin_b1_mg` | REAL | 维生素B1/硫胺素（毫克） |
| `vitamin_b2_mg` | REAL | 维生素B2/核黄素（毫克） |
| `vitamin_b3_mg` | REAL | 维生素B3/烟酸（毫克） |
| `vitamin_c_mg` | REAL | 维生素C（毫克） |
| `vitamin_d_mcg` | REAL | 维生素D（微克） |
| `vitamin_e_mg` | REAL | 维生素E（毫克） |
| `calcium_mg` | REAL | 钙（毫克） |
| `iron_mg` | REAL | 铁（毫克） |
| `zinc_mg` | REAL | 锌（毫克） |
| `magnesium_mg` | REAL | 镁（毫克） |
| `potassium_mg` | REAL | 钾（毫克） |
| `selenium_mcg` | REAL | 硒（微克） |
| `calculation_method` | TEXT | 计算方法（计算/估算/实测） |
| `data_source` | TEXT | 数据来源 |
| `is_estimated` | INTEGER | 是否为估算值（1/0） |
| `confidence_level` | TEXT | 可信度等级（高/中/低） |

---

### `recipe_history` — 烹饪历史表（26字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识 |
| `recipe_id` | TEXT | 关联食谱ID |
| `cook_date` | TEXT | 烹饪日期 |
| `cook_sequence` | INTEGER | 第几次做这道菜 |
| `modifications` | TEXT | 本次改动，JSON数组 |
| `rating_this_time` | INTEGER | 本次评分（1-5） |
| `feedback` | TEXT | 本次反馈 |
| `improvements` | TEXT | 改进计划，JSON数组 |
| `photos` | TEXT | 本次照片，JSON数组 |
| `time_actual_minutes` | INTEGER | 实际耗时（分钟） |
| `time_vs_planned` | TEXT | 实际vs计划耗时对比 |
| `companions` | TEXT | 同行人，JSON数组 |
| `occasion` | TEXT | 场合 |
| `liked_by` | TEXT | 喜欢的人，JSON数组 |
| `would_recommend` | INTEGER | 是否会推荐（1/0） |
| `mood_when_cooking` | TEXT | 做菜时心情 |
| `energy_level` | TEXT | 精力状态（高/中/低） |
| `updated_at` | TEXT | 更新时间 |

---

### `beverage_pairings` — 饮品搭配表（14字段）

| 字段 | 类型 | 含义 |
|------|------|------|
| `id` | TEXT | 唯一标识 |
| `recipe_id` | TEXT | 关联食谱ID |
| `pairing_type` | TEXT | 搭配类型（配酒/配茶/配饮料） |
| `beverage_name` | TEXT | 饮品名称 |
| `beverage_category` | TEXT | 饮品分类（白酒/红酒/啤酒/绿茶/红茶等） |
| `pairing_reason` | TEXT | 搭配理由 |
| `flavor_match` | TEXT | 风味匹配说明，JSON数组 |
| `temperature` | TEXT | 饮用温度 |
| `brand_recommendation` | TEXT | 品牌推荐 |
| `price_range` | TEXT | 价格区间 |
| `substitute_options` | TEXT | 替代选项，JSON数组 |
| `occasion_suitability` | TEXT | 场合适宜性，JSON数组 |
| `region_tradition` | TEXT | 地域传统，JSON数组 |
| `notes` | TEXT | 备注 |

---

## 三、表之间关联关系

```
recipes（主表，id）
├── recipe_locations（通过 recipe_id）
├── ingredients（通过 recipe_id）
├── cooking_steps（通过 recipe_id）
│   └── step_techniques（通过 step_id）
├── ingredient_preparations（通过 recipe_id + ingredient_id）
├── tips（通过 recipe_id）
├── background_knowledge（通过 recipe_id）
├── nutrition_info（通过 recipe_id）
├── recipe_history（通过 recipe_id）
└── beverage_pairings（通过 recipe_id）
```

---

*文档生成时间：2026-05-13*