# JSON文件导入方案 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 `recipe_import.py` 脚本，让低能力AI通过一个JSON文件+一个命令完成食谱录入，替代原来的10步CLI操作。

**Architecture:** 新增 `recipe_import.py` 脚本，内部复用现有manager的数据库操作逻辑（直接SQL，不调用CLI），提供JSON验证、同名冲突处理、事务保护。原有CLI命令完全保留不变。

**Tech Stack:** Python 3, SQLite3, json模块

---

## 文件结构

| 文件 | 操作 | 说明 |
|------|------|------|
| `scripts/recipe_import.py` | 新增 | JSON导入脚本（核心） |
| `scripts/tests/test_recipe_import.py` | 新增 | 单元测试 |
| `templates/recipe_template.json` | 新增 | JSON模板（供AI参考） |
| `references/commands.md` | 修改 | 添加导入命令文档 |
| `features/add.md` | 修改 | 添加JSON导入说明 |
| `SKILL.md` | 修改 | 添加JSON导入功能说明 |

---

### Task 1: 创建JSON模板文件

**Files:**
- Create: `templates/recipe_template.json`

- [ ] **Step 1: 创建模板目录和模板文件**

```bash
mkdir -p "D:/2Study/StudyNotes/SKILLS/私家大厨/templates"
```

创建 `templates/recipe_template.json`:

```json
{
  "name": "宫保虾球",
  "description": "川菜经典，虾球Q弹，酸甜微辣",
  "difficulty": "中等",
  "servings": 2,
  "total_time": 25,
  "status": "未做",

  "category": {
    "cuisine": "川菜",
    "region": "中国-四川",
    "country": "中国"
  },

  "seasons": ["春", "夏"],
  "cooking_methods": ["炒", "炸"],
  "flavors": ["辣", "麻"],
  "diet_tags": ["高蛋白"],
  "meal_types": ["晚餐"],

  "ingredients": [
    {
      "name": "虾",
      "quantity": 300,
      "unit": "g",
      "category": "海鲜",
      "sequence": 1,
      "is_optional": false,
      "substitute": null
    },
    {
      "name": "花生",
      "quantity": 50,
      "unit": "g",
      "category": "干货",
      "sequence": 2,
      "is_optional": true,
      "substitute": "腰果"
    }
  ],

  "steps": [
    {
      "sequence": 1,
      "action": "虾去壳开背，用料酒和盐腌制10分钟",
      "duration": 10,
      "heat_level": "小火",
      "temperature": "常温",
      "expected_result": "虾肉变红，去腥",
      "ingredients_used": [
        {"name": "虾", "quantity_used": 300}
      ]
    },
    {
      "sequence": 2,
      "action": "大火热油，虾下锅炸至变色捞出",
      "duration": 3,
      "heat_level": "大火",
      "temperature": "180度",
      "expected_result": "虾球金黄，外酥内嫩",
      "ingredients_used": []
    }
  ],

  "tips": [
    {
      "step_sequence": 1,
      "content": "开背时去虾线更入味",
      "category": "刀工",
      "priority": 1
    }
  ],

  "techniques": [
    {
      "step_sequence": 1,
      "technique_name": "腌制",
      "description": "用料酒去腥",
      "key_points": "时间要够/料酒要适量"
    }
  ],

  "cookware": [
    {"name": "炒锅", "category": "锅"}
  ],

  "nutrition": {
    "serving_size": 200,
    "serving_unit": "g",
    "calories": 320,
    "protein": 28,
    "fat": 18,
    "carbs": 20,
    "fiber": 2,
    "sodium": 800
  },

  "background": {
    "origin_story": "宫保虾球源自川菜宫保鸡丁的变体",
    "historical_background": "清代丁宝桢任四川总督时改良此菜",
    "cultural_significance": "代表川菜小荔枝口的经典味型"
  }
}
```

- [ ] **Step 2: 验证JSON格式**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨"
python -c "import json; json.load(open('templates/recipe_template.json', encoding='utf-8')); print('JSON格式正确')"
```

Expected: `JSON格式正确`

- [ ] **Step 3: Commit**

```bash
git add templates/recipe_template.json
git commit -m "feat: 添加JSON导入模板文件"
```

---

### Task 2: 创建 recipe_import.py - 验证模块

**Files:**
- Create: `scripts/recipe_import.py`

- [ ] **Step 1: 创建脚本骨架和验证函数**

创建 `scripts/recipe_import.py`:

```python
#!/usr/bin/env python3
"""
私家大厨 - JSON导入脚本
将JSON格式的食谱数据一次性导入数据库

用法：
    python recipe_import.py import <json_file>
    python recipe_import.py validate <json_file>
    python recipe_import.py template
"""

import sys
import os
import json
import uuid
from datetime import datetime

# 添加scripts目录到path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from db_config import get_connection


def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def validate_recipe(data):
    """验证食谱JSON数据，返回错误列表"""
    errors = []

    # 1. 必填字段检查
    if not data.get("name"):
        errors.append("缺少必填字段: name（菜名）")
    if not data.get("ingredients"):
        errors.append("缺少必填字段: ingredients（食材列表）")
    if not data.get("steps"):
        errors.append("缺少必填字段: steps（步骤列表）")

    # 2. 数据类型检查
    if "name" in data and not isinstance(data["name"], str):
        errors.append("name 必须是字符串")
    if "servings" in data and data["servings"] is not None:
        if not isinstance(data["servings"], int):
            errors.append("servings 必须是整数")
    if "total_time" in data and data["total_time"] is not None:
        if not isinstance(data["total_time"], (int, float)):
            errors.append("total_time 必须是数字")
    if "difficulty" in data and data["difficulty"] is not None:
        valid_difficulty = ["快手菜", "简单", "中等", "困难", "大师"]
        if data["difficulty"] not in valid_difficulty:
            errors.append(f"difficulty 必须是以下之一: {', '.join(valid_difficulty)}")

    # 3. 食材验证
    for i, ing in enumerate(data.get("ingredients", [])):
        if not ing.get("name"):
            errors.append(f"ingredients[{i}] 缺少 name（食材名）")
        if "quantity" in ing and ing["quantity"] is not None:
            if not isinstance(ing["quantity"], (int, float)):
                errors.append(f"ingredients[{i}].quantity 必须是数字")

    # 4. 步骤验证
    for i, step in enumerate(data.get("steps", [])):
        if not step.get("action"):
            errors.append(f"steps[{i}] 缺少 action（步骤描述）")
        if "sequence" in step and step["sequence"] is not None:
            if not isinstance(step["sequence"], int):
                errors.append(f"steps[{i}].sequence 必须是整数")
        if "duration" in step and step["duration"] is not None:
            if not isinstance(step["duration"], (int, float)):
                errors.append(f"steps[{i}].duration 必须是数字")

    # 5. 营养信息验证
    if "nutrition" in data and data["nutrition"]:
        nutri = data["nutrition"]
        for field in ["calories", "protein", "fat", "carbs", "fiber", "sodium", "serving_size"]:
            if field in nutri and nutri[field] is not None:
                if not isinstance(nutri[field], (int, float)):
                    errors.append(f"nutrition.{field} 必须是数字")

    return errors
```

- [ ] **Step 2: 验证验证函数能正确工作**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
python -c "
from recipe_import import validate_recipe

# 测试空数据
errors = validate_recipe({})
assert '缺少必填字段: name（菜名）' in errors
assert '缺少必填字段: ingredients（食材列表）' in errors
assert '缺少必填字段: steps（步骤列表）' in errors

# 测试正确数据
data = {'name': '测试', 'ingredients': [{'name': '盐'}], 'steps': [{'action': '加盐'}]}
errors = validate_recipe(data)
assert len(errors) == 0

print('验证函数测试通过')
"
```

Expected: `验证函数测试通过`

- [ ] **Step 3: Commit**

```bash
git add scripts/recipe_import.py
git commit -m "feat: 创建recipe_import.py骨架和验证函数"
```

---

### Task 3: 添加冲突检测和导入核心逻辑

**Files:**
- Modify: `scripts/recipe_import.py`

- [ ] **Step 1: 添加冲突检测函数**

在 `scripts/recipe_import.py` 中追加：

```python
def check_conflict(conn, name, choice=None):
    """检查同名食谱冲突，返回 (has_conflict, result)"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, status FROM recipes
        WHERE name = ? AND status != '已废弃'
    """, (name,))
    existing = cursor.fetchone()

    if not existing:
        return False, None

    # 有冲突，且没有指定choice
    if not choice:
        cursor.execute("""
            SELECT COUNT(*) as cnt, AVG(rating) as avg
            FROM recipe_history WHERE recipe_id = ?
        """, (existing['id'],))
        hist = cursor.fetchone()
        hist_cnt = int(hist['cnt']) if hist['cnt'] else 0
        hist_avg = round(float(hist['avg']), 1) if hist['avg'] else 0

        return True, {
            "conflict": True,
            "message": f"发现同名食谱「{name}」",
            "existing_recipe": {
                "id": existing['id'],
                "name": existing['name'],
                "status": existing['status'],
                "cook_count": hist_cnt,
                "avg_rating": hist_avg
            },
            "choices": [
                {"action": "view", "description": "查看现有食谱详情"},
                {"action": "derive", "description": "基于现有食谱创建新变体（需提供 --new_name）"},
                {"action": "update", "description": "更新现有食谱内容"},
                {"action": "cancel", "description": "放弃本次录入"}
            ],
            "usage": "再次调用时添加 --choice <action> 参数"
        }

    # 有冲突，且指定了choice
    if choice == "cancel":
        return True, {"status": "cancelled", "message": "已取消"}
    elif choice == "view":
        return True, {"status": "view", "recipe_id": existing['id']}
    elif choice == "derive":
        return True, {"status": "derive", "message": "请提供 --new_name 参数"}
    elif choice == "update":
        return True, {"status": "update", "recipe_id": existing['id']}
    else:
        return True, {"error": f"无效选择: {choice}", "valid_choices": ["view", "derive", "update", "cancel"]}
```

- [ ] **Step 2: 添加创建食谱主记录函数**

在 `scripts/recipe_import.py` 中追加：

```python
def create_recipe(conn, data):
    """创建食谱主记录，返回recipe_id"""
    recipe_id = str(uuid.uuid4())
    now = get_now()

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recipes (
            id, name, description, difficulty, servings, total_time_minutes,
            status, photo_url, source, source_url, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        recipe_id,
        data["name"],
        data.get("description"),
        data.get("difficulty"),
        data.get("servings"),
        data.get("total_time"),
        data.get("status", "未做"),
        data.get("photo_url"),
        data.get("source"),
        data.get("source_url"),
        now,
        now
    ))

    return recipe_id
```

- [ ] **Step 3: Commit**

```bash
git add scripts/recipe_import.py
git commit -m "feat: 添加冲突检测和创建食谱函数"
```

---

### Task 4: 添加关联数据导入函数

**Files:**
- Modify: `scripts/recipe_import.py`

- [ ] **Step 1: 添加分类和标签导入函数**

在 `scripts/recipe_import.py` 中追加：

```python
def add_category(conn, recipe_id, category):
    """添加分类信息"""
    if not category:
        return
    cursor = conn.cursor()
    cat_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO recipe_categories (id, recipe_id, cuisine_type, region, country)
        VALUES (?, ?, ?, ?, ?)
    """, (
        cat_id,
        recipe_id,
        category.get("cuisine"),
        category.get("region"),
        category.get("country")
    ))


def add_tag_list(conn, recipe_id, tags, table, column, id_column="id"):
    """通用：添加标签列表（季节/烹饪方式/口味/饮食标签/用餐类型）"""
    if not tags:
        return
    cursor = conn.cursor()
    for tag in tags:
        tag_id = str(uuid.uuid4())
        cursor.execute(f"""
            INSERT INTO {table} (id, recipe_id, {column})
            VALUES (?, ?, ?)
        """, (tag_id, recipe_id, tag))


def add_seasons(conn, recipe_id, seasons):
    add_tag_list(conn, recipe_id, seasons, "recipe_seasons", "season")

def add_cooking_methods(conn, recipe_id, methods):
    add_tag_list(conn, recipe_id, methods, "recipe_cooking_methods", "method")

def add_flavors(conn, recipe_id, flavors):
    add_tag_list(conn, recipe_id, flavors, "recipe_flavors", "flavor")

def add_diet_tags(conn, recipe_id, tags):
    add_tag_list(conn, recipe_id, tags, "recipe_diet_tags", "tag")

def add_meal_types(conn, recipe_id, types):
    add_tag_list(conn, recipe_id, types, "recipe_meal_types", "meal_type")
```

- [ ] **Step 2: 添加食材导入函数**

在 `scripts/recipe_import.py` 中追加：

```python
def add_ingredients(conn, recipe_id, ingredients):
    """添加食材列表，返回 {name: id} 映射"""
    if not ingredients:
        return {}
    cursor = conn.cursor()
    name_id_map = {}

    for i, ing in enumerate(ingredients):
        ingredient_id = str(uuid.uuid4())
        name = ing["name"]
        name_id_map[name] = ingredient_id

        cursor.execute("""
            INSERT INTO ingredients (
                id, recipe_id, sequence, name, category, quantity, unit,
                quantity_text, is_optional, substitute
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            ingredient_id,
            recipe_id,
            ing.get("sequence", i + 1),
            name,
            ing.get("category"),
            ing.get("quantity"),
            ing.get("unit"),
            ing.get("quantity_text"),
            1 if ing.get("is_optional") else 0,
            ing.get("substitute")
        ))

    return name_id_map
```

- [ ] **Step 3: 添加步骤导入函数**

在 `scripts/recipe_import.py` 中追加：

```python
def add_steps(conn, recipe_id, steps, name_id_map):
    """添加步骤列表，返回 {sequence: id} 映射"""
    if not steps:
        return {}
    cursor = conn.cursor()
    seq_id_map = {}

    for i, step in enumerate(steps):
        step_id = str(uuid.uuid4())
        seq = step.get("sequence", i + 1)
        seq_id_map[seq] = step_id

        cursor.execute("""
            INSERT INTO cooking_steps (
                id, recipe_id, sequence, action, duration_minutes,
                heat_level, temperature, expected_result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            step_id,
            recipe_id,
            seq,
            step["action"],
            step.get("duration"),
            step.get("heat_level"),
            step.get("temperature"),
            step.get("expected_result")
        ))

        # 处理步骤×食材关联
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

    return seq_id_map
```

- [ ] **Step 4: Commit**

```bash
git add scripts/recipe_import.py
git commit -m "feat: 添加关联数据导入函数（分类/标签/食材/步骤）"
```

---

### Task 5: 添加可选数据导入函数

**Files:**
- Modify: `scripts/recipe_import.py`

- [ ] **Step 1: 添加小贴士、技法、炊具、营养、背景导入函数**

在 `scripts/recipe_import.py` 中追加：

```python
def add_tips(conn, recipe_id, tips, seq_id_map):
    """添加小贴士"""
    if not tips:
        return
    cursor = conn.cursor()
    for tip in tips:
        tip_id = str(uuid.uuid4())
        step_id = None
        if tip.get("step_sequence") and tip["step_sequence"] in seq_id_map:
            step_id = seq_id_map[tip["step_sequence"]]

        cursor.execute("""
            INSERT INTO tips (id, recipe_id, step_id, ingredient_id, category, content, priority)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            tip_id,
            recipe_id,
            step_id,
            tip.get("ingredient_id"),
            tip.get("category"),
            tip["content"],
            tip.get("priority")
        ))


def add_techniques(conn, recipe_id, techniques, seq_id_map):
    """添加技法"""
    if not techniques:
        return
    cursor = conn.cursor()
    for tech in techniques:
        tech_id = str(uuid.uuid4())
        step_id = None
        if tech.get("step_sequence") and tech["step_sequence"] in seq_id_map:
            step_id = seq_id_map[tech["step_sequence"]]

        cursor.execute("""
            INSERT INTO step_techniques (id, step_id, recipe_id, technique_name, description, key_points)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            tech_id,
            step_id,
            recipe_id,
            tech["technique_name"],
            tech.get("description"),
            tech.get("key_points")
        ))


def add_cookware(conn, recipe_id, cookware_list):
    """添加炊具"""
    if not cookware_list:
        return
    cursor = conn.cursor()
    for cw in cookware_list:
        cw_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO cookware (id, recipe_id, name, category)
            VALUES (?, ?, ?, ?)
        """, (cw_id, recipe_id, cw["name"], cw.get("category")))


def add_nutrition(conn, recipe_id, nutrition):
    """添加营养信息"""
    if not nutrition:
        return
    cursor = conn.cursor()
    nutri_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO nutrition_info (
            id, recipe_id, serving_size, serving_unit,
            calories, protein, fat, carbs, fiber, sodium
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        nutri_id,
        recipe_id,
        nutrition.get("serving_size"),
        nutrition.get("serving_unit"),
        nutrition.get("calories"),
        nutrition.get("protein"),
        nutrition.get("fat"),
        nutrition.get("carbs"),
        nutrition.get("fiber"),
        nutrition.get("sodium")
    ))


def add_background(conn, recipe_id, background):
    """添加背景知识"""
    if not background:
        return
    cursor = conn.cursor()
    bg_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO background_knowledge (id, recipe_id, origin_story, historical_background, cultural_significance)
        VALUES (?, ?, ?, ?, ?)
    """, (
        bg_id,
        recipe_id,
        background.get("origin_story"),
        background.get("historical_background"),
        background.get("cultural_significance")
    ))
```

- [ ] **Step 2: Commit**

```bash
git add scripts/recipe_import.py
git commit -m "feat: 添加可选数据导入函数（小贴士/技法/炊具/营养/背景）"
```

---

### Task 6: 添加主导入函数和CLI入口

**Files:**
- Modify: `scripts/recipe_import.py`

- [ ] **Step 1: 添加主导入函数**

在 `scripts/recipe_import.py` 中追加：

```python
def import_recipe(json_file, choice=None, new_name=None):
    """主导入函数：加载JSON → 验证 → 检查冲突 → 事务导入"""
    # 1. 加载JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {"success": False, "errors": [f"JSON格式错误: {str(e)}"]}
    except FileNotFoundError:
        return {"success": False, "errors": [f"文件不存在: {json_file}"]}

    # 2. 验证
    errors = validate_recipe(data)
    if errors:
        return {"success": False, "errors": errors, "hint": "请修正JSON后重新导入"}

    # 3. 检查同名冲突
    conn = get_connection()
    try:
        has_conflict, conflict_result = check_conflict(conn, data["name"], choice)
        if has_conflict:
            conn.close()
            return conflict_result

        # 4. 处理derive需要new_name的情况
        if choice == "derive" and new_name:
            data["name"] = new_name

        # 5. 开启事务导入
        conn.execute("BEGIN")

        # 创建主记录
        recipe_id = create_recipe(conn, data)

        # 添加分类
        add_category(conn, recipe_id, data.get("category"))

        # 添加标签
        add_seasons(conn, recipe_id, data.get("seasons"))
        add_cooking_methods(conn, recipe_id, data.get("cooking_methods"))
        add_flavors(conn, recipe_id, data.get("flavors"))
        add_diet_tags(conn, recipe_id, data.get("diet_tags"))
        add_meal_types(conn, recipe_id, data.get("meal_types"))

        # 添加食材（返回name→id映射）
        name_id_map = add_ingredients(conn, recipe_id, data.get("ingredients"))

        # 添加步骤（返回seq→id映射，同时处理步骤×食材关联）
        seq_id_map = add_steps(conn, recipe_id, data.get("steps"), name_id_map)

        # 添加可选数据
        add_tips(conn, recipe_id, data.get("tips"), seq_id_map)
        add_techniques(conn, recipe_id, data.get("techniques"), seq_id_map)
        add_cookware(conn, recipe_id, data.get("cookware"))
        add_nutrition(conn, recipe_id, data.get("nutrition"))
        add_background(conn, recipe_id, data.get("background"))

        # 提交事务
        conn.execute("COMMIT")

        # 统计
        stats = {
            "success": True,
            "recipe_id": recipe_id,
            "name": data["name"],
            "ingredients_count": len(data.get("ingredients", [])),
            "steps_count": len(data.get("steps", []))
        }

        # 可选统计
        if data.get("tips"):
            stats["tips_count"] = len(data["tips"])
        if data.get("techniques"):
            stats["techniques_count"] = len(data["techniques"])
        if data.get("cookware"):
            stats["cookware_count"] = len(data["cookware"])
        if data.get("nutrition"):
            stats["has_nutrition"] = True
        if data.get("background"):
            stats["has_background"] = True

        return stats

    except Exception as e:
        try:
            conn.execute("ROLLBACK")
        except:
            pass
        return {"success": False, "error": str(e)}
    finally:
        conn.close()
```

- [ ] **Step 2: 添加CLI入口**

在 `scripts/recipe_import.py` 末尾追加：

```python
def show_template():
    """显示JSON模板路径"""
    template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "templates", "recipe_template.json")
    if os.path.exists(template_path):
        print(f"模板文件: {template_path}")
        with open(template_path, 'r', encoding='utf-8') as f:
            print(f.read())
    else:
        print(f"模板文件不存在: {template_path}")


def main():
    if len(sys.argv) < 2:
        print("""用法：
    python recipe_import.py import <json_file> [--choice <action>] [--new_name <新菜名>]
    python recipe_import.py validate <json_file>
    python recipe_import.py template

说明：
    import   - 导入JSON食谱文件
    validate - 仅验证JSON格式（不导入）
    template - 显示JSON模板

冲突处理选项 (--choice)：
    view     - 查看现有食谱
    derive   - 基于现有食谱创建新变体（需 --new_name）
    update   - 更新现有食谱
    cancel   - 取消导入
""")
        return

    action = sys.argv[1]

    if action == "template":
        show_template()
        return

    if action in ("import", "validate"):
        if len(sys.argv) < 3:
            print(f"错误：请提供JSON文件路径")
            return

        json_file = sys.argv[2]

        if action == "validate":
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                errors = validate_recipe(data)
                if errors:
                    print(f"验证失败：")
                    for err in errors:
                        print(f"  - {err}")
                else:
                    print(f"验证通过！")
            except json.JSONDecodeError as e:
                print(f"JSON格式错误: {e}")
            except FileNotFoundError:
                print(f"文件不存在: {json_file}")
            return

        # import
        choice = None
        new_name = None

        # 解析可选参数
        i = 3
        while i < len(sys.argv):
            if sys.argv[i] == "--choice" and i + 1 < len(sys.argv):
                choice = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--new_name" and i + 1 < len(sys.argv):
                new_name = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        result = import_recipe(json_file, choice=choice, new_name=new_name)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"未知操作：{action}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Commit**

```bash
git add scripts/recipe_import.py
git commit -m "feat: 完成recipe_import.py主导入函数和CLI入口"
```

---

### Task 7: 端到端测试 - 基本导入

**Files:**
- Test: `scripts/recipe_import.py`

- [ ] **Step 1: 创建测试JSON文件**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨"
```

创建临时测试文件 `test_recipe.json`:

```json
{
  "name": "测试菜品导入",
  "description": "端到端测试",
  "difficulty": "简单",
  "servings": 1,
  "total_time": 10,
  "ingredients": [
    {"name": "盐", "quantity": 5, "unit": "g", "category": "调料", "sequence": 1}
  ],
  "steps": [
    {"sequence": 1, "action": "加盐调味", "duration": 1, "heat_level": "小火"}
  ]
}
```

- [ ] **Step 2: 运行导入测试**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
python recipe_import.py import ../test_recipe.json
```

Expected: 输出包含 `"success": true` 和 `"recipe_id"`

- [ ] **Step 3: 验证数据已入库**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
python -c "
from db_config import get_connection
conn = get_connection()
cursor = conn.cursor()

cursor.execute(\"SELECT id, name FROM recipes WHERE name = '测试菜品导入'\")
recipe = cursor.fetchone()
print(f'食谱: {recipe}')

cursor.execute(\"SELECT * FROM ingredients WHERE recipe_id = ?\", (recipe['id'],))
ings = cursor.fetchall()
print(f'食材数: {len(ings)}')

cursor.execute(\"SELECT * FROM cooking_steps WHERE recipe_id = ?\", (recipe['id'],))
steps = cursor.fetchall()
print(f'步骤数: {len(steps)}')

conn.close()
print('数据验证通过')
"
```

Expected: 输出 `食谱:`, `食材数: 1`, `步骤数: 1`, `数据验证通过`

- [ ] **Step 4: 清理测试数据**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
python -c "
from db_config import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute(\"DELETE FROM recipes WHERE name = '测试菜品导入'\")
conn.commit()
conn.close()
print('测试数据已清理')
"
```

- [ ] **Step 5: 删除测试文件**

```bash
rm "D:/2Study/StudyNotes/SKILLS/私家大厨/test_recipe.json"
```

- [ ] **Step 6: Commit**

```bash
git add scripts/recipe_import.py
git commit -m "test: 验证基本导入功能正常"
```

---

### Task 8: 端到端测试 - 完整导入（含所有关联数据）

**Files:**
- Test: `scripts/recipe_import.py`

- [ ] **Step 1: 使用模板文件测试完整导入**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
python recipe_import.py import ../templates/recipe_template.json
```

Expected: 输出包含 `"success": true`，`"ingredients_count": 2`，`"steps_count": 2`

- [ ] **Step 2: 验证所有关联数据已入库**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
python -c "
from db_config import get_connection
conn = get_connection()
cursor = conn.cursor()

cursor.execute(\"SELECT id, name FROM recipes WHERE name = '宫保虾球'\")
recipe = cursor.fetchone()
rid = recipe['id']

# 验证各表
tables = {
    'recipe_categories': '分类',
    'recipe_seasons': '季节',
    'recipe_cooking_methods': '烹饪方式',
    'recipe_flavors': '口味',
    'recipe_diet_tags': '饮食标签',
    'recipe_meal_types': '用餐类型',
    'ingredients': '食材',
    'cooking_steps': '步骤',
    'step_ingredients': '步骤食材关联',
    'step_techniques': '技法',
    'tips': '小贴士',
    'cookware': '炊具',
    'nutrition_info': '营养',
    'background_knowledge': '背景',
}

for table, label in tables.items():
    cursor.execute(f'SELECT COUNT(*) as cnt FROM {table} WHERE recipe_id = ?', (rid,))
    cnt = cursor.fetchone()['cnt']
    status = '✓' if cnt > 0 else '✗'
    print(f'  {status} {label}: {cnt}条')

conn.close()
"
```

Expected: 所有表都有数据（✓）

- [ ] **Step 3: 清理测试数据**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
python -c "
from db_config import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute(\"DELETE FROM recipes WHERE name = '宫保虾球'\")
conn.commit()
conn.close()
print('测试数据已清理')
"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/recipe_import.py
git commit -m "test: 验证完整导入功能（含所有关联数据）"
```

---

### Task 9: 端到端测试 - 验证和冲突处理

**Files:**
- Test: `scripts/recipe_import.py`

- [ ] **Step 1: 测试验证失败**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
python recipe_import.py validate ../templates/recipe_template.json
```

Expected: `验证通过！`

创建一个错误的JSON测试验证失败：

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨"
echo '{"name": 123, "ingredients": "not_array"}' > test_bad.json
cd scripts
python recipe_import.py validate ../test_bad.json
```

Expected: 输出验证错误信息

- [ ] **Step 2: 测试同名冲突**

先导入一次：

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
python recipe_import.py import ../templates/recipe_template.json
```

Expected: `"success": true`

再导入一次（触发冲突）：

```bash
python recipe_import.py import ../templates/recipe_template.json
```

Expected: 输出 `"conflict": true`

- [ ] **Step 3: 测试冲突处理 - 取消**

```bash
python recipe_import.py import ../templates/recipe_template.json --choice cancel
```

Expected: `"status": "cancelled"`

- [ ] **Step 4: 测试冲突处理 - 派生**

```bash
python recipe_import.py import ../templates/recipe_template.json --choice derive --new_name "宫保虾球（改良版）"
```

Expected: `"success": true`, `"name": "宫保虾球（改良版）"`

- [ ] **Step 5: 清理所有测试数据**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"
python -c "
from db_config import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute(\"DELETE FROM recipes WHERE name IN ('宫保虾球', '宫保虾球（改良版）')\")
conn.commit()
conn.close()
print('测试数据已清理')
"
rm "D:/2Study/StudyNotes/SKILLS/私家大厨/test_bad.json"
```

- [ ] **Step 6: Commit**

```bash
git add scripts/recipe_import.py
git commit -m "test: 验证验证和冲突处理功能"
```

---

### Task 10: 更新文档

**Files:**
- Modify: `references/commands.md`
- Modify: `features/add.md`
- Modify: `SKILL.md`

- [ ] **Step 1: 更新 commands.md**

在 `references/commands.md` 末尾添加：

```markdown

---

## JSON导入命令（推荐）

> 低能力AI推荐使用此方式，一步完成食谱导入。

### 基本用法

```bash
# 导入食谱
python scripts/recipe_import.py import <json_file>

# 仅验证（不导入）
python scripts/recipe_import.py validate <json_file>

# 查看模板
python scripts/recipe_import.py template
```

### 冲突处理

```bash
# 查看现有食谱
python scripts/recipe_import.py import recipe.json --choice view

# 派生新变体
python scripts/recipe_import.py import recipe.json --choice derive --new_name "新菜名"

# 更新现有食谱
python scripts/recipe_import.py import recipe.json --choice update

# 取消导入
python scripts/recipe_import.py import recipe.json --choice cancel
```

### JSON格式

参考模板文件：`templates/recipe_template.json`

必填字段：
- `name` (string) - 菜名
- `ingredients` (array) - 食材列表，每项需有 `name`
- `steps` (array) - 步骤列表，每项需有 `action`

可选字段：
- `description`, `difficulty`, `servings`, `total_time`, `status`
- `category`, `seasons`, `cooking_methods`, `flavors`, `diet_tags`, `meal_types`
- `tips`, `techniques`, `cookware`, `nutrition`, `background`
```

- [ ] **Step 2: 更新 features/add.md**

在 `features/add.md` 的"命令参考"部分之前添加：

```markdown

---

## JSON文件导入（推荐）

> 低能力AI推荐使用此方式，避免多步CLI操作的错误。

### 流程

1. AI收集食谱信息
2. AI生成JSON文件
3. 调用导入命令：`python scripts/recipe_import.py import recipe.json`
4. 脚本自动完成所有数据库操作

### 优势

- 只需1个命令（vs 传统方式10个命令）
- JSON格式自验证
- 事务保护（失败自动回滚）
- 错误信息明确

### 参考

- JSON模板：`templates/recipe_template.json`
- 导入命令：`references/commands.md`（JSON导入命令部分）
```

- [ ] **Step 3: 更新 SKILL.md**

在 `SKILL.md` 的"快速导航"表后添加：

```markdown

---

## JSON文件导入（低能力AI推荐）

> 将10步CLI操作简化为1步JSON导入。

```bash
# 1. 查看模板
python scripts/recipe_import.py template

# 2. AI生成JSON文件

# 3. 导入
python scripts/recipe_import.py import recipe.json
```

详细说明见 `references/commands.md` 和 `features/add.md`。
```

- [ ] **Step 4: Commit**

```bash
git add references/commands.md features/add.md SKILL.md
git commit -m "docs: 添加JSON导入命令文档"
```

---

### Task 11: 最终验证

- [ ] **Step 1: 运行完整测试流程**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨/scripts"

# 1. 验证模板
python recipe_import.py validate ../templates/recipe_template.json

# 2. 导入模板
python recipe_import.py import ../templates/recipe_template.json

# 3. 验证数据
python -c "
from db_config import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute(\"SELECT COUNT(*) as cnt FROM recipes WHERE name = '宫保虾球'\")
print(f'食谱数: {cursor.fetchone()[\"cnt\"]}')
conn.close()
"

# 4. 清理
python -c "
from db_config import get_connection
conn = get_connection()
cursor = conn.cursor()
cursor.execute(\"DELETE FROM recipes WHERE name = '宫保虾球'\")
conn.commit()
conn.close()
print('清理完成')
"
```

Expected: 所有步骤成功

- [ ] **Step 2: 检查git状态**

```bash
cd "D:/2Study/StudyNotes/SKILLS/私家大厨"
git status
```

Expected: 工作区干净

- [ ] **Step 3: 最终Commit（如有遗漏）**

```bash
git add -A
git commit -m "feat: JSON文件导入方案完成"
```
