# CLI 命令（2026-06-29 重构版）

> 所有命令通过 `python scripts/schedule_cli.py` 调用。
> 2026-06-29 大改动：5 个新计划事件命令 + 飞书日历联动。

---

## 一、基础数据命令（未变）

### 1. 初始化数据库
```bash
python3 scripts/schedule_cli.py init
```
创建 schedule_records、daily_summary、schedule_plans（新版）三表。

### 2. 写入作息记录（2026-07-22 新增规范化入口）
```bash
# 方式 A: 命令行参数
python3 scripts/schedule_cli.py add \
  --date 2026-07-22 --time-start 10:00 --time-end 11:00 \
  --duration-minutes 60 --activity "写小帅相关代码" \
  --category "工作.AI调优" \
  --source-contents "我在优化 AI" --source-timestamps "10:00" \
  --analysis-reasoning "AI 主动优化"

# 方式 B: JSON 文件
python3 scripts/schedule_cli.py add --json @record.json
```

**必填 9 字段**：`date / time_start / time_end / duration_minutes / activity / category / source_contents / source_timestamps / analysis_reasoning`

**触发词**：记作息 / 补一条作息 / 录作息

**返回**：`{status, data:{id, category, date}, message}` JSON 三段式。

**重要**：所有写入路径必须走 `add` CLI，**禁止直接调 `add_record_full` 函数绕过校验**。

### 3. 准备同步消息
```bash
python3 scripts/schedule_cli.py prepare-messages [<开始> [<结束>]] [--page N] [--page-size N]
```
分页获取游标到当前时间的消息（供 AI 分析）。

### 4~10. 查询 / 报告 / 状态
（保持不变：list / detail / summary / timeline / report / range / status）

---

## 二、日程（旧版 24-hour，**保留兼容**）

### 10. 查询（旧版）
```bash
python3 scripts/schedule_cli.py query-plans <日期1,日期2,...>
```

### 11. 旧版 upsert（保留）
```bash
python3 scripts/schedule_cli.py upsert-plan <日期> --json '{...}'  # 24-hour 模型
```

> 注：如果老 schedule_plans 表已迁移到 `schedule_plans_legacy_2026_06_29`，此命令仍可查询（兼容路径）。

---

## 三、日程（**新版事件型 — 推荐使用**）

### 12. 整日 upsert（**主入口**，必填满 24h）
```bash
python3 scripts/schedule_cli.py upsert-plan-events <日期> --json '...'
# 或从文件：
python3 scripts/schedule_cli.py upsert-plan-events <日期> --json @plan.json
# 或从 stdin：
cat plan.json | python3 scripts/schedule_cli.py upsert-plan-events <日期> --json -
```

**JSON 格式**：
```json
[
  {"time_start":"00:00","time_end":"07:00","title":"睡觉","notes":"深度睡眠","category":"休息"},
  {"time_start":"07:00","time_end":"08:00","title":"起床","notes":"洗漱","category":"起居"},
  {"time_start":"08:00","time_end":"12:00","title":"上班","notes":"干活","category":"工作"},
  ...
  {"time_start":"22:00","time_end":"24:00","title":"休息","notes":null,"category":"休息"}
]
```

**字段说明**：
- 必填：`time_start` / `time_end` / `title`
- 可选：`notes` / `category`
- 联合区间必须 ⊇ [00:00, 24:00]（CLI 层硬校验）

**行为**：
- 与 (date, time_start, time_end) 命中 → UPDATE
- 不命中 → INSERT（feishu_event_id 暂为 NULL）
- 旧活跃但新批次无 → 软删（is_active=0）
- 写完后若飞书可用 → CLI 询问"是否同步飞书日历？"

### 13. 单条修改
```bash
python3 scripts/schedule_cli.py update-event <id> \
    [--title "新标题"] [--notes "新备注"] [--category "新分类"] \
    [--time-start "08:30"] [--time-end "09:30"]
```

- 若该事件已绑定飞书 event_id → CLI 询问"是否同步修改到飞书？"
- 改时段（time_start/time_end）= 飞书"删旧 + 建新"（飞书日历无"改时间"按钮）

### 14. 单条软删
```bash
python3 scripts/schedule_cli.py deactivate-event <id>
```
- 软删（is_active=0），不真删
- 若已绑飞书 event_id → CLI 询问"是否同步删除飞书事件？"

### 15. 查询某日事件 + 飞书状态
```bash
python3 scripts/schedule_cli.py list-events <日期>
```
输出 24 行：
- id / time / title / notes / feishu_event_id / last_synced_at
- ✗ 前缀 = 已软删

### 16. 重同步某天到飞书
```bash
python3 scripts/schedule_cli.py feishu-resync <日期>
```
- 飞书侧 diff（按 description 含"作息管家自动同步"过滤）
- 询问每个 create/update/delete 动作
- 回写 feishu_event_id

---

## 四、飞书能力自动探测

每次涉飞书 CLI 都会自动调用 `is_feishu_available()` 检测本机能力：

| 探测项 | 失败时体验 |
|---|---|
| lark-cli 安装 | 跳过飞书同步，提示"装了飞书后会解锁：① 同步计划 ② 拆分钟级事件 ③ 双向 CRUD" |
| 已装未授权 | 跳过同步，提示"lark-cli auth login" |
| 用户身份 ready | 跳过同步 |
| 日历可写 | 跳过同步 |

**进程内缓存 5 分钟**避免重复探测拖累性能。

---

## 五、迁移命令（仅 2026-06-29 重构时需要跑一次）

```bash
python3 scripts/migrate_plan_to_events.py
```

**作用**：
- 把 `schedule_plans`（24 个 hour 字段）重命名为 `schedule_plans_legacy_2026_06_29`
- CREATE 新 `schedule_plans`（事件型 schema）
- 把所有旧记录按"1 小时 = 1 条事件"形式迁过来
- 幂等可重跑

**全新安装**：检测到无 schedule_plans 表 → 直接建新表，不做迁移。

---

## 六、决策记录（参考）

| 决策 | 选项 | 落地 |
|---|---|---|
| 删除方案 | 软删（is_active=0） | ✅ 不破例硬规范 |
| 改时段飞书处理 | 删旧+建新 | ✅ 飞书日历必须这样 |
| 飞书同步询问时机 | 每次 CRUD 后 AI 询问 | ✅ Y/n，用户主动 |
| 关联主键 | feishu_event_id 内联主表 | ✅ 不需单独映射表 |
| 子段解析 | 不解析，用结构化 JSON | ✅ 零歧义、直接喂飞书 |

---

## 七、典型 AI 工作流示例

```
用户: 帮我规划明天 2026-06-30
AI:  [讨论要点：上午写代码，中午吃饭，下午继续，晚上健身...]
    [生成结构化 JSON]

$ schedule_cli.py upsert-plan-events 2026-06-30 --json @plan.json
✅ 2026-06-30 写入成功
   新增: 9  更新: 0  软删旧: 0  活跃总数: 9

  飞书探测：✅ 全可用
  ? 是否把这 9 个新事件同步到飞书日历？ [Y/n]: y
  ? 是否创建飞书事件「睡觉」？ [Y/n]: y
  ...
  ✅ 飞书同步完成：created=9

$ schedule_cli.py update-event 504 --notes "上午专攻 AQS"
✅ 已更新 id=504
   该事件已同步到飞书
  ? 是否把这次改动也同步到飞书？ [Y/n]: y
  ✅ 飞书事件已更新
```

---

## 八、help

```bash
python3 scripts/schedule_cli.py help
```

---

## 九、HTML 渲染命令(2026-07-23 新增 · 5 模板 8 命令)

> **所有命令输出文件硬绑到 `SKILLS_DB_PATH/schedule_html/record/{子目录}/...`,不传 `--out`。**
> 详细架构设计: `SKILL.md §3.1.2` + `templates/_record_styles.css` + `templates/_record_engine.js`。
> 触发词路由: `SKILL.md §3.x` 表格。

### 1. `render-record-day <日期>` (T1 单日报告)

```bash
python3 scripts/schedule_cli.py render-record-day 2026-07-15
```

**输出**:`$SKILLS_DB_PATH/schedule_html/record/day/2026-07-15_record_day.html`

**4 段视觉**:首屏 4 卡摘要(总时长/分类数/健康分/睡眠) + 分类进度条 + 24h 时间轴 + 睡眠分析 + AI 思考钩子卡。

**触发词**:"查作息 2026-07-15" / "昨天我做了什么" / "今天看看"

### 2. `render-record-range <开始> <结束>` (T2 区间报告)

```bash
python3 scripts/schedule_cli.py render-record-range 2026-07-13 2026-07-19
```

**输出**:`record/range/2026-07-13_to_2026-07-19_record_range.html`

**4 段视觉**:首屏 4 卡摘要(区间天数/总记录数/区间健康分/总睡眠) + 分类进度 + **7 维趋势折线 SVG** + AI 钩子。

**触发词**:"这一周怎么样" / "最近 7 天看看"

### 3. `render-record-compare <labelA> <startA> <endA> <labelB> <startB> <endB>` (T3 对比)

```bash
python3 scripts/schedule_cli.py render-record-compare 6月 2026-06-01 2026-06-30 7月 2026-07-01 2026-07-31
```

**输出**:`record/compare/<labelA>_vs_<labelB>_record_compare.html`

**4 段视觉**:首屏 4 卡对比(标签 A/B + 时长差/总分钟差) + **7 维并排差异柱** + AI 钩子。

### 4. `render-record-compare-months <YYYY-MM> <YYYY-MM>` (T3 简写)

```bash
python3 scripts/schedule_cli.py render-record-compare-months 2026-06 2026-07
```

**输出**:`record/compare/2026年6月_vs_2026年7月_record_compare.html`

整月自动展开为 `YYYY-MM-01 ~ YYYY-MM+1-01`,等效 `render-record-compare` 调用。

### 5. `render-record-category <日期> <category>` (T4 单日单类)

```bash
python3 scripts/schedule_cli.py render-record-category 2026-07-15 健身
```

**输出**:`record/category/<cat>_<date>_to_<date>_record_category.html`

**触发词**:"7/15 健身什么时候做的"

### 6. `render-record-category-range <开始> <结束> <category>` (T4 区间单类)

```bash
python3 scripts/schedule_cli.py render-record-category-range 2026-07-01 2026-07-31 健身
```

**输出**:`record/category/<cat>_<start>_to_<end>_record_category.html`

**核心视觉**:**24h × N 天热力图** — 行为模式感知(如"上午+傍晚双峰健身")。

### 7. `render-record-anomaly [--window N]` (T5 异常检测)

```bash
# 默认 7 天窗口
python3 scripts/schedule_cli.py render-record-anomaly
# 自定义窗口
python3 scripts/schedule_cli.py render-record-anomaly --window 14
```

**输出**:`record/anomaly/<today>_w<N>_record_anomaly.html`

**核心视觉**:**7 维雷达 SVG**(蓝=当前 / 灰=基线 30 天) + 红/黄框异常详情 + AI 钩子。

**触发词**:"最近状态" / "有没有异常"

### 8. `render-record-report <日期>` (兼容旧命令)

```bash
python3 scripts/schedule_cli.py render-record-report 2026-07-15
```

**等价于** `render-record-day`,保留命令避免破坏现有调用方。**输出**:`record/day/2026-07-15_record_day.html`

### 错误处理

所有命令**目录不存在时报错退出**,错误文案带字段名 + 当前值 + 期望值 + 修复建议:

```json
{
  "status": "error",
  "message": "HTML 输出目录不存在: 字段 record_dir(派生自环境变量 SKILLS_DB_PATH),当前值 D:\\.db\\schedule_html\\record,期望 SKILLS_DB_PATH/schedule_html/record/ 存在,建议: mkdir -p D:\\.db\\schedule_html\\record 或检查 SKILLS_DB_PATH 环境变量"
}
```

### 触发词路由表(AI 协同时查此表)

| 用户说 | 调 |
|---|---|
| 查作息 / 查作息报告 / 查作息 YYYY-MM-DD / 昨天我做了什么 | `render-record-day <date>` |
| 这一周 / 最近 7 天 / 7/13~7/19 看看 | `render-record-range <start> <end>` |
| 6 月 vs 7 月 / 整月对比 | `render-record-compare-months 2026-06 2026-07` |
| 这周 vs 上周 / 这月 vs 上月 / 两段时间对比 | `render-record-compare <labelA> ... <labelB> ...` |
| 健身习惯 / 健身什么时候做的 / 健身频次 | `render-record-category-range <start> <end> <category>` |
| 7/15 健身时段分布(单日) | `render-record-category <date> <category>` |
| 最近状态 / 有没有异常 / 异常检测 | `render-record-anomaly --window 7` |
| 兼容旧调用 | `render-record-report <date>` |

