# 数据库结构

## 环境变量配置

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `SKILLS_DB_PATH` | 数据库文件所在目录 | 技能目录/.db/ |
| `HOME_PHOTOS_DIR` | 照片存储目录 | 技能目录/photos/ |

**路径存储规则**：数据库 `photo` 字段存储相对路径，完整路径 = 照片目录 + 相对路径

---

## 表1：items（物品表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| name | TEXT | 物品名称 |
| category | TEXT | 大类（参考 references/categories.md） |
| owner | TEXT | 所有者（默认"使用者"） |
| purchase_price | REAL | 单价（元/件），按单瓶/单袋/单盒记，方便计算当前库存价值 |
| remark | TEXT | 备注 |
| photo | TEXT | 图片路径 |
| access_count | INTEGER | 被访问次数 |
| last_accessed_at | TIMESTAMP | 最后访问时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

> 注意：location、quantity、purchase_date、expiration_date 字段已移除，改为由 item_locations 表管理（每个位置独立记录）

---

## 表2：item_locations（物品位置表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| item_id | INTEGER | 关联 items.id |
| location | TEXT | 存放位置（路径格式，如 `客厅/冰箱/上层`） |
| quantity | INTEGER | 该位置的数量 |
| reason | TEXT | 原因（可选，如"已开封需冷藏"） |
| location_status | TEXT | 位置状态（在家/备用/借用中等） |
| purchase_date | TEXT | 购买日期（YYYY-MM-DD，可空） |
| expiration_date | TEXT | 过期日期（YYYY-MM-DD，可空） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

**特性**：
- 支持同一物品分多个位置存放，每个位置独立记录购买/过期日期
- quantity=0 时该记录自动删除，不保留空位置

---

## 表3：item_tags（标签表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| item_id | INTEGER | 关联 items.id |
| tag | TEXT | 单个标签 |

**特性**：
- 同一物品同一标签不可重复（UNIQUE约束）
- 多个物品可以有相同标签
- 搜索用精确匹配

---

## 表4：locations（位置历史表）

> ⚠️ **已删除** — 此表从未实际使用，位置 autocomplete 功能将由 item_locations 直接实现

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键自增 |
| location_path | TEXT UNIQUE | 位置路径 |
| use_count | INTEGER | 使用次数 |
| last_used | TIMESTAMP | 最后使用时间 |