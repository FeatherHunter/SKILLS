# HTML 模板清单 · 卡路里 Skill

> 2026-07-23 起，按《预置 HTML + 注入数据指导手册》第一性原理实现："模板稳定、数据流动、样式预置、内容注入"。

## 已实现模板（6 个）

| 模板 | 大小 | 唤醒词 | 数据源 | 渲染器 |
|---|---|---|---|---|
| `templates/contraindication_report.html` | 12 KB | 扫禁忌 | `scan_contraindications.py --format json` | `scripts/render_contraindication.py` |
| `templates/review_template.html` | 15 KB | 复盘（含今日/本周/本月/本年/日期范围） | `review_cli.py gen` enriched JSON | `scripts/render_review.py` |
| `templates/workout_plan_view.html` | 12 KB | 查健身计划 | DB 直接 query | `scripts/render_workout_plan.py` |
| `templates/health_dashboard.html` | 15 KB | 查健康报告 | `analysis.dashboard(as_dict=True)` | `scripts/render_health_dashboard.py` |
| `templates/food_ranking.html` | 13 KB | 5 个食物排行（1 模板 5 榜单） | `analysis.diet_food_ranking` × 5 | `scripts/render_food_ranking.py` |
| `templates/exercise_review.html` | 15 KB | 复盘训练 | `exercise_review.py --format json` | `scripts/render_exercise_review_html.py` |

## 通用调用方式

```bash
# 1. 调 CLI / 分析函数拿 JSON
python3 analysis/dashboard.py 2026-07-13 2026-07-19  # 或带 --format json

# 2. 调渲染器（subprocess 调 CLI + 注入模板）
python3 scripts/render_<feature>.py [--range X:Y | --days N] [--output <path>]

# 3. 默认输出到 /tmp/<feature>_<range>.html
#    也可加 --output 指定路径（如同步到 D 盘）
```

## 模板设计原则（与《手册》第 7 节对齐）

- **占位符唯一**：每个模板含 `<!--INJECT-DATA-->` 恰好 1 次（注入器会校验）
- **首屏**：标题 + 状态徽章 + 关键 KPI 卡片（4-6 个）
- **主体**：按维度分组（折叠 `details/summary` 让长内容可折叠）
- **尾部**：复制回 AI 按钮（让用户回填数据）
- **空态 / 错误态**：明确显示（不要白屏）
- **响应式**：桌面 / 平板 / 手机（375px）都要正常显示

## 数据契约

```json
{
  "status": "ok" | "warn" | "error",
  "data": { ... },
  "message": "..."
}
```

所有 `status` 严格用 `"ok" | "warn" | "error"`（与《优秀 Skill 指导手册》第④层接口层规范一致）。

## 注入实现

渲染器统一模式（`render_*.py`）：

```python
# 1. 读模板
template = TEMPLATE_PATH.read_text(encoding='utf-8')
if template.count('<!--INJECT-DATA-->') != 1:
    raise ValueError('占位符必须唯一')

# 2. JSON 序列化 + </ 转义防断标签
payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')

# 3. 注入（替换占位符 1 次）
injected = template.replace('<!--INJECT-DATA-->',
    f'<script>window.__DATA__ = {payload};</script>', 1)

# 4. 输出到文件（原模板不动）
out_path.write_text(injected, encoding='utf-8')
```

## 1 模板多参数（food_ranking 案例）

5 个榜单共用 1 个模板 + 5 个参数：

```python
# 渲染器拉 5 次数据
data = {
    'high_calorie': diet_food_ranking(as_dict=True, category='high_calorie'),
    'low_calorie':  diet_food_ranking(as_dict=True, category='low_calorie'),
    'frequent':     diet_food_ranking(as_dict=True, category='frequent'),
    'high_carb':    diet_food_ranking(as_dict=True, category='high_carb'),
    'high_protein': diet_food_ranking(as_dict=True, category='high_protein'),
}

# 模板按 category 切换
renderCategory(t.dataset.cat)  // tab.onclick
```

## 未来扩展

- **设计系统统一**：6 个模板的色板、字体、阴影、圆角目前手工同步
- **CI 校验**：可加 GitHub Action 自动跑 `占位符数量 == 1` 校验
- **跨 Skill 复用**：卡路里模板的色板可抽到 `templates/_shared.css`

写于 2026-07-23
