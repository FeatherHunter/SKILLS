# 录入食谱

> 路由：SKILL.md 用例1 → features/add.md

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 功能说明

用户发送食谱内容（图片或MD文件），AI解析后写入数据库。

**输入方式**：
1. 发送食谱图片 → OCR解析 → 确认 → 写入
2. 发送MD文件 → 文本解析 → 确认 → 写入

**遵循规范**：SKILL.md 中的"AI使用规范"。字段推测规则见下方。

### 字段推测规则

| 表/字段 | 推测规则 |
|---------|---------|
| recipes.description | 从菜名推断，如"经典川菜" |
| recipes.difficulty | 根据步骤复杂度/时间判断 |
| recipes.photo_url | 询问用户是否有照片 |
| recipes.source_url | 询问用户是否有链接 |
| ingredients.quantity_text | 用户说"适量"时填充，否则留空 |
| ingredients.is_optional | 用户明确说"可选"时设置1 |
| ingredients.substitute | 用户提到"可用XX代替"时填充 |
| ingredients.category | 根据食材名称推断（姜→蔬菜，虾→海鲜） |
| cooking_steps.temperature | 根据heat_level推断：中火≈160度，大火≈180-200度 |
| cooking_steps.expected_result | 根据步骤动作推测合理效果 |
| step_ingredients.quantity_used | 根据步骤动作和食材特性推断该步用量 |
| step_ingredients.introduced_at | 根据步骤序号推断：开局/第X步加入 |

**无法推测时，必须询问用户。**

---

## 格式要求

### 格式A - 结构化文本
```
【菜名】宫保虾球
【难度】中等
【总时间】25分钟
【菜系】川菜
【食材】虾300g，花生50g，干辣椒10g，花椒5g，葱1段，蒜3瓣
【步骤】第1步：虾去壳开背（10分钟）；第2步：大火热油炸变色；第3步：锅留底油爆香
...
```

### 格式B - JSON
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

如果某字段无法从输入中识别，标注为 `[未知]`，而不是留空。

**示例**：
- 难度：[未知]（无法从图片判断难度）→ AI根据步骤复杂度推测
- calories：[未知]（没有提供营养数据）→ AI询问用户或留空

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
...

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

## 录入成功后引导

```
✅ 宫保虾球录入成功！

可以对我说：
- "看看宫保虾球怎么做" ← 查看做法
- "生成宫保虾球的采购清单" ← 采购食材
- "再录入一道" ← 继续录入
```

---

## 命令参考

完整命令见 `references/commands.md`。

核心命令示例：

```bash
# 1. 创建食谱主记录
python scripts/recipe_manager.py add "宫保虾球" \
  --description "川菜经典，虾球Q弹，酸甜微辣" \
  --difficulty 中等 \
  --servings 2 \
  --total_time 25 \
  --status 未做

# 2. 添加分类
python scripts/category_manager.py add "<ID>" \
  --cuisine 川菜 --region 中国-四川 --country 中国

# 3. 添加食材
python scripts/ingredient_manager.py add "<ID>" \
  --name 虾 --quantity 300 --unit g --category 海鲜 --sequence 1

# 4. 添加步骤
python scripts/step_manager.py add "<ID>" \
  --action "虾去壳开背，用料酒和盐腌制10分钟" \
  --sequence 1 --duration 10 --heat_level 小火 \
  --temperature 常温 \
  --expected_result "虾肉变红，去腥"

# 5. 关联步骤×食材
python scripts/step_ingredient_manager.py add \
  --step_id "<步骤ID>" --ingredient_id "<食材ID>" \
  --quantity_used 300 --introduced_at "开局加入"

# 6. 添加技法
python scripts/technique_manager.py add \
  --recipe_id "<ID>" --step_id "<步骤ID>" \
  --technique_name 腌制 \
  --description "用料酒去腥" \
  --key_points "时间要够/料酒要适量"

# 7. 添加小贴士
python scripts/tip_manager.py add "<ID>" \
  --step_id "<步骤ID>" \
  --content "开背时去虾线更入味" \
  --category 刀工 --priority 1

# 8. 添加背景知识
python scripts/background_manager.py add "<ID>" \
  --origin_story "宫保虾球源自川菜宫保鸡丁的变体" \
  --historical_background "清代丁宝桢任四川总督时改良此菜" \
  --cultural_significance "代表川菜小荔枝口的经典味型"

# 9. 添加炊具
python scripts/cookware_manager.py add "<ID>" \
  --name 炒锅 --category 锅

# 10. 添加营养信息
python scripts/nutrition_manager.py add "<ID>" \
  --serving_size 200 --serving_unit g \
  --calories 320 --protein 28 --fat 18 \
  --carbs 20 --fiber 2 --sodium 800
```

---

## 参考

- 分类参考：`references/categories.md`
- 命令行参考：`references/commands.md`
- 表结构：`references/database_schema.md`