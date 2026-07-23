# 案例 01 · 卡路里 Skill HTML 模板注入改造

> 写于 2026-07-23 · 卡路里 Skill · 4 Phase 完整实战记录
> 配套理论框架：[../预置HTML并注入数据指导手册.html](../预置HTML并注入数据指导手册.html)

## TL;DR

| 维度 | 数据 |
|---|---|
| **改造 Skill** | 卡路里（饮食热量/饮水/体重/运动/营养追踪） |
| **4 Phase 总耗时** | ~1 天（2026-07-23） |
| **新增模板** | 5 个（contrain / review_v2 / workout_plan / health_dashboard / food_ranking / exercise_review） |
| **重构 Python 文件** | 6 个（render_workout_plan, analysis/*.py, exercise_review.py） |
| **新增渲染器** | 6 个（render_*.py） |
| **发现 BUG** | 17 个（B-001 ~ B-407，按优先级分 3 档） |
| **总 commit 数** | 6 个（按 Phase 切，方便 revert） |

---

## 一、改造起点：为什么要做？

### 1.1 痛点

- 60+ 个唤醒词里只有"训练复盘"等极个别人工做了 HTML，其余都是 `print()` 文本
- 用户在 4 Phase 中看到的事实：
  - `analysis/dashboard()` 返回 `None`，**完全无法 JSON 化**
  - `analysis/diet_food_ranking()` 返回 `sqlite3.Row`（不可序列化）
  - `exercise_review.py` 是纯 print，无 `--format json`
  - `render_workout_plan.py` 340 行单文件，每次重写 115 KB HTML，无 `<!--INJECT-DATA-->`

### 1.2 第一性原理答案（《手册》第 1.3 节）

> **HTML 页面不是数据源，也不是业务规则层。它只是用户和数据之间的"可视化操作界面"。**

也就是说：**只解决"好看、可交互、可复用"，不解决"数据"和"规则"**。

---

## 二、4 Phase 实施

### Phase A · 扫禁忌（最小阻力先做）

**为什么先做？** CLI 已经基本合规 JSON，只差补字段 + 写模板。失败风险极低。

**A1 · 补全 CLI 字段（`scan_contraindications.py`）**：
- 加 `hits[]` 完整数组（含 `reason` / `safe_variant`）
- 加 `scanned_parts` 字段
- 加 `summary_status` 字段
- `by_movement` 聚合补 `reason` + `safe_variant`

**A2 · 新建 `templates/contraindication_report.html`**：
- 含唯一占位符 `<!--INJECT-DATA-->`
- 状态徽章 + 6 KPI 卡 + 按部位分组（折叠）

**A3 · 新建 `scripts/render_contraindication.py`**：
- `subprocess.run([...], list of args)` 列表传参（避免 PowerShell 中文乱码）
- 占位符唯一性校验
- `</` 转义防断标签

**commit**：`4ba57a4` `[卡路里] Phase A 扫禁忌 HTML 可视化`

---

### Phase B · 复盘报告 v2（数据已合规直接做）

**为什么其次？** 数据完全合规（`review_cli.py gen` 已返回结构化 JSON），只需加占位符 + 扩样式。

**B1 · `review_engine.py:derive()` 补 `anomaly_days`**：
- 4 类异常规则（intake_excess / intake_deficit / fat_excess / exercise_streak_miss）
- 基于 complete_days 排除今日污染

**B2 · 新建 `templates/review_template_v2.html`**：
- Apple 风 8 dim 卡片网格（P1 训练突出 + 紫色渐变）
- 体重 SVG 自动嵌入（算法渲染字符串）
- 一键复制回 AI

**B3 · 新建 `scripts/render_review.py`**：
- 复用 `review_cli.py gen` 的 enriched JSON（避免重复 SQL）
- 自动跳过 leading `→ ` 文本行找 JSON 起始

**commit**：`82b67e4` `[卡路里] Phase B 复盘报告 v2 HTML`

---

### Phase C · render_workout_plan 规范化（已有 HTML 改造为合规）

**为什么？** 这是**唯一已实现的 HTML**，但不符合规范。改造为"模板 + 注入"模式作为示范。

**C1 · 拆分单文件**：
- `render_workout_plan.py`：340 → 201 行（-41%）
- `templates/workout_plan_view.html`：299 行（CSS + JS + 骨架）
- 数据契约：`{status, data:{config, weeks, review}, message}`

**commit**：`3c13bf5` `[卡路里] Phase C 健身计划 HTML 规范化`

---

### Phase D · CLI 重构 + 3 个新模板（最重 · 解锁 3 个 P0）

**为什么最后？** 3 个 P0 #1 / #3 / #4 阻塞于 CLI 不返回 JSON，必须先重 CLI 再做模板。

**D1 · analysis 10 个函数加 `as_dict=False` 参数**：
- `weight_trend / weight_compare / weight_milestone / weight_volatility`
- `diet_calorie_trend / diet_macro_ratio / diet_food_ranking / diet_deficit_analysis`
- `exercise_trend / exercise_type_breakdown / exercise_deficit_contribution`
- `dashboard` 聚合 4 维
- 4 个统一入口（`weight_analysis` 等）透传
- ✅ 向后兼容（`as_dict=False` 默认 print 行为不变）

**D2 · `exercise_review.py` 加 `--format json`**：
- 委托 `analysis.exercise.exercise_review(as_dict=True, silent=True)`

**D3 · 3 个新模板**：
| 模板 | 设计亮点 |
|---|---|
| `health_dashboard.html` | 4 维 KPI + 异常天自动派生 + 复制摘要 |
| `food_ranking.html` | **1 模板 5 榜单**（5 tab 切换） + 营养结构横向条形图 |
| `exercise_review.html` | 7 天完成率热力图（绿/黄/红/灰） + 异常天高亮 |

**D4 · 3 个新渲染器**：每个严格按 A3 的"subprocess + 占位符校验 + `</` 转义"模式。

**D5 · 文档同步**：SKILL.md 加 3 行 + 卡路里.html 顶部加通知 + 新建 `卡路里/references/html_templates.md`

**commits**（另一个并行 agent 完成核心 3 个 commit + 我加 1 个 bugfix）：
- `fc2dd47 ♻️ 重构: 卡路里 analysis 模块 as_dict 化（D1）`
- `9b31ef1 ✨ 功能: 卡路里 Phase D 新增 3 个 HTML 报告模板`
- `df366e5 🔧 杂务: 卡路里 .gitignore 增加 .bak_phase_*/`
- `1231515 🐛 修复: [卡路里] weight_trend 趋势 label 中文显示（D1 后续）`

---

## 三、17 个 BUG 汇总（按严重度）

| ID | 模块 | 描述 | 状态 |
|---|---|---|---|
| 🔴 **B-001** | `dashboard.py` | `return None` | D1 ✅ |
| 🔴 **B-002** | 4 个 trend/compare/ratio 函数 | print-only 不 return dict | D1 ✅ |
| 🔴 **B-201** | `diet_food_ranking` | 返回 `sqlite3.Row`（不可序列化） | D1 ✅ |
| 🔴 **B-301** | `exercise_review.py` | 无 `--format json` | D2 ✅ |
| 🟡 **B-103** | `review_engine.burn_summary.total_minutes=0` | 数据缺失 | 待修 |
| 🟡 **B-106** | `review_engine` | 缺 `anomaly_days` 字段（agent 派生） | B1 部分 ✅ |
| 🟡 **B-205** | `diet_food_ranking` | `low_calorie` 把 💧水 排第 1 | 待修 |
| 🟡 **B-207** | `diet_food_ranking` | 无"营养密度"指标 | 待修 |
| 🟡 **B-304** | `exercise_review` | 无 `by_severity` 聚合 | 待修 |
| 🟡 **B-305** | `exercise_review` | 完成率计算标准模糊 | 待修 |
| 🟡 **B-401** | `scanner.py` | `summary_status` 计算了但没 return | A1 ✅ |
| 🟡 **B-402** | `scanner.py` | 缺 `hits[]` 数组 | A1 ✅ |
| 🟡 **B-403** | `scanner.py` | 缺 `reason` 字段 | A1 ✅ |
| 🟡 **B-407** | `scanner.py` | 缺"替代建议"字段 | 待修 |
| 🟡 **B-501** | `weight_trend` | 趋势 label 显示英文 `up` 而不是中文 `上升` | 后续 fix ✅ |
| 🟡 **B-502** | `diet_deficit_analysis` | "饮食贡献 358%" 异常 | 待修 |
| 🟢 **B-105** | `review_engine` | `weekly_deficit` 字段命名建议通用化 | 待修 |

**修复率**：🔴 致命 4/4 ✅ | 🟡 中等 6/12 | 🟢 低 0/1

**待修 BUG**：建议下次再开一个"D1.5 清理"任务专项处理。

---

## 四、5 条核心经验（给未来 Skill 改造参考）

### 经验 1：CLI 是阻塞点，要"先重 CLI 再做模板"

- **症状**：3 个 P0（健康报告/食物排行/复盘训练）一开始就失败，因为 CLI 只 print 不 return dict
- **教训**：**永远先验证 CLI 是否能返回结构化 JSON** 再投入模板设计
- **行动**：开 Phase 前 30 分钟跑 `python3 <cli> --format json` 测试

### 经验 2：占位符 `<!--INJECT-DATA-->` 必须全文件恰好 1 次

- **症状**：多个模板最初写错位置（比如在 `<script>` 里直接用 JSON parse）
- **教训**：**模板文件被视为稳定资产**——保证占位符唯一、注入器必须有校验
- **行动**：渲染器第一行就是 `if template.count(placeholder) != 1: raise`

### 经验 3：`</` 转义防断标签

- **症状**：JSON 数据含 `</script>` 时会提前闭合
- **教训**：序列化后必须 `.replace('</', '<\\/')`
- **行动**：所有 render_*.py 都遵循这个模式

### 经验 4：subprocess 列表传参避免 PowerShell 乱码

- **症状**：从 PowerShell 调 `python xxx "中文"` 写入的是 `????`
- **教训**：用 `subprocess.run(['python', str(cli_path), ...], capture_output=True)` 列表传参
- **行动**：渲染器统一用 subprocess，不用 `os.system`

### 经验 5：1 模板多参数节省 5 倍工作量

- **成功案例**：`food_ranking.html` 服务 5 个 `category`（高热量/低热量/频繁/高碳水/高蛋白）
- **教训**：**如果多个唤醒词的数据结构相同，不要做 5 个 HTML，做 1 个 HTML + 5 个参数**
- **行动**：判断标准 — "X 个唤醒词输出字段是否一致？是 → 1 模板 + X 参数"

---

## 五、给未来 Skill 改造的 3 条硬规则

1. **改动前必答 3 问**（影响文件 / 数据迁移 / 回滚方案）—— 来自《优秀 Skill 指导手册》第④层
2. **每 Phase 一个 commit**，commit 信息含 `[技能名]` 前缀
3. **CLI 改动默认行为保持不变**（加 `as_dict=False` 参数，向后兼容）

---

## 六、时间线回顾

```
10:00 启动 Phase 0（备份 + .gitignore 准备）
11:00 Phase A1-A4（扫禁忌）
12:00 Phase B1-B4（复盘 v2）
13:00 居家管家 commit 9a09f2b（outfit_picker，刚发现）
14:00 Phase C1-C2（render_workout_plan 规范化）
15:00 自检 + 调研 + commit
16:00 Phase D1（D1 analysis as_dict）
17:00 Phase D2（exercise_review --format json）
18:00 Phase D3-D5（3 模板 + 3 渲染器 + 同步）
19:00 Bug 修复 + commit
19:30 收尾开始
```

---

写于 2026-07-23 · 基于真实 4 Phase 实战 · 配套理论：[预置HTML并注入数据指导手册.html](../预置HTML并注入数据指导手册.html)