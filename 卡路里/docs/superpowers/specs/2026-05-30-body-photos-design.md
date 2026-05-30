# 身材照片记录功能设计

## 概述

在卡路里技能中新增身材照片记录功能，用于每天记录不同角度的身材照片（正面、背面、侧面、手臂等），支持查看历史、对比、生成 GIF 变化动画。

## 数据库设计

### body_photos 表

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

**字段说明**：
- `date`：照片日期，格式 YYYY-MM-DD
- `time`：照片时间，格式 HH:MM:SS
- `photo_path`：相对路径，如 "2026-05-30_001.jpg"
- `tag`：自定义标签（正面/背面/侧面/手臂等）
- `note`：备注，可以是空字符串但不能为 NULL

### 体重关联

照片通过时间戳关联 `weight_log` 表中**最近的体重记录**（按 created_at 排序取最后一条）。

## 存储方案

### 环境变量

- **变量名**：`CALORIE_PHOTOS_DIR`
- **要求**：强制配置，无默认值
- **启动检查**：脚本启动时若未配置，直接报错退出

### 文件命名

- **格式**：`{date}_{序号}.{ext}`
- **示例**：`2026-05-30_001.jpg`
- **序号**：同一天自动递增

### 目录结构

```
$CALORIE_PHOTOS_DIR/
├── 2026-05-30_001.jpg
├── 2026-05-30_002.jpg
├── 2026-05-31_001.jpg
└── gifs/
    ├── 正面_2026-01-01_2026-05-30.gif
    └── ...
```

## CLI 命令

### 记录照片

```bash
python scripts/body_photo_tracker.py add <path1> [path2...] --tag <标签> [--note "..."]
```

- 支持批量添加
- 自动复制照片到 `CALORIE_PHOTOS_DIR`
- 自动生成文件名

### 查询照片

```bash
python scripts/body_photo_tracker.py list [--days 7] [--tag 正面]
```

- `--days`：查询最近 N 天
- `--tag`：按标签筛选
- 默认显示最近 7 天

### 删除照片

```bash
python scripts/body_photo_tracker.py delete <id>
```

- 同时删除数据库记录和文件

### 修改标签

```bash
python scripts/body_photo_tracker.py tag <id> <new_tag>
```

### 生成 GIF

```bash
# 指定日期范围
python scripts/body_photo_tracker.py gif --tag <标签> --start 2026-01-01 --end 2026-05-30 [--output <output.gif>]

# 最近 N 天
python scripts/body_photo_tracker.py gif --tag <标签> --days 90 [--output <output.gif>]
```

- 两种方式二选一，`--start/--end` 优先级高于 `--days`
- 输出到 `CALORIE_PHOTOS_DIR/gifs/` 子目录
- 依赖 Pillow 库

## 唤醒词与 AI 路由

| 唤醒词 | 功能 | CLI |
|--------|------|-----|
| 记身材照 | 记录身材照片（支持批量） | `body_photo_tracker.py add` |
| 查身材照 | 查看照片历史 | `body_photo_tracker.py list` |
| 删身材照 | 删除照片 | `body_photo_tracker.py delete` |
| 改照片标签 | 修改照片标签 | `body_photo_tracker.py tag` |

### AI 路由流程

**记身材照**：
1. 用户发送照片 + 说明角度
2. AI 调用 `add <photo_path> --tag <标签>`
3. 返回确认信息

**查身材照**：
1. 解析查询条件（日期/标签）
2. 调用 `list --days N --tag <标签>`
3. 展示照片列表

**生成 GIF**：
1. 用户说"生成身材变化 GIF"或"对比身材照"
2. 解析：标签 + 时间范围
3. 调用 `gif --tag <标签> --start <date> --end <date>`
4. 返回 GIF 文件路径

## 文件清单

### 新增文件

- `scripts/body_photo_tracker.py` — 主脚本
- `references/body_photos_schema.md` — 数据库文档

### 修改文件

- `SKILL.md` — 添加唤醒词和功能说明
- `references/database_schema.md` — 添加 body_photos 表
- `config-calorie.ts` — 添加新表配置
- `卡路里.html` — 添加身材照片页面

## 与现有功能联动

- **体重关联**：通过时间戳关联 `weight_log` 表中最近的体重记录
- **健康报告**：dashboard 可增加"身材照片"维度
- **Lint 检查**：可增加"照片新鲜度"检查

## 验证方式

1. 运行 `python scripts/body_photo_tracker.py` 确认脚本可执行
2. 测试添加照片、查询、删除、标签修改功能
3. 测试 GIF 生成功能
4. 检查 HTML 页面是否正常显示
