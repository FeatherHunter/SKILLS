# ADR-0005: 复盘 start-end 是独立新工作流,不合并 14 复盘 / 09 查作息范围

## 状态

`accepted` · 2026-07-30 · Grilling Session 6 决策共识

## 背景

用户原报告(`查作息区间_20260730_103630.html`,540 KB):
- "下达 作息管家 复盘本月的命令后,生成的 HTML 文件..."
- "首先数据量爆炸、UI 层面非常混乱,完全没有达到 复盘的效果"
- "需要全方面的重构,无论是功能还是 UI 层面"

调研发现:
- **14 复盘** (`schedule_plan_review.html`) = plan 域单日 completion 写库,4 个场景,不支持月维度
- **09 查作息范围** (`schedule_record_range.html`) = record 域聚合报告,5 状态 fallback 完整但 30 天数据视觉爆炸
- 用户说"复盘本月"AI 实际路由到 09,但产出物在心智模型上不是"复盘"

用户原始诉求产品语义:
> "复盘应该底层是一个 start-end 的范围,但是上层设计好的唤醒词 比较通用"
> "如果用户提出了非预置唤醒词,因为 底层 start-end 参数都能 hold 住"

## 决策

新增独立 `replay` 工作流,不合并 14 复盘 / 09 查作息范围:

- **新模板**:`templates/schedule_replay.html` (132 → 430 行)
- **新 CLI 命令**:`python scripts/schedule_cli.py render-replay <start> <end> [--out PATH]`
- **新渲染函数**:`schedule_html_render.render_replay(start, end, ai_engine="mock")`
- **新模式**:`mode="replay"` + 新中文 command 名 `"replay": "区间复盘"`
- **新 subdir**:`schedule_html/replay/`,文件名 `区间复盘_<YYYYMMDD>_<HHMMSS>.html`
- **接口预留**:`ai_engine="mock" | "llm"`(后续 LLM 接入)

### 4 段叙事架构

```
[input: 任意 start-end 区间]
   ↓
[data: schedule_records + schedule_plans(含 completion)]
   ↓
[process: 4 段叙事]
   ├─ 1. record_aggregate: 分类时长 / 7 维趋势 / 24h 热力图 (T03)
   ├─ 2. plan_aggregate:   completion 6 类分布 + 分类拆解 (T04)
   ├─ 3. cross_domain:     planned_actual_pairs / unexecuted / unexpected / overrun (T05)
   └─ 4. ai_insights:      mock 异常检测 + 周期对比 + 建议 (T06)
   ↓
[output: 单文件 HTML · 离线自包含]
```

### 唤醒词分工 (D 方案)

| 唤醒词 | 路由到 |
|---|---|
| "复盘" / "复盘今天" / "复盘昨天" / "复盘 YYYY-MM-DD" | **14 复盘** (plan_review, 单日 completion 写库) |
| "复盘本周" / "复盘上周" / "复盘本月" / "复盘上月" / "复盘今年" / "复盘上年" / "复盘 [区间]" | **新工作流** (replay, dual-domain 分析报告) |

裸词 "复盘" 默认走 14 复盘 (向后兼容, A 方案)

### 5 状态 fallback (总纲 §04 原则 4)

`ok` / `empty` / `incomplete` / `error` / `offline` — HTML 顶部 hero 区显示状态徽章 (✅/📭/⚠️/❌/📡)

## 理由

1. **用户的"复盘"心智 = 跨域 review** — 14 复盘只覆盖 plan 域写库,09 只覆盖 record 域聚合,缺跨域
2. **不复用 09 模板修复** — schedule_record_range.html 的 5 状态 fallback 不变量保留,新工作流独立演进
3. **不复用 14 复盘流程** — 14 复盘的 Step 0-6 流程(状态机 / AI 匹配打卡 / 追问 / 小结) 是 plan 域 completion 闭环,新工作流是跨域分析
4. **新独立场景符合 ADR-0003 精神** — 宽 Skill 不拆 record_cli/plan_cli,但跨域 review 是作息管家的"独门能力"
5. **数据契约清晰** — 4 段叙事 payload 字段契约 (summary_items/trend/heatmap/completion_distribution/planned_actual_pairs/anomalies/suggestions) 在 spec 第 8 决策固化

## 考虑过的替代方案

- **A. 合并 14 复盘 + 09 查作息范围**: 用户产品语义错误("复盘" = 跨域 review 不是聚合报告),治标不治本,用户原话"完全没达到复盘的效果"
- **B. 增强 09 查作息范围**: 保留名义不改名 = 治标不治本(同上)
- **C. 新独立场景 #X 月度复盘**: **✅ 选 C** (本 ADR),符合 ADR-0003 精神
- **D. 14 复盘 + 09 上下位语义**: 14 是单日写库,09 是任意区间聚合,与"复盘 start-end"心智都不同,选 D 也需要新独立场景

## 后果

1. `schedule_html_render.py` +139 行(`render_replay` 函数 + 4 段叙事算法 + 5 状态 fallback)
2. `templates/schedule_replay.html` 132 → 430 行(T01 骨架 → T08 视觉打磨)
3. `scripts/schedule_cli.py` +57 行(`cmd_render_replay` + elif 分支 + help line)
4. `scripts/schedule_db.py` +45 行(`get_plan_events_range` 区间查询)
5. `tests/test_render.py` +18 个 acceptance 测试
6. `tests/test_replay_visual.py` +5 个端到端测试
7. `tests/test_replay_e2e.py` +13 个 seam + 文档静态测试
8. 9 个 commit (T01 / T03 / T04 / T05 / T06 / T07 / T08 / T09 / T10)
9. 14 复盘 / 09 查作息范围 不动 (用户原报告 bug 修复顺手在 T03 完成:9 个 bug fix)

## 触发重新评估的条件

满足任一即重新评估:

1. 用户要求合并 14 复盘 + 新工作流(违反 ADR-0005)
2. 跨域分析算法被 LLM 真实替代(spec decision 13 的 `ai_engine="llm"` 接入)
3. 4 段叙事扩为 5+ 段(超出 spec 第 8 决策固化)

## Status

`accepted` · 2026-07-30 · Grilling Session 6 决策共识 · 9 个 commit 完成落地