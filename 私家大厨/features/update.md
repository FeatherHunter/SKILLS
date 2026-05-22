# 修改食谱

> 路由：SKILL.md 用例4 → features/update.md

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 功能说明

用户想修改食谱的某一部分时使用。修改粒度细化到：
- 食谱主表（名称/描述/难度/份量/时间/状态/照片/来源/链接）
- 分类标签（菜系/地区/国家/季节/烹饪方式/口味/饮食标签/用餐类型）
- 食材（增/改）
- 步骤（增/改/调整顺序）
- 步骤×食材关联（增/改）
- 技法（增/改）
- 小贴士（增/改）
- 背景故事
- 炊具
- 营养信息
- 烹饪历史（记录/评分/反馈）
- 派生关系（增/改）
- 废弃（discard，不物理删除）

**原则**：只增不删，整道食谱废弃用 discard，不物理删除。

**遵循规范**：SKILL.md 中的"AI使用规范"和"字段推测规则"。

---

## 通用前置步骤

所有修改操作需要先获取实体 ID：

1. **获取 recipe_id**：
   ```bash
   python scripts/recipe_manager.py show <菜名>
   ```
   → 从输出中获取食谱 ID

2. **获取 step_id**（修改步骤时需要）：
   ```bash
   python scripts/step_manager.py list <recipe_id>
   ```
   → 从输出中找到对应序号的步骤 ID

3. **获取 ingredient_id**（修改食材时需要）：
   ```bash
   python scripts/ingredient_manager.py list <recipe_id>
   ```
   → 从输出中找到对应食材的 ID

---

## 修改类型

### 修改主信息（单字段）

```
用户：把宫保虾球的难度改成困难
AI：确认修改：
    菜名：宫保虾球
    修改字段：难度 中等 → 困难

    确认吗？说"对"执行。

执行：
python scripts/recipe_manager.py update <recipe_id> --difficulty 困难
```

### 修改主信息（多字段）

```
用户：把宫保虾球的总时间改成40分钟，份量改成4人份
AI：确认修改：
    菜名：宫保虾球
    修改字段：
      总时间：25分钟 → 40分钟
      份量：2人份 → 4人份

    确认吗？说"对"执行。

执行：
python scripts/recipe_manager.py update <recipe_id> \
  --total_time 40 --servings 4
```

### 修改步骤

```
用户：宫保虾球的第3步改成小火炒，时长改成2分钟
AI：当前第3步：
    动作：锅留底油，大火爆香花椒和干辣椒
    序号：3 | 时长：1分钟 | 火候：大火 | 温度：200度

修改为：
    动作：锅留底油，小火炒香花椒和干辣椒
    序号：3 | 时长：2分钟 | 火候：小火 | 温度：160度

    确认吗？说"对"执行。

执行：
python scripts/step_manager.py update <step_id> \
  --action "锅留底油，小火炒香花椒和干辣椒" \
  --sequence 3 --duration 2 --heat_level 小火 --temperature 160度
```

### 添加食材（含步骤关联）

```
用户：给宫保虾球加一个食材，姜丝10g，在第4步加入
AI：确认添加：
    食材：姜丝
    用量：10g | 单位：g | 分类：蔬菜
    顺序：自动（接续现有顺序）
    关联步骤：第4步（引入时机：开局加入）

    确认吗？说"对"执行。

执行步骤：
1. python scripts/ingredient_manager.py add <recipe_id> \
     --name 姜丝 --quantity 10 --unit g --category 蔬菜
   → 假设返回 ingredient_id = "xxx"

2. python scripts/step_ingredient_manager.py add \
     --step_id <第4步ID> --ingredient_id xxx \
     --quantity_used 10 --introduced_at "开局加入"
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

### 更新小贴士优先级

```
用户：把宫保虾球"开背去虾线"这条小贴士的优先级改成1
AI：确认修改：
    食谱：宫保虾球
    小贴士：开背时去虾线更入味
    修改字段：优先级 3 → 1

    确认吗？说"对"执行。

执行：
python scripts/tip_manager.py update <tip_id> --priority 1
```

### 废弃食谱（discard）

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
# ========== 1. 食谱主表（recipes）==========
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


# ========== 2. 分类标签 ==========
# recipe_categories（菜系/地区/国家）
python scripts/category_manager.py update <recipe_id> --cuisine 新菜系 --region 新地区

# recipe_seasons（季节）
python scripts/season_manager.py add <recipe_id> --season 春,夏

# recipe_cooking_methods（烹饪方式）
python scripts/cooking_method_manager.py add <recipe_id> --method 炒,蒸

# recipe_flavors（口味）
python scripts/flavor_manager.py add <recipe_id> --flavor 辣,鲜

# recipe_diet_tags（饮食标签）
python scripts/diet_tag_manager.py add <recipe_id> --tag 高蛋白,低脂

# recipe_meal_types（用餐类型）
python scripts/meal_type_manager.py add <recipe_id> --meal_type 中,晚


# ========== 3. 食材（ingredients）==========
# 更新食材
python scripts/ingredient_manager.py update <ingredient_id> \
  --name 新名称 \
  --quantity 350 \
  --unit g \
  --quantity_text "350g（约为3两）" \
  --sequence 3 \
  --category 新分类 \
  --substitute 新替代


# ========== 4. 步骤（cooking_steps）==========
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
  --sequence 3 \
  --duration 5 \
  --heat_level 小火 \
  --temperature 120度 \
  --expected_result "新效果"

# 调整步骤顺序
python scripts/step_manager.py reorder <recipe_id> --from 2 --to 3


# ========== 5. 步骤×食材（step_ingredients）==========
# 关联食材到步骤
python scripts/step_ingredient_manager.py add \
  --step_id <step_id> \
  --ingredient_id <ingredient_id> \
  --quantity_used 30 \
  --introduced_at "出锅前"


# ========== 6. 技法（step_techniques）==========
# 添加/更新技法
python scripts/technique_manager.py update <technique_id> \
  --technique_name 新名称 \
  --description "技法解释，如大火热油快速翻炒" \
  --key_points "要点1/要点2"


# ========== 7. 小贴士（tips）==========
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


# ========== 8. 背景知识（background_knowledge）==========
# 更新背景知识
python scripts/background_manager.py update <recipe_id> \
  --origin_story "新故事" \
  --historical_background "新背景" \
  --cultural_significance "新意义"


# ========== 9. 炊具（cookware）==========
# 更新炊具
python scripts/cookware_manager.py update <cookware_id> \
  --name 新名称 --category 新分类


# ========== 10. 营养信息（nutrition_info）==========
# 更新营养信息
python scripts/nutrition_manager.py update <recipe_id> \
  --serving_size 200 \
  --serving_unit g \
  --calories 300 \
  --protein 30 \
  --fat 20 \
  --carbs 25 \
  --fiber 3 \
  --sodium 600


# ========== 11. 烹饪历史（recipe_history）==========
# 更新烹饪记录
python scripts/history_manager.py update <history_id> \
  --rating 4.0 \
  --feedback "新反馈"


# ========== 12. 派生关系（recipe_relations）==========
# 更新食谱派生关系
python scripts/relation_manager.py update <relation_id> \
  --relation_type 变体 \
  --change_summary "新变更说明"
```

---

## 参考

- 分类参考：`references/categories.md`
- 命令行参考：`references/commands.md`
- 表结构：`references/database_schema.md`