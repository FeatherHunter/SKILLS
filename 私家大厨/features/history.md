# 烹饪历史

> 触发词："做了几次"、"评分"、"历史"、"反馈"、"复盘"

---

## 功能说明

记录每次做菜的经历，查看历史，统计评分。

**字段**：
- cook_date：烹饪日期
- cook_sequence：第几次做这道菜
- rating：评分（1-5）
- feedback：本次反馈

---

## 交互场景

### 记录做菜
```
用户：今天做了宫保虾球，评分4分，盐放多了
AI：好的，记录本次烹饪：

【宫保虾球】
- 日期：2025-07-25
- 次数：第3次做
- 评分：4.0
- 反馈：盐放多了

确认吗？说"对"执行。

执行后：
- recipes.status 自动变为"已做"（若原为"未做"）
- 如评分高，可建议更新为"熟练"
```

### 查看历史
```
用户：宫保虾球做了几次？
AI：【宫保虾球 - 烹饪历史】

共做过 3 次：
1. 2025-07-20 第1次 评分4.0 反馈：虾炸过头了
2. 2025-07-22 第2次 评分4.5 反馈：火候控制好了
3. 2025-07-25 第3次 评分4.0 反馈：盐放多了

平均评分：4.2
```

### 查看某次的反馈
```
用户：上次做宫保虾球的反馈是什么？
AI：上次（2025-07-25）反馈：盐放多了
```

---

## 命令参考

```bash
# 记录做菜
python scripts/history_manager.py add <recipe_id> --cook_date 2025-07-25 --rating 4.0 --feedback "盐放多了"

# 查看历史
python scripts/history_manager.py list <recipe_id>

# 统计
python scripts/history_manager.py stats <recipe_id>

# 更新记录
python scripts/history_manager.py update <history_id> --rating 4.5 --feedback "调整了盐量"
```

---

## 状态更新规则

| 条件 | recipes.status 更新 |
|------|-------------------|
| 首次记录 | 未做 → 已做 |
| 做3次以上且平均评分≥4 | 已做 → 熟练 |

---

## 参考

- 表结构：references/database_schema.md
- 命令行参考：references/commands.md