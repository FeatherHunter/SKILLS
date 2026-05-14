# 私家大厨 🍳

> 版本：v1.0
> 创建时间：2026-05-13
> 设计者：成真

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## 🤝 私家大厨帮助

> 用户说"私家大厨 help"时显示本帮助

---

## 食谱管理

## 添加食谱
"添加食谱 [菜名]" / "新建一个食谱"

## 查看食谱
"查看 [菜名]" / "食谱详情 [菜名]"

## 列出食谱
"列出所有食谱" / "有哪些食谱"

## 更新食谱
"更新 [菜名] 的难度" / "修改 [菜名] 的时间"

## 删除食谱
"删除 [菜名]"

## 搜索食谱
"找一下有蒜蓉的菜" / "搜索排骨" / "哪些川菜可以做"

---

## 步骤与材料

## 查看步骤
"[菜名] 怎么做" / "步骤是什么"

## 查看食材
"[菜名] 需要什么材料" / "食材清单"

## 添加步骤
"[菜名] 第1步是..."

## 添加食材
"[菜名] 要加 100g 排骨"

---

## 技法学习

## 查看技法
"爆炒怎么做" / "滑炒是什么"

## 列出技法
"有哪些烹饪技法"

---

## 小贴士

## 添加小贴士
"给 [菜名] 加个小贴士"

## 查看小贴士
"[菜名] 有什么小技巧"

---

## 背景知识

## 查看背景
"[菜名] 有什么故事" / "来历是什么"

---

## 烹饪历史

## 记录做菜
"做了 [菜名] 评分4.5" / "记录做了 [菜名]"

## 查看历史
"做了几次 [菜名]" / "[菜名] 历史"

## 复盘改进
"最近做 [菜名] 怎么样"

---

## 采购清单

## 生成清单
"生成采购清单 [菜名1],[菜名2]" / "下周想吃 [菜名]，要买什么"

## 查看库存
"冰箱里有什么" / "库存查询"

---

## 热量查询

## 查看热量
"[菜名] 有多少卡" / "热量多少"

---

## 智能推荐

## 按场景推荐
"今天有客人，推荐个硬菜" / "做个宴客菜"

## 按时间推荐
"30分钟能搞定的菜" / "快手菜推荐"

## 按口味推荐
"想吃辣的" / "来个麻辣的"

## 按季节推荐
"夏天吃什么好" / "冬季暖身菜"

---

## 炊具管理

## 添加炊具
"我买了砂锅" / "新炊具 电饭煲"

## 查看炊具
"有哪些炊具" / "炊具列表"

---

## 健康检查

## 数据检查
"私家大厨 健康检查" / "lint" / "检查数据"

---

# 私家大厨 - 食谱数据库技能 v1.0

## 功能概述

- **食谱管理**：新增/编辑/删除/搜索食谱（11个manager脚本对应11张表）
- **智能推荐**：按场景/时间/口味/季节/预算推荐菜谱
- **烹饪追踪**：历史日志、评分反馈、改进跟踪
- **采购清单**：勾选菜单 → 自动汇总食材 → 按超市分类
- **热量追踪**：每道菜热量明细、营养素分析
- **技法学习**：中国烹饪技法详解、专项训练
- **小贴士**：采购/刀工/火候/调味/装盘/设备/保存技巧

## 数据库结构（11张表，11个manager脚本）

```
chef_data.db
├── recipes                   # 食谱主表 ← recipe_manager.py
├── recipe_locations          # 地区与分类 ← location_manager.py
├── ingredients               # 食材清单 ← ingredient_manager.py
├── ingredient_preparations   # 食材处理 ← prep_manager.py
├── cooking_steps             # 烹饪步骤 ← step_manager.py
├── step_techniques           # 技法详解 ← technique_manager.py
├── tips                      # 小贴士 ← tip_manager.py
├── background_knowledge      # 背景知识 ← background_manager.py
├── nutrition_info            # 热量营养 ← nutrition_manager.py
├── recipe_history            # 烹饪历史 ← history_manager.py
└── beverage_pairings        # 饮品搭配 ← beverage_manager.py
```

另有2张独立表（无专属manager）：cookware / recipe_collections

## 命令行用法

### 初始化数据库
```bash
python scripts/init_db.py
```

### 食谱管理
```bash
# 添加食谱
python scripts/recipe_manager.py add "蒜蓉蒸排骨" --time 60 --difficulty 中等

# 查看食谱
python scripts/recipe_manager.py show "蒜蓉蒸排骨"

# 列表
python scripts/recipe_manager.py list --cuisine 川菜

# 搜索
python scripts/recipe_manager.py search "排骨"
```

### 步骤管理
```bash
# 添加步骤
python scripts/step_manager.py add "蒜蓉蒸排骨" --step 1 --action "排骨切块，用面粉搓揉清洗" --duration 10

# 查看步骤
python scripts/step_manager.py list "蒜蓉蒸排骨"

# 搜索步骤（含关键词的步骤）
python scripts/step_manager.py search "大火爆香"
```

### 食材管理
```bash
# 添加食材
python scripts/ingredient_manager.py add "蒜蓉蒸排骨" --name 排骨 --quantity 500 --unit g

# 列表
python scripts/ingredient_manager.py list "蒜蓉蒸排骨"
```

### 小贴士
```bash
# 添加小贴士
python scripts/tip_manager.py add "蒜蓉蒸排骨" --category 火候控制 --content "蒸的时候火候不要太大，否则排骨变硬"

# 列表
python scripts/tip_manager.py list "蒜蓉蒸排骨"
```

### 烹饪历史
```bash
# 记录做菜
python scripts/history_manager.py add "蒜蓉蒸排骨" --rating 4.5 --note "这次蒜多了"

# 查看历史
python scripts/history_manager.py list "蒜蓉蒸排骨"
```

### 采购清单

生成采购清单需要手动汇总 ingredients 表数据，或通过 AI 辅助计算。

### 搜索
```bash
# 按食材搜索（ingredient_manager + grep）
# 按菜系搜索（location_manager query_by_cuisine）
python scripts/location_manager.py query-by-cuisine 川菜

# 按口味搜索（location_manager query_by_flavor）
python scripts/location_manager.py query-by-flavor 麻辣

# 按季节搜索（location_manager query_by_season）
python scripts/location_manager.py query-by-season 夏季

# 按场合搜索（location_manager query_by_occasion）
python scripts/location_manager.py query-by-occasion 宴客

# 数据检查（recipe_manager lint）
python scripts/recipe_manager.py lint
```

### 数据导入

暂无独立导入脚本。如需导入可参考 `references/analysis_api.md` 中的分析流程。

### 健康检查
```bash
python scripts/recipe_manager.py lint
```

## AI 触发指引

### 触发场景：用户提到"私家大厨"、"食谱"、"做菜"

触发词：
- "私家大厨"
- "食谱"、"菜谱"
- "做菜"、"做饭"
- "这个菜怎么做"
- "想吃..."

**完整流程**：

#### Step 1：解析用户意图
- 添加食谱 → recipe_manager
- 查看食谱 → recipe_manager
- 搜索食谱 → search
- 记录做菜 → history_manager
- 生成采购清单 → shopping_list

#### Step 2：执行CLI命令
根据意图选择对应脚本

#### Step 3：返回结果
格式化输出返回用户

### 关键约束
- 所有数据操作必须通过CLI
- 禁止直连数据库
- 搜索结果要格式化展示

---

## 联动说明

本技能可能与以下技能产生联动：

| 技能 | 可能的联动场景 |
|------|--------------|
| 卡路里 | 记录饮食时可同步记录菜品热量 |
| 饼干记账 | 记录采购食材时可同步记录支出金额 |
| 居家管家 | 推荐菜谱时可参考现有炊具 |

**处理原则**：在处理用户请求时，主动思考是否需要与上述技能联动。如判断需要联动，先完成主技能操作，再询问用户是否需要触发关联技能的相应功能。不要强制联动，尊重用户意图。

---

## Lint 检查（数据健康检查）

**触发词**：`"私家大厨 健康检查"`、`"私家大厨 lint"`、`"检查数据"`

### 检查项

**1. 数据完整性检查**
- 食谱是否有步骤
- 步骤是否有食材
- 关键步骤是否有小贴士

**2. 数据一致性检查**
- 食材用量是否合理
- 步骤顺序是否正确

**3. 热量数据检查**
- 是否所有食谱都有热量
- 热量值是否合理

**4. 烹饪历史检查**
- 长期未做的食谱（超过30天）
- 评分下降的食谱

### 处理原则
- 发现问题后列出清单，让用户确认是否需要处理
- 不要自动修改，只能建议
- 用户说"检查一下"时执行，不主动触发

---

## 🔗 相关路径

- 技能本体：`D:\2Study\StudyNotes\SKILLS\私家大厨\`
- 数据库：`.db/chef_data.db`
- 数据库设计：`D:\2Study\StudyNotes\2025\.2025个人\大厨的美食城堡🥗\大厨技能数据库设计.md`
- 现有食谱备份：`D:\2Study\StudyNotes\2024\私家大厨\`
- 2025食谱目录：`D:\2Study\StudyNotes\2025\.2025个人\大厨的美食城堡🥗\食谱\`

---

**私家大厨，让家更有家的味道** 🍳