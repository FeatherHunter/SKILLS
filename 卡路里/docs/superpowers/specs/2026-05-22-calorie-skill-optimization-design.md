# 卡路里 SKILL 全面优化设计文档

> 日期：2026-05-22
> 范围：38 个问题全部修复
> 方法：深度拆分 + 文档瘦身 + Bug 修复 + 配置重生成

---

## 1. 文件结构重组

### 1.1 新建 `scripts/db_utils.py`

提取 4 个脚本中重复的 `_find_db_path` 函数（约 20 行 x 4 = 80 行重复代码）为共享模块。

```python
# scripts/db_utils.py
# 导出: find_db_path(skill_dir, db_filename), get_db(db_path)

def find_db_path(skill_dir, db_filename):
    """三层查找DB路径：环境变量 > 技能目录 > 父目录.db"""
    # 与现有 _find_db_path 逻辑完全一致
    ...

def get_db(db_path):
    """获取数据库连接，自动初始化"""
    if not db_path.exists():
        # 不在这里 init，由各脚本自己负责
        pass
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
```

### 1.2 新建 `scripts/analysis.py`

从 `calorie_tracker.py` 第 1077-1823 行整体搬出：

- `_parse_date()`、`_days_between()`
- 体重分析：`weight_trend()`、`weight_compare()`、`weight_milestone()`、`weight_volatility()`
- 饮食分析：`diet_calorie_trend()`、`diet_macro_ratio()`、`diet_food_ranking()`、`diet_deficit_analysis()`
- 运动分析：`exercise_trend()`、`exercise_type_breakdown()`、`exercise_deficit_contribution()`
- 统一入口：`weight_analysis()`、`diet_analysis()`、`exercise_analysis()`、`dashboard()`

依赖：从 `db_utils` 导入 `find_db_path`/`get_db`，从 `calorie_tracker` 导入 `get_goal`/`get_weight_goal`。

**无循环依赖**：`calorie_tracker.py` 只导出 CRUD 函数（`get_goal`、`get_weight_goal`、`add_entry` 等），不 import analysis.py。

### 1.3 瘦身 `calorie_tracker.py`

- 删除第 1077 行以后所有分析代码
- 改用 `from db_utils import find_db_path, get_db`
- 最终约 500 行：init_db + CRUD + CLI

### 1.4 改造其他脚本

`exercise_tracker.py`、`fitness_goals.py`、`sleep_tracker.py`：
- 删除各自的 `_find_db_path` 函数
- 改为 `from db_utils import find_db_path`
- 保留各自的 `init_table()` 和业务逻辑

---

## 2. 代码 Bug 修复（15 项）

### P0 — 崩溃/数据丢失

| # | 文件 | 行号 | 问题 | 修复方案 |
|---|------|------|------|----------|
| 1 | calorie_tracker.py | 1186 | `weight_compare` 的 `first_last` 返回值解包错误，`fl1[1] - fl1[0]` 是数值减元组 | 修正解包：`first_w, first_date = fl1[0]; last_w = fl1[1]; change = last_w - first_w` |
| 2 | calorie_tracker.py | 525 | `set_weight_goal` 用 `INSERT OR REPLACE` 覆盖 calorie_goal 等字段 | 先 `UPDATE daily_goal SET weight_goal=?, goal_deadline=?, updated_at=? WHERE id=1`，若 `rowcount==0` 则 `INSERT INTO daily_goal (id, weight_goal, goal_deadline) VALUES (1, ?, ?)` |
| 3 | config-calorie.ts | queries | daily_goal/fitness_goals/sleep_records 无 date 列但生成了 `WHERE date = '{date}'` | generate_ts_config.py 检测表是否有 date 列，无则生成 `SELECT * FROM {table} ORDER BY id DESC` |

### P1 — 逻辑错误

| # | 文件 | 行号 | 问题 | 修复方案 |
|---|------|------|------|----------|
| 4 | calorie_tracker.py | 1731 | `weight_analysis('compare')` 自己和自己比 | 改为接受 `compare_start`/`compare_end` 参数，无参时默认"上一个等长周期" |
| 5 | calorie_tracker.py | 1243 | `weight_milestone` 用 `(max-min)/30` 算日均 | 改用首尾差值：`(first_weight - last_weight) / span` |
| 6 | calorie_tracker.py | 1445 | `eval_pct` 硬编码 30%/35% | 改为从 `get_goal()` 读取实际目标值计算占比 |
| 7 | calorie_tracker.py | 1024 | `add-product` CLI 用 `'0'` 字符串判断 | 改为 `float(sys.argv[7]) or None` |
| 8 | SKILL.md | 173 | protein_goal 默认值 156 vs 代码 150 | 统一为 150 |

### P2 — 代码质量

| # | 文件 | 行号 | 问题 | 修复方案 |
|---|------|------|------|----------|
| 9 | calorie_tracker.py | 194/1437/333 | 死代码：`complete_goal`、`macro_target_pct`、未用的 `meal` | 删除 |
| 10 | calorie_tracker.py | 多处 | 函数内重复 import（8处） | 删除局部 import，用顶部 |
| 11 | calorie_tracker.py | 135/139/158/1097 | 裸 `except:` | 改为 `except Exception:` |
| 12 | calorie_tracker.py | 533-585 | `get_weight_goal()` 3次开关连接 | 合并为1次 |
| 13 | calorie_tracker.py | 1557/1691 | BMR `* 24 * 1.3` 硬编码2处 | 提取常量 `BMR_ACTIVITY_FACTOR = 1.3` |
| 14 | calorie_tracker.py | 833 | `update_product` f-string SQL | 改为参数化（白名单字段名拼接后用 `?` 占位） |
| 15 | calorie_tracker.py | 890 | `history()` SQL 字符串拼接 | 改为 `datetime.now() - timedelta(days=days)` 计算后传参 |

### fitness_goals.py 额外修复

- 删除 `complete_goal()` 函数（死代码，与 SKILL.md 矛盾）
- 删除 `_find_db_path`（改用 db_utils）

### generate_ts_config.py 额外修复

- `to_ts_type`：`INTEGER` → `number`，`REAL` → `number`，`TEXT` → `string`
- `generate_table_fields`：bedtime/wake_time 不再被 `"time" in name` 误命中
- `carbohydrates` 加 unit 检测：`"carbohydrates" in name` → `"克"`
- `table_labels` 加 `"sleep_records": "睡眠记录"`
- 无 date 列的表生成不同的查询模板

### sleep_tracker.py / exercise_tracker.py

- 删除 `_find_db_path`，改用 db_utils
- sleep_tracker.py 的 `time.time()` 时间戳改为 `datetime.now().isoformat()` 统一格式

---

## 3. SKILL.md 瘦身（625行 → ~300行）

### 删除内容

1. **数据库表结构**（第 151-252 行）→ 移入 `references/database_schema.md`，SKILL.md 只留一行指向
2. **触发词重复**（第 376-547 行中的触发词列表）→ 保留第 20-120 行的帮助区作为唯一触发词来源，AI 触发指引区只保留流程逻辑
3. **nutrition_products 孤立字段表**（第 236-252 行）→ 归入 database_schema.md

### 优化内容

1. **硬编码路径** `workspace/skills/卡路里/` → 改为 `scripts/`
2. **补充说明**：`fitness_goals` 和 `sleep_records` 由各自脚本 `init_table()` 创建
3. **命令行用法区**：补充 exercise_tracker.py、fitness_goals.py、sleep_tracker.py 的 CLI 示例

---

## 4. 文档补全

### references/database_schema.md

- 补全 `fitness_goals` 表定义（字段、索引）
- 补全 `sleep_records` 表定义（字段、索引、归属规则）
- 补全 `idx_product_name` 索引说明
- 更新表关系图

### references/analysis_api.md

- 补全 `dashboard()` 的输出格式说明
- 确认函数签名与 analysis.py 一致

---

## 5. 执行顺序

1. 创建 `scripts/db_utils.py`
2. 创建 `scripts/analysis.py`（从 calorie_tracker.py 搬出）
3. 改造 `calorie_tracker.py`（删分析代码、用 db_utils、修 bug）
4. 改造 `exercise_tracker.py`（用 db_utils）
5. 改造 `fitness_goals.py`（用 db_utils、删死代码）
6. 改造 `sleep_tracker.py`（用 db_utils、统一时间格式）
7. 修复 `generate_ts_config.py`（5 个 bug）
8. 瘦身 `SKILL.md`
9. 补全 `references/database_schema.md`
10. 补全 `references/analysis_api.md`
11. 重新生成 `config-calorie.ts`
12. 验证：运行各脚本确认无报错

---

## 6. 附加项

- `scripts/__pycache__/` 已存在于文件系统中，确认 `.gitignore` 已覆盖（添加 `__pycache__/` 规则）
