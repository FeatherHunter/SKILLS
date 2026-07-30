# 作息管家 · 复盘 start-end · Spec

> Status: `ready-for-agent` · 2026-07-30 · Grilling Session 6 决策共识
> Trace: parent issue → `docs/agents/issue-tracker.md` §"每个 feature 一个目录"
> 
> ## 决策摘要
> - **保留**: 14 复盘 (plan 域 单日 completion 写库), 09 查作息范围 (record 域 任意区间聚合)
> - **新增**: 复盘 start-end (跨域 dual-domain 分析, 4 段叙事)
> - **唤醒词分工(D)**: 14 复盘 = 「复盘 / 复盘今天 / 复盘昨天 / 复盘 YYYY-MM-DD」; 复盘 start-end = 「复盘本周/上周/本月/上月/今年/上年 + 复盘 [区间]」
> - **分析流程颗粒度(C 深层)**: record 聚合 + plan 聚合 + 跨域对比 + AI 洞察
> - **裸词「复盘」默认**: A 方案 → 14 复盘今天 (向后兼容)

---

## Problem Statement

作息管家 v1.1.3 的"复盘"概念当前存在 3 个结构性缺陷,用户做月度复盘时全部暴露:

1. **跨域分析缺失**。用户做"复盘本月"时,需要看 4 类信息:
   - 实际做了什么(record 域: 分类时长、7 维趋势、24h 时间轴)
   - 计划了什么 / 完成了什么(plan 域: completion 分布)
   - **计划 vs 实际**对比(跨域: 哪条计划做了,哪条没做,实际超出计划多少)
   - AI 洞察(异常、周期、建议)
   当前没有任何一个工作流能同时产出这 4 类。09 查作息范围只覆盖 record 域。14 复盘只对单日 plan 域写库 completion,不能跨日。

2. **月度数据视觉爆炸**。09 查作息范围 渲染 30 天 × 863 条记录,直接输出 540KB HTML(用户实测 `查作息区间_20260730_103630.html`):"区间长度"卡片渲染为 30 个日期 join 字符串(a)、53 个 cat-row 占满 2227px 高度(b)、863 条记录 inline 全部展开无折叠(c)、首屏上方 70% 全部空白。Schedule_record_range.html 模板对月度数据场景无 折叠 / 分页 / 虚拟列表 / Top-N 策略。

3. **唤醒词表层统一但语义分裂**。"复盘"既可指 14 复盘(单日 plan 域 写库 写库),又可指 09 查作息范围(任意区间 record 域 统计聚合)。用户说"复盘本月"AI 实际路由到 09,但产出物在心智模型上不是"复盘"(没有 计划 vs 实际),用户原话:"完全没达到 复盘的效果"。

用户原话:"需要全方面的重构,无论是功能还是UI层面"。

---

## Solution

新增一个独立的"复盘 start-end"工作流,按 4 段叙事产出 dual-domain 分析 HTML:

```
[input: 任意 start-end 区间]
   ↓
[data: schedule_records + schedule_plans(含 completion)]
   ↓
[process: 4 段叙事]
   ├─ 1. record 聚合(分类时长 / 7 维趋势 / 24h 时间轴)
   ├─ 2. plan 聚合(完成情况 / 完成率 / 堆叠柱)
   ├─ 3. 跨域对比(计划 vs 实际 / 未执行 / 超预期)
   └─ 4. AI 洞察(异常 / 周期 / 建议)
   ↓
[output: single-file HTML · 离线自包含]
```

7 个预置时间维度唤醒词 + 自由区间,底层都映射到 start-end 范围。保留 14 复盘 + 09 查作息范围 不动。唤醒词分工按 D 方案严格区分避免 AI 路由歧义。

---

## User Stories

### A. 7 个预置时间维度(基础)

1. As a 用户, I want to say "复盘本月", so that 立即得到本月 30 天的完整复盘报告,不需要记 start-end 范围
2. As a 用户, I want to say "复盘本周", so that 立即得到本周一到日的 7 天复盘报告
3. As a 用户, I want to say "复盘上周", so that 立即得到上周一到日的 7 天复盘报告
4. As a 用户, I want to say "复盘上月", so that 立即得到上月 1 号到月末的完整复盘报告
5. As a 用户, I want to say "复盘今年", so that 立即得到本年 1 月 1 日到今的复盘报告
6. As a 用户, I want to say "复盘上年", so that 立即得到去年 1 月 1 日到 12 月 31 日的复盘报告
7. As a 用户, I want to say "复盘今日", so that 走 14 复盘(plan 域 completion 写库,plan 域 写库 单日闭环)

### B. 自由区间(用户提非预置)

8. As a 用户, I want to say "复盘 2026-07-13~2026-07-19", so that 任意指定区间都能 hold 得住
9. As a 用户, I want to say "复盘过去 30 天", so that 相对时间区间也能解析
10. As a 用户, I want to say "复盘 7/13~7/19", so that 简写日期也能解析
11. As a 用户, I want to say "复盘 2026 Q3", so that 季度也能作为输入

### C. 4 段叙事(产出物)

#### 顶部 4 卡(总览)

12. As a 用户, I want 顶部 4 卡 显示区间总时长 / 总记录数 / 计划完成率 / 健康分, so that 30 秒看到核心
13. As a 用户, I want 4 卡按重要性排(success→warn→default 渐变), so that 视觉聚焦关键

#### 第一段 · record 聚合

14. As a 用户, I want 看 分类时长 Top 10, so that 看到主轴类别消耗
15. As a 用户, I want 53 个 cat-row 折叠收缩为 Top 10 + "展开全部"按钮, so that 解决视觉爆炸
16. As a 用户, I want 看 7 维趋势曲线 (工作 / 睡眠 / 运动 / 创作 / 学习 / 休闲 / 健康), so that 看到周期
17. As a 用户, I want 看 24h × N 天热力图, so that 看到时间模式

#### 第二段 · plan 聚合

18. As a 用户, I want 看 计划完成率(整体 %), so that 看到计划 vs 实际的一致性
19. As a 用户, I want 看 完成情况分布堆叠柱(已完成 / 已完成(超时) / 部分完成 / 未完成 / 未完成(不可抗力) / 未复盘), so that 看到完成状态全景
20. As a 用户, I want 看 按分类拆解的计划完成情况, so that 看到哪类计划完成率高

#### 第三段 · 跨域对比(差异化价值)

21. As a 用户, I want 看 "计划 vs 实际"对比表, so that 看到哪些计划做了哪些没做
22. As a 用户, I want 看 "未执行计划"清单 + 占比, so that 重点关注高优先级未执行
23. As a 用户, I want 看 "超预期"清单(record 有但 plan 无), so that 看到意外事件
24. As a 用户, I want 看 "实际超出计划时长"清单, so that 看到超时事件(已完成(超时) 的来源)

#### 第四段 · AI 洞察

25. As a 用户, I want 看 AI 异常检测(某分类骤变 / 睡眠骤减 / 健康分大幅下降), so that 关注异常
26. As a 用户, I want 看周期性对比(本区间 vs 上周 / 上月 / 上年同期), so that 看到趋势
27. As a 用户, I want 看 AI 建议(基于洞察的可执行建议), so that 转化为行动

### D. 5 状态 fallback

28. As a 用户, I want 区间内完全无数据时, 看到空态 HTML(友好提示 + 引导), so that 知道为什么没数据
29. As a 用户, I want 数据库错误时, 看到错误态 HTML(明确错误 + 转交人工), so that 不假装成功
30. As a 用户, I want 数据缺失(只有 record 无 plan 或反之)时, 看到 partial 态(缺失域标"无数据"但其他域正常), so that 跨域 asymmetry 不被掩盖
31. As a 用户, I want 离线时(无网络), 报告仍能打开查看(单文件自包含), so that 飞书/邮件消息预览能用

### E. UI 体验

32. As a 用户, I want 看 单文件 HTML 自包含, no 外部 CSS/JS 依赖, so that IDE / 飞书 / 邮件预览都能用
33. As a 用户, I want 在 360px 手机视口下看 报告, so that 通勤路上通勤路上手机看
34. As a 用户, I want 在 768px 平板视口下看 报告, so that 平板设备体验
35. As a 用户, I want 复制 prompt 按钮(4 部分结构), so that 把报告内容粘给 AI 二次对话
36. As a 用户, I want 顶部 hero 区清晰显示 区间 + 总时长 + 记录数, so that 5 秒内知道这是哪个报告

### F. 路由消歧

37. As a 用户, I want 说 "复盘今日" 走 14 复盘(plan 域 completion 写库), so that 不会 错走 新工作流
38. As a 用户, I want 说 "复盘本月" 走 新工作流, so that 避免 AI 误路由到 09
39. As a 用户, I want 表 14 复盘 改名为 "过当日"("完成现状复盘"), so that 唤醒词分工清晰(可选)
40. As a 用户, I want 14 复盘 保留原表 "复盘" / "复盘今天" / "复盘昨天" 唤醒词, so that 旧接口兼容

### G. 数据契约

41. As a 开发者, I want 自包含 HTML(JS + CSS inline), so that 离线可读
42. As a 开发者, I want payload JSON 完整, so that 后续 NLP 检查 / 行为回放可重现
43. As a 开发者, I want 5 状态 fallback 完整覆盖, so that 不假装成功

---

## Implementation Decisions

### 模块与命名

1. **新模式 `replay`** —— 区别于 `record-day` / `record-range` / `plan-review` / `plan-list`,作为独立的 5th 模式。
2. **新模板 `templates/schedule_replay.html`** —— 复用 `_record_engine.js` 渲染框架,但独立模板文件(因为 4 段叙事 vs 单日/单域范式根本不同)。
3. **新渲染函数 `render_replay(start, end)`** —— 位于 `scripts/schedule_html_render.py`,与 `render_record_day` / `render_record_range` / `render_plans_review` 同级。
4. **新 CLI 命令 `render-replay --start YYYY-MM-DD --end YYYY-MM-DD`** —— 位于 `scripts/schedule_cli.py`,委托 `render_replay`。
5. **新文件名 `区间复盘_<YYYYMMDD>_<HHMMSS>.html`** —— 不带区间(默认用户通过 HTML 头部 meta 看到 start-end,避免长路径)。**`复盘_<TS>.html`(14 复盘) vs `区间复盘_<TS>.html`(新工作流)** 在 subdir 隔离 + 中文前缀双重区分,杜绝文件系统冲突。遵守 ADR-0002 Q5(中文 command 名)+ ADR-0002 Q7(永不覆盖 + _N 冲突保护)。
6. **新 CN_COMMAND_MAP 条目** `"replay": "区间复盘"` —— 在 `schedule_html_render.py` 已有 4 域分组内的"跨域"组(新增第 5 组)。**避免与 `"plan_review": "复盘"`(14 复盘)撞车**，两个工作流共享"复盘"语义但中文 command 名严格区分。
7. **ADR-0003 精神遵循** —— 不拆 `schedule_cli.py` / `schedule_html_render.py`,只在 `CN_COMMAND_MAP` 加新条目 + 域分组注释。

### 数据契约

8. **payload 结构**(`data` 字段):
   ```
   {
     "meta": {
       "mode": "replay",
       "start": "2026-07-01",
       "end": "2026-07-30",
       "days": 30,
       "total_records": 863,
       "total_minutes": 27373,
       "completed_events": 12,
       "total_events": 14,
       "completion_rate": 0.857,
       "health_score": 85,
       "title": "复盘报告 · 2026-07-01 ~ 2026-07-30",
       "subtitle": "30 天 · 863 条记录 · 86% 计划完成率",
       "generated_at": "2026-07-30 11:00:00"
     },
     "record_aggregate": {
       "summary_items": [...],  // 复用 record-range 形态
       "trend": [...],          // 7 维趋势数组
       "heatmap": [...]          // 24h × N 天热力图
     },
     "plan_aggregate": {
       "completion_distribution": {
         "已完成": 12, "已完成(超时)": 2, "部分完成": 1,
         "未完成": 3, "未完成(不可抗力)": 1, "未复盘": 0
       },
       "completion_by_category": [...],
       "completion_rate": 0.857
     },
     "cross_domain": {
       "planned_actual_pairs": [...],   // 计划 vs 实际
       "unexecuted_plans": [...],       // 未执行计划
       "unexpected_records": [...],     // 超预期
       "overrun_plans": [...]            // 实际超出计划时长
     },
     "ai_insights": {
       "anomalies": [...],              // 异常检测
       "periodic_compare": [...],       // 周期对比
       "suggestions": [...]              // AI 建议
     },
     "copy_prompt": "..."              // 4 部分结构
   }
   ```
9. **5 状态 fallback** — 顶层 `status` 字段:`ok` / `empty` / `incomplete` / `error` / `offline`.
   - `ok`: 数据完整
   - `empty`: 区间内无 record 且无 plan(刚装完数据库)
   - `incomplete`: 单域有数据(如只有 record 无 plan)→ 缺失域标"无数据"
   - `error`: 数据库错误 → HTML 显示错误态
   - `offline`: 网络离线(单文件 HTML 仍可打开)

### 4 段叙事实现

10. **record 聚合** — 复用 `render_record_range` 的算法(分类时长 / 趋势 / 24h 热力图),但加 Top-N 折叠策略(默认 Top 10 + "展开全部"按钮,解决 53 个 cat-row 爆炸)。
11. **plan 聚合** — 新增算法,从 `schedule_plans` 拉区间内活跃事件,按 `completion` 字段分 6 类统计。completion 字段 6 个合法值见 `references/数据库结构.md`。
12. **跨域对比** — 新增算法,事件级左连接(plan.events LEFT JOIN records WHERE plan.date = records.date AND time overlap):
    - planned_actual_pairs: 计划有 + record 有 → 显示实际时长 vs 计划时长
    - unexecuted_plans: 计划有 + completion != NULL 表示没做 → 未执行清单
    - unexpected_records: record 有 + 区间内无计划 → 意外事件
    - overrun_plans: 实际超出计划时长 ≥ 20% → 超预期
13. **AI 洞察** — 接口预留,先实现 mock(基于规则的异常检测,例如 某分类 ≥ 2 倍均值时 触发异常)。后续可替换为真实 LLM 调用。

### 触发词解析

14. **CLI 解析** — `schedule_cli.py` 在 `cmd_render_replay` 中:
    - 必填 `--start` + `--end`
    - 内部子命令别名 `replay-today` / `replay-yesterday` / `replay-this-week` / ... 自动换算 start-end
    - 7 个预置时间维度换算:见 ADR-0005(待写)
15. **AI 路由** — SKILL.md `路由规则`章节新增条目:
    - "复盘今天/昨天/今天复盘" → 14 复盘
    - "复盘本周/上周/本月/上月/今年/上年" + "复盘 [区间]" → 复盘 start-end
    - 裸词"复盘" → 默认 14 复盘今天(向后兼容)

### 副作用修复(顺手)

16. **09 查作息范围 5 个 bug 修复** — 不在本次 spec 范围(单独 issue)。如果新工作流复用其算法,顺便修复。注:用户原话"全方面重构",但本次只重构"复盘 start-end",09 查作息范围 留着按总纲 §06 附录 B "B 优先级 · 按需" 后续单独迭代。

---

## Testing Decisions

### 单一 seam: 端到端 HTML 渲染 + playwright 视觉

**Seam 设计** —— 最高 seam(整 HTML 输出),复用现有 `tests/test_render.py` 模式:

1. **新增 `tests/test_render.py:test_render_replay_basic`** — 灌入 fixture(5 条 record + 3 条 plan,跨 3 天),跑 `render_replay("2026-07-15", "2026-07-17")`,断言:
   - `result["status"] == "ok"`
   - `data["meta"]["mode"] == "replay"`
   - `data["meta"]["start"]` / `end` / `days` 正确
   - 4 段叙事 payload 字段都存在
   - `copy_prompt` 4 部分结构存在
2. **新增 `tests/test_render.py:test_render_replay_empty`** — 区间无数据 → `status="empty"`
3. **新增 `tests/test_render.py:test_render_replay_incomplete`** — 只有 record 无 plan → `status="incomplete"`,plan 聚合标"无数据"
4. **新增 `tests/test_render.py:test_render_replay_status_distribution`** — 灌入 6 种 completion 值的 plan_events,断言堆叠柱分布正确
5. **新增 `tests/test_render.py:test_render_replay_cross_domain`** — 灌入 planned_actual_pairs + unexecuted_plans + unexpected_records,断言 4 个跨域清单都返回
6. **新增 `tests/test_render.py:test_render_replay_5_viewports`** — 复用现有 `test_help_mobile_responsive.py` 模式,playwright 360/768/1280 视口截图,断言以下视觉契约:
   - 360px 视口下 4 段叙事全部可见(无水平滚动)
   - "区间长度" 卡片不渲染日期 join 字符串(记 09 bug 教训)
   - 863 条记录 不 inline 全部展开(改 Top-N 折叠)
   - 5 状态 fallback 各视口无 UI 错乱

### 如何判断"好测试"

- **只测外部行为** — 跑 `render_replay` → 断言返回 dict 和生成 HTML,不 mock 内部函数
- **不测实现细节** — 不断言函数调用顺序 / 中间变量
- **fixture 复用** — `tests/test_render.py:26-51` 已有 `insert_test_records` / `insert_test_plan` helper,直接复用

### 既有类似测试(sibling seam)

- `tests/test_render.py:119 test_render_plans_review` —— 14 复盘渲染测试,本 spec 复用其模式
- `tests/test_render.py:103 test_render_plans_preview` —— plan 域 渲染测试
- `tests/test_render.py:55 test_render_record_day` —— record 域 渲染测试
- `tests/test_help_mobile_responsive.py` —— playwright 视觉断言 + 360px 视口模式

---

## Out of Scope

1. **14 复盘 修改** — 保留不动(包括产品语义、流程、唤醒词)。是否改名"过当日"等用户后续单独决策(不在本次 spec)。
2. **09 查作息范围 5 个 bug 修复** — 单独迭代。如果新工作流复用其代码,顺手修。
3. **AI 模型真实接入** — 当前 AI 洞察为规则 mock,后续可替换为 LLM 调用。本次只预留接口。
4. **历史数据迁移** — 不需要
5. **实时同步 / 多端同步** — HTML 是单文件自包含离线,不涉及
6. **打印 / PDF 导出** — 用户可通过浏览器自带 PDF 导出
7. **多用户 / 协作** — 单用户技能,不涉及
8. **国际化和多语言** — 中文优先
9. **14 复盘 + 09 查作息范围 视觉改造** — 本次只重构"复盘 start-end"

---

## Further Notes

### 与已有 ADR 的关系

- **ADR-0001** (作息管家.html 稳定入口): 不冲突 — 复盘 start-end 不需要稳定入口,因为文件名带 timestamp 即可(ADR-0002 Q7 永不覆盖)。
- **ADR-0002** (strict-skill-spec): 复用其 Q5 中文 command 名 + Q7 永不覆盖。
- **ADR-0003** (defer-cli-split): 严格遵守 — 只在 `CN_COMMAND_MAP` 加 1 条 + 域分组注释,不拆文件。

### 与领域第一性

作息管家 = `商量计划 (plan 域 预测) + 复盘 (跨域 review) + 记录 (record 域 过去)`。
14 复盘 = plan 域 写库(完成现状复盘)。
09 查作息范围 = record 域 聚合(看历史)。
**🆕 复盘 start-end = 跨域 review(plan + record + 跨域 + AI)**,这是作息管家的"独门能力"(其他 Skill 没这能力)。

### 不做交互验证的雷达

7 个预置换算 + 自由区间解析涉及时间逻辑,易边界出错:
- 跨月: 7 月 28 日 ~ 8 月 3 日
- 跨年: 12 月 28 日 ~ 1 月 4 日
- 上周 vs 本周(周一为一周开始还是周日?)
- 季度 / 半年 / 全年
本次 spec 不强制规范,沿用 `_naming_path` 既有 `this_week` / `this_month` 算法(按周一为周开始 + 系统当前日期)。如有歧义后续单独 ADR。

### 命名再确认

- 模板 = `schedule_replay.html`(避免 `review` 撞 14 复盘 `schedule_plan_review.html`)
- 模式 = `mode="replay"`(同上)
- 文件名 = `复盘_<YYYYMMDD>_<HHMMSS>.html`(中文 command 名 + timestamp)
- CLI = `render-replay`(连字符)
- 域分组注释 = `=== 跨域 域 ===`

### 跟进产物

按 to-spec 流程,write spec 之后跟进:
- `docs/adr/0005-replay-start-end-new-workflow.md` —— 记录"为何新独立工作流而非合并 14 复盘 / 09 查作息范围"(ADR criterion 3 个都满足)
- `CONTEXT.md`(作息管家首次) —— 核心术语: 复盘 / 14 复盘 / 复盘 start-end / 4 段叙事 / 5 状态 fallback / dual-domain
- `.scratch/replay-start-end/issues/01-...md` 起 —— to-tickets 阶段产出
