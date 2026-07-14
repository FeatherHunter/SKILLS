# ensure-plan-event 幂等键不严 · 未修复 Bug 存档

> **状态**:BUG 未修(代码未动)。下次在飞书 DM 里跟小琢说"加载 ensure-plan-event-idempotency-bug",从这个 md 继续讨论修复。

---

## 一句话结论

`schedule_db.py` 的 `search_plan_event`(line 790-808)用 `(date, title)` 做幂等键,**但 title 每次可能略不同**(AI 拼装差异),导致同 `(date, time_start, time_end)` 的多次"落地健身计划"全部都 INSERT,产生 is_active=1 重复记录。

**真解**:幂等键升级为 `(date, time_start, time_end)`,title 变化不算"新事件"。

---

## 真实数据(2026-07-12 ~ 2026-07-16)

### 各日"同 (date, time_start, time_end) 多条 is_active=1"统计

| 日期 | 总条数 | 重复时段数 | 状态 |
|---|---|---|---|
| 2026-07-12 | 19 | 0 | 干净(但 13:27/13:58/15:58 三批写入) |
| 2026-07-13 | 25 | 4 | 12 条重复(4 段健身 × 3) |
| 2026-07-14 | 22 | 0 | 干净(可能没触发"落地健身计划") |
| 2026-07-15 | 8 | 4 | 8 条重复(4 段 × 2) |
| 2026-07-16 | 8 | 4 | 8 条重复(4 段 × 2) |
| 2026-07-17 | 4 | 0 | 干净(可能只手动加 4 条) |

### 7.13 重复样本(典型 bug 模式)

| id | time | title | feishu_event_id | created_at |
|---|---|---|---|---|
| 818 | 10:00-11:30 | `健身 上午·臂 10:00-11:30` | `37e02d6d...ade8_0` | 2026-07-12 13:27:41 |
| 823 | 10:00-11:30 | `健身·上午·臂 10:00` | `37e02d6d...ade8_0` | 2026-07-12 13:58:08 |
| 845 | 10:00-11:30 | `健身 上午·臂` | `37e02d6d...ade8_0` | 2026-07-12 15:58:04 |

**feishu_event_id 三条完全一样** → 飞书侧只 1 个 event;**title 三个都不一样** → `search_plan_event` 查 (date, title) 不命中 → 三次都 INSERT。

### 7.15 重复样本(2026-07-14 已部分处理)

| id | time | title | is_active | 说明 |
|---|---|---|---|---|
| 831 | 10:00-11:30 | `健身·上午·臂 10:00` | **0(已软删)** | 2026-07-14 23:16 软删 |
| 832 | 15:00-17:00 | `健身·下午·胸 15:00` | **0(已软删)** | 2026-07-14 23:16 软删 |
| 833 | 20:00-21:30 | `健身·晚上·腿 20:00` | 1 | **未处理** |
| 834 | 22:00-22:30 | `健身·居家·腹 22:00` | 1 | **未处理** |

### 7.16 重复样本(全部未处理)

| id | time | title | is_active |
|---|---|---|---|
| 835 | 10:00-11:30 | `健身·上午·肩 10:00` | 1 |
| 836 | 15:00-17:00 | `健身·下午·背 15:00` | 1 |
| 837 | 20:00-21:30 | `健身·晚上·臂 20:00` | 1 |
| 838 | 22:00-22:30 | `健身·居家·腹 22:00` | 1 |

---

## 根因(代码定位)

### 触发链路

1. 用户说"同步健身计划"或"落地健身计划"
2. 卡路里 AI 调作息管家的 `ensure-plan-event`(line 1137-1162 of `schedule_cli.py`)
3. `ensure-plan-event` 调 `ensure_plan_event`(`schedule_db.py` line 815)
4. `ensure_plan_event` 调 `search_plan_event(date, title)` 查重
5. `search_plan_event` 的 SQL(line 790-808):
   ```sql
   WHERE date = ? AND title = ? AND is_active = 1
   ```
6. **3 次调用的 title 略不同**(AI 拼装差异)→ 查不命中 → 都 INSERT

### 3 个 title 的来源(AI 拼装,不是代码生成)

| id | title | 拼装特征 |
|---|---|---|
| 818 | `健身 上午·臂 10:00-11:30` | 全名 + 完整时段 |
| 823 | `健身·上午·臂 10:00` | 用"·"连 + 简写时段 |
| 845 | `健身 上午·臂` | 全名 + 无时段 |

**这些 title 来自飞书 DM 里 AI 每次说"补计划 X 健身 Y"时的自然语言拼装**,不是 `plan_generator.py` 或 `xunji_bridge.py` 生成。

---

## 待修复方案(未实施)

### A 方案 · 幂等键升级(推荐 · 治根)

**改 1 处**:`schedule_db.py` line 790-808 的 `search_plan_event`,新增一个按时间查询的版本:

```python
def search_plan_event_by_time(date: str, time_start: str, time_end: str) -> dict | None:
    """按日期+时段查找活跃计划事件。返回匹配的第一条或 None。"""
    date = _normalize_date(date)
    conn = get_connection()
    try:
        _ensure_new_plans_schema(conn)
        c = conn.cursor()
        cols = ("id", "date", "time_start", "time_end", "title", "notes", "category",
                "feishu_event_id", "last_synced_at", "is_active", "completion", "completion_note")
        c.execute(f'''
            SELECT {", ".join(cols)}
            FROM schedule_plans
            WHERE date = ? AND time_start = ? AND time_end = ? AND is_active = 1
            ORDER BY id
            LIMIT 1
        ''', (date, time_start, time_end))
        r = c.fetchone()
        return dict(zip(cols, r)) if r else None
    finally:
        conn.close()
```

**改 1 处**:`schedule_db.py` line 815-870 的 `ensure_plan_event`,把查重调用换成新函数:

```python
# 旧(错)
existing = search_plan_event(date, title)

# 新(对)
existing = search_plan_event_by_time(date, time_start, time_end)
```

**注意**:`search_plan_event(date, title)` 保留(其他代码可能还在用,比如卡路里的 `search-plan-event` 命令)。新函数是**新增**,不是替换。

### C 方案 · 不推荐(已否决)

原来想"卡路里调用前先规范化 title",但**这等于改用户输入,丢信息** —— 用户可能喜欢"健身 上午·臂 10:00-11:30"这种带时段的写法。否决。

---

## 风险点(动手前要确认)

1. **`search_plan_event` 还在被其他代码用** — 改 `ensure_plan_event` 不会影响其他调用,但需要 grep 确认。
2. **历史脏数据** — 7.13/7.15/7.16 已有重复,代码改完后**新数据**不会再产生重复,但**老重复还在**。需要一次性清理(数据迁移)。
3. **飞书侧 1 event 对应 DB 多记录** — 飞书侧没事(4 个 event 干净),但 DB 端 12 条都指向同 1 个 feishu_event_id,清理时要保留一个,其余 `is_active=0`。
4. **没改的话"复盘"会被干扰** — 7.13 复盘时 4 段健身按 12 条算完成率,数据稀释。

---

## 验证清单(动手后逐条核)

- [ ] `schedule_db.py` line 815 的 `search_plan_event(date, title)` 调用已替换为 `search_plan_event_by_time(date, time_start, time_end)`
- [ ] `search_plan_event_by_time` 函数已加在 `schedule_db.py`(参照上面代码)
- [ ] 测试 1:同一个 (date, time_start, time_end) 调 2 次 ensure-plan-event(用不同 title) → 第 2 次返回 `{"action": "found"}`
- [ ] 测试 2:不同 (date, time_start, time_end) 调 2 次 → 第 2 次返回 `{"action": "created"}`
- [ ] 测试 3:`search_plan_event(date, title)`(原函数)仍正常工作(其他调用方不破)
- [ ] 全 schedule_plans 扫一遍"同 (date, time_start, time_end) 多条 is_active=1",出数据快照
- [ ] 出数据迁移方案(留 1 条/时段,其余 is_active=0)
- [ ] 改 SKILL.md 章节 10 补计划,加一句"重复调用按 (date, time_start, time_end) 幂等"
- [ ] 改作息管家.html,加 word-item 描述

---

## 操作历史

| 时间 | 操作 | 操作人 |
|---|---|---|
| 2026-07-14 23:16 | 软删 831/832(7.15 上午·臂 + 下午·胸) | 小琢(用户指令) |
| 2026-07-14 23:16 | 写本 md 存档 | 小琢 |

**未操作**:
- 833/834(7.15 晚上·腿 + 居家·腹)→ 按用户指令保留
- 835-838(7.16 全 4 段)→ 按用户指令保留
- 7.13 全 12 条 → 未处理
- schedule_db.py 修复 → 未实施

---

## 关键文件路径(下次讨论时直接打开)

- `D:\2Study\StudyNotes\SKILLS\作息管家\scripts\schedule_db.py` line 790(改这里)
- `D:\2Study\StudyNotes\SKILLS\作息管家\scripts\schedule_cli.py` line 1137(ensure-plan-event 入口,不用改,只是引用)
- `D:\2Study\StudyNotes\SKILLS\卡路里\SKILL.md` line 624-636(卡路里"落地健身计划"调作息 CLI 的说明)
- `D:\2Study\StudyNotes\SKILLS\作息管家\SKILL.md` 章节 10 补计划(改文档)

---

## 复盘讨论时的开场话术

下次在飞书 DM 说:

> "加载 ensure-plan-event-idempotency-bug"

小琢应该会读这个 md,然后跟你确认:
1. 是否开始动手改 A 方案
2. 是否同时清理历史脏数据(7.13/7.15/7.16)
3. 改完后做哪些验证