# 修改食谱

> 触发词："改一下"、"更新"、"修改"、"第X步怎么改"、"换个做法"

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

---

## 修改类型

### 修改主信息
```
用户：把宫保虾球的难度改成困难
AI：确认修改：
- 菜名：宫保虾球
- 修改字段：难度 中等 → 困难

确认吗？说"对"执行。
```

### 修改步骤
```
用户：宫保虾球第3步改成小火炒
AI：当前第3步：
- 动作：锅留底油，大火爆香花椒和干辣椒
- 时长：1分钟

修改为：
- 动作：锅留底油，小火炒香花椒和干辣椒
- 时长：2分钟

确认吗？说"对"执行。
```

### 添加食材
```
用户：给宫保虾球加一个食材，姜丝10g
AI：确认添加：
- 食材：姜丝
- 用量：10g
- 单位：g

确认吗？说"对"执行。
```

### 调整步骤顺序
```
用户：宫保虾球第2步和第3步换一下
AI：当前顺序：
- 第2步：大火热油，虾下锅炸至变色捞出
- 第3步：锅留底油，大火爆香花椒和干辣椒

调换后：
- 第2步：锅留底油，大火爆香花椒和干辣椒
- 第3步：大火热油，虾下锅炸至变色捞出

确认吗？说"对"执行。
```

---

## 废弃食谱（discard）

整道食谱废弃（标记为已废弃），不再出现在列表和搜索中：

```
用户：不想要宫保虾球了
AI：确认废弃：
- 食谱：宫保虾球
- 状态：将变为「已废弃」

确认吗？说"对"执行。
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

【修改后】
- 难度：困难

确认吗？说"对"执行。
```

---

## 命令参考

```bash
# 更新食谱主信息
python scripts/recipe_manager.py update <recipe_id> --name "新菜名" --difficulty 困难

# 废弃食谱
python scripts/recipe_manager.py discard <recipe_id>

# 更新分类
python scripts/category_manager.py add-cuisine <recipe_id> --cuisine 川菜
python scripts/season_manager.py add <recipe_id> --season 夏

# 添加/更新食材
python scripts/ingredient_manager.py add <recipe_id> --name 姜 --quantity 10 --unit g
python scripts/ingredient_manager.py update <ingredient_id> --quantity 15

# 添加/更新步骤
python scripts/step_manager.py add <recipe_id> --sequence 4 --action "出锅前撒葱花"
python scripts/step_manager.py update <step_id> --action "新动作" --duration 5

# 关联食材到步骤
python scripts/step_ingredient_manager.py add --step_id <step_id> --ingredient_id <ingredient_id>

# 添加技法
python scripts/technique_manager.py add --step_id <step_id> --recipe_id <recipe_id> --technique_name 爆炒

# 添加小贴士
python scripts/tip_manager.py add <recipe_id> --step_id <step_id> --category 火候 --content "火候要控制好"
```

---

## 参考

- 分类参考：references/categories.md
- 命令行参考：references/commands.md
- 表结构：references/database_schema.md