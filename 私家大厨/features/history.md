# 烹饪历史

> 触发词："做了几次"、"评分多少"、"历史记录"、"反馈"、"复盘"、"记录一下今天做的菜"

---

## 功能说明

记录用户做菜的历史，包括：
- 烹饪日期
- 评分（1-5分）
- 用户反馈/备注

可用于：
- 追踪某道菜做了多少次
- 查看平均评分
- 复盘改进

---

## AI调用规范

### 调用任何manager前，必须：

1. **展示完整参数示例** — 让用户知道这条命令会用哪些参数
2. **对未提供字段进行合理推测** — 基于菜系特点/常见值/烹饪逻辑
3. **推测不出时询问用户** — 不能留空不填

---

## 使用场景

### 记录做菜
```
用户：今天做了宫保虾球，评分4.5，反馈是虾很Q弹
AI：执行命令：
python scripts/history_manager.py add <recipe_id> \
  --cook_date 2026-05-15 \
  --rating 4.5 \
  --feedback "虾很Q弹，下次可以少放点盐"

✅ 烹饪记录添加成功！
   食谱：宫保虾球
   日期：2026-05-15
   第3次做
   评分：4.5
```

### 查看历史
```
用户：宫保虾球做过几次了？
AI：执行命令：
python scripts/history_manager.py list <recipe_id>

宫保虾球 - 烹饪历史：
  2026-05-15 第3次 评分4.5「虾很Q弹」
  2026-05-10 第2次 评分4.0「盐放多了」
  2026-05-01 第1次 评分4.2「第一次做，成功！」
```

### 查看统计
```
用户：宫保虾球的平均评分是多少？
AI：执行命令：
python scripts/history_manager.py stats <recipe_id>

宫保虾球 - 烹饪统计：
  总次数：3次
  平均评分：4.23分
  最高评分：4.5分
  最低评分：4.0分
  最近反馈："虾很Q弹"
```

### 更新记录
```
用户：把上次宫保虾球的评分改成4.0
AI：执行命令：
python scripts/history_manager.py update <history_id> --rating 4.0

✅ 记录更新成功！
```

---

## 命令参考（完整参数）

```bash
# 记录做菜（完整参数）
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

# 查看历史（完整参数）
python scripts/history_manager.py list <recipe_id>

# 示例
python scripts/history_manager.py list 8f3b435b-...

# 统计（完整参数）
python scripts/history_manager.py stats <recipe_id>

# 示例
python scripts/history_manager.py stats 8f3b435b-...

# 更新记录（完整参数）
python scripts/history_manager.py update <history_id> \
  --rating 新评分 \
  --feedback 新反馈

# 参数说明：
#   <history_id>              必需：历史记录ID
#   --rating                  可选：新评分（1-5）
#   --feedback                可选：新反馈

# 示例（完整）：
python scripts/history_manager.py update "history_uuid" \
  --rating 4.0 \
  --feedback "调整了盐量，味道更好"

# 示例（简单）：
python scripts/history_manager.py update "history_uuid" --rating 4.0
```

---

## 字段说明

| 字段 | 说明 | 推测规则 |
|------|------|---------|
| cook_date | 烹饪日期 | 默认今天（自动获取） |
| rating | 评分（1-5） | 用户提供时填，否则留空 |
| feedback | 用户反馈 | 用户提供时填，否则留空 |

---

## 评分参考

| 评分 | 说明 |
|------|------|
| 5.0 | 完美，超出预期 |
| 4.5 | 很好，符合预期 |
| 4.0 | 好，基本符合 |
| 3.5 | 还可以，有小问题 |
| 3.0 | 一般，问题较多 |
| < 3.0 | 失败，需要改进 |

---

## 参考

- 分类参考：references/categories.md
- 命令行参考：references/commands.md
- 表结构：references/database_schema.md