# 分析函数接口文档

## 四大统一入口

### 1. weight_analysis — 体重变化分析

```python
weight_analysis(start_date, end_date=None, analysis_type='trend')
```

| analysis_type | 说明 | 输出示例 |
|---|---|---|
| `'trend'` | 趋势分析 | 均重96.2kg，日均变化0g/天，趋势平稳 |
| `'compare'` | 同期对比 | 本期vs上期均重对比，变化量 |
| `'milestone'` | 目标进度 | 距目标26.8kg，预计达成2026-11-25 |
| `'volatility'` | 波动分析 | 日间±0.15kg，异常记录标记 |

### 2. diet_analysis — 饮食分析

```python
diet_analysis(start_date, end_date=None, analysis_type='calorie_trend')
```

| analysis_type | 说明 | 输出示例 |
|---|---|---|
| `'calorie_trend'` | 热量趋势 | 日均1287卡，目标1800卡，合规0/3天 |
| `'macro_ratio'` | 营养素占比 | 碳水44%↑偏高，蛋白19%↓偏低 |
| `'food_ranking'` | 食物TOP榜 | 热量炸弹/低热量/频繁吃/高碳水/高蛋白 |
| `'deficit_analysis'` | 热量缺口 | 日均缺口1716卡，饮食贡献100% |

**food_ranking 支持的 category：**
- `'high_calorie'` — 热量炸弹榜
- `'low_calorie'` — 低热量健康榜
- `'frequent'` — 频繁吃榜
- `'high_carb'` — 高碳水榜
- `'high_protein'` — 高蛋白榜

### 3. exercise_analysis — 运动分析

```python
exercise_analysis(start_date, end_date=None, analysis_type='exercise_trend')
```

| analysis_type | 说明 | 输出示例 |
|---|---|---|
| `'exercise_trend'` | 运动趋势 | 运动天数12/30天，日均消耗160卡 |
| `'type_breakdown'` | 类型分布 | 骑行消耗60%，跑步25%，力量15% |
| `'deficit_contribution'` | 缺口贡献 | 饮食缺口78%，运动缺口22% |

### 4. dashboard — 综合报告

```python
dashboard(start_date, end_date=None)
```

整合：体重趋势 + 热量趋势 + 运动趋势 + 热量缺口，输出四维度仪表盘。

---

## 调用示例

```python
# 体重趋势
weight_analysis('2026-05-01', '2026-05-09', 'trend')

# 食物热量榜（周榜）
diet_analysis('2026-05-02', '2026-05-09', 'food_ranking')

# 运动类型分布
exercise_analysis('2026-05-01', '2026-05-09', 'type_breakdown')

# 综合报告
dashboard('2026-05-01', '2026-05-09')
```

---

## 时间参数说明

- `end_date=None` 时，默认 `start_date` 为单日查询
- 日期格式：`'YYYY-MM-DD'`，如 `'2026-05-09'`
- 支持跨月/跨年查询