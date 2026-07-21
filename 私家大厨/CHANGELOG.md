# 私家大厨 · CHANGELOG

> 记录每次重要改动。版本号遵循 [Semantic Versioning](https://semver.org/)。
> 配套文档:`SKILL.md` / `references/` / `features/` / `templates/`

---

## [Unreleased] — 5 层架构改造

> 进行中(2026-07-21 开始)。所有改动都有 `.bak.20260721_155955` 备份。

### 改造动机
- 原 SKILL 缺少 5 层架构约束(契约层不统一、业务层无 validators、数据层无封装)
- 录入食谱时,JSON 模板允许字段缺失,AI 容易偷懒
- 缺 changelog / 缺"管什么不管什么"说明,演进困难

### 改动清单

#### ① 文档层
- **SKILL.md**:新增"管什么 / 不管什么"段
- **SKILL.md**:"AI使用规范"新增"全字段必填(硬规则 · 无跳过通道)"小节
- **CHANGELOG.md**:本文档,新建
- **features/add.md**:加错误处理范式(待改)
- **私家大厨.html**:同步上述改动(待改)

#### ③ 业务层
- **scripts/validators.py**:新建(待做)
  - `validate_full_coverage(data)` — 全字段必填校验
  - `build_user_question(missing_fields)` — 生成"一次性问用户"问题
  - `FIELD_LABELS` 字典 — 字段名 → 中文标签

#### ② 契约层
- **scripts/recipe_import.py**:改用 validators.py(待做)
- 统一 `{status, data, message}` 输出格式(待做)
- 错误信息含字段名+当前值+期望值+怎么修(待做)

#### ④ 数据层
- **scripts/db.py**:新建,封装 SQL+事务(待做)
- 自动 .bak 备份机制(待做)
- migration 脚本目录(待做)

### 改动前必答 3 问
1. **影响哪些文件?** 见上"改动清单"4 层共 8+ 个文件
2. **有没有数据迁移?** 无。schema 不动,只改校验逻辑
3. **回滚方案?** 所有文件 `.bak.20260721_155955` 备份,一键还原

---

## [4.0] — 2026-07-10(改造前基线)

> 这是 5 层架构改造前的最后一个稳定版本。

- 17 张表 schema 完整
- 30 个唤醒词(后增到 35)
- 8 大功能模块
- 录入食谱支持传统 CLI 和 JSON 导入
- 无 changelog(本次补建)
