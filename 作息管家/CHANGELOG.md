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

---

## [2026-07-23] · 第二轮清理 · 文档对齐 + 死章节 + 真废命令

**真实清理**(对抗式审查后重新评估,区分"docs 误标为废弃 vs 真的废弃"):

### docs 误标为废弃(实际在用)— 修正标签
- SKILL.md / 作息管家.html 功能速查表 #1 #2 #3 删"(废弃)"标签
  - `prepare-messages` 在 schedule_cli.py:510 实现,在 references/同步流程.md:390、references/Cron任务.md、references/CLI命令.md:40、SKILL.md §1 同步流程、__pycache__ 都被引用 — 实际**当前生效**命令
  - 修正后 #1 改"准备消息(游标分页)",#2 改"同步作息",#3 改"增量同步"

### 真废弃 — 删除
- SKILL.md 功能速查表 #10 "查作息游标" 整行 — `get_last_record_full` 是内部 Python helper,不是 CLI 命令
- SKILL.md 功能速查表 #23 #24 整行 — `Cron 0 */3 * * *`(配置定时同步) + `Cron 30 7 * * *`(配置每日报告)
  - 7:30 报告产物写 `作息管家/reports/`,目录已删 → CRON 跑必 FileNotFoundError
  - 旧 sync 脚本 (`_gen_report_*.py` / `_render_report_*.py`) 全部已删 → CRON 跑也必失败
- SKILL.md §"推荐 Cron 任务" 整章节(40 行) + references/Cron任务.md 文件 — 同上,3 个 cron 任务全部失效
- 作息管家.html 镜像同步删(目录锚 + 章节内容)

### 改动前 → 改动后对比
- SKILL.md: 1049 → 985 行(删 64 行)
- 作息管家.html: 1158 → 864 行(删 294 行)
- references/Cron任务.md: 63 行 → 删除

### 清理边界
**不删**:
- `prepare-messages` 速查表行(改标签,不删) — 命令在用
- `get_last_record_full` Python 函数 — schedule_cli.py:22 引用
- `references/同步流程.md` 流程文档 — 描述 prepare-messages + add 流程,真文档
- `references/CLI命令.md` — CLI 命令文档,真文档

**不重写 SKILL.md 触发词路由表** — 上轮 5 commits 已含完整 §3.x(5 模板 8 命令),与本次清理无冲突
