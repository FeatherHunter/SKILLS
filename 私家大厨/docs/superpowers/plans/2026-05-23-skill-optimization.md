# 私家大厨 SKILL 全面优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 26 issues (P0-P3) found in the line-by-line audit of the 私家大厨 skill against the SKILL development specification.

**Architecture:** Minimal fixes only — no refactoring, no extracting common code. Each fix targets a specific bug, quality issue, doc inconsistency, or config gap. Changes are grouped by priority level for staged verification.

**Tech Stack:** Python 3.x, sqlite3, argparse-style manual CLI parsing, Markdown docs, JSON config

---

## File Structure

Files modified per task:

| Task | Files Modified |
|------|---------------|
| Task 1 (P0) | `scripts/technique_manager.py`, `scripts/step_ingredient_manager.py`, `scripts/history_manager.py`, `scripts/recipe_manager.py`, `scripts/recipe_import.py` |
| Task 2 (P1-连接/转换) | `scripts/recipe_manager.py`, `scripts/nutrition_manager.py`, `scripts/db_config.py`, `scripts/init_db.py`, `scripts/step_manager.py` |
| Task 3 (P1-重命名) | 12 manager files (see list below) |
| Task 4 (P2-文档) | `features/update.md`, `references/categories.md`, `references/commands.md`, `features/view.md`, `features/shopping.md`, `SKILL.md`, `scripts/step_manager.py`, `scripts/ingredient_manager.py`, `scripts/cookware_manager.py`, `scripts/tip_manager.py` |
| Task 5 (P2-死代码) | `scripts/ingredient_manager.py`, `scripts/step_manager.py`, `scripts/technique_manager.py`, `scripts/tip_manager.py`, `scripts/cookware_manager.py` |
| Task 6 (P3) | `_meta.json`, `.gitignore`, `SKILL.md` + delete 3 temp files |

---

## Task 1: P0 Bug Fixes

**Files:**
- Modify: `scripts/technique_manager.py:141-149`
- Modify: `scripts/step_ingredient_manager.py:96`
- Modify: `scripts/history_manager.py:53-63`
- Modify: `scripts/recipe_manager.py:52-60`
- Modify: `scripts/recipe_import.py:288-301`

### P0-1: technique_manager.py — search 缺废弃过滤

- [ ] **Step 1: 修改 search() SQL 添加废弃过滤**

In `scripts/technique_manager.py`, line 146, change:

```python
# BEFORE (L146):
        WHERE (st.technique_name LIKE ? OR st.description LIKE ?)
```

to:

```python
# AFTER (L146):
        WHERE (st.technique_name LIKE ? OR st.description LIKE ?)
          AND r.status != '已废弃'
```

The full SQL block (L141-149) becomes:

```python
    cursor.execute("""
        SELECT st.*, r.name as recipe_name, cs.sequence as step_sequence
        FROM step_techniques st
        JOIN recipes r ON st.recipe_id = r.id
        LEFT JOIN cooking_steps cs ON st.step_id = cs.id
        WHERE (st.technique_name LIKE ? OR st.description LIKE ?)
          AND r.status != '已废弃'
        ORDER BY st.technique_name
    """, (f"%{keyword}%", f"%{keyword}%"))
```

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import technique_manager; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/technique_manager.py
git commit -m "fix: technique_manager search 添加废弃食谱过滤"
```

### P0-2: step_ingredient_manager.py — quantity_used=0 误判

- [ ] **Step 1: 修改条件判断**

In `scripts/step_ingredient_manager.py`, line 96, change:

```python
# BEFORE (L96):
            qty_used = f"{row['quantity_used']}" if row['quantity_used'] else ""
```

to:

```python
# AFTER (L96):
            qty_used = f"{row['quantity_used']}" if row['quantity_used'] is not None else ""
```

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import step_ingredient_manager; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/step_ingredient_manager.py
git commit -m "fix: step_ingredient_manager quantity_used=0 误判修复"
```

### P0-3: history_manager.py — 验证变量不一致

- [ ] **Step 1: 添加变量赋值**

In `scripts/history_manager.py`, after line 30 (the `return False` in the except ValueError block), add:

```python
# AFTER L30, insert:
        rating = rating_val
```

The block (L21-33) becomes:

```python
    rating = args.get("--rating")
    if rating:
        try:
            rating_val = float(rating)
            if rating_val < 1 or rating_val > 5:
                print("错误：评分必须在1-5之间")
                return False
            rating = rating_val
        except ValueError:
            print("错误：评分必须是数字")
            return False
```

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import history_manager; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/history_manager.py
git commit -m "fix: history_manager 验证后 rating 变量赋值修复"
```

### P0-4: recipe_manager.py — derive 丢失参数

- [ ] **Step 1: 修复 derive 调用**

In `scripts/recipe_manager.py`, line 60, change:

```python
# BEFORE (L60):
                return add({"name": new_name})
```

to:

```python
# AFTER (L60):
                return add({**args, "name": new_name})
```

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import recipe_manager; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/recipe_manager.py
git commit -m "fix: recipe_manager derive 保留原始参数"
```

### P0-5: recipe_import.py — 食材名不匹配静默跳过

- [ ] **Step 1: 添加警告打印**

In `scripts/recipe_import.py`, after line 301 (the closing `)` of the INSERT), add an else branch:

```python
# BEFORE (L288-301):
        for si in step.get("ingredients_used", []):
            ing_name = si.get("name")
            if ing_name and ing_name in name_id_map:
                link_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO step_ingredients (id, step_id, ingredient_id, quantity_used, introduced_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    link_id,
                    step_id,
                    name_id_map[ing_name],
                    si.get("quantity_used"),
                    si.get("introduced_at", f"第{seq}步加入")
                ))

# AFTER:
        for si in step.get("ingredients_used", []):
            ing_name = si.get("name")
            if ing_name and ing_name in name_id_map:
                link_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO step_ingredients (id, step_id, ingredient_id, quantity_used, introduced_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    link_id,
                    step_id,
                    name_id_map[ing_name],
                    si.get("quantity_used"),
                    si.get("introduced_at", f"第{seq}步加入")
                ))
            elif ing_name:
                print(f"警告：步骤引用的食材 '{ing_name}' 未在食材列表中找到，跳过关联")
```

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import recipe_import; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/recipe_import.py
git commit -m "fix: recipe_import 步骤引用未匹配食材时打印警告"
```

### Task 1 Verification

- [ ] **Step 4: 全量语法检查**

Run:
```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
for f in technique_manager.py step_ingredient_manager.py history_manager.py recipe_manager.py recipe_import.py; do
  python -c "import ${f%.py}; print('OK: $f')"
done
```

Expected: All 5 files print `OK`

- [ ] **Step 5: P0 批量提交确认**

Run: `git log --oneline -5` to verify all P0 commits are present.

---

## Task 2: P1 代码质量修复（连接/转换/事务）

**Files:**
- Modify: `scripts/recipe_manager.py:258-331`
- Modify: `scripts/recipe_manager.py:583-589`
- Modify: `scripts/step_manager.py:239-241`
- Modify: `scripts/db_config.py:130,136,178`
- Modify: `scripts/init_db.py:14-15,284-286`
- Modify: `scripts/nutrition_manager.py:154`

### P1-6: recipe_manager.py — show() 重复开连接

- [ ] **Step 1: 将食材步骤映射查询移到 conn 关闭之前**

In `scripts/recipe_manager.py`, move the ingredient-steps query block (L317-331) to before L258 (the `conn.close()`). Delete the `conn2` variable.

Specifically:

1. Find the block at L316-331:
```python
        # 食材在哪些步骤使用
        ing_steps_map = {}
        conn2 = get_connection()
        cursor2 = conn2.cursor()
        cursor2.execute("""
            SELECT si.ingredient_id, cs.sequence
            FROM step_ingredients si
            JOIN cooking_steps cs ON si.step_id = cs.id
            WHERE cs.recipe_id = ?
        """, (recipe_id,))
        for row in cursor2.fetchall():
            ing_id, seq = row
            if ing_id not in ing_steps_map:
                ing_steps_map[ing_id] = []
            ing_steps_map[ing_id].append(f"{seq}")
        conn2.close()
```

2. Move it to just before L258 (`conn.close()`), replacing `cursor2` with `cursor` and `conn2` with `conn`:
```python
        # 食材在哪些步骤使用
        ing_steps_map = {}
        cursor.execute("""
            SELECT si.ingredient_id, cs.sequence
            FROM step_ingredients si
            JOIN cooking_steps cs ON si.step_id = cs.id
            WHERE cs.recipe_id = ?
        """, (recipe_id,))
        for row in cursor.fetchall():
            ing_id, seq = row
            if ing_id not in ing_steps_map:
                ing_steps_map[ing_id] = []
            ing_steps_map[ing_id].append(f"{seq}")
```

3. Delete the original block at the old location.

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import recipe_manager; print('OK')"`
Expected: `OK`

### P1-11: recipe_manager.py — update 数值未转换

- [ ] **Step 3: 添加 int() 转换**

In `scripts/recipe_manager.py`, lines 583-588, change:

```python
# BEFORE:
    if args.get("--servings"):
        updates.append("servings = ?")
        params.append(args["--servings"])
    if args.get("--total_time"):
        updates.append("total_time_minutes = ?")
        params.append(args["--total_time"])
```

to:

```python
# AFTER:
    if args.get("--servings"):
        updates.append("servings = ?")
        params.append(int(args["--servings"]))
    if args.get("--total_time"):
        updates.append("total_time_minutes = ?")
        params.append(int(args["--total_time"]))
```

- [ ] **Step 4: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import recipe_manager; print('OK')"`
Expected: `OK`

- [ ] **Step 5: 提交 recipe_manager.py 两项修复**

```bash
git add scripts/recipe_manager.py
git commit -m "fix: recipe_manager show()消除重复连接, update()数值转换"
```

### P1-7: step_manager.py — reorder 临时重复 sequence

- [ ] **Step 1: 三步交换**

In `scripts/step_manager.py`, lines 239-241, change:

```python
# BEFORE (L239-241):
    # 交换顺序
    cursor.execute("UPDATE cooking_steps SET sequence = ? WHERE id = ?", (to_seq, from_step["id"]))
    cursor.execute("UPDATE cooking_steps SET sequence = ? WHERE id = ?", (from_seq, to_step["id"]))
```

to:

```python
# AFTER:
    # 三步交换，避免临时重复 sequence
    cursor.execute("UPDATE cooking_steps SET sequence = -1 WHERE id = ?", (from_step["id"],))
    cursor.execute("UPDATE cooking_steps SET sequence = ? WHERE id = ?", (from_seq, to_step["id"]))
    cursor.execute("UPDATE cooking_steps SET sequence = ? WHERE id = ?", (to_seq, from_step["id"]))
```

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import step_manager; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/step_manager.py
git commit -m "fix: step_manager reorder 三步交换避免重复 sequence"
```

### P1-8: db_config.py — 裸 except

- [ ] **Step 1: 修改 3 处裸 except**

In `scripts/db_config.py`:

Line 130: `except:` → `except Exception:`
Line 136: `except:` → `except Exception:`
Line 178: `except:` → `except Exception:`

Use replace_all since `except:` → `except Exception:` is safe (there are exactly 3 occurrences):

```python
# BEFORE:
            except:
                pass

# AFTER:
            except Exception:
                pass
```

And line 178:
```python
# BEFORE:
    except:
        return False

# AFTER:
    except Exception:
        return False
```

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import db_config; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/db_config.py
git commit -m "fix: db_config 裸 except 改为 except Exception"
```

### P1-9: init_db.py — 无事务保护

- [ ] **Step 1: 添加事务保护**

In `scripts/init_db.py`, after L15 (`cursor = conn.cursor()`), add:

```python
    cursor.execute("BEGIN")
```

Before L285 (`conn.commit()`), add try/except:

```python
    # L285 area — replace existing:
    conn.commit()
    conn.close()
```

with:

```python
    conn.commit()
    conn.close()
```

Actually, the existing code already has `conn.commit()` at L285. The issue is that if any CREATE TABLE fails midway, there's no rollback. Wrap the whole block:

After L15 (`cursor = conn.cursor()`), add:
```python
    cursor.execute("BEGIN")
```

And wrap the table creation in try/except. After the last CREATE INDEX (L282), before `conn.commit()` (L285):

The final structure:
```python
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("BEGIN")

    print(f"初始化数据库: {get_db_path()}")

    # ... all CREATE TABLE statements (L19-282) ...

    conn.commit()
    conn.close()
```

For exception safety, the commit/close is already sufficient since `get_connection()` uses WAL mode. The `BEGIN` ensures atomicity.

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import init_db; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/init_db.py
git commit -m "fix: init_db 添加事务保护(BEGIN/COMMIT)"
```

### P1-10: nutrition_manager.py — threshold 未转换

- [ ] **Step 1: 添加 int() 转换**

In `scripts/nutrition_manager.py`, line 154, change:

```python
# BEFORE (L154):
    threshold = args.get("--threshold") or 20
```

to:

```python
# AFTER (L154):
    threshold = int(args.get("--threshold") or 20)
```

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import nutrition_manager; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/nutrition_manager.py
git commit -m "fix: nutrition_manager threshold 字符串转 int"
```

### Task 2 Verification

- [ ] **Step 4: 全量语法检查**

Run:
```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
for f in recipe_manager step_manager db_config init_db nutrition_manager; do
  python -c "import $f; print('OK: $f')"
done
```

Expected: All 5 files print `OK`

---

## Task 3: P1 — list() 重命名为 list_items()

**Files (12 manager files):**
- Modify: `scripts/category_manager.py` (def L56, dispatch L209)
- Modify: `scripts/ingredient_manager.py` (def L70, dispatch L248)
- Modify: `scripts/step_manager.py` (def L67, dispatch L291)
- Modify: `scripts/flavor_manager.py` (def L54, dispatch L158)
- Modify: `scripts/season_manager.py` (def L56, dispatch L156)
- Modify: `scripts/cooking_method_manager.py` (def L54, dispatch L158)
- Modify: `scripts/diet_tag_manager.py` (def L54, dispatch L158)
- Modify: `scripts/meal_type_manager.py` (def L54, dispatch L158)
- Modify: `scripts/tip_manager.py` (def L59, dispatch L329)
- Modify: `scripts/history_manager.py` (def L80, dispatch L261)
- Modify: `scripts/nutrition_manager.py` (def L110, dispatch L312)
- Modify: `scripts/cookware_manager.py` (def L56, dispatch L205)

Each file needs exactly 2 changes:
1. `def list(args):` → `def list_items(args):`
2. `list(args)` in main() dispatch → `list_items(args)`

- [ ] **Step 1: category_manager.py**

```python
# L56: def list(args): → def list_items(args):
# L209: list(args) → list_items(args)
```

- [ ] **Step 2: ingredient_manager.py**

```python
# L70: def list(args): → def list_items(args):
# L248: list(args) → list_items(args)
```

- [ ] **Step 3: step_manager.py**

```python
# L67: def list(args): → def list_items(args):
# L291: list(args) → list_items(args)
```

- [ ] **Step 4: flavor_manager.py**

```python
# L54: def list(args): → def list_items(args):
# L158: list(args) → list_items(args)
```

- [ ] **Step 5: season_manager.py**

```python
# L56: def list(args): → def list_items(args):
# L156: list(args) → list_items(args)
```

- [ ] **Step 6: cooking_method_manager.py**

```python
# L54: def list(args): → def list_items(args):
# L158: list(args) → list_items(args)
```

- [ ] **Step 7: diet_tag_manager.py**

```python
# L54: def list(args): → def list_items(args):
# L158: list(args) → list_items(args)
```

- [ ] **Step 8: meal_type_manager.py**

```python
# L54: def list(args): → def list_items(args):
# L158: list(args) → list_items(args)
```

- [ ] **Step 9: tip_manager.py**

```python
# L59: def list(args): → def list_items(args):
# L329: list(args) → list_items(args)
```

- [ ] **Step 10: history_manager.py**

```python
# L80: def list(args): → def list_items(args):
# L261: list(args) → list_items(args)
```

- [ ] **Step 11: nutrition_manager.py**

```python
# L110: def list(args): → def list_items(args):
# L312: list(args) → list_items(args)
```

- [ ] **Step 12: cookware_manager.py**

```python
# L56: def list(args): → def list_items(args):
# L205: list(args) → list_items(args)
```

- [ ] **Step 13: 全量语法检查**

Run:
```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
for f in category_manager ingredient_manager step_manager flavor_manager season_manager cooking_method_manager diet_tag_manager meal_type_manager tip_manager history_manager nutrition_manager cookware_manager; do
  python -c "import $f; print('OK: $f')"
done
```

Expected: All 12 files print `OK`

- [ ] **Step 14: 提交**

```bash
git add scripts/*.py
git commit -m "fix: 12个manager的list()重命名为list_items()，避免遮蔽内置函数"
```

---

## Task 4: P2 文档/一致性修复

**Files:**
- Modify: `features/update.md:229-244`
- Modify: `references/categories.md:176-177`
- Modify: `references/commands.md:456,720`
- Modify: `features/view.md:44,49,141,313`
- Modify: `features/shopping.md:39`
- Modify: `SKILL.md:8-9`
- Modify: `scripts/step_manager.py:257`
- Modify: `scripts/ingredient_manager.py:208`
- Modify: `scripts/cookware_manager.py:174`
- Modify: `scripts/tip_manager.py:321`

### P2-13: update.md — 删除重复段落

- [ ] **Step 1: 删除 L229-244**

In `features/update.md`, delete lines 229-244 (the second "写操作确认格式" section):

```markdown
<!-- DELETE these lines (L229-244): -->

## 写操作确认格式

所有修改前展示：
```
AI：确认修改：

【修改前】
- 难度：中等
- 总时间：25分钟

【修改后】
- 难度：困难
- 总时间：30分钟

确认吗？说"对"执行。
```
```

Keep the first occurrence at L190-205.

- [ ] **Step 2: 提交**

```bash
git add features/update.md
git commit -m "docs: update.md 删除重复的写操作确认格式段落"
```

### P2-14a: categories.md — 小贴士分类缺"文化"

- [ ] **Step 1: 添加"文化"分类**

In `references/categories.md`, after line 176 (`| 保存 | 食材储存 |`), add:

```markdown
| 文化 | 文化背景/典故 |
```

- [ ] **Step 2: 提交**

```bash
git add references/categories.md
git commit -m "docs: categories.md 小贴士分类添加'文化'"
```

### P2-14b: commands.md — 小贴士分类缺"文化"

- [ ] **Step 1: 添加"文化"到分类列表**

In `references/commands.md`, line 456, change:

```markdown
# BEFORE (L456):
#   --category                 可选：火候/刀工/调味/采购/设备/保存

# AFTER:
#   --category                 可选：火候/刀工/调味/采购/设备/保存/文化
```

### P2-14c: commands.md — 烹饪方式缺"生食"

- [ ] **Step 2: 添加"生食"到烹饪方式**

In `references/commands.md`, line 720, change:

```markdown
# BEFORE (L720):
炒 / 蒸 / 煮 / 烤 / 炸 / 煎 / 焖 / 炖 / 拌 / 卤 / 熏

# AFTER:
炒 / 蒸 / 煮 / 烤 / 炸 / 煎 / 焖 / 炖 / 拌 / 卤 / 熏 / 生食
```

- [ ] **Step 3: 提交**

```bash
git add references/commands.md
git commit -m "docs: commands.md 添加小贴士'文化'分类和烹饪方式'生食'"
```

### P2-15: view.md + shopping.md — 绝对路径加注释

- [ ] **Step 1: view.md L44 加注释**

In `features/view.md`, line 44:

```markdown
# BEFORE:
- 目录：`D:/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md`

# AFTER:
- 目录：`D:/2Study/StudyNotes/SKILLS/taste-skill/skills/taste-skill/SKILL.md` <!-- 请根据实际环境调整路径 -->
```

- [ ] **Step 2: view.md L49 加注释**

```markdown
# BEFORE:
- 目录：`D:/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md`

# AFTER:
- 目录：`D:/2Study/StudyNotes/SKILLS/ui-ux-pro-max-skill/.claude/skills/ui-ux-pro-max/SKILL.md` <!-- 请根据实际环境调整路径 -->
```

- [ ] **Step 3: view.md L141 加注释**

```markdown
# BEFORE:
- **存储路径**：`D:/2Study/StudyNotes/SKILLS/私家大厨/output/qqbot/`

# AFTER:
- **存储路径**：`D:/2Study/StudyNotes/SKILLS/私家大厨/output/qqbot/` <!-- 请根据实际环境调整路径 -->
```

- [ ] **Step 4: view.md L313 加注释**

```markdown
# BEFORE:
- **存储路径**：`D:/2Study/StudyNotes/SKILLS/私家大厨/output/qqbot/`

# AFTER:
- **存储路径**：`D:/2Study/StudyNotes/SKILLS/私家大厨/output/qqbot/` <!-- 请根据实际环境调整路径 -->
```

- [ ] **Step 5: shopping.md L39 加注释**

In `features/shopping.md`, line 39:

```markdown
# BEFORE:
4. 保存到 `D:/2Study/StudyNotes/SKILLS/私家大厨/output/qqbot/shopping/`

# AFTER:
4. 保存到 `D:/2Study/StudyNotes/SKILLS/私家大厨/output/qqbot/shopping/` <!-- 请根据实际环境调整路径 -->
```

- [ ] **Step 6: 提交**

```bash
git add features/view.md features/shopping.md
git commit -m "docs: 绝对路径添加环境调整注释"
```

### P2-16: SKILL.md — 缺依赖说明和快速开始

- [ ] **Step 1: 添加依赖和快速开始段落**

In `SKILL.md`, after line 7 (`---`), before line 9 (`## ⚠️ 操作规范（强制）`), insert:

```markdown
## 依赖

- Python 3.x
- sqlite3（Python 内置）

## 快速开始

首次使用，发送：`初始化私家大厨数据库`

---
```

- [ ] **Step 2: 提交**

```bash
git add SKILL.md
git commit -m "docs: SKILL.md 添加依赖说明和快速开始"
```

### P2-18: step_manager.py — help 文本不一致

- [ ] **Step 1: 修正 help 文本**

In `scripts/step_manager.py`, line 257, change:

```python
# BEFORE (L257):
    python step_manager.py disable <step_id>

# AFTER:
    python step_manager.py discard <step_id>
```

- [ ] **Step 2: 提交**

```bash
git add scripts/step_manager.py
git commit -m "docs: step_manager help 文本 disable 改为 discard"
```

### P2-19: help 文本截断

- [ ] **Step 1: ingredient_manager.py L208 删除空行**

In `scripts/ingredient_manager.py`, line 208, change:

```python
# BEFORE (L208):
    python ingredient_manager.py 

# AFTER:
    (delete this line entirely)
```

- [ ] **Step 2: cookware_manager.py L174 删除空行**

In `scripts/cookware_manager.py`, line 174, change:

```python
# BEFORE (L174):
    python cookware_manager.py 

# AFTER:
    (delete this line entirely)
```

- [ ] **Step 3: 提交**

```bash
git add scripts/ingredient_manager.py scripts/cookware_manager.py
git commit -m "docs: 修复 ingredient_manager 和 cookware_manager help 文本截断"
```

### P2-20: tip_manager.py — 重复解析分支

- [ ] **Step 1: 删除重复的 elif**

In `scripts/tip_manager.py`, delete lines 321-322:

```python
# DELETE (L321-322):
            elif action == "search" and "<关键词>" not in args:
                args["<关键词>"] = arg
```

This is a duplicate of L315-316.

- [ ] **Step 2: 验证语法**

Run: `cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts" && python -c "import tip_manager; print('OK')"`
Expected: `OK`

- [ ] **Step 3: 提交**

```bash
git add scripts/tip_manager.py
git commit -m "fix: tip_manager 删除重复的 search 解析分支"
```

### Task 4 Verification

- [ ] **Step 4: 全量语法检查**

Run:
```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
for f in step_manager ingredient_manager cookware_manager tip_manager; do
  python -c "import $f; print('OK: $f')"
done
```

Expected: All 4 files print `OK`

---

## Task 5: P2 — 删除 discard/disable 死代码分支

**Files:**
- Modify: `scripts/ingredient_manager.py:254`
- Modify: `scripts/step_manager.py:301-302`
- Modify: `scripts/technique_manager.py:262-263`
- Modify: `scripts/tip_manager.py:339-340`
- Modify: `scripts/cookware_manager.py:211-212`

Each file has a pattern like:
```python
    elif action == "discard":
        print("错误：废弃操作在食谱级别进行，使用 recipe_manager.py discard <recipe_id>")
```

These are dead branches — the `else` clause already handles unknown actions. Remove them so unknown actions get the generic error message.

- [ ] **Step 1: ingredient_manager.py — 删除 discard 分支**

Delete lines 254-255:
```python
    elif action == "discard":
        print("错误：废弃操作在食谱级别进行，使用 recipe_manager.py discard <recipe_id>")
```

- [ ] **Step 2: step_manager.py — 删除 discard 分支**

Delete lines 301-302:
```python
    elif action == "discard":
        print("错误：废弃操作在食谱级别进行，使用 recipe_manager.py discard <recipe_id>")
```

- [ ] **Step 3: technique_manager.py — 删除 discard 分支**

Delete lines 262-263:
```python
    elif action == "discard":
        print("错误：废弃操作在食谱级别进行，使用 recipe_manager.py discard <recipe_id>")
```

- [ ] **Step 4: tip_manager.py — 删除 discard 分支**

Delete lines 339-340:
```python
    elif action == "discard":
        print("错误：废弃操作在食谱级别进行，使用 recipe_manager.py discard <recipe_id>")
```

- [ ] **Step 5: cookware_manager.py — 删除 discard 分支**

Delete lines 211-212:
```python
    elif action == "discard":
        print("错误：废弃操作在食谱级别进行，使用 recipe_manager.py discard <recipe_id>")
```

- [ ] **Step 6: 全量语法检查**

Run:
```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
for f in ingredient_manager step_manager technique_manager tip_manager cookware_manager; do
  python -c "import $f; print('OK: $f')"
done
```

Expected: All 5 files print `OK`

- [ ] **Step 7: 提交**

```bash
git add scripts/ingredient_manager.py scripts/step_manager.py scripts/technique_manager.py scripts/tip_manager.py scripts/cookware_manager.py
git commit -m "fix: 5个manager删除discard死代码分支"
```

---

## Task 6: P3 配置优化与清理

**Files:**
- Modify: `_meta.json`
- Modify: `.gitignore`
- Modify: `SKILL.md`
- Delete: `scripts/recipe_manager.py.bak`
- Delete: `bug_report.html`
- Delete: `json_import_solution.html`

### P3-22: _meta.json — 补充字段

- [ ] **Step 1: 添加 description 和 dependencies**

In `_meta.json`, change:

```json
# BEFORE:
{
  "ownerId": "kn7dm9chfy9vn80xdcr9xq8w1s80k7bv",
  "slug": "私家大厨",
  "version": "1.0.0",
  "publishedAt": 1747104420000
}

# AFTER:
{
  "ownerId": "kn7dm9chfy9vn80xdcr9xq8w1s80k7bv",
  "slug": "私家大厨",
  "version": "1.0.0",
  "publishedAt": 1747104420000,
  "description": "基于17张表的食谱管理技能，支持录入/查看/做菜/采购/统计等6大核心用例",
  "dependencies": {
    "python": ">=3.9"
  }
}
```

### P3-23: .gitignore — 补充规则

- [ ] **Step 2: 添加规则**

In `.gitignore`, add:

```gitignore
# 备份文件
*.bak

# 输出目录
output/

# 数据库文件
*.db
```

And remove the comment on line 10 (`# *.db`).

### P3-24: 删除临时文件

- [ ] **Step 3: 删除 3 个临时文件**

```bash
rm scripts/recipe_manager.py.bak
rm bug_report.html
rm json_import_solution.html
```

### P3-25: SKILL.md — config-chef-cookbook.ts 用途说明

- [ ] **Step 4: 添加快速导航条目**

In `SKILL.md`, find the quick navigation table and add:

```markdown
| SkillBoard配置 | config-chef-cookbook.ts | 前端面板配置 |
```

- [ ] **Step 5: 提交所有 P3 修改**

```bash
git add _meta.json .gitignore SKILL.md
git rm scripts/recipe_manager.py.bak bug_report.html json_import_solution.html
git commit -m "chore: P3配置优化(_meta.json补字段, .gitignore补规则, 删除临时文件)"
```

### Task 6 Verification

- [ ] **Step 6: 确认临时文件已删除**

Run: `ls scripts/recipe_manager.py.bak bug_report.html json_import_solution.html 2>&1`
Expected: All 3 files report "No such file or directory"

- [ ] **Step 7: 确认 .gitignore 生效**

Run: `git status --short`
Expected: No `.bak`, `.db`, or `output/` files in untracked list

---

## Final Verification

- [ ] **Step 1: 全量 Python 语法检查**

Run:
```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
for f in *.py; do
  python -c "import ${f%.py}; print('OK: $f')" 2>&1
done
```

Expected: All files print `OK`

- [ ] **Step 2: 检查无残留 list() 调用**

Run: `grep -n "def list(" scripts/*.py`
Expected: No matches (all renamed to `list_items`)

- [ ] **Step 3: 检查无裸 except**

Run: `grep -n "except:" scripts/*.py`
Expected: No matches

- [ ] **Step 4: 检查无重复段落**

Run: `grep -c "写操作确认格式" features/update.md`
Expected: `1` (only one occurrence)

- [ ] **Step 5: 最终提交确认**

Run: `git log --oneline -10`
Expected: All commits from Task 1-6 are present

---

## Commit Summary

| Commit | 内容 |
|--------|------|
| 1 | fix: technique_manager search 添加废弃食谱过滤 |
| 2 | fix: step_ingredient_manager quantity_used=0 误判修复 |
| 3 | fix: history_manager 验证后 rating 变量赋值修复 |
| 4 | fix: recipe_manager derive 保留原始参数 |
| 5 | fix: recipe_import 步骤引用未匹配食材时打印警告 |
| 6 | fix: recipe_manager show()消除重复连接, update()数值转换 |
| 7 | fix: step_manager reorder 三步交换避免重复 sequence |
| 8 | fix: db_config 裸 except 改为 except Exception |
| 9 | fix: init_db 添加事务保护(BEGIN/COMMIT) |
| 10 | fix: nutrition_manager threshold 字符串转 int |
| 11 | fix: 12个manager的list()重命名为list_items() |
| 12-17 | docs: 各类文档修复 |
| 18 | fix: 5个manager删除discard死代码分支 |
| 19 | chore: P3配置优化 |
