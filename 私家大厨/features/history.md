# 烹饪历史

> 路由：SKILL.md 用例5 → features/history.md

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

**遵循规范**：SKILL.md 中的"AI使用规范"和"字段推测规则"。

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
用户：宫保虾球平均评分多少？
AI：执行命令：
    python scripts/history_manager.py stats <recipe_id>

    宫保虾球 - 烹饪统计：
    总次数：3次
    平均评分：4.23分
    最高评分：4.5分（2026-05-15）
    最低评分：4.0分（2026-05-10）
```

### 更新记录

```
用户：把上次宫保虾球的评分改成4.0
AI：执行命令：
    python scripts/history_manager.py update <history_id> --rating 4.0

    ✅ 记录更新成功！
```

---

## 命令参考

```bash
# 记录做菜
python scripts/history_manager.py add <recipe_id> \
  --cook_date 2026-05-15 \
  --rating 4.5 \
  --feedback "味道不错，虾很Q弹"

# 参数说明：
#   <recipe_id>               必需：食谱ID
#   --cook_date               可选：烹饪日期，格式YYYY-MM-DD，默认今天
#   --rating                  可选：评分（1-5）
#   --feedback                可选：用户反馈/备注

# 记录做菜（简单用法，默认今天，默认无反馈）
python scripts/history_manager.py add <recipe_id> --rating 4.5

# 查看历史
python scripts/history_manager.py list <recipe_id>

# 示例
python scripts/history_manager.py list 宫保虾球

# 统计
python scripts/history_manager.py stats <recipe_id>

# 示例
python scripts/history_manager.py stats 宫保虾球

# 输出格式：
#   宫保虾球 - 烹饪统计：
#   总次数：3次
#   平均评分：4.23分
#   最高评分：4.5分（日期）
#   最低评分：4.0分（日期）

# 更新记录
python scripts/history_manager.py update <history_id> \
  --rating 4.0 \
  --feedback "调整了盐量，味道更好"

# 参数说明：
#   <history_id>              必需：历史记录ID
#   --rating                  可选：新评分（1-5）
#   --feedback                可选：新反馈

# 更新记录（简单用法，只改评分）
python scripts/history_manager.py update <history_id> --rating 4.0
```

---

## 字段说明

| 字段 | 说明 | 推测规则 |
|------|------|---------|
| cook_date | 烹饪日期 | 用户有提供→用用户的；用户未提供→默认为当天 |
| rating | 评分（1-5） | 用户有提供→用用户的；用户未提供→询问用户 |
| feedback | 用户反馈 | 用户有提供→用用户的；用户未提供→询问用户 |

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

- 分类参考：`references/categories.md`
- 命令行参考：`references/commands.md`
- 表结构：`references/database_schema.md`