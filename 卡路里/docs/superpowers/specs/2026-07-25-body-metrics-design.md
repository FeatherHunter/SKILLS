# body_metrics 身材数据录制 · 设计规格(spec)

> **For agentic workers:** 配套 plan 见 `docs/superpowers/plans/2026-07-25-body-metrics.md`
> 本文档是 brainstorm 输出(决策)。开发实施 → plan。

## Goal

为卡路里技能新增 2 套记录体系:
- **`记体脂`**:皮褶钳测 7 个点 + Jackson-Pollock 公式算体脂率
- **`记围度`**:13 个身体部位围度(cm)日常测量

**严格对齐 SKILL开发总纲V1.0**(6 大特性 + 8 反模式 + 5 层骨架 + §03 触发词 v2 + §04 单工铁律 + §05 工程仪式 + §06 演化)。

## 6 大特性对照

| 特性 | 本方案对应 |
|---|---|
| ① 可识别 Discoverable | 8 个 trigger 词(2 套 × 4 元组),各配 2-3 个口语化变体,SKILL.md §触发词速查表 显式列出 |
| ② 可验证 Verifiable | 写入前 `list --latest` 看当前状态;写入后回执 (id + timestamp + 受影响行数);稳定自增主键 ID;每张表 `created_at + updated_at` 审计字段;幂等性(CLI 调用 N 次结果一致)|
| ③ 可恢复 Recoverable | 原子事务(BEGIN → COMMIT);`.bak` 备份 + `git revert` 回滚;软删除 `is_deprecated=1`(不 DELETE) |
| ④ 可约束 Constrainable | 硬规则 `validators.py` 早失败 + 错误信息含字段名 + 当前值 + 期望值 + 怎么修;**无 `--force` 跳过通道**;NOT NULL 严格 |
| ⑤ 可联动 Composable | 所有 CLI 输出 `{status, data, message}` 三段式 JSON(--as_dict 标志切换);稳定字段名;飞书回执可被其他 skill 引用 |
| ⑥ 可演进 Evolve-able | 5 层骨架(每个文件单一职责);HTML 镜像(SKILL.md ↔ 卡路里.html 同 commit);版本号 bump;schema migration(独立 .bak + git commit 备份)|

## 8 反模式检查

| 反模式 | 防御 |
|---|---|
| 黑盒 CLI | 错误信息必含字段名 + 当前值 + 期望值 + 怎么修 |
| 隐式状态 | 所有状态写 SQLite;无内存缓存 |
| 魔法字符串 | `source_constants.py` 集中 `SOURCE_HOME_CALIPER = 'home_caliper'` 等 |
| 静默失败 | `except` 必须 stderr + `sys.exit(1)` |
| 紧耦合 | skill 之间通过 JSON 字段通信,不互相 import |
| 慢反馈 | CLI 命令秒级返回;批处理 5-10 秒输出进度 |
| 中文 CLI 乱码 | Python `subprocess.run([..., str_arg, ...], encoding='utf-8')` |
| **CLI 不返回结构化 JSON** | **必须 `--as_dict=True`** 返回 `{status, data, message}` |

## Decision Log(Brainstorm Q1-Q6)

| Q | 决策 | V1.0 对应 |
|---|---|---|
| Q1 部分 NULL | 体脂钳:7 皮褶全 NOT NULL · 围度:记录级必填(date + ≥1 围度),列级可 NULL | ④ 可约束 |
| Q2 trigger | 2 个分开(`记体脂` + `记围度`)| ① 可识别 |
| Q3 CLI 架构 | 2 个分脚本(`body_composition.py` + `body_measurements.py`)| ① 可识别 + ⑥ 可演进 |
| Q4 体脂率 | CLI 用 Jackson-Pollock 公式自动算,`--body-fat-pct` 跳过(医院测)| ② 可验证(可重算) |
| Q5 CLI 命令 | add / list / delete / trend(4 命令)| ① 可识别 + ② 可验证 |
| Q6 HTML wizard | 单页 + 分组 `<details>`(飞书 webview 兼容)| §04 单工铁律 |

## File Structure(5 层骨架)

### ① 数据层 `scripts/db.py`(扩展)

```sql
-- V1.0 §02 第 ① "所有 SQL 走 db.py"

-- body_composition:体脂钳测,7 皮钳 NOT NULL 严格
CREATE TABLE body_composition (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    source TEXT NOT NULL,
    age INTEGER,
    sex TEXT CHECK (sex IN ('male', 'female')),
    caliper_chest_mm REAL NOT NULL CHECK (caliper_chest_mm > 0 AND caliper_chest_mm < 100),
    caliper_abdominal_mm REAL NOT NULL CHECK (caliper_abdominal_mm > 0 AND caliper_abdominal_mm < 100),
    caliper_thigh_mm REAL NOT NULL CHECK (caliper_thigh_mm > 0 AND caliper_thigh_mm < 100),
    caliper_tricep_mm REAL NOT NULL CHECK (caliper_tricep_mm > 0 AND caliper_tricep_mm < 100),
    caliper_subscapular_mm REAL NOT NULL CHECK (caliper_subscapular_mm > 0 AND caliper_subscapular_mm < 100),
    caliper_suprailiac_mm REAL NOT NULL CHECK (caliper_suprailiac_mm > 0 AND caliper_suprailiac_mm < 100),
    caliper_midaxillary_mm REAL NOT NULL CHECK (caliper_midaxillary_mm > 0 AND caliper_midaxillary_mm < 100),
    body_fat_pct REAL NOT NULL CHECK (body_fat_pct >= 0 AND body_fat_pct <= 60),
    calculated_at TEXT,
    note TEXT DEFAULT '',
    is_deprecated INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_body_composition_date ON body_composition(date);

-- body_measurements:围度,记录级必填,列级可 NULL
CREATE TABLE body_measurements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    chest_cm REAL CHECK (chest_cm IS NULL OR (chest_cm > 20 AND chest_cm < 200)),
    waist_cm REAL CHECK (waist_cm IS NULL OR (waist_cm > 20 AND waist_cm < 200)),
    abdomen_cm REAL CHECK (abdomen_cm IS NULL OR (abdomen_cm > 20 AND abdomen_cm < 200)),
    hip_cm REAL CHECK (hip_cm IS NULL OR (hip_cm > 20 AND hip_cm < 200)),
    left_thigh_cm REAL CHECK (left_thigh_cm IS NULL OR (left_thigh_cm > 10 AND left_thigh_cm < 100)),
    right_thigh_cm REAL CHECK (right_thigh_cm IS NULL OR (right_thigh_cm > 10 AND right_thigh_cm < 100)),
    left_calf_cm REAL CHECK (left_calf_cm IS NULL OR (left_calf_cm > 10 AND left_calf_cm < 80)),
    right_calf_cm REAL CHECK (right_calf_cm IS NULL OR (right_calf_cm > 10 AND right_calf_cm < 80)),
    left_arm_cm REAL CHECK (left_arm_cm IS NULL OR (left_arm_cm > 10 AND left_arm_cm < 60)),
    right_arm_cm REAL CHECK (right_arm_cm IS NULL OR (right_arm_cm > 10 AND right_arm_cm < 60)),
    left_forearm_cm REAL CHECK (left_forearm_cm IS NULL OR (left_forearm_cm > 10 AND left_forearm_cm < 50)),
    right_forearm_cm REAL CHECK (right_forearm_cm IS NULL OR (right_forearm_cm > 10 AND right_forearm_cm < 50)),
    shoulder_cm REAL CHECK (shoulder_cm IS NULL OR (shoulder_cm > 20 AND shoulder_cm < 200)),
    note TEXT DEFAULT '',
    is_deprecated INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_body_measurements_date ON body_measurements(date);

-- 通过 trigger 函数实现记录级必填(date + >=1 围度)
```

### ② 操作层(2 个 CLI 脚本)

**`scripts/body_composition.py`** —— 4 子命令:
```
add     --date YYYY-MM-DD --source {home_caliper,hospital}
        --caliper-chest MM --caliper-abdominal MM --caliper-thigh MM
        --caliper-tricep MM --caliper-subscapular MM
        --caliper-suprailiac MM --caliper-midaxillary MM
        [--age N --sex {male,female}] [--body-fat-pct X] [--note TEXT]
list    [--days N | --date-from X --date-to Y]
delete  --id N
trend   --metric body_fat_pct [--days 30] [--date-from X]
```

**`scripts/body_measurements.py`** —— 4 子命令:
```
add     --date YYYY-MM-DD [--chest-cm N --waist-cm N --abdomen-cm N --hip-cm N ... 13 围度]
        (允许部分 NULL,但至少 1 个围度必填)
list    [--days N] [--date-from X --date-to Y]
delete  --id N
trend   --metric <col_name> [--days 30]
```

**`scripts/source_constants.py`** —— V1.0 §02 第 ⑧ 反模式"魔法字符串"消除:
```python
SOURCE_HOME_CALIPER = 'home_caliper'
SOURCE_HOSPITAL = 'hospital'
SOURCE_CHOICES = (SOURCE_HOME_CALIPER, SOURCE_HOSPITAL)
```

### ③ 规则层 `scripts/validators.py`

```python
# V1.0 §02 第 ④ 可约束 + 第 ⑧ 反模式"魔法字符串"

def validate_composition_input(args) -> None:
    """早失败 + 错误信息含字段名 + 当前值 + 期望值 + 怎么修"""
    if not args.date or not _is_valid_iso_date(args.date):
        _fail('date', args.date, 'YYYY-MM-DD', 'fix: --date 2026-07-25')
    if args.source not in SOURCE_CHOICES:
        _fail('source', args.source, SOURCE_CHOICES, f'fix: --source {" --source ".join(SOURCE_CHOICES)}')
    # ... 7 皮褶值范围校验(CHECK 在 DB 层,但 CLI 早失败给好错误信息)

def validate_measurement_input(args) -> None:
    """记录级必填:date + ≥1 围度"""
    filled = [v for v in [args.chest_cm, args.waist_cm, ...] if v is not None]
    if not filled:
        _fail('围度', 'empty', '至少 1 个', 'fix: --waist-cm 85')
```

### ④ 接口层(统一 JSON 输出)

所有 CLI 默认人类可读(print),`--as_dict` 标志返回 JSON:
```json
{
  "status": "ok",
  "data": {"id": 42, "date": "2026-07-25", "body_fat_pct": 23.5, ...},
  "message": "已记录 1 条 body_composition:2026-07-25 体脂率 23.5%"
}
```

失败:
```json
{
  "status": "fail",
  "data": null,
  "message": "field=date, value=None, expected=YYYY-MM-DD, fix=--date 2026-07-25"
}
```

### ⑤ 文档层(更新 SKILL.md / 卡路里.html)

- frontmatter `触发词:` 加 8 个新 trigger(2 套 × 4)
- §触发词速查表 加 4 行为 2 个新 trigger 列(查 + 记/改/删归类共用 HTML 行)
- §完整 HTML 模板清单 加 2 行(body_composition_wizard + body_measurements_wizard)
- §核心原则 加"V1.0 §02 第 ⑤ 可联动"对照说明
- `卡路里.html` 镜像同步

### HTML Wizard(过程型 HTML + §04 单工铁律)

**`templates/body_composition_wizard.html`**:
- 单页 + 3 个 `<details>` 分组(基本信息 / 7 皮褶 / 备注)
- 默认:日期+source 展开,7 皮褶折叠
- 顶部:状态栏(本次新增会立即显示)
- 底部:📋 复制 prompt 按钮
- `<!--INJECT-DATA-->` 占位符(渲染脚本注入当前用户最近一次数据供对照)

**`templates/body_measurements_wizard.html`**:
- 单页 + 3 个 `<details>` 分组(基本信息 / 上身围度 / 下身围度)
- 同结构

**`scripts/render_body_composition_wizard.py`** / `render_body_measurements_wizard.py`**:
- 注入 `{status, data, message}` to `window.__DATA__`
- 默认输出 `<DATA_DIR>/calorie_html/<cmd>_<YYYYMMDD>_<HHMMSS>.html`

### Tests(5 层 ② ③ ④ 全覆盖)

**`tests/test_body_composition.py`**:
- test_add_missing_date_fails(早失败)
- test_add_with_7_points_succeeds_and_computes_body_fat_pct
- test_add_with_explicit_body_fat_pct_skips_calculation
- test_add_with_invalid_caliper_value_fails(DB CHECK 也 fail)
- test_list_returns_recent
- test_delete_by_id_soft_deletes(is_deprecated=1)
- test_as_dict_returns_structured_json

**`tests/test_body_measurements.py`**:
- test_add_no_metrics_fails(记录级必填)
- test_add_one_metric_succeeds(列级可 NULL)
- test_add_all_13_metrics_succeeds
- test_trend_returns_time_series

**`tests/test_validators.py`**:
- test_error_message_contains_field_and_suggested_fix

## Acceptance Criteria

1. ✅ V1.0 §02 6 大特性 + 8 反模式 全对齐
2. ✅ V1.0 §03 触发词 v2 矩阵(8 trigger, 各自口语化变体 2-3 个)
3. ✅ V1.0 §04 单工铁律(过程型 HTML + 复制 prompt 按钮)
4. ✅ V1.0 §05 工程仪式 "改动前 3 问" 已答
5. ✅ pytest 通过(新 11 测试 + 旧 16 不破)
6. ✅ check_trigger_consistency.py 三边一致(73 → 81)
7. ✅ Fresh Agent 黑盒测试(钩子 ⑥):8 个 trigger 全识别 HTML 路径
8. ✅ HTML 飞书 webview 兼容(单页 + 分组 + base64 嵌图)
9. ✅ CLI `--as_dict` 返回结构化 JSON
10. ✅ DB CHECK 约束(硬规则下沉)

## Out of Scope(本 commit 不做)

- 趋势可视化 SVG(后续 commit)
- 体脂钳/围度合并到主页 dashboard(后续 commit)
- DEXA/InBody 接入(未来 body_composition 扩展)
