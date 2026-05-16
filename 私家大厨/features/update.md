# 修改食谱

> 路由：SKILL.md 用例4 → features/update.md

---

## 功能说明

用户想修改食谱的某一部分时使用。修改粒度细化到：
- 主信息（名称/难度/时间/份量/状态）
- 分类标签（菜系/季节/口味/烹饪方式）
- 食材（增/改）
- 步骤（增/改/调整顺序）
- 技法（增/改）
- 小贴士（增/改）
- 背景故事
- 炊具
- 营养信息

**原则**：只增不删，整道食谱废弃用 discard，不物理删除。

**遵循规范**：SKILL.md 中的"AI使用规范"和"字段推测规则"。

---

## 修改类型

### 修改主信息

```
用户：把宫保虾球的难度改成困难
AI：确认修改：
    菜名：宫保虾球
    修改字段：难度 中等 → 困难

    确认吗？说"对"执行。

执行：
python scripts/recipe_manager.py update <recipe_id> --difficulty 困难
```

### 修改步骤

```
用户：把宫保虾球的第3步改成小火炒
AI：当前第3步：
    动作：锅留底油，大火爆香花椒和干辣椒
    时长：1分钟
    火候：大火
    温度：200度

修改为：
    动作：锅留底油，小火炒香花椒和干辣椒
    时长：2分钟
    火候：小火
    温度：160度

确认吗？说"对"执行。

执行：
python scripts/step_manager.py update <step_id> \
  --action "锅留底油，小火炒香花椒和干辣椒" \
  --duration 2 --heat_level 小火 --temperature 160度
```

### 添加食材

```
用户：给宫保虾球加一个食材，姜丝10g
AI：确认添加：
    食材：姜丝
    用量：10g
    单位：g
    分类：蔬菜
    顺序：自动（接续现有顺序）

确认吗？说"对"执行。

执行：
python scripts/ingredient_manager.py add <recipe_id> \
  --name 姜丝 --quantity 10 --unit g --category 蔬菜
```

### 调整步骤顺序

```
用户：宫保虾球第2步和第3步换一下
AI：当前顺序：
    第2步：大火热油，虾下锅炸至变色捞出
    第3步：锅留底油，大火爆香花椒和干辣椒

调换后：
    第2步：锅留底油，大火爆香花椒和干辣椒
    第3步：大火热油，虾下锅炸至变色捞出

确认吗？说"对"执行。

执行：
python scripts/step_manager.py reorder <recipe_id> --from 2 --to 3
```

### 全局替换做法

```
用户：整道宫保虾球换成红烧做法
AI：确认将"宫保虾球"的烹饪方式从"炒"改为"红烧"，这将影响：
    - 步骤描述
    - 技法
    - 小贴士

是否继续？说"对"执行。
```

---

## 废弃食谱（discard）

整道食谱废弃（标记为已废弃），不再出现在列表和搜索中：

```
用户：不想要宫保虾球了
AI：确认废弃：
    食谱：宫保虾球
    状态：将变为「已废弃」

确认吗？说"对"执行。

执行：
python scripts/recipe_manager.py discard <recipe_id>
```

废弃后可通过 show 查看简要信息：
```
python scripts/recipe_manager.py show 宫保虾球
# 输出：⚠️ 「宫保虾球」已废弃
```

---

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

---

## 命令参考

```bash
# 更新食谱主信息
python scripts/recipe_manager.py update <recipe_id> \
  --name "新菜名" \
  --description "新描述" \
  --difficulty 困难 \
  --servings 4 \
  --total_time 45 \
  --status 熟练 \
  --photo_url "新图片URL" \
  --source "新来源" \
  --source_url "新链接"

# 废弃食谱
python scripts/recipe_manager.py discard <recipe_id>

# 更新分类
python scripts/category_manager.py update <recipe_id> \
  --cuisine 新菜系 --region 新地区

# 添加季节（支持多选）
python scripts/season_manager.py add <recipe_id> --season 春,夏

# 添加烹饪方式（支持多选）
python scripts/cooking_method_manager.py add <recipe_id> --method 炒,蒸

# 添加口味（支持多选）
python scripts/flavor_manager.py add <recipe_id> --flavor 辣,酱香

# 添加饮食标签（支持多选）
python scripts/diet_tag_manager.py add <recipe_id> --tag 荤菜,高蛋白

# 添加用餐类型（支持多选）
python scripts/meal_type_manager.py add <recipe_id> --meal_type 午,晚

# 更新食材
python scripts/ingredient_manager.py update <ingredient_id> \
  --name 新名称 \
  --quantity 350 \
  --unit g \
  --category 新分类 \
  --substitute 新替代

# 添加步骤
python scripts/step_manager.py add <recipe_id> \
  --action "新动作描述" \
  --sequence 4 \
  --duration 5 \
  --heat_level 中火 \
  --temperature 160度 \
  --expected_result "预期效果"

# 更新步骤
python scripts/step_manager.py update <step_id> \
  --action "新动作" \
  --duration 5 \
  --heat_level 小火 \
  --temperature 120度 \
  --expected_result "新效果"

# 调整步骤顺序
python scripts/step_manager.py reorder <recipe_id> --from 2 --to 3

# 关联食材到步骤
python scripts/step_ingredient_manager.py add \
  --step_id <step_id> \
  --ingredient_id <ingredient_id> \
  --quantity_used 30 \
  --introduced_at "出锅前"

# 添加/更新技法
python scripts/technique_manager.py update <technique_id> \
  --technique_name 新名称 \
  --key_points "要点1/要点2"

# 添加小贴士
python scripts/tip_manager.py add <recipe_id> \
  --step_id <step_id> \
  --ingredient_id <ingredient_id> \
  --content "新技巧" \
  --category 火候 \
  --priority 1

# 更新小贴士
python scripts/tip_manager.py update <tip_id> \
  --content "更新后的内容" \
  --category 火候 \
  --priority 2

# 更新背景知识
python scripts/background_manager.py update <recipe_id> \
  --origin_story "新故事" \
  --historical_background "新背景" \
  --cultural_significance "新意义"

# 更新炊具
python scripts/cookware_manager.py update <cookware_id> \
  --name 新名称 --category 新分类

# 更新营养信息
python scripts/nutrition_manager.py update <recipe_id> \
  --calories 300 \
  --protein 30 \
  --fat 20 \
  --carbs 25 \
  --fiber 3 \
  --sodium 600

# 更新烹饪记录
python scripts/history_manager.py update <history_id> \
  --rating 4.0 \
  --feedback "新反馈"
```

---

## 参考

- 分类参考：`references/categories.md`
- 命令行参考：`references/commands.md`
- 表结构：`references/database_schema.md`