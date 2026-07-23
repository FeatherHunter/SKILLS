# Phase G · 卡路里 Skill 下一阶段开发计划

> **起源**：未覆盖唤醒词优先级_2026-07-23.html（AI 协同约束修正版）
> **核心约束**：原则 10（AI 协同 · 所有过程型 HTML 必有"复制 prompt"按钮）
> **总预估**：~3 周（Phase E 1 周 + Phase F 2 周 + Phase G 按需）

---

## 📋 7 项 TODO（按 ROI 排序）

### 🔴 Phase E · S 级（必做 · 1 周）

- [ ] **G1. 卡路里主面板（统一入口）** · 🟢 易 · ROI ★★★★★
  - 模板：`templates/home_dashboard.html`
  - 渲染器：`scripts/render_home.py`
  - 数据源：4 个 analysis 函数（dashboard）+ 当日 daily_intake + weight_log
  - 验收：1 屏看清 4 维 KPI + 当日待办 + 最近趋势（无 AI 互动需求，结果型）

- [ ] **G2. 拍营养表 · AI 识别预览向导** · 🟠 中 · ROI ★★★★★
  - 模板：`templates/nutrition_label_wizard.html`
  - 渲染器：`scripts/render_nutrition_label.py`
  - 数据源：`mmx vision describe` 输出
  - 验收：可编辑表单 + **2 个复制按钮**（采纳短确认 / 修改后完整 prompt）
  - 依赖：mmx vision describe 已集成

### 🟠 Phase F · A 级（强烈推荐 · 2 周）

- [ ] **G3. 4 步流程进度可视化** · 🟠 中 · ROI ★★★★ · 复选☑
  - 模板：`templates/process_progress.html`
  - 渲染器：`scripts/render_process_progress.py`
  - 数据源：sync_plan / 落地健身计划 / 卡路里同步的执行步骤状态
  - 验收：4 步进度展示 + 当前完成的步骤 + 复制"从哪步继续" prompt

- [ ] **G4. 制定健身计划 · 4 步 wizard** · 🔴 难 · ROI ★★★★ · 复选☑
  - 模板：`templates/plan_builder_wizard.html`
  - 渲染器：`scripts/render_plan_builder.py`
  - 数据源：plan_generator.py 输出
  - 验收：4 轮决策预览（基线/结构/精细/动作）+ 采纳 / 修改后复制 plan JSON

- [ ] **G5. 扫禁忌 → 替代建议 + 修改 prompt** · 🔴 难 · ROI ★★★★ · 复选☑
  - 模板：升级 `templates/contraindication_report.html` → v2
  - 渲染器：升级 `scripts/render_contraindication.py`
  - 数据源：scanner.py + SAFE_VARIANTS 白名单
  - 验收：每个 error 旁附"安全替代"按钮 + 复制修改指令

- [ ] **G6. 营养/体重目标配置卡片** · 🟠 中 · ROI ★★★ · 复选☑
  - 模板：`templates/goal_config.html`
  - 渲染器：`scripts/render_goal_config.py`
  - 数据源：nutrition_goal.get_nutrition_goal + weight_goal.get_weight_goal
  - 验收：5 个 slider + mini chart 显示"昨日 vs 新目标"+ 复制新配置 prompt

### 🟢 Phase G · B 级（按需）

- [ ] **G7. 记体重 · 实时趋势叠加** · 🟢 易 · ROI ★★★ · 复选☑
  - 模板：`templates/weight_log_receipt.html`
  - 渲染器：`scripts/render_weight_receipt.py`
  - 数据源：weight_trend + 最新一条 weight_log
  - 验收：录入后立即看到"趋势图 + 新点高亮"（回执型，无 AI 互动）

---

## ⚙️ 通用 SOP（每项必走 6 步）

1. **CLI JSON 化检查** — 是否支持 `as_dict=True`，没有就先重构
2. **写模板** `templates/xxx.html` — 含 `<!--INJECT-DATA-->` + 2 个复制按钮（原则 10）
3. **写渲染器** `scripts/render_xxx.py` — subprocess + 占位符校验 + `</` 转义
4. **实测链路** — Chrome 打开 → 复制 → 粘贴 → AI 执行端到端测试
5. **同步文档** — SKILL.md + 卡路里.html + 案例/04_架构师原则.md（如新增原则）
6. **git commit** — `[卡路里]` 前缀，按 Phase 一个 commit

---

## ✅ 验收标准（每项必达 7/7）

- [ ] 占位符 `<!--INJECT-DATA-->` 唯一
- [ ] 5 状态 fallback（正常 / 空 / 缺数据 / 错误 / 离线）
- [ ] `</` 转义防断标签
- [ ] 2 个复制按钮（采纳 + 修改）
- [ ] 移动端 375px 可读
- [ ] 飞书 embed 也能渲染（无外部资源依赖）
- [ ] Chrome 打开 review 通过

---

## 📊 进度跟踪

| Task | 状态 | 起始日期 | 完成日期 | Commit |
|---|---|---|---|---|
| G1 卡路里主面板 | ⏳ 待开工 | - | - | - |
| G2 拍营养表 wizard | ⏳ 待开工 | - | - | - |
| G3 4 步流程进度 | ⏳ 待开工 | - | - | - |
| G4 制定计划 wizard | ⏳ 待开工 | - | - | - |
| G5 扫禁忌可改版 | ⏳ 待开工 | - | - | - |
| G6 目标配置 slider | ⏳ 待开工 | - | - | - |
| G7 记体重回执 | ⏳ 待开工 | - | - | - |

**状态枚举**：⏳ 待开工 · 🚧 进行中 · ✅ 已完成 · ❌ 阻塞

---

## 📐 复用资源（每次任务前必看）

- `D:\2Study\StudyNotes\SKILLS\模板HTML并注入数据\案例\04_架构师原则.md` ← 11 条原则（必读）
- `D:\2Study\StudyNotes\SKILLS\模板HTML并注入数据\案例\01_卡路里Skill改造案例.md` ← 4 Phase 改造 case study
- `D:\2Study\StudyNotes\SKILLS\模板HTML并注入数据\案例\03_模板设计原则抽象.md` ← CSS / Injector 共享方案

---

## 🎯 预期收益

- **唤醒词覆盖**：8/60+ (13%) → **15/60+ (~25%)**
- **架构统一**：所有过程型 HTML 都遵循原则 10（复用 prompt 模板）
- **可迁移性**：8 个新模板可作为其他 Skill 改造的现成模板

## 💡 备注

如果有任何 task 完成，更新 checkbox + 进度表 + commit `[卡路里]`。
任何问题 → 先查 04_架构师原则.md，可能已经有答案。

---

写于 2026-07-23 · 待开工
