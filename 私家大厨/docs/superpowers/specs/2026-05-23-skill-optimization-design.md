# 私家大厨 SKILL 全面优化设计

> 日期：2026-05-23
> 状态：待审阅
> 范围：P0-P3 共 26 项问题修复
> 策略：最小修复（不重构架构，不提取公共代码）

---

## 背景

基于 SKILL-开发规范对私家大厨技能的全部 35 个文件逐行审查，发现 26 个问题，覆盖代码 Bug、代码质量、文档一致性和配置优化。

## 约束

- 最小修复：只修每个具体问题，不改变文件结构和函数签名
- 9 个 manager 的 `list()` 改名为 `list_items()` 等属于必要修复（遮蔽 Python 内置函数），不算重构
- `get_now()` 重复定义不处理（提取公共模块属于重构）
- 绝对路径保留，加注释说明

---

## P0：代码 Bug 修复（5项）

### 1. technique_manager.py — search 缺废弃过滤

**文件**：`scripts/technique_manager.py`
**位置**：L141-149
**问题**：`search()` SQL 没有 `status != '已废弃'` 过滤，废弃食谱的技法会出现在搜索结果
**修复**：WHERE 子句加 `AND r.status != '已废弃'`

### 2. step_ingredient_manager.py — quantity_used=0 误判

**文件**：`scripts/step_ingredient_manager.py`
**位置**：L96
**问题**：`if row['quantity_used']` 当值为 0 时判断为 False
**修复**：改为 `if row['quantity_used'] is not None`

### 3. history_manager.py — 验证变量不一致

**文件**：`scripts/history_manager.py`
**位置**：L21-60
**问题**：验证用 `rating_val`（float），INSERT 用原始 `rating`（字符串）
**修复**：验证通过后加 `rating = rating_val`

### 4. recipe_manager.py — derive 丢失参数

**文件**：`scripts/recipe_manager.py`
**位置**：L46-60
**问题**：derive 选项只传 `name`，description/difficulty 等参数全丢
**修复**：合并原始 args 到新调用：`add({**args, "name": new_name})`

### 5. recipe_import.py — 食材名不匹配静默跳过

**文件**：`scripts/recipe_import.py`
**位置**：L288-301
**问题**：步骤中 `ingredients_used` 引用的食材名不在 `name_id_map` 中时静默跳过
**修复**：else 分支加 `print(f"警告：步骤引用的食材 '{ing_name}' 未在食材列表中找到，跳过关联")`

---

## P1：代码质量问题（7项）

### 6. recipe_manager.py — show() 重复开连接

**文件**：`scripts/recipe_manager.py`
**位置**：L258-331
**问题**：L258 关闭 conn 后，L318 又开 conn2 查食材步骤映射
**修复**：把 L318-331 的查询逻辑移到 L258 之前（conn 仍打开时），删除 conn2

### 7. step_manager.py — reorder 临时重复 sequence

**文件**：`scripts/step_manager.py`
**位置**：L239-241
**问题**：两步 UPDATE 之间有重复 sequence 值
**修复**：三步操作：① from_step → sequence=-1 ② to_step → from_seq ③ from_step → to_seq

### 8. db_config.py — 裸 except

**文件**：`scripts/db_config.py`
**位置**：L130、L136、L178
**问题**：`except:` 会吞掉 KeyboardInterrupt/SystemExit
**修复**：3 处改为 `except Exception`

### 9. init_db.py — 无事务保护

**文件**：`scripts/init_db.py`
**位置**：L14-286
**问题**：17 张表创建没有事务保护，中途失败会半初始化
**修复**：在 L15 后加 `conn.execute("BEGIN")`，L285 前加 `conn.execute("COMMIT")`，异常时 ROLLBACK

### 10. nutrition_manager.py — threshold 未转换

**文件**：`scripts/nutrition_manager.py`
**位置**：L154
**问题**：`threshold` 是字符串，直接用于 SQL 比较
**修复**：`threshold = int(args.get("--threshold") or 20)`

### 11. recipe_manager.py — update 数值未转换

**文件**：`scripts/recipe_manager.py`
**位置**：L583-589
**问题**：servings 和 total_time 作为字符串存入 INTEGER 列
**修复**：加 `int()` 转换

### 12. 9 个 manager — list() 遮蔽内置函数

**文件**：category_manager.py、ingredient_manager.py、step_manager.py、flavor_manager.py、season_manager.py、cooking_method_manager.py、diet_tag_manager.py、meal_type_manager.py、tip_manager.py、history_manager.py
**问题**：`def list(args)` 遮蔽 Python 内置 `list()`
**修复**：重命名为 `list_items()`，同步更新 main() 中的分支

---

## P2：文档/一致性问题（9项）

### 13. update.md — 重复段落

**文件**：`features/update.md`
**位置**：L229-244
**问题**："写操作确认格式"完整重复了两次
**修复**：删除 L229-244

### 14a. categories.md — 小贴士分类缺"文化"

**文件**：`references/categories.md`
**位置**：L169-177
**修复**：加 `| 文化 | 文化背景/典故 |`

### 14b. commands.md — 小贴士分类缺"文化"

**文件**：`references/commands.md`
**位置**：L456
**修复**：分类列表加"文化"

### 14c. commands.md — 烹饪方式缺"生食"

**文件**：`references/commands.md`
**位置**：L719
**修复**：列表加"生食"

### 15. view.md + shopping.md — 绝对路径

**文件**：`features/view.md`（L44,49,141,313）、`features/shopping.md`（L39）
**修复**：保留绝对路径，加注释 `<!-- 请根据实际环境调整路径 -->`

### 16. SKILL.md — 缺依赖说明和一键安装

**文件**：`SKILL.md`
**位置**：开头
**修复**：在"操作规范"前加：
```
## 依赖
- Python 3.x
- sqlite3（Python 内置）

## 快速开始
首次使用，发送：`初始化私家大厨数据库`
```

### 18. step_manager.py — help 文本不一致

**文件**：`scripts/step_manager.py`
**位置**：L257
**问题**：help 写 `disable`，代码处理 `discard`
**修复**：help 改为 `discard`

### 19. help 文本截断

**文件**：`scripts/ingredient_manager.py`（L208）、`scripts/cookware_manager.py`（L174）
**问题**：help 末尾有多余空行 `python xxx_manager.py `
**修复**：删除空行

### 20. tip_manager.py — 重复解析分支

**文件**：`scripts/tip_manager.py`
**位置**：L315、L321
**问题**：`<关键词>` 解析分支写了两次
**修复**：删除 L321 的重复 elif

### 21. 多个 manager — discard/disable 死代码

**文件**：ingredient_manager.py、step_manager.py、technique_manager.py、tip_manager.py、cookware_manager.py
**问题**：main() 中处理 `discard` action 但不在 if/elif 分支中
**修复**：删除这些死分支（`elif action == "discard": print(...)` 代码块）

---

## P3：建议优化（5项）

### 22. _meta.json — 补充字段

**文件**：`_meta.json`
**修复**：加 `description` 和 `dependencies` 字段

### 23. .gitignore — 补充规则

**文件**：`.gitignore`
**修复**：加 `*.bak`、`output/`、`*.db`（取消注释）

### 24. 临时文件清理

**删除文件**：
- `scripts/recipe_manager.py.bak`
- `bug_report.html`
- `json_import_solution.html`

### 25. config-chef-cookbook.ts — 用途说明

**文件**：`SKILL.md`
**修复**：快速导航表中加一行：`| SkillBoard配置 | config-chef-cookbook.ts | 前端面板配置 |`

### 26. get_now() 重复定义 — 不处理

**原因**：提取公共模块属于重构，超出最小修复范围。记录为已知技术债。

---

## 执行顺序

1. P0（5项）— 保证功能正确
2. P1（7项）— 保证代码健壮
3. P2（9项）— 保证文档一致
4. P3（5项）— 配置和清理

每个优先级完成后验证，无误后进入下一个。
