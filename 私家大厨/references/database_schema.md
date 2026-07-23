# 私家大厨 - 数据库结构 v2.2

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

> 基于17张表规范化设计，无JSON数组，所有多值字段用关联表

## 表总览（17张）

| # | 表名 | 类型 | 说明 |
|---|------|------|------|
| 1 | recipes | 主表 | 食谱核心信息 |
| 2 | recipe_categories | 分类 | 菜系/地区/国家 |
| 3 | recipe_seasons | 分类关联 | 适合季节 |
| 4 | recipe_cooking_methods | 分类关联 | 烹饪方式 |
| 5 | recipe_flavors | 分类关联 | 口味 |
| 6 | recipe_diet_tags | 分类关联 | 饮食标签 |
| 7 | recipe_meal_types | 分类关联 | 用餐类型 |
| 8 | ingredients | 实体 | 食材清单 |
| 9 | cooking_steps | 实体 | 烹饪步骤 |
| 10 | step_ingredients | 关联 | 步骤×食材 |
| 11 | step_techniques | 关联 | 步骤×技法 |
| 12 | tips | 实体 | 小贴士 |
| 13 | recipe_history | 实体 | 烹饪历史 |
| 14 | background_knowledge | 实体 | 背景知识 |
| 15 | recipe_relations | 关联 | 食谱派生关系 |
| 16 | cookware | 实体 | 炊具设备 |
| 17 | nutrition_info | 实体 | 营养信息 |

---

## 表1：recipes — 食谱主表

```sql
CREATE TABLE recipes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    difficulty TEXT,
    servings INTEGER,
    total_time_minutes INTEGER,
    status TEXT DEFAULT '未做',
    photo_url TEXT,           -- 本食谱的成品照片(用户上传、拍照或占位图)
    source TEXT,              -- 食谱来源说明,例如"扬帆远航【紫食谱2.0】-214-313"
    source_url TEXT,          -- 源食谱的网页链接或源食谱的图片 URL(兼容两种)
    created_at TEXT,
    updated_at TEXT
);
CREATE INDEX idx_recipes_name ON recipes(name);
CREATE INDEX idx_recipes_difficulty ON recipes(difficulty);
CREATE INDEX idx_recipes_status ON recipes(status);
```

### 字段语义补充

- **`photo_url`** — **本食谱**的成品照片 URL 或本地路径。AI 自动录入时如果用户没有提供真实照片,可以临时填充 picsum 占位 URL(`https://picsum.photos/seed/<recipe_slug>/<w>/<h>`)作为兜底,但应在 `description` 或 `source` 字段注明,以便后续替换。
- **`source_url`** — 源食谱的 **网页链接**(如 baike.baidu.com/...、下厨房/小红书详情页) **或** 源食谱的 **图片 URL**(如源菜谱书的扫描页截图、源出版物的内页图) **或** 本地源食谱图片路径(命名空间形式 `chef://<recipe_slug>__<source>__<YYYYMMDD>.<ext>`,实际路径在 `$CHEF_OUTPUT_DIR/source_photos/`)。系统按用户实际录入内容存放,渲染时根据格式自动选择显示方式:
  - `chef://...` 命名空间 → 拼回 `$CHEF_OUTPUT_DIR/source_photos/...` 当 `<img>` 显示
  - `.jpg/.jpeg/.png/.webp/.gif` 扩展名 → 当 `<img>` 显示
  - `picsum/loremflickr/imgur/unsplash` 等图床域名 → 当 `<img>` 显示
  - 其他 → 当 `<a target="_blank">` 显示为外链

### 源照片本地存放规范

- 存放根目录:`$CHEF_OUTPUT_DIR/source_photos/`(默认 `D:/CookHub/source_photos/`)
- 文件名格式:`<recipe_slug>__<source>__<YYYYMMDD>.<ext>`
  - `recipe_slug`:菜名 slugify(由 `slugify(name)` 生成)
  - `source`:来源短码,常见值 `baike` / `douyin` / `xiachufang` / `cookbook` / `manual` 等
  - `YYYYMMDD`:录入日期
  - `ext`:实际文件扩展名
- 数据库存什么:`source_url` 字段填 **`chef://<recipe_slug>__<source>__<YYYYMMDD>.<ext>`**(用 `chef://` 命名空间标识,不直接存绝对路径,便于跨设备迁移)
- 写入路径:AI 收到用户提供的本地源食谱图片后,调用:
  ```bash
  cp "<user_file>" "$CHEF_OUTPUT_DIR/source_photos/<recipe_slug>__<source>__$(date +%Y%m%d).<ext>"
  python scripts/recipe_manager.py update <recipe_id> --source_url "chef://<recipe_slug>__<source>__YYYYMMDD.<ext>"
  ```

## 表2：recipe_categories — 分类标签

```sql
CREATE TABLE recipe_categories (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    cuisine_type TEXT,
    region TEXT,
    country TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_recipe_categories_recipe ON recipe_categories(recipe_id);
CREATE INDEX idx_recipe_categories_cuisine ON recipe_categories(cuisine_type);
```

## 表3：recipe_seasons — 适合季节

```sql
CREATE TABLE recipe_seasons (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    season TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_recipe_seasons_recipe ON recipe_seasons(recipe_id);
```

## 表4：recipe_cooking_methods — 烹饪方式

```sql
CREATE TABLE recipe_cooking_methods (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    method TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_recipe_cooking_methods_recipe ON recipe_cooking_methods(recipe_id);
```

## 表5：recipe_flavors — 口味

```sql
CREATE TABLE recipe_flavors (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    flavor TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_recipe_flavors_recipe ON recipe_flavors(recipe_id);
```

## 表6：recipe_diet_tags — 饮食标签

```sql
CREATE TABLE recipe_diet_tags (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_recipe_diet_tags_recipe ON recipe_diet_tags(recipe_id);
```

## 表7：recipe_meal_types — 用餐类型

```sql
CREATE TABLE recipe_meal_types (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    meal_type TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_recipe_meal_types_recipe ON recipe_meal_types(recipe_id);
```

## 表8：ingredients — 食材清单

```sql
CREATE TABLE ingredients (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    sequence INTEGER,
    name TEXT NOT NULL,
    category TEXT,
    quantity REAL,
    unit TEXT,
    quantity_text TEXT,
    is_optional INTEGER DEFAULT 0,
    substitute TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_ingredients_recipe ON ingredients(recipe_id);
CREATE INDEX idx_ingredients_name ON ingredients(name);
```

## 表9：cooking_steps — 烹饪步骤

```sql
CREATE TABLE cooking_steps (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    action TEXT NOT NULL,
    duration_minutes INTEGER,
    heat_level TEXT,
    temperature TEXT,
    expected_result TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_cooking_steps_recipe ON cooking_steps(recipe_id);
CREATE INDEX idx_cooking_steps_sequence ON cooking_steps(recipe_id, sequence);
```

## 表10：step_ingredients — 步骤×食材关联

```sql
CREATE TABLE step_ingredients (
    id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL,
    ingredient_id TEXT NOT NULL,
    quantity_used REAL,
    introduced_at TEXT,
    FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE
);
CREATE INDEX idx_step_ingredients_step ON step_ingredients(step_id);
CREATE INDEX idx_step_ingredients_ingredient ON step_ingredients(ingredient_id);
```

## 表11：step_techniques — 步骤技法

```sql
CREATE TABLE step_techniques (
    id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL,
    recipe_id TEXT NOT NULL,
    technique_name TEXT NOT NULL,
    description TEXT,
    key_points TEXT,
    FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE CASCADE,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_step_techniques_step ON step_techniques(step_id);
CREATE INDEX idx_step_techniques_recipe ON step_techniques(recipe_id);
```

## 表12：tips — 小贴士

```sql
CREATE TABLE tips (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    step_id TEXT,
    ingredient_id TEXT,
    category TEXT,
    content TEXT NOT NULL,
    priority INTEGER,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (step_id) REFERENCES cooking_steps(id) ON DELETE SET NULL,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE SET NULL
);
CREATE INDEX idx_tips_recipe ON tips(recipe_id);
CREATE INDEX idx_tips_step ON tips(step_id);
CREATE INDEX idx_tips_ingredient ON tips(ingredient_id);
```

## 表13：recipe_history — 烹饪历史

```sql
CREATE TABLE recipe_history (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    cook_date TEXT NOT NULL,
    cook_sequence INTEGER,
    rating REAL,
    feedback TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_recipe_history_recipe ON recipe_history(recipe_id);
CREATE INDEX idx_recipe_history_date ON recipe_history(cook_date);
```

## 表14：background_knowledge — 背景知识

```sql
CREATE TABLE background_knowledge (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL UNIQUE,
    origin_story TEXT,
    historical_background TEXT,
    cultural_significance TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_background_recipe ON background_knowledge(recipe_id);
```

## 表15：recipe_relations — 食谱关系

```sql
CREATE TABLE recipe_relations (
    id TEXT PRIMARY KEY,
    parent_id TEXT NOT NULL,
    child_id TEXT NOT NULL,
    relation_type TEXT,
    change_summary TEXT,
    FOREIGN KEY (parent_id) REFERENCES recipes(id) ON DELETE CASCADE,
    FOREIGN KEY (child_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_recipe_relations_parent ON recipe_relations(parent_id);
CREATE INDEX idx_recipe_relations_child ON recipe_relations(child_id);
```

## 表16：cookware — 炊具设备

```sql
CREATE TABLE cookware (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_cookware_recipe ON cookware(recipe_id);
```

## 表17：nutrition_info — 营养信息

```sql
CREATE TABLE nutrition_info (
    id TEXT PRIMARY KEY,
    recipe_id TEXT NOT NULL UNIQUE,
    serving_size REAL,
    serving_unit TEXT,
    calories INTEGER,
    protein REAL,
    fat REAL,
    carbs REAL,
    fiber REAL,
    sodium REAL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);
CREATE INDEX idx_nutrition_recipe ON nutrition_info(recipe_id);
```

---

## ER图（简略）

```
recipes (1)
├── recipe_categories (1:1)
├── recipe_seasons (1:N)
├── recipe_cooking_methods (1:N)
├── recipe_flavors (1:N)
├── recipe_diet_tags (1:N)
├── recipe_meal_types (1:N)
├── ingredients (1:N)
│    └── step_ingredients (1:N) → cooking_steps (1:N)
│         └── step_techniques (1:N)
├── cooking_steps (1:N)
├── tips (1:N) → 可关联 step_id / ingredient_id
├── recipe_history (1:N)
├── nutrition_info (1:1)
├── background_knowledge (1:1)
├── recipe_relations (1:N) → parent/child 双向
└── cookware (1:N)
```

---

## 索引说明

| 索引名 | 表 | 用途 |
|--------|-------|------|
| idx_recipes_name | recipes | 按菜名查询 |
| idx_recipes_difficulty | recipes | 按难度筛选 |
| idx_recipes_status | recipes | 按状态筛选 |
| idx_recipe_categories_cuisine | recipe_categories | 按菜系筛选 |
| idx_ingredients_recipe | ingredients | 按食谱查食材 |
| idx_ingredients_name | ingredients | 按食材名搜索 |
| idx_cooking_steps_recipe | cooking_steps | 按食谱查步骤 |
| idx_cooking_steps_sequence | cooking_steps | 步骤排序 |
| idx_tips_recipe | tips | 按食谱查小贴士 |
| idx_recipe_history_recipe | recipe_history | 按食谱查历史 |
| idx_recipe_history_date | recipe_history | 按日期查询 |
| idx_nutrition_recipe | nutrition_info | 按食谱查营养 |