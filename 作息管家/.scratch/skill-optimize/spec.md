---
Status: ready-for-agent
Type: spec
Feature: skill-optimize
Created: 2026-07-28
Source-Grilling: .notes/grilling-session.html
ADRs: [0001-help-html-stable-mirror.md, 0002-strict-skill-spec.md, 0003-defer-cli-split.md]
---

# Spec · 作息管家与 SKILL 开发总纲 V1.0 对齐重构

## Problem Statement

作息管家 v1.1.3 与 SKILL 开发总纲 V1.0 之间存在 6 处违规 / 缺位:

1. **三源数字对账违规**:作息管家.html 顶部 stats(24/13/11)、SKILL.md 表格(26 唤醒词)、`references/scenarios.yaml`(27 唤醒词 + T4/T5)三处数字不一致,违反总纲 §07 §6 "五者一一对应"契约。
2. **HTML 输出路径违反原则 12.A**:作息管家 15 模板里仅 `help_center.html` 对齐了"中文 command 名 + YYYYMMDD_HHMMSS"格式;record / plan / receipt 域仍用英文 `record_day_<TS>.html` 等。
3. **单工铁律不完整(原则 10)**:record 域 6 模板已落地"复制 prompt"按钮,plan 域 4 模板(`plan_review` / `plan_preview` / `plan_receipt_*`)未确认;部分过程型 HTML 仍缺 4 部分结构(场景/数据/期望/来源)。
4. **`schedule_cli.py` 过大**:116KB / 3053 行,接近总纲 §02 5 层 §② 操作层"不 1 个 2000 行"上限;内部无按域分组。
5. **根目录 `作息管家.html` 手工维护**:与 SKILL.md / scenarios.yaml 实际内容漂移;无强同步机制,违反总纲 §05 钩子 #1 "HTML 同步硬规则"。
6. **缺工程配置**:无 ADR / AGENTS.md / `docs/agents/`(总纲 §02 自检清单 + §07 §1 契约)。

## Solution

8 决策闭环 + 3 份 ADR 落盘 + 4 实施 Phase(待执行):

### 决策闭环(2026-07-28 Grilling 达成)

| # | 主题 | 答案 |
|---|---|---|
| Q1 | 作息管家.html 风格 | A · 纯 HELP 中心 |
| Q2 | 作息管家.html 角色 | A · 永远最新(覆盖写 + git 跟踪) |
| Q3 | 同步机制 | A · 无 flag,自动同步 |
| Q4 | 数字对账脚本 | **不做** · 开发时人工注意 |
| Q5 | 路径对齐原则 12.A | A · 严格按总纲,15 模板一次性全部对齐 |
| Q6 | 单工铁律 plan 域 | A · 全部 15 模板补"复制 prompt" |
| Q7 | schedule_cli.py 拆模块 | B · 暂不拆,Q5 顺便内部分组 |
| Q8 | AGENTS.md | A · 简洁版引用 SKILL.md |

### ADR 落盘

- **ADR-0001** — 作息管家.html 作为 HELP HTML 的稳定入口(总纲 §04 原则 12 例外)
- **ADR-0002** — 严格执行总纲 §04 原则 12.A(中文 command 名)+ 原则 10(全部 15 模板补复制 prompt)
- **ADR-0003** — schedule_cli.py 暂不拆,等 Q5 路径对齐实施时内部分组

### 实施 Phase(4 个)

- **Phase A-3** · ADR-0001 落地 — `help_render.py` 同步作息管家.html(阻力最小)
- **Phase A-1** · Q5+Q6+Q7 — 路径对齐 + 复制 prompt + 内部分组(主任务,需 Fresh Agent 黑盒测试)
- **Phase A-2** · setup-matt-pocock-skills 落地 — ✅ **已完成**(commit `633abc4`)
- **Phase B** · pytest + FAT 验证

## User Stories

1. As an AI agent 开发者,我 want scenarios.yaml 是唯一事实源 so that 所有 HELP HTML / 人类视图 / 机读视图从它派生,避免数字对账违规(总纲 §07 §2.1)
2. As a 用户,我 want 打开作息管家.html 看到当前所有场景 + 复制 prompt 按钮 so that 我能一键给 AI 派活
3. As a 用户,我 want 24 小时时间轴 + 健康分 + 7 维趋势可视化 so that 我一眼能看出今天的作息分布
4. As a 用户,我 want 异常检测(7 维雷达 + 红/黄框)so that 我能发现最近的作息偏差
5. As a 用户,我 want 类别深挖(24h × N 天热力图)so that 我能看出健身习惯(上午/傍晚双峰)
6. As a 用户,我 want 范围对比(7 月 vs 6 月 / 上周 vs 本周)so that 我能比较两个时段
7. As a 用户,我 want 复盘 page(逐条 completion 标记 + 蓝调 diff)so that 我能完成 plan → 复盘 闭环
8. As a 用户,我 want 商量计划(多轮对话 → 24h 录满)so that AI 帮我规划明天
9. As a 用户,我 want 补计划 idempotent(按 date+time 三元组查重)so that 我不会重复创建
10. As a 用户,我 want 改/删计划(询问飞书同步)so that 我能精细调整
11. As a 用户,我 want 飞书日历联动(探测 → 询问 → 同步)so that 我的日程自动同步到飞书
12. As a 用户,我 want 复制 prompt 按钮(原则 10 单工铁律)so that 我能从 HTML 复制场景给 AI 执行
13. As a 用户,我 want 5 状态 fallback(正常 / 空 / 缺数据 / 错误 / 离线)so that 任何渲染失败都有兜底
14. As a 开发者,我 want HTML 路径对齐总纲 §04 原则 12.A(`<command_cn>_<YYYYMMDD>_<HHMMSS>.html`)so that 作息管家文件名与卡路里 / 饼干记账一致
15. As a 开发者,我 want schedule_cli.py 内部按 record / plan / receipt / help 4 域分组(ADR-0003)so that 将来拆分成本低
16. As a 开发者,我 want 8 一级 + ~70 二级 category 白名单 + 心法 5 条(分类心法.md)so that 数据规范化
17. As a 开发者,我 want 前 5 后 5 滑动窗口判断 + BLOCK COUNT 校验 so that 同步消息时 block 边界准确
18. As a 开发者,我 want 9 字段全填才能 add_record(强制规范 #2)so that 数据完整性
19. As a 跨 Skill 调用者,我 want ensure-plan-event 幂等 + search-plan-event 精确匹配 so that 不会重复创建
20. As a 开发者,我 want 3 份 ADR(0001/0002/0003)落盘 so that 关键决策有据可查(总纲 §02 §③ 文档层 / 演化)
21. As a 开发者,我 want AGENTS.md + docs/agents/(issue-tracker / domain)落地 so that 工程 skill 能正确读写(setup-matt-pocock-skills)
22. As a 开发者,我 want git diff 看得见帮助文档变更(ADR-0001)so that 审计强约束
23. As a 用户,我 want "修正作息"(回执型第 2 款)so that 我能改 1 条记录多字段 + 蓝调 diff 审计
24. As a 用户,我 want "对比两个月"(任意范围对比)so that 我能比较任意两个时段(不只是月份)

## Implementation Decisions

1. **作息管家.html = help_render.py 派生产物(ADR-0001)**
   - 根目录 `作息管家.html` 与 `schedule_html/help/作息管家_HELP_<TIMESTAMP>.html` 是同一 HTML 的稳定入口 vs 历史快照
   - 接口:`help_render.py` `render()` 函数额外调用 `sync_to_stable_mirror()`,返回主输出路径 + 同步结果
   - 影响:`help_render.py` 加 ~20 行新函数;`.gitignore` 不排除根目录作息管家.html
   - 总纲 §04 原则 12 例外:此 ADR 即覆盖授权

2. **HTML 路径对齐原则 12.A(ADR-0002)**
   - 全部 15 模板统一 `<command_cn>_<YYYYMMDD>_<HHMMSS>[_<N>].html`
   - `<command_cn>` 中文映射(继承 SKILL.md 触发词速查表字面):
     - record 域:`查作息记录` / `查作息区间` / `查作息对比` / `查作息类别` / `查作息异常` / `作息详情` / `记作息回执` / `修正作息回执`
     - plan 域:`查日程` / `改日程回执` / `补日程回执` / `写日程回执` / `商量计划预览` / `复盘`
   - 接口:`schedule_html_render.py::_naming_path` 接受中文 command 参数;`schedule_cli.py` 所有 `render_*` 子命令传新参数;`default_output_path` 5 处更新
   - SKILL.md 顶部 stats 字段(24/13/11)在 Q1+Q2 自动同步后保持准确

3. **单工铁律原则 10 超字面执行(ADR-0002)**
   - 全部 15 模板(不只是过程型)补"复制 prompt"按钮 + 4 部分结构(场景 / 数据 / 期望 / 来源)
   - 接口:`render_payload` 新增 `prompt_meta` 字段(`_record_engine.js` 共享层支持,`_plan_engine.js` 若存在则补建)
   - 视觉:复制按钮 + 复制成功反馈 + 剪贴板 API fallback(`navigator.clipboard` → `execCommand` + textarea)
   - 4 部分 prompt 模板(原则 10):① 场景:用户在 HTML 中做了什么 ② 数据:用户看到的最终数据 ③ 期望:AI 应执行什么 CLI 操作 ④ 来源:HTML 数据来自哪个 CLI / 时间

4. **schedule_cli.py 暂不拆(ADR-0003)**
   - 116KB / 3053 行暂不拆 record_cli / plan_cli / receipt_cli
   - `_naming_path` 函数内部按 record / plan / receipt / help 4 域加注释分组(为将来拆分打基础)
   - 触发重新评估条件:突破 150KB / 4000 行 / `_naming_path` 已 100% 按域清晰分组 / 用户明确要求

5. **5 层架构保持**
   - 数据层 `schedule_db.py` 不动
   - 操作层 `schedule_cli.py` 内部按域分组(不改 import 结构)
   - 规则层 `validators.py` 不动(8 一级 + ~70 二级白名单已就绪)
   - 接口层 `schedule_cli.py` 子命令不变(`add` / `prepare-messages` / `list` / `render-*` / `amend-record` / ...)
   - 文档层 SKILL.md + html 同步

6. **场景资产唯一事实源(总纲 §07 §2.1)**
   - `references/scenarios.yaml` 不动(7 字段契约已合规)
   - CATEGORY_MAP 5 模块分类(写入 / 查询 / 日程 / 分析 / 辅助)保留

7. **跨 Skill 路由声明(SKILL.md 已有)**
   - "健身"(作息上下文)→ 作息管家;("健身"饮食上下文)→ 卡路里
   - "心愿"(作息上下文)→ 作息管家;("心愿"独立)→ 备忘录
   - "打卡"(复盘上下文)→ 作息管家;("打卡"独立)→ 备忘录
   - 不引入新代码,只声明路由

8. **问题跟踪本地化(setup-matt-pocock-skills)**
   - `.scratch/skill-optimize/` 是本次重构的 issue tracker
   - 本 spec 是 `spec.md`,实施 issue 是 `issues/01-...md` `02-...md` `03-...md`

## Testing Decisions

- **唯一测试 seam**:作息管家已有 `tests/` 目录(11 个 pytest 文件)— 新 seam 不引入
- **测外部行为,非实现细节**:
  - CLI 子命令的 stdout JSON 输出 `{status, data, message}`
  - HTML 文件存在 + 内容关键字存在
  - 文件路径符合命名规则(`<command_cn>_<YYYYMMDD>_<HHMMSS>.html`)
- **新增测试模块**(Phase A-1 实施时):
  - `tests/test_help_sync.py` — 测 ADR-0001:根目录作息管家.html 自动同步
  - `tests/test_naming.py` 扩展 — 覆盖 15 模板中文 command 名(已有命名合规正则可复用)
  - `tests/test_copy_prompt.py` — 测 15 模板都有"复制 prompt"按钮
- **已存在测试做参照**:
  - `tests/test_routing.py`(29 用例 · 相对时间换算)
  - `tests/test_amend_record_cli.py`(CLI 入口 + as_dict=True)
  - `tests/test_compare.py`(命名合规正则)
- **Fresh Agent 黑盒测试(总纲 §05 FAT 协议)**:
  - Phase A-1 必跑(跨多 CLI 子命令,改动大)
  - Phase A-3 可豁免(纯新增派生步骤)
- **pytest baseline**:跑 `pytest tests/ -v` 必须全绿

## Out of Scope

- **Q4 数字对账脚本** — 用户决定不做(`scripts/verify_count.py`);开发时人工注意 SKILL.md / scenarios.yaml 数字一致
- **schedule_cli.py 拆为多文件** — ADR-0003 暂缓,等触发条件满足(150KB / 4000 行)
- **新版 §07 §5 之外的 5 者一一对应** — 只做核心:场景资产 / HELP HTML / SKILL.md / 路由表,不引入新工作流层
- **跨 Skill 协同实现** — 作息管家 ↔ 卡路里 / 备忘录只在 SKILL.md 路由表声明,不做实际集成代码(API 调用 / 数据共享)
- **triage skill 安装** — Section B 跳过(`triage` 未安装时不写 `triage-labels.md`)
- **CONTEXT.md / CONTEXT-MAP.md 创建** — domain-modeling lazy create,本次不动(不创建术语表)
- **飞书 CLI 升级** — 不改飞书集成层,只调整其触发时机

## Further Notes

- **总纲依赖**:`SKILLS/SKILL开发总纲V1.0/` 是元规范,所有改动须遵守 §02 5 层 / §03 触发词 / §04 原则 / §05 工程仪式 / §07 HELP 契约
- **commit 633abc4** 已落地 Phase A-2 文档配套(AGENTS.md + docs/agents/ + .scratch/ + 移除 SKILLS/ 根临时文件)
- **Phase A-3**(ADR-0001 实施) — 30 分钟 · 单 commit · Tested-By exempt
- **Phase A-1**(Q5+Q6+Q7 实施) — 2-3 小时 · 单 commit · Tested-By **pending-FAT** · 跨多 CLI 子命令,需 Fresh Agent 黑盒测试
- **Phase B**(验证) — pytest baseline + FAT + 手动 git diff SKILL.md 引用
- **后续触发条件**:
  - schedule_cli.py 突破 150KB / 4000 行 → 重新评估拆模块
  - scenarios.yaml 增改唤醒词 → 重新跑 help_render.py 同步作息管家.html
  - 总纲更新 → 重审 3 份 ADR 是否仍生效
- **参考产出**:`.notes/grilling-session.html`(本次 Grilling 会话状态)+ `作息管家/docs/adr/0001/0002/0003.md`(3 份 ADR)