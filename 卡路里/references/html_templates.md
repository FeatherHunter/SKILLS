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
```

## 📌 输出目录与命名规范(2026-07-24 起 · 手册 §4.1)

依据《预置HTML+注入数据指导手册》§4.1(2026-07-24 加,跨Skill通用):

| 项 | 规则 |
|---|---|
| 输出目录 | `HTML_DIR = DATA_DIR / calorie_html/`<br>(与 `calorie_data.db` 同级,跟随 `$SKILLS_DB_PATH`,fallback `D:/.db/`) |
| 文件名 | `<command_name>_<YYYYMMDD>_<HHMMSS>[_<N>].html`<br>同秒冲突自动追加 `_2` / `_3` |
| ASCII 短码 | `calorie` |
| 工具模块 | `scripts/html_paths.py`:`html_dir()` / `html_name()` / `html_path()` |
| `--output` | 可显式覆盖到任意路径(共享磁盘 / 飞书云盘等) |

### 不再使用的旧规则
- ❌ `/tmp/<feature>_<range>.html` — 目录不属于数据所在,跨平台不一致
- ❌ 覆盖式写入 `卡路里/健身计划.html` — 不留历史快照
- ❌ `_<range>` / `_<part>` / `_<input>.html` 中缀 — 无 _N 冲突保护

### 实际输出示例(WSL)

```
/mnt/d/2Study/StudyNotes/.db/calorie_html/home_dashboard_20260724_115038.html
/mnt/d/2Study/StudyNotes/.db/calorie_html/weight_log_receipt_mock_weight_receipt_20260724_115123.html
/mnt/d/2Study/StudyNotes/.db/calorie_html/goal_config_mock_goal_config_20260724_115123.html
/mnt/d/2Study/StudyNotes/.db/calorie_html/contradiction_report_腰_20260724_120000_2.html  (同秒第 2 次)
```

### 历史快照保留

- `卡路里/健身计划.html` (2026-07-20 末次内容,118 KB)— render_workout_plan.py 旧默认输出
  B 阶段(commit `292c552`)后已改为 calorie_html/<command>_<TS>.html
  本快照仅作历史参考,后续用 `python scripts/render_workout_plan.py` 生成新 HTML 在 `calorie_html/`

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
