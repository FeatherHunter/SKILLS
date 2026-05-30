# 卡路里数据库结构

## 表总览

| 表名 | 说明 | 主键 |
|------|------|------|
| `entries` | 食物记录 | id |
| `daily_goal` | 每日目标（含体重目标）| id (固定=1) |
| `weight_log` | 体重记录 | id |
| `exercise_log` | 运动记录 | id |
| `fitness_goals` | 健身目标（每日/每周/每月/长期）| id |
| `sleep_records` | 睡眠记录（归属就寝日）| id |
| `nutrition_products` | 食品营养成分库 | id |
| `body_photos` | 身材照片记录 | id |

---

## entries — 食物记录

```sql
CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,           -- 日期 YYYY-MM-DD
    time TEXT,                     -- 时间 HH:MM:SS
    food_name TEXT NOT NULL,      -- 食物名称
    grams INTEGER NOT NULL,       -- 重量（克）
    calories INTEGER NOT NULL,    -- 热量（卡）
    protein INTEGER DEFAULT 0,    -- 蛋白质（克）
    carbs INTEGER DEFAULT 0,      -- 碳水（克）
    fat INTEGER DEFAULT 0,        -- 脂肪（克）
    note TEXT DEFAULT '',         -- 备注
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_entries_date ON entries(date);
```

---

## daily_goal — 每日目标

```sql
CREATE TABLE daily_goal (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    calorie_goal INTEGER NOT NULL DEFAULT 1800,
    protein_goal INTEGER DEFAULT 150,
    carbs_goal INTEGER DEFAULT 200,
    fat_goal INTEGER DEFAULT 60,
    weight_goal REAL,              -- 体重目标（kg）
    goal_deadline TEXT,            -- 目标截止日期
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

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
    reps INTEGER,                 -- 动作次数/组数
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_exercise_date ON exercise_log(date);
```

---

## fitness_goals — 健身目标

```sql
CREATE TABLE fitness_goals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,         -- 目标名称，如"每日俯卧撑"
    goal_type       TEXT NOT NULL,         -- daily/weekly/monthly/longterm
    exercise_type   TEXT NOT NULL,         -- 运动类型
    target_unit     TEXT NOT NULL,         -- 个/分钟/公里
    target_value    INTEGER NOT NULL,      -- 目标值
    start_date      TEXT NOT NULL,         -- 开始日期
    end_date        TEXT,                  -- NULL 表示永久
    status          TEXT DEFAULT 'active', -- active/paused
    note            TEXT,
    created_at      INTEGER NOT NULL,      -- Unix 时间戳
    updated_at      INTEGER
);
CREATE INDEX idx_fg_date ON fitness_goals(start_date);
CREATE INDEX idx_fg_type ON fitness_goals(exercise_type);
CREATE INDEX idx_fg_status ON fitness_goals(status);
```

---

## sleep_records — 睡眠记录

```sql
CREATE TABLE sleep_records (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL UNIQUE,  -- 归属就寝日 YYYY-MM-DD
    sleep_hours     REAL NOT NULL,         -- 睡眠时长（小时）
    bedtime         TEXT,                  -- 就寝时间 HH:MM
    wake_time       TEXT,                  -- 起床时间 HH:MM
    note            TEXT,
    created_at      TEXT NOT NULL,         -- ISO 格式
    updated_at      TEXT
);
CREATE INDEX idx_sleep_date ON sleep_records(date);
```

> **睡眠归属规则**：记录归属于**就寝那天**，而非起床日。

---

## nutrition_products — 食品营养成分库

```sql
CREATE TABLE nutrition_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    brand TEXT,
    calories REAL NOT NULL,       -- 千卡/100g
    protein REAL NOT NULL,        -- 克/100g
    fat REAL NOT NULL,
    saturated_fat REAL,
    carbohydrates REAL NOT NULL,
    sugar REAL,
    dietary_fiber REAL,
    sodium REAL NOT NULL,        -- 毫克/100g
    note TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_product_name ON nutrition_products(product_name);
```

---

## 表关系

```
daily_goal (1条记录)
  ├── calorie_goal, protein_goal, carbs_goal, fat_goal → 每日营养目标
  └── weight_goal, goal_deadline → 体重目标

entries (多条)
  └── date → 每日饮食记录

weight_log (多条)
  └── date → 每日体重

exercise_log (多条)
  └── date → 每日运动

fitness_goals (多条)
  └── goal_type + status → 健身目标管理

sleep_records (多条)
  └── date → 每日睡眠（归属就寝日）

nutrition_products (多条)
  └── product_name → 食品营养成分库
```

---

## 索引说明

| 索引 | 表 | 用途 |
|------|------|------|
| `idx_entries_date` | entries | 按日期查询食物记录 |
| `idx_weight_date` | weight_log | 按日期查询体重 |
| `idx_exercise_date` | exercise_log | 按日期查询运动 |
| `idx_fg_date` | fitness_goals | 按开始日期查询 |
| `idx_fg_type` | fitness_goals | 按运动类型查询 |
| `idx_fg_status` | fitness_goals | 按状态筛选 |
| `idx_sleep_date` | sleep_records | 按日期查询 |
| `idx_product_name` | nutrition_products | 搜索食品名称 |

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

> **存储说明**：照片文件存储在 `CALORIE_PHOTOS_DIR` 环境变量指定的目录，数据库存储相对路径。