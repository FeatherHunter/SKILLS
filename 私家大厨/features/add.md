# 录入食谱

> 路由：SKILL.md 用例1 → features/add.md
>
> **v3 阶段(L1+L2+L3)变更**:
> - L1:所有业务字段 NOT NULL 兜底(占位符/0 值会被拒)
> - L2:validators 占位符黑名单(13 个)+ 0 值白名单(7 个字段)+ 1:1 必录校验
> - L2:tips 表缺 step/ingredient 时**警告但允许写入**(CLI 提示 AI 询问用户)
> - L3:数据导入统一走 `import_orchestrator.py`(单入口,事务包裹)
> - L3:CLI 默认 JSON 三段式输出,加 `--human` 走人类友好

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

> **v4.0 缺字段拒绝制(2026-08-09 用户拍板):不允许 `null`,也不允许空字符串。**

如果某字段无法从输入中识别,AI **必须问用户补齐**;补齐不了就如实汇报缺失,不录入没有意义的菜谱。

**示例**：
- 难度：无法从图片判断难度 → AI 根据步骤复杂度推测,并作为「AI 推测」字段在表单中标色,用户可改
- 照片：没有照片 → AI 必须问用户,用户显式确认后才可用占位图并注明(非系统自动填)
- 其他字段：缺失 → 校验拒绝,缺失清单一次列全,AI 逐项问用户补齐后重新校验

---

## 交互流程（v4.0 · 三态采集表单 · 08 采集+回执）

> **录入的确认环节一律走三态采集表单(G2 决策)**,不再用纯文本确认。渲染器:`scripts/render_add.py`。

```
用户：[发送图片/MD文件/文字描述/说"用表单方式录入"]

AI：解析信息 → 构造采集 payload（fields 三态标注 + payload 完整菜谱）
    → 调 render_add.py collect 生成表单 HTML → 双通道(文字一句话 + HTML)

AI 文字一句话示例："我解析到了这道菜的完整信息,表单已生成:
    正常字段(AI 已确认) / 橙色标注(AI 推测) / 红色框(缺失,需你补充)。"

三态标注规则(G2)：
  1. AI 确认字段    → state=confirmed（100% 准确,正常样式）
  2. AI 推测字段    → state=guessed（底色标注 + 「AI 推测」角标,用户可改）
  3. 缺失字段       → state=missing（红色框 + 「待补充」,必须用户补充）

用户动作：
  - 表单里直接编辑/补全缺失字段
  - 缺失未补全时「确认写入」按钮置灰禁用（系统拦,不带缺口入库）
  - 补全后点「确认写入」→ 复制 prompt（含补全后的完整菜谱 JSON）发给 AI
  - 或点「复制数据」把 5 段 JSON 带走

AI 收确认 prompt → 构造完整 JSON → 校验（缺失清单一次列全,无 null/空串）
    → 调 import_orchestrator.py <json_file> 写库
    → 调 render_add.py receipt 生成回执(成功:结果+diff+撤销 / 失败:原因+修正重试)
    → 双通道交付
```

**payload 构造要点**(render_add.py collect 入参):
- `fields[]`:每个可编辑字段一条 `{path, label, value, state, note}`,path 为 JSON 路径(如 `ingredients[0].quantity_text`)
- `payload`:AI 构造的完整菜谱 JSON(用户补全后回填)
- `scene_id/command_cn/wake_word/occurred_at/target`:08 头部契约,来自场景资产

---

## 校验失败处理（全字段必填 · v4.0 缺字段拒绝制）

> 配合 SKILL.md "全字段必填(硬规则)" 使用。
> **不允许 null / 空字符串(2026-08-09 用户拍板);缺字段 = 拒绝 + 缺失清单一次列全,AI 问用户补齐。**

### 校验失败时，AI 收到这样的错误

```json
{
  "status": "error",
  "errors": [
    {
      "type": "missing_field",
      "field": "photo_url (照片URL)",
      "path": "photo_url",
      "current_value": "(缺失)",
      "expected": "必填,不允许 null / 空字符串",
      "hint": "字段 photo_url 不允许为 null 或空字符串(v4.0 缺字段拒绝制);请补真实值后重新校验"
    },
    {
      "type": "missing_field",
      "field": "ingredients[0].quantity_text (quantity_text)",
      "path": "ingredients[0].quantity_text",
      "current_value": "(空串)",
      "expected": "必填,不允许 null / 空字符串",
      "hint": "字段 ingredients[0].quantity_text 不允许为 null 或空字符串(v4.0 缺字段拒绝制);请补真实值后重新校验"
    }
  ],
  "suggested_user_question": "你手写本上没写:① photo_url (照片URL) ② ingredients[0].quantity_text (quantity_text)。能现场补一下吗?"
}
```

### AI 处理流程(必须遵循)

1. **不要直接补默认值** — 校验失败说明字段缺真实值,默认值 = 偷懒
2. **必须用 suggested_user_question 问用户** — 一次性问,不要拆成多个问题
3. **用户回答后,AI 重新构造 JSON** — 每个字段都要有真实值
4. **二次校验通过后,才调用导入** — `recipe_import.py import` / `import_orchestrator.py`
5. **如果用户说"没有/不知道"** — 如实汇报,不录入没有意义的菜谱;无照片时用户显式确认后才可用占位图并注明
6. **无真实值的字段一律不允许 null / 空串入库** — 宁可拒绝重来,不让带缺口的菜进库

### 用户问题模板(AI 可微调)

- **多字段缺失时**:用一句口语化的话把所有字段打包问
- **示例**:"你手写本上没写:① 菜的描述 ② 烹饪贴士 ③ 技法 ④ 起源故事 ⑤ 烹饪历史 ⑥ 照片。能现场补一下吗?实在没有,我们这单就暂时录不了。"
- **避免**:每个字段单独问(会烦死用户)

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

## 同名食谱冲突处理

当录入的菜名已存在时，脚本会返回JSON格式的冲突信息：

```json
{
  "conflict": true,
  "message": "发现同名食谱「宫保虾球」",
  "existing_recipe": {
    "id": "8f3b435b-...",
    "name": "宫保虾球",
    "status": "已做",
    "cook_count": 3,
    "avg_rating": 4.5
  },
  "choices": [
    {"action": "view", "description": "查看现有食谱详情"},
    {"action": "derive", "description": "基于现有食谱创建新变体（需提供 --new_name）"},
    {"action": "update", "description": "更新现有食谱内容"},
    {"action": "cancel", "description": "放弃本次录入"}
  ],
  "usage": "再次调用时添加 --choice <action> 参数"
}
```

**AI处理流程**：

```
第一次调用（检测冲突）：
python scripts/recipe_manager.py add "宫保虾球"

→ 返回冲突JSON

AI根据用户意图选择：

1. 查看现有食谱：
   python scripts/recipe_manager.py add "宫保虾球" --choice view

2. 派生新变体：
   python scripts/recipe_manager.py add "宫保虾球" --choice derive --new_name "宫保虾球（改良版）"

3. 更新现有食谱：
   python scripts/recipe_manager.py add "宫保虾球" --choice update

4. 取消录入：
   python scripts/recipe_manager.py add "宫保虾球" --choice cancel
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

---

## 录入方式选择

AI收到录入请求时，按以下规则选择方式：

| 场景 | 方式 | 原因 |
|------|------|------|
| 用户说"导入食谱" | JSON导入 | 用户明确指定 |
| 用户发图片/MD文件 | 传统CLI | AI逐步解析，不确定的字段边问边填 |
| 用户提供了完整信息（食材+步骤都有） | JSON导入 | 信息完整，一步到位更高效 |
| 用户只说了菜名或信息不全 | 传统CLI | 需要逐步追问，CLI支持单步操作 |

**判断标准**：用户提供的信息是否足够生成一个完整的JSON。如果够 → JSON导入；不够 → 传统CLI。

---

## JSON文件导入

> 一步完成食谱导入，避免多步CLI操作的错误。

### 完整流程

```
用户：[发送图片/MD文件/文字描述]
    ↓
AI解析信息，构造完整JSON
    ↓
保存为临时文件（如 recipe.json）
    ↓
调用校验脚本：python scripts/recipe_json_validate.py recipe.json
    ↓
├─ 有错误 → AI根据报错修正JSON → 重新校验
├─ 有警告 → AI判断是否需要修正
└─ 全通过 → 进入导入
    ↓
调用导入脚本：python scripts/recipe_import.py import recipe.json
    ↓
返回导入结果
```

### 校验脚本

```bash
python scripts/recipe_json_validate.py <json_file>
```

校验内容（v4.0 缺字段拒绝制）：
- **缺失清单**：null / 空字符串 / 字段缺失 → 一次列全拒绝（不允许 null、不允许空串）
- **步骤关联**：tips/techniques 的 step_sequence 必须指向存在的步骤
- **必填字段**：name、ingredients[].name、steps[].action 等全部字段必须为真实值
- **数据类型**：数值字段是否为数字、数组字段是否为数组
- **外键引用**：步骤引用的食材是否在ingredients中存在
- **枚举警告**：非标准值给出警告（不阻断）

### 参考

- JSON模板：`templates/recipe_template.json`
- 校验脚本：`scripts/recipe_json_validate.py`
- 导入脚本：`scripts/recipe_import.py`
- 命令文档：`references/commands.md`（JSON导入命令部分）

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

# 11. 添加烹饪历史（可选，首次做菜时记录）
python scripts/history_manager.py add "<ID>" \
  --cook_date 2026-05-15 \
  --rating 4.5 \
  --feedback "虾很Q弹，下次可以少放点盐"
```

---

## 录入后 Review 提示(AI 主动思考,非硬规则)

录完一份食谱后,在向用户报告"录入成功"之前,主动 review 一次 `steps[]`,识别需要补充 `tips[]` 的环节,这样日后用户用「做菜模式」时,模板会自动展示这些提示。

### 三大类值得加 tip 的场景

1. **切配粒度**:某步骤涉及切/片/块/丝/丁等刀工,且食材有特别讲究(五花肉切片不要太薄、葱切葱花 vs 葱段)→ 加 step 级 tip(scope=step,关联对应 step),承载"切配粒度建议"。

2. **火候控制**:某步骤涉及"小火煸""中火翻炒""大火收汁"等,且容易翻车 → 加 step 级 tip 说明"怎么判断火候对错"(听到滋滋声 / 看到边缘微焦 / 油烟大小)。

3. **隔夜准备**:某步骤涉及腌/泡/冷藏/解冻,且耗时 ≥ 1 小时 → 加 recipe 级 tip(scope=recipe,关联整道菜),提示用户"今晚腌一下,明天口感更好"。

### 写法建议

- step 级 tip:`scope=step`,关联 `step_id`,`category` 选"刀工"或"火候",`priority` 默认 1(重要)。
- recipe 级 tip:`scope=recipe`,不关联 `step_id`,`category` 选"保存"或"采购",`priority` 默认 1。
- content 写一句具体可执行的话,不要写"注意火候"这种空话,要写"听到锅中噼啪声变小,边缘微焦"。

### 注意事项

- 这是**方向引导,不是 checklist**。AI 根据具体食谱自由判断,不必每道菜都覆盖三类。
- 录入后,**先 show 一下结果**,让用户看 tips 是否合理,再写一次 update 修正。
- 不要为了凑数加 tip — 空泛的 tip 比没有 tip 更糟。
- 做菜模式 HTML 模板 `templates/cooking_mode.html` 会自动识别并展示这些 tip。

---

## 参考

- 分类参考：`references/categories.md`
- 命令行参考：`references/commands.md`
- 表结构：`references/database_schema.md`