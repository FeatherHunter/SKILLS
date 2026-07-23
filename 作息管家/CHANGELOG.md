# 作息管家 CHANGELOG

> 记录对用户有感知的变更。遵守《优秀Skill指导手册》§5.2"改完代码 → 改 SKILL.md → 改 HTML → 改 changelog(顺序不能乱)"。

---

## [Unreleased] · 2026-07-23

### 🚀 重大变更:作息记录查询 → HTML 多模板报告(5 模板 8 命令)

**这是破坏性变更,原因**:用户主动删除 `作息管家/reports/` 目录(7:30 cron 报告链路物理消失),原 27 份历史作息报告 HTML 不可访问。本次重构为「按需生成、单文件 HTML 落到 SKILLS_DB_PATH 下」模式。

### 移除(Removed)

- `scripts/_gen_report_*.py` × 10(死代码,旧 7:30 cron 报告生成器,产物写到 /tmp/report_data_*.json 中间文件)
- `scripts/_render_report_*.py` × 9(死代码,旧 HTML 渲染器)
- `scripts/__orphan_check.py`(死代码,旧飞书孤儿审计)
- `templates/schedule_record_report.html`(4 段单模板,被 T1-T5 替代)
- `作息管家/reports/` 目录(用户主动删除,含 27 份历史报告)

### 新增(Added)

- `scripts/calculations.py` (376 行) — 共享派生层:健康分/异常检测/AI 钩子生成/类别深挖
- `templates/_record_styles.css` (6.5KB) — 5 模板共享样式表
- `templates/_record_engine.js` (16KB) — 5 模板共享 JS 引擎,按 `meta.mode` 分发到 5 个 render 函数
- `templates/schedule_record_day.html` (T1 单日)
- `templates/schedule_record_range.html` (T2 区间)
- `templates/schedule_record_compare.html` (T3 对比)
- `templates/schedule_record_category.html` (T4 类别深挖)
- `templates/schedule_record_anomaly.html` (T5 异常检测)

### 新增命令(New CLI)

| 命令 | 模板 | 路径 |
|------|------|------|
| `render-record-day <date>` | T1 | `record/day/<date>_record_day.html` |
| `render-record-range <start> <end>` | T2 | `record/range/<start>_to_<end>_record_range.html` |
| `render-record-compare <labelA> <startA> <endA> <labelB> <startB> <endB>` | T3 | `record/compare/<labelA>_vs_<labelB>_record_compare.html` |
| `render-record-compare-months <YYYY-MM> <YYYY-MM>` | T3 简写 | 同上 |
| `render-record-category <date> <cat>` | T4 | `record/category/<cat>_<date>_to_<date>_record_category.html` |
| `render-record-category-range <start> <end> <cat>` | T4 | `record/category/<cat>_<start>_to_<end>_record_category.html` |
| `render-record-anomaly [--window N]` | T5 | `record/anomaly/<today>_w<N>_record_anomaly.html` |
| `render-record-report <date>` | (兼容) | 等价 render-record-day |

### 路径硬绑(强制)

所有输出**强制**写到 `SKILLS_DB_PATH/schedule_html/record/<子目录>/...`,**不传 `--out`**。子目录( `day` / `range` / `compare` / `category` / `anomaly` )**必须已存在** — 不静默创建,报错文案带字段名+当前值+修复建议。

### 兼容(Compatibility)

- `render-record-report <date>` 命令保留,等价于 `render-record-day`,`mode="record-report"` 在 `template_map` 映射到 `schedule_record_day.html`。
- 旧 7 个文本 CLI 命令(list/detail/summary/timeline/report/range/status)**完全不动**。

### 5 模板设计的"3 层架构"

- **L1 速读层(5 秒)**:4 张数字卡(活跃分类/总时长/健康分/睡眠),健康分 0-100 红/黄/绿
- **L2 趋势层(30 秒)**:分类进度条 + 24h 时间轴 + 7 维趋势折线 SVG + 24h×N 天热力图 + 7 维雷达 SVG
- **L3 决策层(3 分钟)**:**AI 思考钩子卡**(模板自带 `data.ai_questions[]` 字段,AI 看后能直接追问用户)

### 模板手册 §7 5 状态

所有 5 模板均实现 5 状态:正常 / 空 / 错 / 离线(常驻 banner),**缺数据态** 暂未与"空态"区分(MEDIUM 缺陷待修)。

---

## 待修缺陷(下个 release)

参考 `D:\2Study\StudyNotes\SKILLS\html\review_5710525.html`(对抗式审查报告),按 ROI 修复:

1. **C1 写 CHANGELOG** ✅(本文件)
2. **C2 抄回 13 维业务派生**(meal_records / work_records / leisure_records ...)
3. **H5 删 SKILL.md §3.1.2** 旧路径
4. **H4 更新 references/CLI命令.md** 加 8 个新命令
5. **M6 XSS `</script>` 转义修复**
6. M1-M12 + L1-L10 剩余次要缺陷
