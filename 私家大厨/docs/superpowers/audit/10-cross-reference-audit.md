# 交叉引用一致性检查报告

> 检查范围：6个feature文件 + commands.md + database_schema.md + categories.md + recipe_template.json
> 检查日期：2026-05-23

---

## 命令格式不一致

| 功能文件 | 命令 | 问题 | 严重程度 |
|---------|------|------|---------|
| history.md | `history_manager.py list 宫保虾球` | 示例使用菜名而非recipe_id，与commands.md定义 `<recipe_id>` 不一致 | P0 |
| history.md | `history_manager.py stats 宫保虾球` | 示例使用菜名而非recipe_id，与commands.md定义 `<recipe_id>` 不一致 | P0 |
| search.md | `tip_manager.py search 火候 --recipe-id <食谱ID>` | 使用了 `--recipe-id` 可选参数，但commands.md中tip_manager search未定义此参数 | P1 |
| add.md | 命令参考（第221-278行） | 仅展示10条命令（到营养信息），遗漏第11步"记录烹饪历史"，与commands.md完整工作流（11步）不一致 | P2 |

## 参数名不一致

无发现。各feature文件中使用的参数名（如--cook_date、--rating、--feedback、--difficulty等）均与commands.md定义一致。

## 字段值范围不一致

| 功能文件 | 字段 | 期望值（commands.md） | 实际值 | 严重程度 |
|---------|------|----------------------|--------|---------|
| recipe_template.json | meal_types | 早/中/晚/夜宵/下午茶/聚会 | "晚餐"（应为"晚"） | P0 |
| update.md | flavor | 酸/甜/辣/咸/鲜/苦/麻 | "酱香"（不在有效值列表中） | P1 |
| update.md | meal_type | 早/中/晚/夜宵/下午茶/聚会 | "午"（不在有效值列表中，应为"中"） | P1 |
| commands.md（示例行231） | meal_type | 早/中/晚/夜宵/下午茶/聚会 | "午"（示例与参数说明矛盾） | P1 |
| update.md | diet_tag | 素食/清真/无辣/低碳/无糖/低脂/无麸质/高蛋白 | "荤菜"（不在有效值列表中） | P1 |
| commands.md（示例行766） | diet_tag | 素食/清真/无辣/低碳/无糖/低脂/无麸质/高蛋白 | "荤菜"（示例与参数说明矛盾） | P1 |
| shopping.md | ingredient category | 肉类/蔬菜/调料/海鲜/豆制品/蛋类/主食/干货/其他 | 仅列出6类（肉类/蔬菜/调料/海鲜/蛋类/其他），遗漏豆制品/主食/干货 | P2 |

## 字段推测规则差异

add.md（第23-39行）和commands.md（第819-833行）各维护了一份字段推测规则表，存在以下差异：

| 字段 | add.md | commands.md | 严重程度 |
|------|--------|-------------|---------|
| recipes.description | "从菜名推断，如'经典川菜'" | "如用户说'经典川菜'，则用菜名+类型描述" | P3 |
| recipes.difficulty | 有（根据步骤复杂度/时间判断） | 无 | P2 |
| recipes.photo_url | "询问用户是否有照片" | "留空，询问用户是否有照片" | P3 |
| ingredients.quantity_text | "用户说'适量'时填充，否则留空" | "用户说'适量'、'少许'时填充，否则留空" | P3 |
| ingredients.is_optional | "用户明确说'可选'时设置1" | "用户明确说'可选'时设置为1" | P3 |
| ingredients.category | 有（根据食材名称推断） | 无 | P2 |
| cooking_steps.temperature | "中火≈160度，大火≈180-200度" | "中火≈160-180度，大火≈180-200度" | P2 |
| cooking_steps.expected_result | "根据步骤动作推测合理效果" | "根据步骤动作推测合理效果"（一致） | -- |
| step_ingredients.quantity_used | "根据步骤动作和食材特性推断该步用量" | "继承ingredients.quantity" | P2 |
| step_ingredients.introduced_at | "根据步骤序号推断：开局/第X步加入" | "根据步骤序号推测：开局/第X步加入" | P3 |

---

## 数据库表名/字段名检查

feature文件中引用的表名和字段名与database_schema.md对比：

| 功能文件 | 引用 | 期望值（database_schema.md） | 结果 |
|---------|------|----------------------------|------|
| 全部feature文件 | recipes表字段total_time | 数据库字段名为total_time_minutes | CLI参数为--total_time，与CLI层面一致，但与数据库字段名不同 |
| shopping.md | 输出JSON中ingredients[].is_optional | 数据库字段名为is_integer INTEGER | 字段名一致 |
| search.md | recipe_categories.cuisine_type | 数据库字段cuisine_type | 一致 |

数据库层面无实质性不一致。CLI参数名（--total_time）与数据库字段名（total_time_minutes）的映射由脚本内部处理，不属于feature文件错误。

---

## 分类值参考检查

feature文件中使用的分类值与categories.md对比：

| 功能文件 | 分类 | 使用的值 | categories.md有效值 | 结果 |
|---------|------|---------|-------------------|------|
| commands.md | 菜系 | 示例中用"川菜" | 川菜 | 一致 |
| commands.md | 菜系参数说明 | 川菜/粤菜/湘菜/东北菜/台湾菜/福建菜/京菜/苏菜/浙菜/新疆菜/本帮菜 | categories.md列出11类但含"沪菜"和"鲁菜"，无"新疆菜"和"本帮菜" | 命令参考与分类参考不一致，但不影响功能（数据由用户输入） |
| categories.md | 烹饪方式 | 含"生食" | commands.md有效值列表无"生食" | categories.md多出"生食"值 |

---

## 统计

- **总发现：19个不一致**
- **P0：3个**
  1. history.md示例使用菜名而非recipe_id（list命令）
  2. history.md示例使用菜名而非recipe_id（stats命令）
  3. recipe_template.json中meal_types使用"晚餐"而非"晚"
- **P1：5个**
  1. search.md tip_manager search使用未文档化的--recipe-id参数
  2. update.md示例中flavor使用无效值"酱香"
  3. update.md示例中meal_type使用无效值"午"
  4. commands.md自身示例中meal_type使用"午"与参数说明矛盾
  5. commands.md自身示例中diet_tag使用"荤菜"与参数说明矛盾
- **P2：6个**
  1. add.md遗漏第11步命令（记录烹饪历史）
  2. shopping.md遗漏3个食材分类（豆制品/主食/干货）
  3. add.md推测规则多出recipes.difficulty字段
  4. add.md推测规则多出ingredients.category字段
  5. cooking_steps.temperature推测范围不一致（add.md vs commands.md）
  6. step_ingredients.quantity_used推测逻辑不一致（推断 vs 继承）
- **P3：5个**
  1. recipes.description推测描述措辞差异
  2. recipes.photo_url推测描述差异（留空 vs 直接询问）
  3. ingredients.quantity_text推测值差异（适量 vs 适量/少许）
  4. ingredients.is_optional描述措辞差异
  5. step_ingredients.introduced_at措辞差异（推测 vs 推断）

---

## 修复建议

### P0 修复（立即）

1. **history.md**：将示例中的菜名改为recipe_id占位符 `<recipe_id>`，或确认脚本支持菜名查找并注明
2. **recipe_template.json**：将 `meal_types: ["晚餐"]` 改为 `meal_types: ["晚"]`

### P1 修复（尽快）

3. **commands.md**：在tip_manager search命令中补充 `--recipe-id` 可选参数说明
4. **commands.md**：修正示例中的"午"为"中"
5. **commands.md**：修正示例中的"荤菜"为有效值（或新增"荤菜"到有效值列表）
6. **update.md**：修正flavor示例"酱香"为有效值
7. **update.md**：修正meal_type示例"午"为"中"
8. **update.md**：修正diet_tag示例"荤菜"为有效值

### P2 修复（计划内）

9. **add.md**：补充第11步"记录烹饪历史"命令
10. **shopping.md**：补充完整9个食材分类
11. **统一推测规则表**：合并add.md和commands.md中的字段推测规则为一份权威源
