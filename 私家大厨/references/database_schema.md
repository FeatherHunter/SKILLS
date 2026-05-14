# 私家大厨 - 数据库结构 v1.0

## 表总览（13张，其中11张有专属manager脚本，2张独立）

| 序号 | 表名 | 说明 | manager脚本 |
|------|------|------|-------------|
| 1 | recipes | 食谱主表 | recipe_manager.py |
| 2 | recipe_locations | 地区与分类 | location_manager.py |
| 3 | ingredients | 食材清单 | ingredient_manager.py |
| 4 | ingredient_preparations | 食材处理 | prep_manager.py |
| 5 | cooking_steps | 烹饪步骤 | step_manager.py |
| 6 | step_techniques | 技法详解 | technique_manager.py |
| 7 | tips | 小贴士 | tip_manager.py |
| 8 | background_knowledge | 背景知识 | background_manager.py |
| 9 | nutrition_info | 热量营养 | nutrition_manager.py |
| 10 | recipe_history | 烹饪历史 | history_manager.py |
| 11 | beverage_pairings | 饮品搭配 | beverage_manager.py |
| 12 | cookware | 炊具设备 | （无专属manager） |
| 13 | recipe_collections | 食谱集合 | （无专属manager） |

---

## 表1：recipes — 食谱主表

```sql
CREATE TABLE recipes (
    id TEXT PRIMARY KEY,              -- UUID
    internal_code TEXT,               -- 内部编号（如川-001）
    name TEXT NOT NULL,               -- 菜名
    name_aliases TEXT,                 -- 别名JSON数组
    description TEXT,                 -- 一句话描述
    appearance_desc TEXT,             -- 成品外观描述
    taste_desc TEXT,                  -- 口味描述
    texture_desc TEXT,                -- 口感描述
    time_total_minutes INTEGER,       -- 总时间（分钟）
    time_prep_minutes INTEGER,        -- 准备时间
    time_cook_minutes INTEGER,        -- 烹饪时间
    time_cleanup_minutes INTEGER,     -- 收拾时间
    difficulty TEXT,                  -- 难度：简单/中等/困难/大师
    difficulty_user TEXT,             -- 用户感受难度
    servings INTEGER,                  -- 份量（人数）
    recipe_version TEXT,              -- 版本号
    parent_recipe_id TEXT,            -- 派生自我的哪个食谱
    is_reference INTEGER DEFAULT 0,   -- 是否为参考食谱（待验证）
    status TEXT DEFAULT '未做',       -- 状态：未做/已做/熟练/常做
    times_cooked INTEGER DEFAULT 0,   -- 做过次数
    user_rating REAL,                 -- 用户评分（1-5）
    user_feedback TEXT,              -- 用户反馈
    want_to_cook_level INTEGER,      -- 想做的愿望程度（1-5）
    is_favorite INTEGER DEFAULT 0,    -- 是否收藏
    is_staple INTEGER DEFAULT 0,      -- 是否常备菜
    cost_per_serving REAL,           -- 每份预估成本
    created_at TEXT,                  -- 创建时间
    updated_at TEXT,                  -- 更新时间
    source_url TEXT,                  -- 来源链接
    source_author TEXT,               -- 来源作者/博主
    video_url TEXT,                   -- 视频教程链接
    photo_urls TEXT,                 -- 成品照片路径JSON数组
    keywords TEXT,                    -- 关键词JSON数组
    notes TEXT,                       -- 备注
    mood_when_cooking TEXT,           -- 做饭时的心情
    energy_level TEXT                 -- 体力精力状态
);
CREATE INDEX idx_recipes_name ON recipes(name);
CREATE INDEX idx_recipes_difficulty ON recipes(difficulty);
CREATE INDEX idx_recipes_status ON recipes(status);
```

---

## 表2：recipe_locations — 地区与分类

```sql
CREATE TABLE recipe_locations (
    id TEXT PRIMARY KEY,               -- UUID
    recipe_id TEXT NOT NULL,          -- 外键→recipes
    country TEXT,                      -- 国家
    province TEXT,                    -- 省份/直辖市
    city TEXT,                        -- 城市
    cuisine_type TEXT,                -- 菜系：川菜/粤菜/湘菜/本帮等
    cuisine_type_secondary TEXT,      -- 第二菜系
    dish_type TEXT,                   -- 菜品分类：热菜/凉菜/汤/主食/甜点/饮品/小吃/酱料
    meal_type TEXT,                   -- 用餐类型JSON数组
    cooking_method TEXT,              -- 烹饪方式：炒/蒸/煮/烤/炸/煎/焖/炖/烩/拌/卤/熏
    flavor_profile TEXT,              -- 口味标签JSON数组
    flavor_intensity TEXT,            -- 口味强度：清淡/适中/浓郁/重口
    diet_tags TEXT,                   -- 饮食标签JSON数组
    seasons TEXT,                    -- 适合季节JSON数组
    occasions TEXT,                  -- 场合JSON数组
    target_demographic TEXT,         -- 目标人群JSON数组
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_recipe_locations_recipe ON recipe_locations(recipe_id);
CREATE INDEX idx_recipe_locations_cuisine ON recipe_locations(cuisine_type);
```

---

## 表3：ingredients — 食材清单

```sql
CREATE TABLE ingredients (
    id TEXT PRIMARY KEY,              -- UUID
    recipe_id TEXT NOT NULL,          -- 外键→recipes
    sequence INTEGER,                 -- 序号（决定添加顺序）
    name TEXT NOT NULL,               -- 食材名称
    category TEXT,                    -- 食材大类：肉类/蔬菜/豆制品/调料/海鲜
    quantity REAL,                   -- 用量数值
    quantity_text TEXT,               -- 用量文字描述（如"适量"、"一小把"）
    unit TEXT,                        -- 单位：g/kg/ml/L/个/把/勺/茶匙/杯/大勺/小勺
    state TEXT,                       -- 食材状态：鲜/冻/干/罐头/腌制/熟
    size TEXT,                        -- 处理大小：小块/大片/丝/末/片/整/碎/泥
    cut_style TEXT,                   -- 刀工类型：切/剁/片/砍/刨/刮
    quality_grade TEXT,               -- 食材等级：特级/一级/二级/普通
    brand TEXT,                       -- 推荐品牌
    purchase_place TEXT,              -- 购买渠道
    supermarkets TEXT,                -- 哪些超市有卖JSON数组
    price_per_unit REAL,             -- 单价
    purchase_specs TEXT,             -- 采购规格（啥样的是好的）
    storage_type TEXT,               -- 储存方式：冷藏/冷冻/常温/通风/干燥
    frozen_ok INTEGER DEFAULT 0,     -- 能否冷冻
    shelf_life_days INTEGER,         -- 保鲜天数
    prepped_storage TEXT,            -- 处理后如何保存
    is_optional INTEGER DEFAULT 0,    -- 是否可选
    is_staple INTEGER DEFAULT 0,      -- 是否常备食材
    substitute TEXT,                 -- 替代食材
    substitute_notes TEXT,          -- 替代说明
    introduced_method TEXT,           -- 在哪一步引入（直接加入/出锅前/熄火后）
    notes TEXT,                       -- 备注
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_ingredients_recipe ON ingredients(recipe_id);
CREATE INDEX idx_ingredients_name ON ingredients(name);
```

---

## 表4：ingredient_preparations — 食材处理方式

```sql
CREATE TABLE ingredient_preparations (
    id TEXT PRIMARY KEY,              -- UUID
    recipe_id TEXT NOT NULL,          -- 外键→recipes
    ingredient_id TEXT,               -- 外键→ingredients
    step_sequence INTEGER,            -- 处理发生的步骤序号
    prep_name TEXT,                   -- 处理名称：腌/切/泡/焯/炸/炒/蒸/磨
    prep_details TEXT,                -- 具体处理描述
    tools_used TEXT,                  -- 使用的工具JSON数组
    duration_minutes INTEGER,         -- 处理时长
    temperature TEXT,                -- 温度要求
    temperature_end TEXT,            -- 温度区间（如100-120℃）
    liquid_used TEXT,                -- 用什么液体（水/盐水/料酒）
    liquid_ratio TEXT,               -- 液体比例
    seasoning_added TEXT,            -- 腌料JSON：[{name, quantity}]
    coating_used TEXT,               -- 挂糊/上浆用的材料
    coating_ratio TEXT,              -- 糊/浆比例
    texture_after TEXT,              -- 处理后质感：弹牙/软糯/脆爽/滑嫩/劲道
    color_change TEXT,               -- 颜色变化
    smell_change TEXT,               -- 气味变化
    storage_method TEXT,             -- 临时存放方式
    storage_duration TEXT,           -- 可存放时间
    is_prerequisite INTEGER DEFAULT 0, -- 是否为后续步骤的前提准备
    prerequisite_notes TEXT,         -- 前提准备说明
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE SET NULL
);
CREATE INDEX idx_ingredient_preps_recipe ON ingredient_preparations(recipe_id);
```

---

## 表5：cooking_steps — 烹饪步骤（核心表）

```sql
CREATE TABLE cooking_steps (
    id TEXT PRIMARY KEY,              -- UUID
    recipe_id TEXT NOT NULL,          -- 外键→recipes
    sequence INTEGER NOT NULL,        -- 步骤序号
    phase TEXT,                       -- 烹饪阶段：备菜/炒制/调味/焖煮/收汁/出锅
    action TEXT NOT NULL,             -- 具体动作描述
    purpose TEXT,                     -- 这么做的目的/原因
    sub_purpose TEXT,                 -- 深层目的（了解原理）
    tools TEXT,                       -- 使用的工具JSON数组
    duration_minutes REAL,           -- 该步骤时长
    temperature_value REAL,          -- 温度数值
    temperature_end_value REAL,      -- 温度上限
    temperature_unit TEXT,           -- 温度单位：℃/℉
    heat_level TEXT,                 -- 火候：微火/小火/中火/大火/猛火
    heat_adjustment TEXT,             -- 火候调节时机
    urgency_level TEXT,               -- 紧迫程度：宽松/一般/快速/争分夺秒
    expected_result TEXT,            -- 预期效果描述
    visual_signal TEXT,              -- 视觉信号（变红/冒泡/焦化/变亮）
    audio_signal TEXT,               -- 声音信号（油爆声/水沸声/滋滋声）
    smell_signal TEXT,               -- 气味信号（蒜香/酒香/焦香）
    texture_signal TEXT,             -- 质感信号（弹牙/软糯/脆爽）
    doneness_indicator TEXT,        -- 成熟度判断标准
    color_during TEXT,               -- 过程中的颜色
    color_after TEXT,                -- 完成时的颜色
    texture_during TEXT,            -- 过程中的质感
    texture_after TEXT,              -- 完成时的质感
    can_parallel INTEGER DEFAULT 0,  -- 能否与其他步骤同时进行
    parallel_with INTEGER,           -- 并行哪个步骤
    parallel_notes TEXT,            -- 并行说明
    common_mistakes TEXT,           -- 常见错误
    mistake_causes TEXT,             -- 错误原因分析
    mistake_fixes TEXT,             -- 错误修正方法
    is_critical INTEGER DEFAULT 0,   -- 是否关键步骤（失误会影响成品）
    is_safety_critical INTEGER DEFAULT 0, -- 是否涉及安全（油炸/高温）
    warnings TEXT,                   -- 注意事项/危险提示
    retry_strategy TEXT,            -- 如果失败了怎么补救
    can_skip INTEGER DEFAULT 0,     -- 能否跳过此步
    skip_effects TEXT,              -- 跳过的影响
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_cooking_steps_recipe ON cooking_steps(recipe_id);
CREATE INDEX idx_cooking_steps_sequence ON cooking_steps(recipe_id, sequence);
```

---

## 表6：step_techniques — 步骤技法详解

```sql
CREATE TABLE step_techniques (
    id TEXT PRIMARY KEY,              -- UUID
    step_id TEXT,                     -- 外键→cooking_steps
    recipe_id TEXT,                   -- 外键→recipes（用于不依附步骤的技法）
    technique_code TEXT,              -- 技法代码：爆炒/滑炒/抓炒/颠勺/爆香/煸炒
    technique_name TEXT NOT NULL,     -- 技法名称
    description TEXT,                -- 技法解释
    key_points TEXT,                  -- 关键要点JSON数组
    wrist_action TEXT,               -- 腕部动作描述
    arm_action TEXT,                 -- 手臂动作描述
    fire_control TEXT,               -- 火候配合
    timing TEXT,                      -- 时机把握
    speed TEXT,                       -- 操作速度：慢/中/快/急速
    difficulty_to_learn TEXT,        -- 学习难度：入门/进阶/精通/大师
    learn_stage TEXT,                 -- 学习阶段：第一阶段/第二阶段/第三阶段
    common_errors TEXT,              -- 常见错误JSON数组
    error_signs TEXT,                -- 错误迹象JSON数组
    fix_methods TEXT,                -- 修正方法JSON数组
    prerequisite_skills TEXT,        -- 前置技能JSON数组
    related_techniques TEXT,         -- 相关技法JSON数组
    youtube_links TEXT,              -- 技法视频教程链接JSON数组
    practice_exercises TEXT,         -- 练习菜谱推荐JSON数组
    FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE SET NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE SET NULL
);
CREATE INDEX idx_step_techniques_step ON step_techniques(step_id);
CREATE INDEX idx_step_techniques_code ON step_techniques(technique_code);
```

---

## 表7：tips — 小贴士

```sql
CREATE TABLE tips (
    id TEXT PRIMARY KEY,              -- UUID
    recipe_id TEXT,                   -- 外键→recipes
    category TEXT NOT NULL,          -- 分类：采购技巧/刀工技巧/火候控制/调味技巧/装盘技巧/设备巧用/食材保存/时间管理/健康贴士
    content TEXT NOT NULL,            -- 技巧内容
    apply_to_step INTEGER,           -- 适用的步骤序号（NULL表示通用）
    apply_to_ingredient INTEGER,      -- 适用于哪个食材ID
    cost_level TEXT,                 -- 花多少钱：经济/普通/奢侈
    time_cost TEXT,                   -- 需要多少时间
    equipment_needed TEXT,           -- 需要什么工具JSON数组
    difficulty TEXT,                 -- 实施难度：简单/需要练习/专业级
    effectiveness_proven INTEGER DEFAULT 0, -- 效果是否经过验证
    difficulty_proven TEXT,          -- 验证难度：试了就行/需要多次/反复练习
    effectiveness_rating INTEGER,     -- 效果评分（1-5）
    source TEXT,                      -- 来源
    author TEXT,                      -- 作者/博主
    author_url TEXT,                  -- 作者链接
    is_verified INTEGER DEFAULT 0,   -- 是否已验证
    verified_by_user INTEGER DEFAULT 0, -- 用户是否验证过
    verified_date TEXT,              -- 验证日期
    user_modified_content TEXT,       -- 用户修改后的内容
    user_verified_result TEXT,       -- 用户的验证结果
    is_public INTEGER DEFAULT 0,     -- 是否公开分享
    likes_count INTEGER DEFAULT 0,  -- 获赞数
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_tips_recipe ON tips(recipe_id);
CREATE INDEX idx_tips_category ON tips(category);
```

---

## 表8：background_knowledge — 背景知识

```sql
CREATE TABLE background_knowledge (
    id TEXT PRIMARY KEY,              -- UUID
    recipe_id TEXT NOT NULL UNIQUE,  -- 外键→recipes（一道菜一份背景）
    origin_story TEXT,               -- 起源故事
    historical_background TEXT,       -- 历史背景
    era TEXT,                        -- 哪个朝代/时期
    cultural_significance TEXT,      -- 文化意义
    story_variants TEXT,             -- 不同版本的故事JSON数组
    famous_restaurants TEXT,         -- 著名餐厅JSON：[{name, location, signature_dish, notes}]
    famous_chefs TEXT,               -- 名厨大师JSON：[{name, era, specialty, contribution}]
    related_dishes TEXT,             -- 相关菜品JSON数组
    regional_variants TEXT,          -- 地域变种JSON：[{region, name, differences}]
    nutrition_benefits TEXT,         -- 营养价值/功效
    nutrition_highlights TEXT,       -- 营养亮点JSON数组
    nutrition_concerns TEXT,         -- 营养顾虑
    taboos TEXT,                     -- 饮食禁忌
    wine_pairing TEXT,               -- 配酒建议
    wine_pairing_details TEXT,      -- 配酒详细说明
    beverage_pairing TEXT,          -- 配饮建议（茶/果汁）
    staplefood_pairing TEXT,        -- 主食搭配
    side_dish_pairing TEXT,         -- 配菜推荐JSON数组
    weather_suitability TEXT,       -- 天气适宜性
    external_links TEXT,             -- 参考链接JSON：[{title, url, source}]
    media_references TEXT,           -- 媒体引用JSON：[{title, program, episode, url}]
    cultural_notes TEXT,             -- 文化备注
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_background_recipe ON background_knowledge(recipe_id);
```

---

## 表9：nutrition_info — 热量与营养

```sql
CREATE TABLE nutrition_info (
    id TEXT PRIMARY KEY,              -- UUID
    recipe_id TEXT NOT NULL UNIQUE,  -- 外键→recipes（一道菜一份营养）
    serving_size REAL,               -- 每份份量数值
    serving_unit TEXT,               -- 份量单位：g/克/份/碗
    servings_total INTEGER,         -- 总份数
    calories_kcal INTEGER,          -- 总热量（千卡）
    calories_per_serving INTEGER,    -- 每份热量
    protein_grams REAL,              -- 蛋白质（克）
    fat_grams REAL,                 -- 脂肪（克）
    saturated_fat_g REAL,           -- 饱和脂肪（克）
    trans_fat_g REAL,               -- 反式脂肪（克）
    carbohydrates_grams REAL,       -- 碳水化合物（克）
    fiber_grams REAL,               -- 膳食纤维（克）
    sugar_grams REAL,               -- 糖分（克）
    added_sugar_g REAL,             -- 添加糖（克）
    sodium_mg REAL,                -- 钠（毫克）
    cholesterol_mg REAL,            -- 胆固醇（毫克）
    vitamin_a_mcg REAL,             -- 维生素A（微克）
    vitamin_b1_mg REAL,             -- 维生素B1（毫克）
    vitamin_b2_mg REAL,             -- 维生素B2（毫克）
    vitamin_b3_mg REAL,             -- 维生素B3（毫克）
    vitamin_c_mg REAL,              -- 维生素C（毫克）
    vitamin_d_mcg REAL,             -- 维生素D（微克）
    vitamin_e_mg REAL,              -- 维生素E（毫克）
    calcium_mg REAL,                -- 钙（毫克）
    iron_mg REAL,                   -- 铁（毫克）
    zinc_mg REAL,                   -- 锌（毫克）
    magnesium_mg REAL,              -- 镁（毫克）
    potassium_mg REAL,              -- 钾（毫克）
    selenium_mcg REAL,              -- 硒（微克）
    calculation_method TEXT,        -- 计算方式说明
    data_source TEXT,               -- 数据来源
    is_estimated INTEGER DEFAULT 1, -- 是否估算
    confidence_level TEXT,          -- 数据置信度：低/中/高
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_nutrition_recipe ON nutrition_info(recipe_id);
```

---

## 表10：recipe_history — 烹饪历史日志

```sql
CREATE TABLE recipe_history (
    id TEXT PRIMARY KEY,              -- UUID
    recipe_id TEXT NOT NULL,          -- 外键→recipes
    cook_date TEXT NOT NULL,          -- 烹饪日期
    cook_sequence INTEGER,           -- 第几次做这道菜
    modifications TEXT,              -- 这次做的改动JSON：[{field, old_value, new_value, reason}]
    rating_this_time INTEGER,        -- 这次评分（1-5）
    feedback TEXT,                   -- 这次的口味反馈
    improvements TEXT,               -- 需要改进的地方
    photos TEXT,                     -- 这次的照片路径JSON数组
    time_actual_minutes INTEGER,     -- 这次实际用时
    time_vs_planned TEXT,            -- 实际与计划的对比
    companions TEXT,                 -- 同吃的人
    occasion VARCHAR(100),           -- 什么场合
    liked_by TEXT,                   -- 谁喜欢JSON：['我','女朋友','爸妈']
    would_recommend INTEGER,         -- 是否推荐
    mood TEXT,                       -- 做饭时的心情
    energy_level TEXT,              -- 体力/精力状态：充沛/一般/疲惫
    weather TEXT,                   -- 天气
    location TEXT,                   -- 在哪做的（家里/外面/公司）
    cost_actual REAL,               -- 这次花了多少钱
    difficulty_actual TEXT,         -- 这次觉得难度如何
    cleanup_time_actual INTEGER,     -- 收拾时间
    leftover_amount TEXT,           -- 剩了多少
    leftover_handling TEXT,         -- 剩菜怎么处理
    created_at TEXT,                 -- 创建时间
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_recipe_history_recipe ON recipe_history(recipe_id);
CREATE INDEX idx_recipe_history_date ON recipe_history(cook_date);
```

---

## 表11：cookware — 炊具/设备表

```sql
CREATE TABLE cookware (
    id TEXT PRIMARY KEY,              -- UUID
    name TEXT NOT NULL,               -- 炊具名称
    category TEXT,                    -- 分类：炒锅/煎锅/蒸锅/烤箱/砂锅/电饭煲/空气炸锅/高压锅/料理机/其他
    size TEXT,                        -- 尺寸（如28cm/30cm）
    material TEXT,                    -- 材质：铁/不锈钢/不粘/砂锅/铜
    heat_source TEXT,                 -- 热源：燃气/电磁炉/电陶炉/通用
    quantity INTEGER DEFAULT 1,      -- 数量
    purchase_date TEXT,               -- 购买日期
    brand TEXT,                       -- 品牌
    price REAL,                      -- 价格
    condition TEXT,                  -- 状态：全新/良好/一般/需更换
    notes TEXT,                       -- 备注
    maintenance_tips TEXT,           -- 保养技巧
    compatible_dishes TEXT,           -- 适合的菜JSON数组
    incompatible_dishes TEXT,         -- 不适合的菜JSON数组
    user_rating INTEGER,             -- 用户评分（1-5）
    created_at TEXT,                 -- 创建时间
    updated_at TEXT                   -- 更新时间
);
CREATE INDEX idx_cookware_name ON cookware(name);
CREATE INDEX idx_cookware_category ON cookware(category);
```

---

## 表12：beverage_pairings — 饮品搭配表

```sql
CREATE TABLE beverage_pairings (
    id TEXT PRIMARY KEY,              -- UUID
    recipe_id TEXT NOT NULL,          -- 外键→recipes
    pairing_type TEXT,               -- 搭配类型：配酒/配茶/配饮料/配主食
    beverage_name TEXT NOT NULL,     -- 饮品名称
    beverage_category TEXT,          -- 饮品大类：白酒/红酒/啤酒/清酒/威士忌/绿茶/红茶/乌龙茶/果汁/汽水
    pairing_reason TEXT,             -- 搭配理由
    flavor_match TEXT,               -- 风味搭配说明
    temperature TEXT,                -- 饮用温度：冰镇/常温/温热/热饮
    brand_recommendation TEXT,       -- 推荐品牌
    price_range TEXT,                -- 价格区间
    substitute_options TEXT,         -- 替代选择JSON数组
    occasion_suitability TEXT,       -- 场合适宜性JSON数组
    region_tradition TEXT,          -- 地域传统搭配
    notes TEXT,                       -- 备注
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_beverage_recipe ON beverage_pairings(recipe_id);
```

---

## 表13：recipe_collections — 食谱集合/专题

```sql
CREATE TABLE recipe_collections (
    id TEXT PRIMARY KEY,              -- UUID
    name TEXT NOT NULL,               -- 集合名称（如"川菜专题"）
    description TEXT,                 -- 集合描述
    type TEXT,                        -- 类型：节日专题/季节专题/菜系专题/场景专题/难度专题/食材专题/健康专题
    cover_image TEXT,                 -- 封面图片
    recipe_ids TEXT,                  -- 包含的食谱ID列表JSON
    created_by TEXT,                  -- 创建人：system/user
    is_public INTEGER DEFAULT 0,     -- 是否公开
    tags TEXT,                        -- 标签JSON数组
    target_audience TEXT,            -- 目标人群
    usage_count INTEGER DEFAULT 0,   -- 被使用次数
    created_at TEXT,                  -- 创建时间
    updated_at TEXT,                  -- 更新时间
    notes TEXT                        -- 备注
);
CREATE INDEX idx_recipe_collections_name ON recipe_collections(name);
CREATE INDEX idx_recipe_collections_type ON recipe_collections(type);
```

---

## 表关系

```
recipes (主表)
    │
    ├── recipe_locations (1:N)
    ├── ingredients (1:N)
    │         └── ingredient_preparations (1:N)
    ├── cooking_steps (1:N)
    │         └── step_techniques (1:N)
    ├── tips (1:N)
    ├── background_knowledge (1:1)
    ├── nutrition_info (1:1)
    ├── recipe_history (1:N)
    ├── beverage_pairings (1:N)
    └── recipe_collections (N:N)
```

---

## 索引说明

| 索引 | 表 | 用途 |
|------|------|------|
| `idx_recipes_name` | recipes | 按菜名搜索 |
| `idx_recipes_difficulty` | recipes | 按难度筛选 |
| `idx_recipes_status` | recipes | 按状态筛选 |
| `idx_recipe_locations_cuisine` | recipe_locations | 按菜系筛选 |
| `idx_ingredients_name` | ingredients | 按食材名搜索 |
| `idx_cooking_steps_sequence` | cooking_steps | 按步骤顺序查询 |
| `idx_tips_category` | tips | 按分类查询小贴士 |
| `idx_recipe_history_date` | recipe_history | 按日期查询烹饪历史 |
| `idx_cookware_category` | cookware | 按分类查询炊具 |

---

## 数据库文件

- 路径：`.db/chef_data.db`
- 创建脚本：`scripts/init_db.py`