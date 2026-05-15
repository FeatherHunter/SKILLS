# 录入食谱

> 触发词：（通过图片路由技能自动触发，或用户主动说"录入这个菜"）

---

## 功能说明

用户发送食谱内容（图片或MD文件），AI解析后写入数据库。

**输入方式**：
1. 发送食谱图片 → OCR解析 → 确认 → 写入
2. 发送MD文件 → 文本解析 → 确认 → 写入

**原则**：
- 只增不删
- 所有写操作前必须展示，用户确认后再执行
- 信息不完整时追问，不猜测

---

## AI调用规范

### 调用任何manager前，必须：

1. **展示完整参数示例** — 让用户知道这条命令会用哪些参数
2. **对未提供字段进行合理推测** — 基于菜系特点/常见值/烹饪逻辑
3. **推测不出时询问用户** — 不能留空不填

### 字段推测规则

| 字段 | 推测规则 |
|------|---------|
| recipes.description | 从菜名推断，如"经典川菜" |
| recipes.difficulty | 根据步骤复杂度/时间判断 |
| ingredients.quantity_text | 用户说"适量"时填充，否则留空 |
| ingredients.is_optional | 用户明确说"可选"时设置1 |
| ingredients.substitute | 用户提到"可用XX代替"时填充 |
| cooking_steps.temperature | 根据heat_level推断：中火≈160度，大火≈180-200度 |
| cooking_steps.expected_result | 根据步骤动作推测合理效果 |

---

## 【致调用方AI - 字段清单】

当你准备调用本技能录入食谱时，请尽量提供以下所有字段。调用方AI应从输入中提取并组织这些数据。

---

### 一、食谱主表（recipes）

| 字段名 | 说明 | 示例 | 推测规则 |
|--------|------|------|---------|
| name | 菜名 | 宫保虾球 | 必需 |
| description | 一句话描述 | 川菜经典，虾球Q弹 | 从菜名推断 |
| difficulty | 难度 | 快手菜/简单/中等/困难/大师 | 根据步骤复杂度判断 |
| servings | 份量（人数） | 2 | 默认2 |
| total_time_minutes | 总时间（分钟） | 25 | 累加步骤时长 |
| status | 状态 | 未做/已做/熟练 | 默认未做 |
| photo_url | 模板照URL或路径 | /path/to/photo.jpg | 询问用户 |
| source | 来源说明 | 中餐厅节目 | 从内容提取 |
| source_url | 原始链接 | https://example.com/recipe | 留空，询问用户 |

---

### 二、分类标签

#### 2.1 recipe_categories（菜系/地区/国家）
| 字段名 | 说明 | 示例 |
|--------|------|------|
| cuisine_type | 菜系 | 川菜/粤菜/湘菜/东北菜/台湾菜/福建菜/京菜/苏菜/浙菜/新疆菜 |
| region | 地区 | 中国-四川/中国-广东-潮汕/中国-江苏-如皋 |
| country | 国家 | 中国/日本/泰国/美国/法国 |

#### 2.2 recipe_seasons（适合季节）
| 字段名 | 说明 | 示例 |
|--------|------|------|
| season | 季节（可多选） | 春/夏/秋/冬 |

#### 2.3 recipe_cooking_methods（烹饪方式）
| 字段名 | 说明 | 示例 |
|--------|------|------|
| method | 烹饪方式（可多选） | 炒/蒸/煮/烤/炸/煎/焖/炖/拌/卤/熏 |

#### 2.4 recipe_flavors（口味）
| 字段名 | 说明 | 示例 |
|--------|------|------|
| flavor | 口味（可多选） | 酸/甜/辣/咸/鲜/苦/麻 |

#### 2.5 recipe_diet_tags（饮食标签）
| 字段名 | 说明 | 示例 |
|--------|------|------|
| tag | 饮食标签（可多选） | 素食/清真/无辣/低碳/无糖/低脂/无麸质/高蛋白 |

#### 2.6 recipe_meal_types（用餐类型）
| 字段名 | 说明 | 示例 |
|--------|------|------|
| meal_type | 用餐类型（可多选） | 早/中/晚/夜宵/下午茶/聚会 |

---

### 三、食材清单（ingredients）

每种食材需提供以下字段：

| 字段名 | 说明 | 示例 | 推测规则 |
|--------|------|------|---------|
| sequence | 添加顺序（数字） | 1 | 自动+1 |
| name | 食材名称 | 虾 | 必需 |
| category | 分类 | 肉类/蔬菜/调料/海鲜/豆制品/蛋类/主食/干货/其他 | 根据名称推断 |
| quantity | 用量数值 | 300 | 用户提供时填，否则留空 |
| unit | 单位 | g/kg/ml/L/个/勺/把/茶匙/杯/段/瓣 | 根据quantity推断 |
| quantity_text | 文字描述（替代用量） | 适量/少许/一小把/若干 | 用户说"适量"时填 |
| is_optional | 是否可选（1=可选） | 0 | 用户明确说"可选"时设1 |
| substitute | 替代食材 | 可用鸡胸肉代替 | 用户提到替代时填 |

---

### 四、烹饪步骤（cooking_steps）

每个步骤需提供以下字段：

| 字段名 | 说明 | 示例 | 推测规则 |
|--------|------|------|---------|
| sequence | 步骤顺序（数字） | 1 | 自动+1 |
| action | 动作描述 | 虾去壳开背，用料酒和盐腌制10分钟 | 必需 |
| duration_minutes | 该步时长（分钟） | 10 | 从内容提取 |
| heat_level | 火候 | 微火/小火/中火/大火/猛火 | 根据动作推断 |
| temperature | 温度描述 | 160度/中小火/滚开 | 根据heat_level推断 |
| expected_result | 预期效果 | 虾肉变红，表面微焦 | 根据动作推测 |

---

### 五、步骤×食材关联（step_ingredients）

每个步骤关联的每个食材需提供：

| 字段名 | 说明 | 示例 | 推测规则 |
|--------|------|------|---------|
| step_sequence | 关联的步骤序号 | 1 | 必需 |
| ingredient_name | 食材名称 | 虾 | 必需 |
| quantity_used | 该步使用量 | 300 | 继承ingredients.quantity |
| introduced_at | 引入时机描述 | 开局加入/出锅前/熄火后 | 根据步骤序号推断 |

---

### 六、步骤技法（step_techniques）

每个步骤的技法需提供：

| 字段名 | 说明 | 示例 |
|--------|------|------|
| step_sequence | 关联的步骤序号 | 2 |
| technique_name | 技法名称 | 爆炒/滑炒/煸炒/颠勺/爆香/滑蛋/挂糊/上浆 |
| description | 技法解释 | 大火热油，快速翻炒 |
| key_points | 关键要点（用/分隔） | 油温要高/翻炒要快/时间要短 |

---

### 七、小贴士（tips）

每条小贴士需提供：

| 字段名 | 说明 | 示例 |
|--------|------|------|
| step_sequence | 关联步骤（可选） | 2 |
| ingredient_name | 关联食材名称（可选） | 虾 |
| category | 分类 | 火候/刀工/调味/采购/设备/保存 |
| content | 技巧内容 | 开背时去虾线更入味 |
| priority | 优先级（数字越小越重要） | 1 |

---

### 八、背景知识（background_knowledge）

| 字段名 | 说明 | 示例 |
|--------|------|------|
| origin_story | 起源故事 | 宫保虾球源自川菜宫保鸡丁的变体 |
| historical_background | 历史背景 | 清代丁宝桢发明 |
| cultural_significance | 文化意义 | 代表川菜小荔枝口的经典味型 |

---

### 九、炊具（cookware）

每种炊具需提供：

| 字段名 | 说明 | 示例 |
|--------|------|------|
| name | 炊具名称 | 电饭锅/砂锅/烤箱/蒸笼/空气炸锅 |
| category | 分类 | 锅/炉/刀/其他 |

---

### 十、营养信息（nutrition_info）

| 字段名 | 说明 | 示例 |
|--------|------|------|
| serving_size | 每份份量数值 | 200 |
| serving_unit | 份量单位 | g/克/份/碗 |
| calories | 每份热量（kcal） | 320 |
| protein | 每份蛋白质（g） | 28 |
| fat | 每份脂肪（g） | 18 |
| carbs | 每份碳水化合物（g） | 20 |
| fiber | 每份膳食纤维（g） | 2 |
| sodium | 每份钠（mg） | 800 |

---

## 格式要求

请按以下格式组织数据传递给本技能：

**格式A - 结构化文本**：
```
【菜名】宫保虾球
【难度】中等
【总时间】25分钟
【菜系】川菜
【食材】虾300g，花生50g，干辣椒10g，花椒5g，葱1段，蒜3瓣
【步骤】第1步：虾去壳开背（10分钟）；第2步：大火热油炸变色；第3步：锅留底油爆香
...
```

**格式B - JSON**：
```json
{
  "name": "宫保虾球",
  "difficulty": "中等",
  "total_time_minutes": 25,
  "cuisine_type": "川菜",
  "ingredients": [...],
  "steps": [...],
  ...
}
```

---

## 缺失字段处理

如果某字段无法从输入中识别，请在输出中标注为 `[未知]`，而不是留空。

**示例**：
- 难度：[未知]（无法从图片判断难度）→ AI根据步骤复杂度推测
- calories：[未知]（没有提供营养数据）→ AI询问用户或留空

本技能会询问用户补充关键字段。

---

## 交互流程

```
用户：[发送图片或MD文件]

AI：我解析到了这道菜的完整信息，请确认：

【菜名】宫保虾球
【难度】中等 | 【时间】25分钟 | 【份量】2人份
【分类】川菜 | 【口味】辣/麻

【食材清单】
1. 虾 300g
2. 花生 50g（可选）
3. 干辣椒 10g
4. 花椒 5g
5. 葱 1段
6. 蒜 3瓣
7. 盐 适量
8. 料酒 15ml

【完整步骤】
第1步（10分钟）：虾去壳开背，用料酒和盐腌制10分钟
第2步（3分钟）：大火热油，虾下锅炸至变色捞出
第3步（1分钟）：锅留底油，大火爆香花椒和干辣椒
...

确认无误吗？说"对"开始录入。
```

---

## 解析失败处理

```
用户：[发送图片]

AI：抱歉，我无法从这张图片中解析出食谱内容。
请尝试：
1. 确保图片中包含清晰的文字（如菜名、食材、步骤）
2. 或者直接告诉我这道菜的菜名，我帮你新建一个空的食谱
3. 也可以发送MD格式的食谱文件
```

---

## AI执行示例

### 完整录入一道菜

```bash
# 1. 创建食谱主记录（完整参数）
python scripts/recipe_manager.py add "宫保虾球" \
  --description "川菜经典，虾球Q弹，酸甜微辣" \
  --difficulty 中等 \
  --servings 2 \
  --total_time 25 \
  --status 未做 \
  --source "中餐厅节目"

# 2. 添加分类
python scripts/category_manager.py add "<返回的ID>" \
  --cuisine 川菜 --region 中国-四川 --country 中国

python scripts/season_manager.py add "<ID>" --season 春,夏,秋

python scripts/cooking_method_manager.py add "<ID>" --method 炒

python scripts/flavor_manager.py add "<ID>" --flavor 辣,酸甜

python scripts/diet_tag_manager.py add "<ID>" --tag 荤菜

python scripts/meal_type_manager.py add "<ID>" --meal_type 午,晚

# 3. 添加食材（每种食材完整参数）
python scripts/ingredient_manager.py add "<ID>" \
  --name 虾 --quantity 300 --unit g --category 海鲜 --sequence 1

python scripts/ingredient_manager.py add "<ID>" \
  --name 花生 --quantity 50 --unit g --category 其他 --sequence 2 \
  --optional --substitute 腰果

python scripts/ingredient_manager.py add "<ID>" \
  --name 干辣椒 --quantity 10 --unit g --category 调料 --sequence 3

python scripts/ingredient_manager.py add "<ID>" \
  --name 花椒 --quantity 5 --unit g --category 调料 --sequence 4

# ... 其他食材

# 4. 添加步骤（完整参数）
python scripts/step_manager.py add "<ID>" \
  --action "虾去壳开背，用料酒和盐腌制10分钟" \
  --sequence 1 --duration 10 --heat_level 小火 \
  --temperature 常温 \
  --expected_result "虾肉变红，去腥"

python scripts/step_manager.py add "<ID>" \
  --action "大火热油，虾下锅炸至变色捞出" \
  --sequence 2 --duration 3 --heat_level 大火 \
  --temperature 180度 \
  --expected_result "虾肉变红，表面微焦"

# ... 其他步骤

# 5. 关联步骤×食材
python scripts/step_ingredient_manager.py add \
  --step_id "<步骤1ID>" --ingredient_id "<虾ID>" \
  --quantity_used 300 --introduced_at "开局加入"

# ... 其他关联

# 6. 添加技法
python scripts/technique_manager.py add \
  --recipe_id "<ID>" --step_id "<步骤2ID>" \
  --technique_name 油炸 \
  --description "高油温快速定型，外焦里嫩" \
  --key_points "油温要高/炸制时间短/复炸更酥脆"

# 7. 添加小贴士
python scripts/tip_manager.py add "<ID>" \
  --step_id "<步骤1ID>" \
  --content "开背时去虾线更入味" \
  --category 刀工 --priority 1

# 8. 添加背景知识
python scripts/background_manager.py add "<ID>" \
  --origin_story "宫保虾球源自川菜宫保鸡丁的变体，由山东人丁宝桢发明" \
  --historical_background "清代丁宝桢任四川总督时改良此菜" \
  --cultural_significance "代表川菜小荔枝口的经典味型"

# 9. 添加炊具
python scripts/cookware_manager.py add "<ID>" \
  --name 炒锅 --category 锅

# 10. 添加营养信息（完整参数）
python scripts/nutrition_manager.py add "<ID>" \
  --serving_size 200 --serving_unit g \
  --calories 320 --protein 28 --fat 18 \
  --carbs 20 --fiber 2 --sodium 800

# 11. 记录烹饪历史
python scripts/history_manager.py add "<ID>" \
  --cook_date 2026-05-15 --rating 4.5 \
  --feedback "味道不错，虾很Q弹"
```

---

## 参考

- 分类参考：references/categories.md
- 命令行参考：references/commands.md
- 表结构：references/database_schema.md