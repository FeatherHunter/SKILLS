# body_photos — 身材照片记录

```sql
CREATE TABLE body_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,           -- 日期 YYYY-MM-DD
    time TEXT NOT NULL,           -- 时间 HH:MM:SS
    photo_path TEXT NOT NULL,     -- 相对路径，如 "2026-05-30_001.jpg"
    tag TEXT NOT NULL,            -- 自定义标签：正面/背面/侧面/手臂等
    note TEXT NOT NULL,           -- 备注
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_body_photos_date ON body_photos(date);
CREATE INDEX idx_body_photos_tag ON body_photos(tag);
```

## 存储说明

- **环境变量**：`CALORIE_PHOTOS_DIR`（强制配置，无默认值）
- **照片命名**：`{date}_{序号}.{ext}`，如 `2026-05-30_001.jpg`
- **数据库**：存储相对路径

## 体重关联

照片通过时间戳关联 `weight_log` 表中最近的体重记录（按 created_at 排序取最后一条）。
