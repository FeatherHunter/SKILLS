# 作息管家 · Domain Glossary

> CONTEXT.md · 首次创建 · 2026-07-30 · Phase E · ADR-0005

作息管家的领域术语词典。不写实现细节,只固化"概念是什么 / 与其他概念的关系"。

---

## 核心概念

### 复盘

"复盘" = 跨域 dual-domain 分析(任意 start-end 区间)。

底层 = 任意 start-end 区间参数;上层 = 一组按时间维度预设的快捷唤醒词。

第一性:作息管家 = 商量计划 (plan 域预测) + 复盘 (跨域 review) + 记录 (record 域过去)。

### 14 复盘

14 复盘 = plan 域单日 completion 写库工作流。

逐条 review plan_events.completion,产生 6 类完成状态 (已完成/已完成(超时)/部分完成/未完成/未完成(不可抗力)/未复盘)。

适用:当日 / 昨天 / 指定日期 (单日)。

### 09 查作息范围

09 查作息范围 = record 域任意区间聚合报告。

统计聚合 (分类时长/7 维趋势/24h 时间轴/健康分/AI 钩子),不写库。

适用:任意 start-end 区间,纯展示。

### 复盘 start-end (本 ADR-0005 新工作流)

跨域 dual-domain 分析报告 = record 域聚合 + plan 域聚合 + 跨域对比 + AI 洞察。

4 段叙事骨架:
1. record_aggregate (分类时长 / 7 维趋势 / 24h 热力图)
2. plan_aggregate (completion 6 类分布 + 分类拆解)
3. cross_domain (planned_actual_pairs / unexecuted / unexpected / overrun)
4. ai_insights (mock 异常检测 + 周期对比 + 建议)

模板:`schedule_replay.html`;文件名:`区间复盘_<YYYYMMDD>_<HHMMSS>.html`。

### dual-domain (跨域)

dual-domain = 同时跨 `schedule_records` + `schedule_plans` 两表做左连接 / 配对。

与单域聚合区别:单域只统计一个表;跨域做两表时间对齐(plan 时间段 vs record 时间段重叠)。

### 5 状态 fallback (总纲 §04 原则 4)

5 状态枚举:`ok` / `empty` / `incomplete` / `error` / `offline`

| 状态 | 触发条件 | HTML 徽章 |
|---|---|---|
| ok | 两域数据完整 | ✅ ok (绿色) |
| empty | 两域都空 | 📭 empty (灰色) |
| incomplete | 单域有数据 | ⚠️ incomplete (橙色) |
| error | 数据库错误 | ❌ error (红色) |
| offline | 网络不通 | 📡 offline (橙色 + 顶部横幅) |

### 4 段叙事

复盘 start-end 工作流的 HTML 输出结构 = 4 段叙事 + 顶部 4 卡总览 + 复制 prompt。

4 段叙事对应 4 段数据聚合,按"实际 → 计划 → 对比 → 洞察"叙事递进。

---

## 域 (Domain)

作息管家内部 2 个语义不同的域 + 1 个跨域:

- **record 域**: `schedule_records` + `daily_summary` 表,回顾性输入(过去发生什么)
- **plan 域**: `schedule_plans` 表,预测性输入(未来计划什么)
- **跨域**: dual-domain 分析(ADR-0005 新增),不属于 record 域或 plan 域

---

## 路由规则(唤醒词 → 工作流)

| 唤醒词 | 路由到 |
|---|---|
| 复盘 / 复盘今天 / 复盘昨天 / 复盘 YYYY-MM-DD | 14 复盘 (plan 域 completion 写库) |
| 复盘本周 / 复盘上周 / 复盘本月 / 复盘上月 / 复盘今年 / 复盘上年 | 复盘 start-end (跨域 dual-domain) |
| 复盘 YYYY-MM-DD~YYYY-MM-DD / 复盘 过去 N 天 / 复盘 YYYY Qn | 复盘 start-end (跨域 dual-domain) |
| 复盘 (裸词,默认) | 14 复盘 (向后兼容, A 方案) |
| 查作息记录 / 查作息区间 / 查作息对比 / 查作息类别 / 查作息异常 / 作息详情 | 09 record 域 (查询类) |
| 查日程 / 商量计划预览 / 复盘 | plan 域 |
| 记作息 / 修正作息 / 改日程 / 补日程 / 写摘要 | receipt 域 (回执型) |

---

## 文件名规范(ADR-0002 Q5 + Q7)

`{中文 command 名}_<YYYYMMDD>_<HHMMSS>[_<N>].html`

| 工作流 | 中文 command 名 | subdir | 示例 |
|---|---|---|---|
| 14 复盘 (plan_review) | 复盘 | plan/list | 复盘_20260730_103000.html |
| 09 查作息范围 (record_range) | 查作息区间 | record/range | 查作息区间_20260730_103000.html |
| **复盘 start-end (replay) [新]** | **区间复盘** | **replay** | **区间复盘_20260730_103000.html** |
| record-day | 查作息记录 | record/day | 查作息记录_20260730_103000.html |
| plan-list | 查日程 | plan/list | 查日程_20260730_103000.html |

永不覆盖:`_2` / `_3` 后缀冲突保护(总纲 §04 原则 12)。

---

## 工具/路径

- 单文件模板:`templates/schedule_replay.html`(T01 骨架 → T08 视觉打磨, 132 → 430 行)
- CLI 入口:`python scripts/schedule_cli.py render-replay <start> <end>`
- 数据查询:`schedule_db.get_plan_events_range(start, end, include_inactive=False)` (T01 新增)
- 计算复用:`calculations.aggregate_by_category / build_trend_series / build_24h_heatmap` (T03 复用)

---

## 历史 ADR 索引

- ADR-0001: HELP HTML 稳定入口 (作息管家.html 镜像)
- ADR-0002: 严格 skill 规范 (中文 command 名)
- ADR-0003: schedule_cli.py 暂不拆,等 Q5 路径对齐实施时内部分组
- ADR-0004: HELP Toast UI 对齐卡路里 (iOS 通知风格)
- **ADR-0005: 复盘 start-end 是独立新工作流,不合并 14 复盘 / 09 查作息范围** (本 Phase E)

---

## 引用

- 总纲:`SKILLS/SKILL开发总纲V1.0/`
- 本 Skill spec:`.scratch/replay-start-end/spec.md`
- 实施 ticket:`.scratch/replay-start-end/issues/` (T01-T10)
- 本仓库根 AGENTS.md · docs/agents/issue-tracker.md · docs/agents/domain.md