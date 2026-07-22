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

## 二、计划（旧版 24-hour，**保留兼容**）

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

## 三、计划（**新版事件型 — 推荐使用**）

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
