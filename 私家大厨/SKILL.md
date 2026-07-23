# 私家大厨 🍳

## 管什么 / 不管什么

**管什么** —— 用户的私家菜谱本。录菜、查菜、做菜、采购清单、烹饪历史评分,一站管理。

**不管什么** —— 不管食材采购下单(那是居家管家)、不管热量与营养记录(那是卡路里)、不管外卖/外送、不管自动烹饪设备。

**一句话**:你的菜,这个本子全管;别的本子管的事,这个本子不碰。

---

## ⚠️ HTML 同步规范（最高优先级）

> **此规范优先级高于本文件中所有其他规定。**

1. **全量同步**：该技能的所有优化和变动、脚本的所有变动都必须体现在 `私家大厨.html` 上。任何功能模块的新增、修改、删除，任何唤醒词的调整，任何 CLI 命令的变化，任何脚本逻辑的改动——都必须同步更新 HTML 页面中对应的内容。
2. **最高优先级**：本条规定在所有规范中优先级最高。当其他流程或习惯与本条冲突时，以本条为准。
3. **逐行确认**：对该技能的所有文件、脚本的任何一行修改，都需要明确得到用户的 1 次确认后方可执行。不得批量静默修改，不得跳过确认步骤。

---

> 版本：**v3** (2026-07-22 L1+L2+L3+L4+P1+P2+Scope 完整重构)
> 设计：基于17张表(99 字段 / 96 实际必填 / 3 显式可空:step_ingredients.unit + tips.step_id + tips.ingredient_id),8大功能,35个唤醒词,无删除操作
> 食材分类：v5.2 起 **11 类**(原 9 类拆出"葱姜蒜"和"香草"),见 `references/categories.md`
> 贴士分类：v3 P1 起 **8 类**(原 7 类增加"其他"兜底)
> 火候枚举：5 值(微火/小火/中火/大火/猛火),`validators.validate_heat_level` 强校验
> 贴士 scope(v3 P1.5 决策 2):**`step` / `ingredient` / `recipe` 三选一** 必填,通过 `--scope <值>` 显式声明 tip 关联范围
> 5层架构改造：
> - v5.0 (2026-07-21) — 24/24 + 30/30 自检通过,见 `CHANGELOG.md` [5.1]
> - **v3 L1** (2026-07-22) — DB NOT NULL 兜底墙,`init_db.py` + `migrations/004_all_fields_not_null.sql`
> - **v3 L2** (2026-07-22) — validators 占位符黑名单 + 18 manager 改 db.py + orchestrator.py 新建
> - **v3 L3** (2026-07-22) — CLI 三段式统一 + `--human`/`--json` 开关 + orchestrator 完整迁移
> - **v3 L4** (2026-07-22) — 18 manager 函数体真迁 db.execute/query/transaction(`recipe_manager.export_json` 整体重构,4 处隐 bug 顺手修)
> - **v3 P1** (2026-07-22) — 6 真 CLI bug 修复 + L1 哲学回归(无默认值兜底)+ `step_ingredients.unit` 改 NOT NULL(`migration 005`) + tips 加 `--scope` 值格式 flag + 加 7 个 validators(cookware/relation/serving_unit/rating/positive_int/date_format/array_enum)
> - **v3 P2** (2026-07-22) — `L4_verify.py` 盲点修复(加正信号 + import 完整性)
> 详细变更见 `CHANGELOG.md`

---

## 唤醒词清单（35个）

> 全部为动词+名词格式，指令化，不追求自然。
> 总览词和细分词并列共存，互不冲突。

### A. 做菜模式（2个）

| 唤醒词 | 说明 |
|--------|------|
| 做菜模式 | 进入做菜模式，需配合菜名 |
| 开始做菜 | "开始做宫保虾球" |

### B. 查看食谱（5个）

> **机制说明**：「查看食材 / 步骤 / 营养 / 背景」这 4 个细分唤醒词,是**给 AI 中介的路由提示**——AI 调 `recipe_manager.py show <菜名>` 拿到全量输出后,从中**截取**对应 section 给用户。**不单独走 CLI**。
>
> 这避免"查看食材"和"查看食谱+食材"在用户感受上有差别,实际上**全量数据已包含**所有 section。

| 唤醒词 | 说明 |
|--------|------|
| 查看食谱 | 展示完整食谱（全部section） |
| 查看食材 | 仅展示食材清单(AI 截取) |
| 查看步骤 | 仅展示烹饪步骤(AI 截取) |
| 查看营养 | 仅展示营养信息(AI 截取) |
| 查看背景 | 仅展示背景知识(AI 截取) |

### C. 搜索筛选（10个）

| 唤醒词 | 说明 |
|--------|------|
| 搜索食谱 | 按菜名关键词搜索 |
| 筛选菜系 | "筛选川菜" |
| 筛选食材 | "筛选含虾的菜" |
| 筛选难度 | "筛选简单菜" |
| 筛选时间 | "筛选30分钟内的菜" |
| 筛选炊具 | "筛选用砂锅的菜" |
| 筛选口味 | "筛选辣的菜" |
| 筛选季节 | "筛选适合夏天的菜" |
| 筛选状态 | "筛选已做的菜" |
| 查看全部 | 列出所有食谱，无筛选条件 |

### D. 修改食谱（9个）

| 唤醒词 | 说明 |
|--------|------|
| 修改食谱 | 通用修改入口 |
| 修改步骤 | 改步骤内容/顺序 |
| 修改食材 | 改食材用量/添加食材 |
| 修改难度 | 改难度等级 |
| 修改份量 | 改份数 |
| 废弃食谱 | 标记为已废弃（只增不删） |
| 不想要 | 口语化入口，等价于「废弃食谱」 |
| 删掉 | 口语化入口，等价于「废弃食谱」 |
| 废弃 | 简写入口，等价于「废弃食谱」 |

### E. 烹饪历史（3个）

| 唤醒词 | 说明 |
|--------|------|
| 记录做菜 | 记录一次烹饪（评分+反馈） |
| 查看历史 | 查看某道菜的烹饪历史 |
| 查看统计 | 查看评分统计（均分/次数） |

### F. 采购清单（2个）

| 唤醒词 | 说明 |
|--------|------|
| 生成清单 | 生成采购清单 |
| 排除可选 | 生成不含可选食材的清单 |

### G. 录入食谱（2个）

| 唤醒词 | 说明 |
|--------|------|
| 录入食谱 | 录入新食谱（图片/文本/JSON） |
| 导入食谱 | JSON文件导入 |

### H. 派生关系（2个，v5.1 新增）

| 唤醒词 | 说明 |
|--------|------|
| 添加派生关系 | 标记一道菜基于另一道菜的变体（派生/变体/改良） |
| 查看派生关系 | 查看一道菜的所有父本/子本关系 |

---

## 依赖

- Python 3.x
- sqlite3（Python 内置）

## CLI 输出格式(5 层架构:AI 可解析)

> **L3 阶段新增**(2026-07-22)

| 工具 | 默认输出 | 加 `--json` | 加 `--human` |
|---|---|---|---|
| 18 个 `*_manager.py` | 中文友好文本 | JSON 三段式 `{status, data, message}` | (默认即人类) |
| `recipe_import.py import` | **JSON 三段式** | (默认即 JSON) | 中文友好 |
| `recipe_import.py validate` | JSON 三段式 | (默认) | 中文友好 |
| `import_orchestrator.py` | JSON 三段式 | (默认) | (暂未支持) |

**JSON 三段式示例**:
```json
{
  "status": "success",
  "data": {
    "recipe_id": "abc-123",
    "name": "测试菜",
    "child_ids": {
      "recipes": 1,
      "ingredients": 11,
      "cooking_steps": 6
    }
  },
  "message": "成功导入食谱「测试菜」(ID: abc-123...)"
}
```

**状态字段约定**:
- `success` ✅ 操作成功
- `error` ❌ 操作失败(有 `errors` 字段列明细)
- `warning` ⚠️ 操作成功但有警告(如 tips 缺字段,`tips_warnings` 字段列出)
- `dry_run` 🔍 校验通过但未写入

**导入入口统一** —— 所有数据导入都走 `import_orchestrator.py`:
```bash
python scripts/import_orchestrator.py <json_file> [--dry-run] [--json]
```

---

## 配置

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `CHEF_OUTPUT_DIR` | HTML 输出目录 | `D:/CookHub` |
| `CHEF_OUTPUT_DIR_PREFIX` | 本地源食谱图片命名空间前缀 | `chef://` |

## 一键安装

复制以下内容发送给 AI：

```
帮我初始化私家大厨技能：
1. 询问我 HTML 输出目录路径，然后帮我设置环境变量 CHEF_OUTPUT_DIR
2. 显示当前环境变量配置
3. 告诉我如何更改数据目录
```

---

## ⚠️ 操作规范（强制）

本技能所有数据操作必须通过 CLI，禁止直连数据库。

---

## AI使用规范（强制）

### 全字段必填（硬规则 · 无跳过通道）

> **录入食谱时,所有字段都必须有值或显式 null。AI 不得"字段不重要就跳过"。**

1. **JSON 必须包含所有字段** — 值可以是真实数据,也可以是 `null`(显式标记"AI 已确认无数据"),但字段本身不能缺失
2. **缺字段 = 校验失败** — `scripts/validators.py::validate_full_coverage()` 会一次性列出所有缺失字段,AI 收到后必须补齐
3. **null ≠ 跳过** — `null` 是 AI 主动确认"无数据",不是偷懒省略
4. **多个字段缺失时,一次性问用户** — 用一个问题把多个字段打包问,不要每个字段单独问(那太烦)
5. **错误信息含"字段名 + 当前值 + 期望值 + 怎么修"** — 遵守"可约束"特性,让 AI 知道怎么改
6. **早失败优于晚失败** — 在校验阶段直接拒,不要等到 SQL 报错
7. **无 --force / --skip-validation 通道** — AI 偷懒会立刻用上,设计上禁止

### L1 NOT NULL 设计哲学(v3 P1 用户拍板)

**L1 设计意图:DB NOT NULL 是故意拦截 AI 偷懒不传字段的。**

| 场景 | 错误做法 | 正确做法 |
|---|---|---|
| CLI add 缺必填字段 | AI 看不到字段 → DB 崩 stacktrace | CLI 友好报错(含字段名 + 当前值 + 期望值 + 怎么修)→ AI 拿错误信息问用户 |
| 缺字段时 | 给个"中火"/"适量"/"完成"默认值兜底(让 AI 跳过思考) | 让 AI 必须问用户拿到所有字段后再调 |
| 字段看似可推算(如 quantity_text) | 自动从 quantity+unit 拼接 | 必须显式提供,即使是冗余也要 AI 主动思考 |

**反例**(v3 P1 之前的 fix,被用户纠错):
- ❌ `step_manager.add` 没传 heat_level/temperature/expected_result 时默认 "中火/常温/完成"
- ❌ `ingredient_manager.add` 没传 substitute 时默认 "无替代品"
- ❌ `quantity_text` 自动从 quantity+unit 拼接

**正解**(v3 P1 重做):
- ✅ 缺字段 → 友好报错,AI 拿错误信息问用户,重试
- ✅ user 明确说 "用豆腐代替" → `--substitute "豆腐"`
- ✅ user 明确说 "无替代品" → `--substitute "无替代品"`(显式传,不是默认)

**适用范围**:所有 CLI add path(`ingredient_manager` / `step_manager` / `tip_manager` / `recipe_manager`),不仅限录入食谱;做饭路径不强制(读路径字段可推算)。

### tip scope 枚举(v3 P1.5 决策 2 · 方案 A+)

`tips` 表的 `step_id` 和 `ingredient_id` 故意保留可空 — L1 哲学允许"菜级 tip"。但 L1 NOT NULL 设计意图要求 AI **显式声明** 这条 tip 关联什么。

**`tip_manager.add` 必传 `--scope`**,枚举三选一,值直接跟字段语义挂钩 — AI 看到 `--scope recipe` 立刻明白"这条 tip 的 scope 是 recipe":

| `--scope` 值 | 含义 | 必须字段 |
|---|---|---|
| `step` | 此 tip 关联某个步骤 | `--step_id` |
| `ingredient` | 此 tip 关联某个食材 | `--ingredient_id` |
| `recipe` | 此 tip 是整道菜级(常识/保存等) | (都允许空) |

**validator 强制规则**(`scripts/validators.py::validate_tip_scope`):
- `scope='step'` 缺 `--step_id` → 友好报错
- `scope='ingredient'` 缺 `--ingredient_id` → 友好报错
- `scope` 非法值 → 报错列出合法值

**JSON 路径**(`import_orchestrator.py`):JSON tip 必须有 `"scope": "step|ingredient|recipe"` 字段。

**为什么选方案 A+**:0 schema 改动 + 值格式 flag 比 magic word(`--confirm-detached`)AI 一眼能懂 + DB schema 仍是 L1 一致(允许空)。

### validators 9 个校验函数(v3 P1.5 决策 3)

除原有占位符/tips 业务校验外,v3 P1.5 新增 7 个 enum/范围/格式校验函数(`scripts/validators.py`):

| 函数 | 校验目标 | 合法值/范围 |
|---|---|---|
| `validate_cookware_category` | `cookware.category` | 锅/炉/刀/其他 |
| `validate_relation_type` | `recipe_relations.relation_type` | 派生/变体/改良 |
| `validate_serving_unit` | `nutrition_info.serving_unit` | g/ml/份/杯 |
| `validate_rating_range` | `recipe_history.rating` | 0-5(含小数) |
| `validate_positive_int` | `recipe_history.cook_sequence` 等 | 正整数 > 0 |
| `validate_date_format` | `recipe_history.cook_date` | YYYY-MM-DD |
| `validate_array_enum` | 5 张 tag array | 各自 enum 值 |

**集成方式**:CLI `*_manager.py::add()` 在 INSERT 前调用,JSON 路径 `validate_recipe_for_import()` 调用。

### step_ingredients.unit NOT NULL(v3 P1.5 决策 1)

L1 阶段 `migrations/004_all_fields_not_null.sql` 漏设 `unit` NOT NULL,12 行数据实测全有值但仍有 schema 风险。`migrations/005_step_ingredients_unit_not_null.sql` 用 SQLite recreate table 模式迁移:

1. `CREATE TABLE step_ingredients_new (... unit TEXT NOT NULL ...)`
2. `INSERT INTO step_ingredients_new SELECT * FROM step_ingredients WHERE unit IS NOT NULL`
3. `DROP TABLE step_ingredients` + `RENAME`
4. 重建索引

**对应 CLI 改动**:`step_ingredient_manager.add` 加 friendly 报错(unit 缺/缺 quantity_used/introduced_at),`recipe_import.add_step_ingredients` 用 `name_unit_map`(从 ingredients.unit 兜底)。

### 字段推算边界(AI 何时推算,何时问用户)

> **按"5 层架构"+ 6 大特性"可约束"原则。AI 不知道什么时候该推算、什么时候该问,SKILL 给出明确边界。**

| 分类 | 典型字段 | AI 行为 |
|---|---|---|
| 🔴 **必问用户** | 用户专属(口味偏好 / 来源 / 食材品牌 / 这菜给谁吃) | 用 `validators.suggested_user_question()` 一次性打包问 |
| 🟡 **必推算** | `diet_tags` 从 nutrition 推 / `total_time` 从步骤求和 / `cooking_methods` 从步骤动作推 | AI 主动算,过 validators 校验 |
| 🟢 **可补常识** | `tips` / `techniques` / `background.origin_story` / 经典菜起源 | AI 主动补常识,过 validators 校验(标"AI 补"在内容里) |
| ⚪ **可显式 null** | 用户说"没/不知道/不重要" / 通用字段无数据 | AI 标 `null`,不省略字段 |

**原则**:
- 录入时**不主动问**用户"这道菜 X 字段填什么"——除非是用户专属信息
- AI 推算/补常识后**仍然过 validators 校验**(避免推算出"香"这种枚举外的值)
- 用户说"我也不知道" → AI 用 `null`,不是省略字段

### 调用任何manager前，必须：

1. **展示完整参数示例** — 让用户知道这条命令会用哪些参数
2. **对未提供字段进行合理推测** — 基于菜系特点/常见值/烹饪逻辑
3. **推测不出时询问用户** — 不能留空不填

### 字段推测规则（仅录入时使用）

> 详见 `features/add.md` — 仅在录入食谱时调用，查看/做菜模式不需要此规则。

### HTML 生成强制（v5.0 新增，v5.2 强化）

**「查看食谱」** AI 收到时**必须自动**按以下 2 步走，**禁止只跑第 1 步**：

```bash
# 第 1 步:展示文本(必跑)
python scripts/recipe_manager.py show <菜名或ID>

# 第 2 步:同步 HTML(必跑,紧跟第 1 步)
python scripts/recipe_render.py render <菜名或ID>
```

**4 条执行规则**:

1. **两步必跑** —— 收到"查看食谱 X"时,**自动**依次跑 show + render,不要等用户追问
2. **HTML 必发** —— render 成功后,**用 `<media>` 标签**把生成的 HTML 文件**推给用户**;只告诉路径不算交付
3. **失败降级** —— render 失败时静默降级,只 stderr 一行"HTML 同步跳过:{原因}",show 文本照常展示
4. **不调 render 也行** 的例外 —— 同一会话内刚跑过 render(<5 分钟)且没改过菜谱,可跳过第 2 步直接发旧 HTML
5. **HTML 文件命名固定** —— 三类 HTML 正式交付必须按统一命名表执行,禁止把 `recipe_view_辣椒炒肉_current.html`、`preview.html`、`test.html`、`current.html`、`final.html` 这类临时文件名作为正式交付

**HTML 统一命名表**:

| 类型 | 输出目录 | 文件名格式 | 示例 |
|---|---|---|---|
| 查看食谱 | `$CHEF_OUTPUT_DIR/recipes/` | `<recipe_slug>.html` | `辣椒炒肉.html` |
| 做菜模式 | `$CHEF_OUTPUT_DIR/cooking/` | `做菜模式_<recipe_slug>_<YYYYMMDD_HHMMSS>.html` | `做菜模式_辣椒炒肉_20260723_183000.html` |
| 采购清单 | `$CHEF_OUTPUT_DIR/shopping/` | `采购清单_<recipe_slug_or_joined_slugs>_<YYYYMMDD_HHMMSS>.html` | `采购清单_辣椒炒肉_20260723_183000.html` |

**禁止事项**:
- 自行拼接 HTML 字符串
- 调用 taste-skill / ui-ux-pro-max-skill(已废弃,统一由模板服务)
- 内联 CSS / JS(已统一在 `templates/recipe_view.html`)
- 只告诉用户 HTML 路径而不发文件(违反"必发"规则)

**「做菜模式」** 收到时必须调用 `python scripts/cooking_render.py render <菜名或ID>` 生成正式 HTML;禁止 AI 手动复制模板再临时命名。`cooking_render.py` 会自动 show --json、注入 `templates/cooking_mode.html`、输出 `$CHEF_OUTPUT_DIR/cooking/做菜模式_<recipe_slug>_<YYYYMMDD_HHMMSS>.html`。做饭页右侧"剩余约 N 分钟"必须按 `references/cooking_mode.md` 的剩余时间规则计算:当前步骤显示剩余分钟 + 后续所有步骤计划分钟之和;暂停保持、重做重置、归零/超时时当前步骤最低按计划时长显示。

### 采购清单 HTML 强制（v5.2 新增）

**「生成清单 / 排除可选」** AI 收到时**必须自动**按以下 2 步走：

```bash
# 第 1 步:拿数据(必跑,可省略文本直接给 HTML)
python scripts/shopping_manager.py generate <recipe_id1>[,<recipe_id2>,...]

# 第 2 步:渲染 HTML(必跑)
python scripts/shopping_render.py render <recipe_id1>[,<recipe_id2>,...]
```

**3 条执行规则**:

1. **跨食谱合并自动跑** —— 用户说"宫保虾球和辣炒虾球的采购清单",AI **自动解析**所有菜名,一次性调 generate + render(逗号分隔)
2. **HTML 必发** —— render 成功后,**用 `<media>` 标签**推给用户(同查看食谱规则)
3. **失败降级** —— render 失败时静默降级,JSON 数据照常展示

**features/shopping.md** 里 14 项 HTML 要求已由 `templates/shopping_view.html` 实现,AI 无需自写 HTML。

---

## 路由算法（核心）

### 匹配流程

```
用户输入
    ↓
第1步：唤醒词识别
    按 A>B>C>D>E>F>G 优先级，扫描唤醒词（动词+名词格式）
    命中即确定意图，不再往下匹配
    同优先级下，选最长匹配（"查看食材"优先于"查看食谱"）
    ↓
第2步：菜名/条件提取
    根据唤醒词在输入中的位置，按以下规则提取：

    规则A：唤醒词在开头
        "开始做宫保虾球" → 取唤醒词后面的文字 → "宫保虾球"
        "查看食材宫保虾球" → 取唤醒词后面的文字 → "宫保虾球"
        "筛选川菜" → 取唤醒词后面的文字 → "川菜"（筛选条件）

    规则B：唤醒词在末尾
        "宫保虾球查看食谱" → 取唤醒词前面的文字 → "宫保虾球"

    规则C：唤醒词在中间
        "宫保虾球修改步骤" → 取唤醒词前面的文字 → "宫保虾球"

    清洗：提取后去掉首尾空格，去掉末尾的"的"、"了"、"吧"等语气词
    过滤：菜名必须 ≥2 个字符，且不能是"一个"、"一道"、"新菜"等泛指短语
    菜名缺失 → 追问用户（不能猜）
    ↓
第3步：功能分流
    唤醒词 + 菜名/条件 → 加载对应 features/*.md
    细分唤醒词（如"查看食材"）→ 告知 AI 只展示对应部分
    菜名缺失 → 追问用户（不能猜）
    ↓
第4步：兜底
    没有任何唤醒词命中 → 默认走 search.md（可能是纯菜名输入）
```

### 匹配规则

| # | 规则 | 说明 |
|---|------|------|
| R1 | 优先级排序 | A>B>C>D>E>F>G，高优先级命中直接分流 |
| R2 | 最长匹配 | 同优先级下，选唤醒词最长的；同长度时，细分词优先于总览词（"查看食材"优先于"查看食谱"，"修改步骤"优先于"修改食谱"） |
| R3 | 关键词独立 | 触发词是独立词，不是子串匹配 |
| R4 | 菜名提取 | 触发词在开头→取后面文字；触发词在末尾或中间→取前面文字。提取后清洗语气词，过滤泛指短语 |
| R5 | 兜底 search | 没有任何关键词命中 → 走 search.md |
| R6 | 追问确认 | 菜名提取失败（<2字符或为空）→ 追问用户 |
| R7 | 泛指过滤 | 菜名提取结果为"一个/一道/新菜/什么/哪些"等泛指短语时，视为无效菜名，追问用户 |
| R8 | 筛选条件提取 | "筛选XX"类唤醒词，XX后面的文字作为筛选条件，不作为菜名 |

---

## 路由表（35个唤醒词）

> 全部为动词+名词格式。总览词和细分词并列共存，由 R2（最长匹配）保证不冲突。

### A. 做菜模式 → `view.md`（功能二）

| # | 唤醒词 | 说明 |
|---|--------|------|
| 1 | 做菜模式 | 进入做菜模式，需配合菜名 |
| 2 | 开始做菜 | "开始做宫保虾球" |

---

### B. 查看食谱 → `view.md`

| # | 唤醒词 | 说明 |
|---|--------|------|
| 3 | 查看食谱 | 展示完整食谱（全部section），末尾问"要开始做吗？" |
| 4 | 查看食材 | 仅展示食材清单 |
| 5 | 查看步骤 | 仅展示烹饪步骤 |
| 6 | 查看营养 | 仅展示营养信息 |
| 7 | 查看背景 | 仅展示背景知识 |

---

### C. 搜索筛选 → `search.md`

| # | 唤醒词 | 说明 |
|---|--------|------|
| 8 | 搜索食谱 | 按菜名关键词搜索 |
| 9 | 筛选菜系 | "筛选川菜"，按菜系筛选 |
| 10 | 筛选食材 | "筛选含虾的菜"，按食材筛选 |
| 11 | 筛选难度 | "筛选简单菜"，按难度筛选 |
| 12 | 筛选时间 | "筛选30分钟内的菜"，按时间筛选 |
| 13 | 筛选炊具 | "筛选用砂锅的菜"，按炊具筛选 |
| 14 | 筛选口味 | "筛选辣的菜"，按口味筛选 |
| 15 | 筛选季节 | "筛选适合夏天的菜"，按季节筛选 |
| 16 | 筛选状态 | "筛选已做的菜"，按状态筛选 |
| 17 | 查看全部 | 列出所有食谱，无筛选条件 |

---

### D. 修改食谱 → `update.md`

| # | 唤醒词 | 说明 |
|---|--------|------|
| 18 | 修改食谱 | 通用修改入口，需配合菜名和具体修改内容 |
| 19 | 修改步骤 | 改步骤内容/顺序 |
| 20 | 修改食材 | 改食材用量/添加食材 |
| 21 | 修改难度 | 改难度等级 |
| 22 | 修改份量 | 改份数 |
| 23 | 废弃食谱 | 标记为已废弃（只增不删原则） |
| 24 | 不想要 | 口语化入口，等价于「废弃食谱」 |
| 25 | 删掉 | 口语化入口，等价于「废弃食谱」 |
| 26 | 废弃 | 简写入口，等价于「废弃食谱」 |

---

### H. 派生关系 → `relation.md`（v5.1 新增）

| # | 唤醒词 | 说明 |
|---|--------|------|
| 27 | 添加派生关系 | 标记一道菜基于另一道菜的变体（派生/变体/改良） |
| 28 | 查看派生关系 | 查看一道菜的所有父本/子本关系 |

---

### E. 烹饪历史 → `history.md`

| # | 唤醒词 | 说明 |
|---|--------|------|
| 24 | 记录做菜 | 记录一次烹饪（评分+反馈） |
| 25 | 查看历史 | 查看某道菜的烹饪历史 |
| 26 | 查看统计 | 查看评分统计（均分/次数） |

---

### F. 采购清单 → `shopping.md`

| # | 唤醒词 | 说明 |
|---|--------|------|
| 27 | 生成清单 | 生成采购清单，支持多菜名 |
| 28 | 排除可选 | 生成不含可选食材的清单 |

---

### G. 录入食谱 → `add.md`

| # | 唤醒词 | 说明 |
|---|--------|------|
| 29 | 录入食谱 | 录入新食谱（图片/文本解析，信息完整时走JSON导入） |
| 30 | 导入食谱 | JSON文件导入 |

---

## 菜名提取示例

| 用户输入 | 唤醒词 | 位置 | 提取菜名 | 路由 |
|---------|--------|------|---------|------|
| "开始做红酒慢炖牛腩" | 开始做菜 | 开头 | 红酒慢炖牛腩 | view.md（做菜模式） |
| "做菜模式宫保虾球" | 做菜模式 | 开头 | 宫保虾球 | view.md（做菜模式） |
| "查看食谱宫保虾球" | 查看食谱 | 开头 | 宫保虾球 | view.md（完整食谱） |
| "查看食材宫保虾球" | 查看食材 | 开头 | 宫保虾球 | view.md（仅食材） |
| "查看步骤宫保虾球" | 查看步骤 | 开头 | 宫保虾球 | view.md（仅步骤） |
| "查看营养宫保虾球" | 查看营养 | 开头 | 宫保虾球 | view.md（仅营养） |
| "查看背景宫保虾球" | 查看背景 | 开头 | 宫保虾球 | view.md（仅背景） |
| "搜索食谱排骨" | 搜索食谱 | 开头 | 排骨 | search.md |
| "筛选川菜" | 筛选菜系 | 开头 | 川菜（筛选条件） | search.md |
| "筛选含虾的菜" | 筛选食材 | 开头 | 虾（筛选条件） | search.md |
| "筛选简单菜" | 筛选难度 | 开头 | 简单（筛选条件） | search.md |
| "查看全部" | 查看全部 | 完整 | 无 | search.md（列出全部） |
| "修改食谱宫保虾球" | 修改食谱 | 开头 | 宫保虾球 | update.md |
| "修改步骤宫保虾球" | 修改步骤 | 开头 | 宫保虾球 | update.md |
| "废弃食谱宫保虾球" | 废弃食谱 | 开头 | 宫保虾球 | update.md |
| "不想要宫保虾球" | 不想要 | 开头 | 宫保虾球 | update.md |
| "删掉宫保虾球" | 删掉 | 开头 | 宫保虾球 | update.md |
| "废弃宫保虾球" | 废弃 | 开头 | 宫保虾球 | update.md |
| "记录做菜宫保虾球" | 记录做菜 | 开头 | 宫保虾球 | history.md |
| "查看历史宫保虾球" | 查看历史 | 开头 | 宫保虾球 | history.md |
| "查看统计宫保虾球" | 查看统计 | 开头 | 宫保虾球 | history.md |
| "生成清单宫保虾球" | 生成清单 | 开头 | 宫保虾球 | shopping.md |
| "录入食谱宫保虾球" | 录入食谱 | 开头 | 宫保虾球 | add.md |
| "导入食谱" | 导入食谱 | 完整 | 无 | add.md（JSON导入） |
| "添加派生关系 宫保虾球 基于 上海排骨年糕" | 添加派生关系 | 开头 | 宫保虾球 | relation.md |
| "查看派生关系 上海排骨年糕" | 查看派生关系 | 开头 | 上海排骨年糕 | relation.md |
| "宫保虾球" | 无命中 | - | 宫保虾球 | search.md（兜底菜名搜索） |

---

## 快速导航

| 功能 | 唤醒词数 | 参考文档 | 分类 |
|------|----------|----------|------|
| 做菜模式 | 2 | `features/view.md`（功能二） | A |
| 查看食谱 | 5 | `features/view.md`（功能一） | B |
| 搜索筛选 | 10 | `features/search.md` | C |
| 修改食谱 | 9 | `features/update.md` | D |
| 烹饪历史 | 3 | `features/history.md` | E |
| 采购清单 | 2 | `features/shopping.md` | F |
| 录入食谱 | 2 | `features/add.md` | G |
| 派生关系 | 2 | `features/relation.md` | H |
| 数据库结构 | - | `references/database_schema.md` | - |
| 分类参考 | - | `references/categories.md` | - |
| CLI命令 | - | `references/commands.md` | - |
| 做菜模式(2026-07-23 新) | - | `references/cooking_mode.md` + `templates/cooking_mode.html` | - |
| SkillBoard配置 | - | config-chef-cookbook.ts | - |

---

## JSON文件导入

> 将10步CLI操作简化为1步JSON导入。适合信息完整的场景。

```bash
# 1. 查看模板
python scripts/recipe_import.py template

# 2. AI生成JSON文件

# 3. 校验JSON
python scripts/recipe_json_validate.py recipe.json

# 4. 校验通过后导入
python scripts/recipe_import.py import recipe.json
```

详细说明见 `references/commands.md` 和 `features/add.md`。

---

## 核心原则

### 只增不删
- 没有物理删除操作
- 整道食谱废弃用 discard（status = '已废弃'），自动从列表/搜索中过滤
- 已废弃食谱可通过 show 查看简要信息

### 交互确认
- 所有写操作前必须展示，用户确认后执行
- 多选项时让用户选择，不默认

### 自然语言解析
- AI 负责解析用户意图，转换为 CLI 命令
- 信息不完整时追问，不猜测

---

## 表结构

共17张表，详见 `references/database_schema.md`

---

## 数据库并发支持

- **WAL 模式**：允许并发读和单个写
- **连接重试**：数据库锁定时自动重试（最多5次）
- **上下文管理器**：自动关闭连接，异常时回滚
- 详见 `scripts/db_config.py`

---

## 与其他技能联动

| 技能 | 联动场景 |
|------|---------|
| 卡路里 | 采购食品时可同步记录营养成分 |
| 居家管家 | 炊具借用/归位时参考 |

**处理原则**：主动思考是否需要联动，先完成主技能，再询问用户。