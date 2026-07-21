# 私家大厨 · CHANGELOG

> 记录每次重要改动。版本号遵循 [Semantic Versioning](https://semver.org/)。
> 配套文档:`SKILL.md` / `references/` / `features/` / `templates/`

---

## [5.1] — 2026-07-21 — 修复"辣椒炒肉"端到端测试发现的 5+1 个 bug + 完善 SKILL

> 全部 Phase 7-12 精准完成(2026-07-21 16:40 → 17:00,约 20 分钟)。所有改动基于 v5.0 备份 `.bak.20260721_155955`。
> 自检 30/30 通过。第二道菜"西红柿炒鸡蛋"端到端测试通过。

### 改造动机
- v5.0 端到端测试"辣椒炒肉"时,对抗式审查发现 5+1 个 bug
- 从第一性原理看,bug 根因是 **SKILL 工具不完整**——校验不严 + 枚举不全 + Schema 缺字段 + 推算规则模糊
- 不修工具只修数据 = 治标,下次录第二道菜还会踩同一坑

### 修复的 5+1 个 bug

| # | Bug | 修法 |
|---|---|---|
| 1 | step_ingredients 表**没 unit 字段**,JSON 写了 unit 数据库没存 | migration 加列(v5.1) |
| 2 | `meal_types` 用了"午"(不在标准值) | 改 "中"和"晚" |
| 3 | `cooking_methods` 用了"煸"(不在标准值) | 扩 enums 加 "煸" |
| 4 | `flavors` 用了"香"(不在标准值) | 扩 enums 加 "香" |
| 5 | `introduced_at` 用了"第N步加入"格式 | 改 "中途加入" |
| 6 | `diet_tags`/`background` 该推算/补常识的标了 null | AI 主动推算 + 补常识 |

### 改动清单(全部完成)

#### ① 文档层
- **SKILL.md**:新增"字段推算边界"段(必问用户 / 必推算 / 可补常识 / 可显式 null 四类)
- **references/enums.py**:**新建 6.8 KB**(15 个枚举 + 输入归一化 + 软删除常量)
- **CHANGELOG.md**:v5.1 段(本段)

#### ③ 业务层
- **scripts/validators.py**:升级 13.7 → 23.2 KB
  - 改用 `references/enums.py` 读合法值(单一事实来源)
  - 新增 `validate_step_structure()`:步骤子结构必填校验
  - 新增 `validate_step_ingredient_inventory()`:校验 step.ingredients_used 引用的食材都在 ingredients 里
  - 枚举强校验:支持别名归一化(发现"午"自动建议"中",并提示用户)

#### ② 契约层
- **scripts/recipe_import.py**:改用 enums.py(3 处"已废弃"→`enums.ARCHIVED_STATUS`)
- **scripts/recipe_json_validate.py**:改用 enums.py(动态注入 schema 合法值,消除 2 套标准不一致)
- **recipes 写入路径**:`INSERT INTO step_ingredients` 加 `unit` 列(配合 migration)

#### ④ 数据层
- **scripts/migrations/001_add_step_ingredients_unit.sql**:**新建**(ADD COLUMN unit)
- **scripts/migrations/001_rollback.sql**:**新建**(回滚用)
- **scripts/db.py**:用 `db.run_migration()` 跑 migration,自动备份

### 改动前 3 问(回顾)
1. **影响哪些文件?** 5 个层共 9+ 个文件,新建 3 个文件(references/enums.py、2 个 migration)
2. **有没有数据迁移?** **有 1 个**——ALTER TABLE step_ingredients ADD COLUMN unit(SQLite 安全,默认 NULL)
3. **回滚方案?** migration 自带 rollback.sql,其他文件有 `.bak.20260721_155955` 备份

### 自检结果
- **5 层 + 6 特性自检**:30/30 通过(从 v5.0 的 24/24 提升)
  - 文档层 7/7(+管什么/不管什么 + 全字段必填 + 字段推算边界 + enums.py + migrations)
  - 契约层 5/5(recipe_import + recipe_json_validate 都改用 enums)
  - 业务层 5/5(枚举强校验 + 步骤子结构 + 食材引用校验)
  - 数据层 7/7(migration + unit 列填了 100%)
  - 6 大特性 6/6

### 端到端验证
- **"辣椒炒肉"重录**(merge 模式,自动覆盖):6+1 个 bug 全部修复
  - 11 食材 / 6 步 / 0 tips / 0 techniques / 0 history / 0 relations
  - `step_ingredients` **9/9 行 unit 列全部填了**(之前是 0/9)
- **"西红柿炒鸡蛋"录入**(新流程):5 食材 / 5 步 / 2 tips / 1 technique / 2 炊具 / 营养 / 背景
  - 验证 `unit` 字段同样填了 9/9 行
  - 验证 step 必填子结构(action/sequence/duration/heat_level)全部存在
  - 验证步骤食材引用全部合法

### 已知问题(留给将来)
- **recipe_json_validate.py 仍不接受 null**(JSON Schema 严格模式 vs validators.py 接受 null,核心设计选择)。**建议未来**:统一两套校验,或者放弃 recipe_json_validate.py 让 recipe_import.py 走 validators。
- **recipe_manager.py 仍有 1 处硬编码"已废弃"**(list / show 的过滤逻辑)。**建议未来**:一并改用 `enums.ARCHIVED_STATUS`。
- **17 个 manager 脚本未迁移到 db.py** ——风险/价值比不高,db.py 作为新代码入口,新功能用它。

---

## [5.0] — 2026-07-21 — 5 层架构改造

---

## [4.0] — 2026-07-10(改造前基线)

> 这是 5 层架构改造前的最后一个稳定版本。

- 17 张表 schema 完整
- 30 个唤醒词(后增到 35)
- 8 大功能模块
- 录入食谱支持传统 CLI 和 JSON 导入
- 无 changelog(本次补建)
