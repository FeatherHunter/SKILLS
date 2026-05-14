# 私家大厨 - 分析接口文档

> 版本：v1.0
> 说明：私家大厨技能提供的分析功能接口

---

## 📊 分析功能一览

| 分析类型 | 函数名 | 说明 |
|---------|--------|------|
| 食谱统计 | `recipe_stats()` | 食谱总数/已完成/熟练 |
| 热度分析 | `recipe_popularity()` | 最常做的菜TOP10 |
| 口味分析 | `flavor_analysis()` | 偏好口味分布 |
| 热量追踪 | `calorie_summary()` | 日/周/月热量汇总 |
| 采购分析 | `shopping_analysis()` | 采购频次统计 |
| 技法分布 | `technique_distribution()` | 技法使用统计 |
| 季节分析 | `season_analysis()` | 各季节做菜分布 |
| 成本分析 | `cost_analysis()` | 成本统计 |

---

## 📝 接口详情

### recipe_stats()

返回整体食谱统计信息。

**返回示例**：
```json
{
  "total": 959,
  "by_status": {"未做": 800, "已做": 150, "熟练": 9},
  "by_difficulty": {"简单": 300, "中等": 500, "困难": 150, "大师": 9},
  "by_cuisine": {"川菜": 200, "粤菜": 180, "湘菜": 120, ...}
}
```

---

### recipe_popularity(start_date, end_date)

返回指定时间段内最常做的菜。

**参数**：
- `start_date`: 开始日期 (YYYY-MM-DD)
- `end_date`: 结束日期 (YYYY-MM-DD)

**返回示例**：
```json
{
  "top_recipes": [
    {"name": "蒜蓉蒸排骨", "count": 5, "avg_rating": 4.2},
    {"name": "三杯鸡", "count": 3, "avg_rating": 4.5}
  ],
  "total_cooks": 45
}
```

---

### flavor_analysis(start_date, end_date)

返回口味偏好分析。

**返回示例**：
```json
{
  "flavor_distribution": [
    {"flavor": "麻辣", "count": 150, "percentage": 35},
    {"flavor": "咸鲜", "count": 120, "percentage": 28}
  ],
  "insight": "你偏好重口味，麻辣占比最高"
}
```

---

### calorie_summary(date)

返回指定日期的热量汇总。

**返回示例**：
```json
{
  "date": "2026-05-13",
  "total_calories": 1850,
  "meals": {
    "breakfast": {"calories": 450, "recipes": ["鸡蛋饼", "豆浆"]},
    "lunch": {"calories": 650, "recipes": ["蒜蓉蒸排骨"]},
    "dinner": {"calories": 750, "recipes": ["三杯鸡", "炒青菜"]}
  },
  "vs_goal": {
    "goal": 2000,
    "percentage": 92.5
  }
}
```

---

### shopping_analysis(start_date, end_date)

返回采购分析。

**返回示例**：
```json
{
  "total_spend": 2500,
  "by_category": {
    "肉类": 1200,
    "蔬菜": 500,
    "调料": 300,
    "海鲜": 500
  },
  "frequent_items": [
    {"name": "排骨", "count": 5},
    {"name": "鸡翅", "count": 4}
  ]
}
```

---

### technique_distribution()

返回技法使用分布。

**返回示例**：
```json
{
  "techniques": [
    {"code": "爆炒", "count": 150, "recipes": ["宫保虾球", "辣子鸡"]},
    {"code": "滑炒", "count": 80, "recipes": ["鱼香肉丝", "滑蛋牛肉"]},
    {"code": "蒸", "count": 60, "recipes": ["蒜蓉蒸排骨", "清蒸鱼"]}
  ],
  "unmastered": ["抓炒", "颠勺"]
}
```

---

### season_analysis(year)

返回季节性做菜分析。

**返回示例**：
```json
{
  "spring": {"count": 45, "top_recipes": ["香椿炒蛋", "春笋烧肉"]},
  "summer": {"count": 38, "top_recipes": ["凉拌黄瓜", "冷面"]},
  "autumn": {"count": 52, "top_recipes": ["大闸蟹", "板栗烧鸡"]},
  "winter": {"count": 60, "top_recipes": ["火锅", "羊肉汤"]}
}
```

---

### cost_analysis(start_date, end_date)

返回成本分析。

**返回示例**：
```json
{
  "total_cost": 3500,
  "avg_per_meal": 78.5,
  "by_cuisine": {
    "川菜": 1200,
    "粤菜": 800,
    "西餐": 600
  },
  "high_cost_recipes": [
    {"name": "佛跳墙", "cost": 200},
    {"name": "龙虾", "cost": 180}
  ]
}
```

---

## 🔗 调用示例

```python
# 在AI处理用户请求时调用
from scripts.analysis import recipe_stats, flavor_analysis

stats = recipe_stats()
print(f"你已有 {stats['total']} 道食谱")

analysis = flavor_analysis('2026-04-01', '2026-05-13')
print(f"你的口味偏好: {analysis['insight']}")
```

---

## 📋 未来扩展

- [ ] `nutrient_trend()` - 营养素趋势分析
- [ ] `meal_plan_suggestion()` - 膳食建议
- [ ] `recipe_compare()` - 两道菜对比分析
- [ ] `cooking_efficiency()` - 烹饪效率分析