# 查看食谱 + 做菜模式

> 路由：SKILL.md 用例2 → features/view.md

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 功能说明

### 查看食谱
用户想了解一道菜的做法时，生成**完整信息展示 HTML**，覆盖 17 张表所有可展示字段。

### 做菜模式
从查看食谱延伸，用户确认开始做菜后，生成**可交互检查清单 HTML**，辅助实际做菜过程。

**遵循规范**：SKILL.md 中的"AI使用规范"和"字段推测规则"。

---

## 内部分流逻辑

```
用户说"开始做这道菜"或"开始做XX"
    → 直接进入做菜模式（复用已查数据，不再重复查询）

用户说"看看XX怎么做"等
    → 先展示完整食谱
    → 末尾问"要开始做吗？"
    → 用户确认后才进入做菜模式
```

---

## 查看食谱模式

### 工作流

```
用户："看看XX怎么做"
    ↓
【查询阶段】按顺序执行以下命令，收集所有数据
    ↓
【生成阶段】AI 将所有数据组织为 HTML
    ↓
【发送阶段】HTML 保存到媒体目录，通过 QQBot 发送
```

### 查询命令清单（按顺序）

```bash
# 1. 主表
python scripts/recipe_manager.py show <菜名或ID>

# 2. 分类标签（7张分类关联表）
python scripts/category_manager.py list <recipe_id>
python scripts/season_manager.py list <recipe_id>
python scripts/cooking_method_manager.py list <recipe_id>
python scripts/flavor_manager.py list <recipe_id>
python scripts/diet_tag_manager.py list <recipe_id>
python scripts/meal_type_manager.py list <recipe_id>

# 3. 炊具
python scripts/cookware_manager.py list <recipe_id>

# 4. 食材（含关联的 step_ingredients）
python scripts/ingredient_manager.py list <recipe_id>
# 遍历每条食材，获取其被哪些步骤使用
python scripts/step_ingredient_manager.py list-by-ingredient <ingredient_id>

# 5. 步骤（含关联的 step_techniques）
python scripts/step_manager.py list <recipe_id>
# 遍历每条步骤，获取其关联的技法
python scripts/technique_manager.py list-by-step <step_id>
# 遍历每条步骤，获取其投入的食材
python scripts/step_ingredient_manager.py list-by-step <step_id>

# 6. 小贴士
python scripts/tip_manager.py list <recipe_id>

# 7. 烹饪历史
python scripts/history_manager.py list <recipe_id>

# 8. 背景知识
python scripts/background_manager.py get <recipe_id>

# 9. 派生关系
python scripts/relation_manager.py list-parent <recipe_id>
python scripts/relation_manager.py list-child <recipe_id>

# 10. 营养信息
python scripts/nutrition_manager.py get <recipe_id>
```

### 字段覆盖清单（17张表 × 所有可展示字段）

| 表 | 字段 | 展示位置 |
|---|---|---|
| **recipes** | name | 页面标题 |
| | description | 基本信息区（独立一行） |
| | difficulty | 基本信息区 |
| | servings | 基本信息区（"2人份"） |
| | total_time_minutes | 基本信息区（"25分钟"） |
| | status | 基本信息区（附"已做X次，评分Y"） |
| | photo_url | 图片区（有图显示，无图用emoji占位） |
| | source | 基本信息区 |
| | source_url | 基本信息区（可点击链接） |
| | created_at/updated_at | 基本信息区底部（时间） |
| **recipe_categories** | cuisine_type | 分类标签区（pill样式） |
| | region | 分类标签区 |
| | country | 分类标签区 |
| **recipe_seasons** | season | 分类标签区（春/夏/秋/冬） |
| **recipe_cooking_methods** | method | 分类标签区（炒/蒸/煮...） |
| **recipe_flavors** | flavor | 分类标签区（酸/甜/辣...） |
| **recipe_diet_tags** | tag | 分类标签区（荤菜/高蛋白...） |
| **recipe_meal_types** | meal_type | 分类标签区（早/中/晚...） |
| **cookware** | name | 厨具区（炒锅） |
| | category | 厨具区（锅） |
| **ingredients** | name | 食材区（虾） |
| | quantity | 食材区（300） |
| | unit | 食材区（g） |
| | quantity_text | 食材区（适量/约300g） |
| | is_optional | 食材区（"可选"标记） |
| | substitute | 食材区（"可用XXX代替"） |
| | category | 食材区（海鲜） |
| **cooking_steps** | sequence | 步骤区（"第1步"） |
| | action | 步骤区（动作描述） |
| | duration_minutes | 步骤区（"10分钟"） |
| | heat_level | 步骤区（"小火"） |
| | temperature | 步骤区（"180度"） |
| | expected_result | 步骤区（"虾肉变红"） |
| **step_ingredients** | quantity_used | 内嵌步骤区（"投入：虾 300g"） |
| | introduced_at | 内嵌步骤区（"第2步加入"） |
| **step_techniques** | technique_name | 内嵌步骤区（"腌制"） |
| | description | 内嵌步骤区（"用料酒去腥"） |
| | key_points | 内嵌步骤区（"时间要够/料酒适量"） |
| **tips** | content | 小贴士区 |
| | category | 小贴士区标签（刀工/火候/采购...） |
| | priority | 小贴士区（数字越小越靠前） |
| | step_id | 小贴士区（关联步骤标注） |
| | ingredient_id | 小贴士区（关联食材标注） |
| **recipe_history** | cook_date | 历史区（"2026-05-15"） |
| | cook_sequence | 历史区（"第3次"） |
| | rating | 历史区（"4.5分"） |
| | feedback | 历史区（"虾很Q弹"） |
| **background_knowledge** | origin_story | 背景区第一段（起源） |
| | historical_background | 背景区第二段（历史） |
| | cultural_significance | 背景区第三段（文化） |
| **recipe_relations** | parent_id/relation_type | 派生区（"由宫保鸡丁派生"） |
| | child_id/relation_type | 派生区（"变体：宫保虾球"） |
| | change_summary | 派生区（变更说明） |
| **nutrition_info** | serving_size | 营养区（"每份200g"） |
| | serving_unit | 营养区（"g"） |
| | calories | 营养区（"320kcal"） |
| | protein | 营养区（"28g"） |
| | fat | 营养区（"18g"） |
| | carbs | 营养区（"20g"） |
| | fiber | 营养区（"2g"） |
| | sodium | 营养区（"800mg"） |

### HTML 生成规则

**文件名格式**：
```
食谱详情_{菜名}_{时间戳}.html
例：食谱详情_宫保虾球_20260516_120000.html
```

**存储路径**：`/home/feather/.openclaw/media/qqbot/`

**页面结构**：

```
【顶部固定区】
  菜名（大标题）
  一句话描述（description）
  [照片区] 成品图 or 占位emoji

【基本信息区】（4格横排）
  难度 | 总时间 | 份量 | 状态

【分类标签区】（横向pill排列）
  川菜 | 中国-四川 | 中国 | 春/秋 | 炒 | 辣/麻 | 荤菜 | 中/晚

【营养信息区】（表格，右上角可折叠）
  热量320kcal | 蛋白质28g | 脂肪18g | 碳水20g | 纤维2g | 钠800mg
  （显示每份XXXg的数值）

【步骤区】（纵向卡片流，每步一个卡片）
  步骤N（序号）| 时长 | 火候 | 温度
  动作描述（大字）
  预期效果（斜体）
  投入食材（来自 step_ingredients）
  技法（来自 step_techniques）
  步骤内小贴士（来自 tips.step_id=N）

【食材清单区】（表格，可折叠）
  序号 | 食材名 | 用量 | 分类 | 可选/替代

【小贴士区】（优先级排序，带分类标签）
  [刀工-1] 开背去虾线更入味
  [火候-1] 油温不够会吸油
  [采购-2] 选新鲜活虾

【背景知识区】（三段，可折叠）
  【起源】丁宝桢发明的故事...
  【历史】清代改良的经过...
  【文化】小荔枝口味型的意义...

【烹饪历史区】（时间线，可折叠）
  2026-05-15 第3次 评分4.5「虾很Q弹」
  2026-05-10 第2次 评分4.0「盐放多了」
  2026-05-01 第1次 评分4.2「成功」

【派生关系区】（树形，可折叠）
  宫保鸡丁（父）
    └── 宫保虾球（变体）：减少花生用量，增加虾

【来源信息区】
  来源：中餐厅节目
  链接：[URL]（可点击）

【底部引导】
  要开始做吗？说"开始做这道菜"进入做菜模式。
```

### 查看食谱示例输出（文字版）

```
菜名：宫保虾球
描述：川菜经典，虾球Q弹，酸甜微辣
难度：中等 | 总时间：25分钟 | 份量：2人份 | 状态：已做（3次，评分4.5）
来源：中餐厅节目 | 链接：https://example.com/recipe

分类标签：川菜 | 中国-四川 | 中国 | 春/秋 | 炒 | 辣/麻 | 荤菜 | 中/晚

营养信息（每份200g）：
热量320kcal | 蛋白质28g | 脂肪18g | 碳水20g | 纤维2g | 钠800mg

步骤：
第1步（10分钟）[小火] 温度：常温
  动作：虾去壳开背，用料酒和盐腌制10分钟
  预期：虾肉变红，去腥
  投入：虾 300g（开局加入）
  技法：腌制（用料酒去腥，关键：时间要够/料酒要适量）
  小贴士：[刀工] 开背时去虾线更入味

第2步（3分钟）[大火] 温度：180度
  动作：大火热油，虾下锅炸至变色捞出
  预期：虾肉变红，表面微焦
  投入：虾 300g（第2步加入）
  技法：油炸（高油温快速定型，关键：油温要高/炸制时间短）
  小贴士：[火候] 油温不够会导致虾吸油

...（后续步骤同理）

食材清单（共8种）：
1. 虾 300g | 海鲜 | 不可选
2. 花生 50g | 其他 | 可选（可用腰果代替）
3. 干辣椒 10g | 调料
4. 花椒 5g | 调料
...（完整列表）

小贴士：
[刀工-1] 开背时去虾线更入味
[火候-1] 油温不够会导致虾吸油
[采购-2] 选择新鲜活虾，口感更Q弹

背景故事：
【起源】宫保虾球源自川菜宫保鸡丁的变体，由山东人丁宝桢发明...
【历史】清代丁宝桢任四川总督时改良此菜...
【文化】代表川菜小荔枝口的经典味型...

烹饪历史：
2026-05-15 第3次 评分4.5「味道不错，虾很Q弹」
2026-05-10 第2次 评分4.0「盐放多了」

要开始做吗？说"开始做这道菜"进入做菜模式。
```

---

## 做菜模式

### 工作流

```
用户："开始做这道菜" / "做菜模式"
    ↓
【复用阶段】复用"查看食谱"已查询的数据（不再重复查库）
    ↓
【生成阶段】AI 将数据重组织为做菜模式 HTML
    ↓
【发送阶段】HTML 保存到媒体目录，通过 QQBot 发送
```

### 与查看食谱的分工

| | 查看食谱 | 做菜模式 |
|---|---|---|
| 数据来源 | 重新查库（15条命令） | 复用查看食谱已查数据 |
| 输出形式 | 信息展示 HTML | 可交互检查清单 HTML |
| 目的 | 了解菜的全部信息 | 辅助实际做菜过程 |

### HTML 生成规则（做菜模式）

**文件名格式**：
```
做菜模式_{菜名}_{时间戳}.html
例：做菜模式_宫保虾球_20260516_120000.html
```

**存储路径**：`/home/feather/.openclaw/media/qqbot/`

**页面结构**：

```
【顶部进度条】
  菜名 | 完成进度（0/X步）
  [进度条：已完成0步 / 共4步]

【厨具确认区】（所有厨具列出）
  □ 炒锅（锅）
  □ 漏勺
  （全部勾选后厨具区自动折叠）

【食材检查区】（按步骤分组，每组显示该步骤需要的食材）
  步骤1食材：
    □ 虾 300g
    □ 料酒 15ml
  步骤2食材：
    □ 虾 300g（继续使用）
    □ 油 适量

【步骤卡片区】（每步一个可折叠卡片）
  步骤1（10分钟）[小火]
  ════════════════════
  动作：虾去壳开背，用料酒和盐腌制10分钟
  预期：虾肉变红，去腥
  投入：虾 300g（开局加入）
  技法要点：腌制（时间要够/料酒要适量）
  步骤贴士：开背时去虾线更入味
  ──────────────────
  [✅ 完成此步]  ← 点击后此卡片变灰+划线

【完成引导区】（全部步骤完成后显示）
  🎉 恭喜完成！
  要记录这次做的情况吗？
  [去评分]

【步骤导航】
  [上一步] [下一步]（卡片间快速跳转）
```

**动态行为（纯 HTML + JS，无需后端）**：
- 食材复选框点击 → localStorage 记住状态，进度条更新
- 步骤完成按钮点击 → 卡片变灰+划线，进度条更新，localStorage 记住
- 折叠/展开步骤卡片
- 进度百分比自动计算
- 页面刷新后恢复之前状态

**交互细节**：
- 按钮尺寸≥44px（单手友好）
- 高对比度配色（强光可读）
- 已完成项变灰+划线+复选框打勾
- 进度条实时显示"已完成X步/共Y步"

---

## 查询逻辑（两模式共用）

1. 先通过菜名查 `recipes` 表获取 `recipe_id`
2. 用 `recipe_id` 查所有关联表
3. 做菜模式直接复用上述数据，不再查库
4. 如果某字段为空，显示为"未知"或"-"

---

## 命令参考

```bash
# 查看食谱详情（完整输出）
python scripts/recipe_manager.py show <菜名或ID>

# 分类
python scripts/category_manager.py list <recipe_id>
python scripts/season_manager.py list <recipe_id>
python scripts/cooking_method_manager.py list <recipe_id>
python scripts/flavor_manager.py list <recipe_id>
python scripts/diet_tag_manager.py list <recipe_id>
python scripts/meal_type_manager.py list <recipe_id>

# 炊具
python scripts/cookware_manager.py list <recipe_id>

# 食材
python scripts/ingredient_manager.py list <recipe_id>
python scripts/step_ingredient_manager.py list-by-ingredient <ingredient_id>

# 步骤
python scripts/step_manager.py list <recipe_id>
python scripts/technique_manager.py list-by-step <step_id>
python scripts/step_ingredient_manager.py list-by-step <step_id>

# 小贴士
python scripts/tip_manager.py list <recipe_id>

# 历史
python scripts/history_manager.py list <recipe_id>

# 背景
python scripts/background_manager.py get <recipe_id>

# 派生
python scripts/relation_manager.py list-parent <recipe_id>
python scripts/relation_manager.py list-child <recipe_id>

# 营养
python scripts/nutrition_manager.py get <recipe_id>
```

---

## 参考

- 分类参考：`references/categories.md`
- 命令行参考：`references/commands.md`
- 表结构：`references/database_schema.md`