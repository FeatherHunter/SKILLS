# 私家大厨变更日志

记录所有重大修改、决策、数据迁移、破坏性变更。
约定:① 破坏性变更提前公告;② 数据迁移必须有备份 + 回滚方案;③ 每个版本日期戳 + 改动清单。

---

## 2026-07-22 - L1 阶段完工(98 字段全 NOT NULL)

### 改动清单

#### L1-A:DB schema 兜底
- **17 张表 DDL**:`init_db.py` 全量改
- **98 字段 NOT NULL**(含 17 PK),**仅 tips 2 字段可空**(允许"菜级 tip")
- **2 个 DEFAULT 去掉**:`recipes.status DEFAULT '未做'` 和 `ingredients.is_optional DEFAULT 0`,完全靠 validators 必传
- **2 个 DEFAULT 保留**:`recipes.created_at` / `updated_at` 保留 `CURRENT_TIMESTAMP`(Python 端易漏,系统必需)
- **migration 004**:`migrations/004_all_fields_not_null.sql` (7.6KB) 作为 init_db.py 的只读副本
- **⚠️ SQLite 限制**:ALTER TABLE 不能改 NOT NULL,所以 004 不是真"迁移脚本",而是 DDL 快照。回滚 = 恢复 init_db.py.bak

#### L1-B:清库 + 重 init
- **备份**:`.bak.20260722_142800_pre_L1_clean` (290KB)
- **删真实 DB**:`D:\2Study\StudyNotes\.db\chef_data.db`
- **重 init**:`python scripts/init_db.py` 重建 17 张表(空)
- **临时 DB 验证**:`test_db_tmp` 隔离,跑 6 项检查全通过

### 用户决策(拍板记录)
- **R2**:98 字段全 NOT NULL ✓
- **R3**:`status` / `is_optional` 去掉 DEFAULT,完全靠 validators ✓
- **R1**(tips 表 SET NULL 矛盾):改回 tips.step_id/ingredient_id 可空 + SET NULL ✓
- **R4**(业务校验):选"对话流申请制",L2 阶段 validators 加:优先要求 3 个 ID,迫不得已才允许不全

### L1 验证 6/6 全通过
1. ✓ DB schema 检查(98 字段 NOT NULL)
2. ✓ 17 张表全部 0 行(清库成功)
3. ✓ init_db.py 可重入
4. ✓ DEFAULT 正确(created_at 自动填)
5. ✓ NOT NULL 兜底(INSERT 缺 name 报错)
6. ✓ FK CASCADE(删 recipes 子表自动清空)

### 文件改动
- `scripts/init_db.py`(13KB → 改 17 表 DDL)
- `scripts/init_db.py.bak.20260722_142500`(备份,13KB)
- `scripts/migrations/004_all_fields_not_null.sql`(新,7.6KB)

### 数据状态
- 真实 DB:空库,98 字段全 NOT NULL,1 道菜留底在 `recipes_export_20260722_clean.json`

---

## 2026-07-22 - 重构启动 L0 阶段

### 背景
按 SKILL 五层架构规范完整重构。决策:
1. 不允许任何占位符(`""`/`"未知"`/`"未提供"` 等 + 数字 `-1` + 数字 `0` 除 7 个白名单字段外)
2. 1:1 UNIQUE 表每菜必录 1 行(`nutrition_info` / `background_knowledge` 行内字段全 NOT NULL)
3. 已废弃菜保留原值(软删除只改 status)
4. DB NOT NULL 是兜底墙,系统字段允许 DEFAULT(`_at` / `status` / `is_optional`),业务字段完全靠 validators 强制

### 数据准备
- **DB 备份**:`D:\2Study\StudyNotes\.db\chef_data.db` → `.bak.20260722_130832` (290KB)
- **孤儿清理**:删 2 个真孤儿 recipe_id 的子表残骸
  - `cooking_steps`:删 1 行(recipe_id=`d7ced93a-14af-4078-89c3-4b1c9b8beaeb`,action="测试步骤")
  - `cookware`:删 2 行(recipe_id=`42c7c24f-8a5f-4bde-8c20-048efa09617f`,name="炒锅"/"锅铲")
  - 备份:`.bak.20260722_134846_pre_orphan_clean`
- **完整留底**:1 道菜(辣椒炒肉)导出到 `D:\2Study\StudyNotes\.db\recipes_export_20260722.json` (16KB)

### 后续阶段
- [x] L0:DB NOT NULL 兜底 + 清库 + 重 init
- [ ] L2:recipe_import 调 validators + 16 个 manager 改用 db.py
- [ ] L3:CLI 统一三段式 + `--human` 开关 + 4 文档同步 + orchestrator
- [ ] 收尾测试:用 recipe_import.py 重新导入辣椒炒肉 JSON