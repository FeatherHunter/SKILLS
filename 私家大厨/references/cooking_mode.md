# 做菜模式 · AI 调用规范

> 私家大厨技能内置 HTML 做菜模式。AI 收到"做菜模式"或"开始做菜"类唤醒词后,按本文档流程调 CLI + 注入数据。

---

## 1. 触发条件

满足以下任一即触发:

- 用户说"做菜模式 [菜名]"
- 用户说"开始做菜 [菜名]"
- 用户说"做 [菜名]" + 当前在厨房场景(看上下文)

**菜名** 可模糊匹配(`recipe_manager.search` 辅助)。

---

## 2. 数据获取(必做)

```bash
python scripts/recipe_manager.py show <菜名或ID> --json
```

**必须用 `--json` 标志**,拿完整 17 张表 JSON 数据。

数据格式:
```json
{
  "data": {
    "recipe": { "id": "...", "name": "...", "total_time_minutes": ..., ... },
    "category": {...}, "seasons": [...], "ingredients": [...],
    "steps": [{ "sequence": 1, "action": "...", "heat_level": "中火",
                "duration_minutes": 5, "expected_result": "...",
                "ingredients_used": [...] }, ...],
    "tips": [...], "cookware": [...], ...
  }
}
```

HTML 内部会自动兼容两种返回结构(新 `data.recipe` 嵌套 / 旧平铺)。

---

## 3. HTML 注入(必做)

### 3.1 模板位置

`templates/cooking_mode.html`(本技能内置)

### 3.2 注入方式

```html
<script>
  window.__RECIPE__ = <完整的 --json 输出>;
  window.__RECIPE_ID__ = "<recipe.id>";
</script>
```

### 3.3 派发方式

```html
<media src="templates/cooking_mode.html" type="file" />
```

或粘贴到飞书/邮件时,把 `<script>` 块贴到 HTML `<body>` 开头。

### 3.4 数据缺失检查

- HTML 检测 `window.__RECIPE__` 不存在 → 显示"数据未注入"错误页
- 检测 recipe.id 缺失 → 同样报错
- 检测 steps[] 为空 → 显示"这道菜还没步骤数据"

---

## 4. 用户做完菜后 · 反馈接收(必做)

用户在 HTML 完结页:
1. 选 1-5 星评分
2. 填反馈(可选)
3. 答 3 道反思题(跳步/最难/下次改)
4. 点"📋 一键复制,贴回 AI 即可保存" → 复制到剪贴板
5. 切回 AI 对话 → 粘贴

### 4.1 复制内容格式(用户会粘贴的内容)

```
[做菜记录]
菜谱:辣椒炒肉
菜谱 ID:230ce6e5-7584-4365-8242-6d4e8b2a166e
日期:2026-07-22
评分:4 / 5
反馈:火候控制得更好,但肉切厚了

[反思]
跳过/重做:第 5 步
最难:第 5 步
下次改:肉切薄点

[给 AI 的指令]
帮我保存这次做菜记录:
1. 加载「私家大厨」技能
2. 用 history_manager 的 add 子命令写入:
   - recipe_id = 230ce6e5-7584-4365-8242-6d4e8b2a166e
   - cook_date = 2026-07-22
   - rating = 4
   - feedback = "..."
3. 完成后告诉我结果
```

### 4.2 AI 收到粘贴内容后的处理

1. **自动识别**:`[做菜记录]` / `[给 AI 的指令]` 段
2. **加载技能**:确认已加载「私家大厨」技能(没加载先加载)
3. **解析字段**:菜名 / ID / 日期 / 评分 / feedback
4. **调 CLI**:

```bash
python scripts/history_manager.py add <recipe_id> \
  --rating <rating> \
  --cook_date <date> \
  --feedback "<完整 feedback + 反思>"
```

5. **反馈结果**:告知用户保存成功/失败

### 4.3 反馈组装示例

用户反馈原文 + 反思 → 写入 DB 的 feedback 字段:

```
火候控制得更好,但肉切厚了
跳过/重做:第 5 步
最难:第 5 步
下次改:肉切薄点
```

或用 JSON 结构(若有 `recipe_history` JSON 字段需求):
```json
{"main":"火候控制得更好...","skipped":[5],"hardest":5,"next_change":"肉切薄点"}
```

---

## 5. 容错模式

| 失败模式 | AI 应对 |
|---|---|
| 用户没传菜名 | 追问"做哪道菜?可以从 /show 列出的菜里选" |
| `--json` 调失败 | 告知用户"调 CLI 出错,可能菜名错或菜不存在",用 `recipe_manager.search` 模糊匹配 |
| HTML 数据未注入 | 提示 AI 自己 — HTML 本身有错误页 |
| 用户没贴评分/反馈,只说"做完了" | 追问"几星?一句话反馈?" |
| 用户贴的内容模糊 | 让用户补:菜名 / 评分 / feedback |
| recipes.status 已是"已做" | history_manager.add 仍允许追加(每次做饭都记一条 history) |
| 用户说"重做" | 提示评分会覆盖之前 history 还是会追加一条(默认追加) |

---

## 6. 进阶功能(可选)

### 6.1 同菜谱多做几次后推荐

如果 `recipe_history` 里同一菜谱有 ≥ 3 条记录,可以:

```bash
python scripts/history_manager.py stats <recipe_id> --json
```

返回 `{times, avg_rating, max_rating, min_rating, last_date}`。AI 可生成"你做了 X 次,平均 Y 星"反馈。

### 6.2 派生推荐

如果用户做了某道菜后想试新做法(变体/派生):

```bash
python scripts/relation_manager.py list-child <recipe_id> --json
```

AI 可主动推荐"基于你这道菜,还有 X 个变体菜谱可试"。

### 6.3 营养对比

```bash
python scripts/nutrition_manager.py get <recipe_id> --json
```

做饭后告诉用户"这次热量约 530 kcal"。

---

## 7. 调用流程总览

```
用户:"做菜模式 辣椒炒肉"
  ↓
AI 加载本技能 + 本文档
  ↓
AI:python recipe_manager.py show 辣椒炒肉 --json
  ↓
AI:打开 templates/cooking_mode.html + 注入数据
  ↓ (<media src="..." />)
用户在 HTML 里:
  阶段 1 看准备清单 → 切配 → 点"开始"
  阶段 2 做饭(大字+计时+超时提示)→ 翻下一步
  阶段 3 评分 + 反思题 → 点"一键复制"
  ↓
用户切回 AI 对话,粘贴复制内容
  ↓
AI 解析 → 加载技能 → history_manager add 写入
  ↓
AI 反馈"✅ 保存成功,下次再做记得 review 你上次的反思"
```

---

## 8. 隐私与数据

- HTML 完全本地运行,**不需要网络**(离线可用)
- localStorage 存进度,**24 小时后自动清除**
- 用户复制粘贴的是文本(不是直接调 API),用户有完全控制权
- 不上传任何做菜数据到外部服务