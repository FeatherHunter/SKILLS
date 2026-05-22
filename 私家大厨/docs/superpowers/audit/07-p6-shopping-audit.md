# P6 采购清单功能审计报告

> 审计日期：2026-05-23
> 审计范围：`features/shopping.md` + `scripts/shopping_manager.py` + `SKILL.md` P6路由
> 审计方法：模拟AI执行者完成2条采购清单路径的完整流程

---

## 一、功能定义摘要

| 项目 | 内容 |
|------|------|
| 路由 | SKILL.md P6，触发词：采购/清单/买/要买/准备食材 |
| 分流 | `features/shopping.md` |
| 脚本 | `scripts/shopping_manager.py generate <recipe_ids>` |
| 输出 | JSON → AI生成HTML → 保存到 `/home/feather/.openclaw/media/qqbot/shopping/` |
| HTML要求 | 12项基础 + 2项附加，共14项 |

---

## 二、路径一：单食谱（宫保虾球采购清单）

### 2.1 模拟流程

```
用户："宫保虾球采购清单"
  → SKILL.md P6触发词命中"采购"
  → 菜名提取："宫保虾球"
  → 分流到 shopping.md
  → AI需要先获取食谱ID
  → 调用 shopping_manager.py generate <id>
  → 获取JSON
  → AI生成HTML
  → 保存文件 + QQBot发送
```

### 2.2 发现的问题

#### [BUG-01] 命令不接受菜名，工作流缺失"菜名→ID"步骤（严重）

**位置**：`shopping.md` 工作流 + 命令参考

**现象**：
- 用户输入是菜名（如"宫保虾球"），但 `shopping_manager.py generate` 只接受 recipe_id（UUID格式）
- `shopping.md` 的工作流写的是 `用户请求 → AI调用脚本获取JSON → AI生成HTML → 发送HTML给用户`
- 缺少关键步骤：AI必须先通过 `recipe_manager.py show <菜名>` 获取 recipe_id

**对比**：`view.md` 的命令参考中明确列出了 `recipe_manager.py show <菜名或ID>`，而 `shopping.md` 完全没有提及这一步。

**影响**：AI执行者可能直接用菜名调用 `shopping_manager.py generate 宫保虾球`，导致查不到数据。

**修复建议**：工作流改为：
```
用户请求 → AI用菜名查recipe_id → AI调用脚本获取JSON → AI生成HTML → 发送HTML给用户
```

---

#### [BUG-02] shopping.md 未引用设计辅助技能（中等）

**位置**：`shopping.md` 全文

**现象**：
- `view.md` 明确要求生成HTML时**必须**调用 Taste Skill + UI/UX Pro Max 两个辅助技能
- `shopping.md` 的HTML生成要求部分完全没有提及这两个技能
- 采购清单HTML同样是手机端交互页面，需要同样的UX设计质量

**对比**：`view.md` 原文：
> "生成 HTML 时必须调用以下两个技能，违反视为不合格输出。"

**影响**：AI执行者可能跳过UX设计步骤，生成的HTML质量不一致。

**修复建议**：在 shopping.md 的"HTML 生成要求"部分添加与 view.md 相同的设计辅助技能要求。

---

#### [BUG-03] shopping_manager.py 参数解析不支持 `<recipe_ids>` 键名（轻微）

**位置**：`scripts/shopping_manager.py` 第16行

**现象**：
```python
recipe_ids_str = args.get("<recipe_id>") or args.get("<recipe_ids>")
```
脚本同时检查 `<recipe_id>` 和 `<recipe_ids>` 两个键名，但参数解析逻辑（第102行）只设置 `<recipe_id>`：
```python
if "<recipe_id>" not in args and "<recipe_ids>" not in args:
    args["<recipe_id>"] = arg
```
实际上 `<recipe_ids>` 永远不会被设置，`args.get("<recipe_ids>")` 是死代码。

**影响**：功能不受影响（`<recipe_id>` 始终被设置），但代码可读性差，且文档中 `<recipe_ids>` 的表述可能误导开发者。

---

#### [BUG-04] `--exclude-optional` 参数解析不严谨（轻微）

**位置**：`scripts/shopping_manager.py` 第42行

**现象**：
```python
if exclude_optional:
    conditions.append("is_optional = 0")
```
`--exclude-optional` 是布尔标志，当用户传 `--exclude-optional true` 或 `--exclude-optional false` 时，`args["--exclude-optional"]` 都是字符串 `"true"` / `"false"`，都为真值。

**影响**：`--exclude-optional false` 会错误地排除可选食材。

---

## 三、路径二：多食谱（宫保虾球+辣炒虾球采购清单）

### 3.1 模拟流程

```
用户："宫保虾球和辣炒虾球的采购清单"
  → SKILL.md P6触发词命中"采购"
  → 菜名提取困难（"宫保虾球和辣炒虾球"含连接词）
  → AI需解析出两个菜名
  → 分别查询两个recipe_id
  → 调用 shopping_manager.py generate "id1,id2"
  → 获取JSON
  → AI生成HTML（需处理同名食材合并）
  → 保存文件：采购清单_宫保虾球+辣炒虾球_时间戳.html
```

### 3.2 发现的问题

#### [BUG-05] 同名食材合并逻辑未定义（严重）

**位置**：`shopping.md` HTML生成要求 第11项

**现象**：
- 文档要求："多食谱同名食材合并显示总用量+来源"
- 但 `shopping_manager.py` 返回的JSON是按食谱分组的，每个食谱独立列出食材
- 文档没有定义合并规则：
  - 单位不同时如何合并？（如食谱A用"300g"，食谱B用"半斤"）
  - quantity为null时如何处理？
  - 合并后的quantity_text如何生成？
  - 合并后is_optional如何处理？（一个必需+一个可选）

**影响**：AI执行者需要自行决定合并策略，可能导致不一致的行为。

**修复建议**：在 shopping.md 中添加合并规则：
```
### 同名食材合并规则
1. 按食材name匹配（区分大小写）
2. 相同单位：quantity直接相加，quantity_text重新生成
3. 不同单位：保留原始显示，用"+"连接（如"300g+200ml"）
4. is_optional：合并后只要有一个食谱标记为必需，则标记为必需
5. substitute：合并后取非null值
6. 来源：记录所有来源食谱名
```

---

#### [BUG-06] shopping_manager.py 不执行食材合并（设计缺口）

**位置**：`scripts/shopping_manager.py`

**现象**：
- 脚本返回的是按食谱分组的原始数据
- 同名食材合并需要AI在生成HTML时自行处理
- 这意味着合并逻辑完全依赖AI的"理解"，没有确定性保障

**两种可能的修复方向**：
1. 在脚本中实现合并逻辑，返回合并后的数据
2. 在文档中详细定义合并规则，让AI按规则处理

---

#### [BUG-07] 多菜名解析规则缺失（中等）

**位置**：`shopping.md` 输入部分

**现象**：
- 用户可能说"宫保虾球和辣炒虾球的采购清单"、"宫保虾球、辣炒虾球清单"、"做宫保虾球和辣炒虾球需要买什么"
- 文档没有说明AI应如何从自然语言中提取多个菜名
- 文件名格式中用"+"连接多菜名，但这是文件命名规则，不是菜名解析规则

**影响**：AI可能无法正确解析多菜名输入。

---

## 四、存储路径差异分析

### 4.1 路径对比

| 功能 | 存储路径 |
|------|---------|
| 查看食谱 HTML | `/home/feather/.openclaw/media/qqbot/` |
| 做菜模式 HTML | `/home/feather/.openclaw/media/qqbot/` |
| 采购清单 HTML | `/home/feather/.openclaw/media/qqbot/shopping/` |

### 4.2 判定：有意设计

**理由**：
1. 采购清单是独立的功能模块，存储在子目录中便于管理和清理
2. 查看/做菜模式的HTML是食谱展示类，采购清单是工具类，性质不同
3. 文件命名规范也不同（`私房菜谱_*` vs `采购清单_*`），子目录进一步区分

**建议**：虽然判定为有意设计，但建议在 shopping.md 中说明为什么使用子目录，避免后续开发者误解。

---

## 五、14项HTML要求可执行性分析

| # | 要求 | 可执行性 | 问题 |
|---|------|---------|------|
| 1 | 单手操作友好 | 可执行 | 无 |
| 2 | 强光下可读 | 可执行 | 无 |
| 3 | 快速扫描 | 可执行 | 无 |
| 4 | 点击即标记 | 可执行 | 无 |
| 5 | 已买/未买区分 | 可执行 | 无 |
| 6 | 进度反馈 | 可执行 | 无 |
| 7 | 分类折叠 | 可执行 | 无 |
| 8 | 移动端适配 | 可执行 | 无 |
| 9 | 来源可见性 | **条件依赖** | 多食谱时才需要；单食谱时无意义 |
| 10 | 合并/拆分视图 | **条件依赖** | 多食谱时才需要 |
| 11 | 同名食材合并 | **规则缺失** | 合并规则未定义（见BUG-05） |
| 12 | 按食谱分组显示 | **条件依赖** | 多食谱时才需要 |
| 13 | 可选食材特殊标识 | 可执行 | 无 |
| 14 | 替代食材显示 | 可执行 | 无 |

**关键问题**：要求9/10/11/12在单食谱场景下无意义，但文档没有区分单/多食谱的HTML模板差异。

---

## 六、与view.md的对比分析

| 维度 | view.md | shopping.md | 差异 |
|------|---------|-------------|------|
| 设计辅助技能 | 必须调用Taste+UI/UX | 未提及 | **缺失** |
| 工作流完整性 | 查询→设计→生成→发送 | 请求→脚本→HTML→发送 | **缺少"菜名→ID"步骤** |
| HTML模板 | 有详细设计目标 | 仅14项要求 | 较简略 |
| 文件规范 | 明确 | 明确 | 一致 |
| 错误处理 | 未提及 | 未提及 | 一致（都缺失） |

---

## 七、问题汇总

| 编号 | 严重度 | 类型 | 摘要 |
|------|--------|------|------|
| BUG-01 | 严重 | 工作流缺陷 | 命令不接受菜名，缺少"菜名→ID"查询步骤 |
| BUG-02 | 中等 | 文档缺失 | 未引用Taste Skill和UI/UX Pro Max设计辅助技能 |
| BUG-03 | 轻微 | 代码质量 | `<recipe_ids>` 键名是死代码 |
| BUG-04 | 轻微 | 参数解析 | `--exclude-optional false` 会错误排除可选食材 |
| BUG-05 | 严重 | 规则缺失 | 同名食材合并逻辑未定义 |
| BUG-06 | 中等 | 设计缺口 | 脚本不执行合并，依赖AI自行处理 |
| BUG-07 | 中等 | 文档缺失 | 多菜名自然语言解析规则缺失 |

---

## 八、修复建议优先级

### P0（阻塞级）
1. **BUG-01**：在 shopping.md 工作流中补充"菜名→ID"步骤，明确AI需先调用 `recipe_manager.py show <菜名>` 获取ID
2. **BUG-05**：在 shopping.md 中定义同名食材合并规则（单位兼容、可选优先级、来源标注）

### P1（重要）
3. **BUG-02**：在 shopping.md 中添加设计辅助技能引用
4. **BUG-06**：考虑在 shopping_manager.py 中实现合并逻辑，或明确文档规则
5. **BUG-07**：补充多菜名解析规则示例

### P2（改进）
6. **BUG-03**：清理死代码
7. **BUG-04**：修正参数解析逻辑

---

## 九、结论

**状态：DONE_WITH_CONCERNS**

P6采购清单功能的核心流程基本可走通，但存在2个严重问题：
1. 工作流缺少"菜名→ID"的必要步骤，可能导致AI执行者直接用菜名调用脚本而失败
2. 多食谱合并的核心规则未定义，AI需要自行发明合并策略

建议优先修复BUG-01和BUG-05后再投入使用。
