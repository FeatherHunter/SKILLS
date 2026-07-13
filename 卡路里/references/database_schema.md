# 卡路里数据库结构

> **⚠️ 本文件由人工维护,任何 DDL 变更请同步本文件。**
> 权威源:`scripts/db.py` 的 `init_db()`。本文件必须与之 100% 对齐。
>
> **维护建议**:后续可考虑 `scripts/generate_schema_doc.py` 从 `PRAGMA table_info()` 自动生成,以根治漂移。

---

## 表总览

| 表名 | 说明 | 主键 | init 归属 |
|------|------|------|-----------|
| `food_log` | 食物记录（含饮水）| id | `db.py:init_db` |
| `daily_goal` | 每日目标（营养+体重+饮水）| id (固定=1) | `db.py:init_db` |
| `exercise_log` | 运动记录 | id | `db.py:init_db` |
| `weight_log` | 体重记录 | id | `db.py:init_db` |
| `nutrition_products` | 食品营养成分库 | id | `db.py:init_db` |
| `workout_plan_config` | 健身计划元信息 | id (固定=1) | `db.py:init_db` |
| `workout_plans` | 健身日程 | id | `db.py:init_db` |
| `body_photos` | 身材照片记录 | id | `db.py:init_db` |

> **重构历史**:
> - `2026-07-12`:删除 `fitness_goals` / `sleep_records` 两张废弃表;`entries` → `food_log` 改名;新增 `workout_plan_config` / `workout_plans`;`exercise_log` 加 `xunji_localid` / `xunji_title`。
> - `2026-06-29`:运动功能扩展,`exercise_log` 加 6 字段(category/difficulty/distance_km/avg_heart_rate/set_index/load_kg)。
> - `2026-07-13`:补 `exercise_log.reps` DDL 声明(原漏);补 `xunji_localid` 索引。

---

## food_log — 食物记录（含饮水）

```sql
CREATE TABLE food_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,           -- 日期 YYYY-MM-DD
    time TEXT,                    -- 时间 HH:MM:SS
    food_name TEXT NOT NULL,      -- 食物名称（饮水统一为 '💧水'）
    grams INTEGER NOT NULL,       -- 重量（克）
    calories INTEGER NOT NULL,    -- 热量（卡）
    protein INTEGER DEFAULT 0,    -- 蛋白质（克）
    carbs INTEGER DEFAULT 0,      -- 碳水（克）
    fat INTEGER DEFAULT 0,        -- 脂肪（克）
    note TEXT DEFAULT '',         -- 备注
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_food_log_date ON food_log(date);
```

> **迁移历史**:
> - 2026-07-12 之前表名为 `entries`;`db.py:179-186` 自动 rename / 合并 / drop。
> - 饮水复用本表,`food_name='💧水'`,`grams` 字段用作 ml 数值。

---

## daily_goal — 每日目标

```sql
CREATE TABLE daily_goal (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- 单行表
    calorie_goal INTEGER NOT NULL DEFAULT 1800,   -- 每日热量目标
    protein_goal INTEGER DEFAULT 150,            -- 蛋白 g
    carbs_goal INTEGER DEFAULT 200,              -- 碳水 g
    fat_goal INTEGER DEFAULT 60,                 -- 脂肪 g
    weight_goal REAL,                            -- 体重目标 kg
    goal_deadline TEXT,                          -- 目标截止日期
    water_goal INTEGER DEFAULT 2000,             -- 饮水目标 ml（2026-06-29 迁移加）
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

> **触发词映射**（避免 D5 混淆）:
> - 「**设营养目标**」= calorie_goal / protein_goal / carbs_goal / fat_goal 4 字段
> - 「**设体重目标**」= weight_goal + goal_deadline 2 字段
> - 「**设饮水目标**」= water_goal 1 字段(`calorie_tracker.py goal` 第 5 参)
> - daily_goal 同时承载 3 类目标,DB 拆表会破坏向后兼容,文档注释为当前方案。

---

## exercise_log — 运动记录

```sql
CREATE TABLE exercise_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT,
    exercise_type TEXT NOT NULL,  -- 运动类型
    duration_minutes INTEGER,     -- 时长（分钟）
    calories_burned INTEGER NOT NULL,  -- 消耗卡路里
    note TEXT DEFAULT '',
    reps INTEGER,                 -- 动作次数/组数（2026-07-13 补 DDL）
    -- 2026-06-29 运动功能扩展 6 字段
    category TEXT,                -- 有氧/力量/柔韧/日常
    difficulty TEXT,              -- easy/normal/hard（2026-07-12 从 intensity 改名）
    distance_km REAL,             -- 跑步/骑行距离
    avg_heart_rate INTEGER,       -- 平均心率 bpm
    set_index INTEGER,            -- 力量场景：第几组
    load_kg REAL,                 -- 力量场景：单侧重量
    -- 2026-07-12 训记关联 2 字段
    xunji_localid TEXT,           -- 训记训练记录唯一标识（去重键）
    xunji_title TEXT,             -- 训记训练名称
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

**索引**:
- `idx_exercise_date` — 按日期查询
- `idx_exercise_category` — 按类查询（2026-06-29 加）
- `idx_exercise_type` — 按类型查询（2026-06-29 加）
- `idx_exercise_xunji_localid` — 训记去重（2026-07-13 补）

> **字段注意**:
> - `difficulty` 旧值为中文 4 档（'低'/'中'/'高'/'极限'）;2026-07-12 迁移改为 english 3 档（'easy'/'normal'/'hard'）。
> - `reps` 字段被 `exercise.py:53` 使用写入,但 DDL 原始未声明;2026-07-13 通过 ALTER 迁移补齐。**已存在的老库下次 init_db 时自动获得此列**。
> - `xunji_localid` + `set_index` 组成训记去重键(`xunji_adapter.py:75-79`)。

---

## weight_log — 体重记录

```sql
CREATE TABLE weight_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT,
    weight_kg REAL NOT NULL,      -- 体重（公斤）
    height_cm REAL,               -- 身高（厘米）
    bmi REAL,                     -- BMI（自动计算）
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_weight_date ON weight_log(date);
```

---

## nutrition_products — 食品营养成分库

```sql
CREATE TABLE nutrition_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    brand TEXT,
    calories REAL NOT NULL,        -- 千卡/100g
    protein REAL NOT NULL,         -- 克/100g
    fat REAL NOT NULL,
    saturated_fat REAL,
    carbohydrates REAL NOT NULL,
    sugar REAL,
    dietary_fiber REAL,
    sodium REAL NOT NULL,          -- 毫克/100g
    source TEXT NOT NULL DEFAULT '未知',      -- 数据来源(自由文本,见数据治理原则)
    is_deprecated INTEGER NOT NULL DEFAULT 0, -- 废弃标记 0=有效 1=废弃
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_product_name ON nutrition_products(product_name);
CREATE INDEX idx_product_source ON nutrition_products(source);
```

> **`source` 字段治理**（2026-06-30 共识）:
> - 不维护"推荐来源枚举",AI 自由填写。
> - 不知道就写 `"未知"` 或 `"AI估算,未查证"`,不编造权威来源。
> - 完全自由文本,只要非空。

> **`is_deprecated` 字段**:
> - `0` = 有效,默认查询可见
> - `1` = 废弃,默认查询不返回
> - 替代旧的 `[已废弃]` note 字符串标记。
> - `batch_import.py dedupe` 检查有效条目中的重复。

---

## workout_plan_config — 健身计划元信息

```sql
CREATE TABLE workout_plan_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- 单行表
    title TEXT NOT NULL,                    -- 计划标题
    version TEXT,                           -- 版本号
    description TEXT,                       -- 计划描述
    total_weeks INTEGER NOT NULL,           -- 计划总周数
    start_date TEXT NOT NULL,               -- 计划起始日期 YYYY-MM-DD
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

> **循环逻辑**:`workout_plan.calc_plan_week(target_date, config)`:
> ```
> real_week = (date - start_date).days // 7 + 1
> plan_week = ((real_week - 1) % total_weeks) + 1
> day_of_week = date.isoweekday()  (1=Mon...7=Sun)
> ```

---

## workout_plans — 健身日程

```sql
CREATE TABLE workout_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,           -- 1=Mon...7=Sun
    session_index INTEGER NOT NULL DEFAULT 1,
    session_label TEXT NOT NULL,            -- e.g. "A1 推"
    time_start TEXT,                        -- HH:MM
    time_end TEXT,                          -- HH:MM
    is_rest_day INTEGER DEFAULT 0,          -- 0=训练 / 1=休息
    total_sets INTEGER,                     -- 总组数
    movements TEXT NOT NULL DEFAULT '[]',   -- JSON 数组(见下方结构)
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(week_number, day_of_week, session_index)
);
CREATE INDEX idx_wp_week_day ON workout_plans(week_number, day_of_week);
```

**`movements` JSON 结构**:
```json
{
  "session_label": "A1 推",
  "movements": [
    {
      "name": "哑铃卧推",
      "part": "胸",
      "type": "复合",
      "note": "主项",
      "rest": "90s",
      "sets": [
        {"reps": 12, "weight": 20, "unit": "kg"},
        {"reps": 10, "weight": 22.5, "unit": "kg"}
      ]
    }
  ]
}
```

> **写入**: `plan_generator.write_plan(plan_json)` 校验后全量覆盖(`DELETE + INSERT`)。
> **增量 CRUD**: `add_session` / `update_session` / `delete_session` / `copy_week` / `delete_week` / `insert_week`。
> **循环查询**: `workout_plan.get_day_plan(date)` 走 `calc_plan_week()`。

---

## body_photos — 身材照片记录

```sql
CREATE TABLE body_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    photo_path TEXT NOT NULL,
    tag TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_body_photos_date ON body_photos(date);
CREATE INDEX idx_body_photos_tag ON body_photos(tag);
```

> **存储说明**: 照片文件存储在 `CALORIE_PHOTOS_DIR` 环境变量指定的目录,数据库存储相对路径。

---

## 索引说明

| 索引 | 表 | 用途 | 来源 |
|------|------|------|------|
| `idx_food_log_date` | food_log | 按日期查询 | db.py:177 |
| `idx_weight_date` | weight_log | 按日期查询 | db.py:191 |
| `idx_exercise_date` | exercise_log | 按日期查询 | db.py:192 |
| `idx_exercise_category` | exercise_log | 按类查询 | db.py:279（2026-06-29） |
| `idx_exercise_type` | exercise_log | 按类型查询 | db.py:280（2026-06-29） |
| `idx_exercise_xunji_localid` | exercise_log | 训记去重 | db.py:280（2026-07-13 补） |
| `idx_product_name` | nutrition_products | 搜索食品名称 | db.py:193 |
| `idx_product_source` | nutrition_products | 按数据来源过滤 | db.py:222 |
| `idx_wp_week_day` | workout_plans | 按周次+星期查 | db.py:315 |
| `idx_body_photos_date` | body_photos | 按日期查 | db.py:325 |
| `idx_body_photos_tag` | body_photos | 按标签查 | db.py:326 |

---

## 表关系

```
daily_goal (1条记录,单行表)
  ├── calorie_goal / protein_goal / carbs_goal / fat_goal → 每日营养目标
  ├── weight_goal / goal_deadline → 体重目标
  └── water_goal → 饮水目标

food_log (多条)
  └── date → 每日饮食记录（含饮水）

weight_log (多条)
  └── date → 每日体重

exercise_log (多条)
  ├── date → 每日运动
  └── xunji_localid + set_index → 训记去重键

nutrition_products (多条)
  └── product_name → 食品营养成分库

workout_plan_config (1条,单行表)
  └── total_weeks / start_date → 循环基础

workout_plans (多条)
  └── week_number + day_of_week + session_index → 训练日程
       └── movements (JSON) → 计划动作详情

body_photos (多条)
  └── date / tag → 身材照片
```

---

## 删除的表（已迁移出本技能）

| 表名 | 替代去向 | 删除时间 | 删除原因 |
|------|---------|---------|---------|
| `fitness_goals` | `workout_plans`（2026-07-12 重构）| 2026-07-12 | 每日/每周/每月目标改为"健身计划"模型 |
| `sleep_records` | `作息管家`技能 | 2026-07-12 | 睡眠追踪移交给作息管家 |
| `entries` | `food_log` | 2026-07-12 | 重命名 + 合并 |

> **数据保留**: `db.py` 迁移代码确保数据不丢。`fitness_goals` / `sleep_records` 物理删除,`entries` 改名合并到 `food_log`。

---

## 迁移时间线

| 日期 | 变更 | 迁移代码位置 |
|------|------|------------|
| 2026-06-29 | exercise_log 加 6 字段(运动扩展) | db.py:235-256 |
| 2026-06-29 | nutrition_products 加 source / is_deprecated | db.py:209-219 |
| 2026-06-29 | daily_goal 加 water_goal | db.py:204-207 |
| 2026-07-12 | 删除 sleep_records | db.py:189-190 |
| 2026-07-12 | entries → food_log 改名/合并 | db.py:179-186 |
| 2026-07-12 | exercise_log 加 xunji_localid / xunji_title | db.py:270-276 |
| 2026-07-12 | 删除 fitness_goals | db.py:317-319 |
| 2026-07-12 | 新建 workout_plan_config / workout_plans | db.py:282-315 |
| 2026-07-12 | intensity → difficulty 映射 | db.py:258-268 |
| 2026-07-13 | 补 exercise_log.reps DDL | db.py:251 |
| 2026-07-13 | 加 idx_exercise_xunji_localid | db.py:280 |

> **幂等保证**: 所有迁移使用 `IF NOT EXISTS` / `IF EXISTS` / `try-except pass`,重复运行 init_db 不会报错。
