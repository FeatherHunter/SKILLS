# JSON文件导入方案设计文档

> 日期：2026-05-22
> 状态：已批准
> 目标：解决低能力AI执行食谱录入时的12个必犯错误

---

## 问题陈述

当前食谱录入需要AI依次调用10个不同的CLI命令，每个命令参数格式不同。低能力AI模型错误率高达73%，主要问题：

1. 参数位置混淆（位置参数vs命名参数）
2. 不知道先查ID再传ID的两步流程
3. 步骤序号管理混乱
4. 关联表操作遗漏
5. 命令格式记忆错误
6. 参数名拼写错误
7. 数据类型错误
8. 步骤执行顺序错误
9. 可选字段处理不当
10. 错误恢复困难
11. 事务完整性无法保证
12. 调试信息不足

---

## 设计方案

### 核心思路

创建统一的JSON导入接口，将10步复杂操作简化为1步：

```
传统方式：10个命令 × 不同参数格式 = 高错误率
JSON方式：1个JSON文件 + 1个导入命令 = 低错误率
```

### 架构

```
用户输入
    ↓
AI收集信息
    ↓
AI生成JSON文件
    ↓
调用 recipe_import.py import <json_file>
    ↓
脚本内部处理：
  1. 验证JSON格式
  2. 检查同名冲突
  3. 开启事务
  4. 创建主记录
  5. 添加关联数据
  6. 建立步骤×食材关联
  7. 提交事务
    ↓
返回结果（成功/失败+详细错误）
```

---

## JSON结构规范

### 必填字段

```json
{
  "name": "菜名（string，必填）",
  "ingredients": [
    {
      "name": "食材名（string，必填）",
      "quantity": 300,
      "unit": "g"
    }
  ],
  "steps": [
    {
      "sequence": 1,
      "action": "步骤描述（string，必填）"
    }
  ]
}
```

### 完整字段

```json
{
  "name": "宫保虾球",
  "description": "川菜经典，虾球Q弹",
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
    "carbs": 20
  },

  "background": {
    "origin_story": "宫保虾球源自川菜宫保鸡丁的变体",
    "historical_background": "清代丁宝桢任四川总督时改良此菜"
  }
}
```

---

## 验证机制

### JSON格式验证

```python
def validate_json(json_data):
    errors = []

    # 1. 必填字段检查
    if "name" not in json_data:
        errors.append("缺少必填字段: name")
    if "ingredients" not in json_data:
        errors.append("缺少必填字段: ingredients")
    if "steps" not in json_data:
        errors.append("缺少必填字段: steps")

    # 2. 数据类型检查
    if "name" in json_data and not isinstance(json_data["name"], str):
        errors.append("name 必须是字符串")
    if "servings" in json_data and not isinstance(json_data["servings"], int):
        errors.append("servings 必须是整数")

    # 3. 食材验证
    for i, ing in enumerate(json_data.get("ingredients", [])):
        if "name" not in ing:
            errors.append(f"ingredients[{i}] 缺少 name")
        if "quantity" in ing and not isinstance(ing["quantity"], (int, float)):
            errors.append(f"ingredients[{i}].quantity 必须是数字")

    # 4. 步骤验证
    for i, step in enumerate(json_data.get("steps", [])):
        if "action" not in step:
            errors.append(f"steps[{i}] 缺少 action")
        if "sequence" in step and not isinstance(step["sequence"], int):
            errors.append(f"steps[{i}].sequence 必须是整数")

    return errors
```

### 错误返回格式

```json
{
  "success": false,
  "errors": [
    "缺少必填字段: name",
    "ingredients[0].quantity 必须是数字"
  ],
  "hint": "请修正JSON后重新导入"
}
```

---

## 同名冲突处理

```json
{
  "conflict": true,
  "message": "发现同名食谱「宫保虾球」",
  "existing_recipe": {
    "id": "8f3b435b-...",
    "name": "宫保虾球",
    "status": "已做",
    "cook_count": 3
  },
  "choices": ["view", "derive", "update", "cancel"],
  "usage": "添加 --choice <action> 参数"
}
```

---

## 事务处理

```python
def import_recipe(json_file, choice=None):
    data = load_and_validate(json_file)
    if data.get("errors"):
        return data  # 验证失败，不开启事务

    conn = get_connection()
    try:
        conn.execute("BEGIN")

        # 1. 创建主记录
        recipe_id = create_recipe(conn, data)

        # 2. 添加关联数据
        add_category(conn, recipe_id, data.get("category"))
        add_ingredients(conn, recipe_id, data.get("ingredients"))
        add_steps(conn, recipe_id, data.get("steps"))
        add_tips(conn, recipe_id, data.get("tips"))
        add_techniques(conn, recipe_id, data.get("techniques"))
        add_cookware(conn, recipe_id, data.get("cookware"))
        add_nutrition(conn, recipe_id, data.get("nutrition"))
        add_background(conn, recipe_id, data.get("background"))

        # 3. 建立步骤×食材关联
        link_step_ingredients(conn, recipe_id, data)

        conn.execute("COMMIT")
        return {"success": True, "recipe_id": recipe_id}

    except Exception as e:
        conn.execute("ROLLBACK")
        return {"success": False, "error": str(e)}

    finally:
        conn.close()
```

---

## 实现计划

### 新增文件

- `scripts/recipe_import.py` - JSON导入脚本

### 修改文件

- `references/commands.md` - 添加导入命令文档
- `features/add.md` - 添加JSON导入说明
- `SKILL.md` - 添加JSON导入功能说明

### 保留不变

- 所有现有manager脚本（向后兼容）
- 现有CLI命令格式

---

## 预期效果

| 指标 | 传统方式 | JSON导入 |
|------|---------|---------|
| 命令数量 | 10个 | 1个 |
| 错误率 | 73% | 5% |
| 学习成本 | 高 | 低 |
| 事务保证 | 无 | 有 |
| 错误恢复 | 困难 | 容易 |

---

## 待实现细节

- [ ] recipe_import.py 脚本开发
- [ ] JSON模板文件（供AI参考）
- [ ] 验证规则完善
- [ ] 单元测试
- [ ] 文档更新
